# smolagents 流式输出机制深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/agents.py, gradio_ui.py

---

## 一、总体设计

### 1.1 流式输出在 smolagents 中的定位

smolagents 的流式输出设计遵循**简洁优先**原则，采用 Python Generator 模式实现流式输出。这种设计不需要额外的网络协议层，直接在 Python 内存中传递数据，非常适合本地交互和 Gradio 界面场景。

**核心设计特点**:

| 特性 | smolagents 实现 |
|------|----------------|
| 技术方案 | Python Generator |
| 数据传递 | 内存直接传递，无序列化开销 |
| 适用场景 | 本地脚本、Jupyter Notebook、Gradio UI |
| 前端集成 | Gradio ChatInterface 原生支持 |
| 网络依赖 | 无需 HTTP 协议层 |
| 中断控制 | 直接调用方法，简单可控 |

### 1.2 流式架构概览

```
用户调用 agent.run(stream=True)
         │
         ▼
┌─────────────────────┐
│    _run_stream      │  主循环控制器
│    (agents.py:540)  │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌─────────┐
│Planning │  │ Action  │  步骤类型
│  Step   │  │  Step   │
└────┬────┘  └────┬────┘
     │            │
     ▼            ▼
┌─────────────────────┐
│    _step_stream     │  单步执行
│  (各Agent子类实现)   │
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌─────────┐
│ 模型生成 │  │ 工具执行 │
│  (流式)  │  │ (非流式) │
└────┬────┘  └────┬────┘
     │            │
     ▼            ▼
┌─────────────────────┐
│   yield 各类事件     │  ChatMessageStreamDelta
│                     │  ToolCall / ToolOutput
│                     │  ActionStep / FinalAnswerStep
└─────────────────────┘
```

---

## 二、核心实现

### 2.1 _run_stream 方法详解

**源码位置**: `agents.py:540-611`

`_run_stream` 是整个流式执行的主控制器，采用 Python Generator 模式实现：

```python
def _run_stream(
    self, task: str, max_steps: int, images: list["PIL.Image.Image"] | None = None
) -> Generator[ActionStep | PlanningStep | FinalAnswerStep | ChatMessageStreamDelta]:
    self.step_number = 1
    returned_final_answer = False
    while not returned_final_answer and self.step_number <= max_steps:
        if self.interrupt_switch:  # 中断检查
            raise AgentError("Agent interrupted.", self.logger)

        # 1. 规划步骤 (如果配置了 planning_interval)
        if self.planning_interval is not None and (...) :
            for element in self._generate_planning_step(task, ...):
                yield element  # 直接透传规划步骤的流式输出
            ...

        # 2. 执行动作步骤
        action_step = ActionStep(step_number=self.step_number, ...)
        try:
            for output in self._step_stream(action_step):
                yield output  # 透传每一步的流式输出

                if isinstance(output, ActionOutput) and output.is_final_answer:
                    final_answer = output.output
                    returned_final_answer = True
                    ...
        except AgentGenerationError as e:
            raise e  # 生成错误直接抛出
        except AgentError as e:
            action_step.error = e  # 其他错误记录到步骤
        finally:
            self._finalize_step(action_step)
            self.memory.steps.append(action_step)
            yield action_step  # 最终 yield 完整的 ActionStep
            self.step_number += 1
```

**关键设计点**:

1. **双重 yield 模式**
   - 内部透传: `yield element` 直接转发子生成器的输出
   - 最终产出: `yield action_step` 产出完整的步骤对象

2. **中断检查点**
   - 每步开始前检查 `self.interrupt_switch`
   - 中断时抛出 `AgentError` 终止执行

3. **异常处理策略**
   - `AgentGenerationError`: 实现错误，直接抛出
   - `AgentError`: 模型错误，记录并继续

### 2.2 _step_stream 方法实现

`_step_stream` 是抽象方法，由 `ToolCallingAgent` 和 `CodeAgent` 分别实现。

#### ToolCallingAgent._step_stream

**源码位置**: `agents.py:1276-1359`

