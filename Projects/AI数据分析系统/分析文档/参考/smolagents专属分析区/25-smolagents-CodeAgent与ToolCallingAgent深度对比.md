# smolagents CodeAgent与ToolCallingAgent深度对比

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/agents.py
> 分析范围: ToolCallingAgent (line 1215-1498), CodeAgent (line 1505-1805)

---

## 一、核心差异总览

ToolCallingAgent 和 CodeAgent 是 smolagents 框架提供的两种核心 Agent 实现，它们共享相同的 MultiStepAgent 基类，但在工具调用方式上有本质区别。

### 1.1 关键维度对比

| 维度 | CodeAgent | ToolCallingAgent |
|------|-----------|------------------|
| 输出格式 | Python 代码块 | JSON Tool Call |
| 适用模型 | 任何 LLM | 需原生支持 tool calling |
| 灵活性 | 极高，任意 Python 代码 | 受限，预定义工具 |
| 安全性 | 需沙箱保护 | 较高，受限工具集 |
| 并行执行 | 代码内自行控制 | 原生支持多 tool 并行 |
| 状态保持 | 执行器内自动保持 | 需显式传递 |
| 典型场景 | 复杂数据处理、代码生成 | API 调用、结构化任务 |

### 1.2 架构位置

```
MultiStepAgent (抽象基类)
    ├── ToolCallingAgent ──▶ JSON Tool Call 模式
    └── CodeAgent ─────────▶ Python Code 模式
```

### 1.3 视觉对比图

![smolagents-两种Agent对比图.svg](graphviz/smolagents-两种Agent对比图.svg)

---

## 二、架构实现对比

### 2.1 类定义与初始化

#### ToolCallingAgent 定义

```python
class ToolCallingAgent(MultiStepAgent):
    """
    This agent uses JSON-like tool calls, using method `model.get_tool_call` 
    to leverage the LLM engine's tool calling capabilities.
    """
    
    def __init__(
        self,
        tools: list[Tool],
        model: Model,
        prompt_templates: PromptTemplates | None = None,
        planning_interval: int | None = None,
        stream_outputs: bool = False,
        max_tool_threads: int | None = None,  # 并行执行关键参数
        **kwargs,
    ):
        prompt_templates = prompt_templates or yaml.safe_load(
            importlib.resources.files("smolagents.prompts")
            .joinpath("toolcalling_agent.yaml").read_text()
        )
        super().__init__(...)
        self.max_tool_threads = max_tool_threads  # ThreadPoolExecutor 线程数
```

#### CodeAgent 定义

```python
class CodeAgent(MultiStepAgent):
    """
    In this agent, the tool calls will be formulated by the LLM in code format, 
    then parsed and executed.
    """
    
    def __init__(
        self,
        tools: list[Tool],
        model: Model,
        prompt_templates: PromptTemplates | None = None,
        additional_authorized_imports: list[str] | None = None,  # 关键安全参数
        planning_interval: int | None = None,
        executor: PythonExecutor = None,
        executor_type: Literal["local", "blaxel", "e2b", "modal", "docker", "wasm"] = "local",
        executor_kwargs: dict[str, Any] | None = None,
        max_print_outputs_length: int | None = None,
        stream_outputs: bool = False,
        use_structured_outputs_internally: bool = False,
        code_block_tags: str | tuple[str, str] | None = None,
        **kwargs,
    ):
        self.additional_authorized_imports = additional_authorized_imports or []
        self.authorized_imports = sorted(
            set(BASE_BUILTIN_MODULES) | set(self.additional_authorized_imports)
        )
        # 支持 6 种执行器类型
        self.executor_type = executor_type
        self.python_executor = executor or self.create_python_executor()
```

### 2.2 _step_stream 方法详解

#### ToolCallingAgent._step_stream (line 1276-1359)

```python
def _step_stream(self, memory_step: ActionStep):
    """
    执行 ReAct 循环的单步：
    1. 构建输入消息
    2. 调用 LLM 生成 tool call
    3. 解析 tool calls
    4. 并行执行 tools
    5. 返回最终结果
    """
    # 步骤 1: 构建消息
    memory_messages = self.write_memory_to_messages()
    input_messages = memory_messages.copy()
    memory_step.model_input_messages = input_messages
    
    # 步骤 2: 调用模型生成 tool call
    chat_message = self.model.generate(
        input_messages,
        stop_sequences=["Observation:", "Calling tools:"],
        tools_to_call_from=self.tools_and_managed_agents,  # 传入可用工具
    )
    
    # 步骤 3: 解析 tool calls
    if chat_message.tool_calls is None:
        # 模型原生不支持时，用 parse_tool_calls 解析
        chat_message = self.model.parse_tool_calls(chat_message)
    else:
        # 解析参数
        for tool_call in chat_message.tool_calls:
            tool_call.function.arguments = parse_json_if_needed(
                tool_call.function.arguments
            )
    
    # 步骤 4: 处理 tool calls（并行执行）
    for output in self.process_tool_calls(chat_message, memory_step):
        yield output
```

