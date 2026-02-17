# smolagents vs DB-GPT 流式输出对比

> 分析日期: 2026-02-06
> 对比项目: smolagents vs DB-GPT

---

## 一、技术方案对比

### 1.1 核心方案差异

| 维度 | smolagents | DB-GPT |
|------|------------|--------|
| 技术方案 | Python Generator | SSE |
| 传输层 | 内存 | HTTP |
| 适用场景 | 本地库、脚本 | Web服务 |
| 延迟 | 极低 | 低 |
| 实现复杂度 | 简单 | 中等 |
| 网络依赖 | 无 | 需要HTTP服务器 |

### 1.2 架构定位差异

smolagents 采用**简洁优先**的设计哲学。作为Python库，它不需要考虑网络传输，直接使用语言原生的Generator机制实现流式输出。这种设计让本地脚本和Gradio界面可以直接消费流式数据，无需额外的协议封装。

DB-GPT 采用**Web优先**的设计哲学。作为完整的Web应用，它需要支持浏览器客户端通过HTTP协议接收流式数据。SSE是Web标准支持的流式传输方案，与React前端配合成熟。

### 1.3 协议层对比

smolagents 没有协议层。Generator在内存中直接传递Python对象，延迟仅限于函数调用开销。

DB-GPT 基于HTTP协议。SSE使用标准的text/event-stream媒体类型，需要维护TCP连接、HTTP头部解析、事件格式封装，延迟包含网络往返时间。

---

## 二、实现机制详解

### 2.1 smolagents 实现机制

#### 核心类图

```
┌─────────────────────────────────────────────────────────────┐
│                      smolagents 流式架构                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌──────────────┐                                          │
│   │  agent.run   │  stream=True 触发流式模式                  │
│   └──────┬───────┘                                          │
│          │                                                   │
│          ▼                                                   │
│   ┌──────────────┐     ┌──────────────┐                     │
│   │  _run_stream │────▶│  Generator   │  主控制器            │
│   └──────┬───────┘     └──────────────┘                     │
│          │                                                   │
│     ┌────┴────┐                                             │
│     ▼         ▼                                             │
│ ┌────────┐  ┌────────┐                                      │
│ │Planning│  │ Action │  步骤类型                             │
│ │ Step   │  │ Step   │                                      │
│ └───┬────┘  └────┬───┘                                      │
│     │            │                                           │
│     └────┬───────┘                                           │
│          ▼                                                   │
│   ┌──────────────┐                                          │
│   │ _step_stream │  各Agent子类实现                          │
│   └──────┬───────┘                                          │
│          │                                                   │
│     ┌────┴────┐                                             │
│     ▼         ▼                                             │
│ ┌────────┐  ┌────────┐                                      │
│ │模型生成 │  │工具执行 │                                      │
│ │ 流式   │  │ 非流式 │                                      │
│ └───┬────┘  └────┬───┘                                      │
│     │            │                                           │
│     └────┬───────┘                                           │
│          ▼                                                   │
│   ┌──────────────┐                                          │
│   │ yield 事件   │  ChatMessageStreamDelta                  │
│   │              │  ToolCall / ToolOutput                   │
│   │              │  ActionStep / FinalAnswerStep            │
│   └──────────────┘                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### _run_stream 方法实现

`_run_stream` 是整个流式执行的主控制器，采用Python Generator模式实现。

```python
def _run_stream(
    self, task: str, max_steps: int, images: list["PIL.Image.Image"] | None = None
) -> Generator[ActionStep | PlanningStep | FinalAnswerStep | ChatMessageStreamDelta]:
    self.step_number = 1
    returned_final_answer = False
    while not returned_final_answer and self.step_number <= max_steps:
        if self.interrupt_switch:  # 中断检查
            raise AgentError("Agent interrupted.", self.logger)

        # 1. 规划步骤
        if self.planning_interval is not None:
            for element in self._generate_planning_step(task, ...):
                yield element  # 直接透传规划步骤的流式输出

        # 2. 执行动作步骤
        action_step = ActionStep(step_number=self.step_number, ...)
        try:
            for output in self._step_stream(action_step):
                yield output  # 透传每一步的流式输出

                if isinstance(output, ActionOutput) and output.is_final_answer:
                    final_answer = output.output
                    returned_final_answer = True
        except AgentGenerationError as e:
            raise e
        except AgentError as e:
            action_step.error = e
        finally:
            self._finalize_step(action_step)
            self.memory.steps.append(action_step)
            yield action_step  # 最终产出完整的ActionStep
            self.step_number += 1