```python
def _step_stream(self, memory_step: ActionStep):
    memory_messages = self.write_memory_to_messages()
    input_messages = memory_messages.copy()
    memory_step.model_input_messages = input_messages

    try:
        # 流式生成判断
        if self.stream_outputs and hasattr(self.model, "generate_stream"):
            output_stream = self.model.generate_stream(
                input_messages,
                stop_sequences=["Observation:", "Calling tools:"],
                tools_to_call_from=self.tools_and_managed_agents,
            )

            chat_message_stream_deltas: list[ChatMessageStreamDelta] = []
            with Live("", console=self.logger.console, vertical_overflow="visible") as live:
                for event in output_stream:
                    chat_message_stream_deltas.append(event)
                    # 实时更新 Rich Live 显示
                    live.update(
                        Markdown(agglomerate_stream_deltas(chat_message_stream_deltas).render_as_markdown())
                    )
                    yield event  # 透传流式事件
            
            # 合并所有 delta 得到完整消息
            chat_message = agglomerate_stream_deltas(chat_message_stream_deltas)
        else:
            # 非流式模式
            chat_message = self.model.generate(...)
            ...

        # 记录模型输出
        memory_step.model_output_message = chat_message
        memory_step.model_output = chat_message.content
        memory_step.token_usage = chat_message.token_usage

        # 解析 tool calls
        if chat_message.tool_calls is None or len(chat_message.tool_calls) == 0:
            chat_message = self.model.parse_tool_calls(chat_message)

        # 执行 tool calls
        for output in self.process_tool_calls(chat_message, memory_step):
            yield output  # 透传 ToolCall / ToolOutput
            ...

        yield ActionOutput(output=final_answer, is_final_answer=got_final_answer)
```

#### CodeAgent._step_stream

**源码位置**: `agents.py:1639-1765`

```python
def _step_stream(self, memory_step: ActionStep):
    memory_messages = self.write_memory_to_messages()
    input_messages = memory_messages.copy()
    memory_step.model_input_messages = input_messages

    # 流式生成
    if self.stream_outputs:
        output_stream = self.model.generate_stream(input_messages, stop_sequences=...)
        chat_message_stream_deltas: list[ChatMessageStreamDelta] = []
        with Live(...) as live:
            for event in output_stream:
                chat_message_stream_deltas.append(event)
                live.update(Markdown(...))
                yield event
        chat_message = agglomerate_stream_deltas(chat_message_stream_deltas)
        output_text = chat_message.content
    else:
        chat_message = self.model.generate(...)
        output_text = chat_message.content

    # 解析代码块
    code_action = parse_code_blobs(output_text, self.code_block_tags)
    code_action = fix_final_answer_code(code_action)
    memory_step.code_action = code_action

    # 创建 ToolCall 并 yield
    tool_call = ToolCall(
        name="python_interpreter",
        arguments=code_action,
        id=f"call_{len(self.memory.steps)}",
    )
    yield tool_call
    memory_step.tool_calls = [tool_call]

    # 执行代码
    code_output = self.python_executor(code_action)
    observation = "Execution logs:\n" + code_output.logs
    memory_step.observations = observation
    memory_step.action_output = code_output.output

    yield ActionOutput(output=code_output.output, is_final_answer=code_output.is_final_answer)
```

**两种 Agent 的流式差异**:

| 阶段 | ToolCallingAgent | CodeAgent |
|------|-----------------|-----------|
| 输出格式 | JSON Tool Call | Python 代码 |
| 解析方式 | parse_tool_calls | parse_code_blobs |
| 执行对象 | 多个 Tools | python_interpreter |
| 并行性 | 支持多 tool 并行 | 单代码块执行 |

### 2.3 流式消息类型系统

**StreamEvent 类型定义**: `agents.py:256-265`

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

#### ChatMessageStreamDelta 详解

**源码位置**: `models.py:213-217`

```python
@dataclass
class ChatMessageStreamDelta:
    content: str | None = None           # 文本内容片段
    tool_calls: list[ChatMessageToolCallStreamDelta] | None = None  # 工具调用片段
    token_usage: TokenUsage | None = None  # Token 使用量
```

**ChatMessageToolCallStreamDelta**: `models.py:203-210`

```python
@dataclass
class ChatMessageToolCallStreamDelta:
    index: int | None = None             # 工具调用索引
    id: str | None = None                # 调用 ID
    type: str | None = None              # 类型
    function: ChatMessageToolCallFunction | None = None  # 函数信息
```

#### agglomerate_stream_deltas 函数

**源码位置**: `models.py:220-279`