#### CodeAgent._step_stream (line 1639-1765)

```python
def _step_stream(self, memory_step: ActionStep):
    """
    执行 ReAct 循环的单步：
    1. 构建输入消息
    2. 调用 LLM 生成代码
    3. 解析代码块
    4. 修复 final_answer
    5. 创建 python_interpreter tool_call
    6. 在 Executor 中执行代码
    7. 返回执行结果
    """
    # 步骤 1: 构建消息
    memory_messages = self.write_memory_to_messages()
    input_messages = memory_messages.copy()
    memory_step.model_input_messages = input_messages
    
    # 步骤 2: 生成代码
    chat_message = self.model.generate(
        input_messages,
        stop_sequences=["Observation:", "Calling tools:", self.code_block_tags[1]],
    )
    output_text = chat_message.content
    
    # 步骤 3: 解析代码块
    if self._use_structured_outputs_internally:
        code_action = json.loads(output_text)["code"]
        code_action = extract_code_from_text(code_action, self.code_block_tags)
    else:
        code_action = parse_code_blobs(output_text, self.code_block_tags)
    
    # 步骤 4: 修复 final_answer 代码
    code_action = fix_final_answer_code(code_action)
    memory_step.code_action = code_action
    
    # 步骤 5: 创建 ToolCall
    tool_call = ToolCall(
        name="python_interpreter",
        arguments=code_action,
        id=f"call_{len(self.memory.steps)}",
    )
    yield tool_call
    
    # 步骤 6: 执行代码
    code_output = self.python_executor(code_action)
    
    # 步骤 7: 返回结果
    observation = "Execution logs:\n" + code_output.logs
    yield ActionOutput(output=code_output.output, is_final_answer=code_output.is_final_answer)
```

### 2.3 核心执行流程图

#### CodeAgent 执行流程

![smolagents-CodeAgent执行流程图.svg](graphviz/smolagents-CodeAgent执行流程图.svg)

#### ToolCallingAgent 执行流程

![smolagents-ToolCallingAgent执行流程图.svg](graphviz/smolagents-ToolCallingAgent执行流程图.svg)

### 2.4 关键方法实现对比

| 方法 | ToolCallingAgent | CodeAgent |
|------|------------------|-----------|
| `parse_code_blobs` | 不使用 | 核心，解析代码块 |
| `fix_final_answer_code` | 不使用 | 修复 final_answer 调用格式 |
| `parse_tool_calls` | 核心，解析 JSON | 不使用 |
| `process_tool_calls` | 并行执行 tools | 不使用 |
| `python_executor` | 不使用 | 核心，执行 Python 代码 |
| `execute_tool_call` | 单个 tool 执行 | 不使用 |

---

## 三、Prompt设计对比

### 3.1 CodeAgent Prompt (code_agent.yaml)

#### System Prompt 核心结构

```yaml
system_prompt: |-
  You are an expert assistant who can solve any task using code blobs.
  You will be given a task to solve as best you can.
  
  To solve the task, you must plan forward to proceed in a series of steps,
  in a cycle of Thought, Code, and Observation sequences.
```

#### 代码编写指导

```yaml
  At each step, in the 'Thought:' sequence, you should first explain your 
  reasoning towards solving the task and the tools that you want to use.
  
  Then in the Code sequence you should write the code in simple Python.
  The code sequence must be opened with '{{code_block_opening_tag}}',
  and closed with '{{code_block_closing_tag}}'.
```

#### 工具调用格式（以代码形式）

```yaml
  During each intermediate step, you can use 'print()' to save whatever 
  important information you will then need.
  
  These print outputs will then appear in the 'Observation:' field,
  which will be available as input for the next step.
```

#### final_answer 调用方式

```yaml
  In the end you have to return a final answer using the `final_answer` tool.
```

示例代码：
```python
result = 5 + 3 + 1294.678
final_answer(result)
```

### 3.2 ToolCallingAgent Prompt (toolcalling_agent.yaml)

#### System Prompt 核心结构

```yaml
system_prompt: |-
  You are an expert assistant who can solve any task using tool calls.
  You will be given a task to solve as best you can.
  
  The tool call you write is an action: after the tool is executed,
  you will get the result of the tool call as an "observation".
```

#### JSON 格式说明

