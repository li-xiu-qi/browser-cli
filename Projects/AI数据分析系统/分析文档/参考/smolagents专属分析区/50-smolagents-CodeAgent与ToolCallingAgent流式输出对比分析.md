# smolagents CodeAgent 与 ToolCallingAgent 流式输出对比分析

> 项目: smolagents  
> 分析日期: 2026-02-08  
> 源码位置: src/smolagents/agents.py

---

## 一、流式输出架构总览

### 1.1 两种 Agent 的流式输出位置

在 smolagents 中，流式输出主要通过 `_step_stream` 方法实现，该方法在 `ToolCallingAgent` 和 `CodeAgent` 中有完全不同的实现。

```
Agent.run_stream()
    ├── yield PlanningStep
    ├── yield ActionStep  ← 步骤级别事件
    │       └── _step_stream()  ← 流式输出核心
    │               ├── yield ChatMessageStreamDelta  ← Token 级别流式
    │               ├── yield ToolCall
    │               ├── yield ToolOutput
    │               └── yield ActionOutput
    └── yield FinalAnswerStep
```

### 1.2 _step_stream 方法签名对比

| 特性 | ToolCallingAgent | CodeAgent |
|------|------------------|-----------|
| **方法位置** | agents.py:1276 | agents.py:1639 |
| **返回值** | Generator[ChatMessageStreamDelta \| ToolCall \| ToolOutput \| ActionOutput] | 相同 |
| **核心职责** | 处理工具调用循环 | 处理代码生成与执行 |

---

## 二、ToolCallingAgent 流式输出详解

### 2.1 流式输出流程

```
_step_stream 开始
    │
    ▼
生成模型输出（流式）
    │
    ├── yield ChatMessageStreamDelta  ← 逐 token 输出思考过程
    │
    ▼
解析工具调用
    │
    ├── yield ToolCall  ← 多个工具调用
    │
    ▼
执行工具
    │
    ├── yield ToolOutput  ← 每个工具的执行结果
    │
    ▼
yield ActionOutput  ← 步骤最终结果
```

### 2.2 关键代码分析

**源码位置**: agents.py:1276-1359

```python
def _step_stream(self, memory_step: ActionStep):
    # 1. 准备输入消息
    memory_messages = self.write_memory_to_messages()
    input_messages = memory_messages.copy()
    memory_step.model_input_messages = input_messages

    # 2. 流式生成模型输出
    if self.stream_outputs and hasattr(self.model, "generate_stream"):
        output_stream = self.model.generate_stream(
            input_messages,
            stop_sequences=["Observation:", "Calling tools:"],
            tools_to_call_from=self.tools_and_managed_agents,
        )
        
        # 逐 token 输出
        chat_message_stream_deltas = []
        for event in output_stream:
            chat_message_stream_deltas.append(event)
            yield event  # ← 流式输出每个 token
        
        chat_message = agglomerate_stream_deltas(chat_message_stream_deltas)
    else:
        # 非流式模式
        chat_message = self.model.generate(...)

    # 3. 解析工具调用
    memory_step.model_output_message = chat_message
    memory_step.model_output = chat_message.content
    
    # 4. 处理工具调用（循环）
    for output in self.process_tool_calls(chat_message, memory_step):
        yield output  # ← 输出 ToolCall 和 ToolOutput
        if isinstance(output, ToolOutput) and output.is_final_answer:
            final_answer = output.output
            got_final_answer = True

    # 5. 输出最终结果
    yield ActionOutput(output=final_answer, is_final_answer=got_final_answer)
```

### 2.3 流式事件类型

| 事件类型 | 触发时机 | 数据内容 | 前端展示建议 |
|----------|----------|----------|--------------|
| ChatMessageStreamDelta | 每生成一个 token | role, content | 打字机效果，实时显示思考过程 |
| ToolCall | 解析到工具调用 | name, arguments | 工具卡片，显示调用参数 |
| ToolOutput | 工具执行完成 | output, is_final_answer | 结果面板，代码块或文本 |
| ActionOutput | 步骤结束 | output, is_final_answer | 步骤总结，是否最终答案 |

### 2.4 支持多工具调用

ToolCallingAgent 的特殊之处在于支持**一次生成多个工具调用**：

```python
# 模型可能生成多个工具调用
chat_message.tool_calls = [
    ToolCall(name="web_search", arguments={"query": "..."}),
    ToolCall(name="calculator", arguments={"expression": "..."}),
]

# 逐个执行并流式输出
for tool_call in chat_message.tool_calls:
    yield tool_call  # ← 输出工具调用
    result = execute_tool(tool_call)
    yield ToolOutput(output=result)  # ← 输出执行结果
```

---

## 三、CodeAgent 流式输出详解

### 3.1 流式输出流程