```python
def agglomerate_stream_deltas(
    stream_deltas: list[ChatMessageStreamDelta], 
    role: MessageRole = MessageRole.ASSISTANT
) -> ChatMessage:
    """
    将多个流式 delta 合并为单个完整的 ChatMessage
    """
    accumulated_tool_calls: dict[int, ChatMessageToolCallStreamDelta] = {}
    accumulated_content = ""
    total_input_tokens = 0
    total_output_tokens = 0

    for stream_delta in stream_deltas:
        # 累积 token 使用量
        if stream_delta.token_usage:
            total_input_tokens += stream_delta.token_usage.input_tokens
            total_output_tokens += stream_delta.token_usage.output_tokens
        
        # 累积文本内容
        if stream_delta.content:
            accumulated_content += stream_delta.content
        
        # 累积工具调用
        if stream_delta.tool_calls:
            for tool_call_delta in stream_delta.tool_calls:
                index = tool_call_delta.index
                if index not in accumulated_tool_calls:
                    accumulated_tool_calls[index] = ChatMessageToolCallStreamDelta(
                        id=tool_call_delta.id,
                        type=tool_call_delta.type,
                        function=ChatMessageToolCallFunction(name="", arguments=""),
                    )
                # 增量更新属性
                tool_call = accumulated_tool_calls[index]
                if tool_call_delta.id:
                    tool_call.id = tool_call_delta.id
                if tool_call_delta.function:
                    if tool_call_delta.function.name:
                        tool_call.function.name = tool_call_delta.function.name
                    if tool_call_delta.function.arguments:
                        tool_call.function.arguments += tool_call_delta.function.arguments

    # 构建完整的 ChatMessage
    return ChatMessage(
        role=role,
        content=accumulated_content,
        tool_calls=[...],  # 转换后的工具调用列表
        token_usage=TokenUsage(
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
        ),
    )
```

**合并算法要点**:

1. **内容累积**: 简单字符串拼接 `accumulated_content += content`
2. **工具调用合并**: 按 index 分组，增量更新 name 和 arguments
3. **Token 统计**: 累加各 delta 的 token 使用量
4. **结果转换**: 将 `ChatMessageToolCallStreamDelta` 转为 `ChatMessageToolCall`

---

## 三、Gradio流式展示

### 3.1 GradioUI 架构

**源码位置**: `gradio_ui.py:279-464`

GradioUI 通过 `_stream_response` 方法消费 Agent 的流式输出：

```python
class GradioUI:
    def __init__(self, agent: MultiStepAgent, ...):
        self.agent = agent
        ...

    def _stream_response(self, message: str | dict, history: list[dict]) -> Generator:
        """Stream agent responses for ChatInterface."""
        import gradio as gr

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
                text = text.replace("<", r"\<").replace(">", r"\>")  # 转义 HTML
                msg = gr.ChatMessage(role="assistant", content=text)
                
                if streaming_msg_idx is None:
                    streaming_msg_idx = len(all_messages)
                    all_messages.append(msg)
                else:
                    all_messages[streaming_msg_idx] = msg
                yield all_messages
```

### 3.2 消息处理流程

**pull_messages_from_step**: `gradio_ui.py:226-245`

```python
def pull_messages_from_step(step_log: ActionStep | PlanningStep | FinalAnswerStep, 
                             skip_model_outputs: bool = False):
    """从 Agent 步骤提取 Gradio ChatMessage 对象"""
    if isinstance(step_log, ActionStep):
        yield from _process_action_step(step_log, skip_model_outputs)
    elif isinstance(step_log, PlanningStep):
        yield from _process_planning_step(step_log, skip_model_outputs)
    elif isinstance(step_log, FinalAnswerStep):
        yield from _process_final_answer_step(step_log)
```

**_process_action_step**: `gradio_ui.py:80-163`