```yaml
  This Action/Observation can repeat N times, you should take several 
  steps when needed.
  
  You can use the result of the previous action as input for the next action.
  The observation will always be a string.
```

#### Tool Calls 格式

```yaml
  Action:
  {
    "name": "tool_name",
    "arguments": {"param1": "value1"}
  }
```

#### 最终答案格式

```yaml
  To provide the final answer to the task, use an action blob with 
  "name": "final_answer" tool.
```

示例：
```json
{
  "name": "final_answer",
  "arguments": {"answer": "insert your final answer here"}
}
```

### 3.3 Prompt 关键差异对比

| 特性 | CodeAgent | ToolCallingAgent |
|------|-----------|------------------|
| 主要格式 | Python 代码块 | JSON Action |
| 代码块标签 | `<code>`/`</code>` 或 Markdown | 无，纯 JSON |
| Thought 要求 | 显式要求 "Thought:" | 隐式在 Action 中 |
| print 机制 | 使用 print 传递中间结果 | 通过 Observation 传递 |
| 工具描述方式 | Python 函数签名 | JSON Schema 描述 |
| 并行能力 | 代码内自行控制 | 原生支持多 tool |

---

## 四、执行流程对比

### 4.1 CodeAgent 执行流程详解

```
┌─────────────────────────────────────────────────────────────────┐
│                      CodeAgent 执行流程                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 生成 Python 代码                                             │
│     └── model.generate()                                         │
│         └── stop_sequences: ["Observation:", "Calling tools:",   │
│                              code_block_tags[1]]                │
│                                                                 │
│  2. 解析代码块                                                   │
│     └── parse_code_blobs(output_text, code_block_tags)          │
│         └── 提取 <code>...</code> 之间的内容                     │
│                                                                 │
│  3. 修复 final_answer                                            │
│     └── fix_final_answer_code(code_action)                      │
│         └── 确保 final_answer 调用格式正确                       │
│                                                                 │
│  4. 创建 python_interpreter tool_call                            │
│     └── ToolCall(name="python_interpreter", arguments=code)     │
│                                                                 │
│  5. 在 Executor 中执行代码                                       │
│     └── python_executor(code_action)                            │
│         ├── LocalPythonExecutor                                 │
│         ├── E2BExecutor                                         │
│         ├── DockerExecutor                                      │
│         └── ... 其他执行器                                       │
│                                                                 │
│  6. 返回执行结果                                                 │
│     └── ActionOutput(output=code_output.output,                 │
│                       is_final_answer=...)                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 ToolCallingAgent 执行流程详解

```
┌─────────────────────────────────────────────────────────────────┐
│                   ToolCallingAgent 执行流程                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 调用模型生成 tool_calls                                      │
│     └── model.generate(tools_to_call_from=tools)                │
│         └── LLM 原生支持时返回 chat_message.tool_calls          │
│                                                                 │
│  2. 解析 tool_calls                                              │
│     ├── 原生支持: 直接使用 chat_message.tool_calls              │
│     └── 不支持:  model.parse_tool_calls(chat_message)           │
│         └── 从文本中提取 JSON 格式的 tool calls                  │
│                                                                 │
│  3. 处理 tool_calls                                              │
│     └── process_tool_calls(chat_message, memory_step)           │
│                                                                 │
│  4. 并行执行多个 tool                                            │
│     ├── 单工具: 直接执行                                         │
│     └── 多工具: ThreadPoolExecutor(max_workers=max_tool_threads)│
│         ├── validate_tool_arguments(tool, arguments)            │
│         ├── execute_tool_call(tool_name, arguments)             │
│         └── 格式化为 ToolOutput                                 │
│                                                                 │
│  5. 收集所有 tool 输出                                           │
│     └── 按 tool_call.id 排序                                     │
│                                                                 │
│  6. 返回结果                                                     │
│     └── ActionOutput(output=final_answer,                       │
│                       is_final_answer=got_final_answer)         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 流程差异关键代码

#### ToolCallingAgent 并行执行代码 (line 1416-1434)

```python
def process_tool_calls(self, chat_message: ChatMessage, memory_step: ActionStep):
    parallel_calls: dict[str, ToolCall] = {}
    
    # 收集所有 tool calls
    for chat_tool_call in chat_message.tool_calls:
        tool_call = ToolCall(...)
        yield tool_call
        parallel_calls[tool_call.id] = tool_call
    
    # 并行执行
    outputs = {}
    if len(parallel_calls) == 1:
        # 单工具直接执行
        tool_call = list(parallel_calls.values())[0]
        tool_output = process_single_tool_call(tool_call)
        outputs[tool_output.id] = tool_output
        yield tool_output
    else:
        # 多工具并行执行
        with ThreadPoolExecutor(self.max_tool_threads) as executor:
            futures = []
            for tool_call in parallel_calls.values():
                ctx = copy_context()
                futures.append(executor.submit(ctx.run, process_single_tool_call, tool_call))
            for future in as_completed(futures):
                tool_output = future.result()
                outputs[tool_output.id] = tool_output
                yield tool_output
```

