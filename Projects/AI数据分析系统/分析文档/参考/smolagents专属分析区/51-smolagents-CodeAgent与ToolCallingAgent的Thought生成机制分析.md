# smolagents CodeAgent 与 ToolCallingAgent 的 Thought 生成机制分析

> 项目: smolagents  
> 分析日期: 2026-02-08  
> 源码位置: src/smolagents/agents.py, prompts/code_agent.yaml, prompts/toolcalling_agent.yaml

---

## 核心结论

| Agent 类型 | Thought 来源 | Prompt 强制要求 | 适用模型 |
|-----------|-------------|----------------|---------|
| **CodeAgent** | `model_output` 中的 `Thought:` 部分 | **是**，Prompt 明确要求 | 所有模型 |
| **ToolCallingAgent** | `model_output` 中的自由文本 | **否**，依赖模型自行输出 | 所有模型 |

**关键洞察**：CodeAgent 通过 **Prompt 工程** 强制模型输出详细推理过程，而 ToolCallingAgent 的推理过程是可选的。这与是否使用"Thinking 模型"无关，标准模型同样适用。

---

## 一、Thought 的存储位置

### 1.1 ActionStep 中的 model_output

无论是 CodeAgent 还是 ToolCallingAgent，Thought 都存储在 `ActionStep.model_output` 字段中：

```python
# memory.py 第 57-58 行
@dataclass
class ActionStep(MemoryStep):
    model_output_message: ChatMessage | None = None  # 完整消息对象
    model_output: str | list[dict[str, Any]] | None = None  # 模型输出的文本内容
```

**存储时机**：

```python
# agents.py 第 1321-1322 行（ToolCallingAgent）
# agents.py 第 1698-1699 行（CodeAgent）
memory_step.model_output_message = chat_message
memory_step.model_output = chat_message.content  # Thought 在这里
```

### 1.2 如何访问 Thought

```python
# 遍历执行步骤获取 Thought
for step in agent.memory.steps:
    if isinstance(step, ActionStep) and step.model_output:
        print(f"步骤 {step.step_number} 的模型输出:")
        print(step.model_output)
        
        # CodeAgent: 可以提取 Thought 部分
        if "Thought:" in step.model_output:
            thought = step.model_output.split("Thought:")[1].split("Code:")[0]
            print(f"思考过程: {thought}")
```

---

## 二、CodeAgent 的 Thought 生成机制

### 2.1 Prompt 强制要求 Thought

**源码位置**: `prompts/code_agent.yaml` 第 4-10 行

```yaml
system_prompt: |-
  You are an expert assistant who can solve any task using code blobs.
  
  To solve the task, you must plan forward to proceed in a series of steps, 
  in a cycle of Thought, Code, and Observation sequences.

  At each step, in the 'Thought:' sequence, you should first explain your 
  reasoning towards solving the task and the tools that you want to use.
  Then in the Code sequence you should write the code in simple Python.
```

**关键指令**：
- `"in a cycle of Thought, Code, and Observation sequences"` — 明确定义三阶段循环
- `"in the 'Thought:' sequence, you should first explain your reasoning"` — 强制要求输出 Thought
- `"Then in the Code sequence"` — Thought 必须在 Code 之前

### 2.2 输出格式示例

**CodeAgent 的标准输出格式**：

```
Thought: I will proceed step by step and use the following tools: `document_qa` 
to find the oldest person in the document, then `image_generator` to generate an image.

Code:
```python
answer = document_qa(document=document, question="Who is the oldest person mentioned?")
print(answer)
```
```

**存储到 model_output**：

```python
model_output = """Thought: I will proceed step by step and use the following tools: `document_qa` 
to find the oldest person in the document, then `image_generator` to generate an image.

Code:
```python
answer = document_qa(document=document, question="Who is the oldest person mentioned?")
print(answer)
```"""
```

### 2.3 Thought 与 Code 的分离

在 CodeAgent 中，Thought 和 Code 是通过字符串解析分离的：

```python
# 从 model_output 中提取 Thought
if "Thought:" in step.model_output:
    parts = step.model_output.split("Code:")
    thought = parts[0].replace("Thought:", "").strip()
    code = parts[1].strip() if len(parts) > 1 else ""
```

---