```
_step_stream 开始
    │
    ▼
生成模型输出（流式）
    │
    ├── yield ChatMessageStreamDelta  ← 逐 token 输出代码
    │
    ▼
解析代码块
    │
    ├── yield ToolCall  ← 单个 python_interpreter 调用
    │
    ▼
执行代码
    │
    ├── 无流式输出，同步执行
    │
    ▼
yield ActionOutput  ← 执行结果
```

### 3.2 关键代码分析

**源码位置**: agents.py:1639-1765

```python
def _step_stream(self, memory_step: ActionStep):
    # 1. 准备输入消息
    memory_messages = self.write_memory_to_messages()
    input_messages = memory_messages.copy()
    memory_step.model_input_messages = input_messages

    # 2. 流式生成代码
    stop_sequences = ["Observation:", "Calling tools:"]
    if self.code_block_tags[1] not in self.code_block_tags[0]:
        stop_sequences.append(self.code_block_tags[1])  # 添加代码结束标记

    if self.stream_outputs:
        output_stream = self.model.generate_stream(
            input_messages,
            stop_sequences=stop_sequences,
        )
        
        # 逐 token 输出代码
        chat_message_stream_deltas = []
        for event in output_stream:
            chat_message_stream_deltas.append(event)
            yield event  # ← 流式输出代码
        
        chat_message = agglomerate_stream_deltas(chat_message_stream_deltas)
        output_text = chat_message.content
    else:
        chat_message = self.model.generate(...)
        output_text = chat_message.content

    # 3. 自动补全代码结束标记
    if output_text and not output_text.strip().endswith(self.code_block_tags[1]):
        output_text += self.code_block_tags[1]

    memory_step.model_output = output_text

    # 4. 解析代码块
    code_action = parse_code_blobs(output_text, self.code_block_tags)
    code_action = fix_final_answer_code(code_action)
    memory_step.code_action = code_action

    # 5. 创建单个工具调用
    tool_call = ToolCall(
        name="python_interpreter",
        arguments=code_action,
        id=f"call_{len(self.memory.steps)}",
    )
    yield tool_call  # ← 输出代码执行请求
    memory_step.tool_calls = [tool_call]

    # 6. 执行代码（同步，无流式）
    code_output = self.python_executor(code_action)
    
    observation = "Execution logs:\n" + code_output.logs
    observation += "Last output from code snippet:\n" + str(code_output.output)
    memory_step.observations = observation

    # 7. 输出结果
    yield ActionOutput(
        output=code_output.output, 
        is_final_answer=code_output.is_final_answer
    )
```

### 3.3 与 ToolCallingAgent 的关键差异

| 差异点 | ToolCallingAgent | CodeAgent |
|--------|------------------|-----------|
| **生成内容** | JSON 格式工具调用 | Python 代码块 |
| **工具调用数量** | 支持多个 | 仅一个 python_interpreter |
| **代码执行** | 工具内部实现 | 统一的 python_executor |
| **代码结束标记** | 无 | 自动补全 closing tag |
| **结构化输出** | 可选 | 支持内部结构化输出 |

### 3.4 代码块解析机制

CodeAgent 需要特殊处理代码块的提取：

```python
# 从模型输出中提取代码
code_action = parse_code_blobs(output_text, self.code_block_tags)

# 处理 final_answer 特殊代码
code_action = fix_final_answer_code(code_action)

# 示例：模型输出
generated_output = """
让我计算这个数据框的统计信息。
```python
import pandas as pd
result = df.describe()
print(result)
```
"""

# 提取后的代码
code_action = """
import pandas as pd
result = df.describe()
print(result)
"""
```

---

## 四、流式输出对比总结

### 4.1 事件序列对比

**ToolCallingAgent 典型事件序列**：
```
ChatMessageStreamDelta(role="assistant", content="让我")
ChatMessageStreamDelta(role="assistant", content="搜索")
ChatMessageStreamDelta(role="assistant", content="相关")
ChatMessageStreamDelta(role="assistant", content="信息")
ToolCall(name="web_search", arguments={"query": "..."})
ToolOutput(output="搜索结果...", is_final_answer=False)
ToolCall(name="visit_webpage", arguments={"url": "..."})
ToolOutput(output="网页内容...", is_final_answer=False)
ActionOutput(output="根据搜索结果...", is_final_answer=True)
```