#### CodeAgent 代码解析代码 (line 1703-1714)

```python
# Parse output
try:
    if self._use_structured_outputs_internally:
        # 结构化输出模式
        code_action = json.loads(output_text)["code"]
        code_action = extract_code_from_text(code_action, self.code_block_tags)
    else:
        # 普通模式，解析代码块
        code_action = parse_code_blobs(output_text, self.code_block_tags)
    
    # 修复 final_answer 调用
    code_action = fix_final_answer_code(code_action)
    memory_step.code_action = code_action
except Exception as e:
    error_msg = f"Error in code parsing:\n{e}\nMake sure to provide correct code blobs."
    raise AgentParsingError(error_msg, self.logger)
```

---

## 五、工具调用方式对比

### 5.1 CodeAgent 的工具调用

模型生成的是纯 Python 代码，工具以 Python 函数的形式被调用：

```python
# 模型生成的代码示例：
web_search("query")
visit_webpage("url")
final_answer("result")

# 复杂示例：
pages = web_search(query="current pope age")
print("Pope age:", pages)
answer = image_qa(image=image, question=translated_question)
final_answer(f"The answer is {answer}")

# 支持循环、条件等编程特性：
for city in ["Guangzhou", "Shanghai"]:
    print(f"Population {city}:", web_search(f"{city} population"))
```

特点：
- 工具调用就是普通的 Python 函数调用
- 变量赋值自动保持，可在后续代码中使用
- 使用 print 输出中间结果到 Observation
- 支持任意 Python 控制流：循环、条件、函数定义等

### 5.2 ToolCallingAgent 的工具调用

模型生成的是 JSON 格式的 tool call：

```json
{
  "tool_calls": [
    {"name": "web_search", "arguments": {"query": "xxx"}},
    {"name": "visit_webpage", "arguments": {"url": "xxx"}}
  ]
}
```

实际 LLM 输出示例：
```json
{
  "name": "document_qa",
  "arguments": {"document": "document.pdf", "question": "Who is the oldest person mentioned?"}
}
```

 Observation 结果：
```
Observation: "The oldest person in the document is John Doe..."
```

下一步 Action：
```json
{
  "name": "image_generator",
  "arguments": {"prompt": "A portrait of John Doe..."}
}
```

### 5.3 工具调用方式对比表

| 对比项 | CodeAgent | ToolCallingAgent |
|--------|-----------|------------------|
| 调用语法 | Python 函数调用 | JSON 格式 |
| 参数传递 | 位置/关键字参数 | JSON 对象 |
| 结果获取 | 变量赋值 | Observation 字符串 |
| 多工具调用 | 代码内顺序/并行控制 | LLM 一次生成多个 |
| 变量状态 | 执行器内自动保持 | 无状态，需显式传递 |
| 循环/条件 | 原生支持 | 不支持，需多轮交互 |

---

## 六、优劣势深度分析

### 6.1 CodeAgent 优势

#### 1. 任何模型都可用

不需要 LLM 原生支持 tool calling。只要模型能生成 Python 代码，就可以使用 CodeAgent。

```python
# 使用不支持 tool calling 的模型
from smolagents import HfApiModel, CodeAgent

model = HfApiModel("meta-llama/Llama-3.2-1B-Instruct")
agent = CodeAgent(tools=[web_search], model=model)
agent.run("搜索天气信息")
```

#### 2. 极度灵活，可写任意 Python 代码

支持所有 Python 编程特性：

```python
# 变量和计算
result = 5 + 3 + 1294.678

# 条件语句
if temperature > 30:
    print("Hot day")
else:
    print("Cool day")

# 循环
for city in ["Guangzhou", "Shanghai"]:
    data = web_search(f"{city} population")
    print(data)

# 列表推导
results = [web_search(q) for q in queries]

# 函数定义
def analyze_data(data):
    return sum(data) / len(data)
```

#### 3. 状态自动保持

代码执行器会自动保持变量状态：

```python
# Step 1
data = web_search("population data")
df = pd.DataFrame(data)  # df 被保持

# Step 2
result = df.mean()  # 可以直接使用 df
```

#### 4. 适合复杂数据处理

数据分析和科学计算场景的天然优势：

