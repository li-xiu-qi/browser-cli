# RAGFlow vs DB-GPT：流式输出实现深度分析

> 详细对比 DB-GPT 和 RAGFlow 的流式输出技术实现，从前端到后端的完整链路分析。

---

## 一、核心结论

### 两者都使用 SSE (Server-Sent Events)

| 项目 | 前端实现 | 后端实现 | 模型来源 |
|------|---------|---------|----------|
| **DB-GPT** | `@microsoft/fetch-event-source` | FastAPI `StreamingResponse` | 自托管 Worker |
| **RAGFlow** | 原生 `EventSource` API | Flask `Response` (迭代器) | 外部 LLM API |

### 核心差异

```
DB-GPT:  Worker(自托管) → StreamingResponse → 前端
RAGFlow: 外部 LLM API → Response → 前端
```

---

## 二、DB-GPT 流式输出实现

![DB-GPT 实现](assets/dbgpt-streaming-implementation.svg)

### 2.1 完整数据流

```
用户输入
    ↓
useChat Hook (React)
    ↓
@microsoft/fetch-event-source
    ↓
POST /api/v1/chat/completions
    ↓
FastAPI StreamingResponse
    ↓
Worker.stream_generate()
    ↓
逐字返回 token
```

### 2.2 前端实现

```typescript
// client/hooks/use-chat.ts
import { fetchEventSource } from '@microsoft/fetch-event-source';

export const useChat = () => {
  const chat = useCallback(async (params: ChatParams) => {
    const { data, onMessage, onDone, onError } = params;
    
    // 使用 fetchEventSource 建立 SSE 连接
    await fetchEventSource('/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
      
      // 收到消息回调
      onmessage(event) {
        if (event.data === '[DONE]') {
          onDone?.();
          return;
        }
        
        // 解析并回调
        const message = JSON.parse(event.data);
        const token = message.choices[0]?.delta?.content || '';
        onMessage?.(token);
      },
      
      // 错误处理
      onerror(err) {
        onError?.(err);
        throw err;
      },
      
      // 连接打开
      onopen(response) {
        if (response.ok) {
          return; // 一切正常
        }
        throw new Error('连接失败');
      },
      
      // 连接关闭
      onclose() {
        onDone?.();
      },
    });
  }, []);
  
  return { chat };
};

// 使用示例
const ChatComponent = () => {
  const { chat } = useChat();
  const [content, setContent] = useState('');
  
  const handleSend = async (message: string) => {
    await chat({
      data: { message, model: 'qwen-72b' },
      onMessage(token) {
        setContent(prev => prev + token); // 逐字追加
      },
    });
  };
  
  return <div>{content}</div>;
};
```

**特点**：
- 使用 `@microsoft/fetch-event-source` 库
- 支持自定义 headers（如 Authorization）
- 自动重连
- 详细的回调函数

### 2.3 后端实现

```python
# packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.post("/api/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """流式对话接口"""
    
    # 1. 获取 Worker
    worker_manager = get_worker_manager()
    worker = await worker_manager.get_worker(request.model)
    
    # 2. 定义流式生成器
    async def generate():
        try:
            # 调用 Worker 的流式生成
            async for token in worker.stream_generate(
                prompt=request.prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            ):
                # 封装为 SSE 格式
                data = {
                    "choices": [{
                        "delta": {"content": token},
                        "index": 0,
                        "finish_reason": None
                    }],
                    "model": request.model,
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            # 发送结束标记
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            # 错误处理
            error_data = {"error": str(e)}
            yield f"data: {json.dumps(error_data)}\n\n"
    
    # 3. 返回 StreamingResponse
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**特点**：
- 使用 FastAPI 的 `StreamingResponse`
- 异步生成器 `async def generate()`
- 自动管理 HTTP 连接
- 支持背压（backpressure）

### 2.4 Worker 流式生成

```python
# Worker 内部实现
class ModelWorker:
    async def stream_generate(self, prompt: str, **kwargs):
        """流式生成 token"""
        # 调用模型
        stream = self.model.generate_stream(prompt, **kwargs)
        
        # 逐字 yield
        for token in stream:
            yield token
            # 可选：添加小延迟模拟打字效果
            # await asyncio.sleep(0.01)
```

---

## 三、RAGFlow 流式输出实现

![RAGFlow 实现](assets/ragflow-streaming-implementation.svg)

### 3.1 完整数据流

```
用户输入
    ↓
chat-service.ts
    ↓
EventSource API
    ↓
POST /v1/chat/completions
    ↓
Flask Response (迭代器)
    ↓
RAG Pipeline (检索 + Prompt 构建)
    ↓
外部 LLM API (stream: true)
    ↓