```

关键设计点：

- **双重yield模式**: 内部透传直接转发子生成器的输出，最终产出完整的步骤对象
- **中断检查点**: 每步开始前检查`self.interrupt_switch`，中断时抛出`AgentError`
- **异常处理策略**: `AgentGenerationError`直接抛出，`AgentError`记录并继续

#### 流式消息类型系统

```python
StreamEvent: TypeAlias = Union[
    ChatMessageStreamDelta,    # 模型流式输出片段
    ChatMessageToolCall,        # 工具调用定义
    ActionOutput,               # 动作输出结果
    ToolCall,                   # 工具调用请求
    ToolOutput,                 # 工具执行输出
    PlanningStep,               # 规划步骤
    ActionStep,                 # 动作步骤
    FinalAnswerStep,            # 最终答案
]
```

`ChatMessageStreamDelta`定义：

```python
@dataclass
class ChatMessageStreamDelta:
    content: str | None = None           # 文本内容片段
    tool_calls: list[ChatMessageToolCallStreamDelta] | None = None
    token_usage: TokenUsage | None = None
```

#### Gradio消费方式

GradioUI通过`_stream_response`方法直接消费Agent的流式输出：

```python
def _stream_response(self, message: str | dict, history: list[dict]) -> Generator:
    task, task_files = self._process_message(message)
    all_messages: list[gr.ChatMessage] = []
    accumulated_events: list[ChatMessageStreamDelta] = []
    streaming_msg_idx: int | None = None

    for event in self.agent.run(task, stream=True, ...):
        if isinstance(event, ActionStep | PlanningStep | FinalAnswerStep):
            # 步骤完成，清理流式消息，添加完整步骤消息
            if streaming_msg_idx is not None:
                all_messages.pop(streaming_msg_idx)
                streaming_msg_idx = None

            for msg in pull_messages_from_step(event, skip_model_outputs=...):
                all_messages.append(gr.ChatMessage(...))
                yield all_messages
            accumulated_events = []

        elif isinstance(event, ChatMessageStreamDelta):
            # 流式增量，实时更新消息
            accumulated_events.append(event)
            text = agglomerate_stream_deltas(accumulated_events).render_as_markdown()
            text = text.replace("<", r"\<").replace(">", r"\>")
            msg = gr.ChatMessage(role="assistant", content=text)
            
            if streaming_msg_idx is None:
                streaming_msg_idx = len(all_messages)
                all_messages.append(msg)
            else:
                all_messages[streaming_msg_idx] = msg
            yield all_messages