```python
import pandas as pd
import numpy as np

# 读取数据
df = pd.read_csv("data.csv")

# 数据清洗
df = df.dropna()
df['normalized'] = (df['value'] - df['value'].mean()) / df['value'].std()

# 统计分析
correlation = df.corr()
print(correlation)

final_answer(correlation.to_dict())
```

### 6.2 CodeAgent 劣势

#### 1. 需要沙箱保障安全

任意代码执行存在安全风险：

```python
# 潜在危险代码
delete_all_files()
send_data_to_remote_server()
```

必须配置执行器白名单：

```python
agent = CodeAgent(
    tools=[],
    model=model,
    additional_authorized_imports=["pandas", "numpy"],  # 明确授权
    executor_type="docker",  # 使用容器隔离
)
```

#### 2. 模型可能生成错误代码

代码语法错误或逻辑错误：

```python
# 可能的错误
result = undefined_variable  # NameError
for i in range(  # SyntaxError
```

需要错误处理和重试机制。

#### 3. 代码解析有一定开销

需要解析代码块、验证语法、修复 final_answer 等步骤。

#### 4. 难以并行执行多个独立 tool

需要在代码内手动控制并行：

```python
# CodeAgent 难以表达这种并行
# Tool1 和 Tool2 无依赖，应该并行执行
result1 = tool1()  # 顺序执行
result2 = tool2()  # 等待 tool1 完成后才执行
```

### 6.3 ToolCallingAgent 优势

#### 1. 原生 tool calling，可靠性高

利用 LLM 的原生能力，格式更准确：

```python
# OpenAI/Anthropic 等模型原生支持
tool_calls = [
    {"name": "web_search", "arguments": {"query": "weather"}},
    {"name": "calculator", "arguments": {"expression": "2+2"}},
]
```

#### 2. 支持并行执行多个 tool

```python
# 模型一次生成多个 tool calls
{
  "tool_calls": [
    {"name": "web_search", "arguments": {"query": "Guangzhou population"}},
    {"name": "web_search", "arguments": {"query": "Shanghai population"}}
  ]
}

# smolagents 自动并行执行
with ThreadPoolExecutor(max_workers=self.max_tool_threads) as executor:
    futures = [executor.submit(process_tool, call) for call in tool_calls]
```

#### 3. 安全性更高

只能调用预定义的、受限的工具集：

```python
# 只能使用提供的 tools
agent = ToolCallingAgent(
    tools=[web_search, calculator],  # 只允许这些工具
    model=model,
)

# 无法执行任意代码
```

#### 4. 延迟更低

无需代码解析和沙箱执行，直接调用工具函数。

### 6.4 ToolCallingAgent 劣势

#### 1. 需要模型原生支持

不支持 tool calling 的模型无法使用：

```python
# Llama 3.2 1B 不支持 tool calling
model = HfApiModel("meta-llama/Llama-3.2-1B-Instruct")
agent = ToolCallingAgent(tools=[web_search], model=model)  # 可能无法正常工作
```

#### 2. 灵活性受限，只能用预定义工具

无法执行任意计算：

```json
// 不能做这种复杂计算
{
  "name": "calculator",
  "arguments": {"expression": "(5 + 3) * 1294.678 / sqrt(16)"}
}
```

#### 3. 不支持复杂编程逻辑

无循环、条件等控制流：

```json
// 无法实现
{
  "tool_calls": [
    {"name": "for_loop", ...},  // 不存在
    {"name": "if_condition", ...}  // 不存在
  ]
}
```

需要通过多轮交互模拟：

```
Step 1: 搜索 Guangzhou
Step 2: 搜索 Shanghai
Step 3: 比较结果
```

#### 4. 某些场景表达能力不足

数据处理场景需要大量中间步骤：

```
Step 1: 读取文件
Step 2: 清洗数据
Step 3: 计算统计量
Step 4: 生成可视化
Step 5: 返回结果
```

CodeAgent 可以在一步内完成：

```python
df = pd.read_csv("data.csv")
df = df.dropna()
stats = df.describe()
print(stats)
final_answer(stats.to_dict())
```

---

## 七、选型决策树

```
1. 模型是否支持原生 tool calling？
   ├─ 否 ───────────────────────────▶ 必须使用 CodeAgent
   │
   └─ 是 ───────────────────────────▶ 继续判断

2. 是否需要复杂编程逻辑（循环/条件/变量）？
   ├─ 是 ───────────────────────────▶ 选择 CodeAgent
   │
   └─ 否 ───────────────────────────▶ 继续判断

3. 是否需要并行调用多个独立 tool？
   ├─ 是 ───────────────────────────▶ 选择 ToolCallingAgent
   │
   └─ 否 ───────────────────────────▶ 继续判断

4. 安全要求是否极高？
   ├─ 是 ───────────────────────────▶ 选择 ToolCallingAgent
   │
   └─ 否 ───────────────────────────▶ 选择 CodeAgent

默认推荐：CodeAgent
```