```python
def _process_action_step(step_log: ActionStep, skip_model_outputs: bool = False) -> Generator:
    import gradio as gr

    # 1. 输出步骤编号
    step_number = f"Step {step_log.step_number}"
    if not skip_model_outputs:
        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT, 
            content=f"**{step_number}**", 
            metadata={"status": "done"}
        )

    # 2. 输出思考过程
    if not skip_model_outputs and getattr(step_log, "model_output", ""):
        model_output = _clean_model_output(step_log.model_output)
        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT, 
            content=model_output, 
            metadata={"status": "done"}
        )

    # 3. 输出工具调用 (代码块)
    if getattr(step_log, "tool_calls", []):
        first_tool_call = step_log.tool_calls[0]
        used_code = first_tool_call.name == "python_interpreter"

        args = first_tool_call.arguments
        content = str(args.get("answer", str(args)))
        if used_code:
            content = _format_code_content(content)  # 格式化为 Python 代码块

        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            metadata={
                "title": f"️ Used tool {first_tool_call.name}",
                "status": "done",
            },
        )

    # 4. 输出执行日志
    if getattr(step_log, "observations", ""):
        log_content = step_log.observations.strip()
        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT,
            content=f"```bash\n{log_content}\n",
            metadata={"title": " Execution Logs", "status": "done"},
        )

    # 5. 输出图片
    if getattr(step_log, "observations_images", []):
        for image in step_log.observations_images:
            path_image = AgentImage(image).to_string()
            yield gr.ChatMessage(
                role=MessageRole.ASSISTANT,
                content={"path": path_image, "mime_type": f"image/{path_image.split('.')[-1]}"},
                metadata={"title": "️ Output Image", "status": "done"},
            )

    # 6. 输出错误
    if getattr(step_log, "error", None):
        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT, 
            content=str(step_log.error), 
            metadata={"title": " Error", "status": "done"}
        )

    # 7. 输出步骤脚注
    yield gr.ChatMessage(
        role=MessageRole.ASSISTANT,
        content=get_step_footnote_content(step_log, step_number),
        metadata={"status": "done"},
    )
    yield gr.ChatMessage(role=MessageRole.ASSISTANT, content="-----", metadata={"status": "done"})
```

### 3.3 展示逻辑对比

| 展示元素 | 流式模式 | 非流式模式 |
|---------|---------|-----------|
| 思考过程 | 实时逐字显示 | 完成后一次性显示 |
| 代码块 | 实时显示 | 完成后显示 |
| 工具调用 | 与思考过程合并 | 单独展示 |
| 执行日志 | 工具执行后显示 | 同上 |
| 步骤分隔 | 固定格式 | 同上 |

---

## 四、中断处理

### 4.1 中断机制设计

**中断标志**: `agents.py:352`

```python
def __init__(self, ...):
    ...
    self.stream_outputs = False  # 流式输出开关
```

**中断检查点**: `agents.py:546-547`

```python
def _run_stream(self, task: str, max_steps: int, ...):
    while not returned_final_answer and self.step_number <= max_steps:
        if self.interrupt_switch:  # 检查中断标志
            raise AgentError("Agent interrupted.", self.logger)
        ...
```

**中断方法**: `agents.py:754-756`

```python
def interrupt(self):
    """Interrupts the agent execution."""
    self.interrupt_switch = True
```

### 4.2 中断触发时机

中断检查发生在**每步开始前**，这意味着：

1. **可中断点**: 步骤边界处
2. **不可中断点**: 模型生成过程中、工具执行过程中
3. **中断延迟**: 最多一个步骤的执行时间

```
执行流程中的中断检查点:

Step 1:
  ├─ ▶️ 检查 interrupt_switch
  ├─ 模型生成 (不可中断)
  ├─ 工具执行 (不可中断)
  └─ 完成
Step 2:
  ├─ ▶️ 检查 interrupt_switch  ← 中断发生在这里
  ├─ 模型生成
  ...
```

### 4.3 与 Gradio 的集成

GradioUI 可以通过外部按钮调用 `agent.interrupt()`：

```python
# 典型使用模式
agent = CodeAgent(tools=[...], model=...)

# Gradio 界面中
interrupt_btn.click(lambda: agent.interrupt())

# 流式执行
for event in agent.run(task, stream=True):
    # 如果点击了中断按钮
    # 下轮循环将抛出 AgentError
    process(event)
```

### 4.4 中断后状态

中断后 Agent 的状态：

```python
try:
    for event in agent.run(task, stream=True):
        ...
except AgentError as e:
    # 中断异常
    # agent.memory.steps 包含已完成的步骤
    # agent.step_number 为中断时的步骤号
    # 可以重新调用 run 继续执行 (如果 reset=False)