```

### 2.2 DB-GPT 实现机制

#### 核心类图

```
┌─────────────────────────────────────────────────────────────┐
│                       DB-GPT 流式架构                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────┐                                               │
│   │  用户   │                                               │
│   └────┬────┘                                               │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────┐                                            │
│   │ React 前端  │                                            │
│   └──────┬──────┘                                            │
│          │                                                   │
│          ▼                                                   │
│   ┌─────────────┐     ┌─────────────────┐                   │
│   │   useChat   │────▶│fetchEventSource │                   │
│   └──────┬──────┘     │ @microsoft/...  │                   │
│          │            └────────┬────────┘                   │
│          │                     │                            │
│          │                     ▼                            │
│          │            ┌─────────────────┐                   │
│          │            │ POST /api/v1/   │                   │
│          │            │ chat/completions│                   │
│          │            └────────┬────────┘                   │
│          │                     │                            │
│          │                     ▼                            │
│          │            ┌─────────────────┐                   │
│          │            │StreamingResponse│  FastAPI           │
│          │            │   text/event-   │                   │
│          │            │    stream       │                   │
│          │            └────────┬────────┘                   │
│          │                     │                            │
│          │                     ▼                            │
│          │            ┌─────────────────┐                   │
│          └───────────▶│  Worker流式生成  │                   │
│                       └─────────────────┘                   │
│                                                              │
│   数据流向: 服务器 → HTTP流 → 前端 onmessage 回调 → 逐字渲染    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 前端实现

使用`@microsoft/fetch-event-source`库实现SSE客户端：

```typescript
// hooks/use-chat.ts
import { fetchEventSource } from '@microsoft/fetch-event-source';

const useChat = ({ queryAgentURL = '/api/v1/chat/completions' }: Props) => {
  const chat = useCallback(async ({ data, onMessage, onDone }: ChatParams) => {
    await fetchEventSource(`${API_BASE_URL}${queryAgentURL}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      onmessage: event => {
        const token = event.data;
        onMessage?.(token);  // 逐字渲染
      },
      onclose: () => {
        onDone?.();
      },
    });
  }, []);

  return { chat };
};
```

前端状态管理：

```typescript
interface ChatState {
  // 历史消息列表（已完成的对话）
  messages: Array<{
    id: string;
    role: 'user' | 'assistant';
    content: string;
    createdAt: Date;
  }>;
  
  // 当前流式消息缓冲区（正在生成的）
  currentMessage: string;
  
  // SSE连接实例
  eventSource: EventSource | null;
  
  // 加载状态
  isStreaming: boolean;
}
```

#### 后端实现

FastAPI使用StreamingResponse返回SSE流：

```python
from fastapi.responses import StreamingResponse