### 7.1 决策矩阵

| 场景 | 推荐 | 理由 |
|------|------|------|
| 使用开源小模型 | CodeAgent | 不支持 tool calling |
| 数据分析任务 | CodeAgent | 需要编程能力 |
| API 集成任务 | ToolCallingAgent | 结构化调用 |
| 需要并行搜索 | ToolCallingAgent | 原生并行支持 |
| 高安全要求环境 | ToolCallingAgent | 受限工具集 |
| 教育/演示场景 | CodeAgent | 更易理解 |

---

## 八、性能对比

### 8.1 Token 消耗对比

| 指标 | CodeAgent | ToolCallingAgent | 差异 |
|------|-----------|------------------|------|
| System Prompt 长度 | 较长，需包含 import 白名单 | 较短，纯工具描述 | CodeAgent 多约 30% |
| 单次输出 Token | 代码 + Thought | JSON + Thought | CodeAgent 略多 |
| 上下文累积 | 代码块保留在记忆 | Tool calls 保留 | 相近 |

### 8.2 延迟对比

| 阶段 | CodeAgent | ToolCallingAgent | 说明 |
|------|-----------|------------------|------|
| LLM 生成 | 相近 | 相近 | 取决于模型 |
| 解析 | 需解析代码块 | 解析 JSON | CodeAgent 略慢 |
| 执行 | 沙箱执行 | 直接调用 | ToolCallingAgent 更快 |
| 多 tool 场景 | 顺序执行 | 并行执行 | ToolCallingAgent 优势明显 |

### 8.3 准确率对比

基于不同任务类型的分析：

| 任务类型 | CodeAgent | ToolCallingAgent | 说明 |
|----------|-----------|------------------|------|
| 数学计算 | 高 | 中 | CodeAgent 可直接计算 |
| 数据处理 | 高 | 低 | ToolCallingAgent 需多步 |
| API 调用 | 中 | 高 | ToolCallingAgent 格式更准确 |
| 多步骤推理 | 中 | 中 | 取决于具体任务 |
| 代码生成 | 高 | 低 | CodeAgent 擅长 |

### 8.4 错误率对比

| 错误类型 | CodeAgent | ToolCallingAgent | 缓解措施 |
|----------|-----------|------------------|----------|
| 语法错误 | 有 | 无 | CodeAgent 需代码验证 |
| 工具调用格式错误 | 低 | 极低 | ToolCallingAgent 原生支持 |
| 运行时错误 | 有 | 有 | 两者都需要错误处理 |
| 安全违规 | 风险较高 | 风险较低 | CodeAgent 需沙箱 |

---

## 九、实际案例对比

### 9.1 案例：获取两个城市的人口并比较

#### CodeAgent 实现

```python
from smolagents import CodeAgent, HfApiModel, DuckDuckGoSearchTool

agent = CodeAgent(
    tools=[DuckDuckGoSearchTool()],
    model=HfApiModel(),
)

result = agent.run("比较广州和上海的人口哪个更多")
```

CodeAgent 可能生成的代码：

```python
# 一步完成搜索和比较
for city in ["Guangzhou", "Shanghai"]:
    print(f"Population {city}:", web_search(f"{city} population"))

# Observation 包含两个城市的数据
# Thought: 比较后得出结论
final_answer("Shanghai")
```

特点：
- 使用循环并行发起搜索请求
- 一步完成两个搜索
- 代码简洁

#### ToolCallingAgent 实现

```python
from smolagents import ToolCallingAgent, HfApiModel, DuckDuckGoSearchTool

agent = ToolCallingAgent(
    tools=[DuckDuckGoSearchTool()],
    model=HfApiModel(),
    max_tool_threads=4,  # 启用并行
)

result = agent.run("比较广州和上海的人口哪个更多")
```

ToolCallingAgent 的执行流程：

```
Step 1: 同时发起两个搜索（并行）
Action: [
  {"name": "web_search", "arguments": {"query": "Guangzhou population"}},
  {"name": "web_search", "arguments": {"query": "Shanghai population"}}
]
Observation: "Population Guangzhou: 15 million... Population Shanghai: 26 million..."

Step 2: 返回结果
Action: {"name": "final_answer", "arguments": "Shanghai"}
```

特点：
- 通过 max_tool_threads 实现并行
- 需要 LLM 主动选择并行调用
- 两次搜索在一轮内完成

#### 对比结果