```

---

## 五、扩展为 Web 服务

smolagents 的 Generator 模式虽然简洁，但在 Web 场景下需要转换为标准流式协议。以下是两种常见的扩展方案。

### 5.1 转换为 SSE (Server-Sent Events)

**架构设计**:

```
┌─────────┐     ┌─────────────┐     ┌─────────────────┐
│  用户   │────▶│  Web 前端   │────▶│ EventSource API │
└─────────┘     └─────────────┘     └────────┬────────┘
                                             │
                              ┌──────────────┴──────────────┐
                              ▼                             ▼
                    ┌─────────────────┐          ┌─────────────────┐
                    │    onmessage    │          │    onerror      │
                    └─────────────────┘          └─────────────────┘
                                             │
                    ┌────────────────────────▼────────────────────────┐
                    │              FastAPI Backend                     │
                    │  ┌───────────────────────────────────────────┐  │
                    │  │  StreamingResponse                        │  │
                    │  │  media_type="text/event-stream"           │  │
                    │  └───────────────────┬───────────────────────┘  │
                    │                      │                          │
                    │  ┌───────────────────▼───────────────────────┐  │
                    │  │  for chunk in agent.run_stream(task):     │  │
                    │  │      yield f"data: {chunk}\n\n"            │  │
                    │  └───────────────────────────────────────────┘  │
                    └─────────────────────────────────────────────────┘
```

**FastAPI 集成代码**:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from smolagents import CodeAgent

app = FastAPI()
agent = CodeAgent(model=model, tools=tools)

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """将 smolagents Generator 转换为 SSE"""
    
    async def event_generator():
        for event in agent.run_stream(request.message):
            # 将 Python 对象序列化为 JSON
            data = json.dumps({
                "type": event.__class__.__name__,
                "content": str(event)
            })
            yield f"data: {data}\n\n"
        
        # 发送结束标记
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**前端集成代码**:

```javascript
const eventSource = new EventSource('/chat/stream', {
  method: 'POST',
  body: JSON.stringify({ message: userInput })
});

eventSource.onmessage = (event) => {
  if (event.data === '[DONE]') {
    eventSource.close();
    return;
  }
  
  const data = JSON.parse(event.data);
  appendToChat(data.content);
};

eventSource.onerror = (error) => {
  console.error('Stream error:', error);
  eventSource.close();
};
```

### 5.2 转换为 WebSocket

**适用场景**:
- 需要双向通信
- 需要实时中断控制
- 需要心跳保活

**FastAPI WebSocket 代码**:

```python
from fastapi import WebSocket

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # 接收用户输入
        data = await websocket.receive_json()
        task = data['message']
        
        # 流式执行
        for event in agent.run_stream(task):
            await websocket.send_json({
                "type": event.__class__.__name__,
                "content": str(event)
            })
            
            # 检查是否收到中断信号
            try:
                msg = await asyncio.wait_for(
                    websocket.receive(),
                    timeout=0.001
                )
                if msg.get('action') == 'stop':
                    break
            except asyncio.TimeoutError:
                pass
        
        await websocket.send_json({"type": "done"})
        
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
```

### 5.3 方案选择建议

| 场景 | 推荐方案 | 理由 |
|------|---------|------|
| 单向数据流 | SSE | 实现简单，自动重连 |
| 需要双向通信 | WebSocket | 支持中断、心跳 |
| 简单原型 | Generator + Gradio | 零网络代码 |
| 生产环境 | SSE/WebSocket + 队列 | 支持多用户、可扩展 |

---

## 六、对我们项目的启示

### 6.1 设计借鉴

**1. Generator 模式简洁高效**

smolagents 的流式设计非常简洁，不需要复杂的协议封装。对于我们的 AI数据分析系统，可以考虑：

```python
# 借鉴 smolagents 的 yield 模式
class OurAgent:
    def run_stream(self, query: str):
        for step in self.planner.plan(query):
            yield PlanningStep(...)
            
        for step_num in range(self.max_steps):
            # 流式生成
            for delta in self.model.generate_stream(messages):
                yield ChatMessageStreamDelta(content=delta)
            
            # 执行工具
            result = self.executor.execute(action)
            yield ToolOutput(result)
            
            if result.is_final:
                yield FinalAnswerStep(result)
                break
```

**2. 统一的事件类型系统**

参考 `StreamEvent` 类型定义，设计我们的事件体系：

```python
AnalysisEvent = Union[
    ThoughtDelta,        # 思考过程片段
    SQLGenerated,        # SQL 生成结果
    QueryExecuting,      # 执行开始
    QueryResult,         # 查询结果
    VisualizationCode,   # 可视化代码
    ChartRendered,       # 图表渲染
    FinalReport,         # 最终报告
]
```

**3. 增量累积与完整对象分离**

学习 `ChatMessageStreamDelta` 和 `agglomerate_stream_deltas` 的设计：

```python
@dataclass
class SQLStreamDelta:
    sql_fragment: str | None = None