透传 token 流
```

### 3.2 前端实现

```typescript
// web/src/services/chat-service.ts

export class ChatService {
  async sendMessage(params: ChatParams, callbacks: ChatCallbacks) {
    const { question, conversationId, onMessage, onDone } = params;
    
    // 使用原生 EventSource API
    const eventSource = new EventSource(
      `/v1/chat/completions?conversation_id=${conversationId}`
    );
    
    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') {
        onDone?.();
        eventSource.close();
        return;
      }
      
      try {
        const data = JSON.parse(event.data);
        const token = data.choices?.[0]?.delta?.content || '';
        onMessage?.(token);
      } catch (e) {
        console.error('解析失败:', e);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('SSE 错误:', error);
      eventSource.close();
    };
    
    eventSource.onopen = () => {
      console.log('SSE 连接已建立');
    };
    
    // 返回关闭函数
    return () => eventSource.close();
  }
}

// 使用示例
const ChatComponent = () => {
  const [content, setContent] = useState('');
  const chatService = useMemo(() => new ChatService(), []);
  
  const handleSend = async (question: string) => {
    await chatService.sendMessage(
      { question },
      {
        onMessage(token) {
          setContent(prev => prev + token);
        },
        onDone() {
          console.log('生成完成');
        },
      }
    );
  };
  
  return <div>{content}</div>;
};
```

**特点**：
- 使用原生 `EventSource` API
- 代码更简洁
- GET 请求（URL 传参）
- 不便于传递复杂 headers

### 3.3 后端实现

```python
# api/apps/conversation_app.py

from flask import Flask, Response, request
import json

app = Flask(__name__)

@app.route("/v1/chat/completions", methods=["POST"])
def chat_completions():
    """流式对话接口"""
    
    # 1. 解析请求
    req = request.json
    question = req.get("question")
    conversation_id = req.get("conversation_id")
    
    # 2. RAG 检索
    retriever = get_retriever()
    chunks = retriever.retrieve(question, top_k=5)
    
    # 3. 构建 Prompt
    prompt_builder = get_prompt_builder()
    prompt = prompt_builder.build(
        context="\n".join([c.content for c in chunks]),
        question=question
    )
    
    # 4. 定义生成器
    def generate():
        try:
            # 调用外部 LLM (流式)
            llm_client = get_llm_client()
            stream = llm_client.stream_chat(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4",
                stream=True,
            )
            
            # 透传 token
            for chunk in stream:
                token = chunk.choices[0].delta.content
                data = {
                    "choices": [{
                        "delta": {"content": token},
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(data)}\n\n"
            
            # 结束标记
            yield "data: [DONE]\n\n"
            
            # 保存对话历史
            save_conversation(conversation_id, question, full_response)
            
        except Exception as e:
            yield f"data: {{'error': '{str(e)}'}}\n\n"
    
    # 5. 返回流式响应
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
        }
    )
```

**特点**：
- 使用 Flask 的 `Response` + 生成器
- 先进行 RAG 检索（同步）
- 再调用外部 LLM（流式）
- 透传外部 API 的流

---

## 四、技术对比

![技术对比](assets/streaming-implementation-comparison.svg)

### 4.1 详细对比

| 维度 | DB-GPT | RAGFlow |
|------|--------|---------|
| **前端库** | `@microsoft/fetch-event-source` | 原生 `EventSource` |
| **优点** | 支持 POST、自定义 headers | 简洁、无需额外依赖 |
| **缺点** | 需要安装依赖 | 只支持 GET、headers 受限 |
| **后端框架** | FastAPI | Flask |
| **响应类** | `StreamingResponse` | `Response` |
| **异步支持** | 原生 async/await | 需配合生成器 |
| **模型位置** | 自托管 Worker | 外部 API |
| **流式层级** | Worker → 后端 → 前端 | 外部 API → 后端 → 前端 |
| **RAG 集成** | 可选 (AWEL) | 内置 (DeepDoc) |

### 4.2 性能对比

| 指标 | DB-GPT | RAGFlow |
|------|--------|---------|
| **首 token 延迟** | Worker 响应时间 | 检索 + 外部 API 延迟 |
| **生成速度** | 取决于 Worker GPU | 取决于外部 API |
| **稳定性** | 受 Worker 负载影响 | 受外部 API 稳定性影响 |
| **可扩展性** | 扩容 Worker | 无法直接控制 |

---

## 五、SSE 协议详解

![SSE 协议](assets/sse-protocol-detail.svg)

### 5.1 协议格式

```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive

data: {"choices":[{"delta":{"content":"你"}}]}

data: {"choices":[{"delta":{"content":"你好"}}]}

data: {"choices":[{"delta":{"content":"你好，"}}]}

data: [DONE]