| 维度 | CodeAgent | ToolCallingAgent |
|------|-----------|------------------|
| 实现复杂度 | 低 | 低 |
| Token 消耗 | 较少（单步） | 相近 |
| 执行时间 | 快（并行循环） | 快（原生并行） |
| 成功率 | 高 | 高 |
| 可读性 | 代码直观 | JSON 结构化 |

### 9.2 案例：复杂数据分析

#### CodeAgent 实现

```python
agent.run("""
读取 sales.csv 文件，按月份分组计算总销售额，
找出销售额最高的月份，并计算月增长率
""")
```

生成的代码：

```python
import pandas as pd

# 读取数据
df = pd.read_csv("sales.csv")

# 数据转换
df['date'] = pd.to_datetime(df['date'])
df['month'] = df['date'].dt.to_period('M')

# 按月分组统计
monthly_sales = df.groupby('month')['amount'].sum()

# 找出最高月份
max_month = monthly_sales.idxmax()
max_amount = monthly_sales.max()

# 计算增长率
growth_rate = monthly_sales.pct_change() * 100

print(f"最高销售月份: {max_month}, 销售额: {max_amount}")
print("月增长率:")
print(growth_rate)

final_answer({
    "max_month": str(max_month),
    "max_amount": float(max_amount),
    "growth_rates": growth_rate.to_dict()
})
```

#### ToolCallingAgent 实现

ToolCallingAgent 面临挑战：

1. 没有 pandas 工具可用
2. 即使有，需要多轮调用：
   - Step 1: 读取文件
   - Step 2: 转换日期
   - Step 3: 分组
   - Step 4: 计算增长率
   - Step 5: 找出最高值
   - Step 6: 返回结果

```python
# 需要添加 python_interpreter 工具
agent = ToolCallingAgent(
    tools=[python_interpreter],  # 本质上退化为 CodeAgent 方式
    model=model,
)
```

#### 对比结果

| 维度 | CodeAgent | ToolCallingAgent |
|------|-----------|------------------|
| 适用性 | 非常适合 | 不适合 |
| 步骤数 | 1-2 步 | 6+ 步 |
| Token 效率 | 高 | 低 |
| 成功率 | 高 | 低（需多步协调） |

---

## 十、混合使用策略

### 10.1 何时使用 CodeAgent

- 模型不支持原生 tool calling
- 需要复杂编程逻辑（循环、条件、变量）
- 数据分析和科学计算任务
- 需要保持中间状态
- 需要生成代码的场景

### 10.2 何时使用 ToolCallingAgent

- 使用 OpenAI/Anthropic 等原生支持 tool calling 的模型
- 需要并行执行多个独立工具
- 安全要求极高的环境
- API 集成和结构化任务
- 延迟敏感的场景

### 10.3 Manager CodeAgent + Managed ToolCallingAgent 组合

利用 smolagents 的多 Agent 机制：

```python
from smolagents import CodeAgent, ToolCallingAgent, ManagedAgent

# 创建专门的搜索 Agent（使用 ToolCallingAgent 并行搜索）
search_agent = ToolCallingAgent(
    tools=[web_search, visit_webpage],
    model=model,
    max_tool_threads=4,
)

managed_search = ManagedAgent(
    agent=search_agent,
    name="search_expert",
    description="Expert in web search and information retrieval",
)

# 创建主 Agent（CodeAgent 处理复杂逻辑）
main_agent = CodeAgent(
    tools=[calculator],
    model=model,
    managed_agents=[managed_search],  # 子 Agent
)

# 使用
result = main_agent.run("""
搜索广州和上海的人口数据，
然后计算人口比例的百分比
""")
```

执行流程：

```
CodeAgent (Manager)
    ├── 分析任务
    ├── 调用 search_expert (并行搜索两个城市)
    │       └── ToolCallingAgent 并行执行
    │           ├── web_search("Guangzhou population")
    │           └── web_search("Shanghai population")
    ├── 获取搜索结果
    ├── 计算比例
    └── final_answer
```

优势：
- CodeAgent 处理复杂逻辑
- ToolCallingAgent 高效并行搜索
- 职责分离清晰

### 10.4 动态切换策略

根据任务类型自动选择：

```python
def create_agent_for_task(task: str, model):
    """根据任务类型选择合适的 Agent"""
    
    # 数据分析任务 -> CodeAgent
    if any(keyword in task.lower() for keyword in 
           ["csv", "pandas", "data", "分析", "统计"]):
        return CodeAgent(
            tools=[PythonInterpreterTool(), web_search],
            model=model,
            additional_authorized_imports=["pandas", "numpy", "matplotlib"],
        )
    
    # API 调用任务 -> ToolCallingAgent
    elif any(keyword in task.lower() for keyword in 
             ["搜索", "查询", "api", "调用"]):
        return ToolCallingAgent(
            tools=[web_search, visit_webpage],
            model=model,
            max_tool_threads=4,
        )
    
    # 默认使用 CodeAgent
    else:
        return CodeAgent(tools=[web_search], model=model)
```