@app.post("/api/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    async def generate():
        async for token in worker.stream_generate(request.message):
            yield f"data: {token}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

后端状态管理：

```python
@app.post("/api/chat")
async def chat(request: ChatRequest):
    # 1. 保存用户消息
    await save_message(
        conv_id=request.conv_id,
        role='user',
        content=request.message
    )
    
    # 2. 创建消息缓冲区
    message_buffer = []
    
    # 3. 流式生成
    async def generate():
        try:
            async for token in worker.stream_generate(request.message):
                message_buffer.append(token)
                yield f"data: {token}\n\n"
        finally:
            # 4. 无论是否中断，都保存已生成内容
            await save_message(
                conv_id=request.conv_id,
                role='assistant',
                content=''.join(message_buffer),
                is_complete=len(message_buffer) > 0
            )
    
    return StreamingResponse(generate())
```

### 2.3 机制差异总结

| 阶段 | smolagents | DB-GPT |
|------|------------|--------|
| 数据生成 | Python Generator yield | 异步生成器 yield |
| 数据传输 | 内存直接传递 | HTTP SSE协议 |
| 数据消费 | Gradio直接迭代 | fetchEventSource监听 |
| 状态管理 | 本地内存 | 前端State + 后端buffer |
| 中断方式 | 设置标志位 | 关闭连接或abort |
| 历史保存 | 内存中累积 | 数据库一次性写入 |

---

## 三、优缺点对比

### 3.1 smolagents Generator方案

#### 优点

1. **实现简单**
   - 使用Python原生Generator语法
   - 无需网络协议封装
   - 代码量少，易于理解

2. **延迟极低**
   - 内存直接传递Python对象
   - 无网络往返开销
   - 无序列化/反序列化开销

3. **资源占用低**
   - 无需维护HTTP连接
   - 无需事件格式封装
   - 适合资源受限环境

4. **调试友好**
   - 可以直接在Python中迭代测试
   - 无需启动Web服务器
   - 错误堆栈清晰

#### 缺点

1. **仅限本地**
   - 无法跨网络传输
   - 无法分布式部署
   - 前后端必须在一台机器

2. **前端受限**
   - 主要支持Gradio
   - 浏览器集成需要额外适配
   - 移动端支持困难

3. **扩展性有限**
   - 不支持多用户并发
   - 无法水平扩展
   - 不适合微服务架构

### 3.2 DB-GPT SSE方案

#### 优点

1. **标准化协议**
   - SSE是Web标准
   - 浏览器原生支持
   - 与现有Web生态兼容

2. **跨网络支持**
   - 支持前后端分离
   - 可以分布式部署
   - 支持移动端访问

3. **技术栈成熟**
   - FastAPI StreamingResponse成熟
   - React + fetchEventSource广泛使用
   - 文档和社区资源丰富

4. **可扩展**
   - 支持负载均衡
   - 可以水平扩展
   - 适合微服务架构

#### 缺点

1. **需要HTTP服务器**
   - 必须部署FastAPI/Flask
   - 增加运维复杂度
   - 需要处理部署和配置

2. **延迟略高**
   - 网络传输延迟
   - HTTP协议开销
   - 序列化/反序列化开销

3. **资源占用较高**
   - 维护TCP连接
   - 服务器并发连接数限制
   - 需要连接池管理

4. **实现复杂度中等**
   - 需要处理连接管理
   - 需要处理重连逻辑
   - 错误处理更复杂

### 3.3 对比矩阵

| 维度 | smolagents Generator | DB-GPT SSE |
|------|---------------------|------------|
| 复杂度 | 低 | 中等 |
| 实时性 | 极高 | 高 |
| 可扩展性 | 限于单机 | 支持分布式 |
| 前端选择 | 依赖Gradio | 任意前端框架 |
| 浏览器外使用 | Python脚本友好 | 需HTTP客户端 |
| 中断控制 | 简单，直接调方法 | 需关闭连接 |
| 资源占用 | 低 | 较高 |
| 部署成本 | 极低 | 中等 |
| 调试难度 | 低 | 中等 |
| 跨网络 | 不支持 | 支持 |

---

## 四、适用场景对比

### 4.1 场景推荐表

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| Python库 | smolagents | 无需服务器，直接集成 |
| Web应用 | DB-GPT | 标准化协议，浏览器支持好 |
| 微服务 | DB-GPT | 跨服务通信，HTTP友好 |
| Jupyter Notebook | 两者皆可 | smolagents更简洁，DB-GPT可演示 |
| 移动端 | DB-GPT | HTTP协议，移动网络友好 |
| 快速原型 | smolagents | 快速验证，无需部署 |
| 生产环境Web | DB-GPT | 标准化，可扩展 |
| 数据分析脚本 | smolagents | 本地执行，无需网络 |
| 多用户系统 | DB-GPT | 支持并发，可水平扩展 |
| 嵌入式设备 | smolagents | 资源占用低 |

### 4.2 场景详解

#### 场景1: Python库开发

推荐使用 smolagents。

理由：
- 库的用户不需要部署Web服务器
- Generator接口是Python标准模式
- 可以直接在脚本中使用
- 与Jupyter Notebook无缝集成

#### 场景2: Web应用

推荐使用 DB-GPT。

理由：
- 浏览器需要HTTP协议
- SSE是Web标准
- 前端框架都有SSE支持
- 可以部署到云端

#### 场景3: Jupyter Notebook

两者皆可。

smolagents优势：
- 更简单，无需启动服务器
- 直接显示输出
- 适合个人分析

DB-GPT优势：
- 可以模拟生产环境
- 可以分享给其他人访问
- 适合演示和教学

#### 场景4: 微服务架构

推荐使用 DB-GPT。

理由：
- 服务间通过HTTP通信
- 可以独立部署和扩展
- 支持服务发现和负载均衡
- 与K8s等编排系统兼容

#### 场景5: 移动端应用

推荐使用 DB-GPT。

理由：
- HTTP协议移动网络友好
- 可以处理网络不稳定
- 支持自动重连
- 与移动开发框架兼容

---

## 五、如何为我们的项目选择

### 5.1 AI数据分析系统的架构需求

AI数据分析系统的核心需求：

1. **用户界面**: 需要Web界面供业务用户使用
2. **部署方式**: 可能需要在企业内网部署
3. **并发支持**: 多用户同时使用
4. **集成需求**: 可能需要与其他系统集成
5. **开发效率**: 需要快速迭代开发
6. **运维成本**: 需要控制部署和运维成本

### 5.2 推荐方案: 混合架构

基于以上需求，推荐采用**混合架构**：

```
┌─────────────────────────────────────────────────────────────┐
│                    AI数据分析系统 混合架构                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                    前端层                            │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │   │
│   │  │  Web界面    │  │ Jupyter插件 │  │  API客户端  │  │   │
│   │  │  React      │  │  插件       │  │  Python SDK│  │   │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │   │
│   │         └─────────────────┴─────────────────┘        │   │
│   │                         │                            │   │
│   │                         ▼                            │   │
│   │              ┌─────────────────┐                     │   │
│   │              │  API Gateway    │                     │   │
│   │              │  FastAPI        │                     │   │
│   │              └────────┬────────┘                     │   │
│   └───────────────────────┼──────────────────────────────┘   │
│                           │                                  │
│   ┌───────────────────────┼──────────────────────────────┐   │
│   │                核心引擎层 ← 参考smolagents设计          │   │
│   │                       │                                │   │
│   │              ┌────────▼────────┐                       │   │
│   │              │ AnalysisAgent   │                       │   │
│   │              │ ┌─────────────┐ │                       │   │
│   │              │ │_run_stream  │ │  Generator模式         │   │
│   │              │ │ yield Event │ │  内部使用              │   │
│   │              │ └─────────────┘ │                       │   │
│   │              └────────┬────────┘                       │   │
│   │                       │                                │   │
│   │         ┌─────────────┼─────────────┐                  │   │
│   │         ▼             ▼             ▼                  │   │
│   │   ┌─────────┐   ┌─────────┐   ┌─────────┐             │   │
│   │   │ NLU理解 │   │ SQL生成 │   │ 可视化  │             │   │
│   │   └─────────┘   └─────────┘   └─────────┘             │   │
│   │                                                       │   │
│   └───────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 具体设计建议

#### 核心引擎: 采用smolagents模式

核心分析引擎使用Generator模式，参考smolagents设计：

```python
# 核心分析引擎使用Generator
class AnalysisAgent:
    def analyze_stream(self, question: str) -> Generator[AnalysisEvent, None, None]:
        """流式数据分析主流程"""
        
        # 阶段1: 意图理解
        yield AnalysisStatus("正在理解问题...")
        for delta in self.nlu_model.stream_generate(question):
            yield ThoughtDelta(delta)
        
        # 阶段2: SQL生成
        yield AnalysisStatus("正在生成SQL...")
        sql_deltas = []
        for delta in self.sql_model.stream_generate(prompt):
            sql_deltas.append(delta)
            yield SQLStreamDelta(delta)
        sql = accumulate_sql(sql_deltas).sql
        
        # 阶段3: 执行查询
        yield AnalysisStatus("正在执行查询...")
        result = self.db.execute(sql)
        yield QueryResult(result)
        
        # 阶段4: 生成可视化
        yield AnalysisStatus("正在生成图表...")
        chart_code = self.viz_generator.generate(result)
        yield VisualizationCode(chart_code)
        
        # 阶段5: 最终报告
        yield FinalReport(self.report_generator.generate(question, result, chart_code))
```

#### Web接口: 采用DB-GPT模式

Web层使用SSE协议，参考DB-GPT设计：

```python
# FastAPI适配层
@app.post("/api/analyze/stream")
async def analyze_stream_endpoint(request: QueryRequest):
    agent = get_agent()
    
    async def event_generator():
        # 将Generator转换为SSE流
        for event in agent.analyze_stream(request.question):
            yield f"data: {json.dumps(event.to_dict())}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
```

#### 事件类型设计

参考smolagents的StreamEvent，设计统一的事件体系：

```python
AnalysisEvent = Union[
    ThoughtDelta,        # 思考过程片段
    SQLGenerated,        # SQL生成结果
    QueryExecuting,      # 执行开始
    QueryResult,         # 查询结果
    VisualizationCode,   # 可视化代码
    ChartRendered,       # 图表渲染
    FinalReport,         # 最终报告
]

@dataclass
class ThoughtDelta:
    content: str
    phase: str  # 当前阶段
    
@dataclass
class SQLStreamDelta:
    sql_fragment: str
    
@dataclass
class QueryResult:
    data: dict
    row_count: int
```

#### 中断处理

参考smolagents的简单中断机制，结合asyncio实现：

```python
class AnalysisAgent:
    def __init__(self):
        self._interrupt_flag = False
        self._cancel_event = asyncio.Event()
    
    def interrupt(self):
        self._interrupt_flag = True
        self._cancel_event.set()
    
    async def analyze_stream(self, question: str):
        for step in self.steps:
            if self._interrupt_flag:
                yield AnalysisInterrupted(reason="用户中断")
                return
            
            async for event in self.execute_step(step):
                yield event
```

### 5.4 混合方案的优势

1. **核心引擎简洁**
   - 使用Generator模式，代码简洁
   - 易于单元测试
   - 不依赖Web框架

2. **接口层灵活**
   - Web层使用SSE，标准化
   - 可以支持多种前端
   - 可以添加认证、限流等中间件

3. **可扩展**
   - 核心引擎可以独立演进
   - Web层可以水平扩展
   - 支持多种客户端

4. **开发效率高**
   - 核心逻辑用Generator，易于调试
   - 接口层标准化，文档自动生成
   - 前后端可以并行开发

---

## 六、总结

### 6.1 核心结论

| 维度 | smolagents | DB-GPT |
|------|------------|--------|
| 核心方案 | Python Generator | SSE over HTTP |
| 最佳场景 | 本地库、Python脚本 | Web应用、分布式系统 |
| 技术复杂度 | 低 | 中等 |
| 扩展性 | 单机 | 分布式 |
| 延迟 | 极低 | 低 |

### 6.2 选择建议

- **如果开发Python库**: 直接使用smolagents的Generator模式
- **如果开发Web应用**: 使用DB-GPT的SSE方案
- **如果需要兼顾两者**: 采用混合架构，核心用Generator，接口层用SSE

### 6.3 对我们项目的最终建议

AI数据分析系统推荐采用**混合架构**：

1. **核心分析引擎**参考smolagents，使用Python Generator实现流式输出
2. **Web API层**参考DB-GPT，使用SSE协议与前端通信
3. **事件系统设计**参考smolagents的StreamEvent类型定义
4. **前端消费**参考DB-GPT的useChat hook设计

这种架构兼顾了开发效率和部署灵活性，核心逻辑简洁可测试，接口层标准化可扩展。

---

## 附录

### 相关文档

- [[03-smolagents-流式输出机制深度分析]]
- [[DB-GPT-流式输出支持]]
- [[流式输出与历史会话生命周期分析]]

### 参考代码仓库

- smolagents: huggingface/smolagents
- DB-GPT: eosphoros-ai/DB-GPT

---

*文档更新时间: 2026-02-06*