```

### 5.2 关键字段

| 字段 | 说明 | 示例 |
|------|------|------|
| `data:` | 消息数据（必需） | `data: {"text": "hello"}` |
| `event:` | 事件类型（可选） | `event: message` |
| `id:` | 消息 ID（可选） | `id: 12345` |
| `retry:` | 重连时间（可选） | `retry: 3000` |
| 空行 | 触发 `onmessage` | 两个 `\n` |

---

## 六、最佳实践

### 6.1 前端最佳实践

```typescript
// 1. 使用 AbortController 支持取消
const controller = new AbortController();

await fetchEventSource('/api/chat', {
  signal: controller.signal,
  // ...
});

// 用户点击停止时
controller.abort();

// 2. 防抖处理
const handleMessage = useCallback(
  debounce((token) => {
    setContent(prev => prev + token);
  }, 16), // 60fps
  []
);

// 3. 错误重试
let retryCount = 0;
const maxRetries = 3;

const chatWithRetry = async () => {
  try {
    await chat();
  } catch (e) {
    if (retryCount < maxRetries) {
      retryCount++;
      setTimeout(chatWithRetry, 1000);
    }
  }
};
```

### 6.2 后端最佳实践

```python
# 1. 设置超时
@app.post("/chat")
async def chat():
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no"},  # 禁用代理缓冲
    )

# 2. 错误处理
async def generate():
    try:
        async for token in model.generate():
            yield f"data: {token}\n\n"
    except Exception as e:
        yield f"event: error\ndata: {str(e)}\n\n"
    finally:
        yield "data: [DONE]\n\n"

# 3. 背压控制
async def generate():
    queue = asyncio.Queue(maxsize=10)  # 限制队列大小
    
    async def producer():
        async for token in model.generate():
            await queue.put(token)
    
    async def consumer():
        while True:
            token = await queue.get()
            yield f"data: {token}\n\n"
```

---

## 七、常见问题

### Q1: 为什么不用 WebSocket？

```
SSE vs WebSocket

SSE:
• 基于 HTTP，更简单
• 自动重连
• 单向通信（服务器→客户端）
• 适合：流式输出、推送通知

WebSocket:
• 全双工通信
• 需要额外协议升级
• 代码更复杂
• 适合：聊天室、实时协作
```

**结论**：流式输出用 SSE 更简单、更合适。

### Q2: 如何处理中断？

```typescript
// 前端：AbortController
const controller = new AbortController();
fetchEventSource('/chat', { signal: controller.signal });
controller.abort(); // 中断请求

// 后端：检测连接断开
async def generate():
    try:
        async for token in model.generate():
            yield token
            # 如果客户端断开，这里会抛出异常
    except asyncio.CancelledError:
        # 清理资源
        model.stop_generation()
```

### Q3: 如何优化首 token 延迟？

```
优化策略：

1. 预热连接
   - 保持长连接池
   - 减少 TCP 握手时间

2. 并行处理
   - DB-GPT: 检索和生成并行
   - RAGFlow: 优化检索速度

3. 缓存优化
   - 缓存常用 Prompt
   - 预加载模型

4. 模型优化
   - 使用更快的模型
   - 模型量化
```

---

## 八、总结

### 核心差异

```
DB-GPT:  自托管模型 + FastAPI + fetch-event-source
RAGFlow: 外部 LLM   + Flask   + EventSource
```

### 选择建议

| 场景 | 推荐方案 |
|------|---------|
| 自托管模型 | DB-GPT 方案 |
| 调用外部 API | RAGFlow 方案 |
| 需要 POST 传参 | `@microsoft/fetch-event-source` |
| 简单场景 | 原生 `EventSource` |
| Python 后端 | FastAPI `StreamingResponse` |

### 一句话总结

> **DB-GPT 和 RAGFlow 都使用 SSE 实现流式输出，区别在于：DB-GPT 自托管模型，使用 FastAPI + fetch-event-source；RAGFlow 调用外部 LLM，使用 Flask + EventSource。SSE 是流式输出的行业标准，比 WebSocket 更简单、更适合单向数据流。**

---

## 附录

### 相关图表

| 图表 | 说明 |
|------|------|
| `dbgpt-streaming-implementation.svg` | DB-GPT 实现细节 |
| `ragflow-streaming-implementation.svg` | RAGFlow 实现细节 |
| `streaming-implementation-comparison.svg` | 技术对比 |
| `sse-protocol-detail.svg` | SSE 协议详解 |

### 参考文档

- [DB-GPT-流式输出支持](DB-GPT-流式输出支持.md)
- [DB-GPT-前端架构分析](DB-GPT-前端架构分析.md)
- [RAGFlow-架构深度分析](RAGFlow-架构深度分析.md)

---

*文档更新时间: 2026-02-06*