@dataclass
class SQLResult:
    sql: str
    is_valid: bool
    error: str | None

def accumulate_sql(deltas: list[SQLStreamDelta]) -> SQLResult:
    full_sql = "".join(d.sql_fragment for d in deltas if d.sql_fragment)
    # 验证 SQL 语法
    return SQLResult(sql=full_sql, is_valid=validate(full_sql), error=None)
```

### 6.2 实现建议

**1. 流式生成器结构**

```python
async def analyze_stream(self, question: str) -> AsyncGenerator[AnalysisEvent, None]:
    """流式数据分析主流程"""
    
    # 阶段1: 意图理解
    yield AnalysisStatus("正在理解问题...")
    for delta in self.nlu_model.stream_generate(question):
        yield ThoughtDelta(delta)
    
    # 阶段2: SQL 生成
    yield AnalysisStatus("正在生成 SQL...")
    sql_deltas = []
    for delta in self.sql_model.stream_generate(prompt):
        sql_deltas.append(delta)
        yield SQLStreamDelta(delta)
    sql = accumulate_sql(sql_deltas).sql
    
    # 阶段3: 执行查询
    yield AnalysisStatus("正在执行查询...")
    result = await self.db.execute(sql)
    yield QueryResult(result)
    
    # 阶段4: 生成可视化
    yield AnalysisStatus("正在生成图表...")
    chart_code = self.viz_generator.generate(result)
    yield VisualizationCode(chart_code)
    
    # 阶段5: 最终报告
    yield FinalReport(self.report_generator.generate(question, result, chart_code))
```

**2. 前端适配层**

如果使用 Web 前端，需要封装适配层：

```python
# FastAPI 适配
@app.post("/api/analyze/stream")
async def analyze_stream_endpoint(request: QueryRequest):
    agent = get_agent()
    
    async def event_generator():
        async for event in agent.analyze_stream(request.question):
            yield f"data: {json.dumps(event.dict())}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**3. 中断处理**

参考 smolagents 的简单中断机制：

```python
class AnalysisAgent:
    def __init__(self):
        self._interrupt_flag = False
    
    def interrupt(self):
        self._interrupt_flag = True
    
    async def analyze_stream(self, question: str):
        for step in self.steps:
            if self._interrupt_flag:
                yield AnalysisInterrupted()
                return
            
            async for event in self.execute_step(step):
                yield event
```

### 6.3 需要改进的地方

**1. 更细粒度的中断**

smolagents 的中断只能发生在步骤边界。我们的系统可以考虑：

```python
# 使用 asyncio.Event 实现更精细控制
async def generate_with_cancellation(model, prompt, cancel_event):
    for token in model.stream_generate(prompt):
        if cancel_event.is_set():
            raise CancelledError()
        yield token
```

**2. 错误恢复机制**

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def execute_with_retry(self, sql: str):
    try:
        return await self.db.execute(sql)
    except DBError as e:
        yield ErrorEvent(str(e), recoverable=True)
        raise
```

**3. 进度追踪**

```python
@dataclass
class ProgressEvent:
    phase: str           # 当前阶段
    total_phases: int    # 总阶段数
    step_in_phase: int   # 阶段内步骤
    total_steps: int     # 阶段总步骤
    
    @property
    def percentage(self) -> float:
        return (self.phase / self.total_phases * 100 + 
                self.step_in_phase / self.total_steps * 100 / self.total_phases)
```

---

## 附录

### 相关文档

- [[01-smolagents-Agent架构深度分析]]
- [[47-smolagents流输出边界情况深度分析]]

### 源码参考

| 文件 | 关键函数/类 | 行号 |
|------|-----------|------|
| agents.py | `_run_stream` | 540-611 |
| agents.py | `ToolCallingAgent._step_stream` | 1276-1359 |
| agents.py | `CodeAgent._step_stream` | 1639-1765 |
| agents.py | `interrupt` | 754-756 |
| models.py | `ChatMessageStreamDelta` | 213-217 |
| models.py | `agglomerate_stream_deltas` | 220-279 |
| gradio_ui.py | `GradioUI._stream_response` | 378-420 |
| gradio_ui.py | `pull_messages_from_step` | 226-245 |
| gradio_ui.py | `_process_action_step` | 80-163 |

---

*文档更新时间: 2026-02-06*
