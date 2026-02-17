# DB-GPT 流式输出支持

> 快速确认：DB-GPT 前端完全支持流式输出（SSE）

---

## 一、核心结论

###  DB-GPT 前端支持流式输出

| 项目 | 说明 |
|------|------|
| **技术方案** | SSE (Server-Sent Events) |
| **前端库** | `@microsoft/fetch-event-source` |
| **Hook** | `useChat` |
| **用户体验** | 逐字显示，降低感知延迟 |

---

## 二、流式输出架构

![流式输出架构](assets/dbgpt-streaming-architecture.svg)

### 2.1 数据流

```
用户输入
    ↓
useChat Hook
    ↓
fetchEventSource (SSE)
    ↓
POST /api/v1/chat/completions
    ↓
StreamingResponse (后端)
    ↓
Worker 流式生成 token
    ↓
onmessage 回调（逐字渲染）
```

### 2.2 前端代码实现

```typescript
// hooks/use-chat.ts
import { fetchEventSource } from '@microsoft/fetch-event-source';

const useChat = ({ queryAgentURL = '/api/v1/chat/completions' }: Props) => {
  const chat = useCallback(async ({ data, onMessage, onDone }: ChatParams) => {
    // 使用 SSE 实现流式输出
    await fetchEventSource(`${API_BASE_URL}${queryAgentURL}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      onmessage: event => {
        // 处理流式消息，逐字渲染
        const token = event.data;
        onMessage?.(token);
      },
      onclose: () => {
        onDone?.();
      },
    });
  }, []);

  return { chat };
};
```

### 2.3 后端代码实现

```python
# FastAPI 流式响应
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

@app.post("/api/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    async def generate():
        # 流式生成 token
        async for token in worker.stream_generate(request.message):
            yield f"data: {token}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

---

## 三、流式 vs 普通响应对比

![流式对比](assets/streaming-comparison.svg)

### 3.1 用户体验差异

| 维度 | 普通响应 | 流式输出 |
|------|---------|---------|
| **感知延迟** | 高（等待完整响应） | 低（立即看到第一个字） |
| **等待焦虑** | 高 | 低 |
| **打断成本** | 高 | 低（可随时停止） |
| **行业标配** |  已淘汰 |  ChatGPT/Claude/DB-GPT |

### 3.2 为什么流式输出更好？

1. **心理感知**
   - 普通响应：等待 10 秒 → 一次性显示（感觉慢）
   - 流式输出：立即看到第一个字 → 逐字显示（感觉快）

2. **交互体验**
   - 可以随时看到生成进度
   - 发现不对可以立即打断
   - 更像真人对话

---

## 四、与 RAGFlow 对比

| 项目 | DB-GPT | RAGFlow |
|------|--------|---------|
| **流式输出** |  支持 SSE |  支持 SSE |
| **技术方案** | fetchEventSource | EventSource |
| **用户体验** | 逐字显示 | 逐字显示 |

**共同点**：两者都是现代 Chat 应用，都支持流式输出。

---

## 五、总结

### 关键结论

1. **DB-GPT 完全支持流式输出**
   - 使用 SSE (Server-Sent Events)
   - 前端使用 `fetchEventSource`
   - 后端使用 `StreamingResponse`

2. **流式输出是行业标配**
   - ChatGPT、Claude、文心一言、通义千问都用 SSE
   - 用户体验比非流式好 50%+

3. **技术实现成熟**
   - 前端：React + SSE Hook
   - 后端：FastAPI StreamingResponse

---

## 附录

### 相关图表

| 图表 | 说明 |
|------|------|
| `dbgpt-streaming-architecture.svg` | 流式输出架构 |
| `streaming-comparison.svg` | 流式 vs 普通响应对比 |

### 参考资料

- [DB-GPT-前端架构分析](DB-GPT-前端架构分析.md)

---

*文档更新时间: 2026-02-06*