### 10.5 最佳实践总结

| 策略 | 适用场景 | 实现方式 |
|------|----------|----------|
| 单一 CodeAgent | 数据分析、代码生成 | 标准配置 |
| 单一 ToolCallingAgent | API 集成、结构化任务 | 标准配置 |
| Manager-Managed | 复杂任务分解 | CodeAgent + ToolCallingAgent 组合 |
| 动态选择 | 多类型任务系统 | 任务分类器 + Agent 工厂 |

---

## 十一、对我们项目的启示

### 11.1 设计借鉴

#### 1. 双模式 Agent 设计

我们的 AI数据分析系统 可以同时支持两种模式：

```python
class OurAgent:
    def __init__(self, mode: Literal["code", "tool_calling"] = "code"):
        if mode == "code":
            self.agent = CodeAgent(...)
        else:
            self.agent = ToolCallingAgent(...)
```

#### 2. 统一基类设计

参考 MultiStepAgent 设计我们的基类：

```python
class DataAnalysisAgent(ABC):
    def __init__(self, tools, model, memory):
        self.tools = tools
        self.model = model
        self.memory = memory
    
    @abstractmethod
    def _step_stream(self, memory_step):
        pass
```

#### 3. 执行器抽象

CodeAgent 的多执行器设计值得借鉴：

```python
class CodeExecutor(ABC):
    @abstractmethod
    def execute(self, code: str) -> ExecutionResult:
        pass

class LocalExecutor(CodeExecutor): ...
class DockerExecutor(CodeExecutor): ...
class E2BExecutor(CodeExecutor): ...
```

### 11.2 技术选型建议

#### 推荐方案：以 CodeAgent 为主，ToolCallingAgent 为辅

```
┌─────────────────────────────────────────────────────────┐
│                    AI数据分析系统                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌─────────────────────────────────────────────────┐  │
│   │              主 Agent (CodeAgent)                │  │
│   │  - 复杂数据分析                                  │  │
│   │  - 代码生成                                      │  │
│   │  - 状态保持                                      │  │
│   └────────────────────┬────────────────────────────┘  │
│                        │                                │
│           ┌────────────┼────────────┐                  │
│           ▼            ▼            ▼                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│   │ SQL工具  │  │ 可视化   │  │ 子 Agent │            │
│   └──────────┘  └──────────┘  └──────────┘            │
│                                  │                      │
│                                  ▼                      │
│                        ┌──────────────────┐            │
│                        │ 搜索 Agent        │            │
│                        │ (ToolCallingAgent)│            │
│                        │ - 并行搜索        │            │
│                        │ - 网页抓取        │            │
│                        └──────────────────┘            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

理由：
- 数据分析场景 CodeAgent 更适合
- 搜索场景可用 ToolCallingAgent 作为子 Agent
- 兼容更多模型

### 11.3 关键实现要点

| 要点 | 实现建议 |
|------|----------|
| 代码安全 | 使用白名单 + 沙箱执行 |
| 并行执行 | 参考 ToolCallingAgent 的 ThreadPoolExecutor |
| 状态保持 | 参考 CodeAgent 的 executor state |
| 错误处理 | 区分解析错误、执行错误、生成错误 |
| Prompt 管理 | 使用 YAML 模板，支持自定义指令 |

### 11.4 避免的坑

1. **不要过度依赖 ToolCallingAgent 的并行能力**
   - 只有当工具间无依赖时才并行
   - 并行度需要限制，避免资源耗尽

2. **CodeAgent 的安全配置要完善**
   - 默认白名单要足够严格
   - 生产环境务必使用 Docker/E2B 执行器

3. **Prompt 模板要预留扩展点**
   - 参考 smolagents 的 custom_instructions
   - 支持用户自定义系统提示

4. **错误信息要友好**
   - 代码执行错误要定位到具体行
   - 提供修复建议

---

## 参考文档

- [[01-smolagents-Agent架构深度分析]]
- [[07-smolagents-工具系统设计深度分析]]
- [[21-smolagents-vs-TaskWeaver-架构对比]]
- [[06-smolagents-多Agent系统深度分析]]

---

## 图表索引

- [smolagents-CodeAgent执行流程图.svg](graphviz/smolagents-CodeAgent执行流程图.svg)
- [smolagents-ToolCallingAgent执行流程图.svg](graphviz/smolagents-ToolCallingAgent执行流程图.svg)
- [smolagents-两种Agent对比图.svg](graphviz/smolagents-两种Agent对比图.svg)