## 三、ToolCallingAgent 的 Thought 生成机制

### 3.1 Prompt 不强制要求 Thought

**源码位置**: `prompts/toolcalling_agent.yaml` 第 1-27 行

```yaml
system_prompt: |-
  You are an expert assistant who can solve any task using tool calls.
  
  The tool call you write is an action: after the tool is executed, 
  you will get the result of the tool call as an "observation".
  This Action/Observation can repeat N times, you should take several steps when needed.

  To provide the final answer to the task, use an action blob with "name": "final_answer" tool.
```

**关键差异**：
- 没有明确要求 `"Thought:"` 部分
- 只要求 `"Action:"` 和 `"Observation:"` 循环
- 模型可以自由选择是否输出推理过程

### 3.2 输出格式示例

**ToolCallingAgent 的标准输出格式**：

```
Action:
{
  "name": "document_qa",
  "arguments": {"document": "document.pdf", "question": "Who is the oldest person mentioned?"}
}
```

**注意**：某些模型（如 GPT-4）可能会自行在 Action 前添加推理：

```
Let me search for the oldest person in the document first.  # ← 这是模型自由生成的

Action:
{
  "name": "document_qa",
  "arguments": {"document": "document.pdf", "question": "Who is the oldest person mentioned?"}
}
```

**这种自由生成的推理文本也会被存入 model_output**，但：
- 格式不固定
- 内容不可控
- 可能为空

### 3.3 对比总结

| 特性 | CodeAgent | ToolCallingAgent |
|------|-----------|------------------|
| **Prompt 要求** | 强制要求 `Thought:` | 不强制要求 |
| **输出格式** | 固定格式 `Thought: ... Code: ...` | 自由格式，可能只有 Action JSON |
| **Thought 可靠性** | 高，每步都有 | 低，依赖模型自行决定 |
| **Thought 完整性** | 完整，包含推理和工具选择 | 不确定，可能缺失 |

---

## 四、Thinking/Reasoning 模型的支持情况

### 4.1 当前支持状态

目前 smolagents **没有特殊处理**支持 reasoning/thinking 的模型：

| 模型类型 | 特殊字段 | smolagents 处理 | 结果 |
|---------|---------|----------------|------|
| DeepSeek-R1 | `reasoning_content` | 未处理 | **丢失** |
| Claude 3.7 thinking | `thinking` 块 | 未处理 | **丢失** |
| OpenAI o3/o4 | 内置 reasoning | 不支持 stop 参数 | 部分兼容 |
| Amazon Bedrock | `thinking` 块 | 显式过滤 | **丢弃** |

### 4.2 Amazon Bedrock 的处理方式

**源码位置**: `models.py` 第 2041-2048 行

```python
# Get content blocks with "text" key: in case thinking blocks are present, discard them
message_content_blocks_with_text = [
    block for block in response["output"]["message"]["content"] 
    if "text" in block  # 只保留 text 类型
]
# Keep the last one
content = message_content_blocks_with_text[-1]["text"]
```

**问题**：如果模型将 thinking 内容放在特殊字段（如 `reasoning_content`），这部分内容会被**过滤掉**，不会进入 `model_output`。

### 4.3 OpenAI o3/o4 的特殊说明

**源码位置**: `models.py` 第 422-434 行

```python
# Not supported with reasoning models openai/o3, openai/o4-mini, and the openai/gpt-5 series
if model_name == "o3-mini":
    return True
# o3* (except mini), o4*, all grok-* models, and the gpt-5* family don't support stop parameter
openai_model_pattern = r"(o3(?:$|[-.].*)|o4(?:$|[-.].*)|gpt-5.*)"
```

**限制**：Reasoning 模型不支持 `stop_sequences` 参数，可能影响 CodeAgent 的执行。

---

## 五、如何获取更详细的 Thought

### 5.1 方案一：使用 CodeAgent（推荐）

CodeAgent 的 Prompt 强制要求详细的 Thought，适合需要查看推理过程的场景：

```python
from smolagents import CodeAgent, HfApiModel

agent = CodeAgent(
    tools=[search_tool, calculator_tool],
    model=HfApiModel(),
)

result = agent.run("分析过去一年的销售数据")

# 获取每步的 Thought
for step in agent.memory.steps:
    if hasattr(step, 'model_output') and step.model_output:
        print(f"\n步骤 {step.step_number}:")
        print(step.model_output)
```