**CodeAgent 典型事件序列**：
```
ChatMessageStreamDelta(role="assistant", content="```python")
ChatMessageStreamDelta(role="assistant", content="\nimport")
ChatMessageStreamDelta(role="assistant", content=" pandas")
ChatMessageStreamDelta(role="assistant", content=" as")
ChatMessageStreamDelta(role="assistant", content=" pd")
ChatMessageStreamDelta(role="assistant", content="\n...")
ChatMessageStreamDelta(role="assistant", content="\n```")
ToolCall(name="python_interpreter", arguments="import pandas...")
# 无 ToolOutput，直接到结果
ActionOutput(output="   A  B  C\n0  1  2  3", is_final_answer=False)
```

### 4.2 流式粒度对比

| 粒度 | ToolCallingAgent | CodeAgent |
|------|------------------|-----------|
| **Token 级别** | 思考过程流式输出 | 代码流式输出 |
| **工具调用级别** | 多个工具依次输出 | 仅一个代码执行 |
| **执行过程** | 每个工具执行后立即输出 | 代码执行完成后一次性输出 |
| **Observation** | 每个工具一个 | 仅一个，包含 logs 和 output |

### 4.3 前端展示建议对比

**ToolCallingAgent 前端设计**：
```
[思考过程] 流式显示，灰色文字
[工具调用1] 卡片展示，可展开参数
[结果1] 面板展示
[工具调用2] 卡片展示
[结果2] 面板展示
[总结] 最终答案
```

**CodeAgent 前端设计**：
```
[代码生成] 代码块流式显示，语法高亮
[执行按钮] 或自动执行
[执行日志] 折叠面板
[执行结果] 表格或文本展示
```

---

## 五、特殊场景处理

### 5.1 ToolCallingAgent 多工具并发

当模型一次生成多个工具调用时，需要依次执行：

```python
# 模型输出多个工具调用
for output in self.process_tool_calls(chat_message, memory_step):
    yield output  # 依次 yield 每个 ToolCall 和 ToolOutput
```

**前端处理**：
- 显示多个工具调用卡片
- 按顺序展示执行结果
- 如果有最终答案工具，标记为最终结果

### 5.2 CodeAgent 代码执行错误

代码执行错误不会生成 ToolOutput，而是直接抛出异常：

```python
try:
    code_output = self.python_executor(code_action)
except Exception as e:
    # 记录错误日志
    error_msg = str(e)
    raise AgentExecutionError(error_msg, self.logger)
```

**前端处理**：
- 捕获错误事件
- 显示错误信息和堆栈
- 提供重试按钮

### 5.3 流式中断处理

两种 Agent 都支持流式中断：

```python
# 检查中断标志
if self.interrupt_switch:
    raise AgentError("Agent interrupted.", self.logger)
```

**前端实现**：
- 提供停止按钮
- 调用 agent.interrupt()
- 优雅处理 Generator 终止

---

## 六、实现建议

### 6.1 统一事件处理器

```python
class StreamingEventHandler:
    def handle_event(self, event):
        if isinstance(event, ChatMessageStreamDelta):
            self.handle_stream_delta(event)
        elif isinstance(event, ToolCall):
            self.handle_tool_call(event)
        elif isinstance(event, ToolOutput):
            self.handle_tool_output(event)
        elif isinstance(event, ActionOutput):
            self.handle_action_output(event)

    def handle_stream_delta(self, event):
        # ToolCallingAgent: 思考过程
        # CodeAgent: 代码生成
        if self.agent_type == "code":
            self.render_code_stream(event.content)
        else:
            self.render_thought_stream(event.content)
```

### 6.2 代码高亮优化

CodeAgent 的流式代码需要特殊处理语法高亮：

```python
# 累积代码片段
code_buffer = ""
for event in stream:
    code_buffer += event.content
    # 定期更新语法高亮
    if should_update_highlight(code_buffer):
        update_code_editor(code_buffer)
```

### 6.3 性能优化

| 优化点 | ToolCallingAgent | CodeAgent |
|--------|------------------|-----------|
| **Token 节流** | 限制思考长度 | 限制代码长度 |
| **图片懒加载** | 工具返回图片 | 代码生成图片 |
| **代码折叠** | 不适用 | 长代码折叠 |
| **虚拟滚动** | 多工具场景 | 长日志场景 |

---

## 七、总结

### 核心差异

| 维度 | ToolCallingAgent | CodeAgent |
|------|------------------|-----------|
| **流式内容** | 思考过程 | 代码生成 |
| **工具数量** | 多个 | 一个 |
| **执行透明度** | 每个工具独立 | 代码黑盒执行 |
| **适用场景** | 多步骤推理 | 数据分析、计算 |
| **前端复杂度** | 中等 | 较高（需要代码编辑器） |

### 选型建议

- **选择 ToolCallingAgent**：需要多个工具协作、多步骤推理、外部 API 调用
- **选择 CodeAgent**：需要复杂计算、数据处理、灵活编程

---

**相关文档**：
- [[25-smolagents-CodeAgent与ToolCallingAgent深度对比]]
- [[03-smolagents-流式输出机制深度分析]]
- [[47-smolagents流输出边界情况深度分析]]