### 5.2 方案二：自定义 ToolCallingAgent Prompt

添加 Thought 要求到 ToolCallingAgent：

```python
custom_prompt = """You must follow this format:

Thought: First, explain your reasoning towards solving the task.

Action: {"name": "tool_name", "arguments": {...}}
"""

from smolagents import ToolCallingAgent

agent = ToolCallingAgent(
    tools=tools,
    model=model,
    system_prompt=custom_prompt  # 覆盖默认 prompt
)
```

### 5.3 方案三：使用结构化输出（CodeAgent）

启用 `_use_structured_outputs_internally` 获取分离的 thought 和 code：

```python
agent = CodeAgent(
    tools=tools,
    model=model,
    use_structured_outputs=True  # 返回 {"thought": "...", "code": "..."}
)

# 此时 model_output 可能是 JSON 格式
# {"thought": "I will search for...", "code": "result = search(...)"}
```

### 5.4 方案四：使用 step_callbacks 监控

```python
def on_action_step(step, agent):
    if hasattr(step, 'model_output') and step.model_output:
        # 提取 Thought
        if "Thought:" in step.model_output:
            thought = step.model_output.split("Thought:")[1].split("Code:")[0]
            print(f"[思考] {thought}")
        else:
            print(f"[输出] {step.model_output}")

agent = CodeAgent(
    tools=tools,
    model=model,
    step_callbacks=[on_action_step]
)
```

---

## 六、前端展示建议

### 6.1 Thought 的展示方式

| Agent 类型 | Thought 展示 | 特殊处理 |
|-----------|-------------|---------|
| **CodeAgent** | 可折叠的思维卡片 | 语法高亮、Markdown 渲染 |
| **ToolCallingAgent** | 可选的推理文本 | 如果没有 Thought，隐藏该部分 |

### 6.2 CodeAgent Thought 展示示例

```
┌─ Step 1 ──────────────────────────┐
│ Thought:                          │
│ I need to analyze the sales data  │
│ to identify trends. First, I will │
│ load the data and check its       │
│ structure.                        │
├─ Code ────────────────────────────┤
│ ```python                           │
│ import pandas as pd                 │
│ df = pd.read_csv('sales.csv')       │
│ print(df.head())                    │
│ ```                                 │
└───────────────────────────────────┘
```

### 6.3 ToolCallingAgent Thought 展示示例

```
┌─ Step 1 ──────────────────────────┐
│ [推理过程可选显示]                 │
│ Let me search for the information │
│                                   │
│ Action:                           │
│ {                                   │
│   "name": "web_search",            │
│   "arguments": {"query": "..."}    │
│ }                                   │
└───────────────────────────────────┘
```

---

## 七、最佳实践总结

### 7.1 选择合适的 Agent

| 场景 | 推荐 Agent | 理由 |
|------|-----------|------|
| 需要查看详细推理过程 | **CodeAgent** | Prompt 强制要求 Thought |
| 需要简洁的 JSON 输出 | ToolCallingAgent | 输出结构简单 |
| 复杂多步骤任务 | **CodeAgent** | Thought 帮助理解执行逻辑 |
| 与外部 API 集成 | ToolCallingAgent | 标准 JSON 格式易于解析 |

### 7.2 Thought 的利用方式

1. **调试**：通过 Thought 理解 Agent 的决策逻辑
2. **展示**：向用户展示 AI 的推理过程，增加透明度
3. **日志**：记录 Thought 用于后续分析和优化
4. **干预**：基于 Thought 内容判断是否需要人工干预

### 7.3 注意事项

1. **不要假设 ToolCallingAgent 一定有 Thought**
2. **CodeAgent 的 Thought 可能包含代码片段**，需要适当过滤
3. **Thinking 模型的特殊内容可能被丢弃**，如需使用需自定义 Model 类

---

## 相关文档

- [[25-smolagents-CodeAgent与ToolCallingAgent深度对比]]
- [[50-smolagents-CodeAgent与ToolCallingAgent流式输出对比分析]]
- [[26-smolagents-CodeAgent与ToolCallingAgent协作模式]]
