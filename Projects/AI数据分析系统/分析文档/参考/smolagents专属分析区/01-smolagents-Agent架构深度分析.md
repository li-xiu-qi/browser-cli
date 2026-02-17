# smolagents Agent 架构深度分析

> **项目**: smolagents (Hugging Face)  
> **分析日期**: 2026-02-06  
> **源码位置**: `src/smolagents/agents.py`  
> **版本**: 1.12.0+

---

## 一、总体架构设计

### 1.1 核心设计哲学

smolagents 采用**极简主义设计**，核心目标是用最少的代码实现强大的 Agent 功能：

![smolagents-核心架构图.svg](graphviz/smolagents-核心架构图.svg)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        smolagents 核心架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    MultiStepAgent (抽象基类)                         │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │  │
│   │  │    Tools    │  │    Model    │  │   Memory    │  │  Executor  │ │  │
│   │  │   工具集合   │  │   模型接口   │  │   记忆系统   │  │  代码执行器 │ │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│           ┌──────────────────┼──────────────────┐                          │
│           ▼                  ▼                  ▼                          │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                 │
│   │ ToolCallingAgent│  │   CodeAgent   │  │  ManagedAgent │                 │
│   │  (JSON Tool Call)│  │ (Python Code) │  │  (子Agent)    │                 │
│   └───────────────┘  └───────────────┘  └───────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 与 TaskWeaver/PandasAI 对比

| 维度 | smolagents | TaskWeaver | PandasAI |
|------|-----------|------------|----------|
| **架构复杂度** | 极简 (~1800行) | 复杂 (多层架构) | 中等 |
| **核心模式** | ReAct + Tool/Code | Planner-Worker | Facade |
| **代码执行** | LocalPythonExecutor | IPython Kernel | Sandbox (可选) |
| **Agent 类型** | ToolCalling + Code | Planner + Worker | 单一 Agent |
| **多 Agent** | ManagedAgent | 不完全支持 | 不支持 |
| **依赖注入** | 无 | 有 (injector) | 无 |

---

## 二、核心类详解

### 2.1 MultiStepAgent - 抽象基类

**文件位置**: `agents.py:268`

```python
class MultiStepAgent(ABC):
    """
    Agent class that solves the given task step by step, using the ReAct framework:
    While the objective is not reached, the agent will perform a cycle of 
    action (given by the LLM) and observation (obtained from the environment).
    """
```

**核心属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `tools` | `dict[str, Tool]` | 工具字典，key 为工具名 |
| `model` | `Model` | LLM 模型接口 |
| `memory` | `AgentMemory` | 记忆系统 |
| `max_steps` | `int` | 最大执行步数 (默认 20) |
| `managed_agents` | `dict` | 子 Agent 字典 |
| `python_executor` | `PythonExecutor` | Python 代码执行器 |

**核心方法**:

```python
def run(self, task: str, stream: bool = False, ...) -> Any | RunResult:
    """运行 Agent 执行任务"""
    
def step(self, memory_step: ActionStep) -> Any:
    """执行单步 ReAct 循环"""
    
def _run_stream(self, task: str, max_steps: int) -> Generator:
    """流式执行，yield 每一步的结果"""
```

### 2.2 ReAct 循环实现

**核心流程** (`_run_stream` 方法, line 540-611):

```python
def _run_stream(self, task: str, max_steps: int):
    self.step_number = 1
    while not returned_final_answer and self.step_number <= max_steps:
        
        # 1. 规划步骤 (可选)
        if self.planning_interval and should_plan:
            planning_step = self._generate_planning_step(task)
            yield planning_step
        
        # 2. 执行动作步骤
        action_step = ActionStep(step_number=self.step_number)
        try:
            for output in self._step_stream(action_step):
                yield output
                if isinstance(output, ActionOutput) and output.is_final_answer:
                    returned_final_answer = True
        except AgentError as e:
            action_step.error = e
        
        self.memory.steps.append(action_step)
        self.step_number += 1
```

**ReAct 循环图示**:

![smolagents-ReAct循环图.svg](graphviz/smolagents-ReAct循环图.svg)

```
┌────────────────────────────────────────────────────────────────┐
│                      ReAct 循环流程                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐              │
│   │  Thought │────▶│   Action │────▶│Observation│              │
│   │  (思考)  │     │  (行动)  │     │  (观察)   │              │
│   └──────────┘     └──────────┘     └──────────┘              │
│         ▲                                    │                 │
│         └────────────────────────────────────┘                 │
│                                                                │
│   循环直到:                                                     │
│   - 达到最终答案 (is_final_answer=True)                         │
│   - 超过最大步数 (step_number > max_steps)                      │
│   - 发生中断 (interrupt_switch=True)                           │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 三、两种 Agent 实现对比

### 3.1 ToolCallingAgent - JSON Tool Call 模式

**文件位置**: `agents.py:1215`

```python
class ToolCallingAgent(MultiStepAgent):
    """
    使用 JSON 格式的 Tool Call，利用 LLM 原生的 tool calling 能力
    """
```

**执行流程** (`_step_stream`, line 1276-1359):

```python
def _step_stream(self, memory_step: ActionStep):
    # 1. 构建输入消息
    memory_messages = self.write_memory_to_messages()
    input_messages = memory_messages.copy()
    
    # 2. 调用模型生成 tool call
    chat_message = self.model.generate(
        input_messages,
        stop_sequences=["Observation:", "Calling tools:"],
        tools_to_call_from=self.tools_and_managed_agents,
    )
    
    # 3. 解析 tool calls
    if chat_message.tool_calls is None:
        chat_message = self.model.parse_tool_calls(chat_message)
    
    # 4. 并行执行 tool calls
    for tool_call in chat_message.tool_calls:
        yield tool_call
        tool_output = self.execute_tool_call(tool_call.name, tool_call.arguments)
        yield ToolOutput(...)
    
    # 5. 返回最终结果
    yield ActionOutput(output=final_answer, is_final_answer=got_final_answer)
```

**特点**:
- 利用 OpenAI/Anthropic 等模型的原生 tool calling 能力
- 支持并行执行多个 tool calls
- 使用 ThreadPoolExecutor 实现并行 (`max_tool_threads`)

### 3.2 CodeAgent - Python Code 模式

**文件位置**: `agents.py:1505`

```python
class CodeAgent(MultiStepAgent):
    """
    Tool calls 以 Python 代码形式表达，然后解析执行
    """
```

**执行流程** (`_step_stream`, line 1639-1765):

```python
def _step_stream(self, memory_step: ActionStep):
    # 1. 生成代码
    chat_message = self.model.generate(input_messages, stop_sequences=[...])
    output_text = chat_message.content
    
    # 2. 解析代码块
    code_action = parse_code_blobs(output_text, self.code_block_tags)
    code_action = fix_final_answer_code(code_action)
    
    # 3. 创建 ToolCall
    tool_call = ToolCall(
        name="python_interpreter",
        arguments=code_action,
        id=f"call_{len(self.memory.steps)}",
    )
    yield tool_call
    
    # 4. 执行代码
    code_output = self.python_executor(code_action)
    
    # 5. 返回结果
    observation = "Execution logs:\n" + code_output.logs
    yield ActionOutput(output=code_output.output, is_final_answer=code_output.is_final_answer)
```

**特点**:
- LLM 生成 Python 代码片段
- 代码在沙箱环境中执行
- 支持多种执行器类型 (local, docker, e2b, wasm, etc.)
- 更灵活，可以执行任意 Python 代码

### 3.3 两种模式对比

![smolagents-两种Agent对比图.svg](graphviz/smolagents-两种Agent对比图.svg)

| 特性 | ToolCallingAgent | CodeAgent |
|------|-----------------|-----------|
| **输出格式** | JSON Tool Call | Python Code |
| **模型依赖** | 需要原生支持 tool calling | 任何模型 |
| **灵活性** | 受限于预定义工具 | 任意 Python 代码 |
| **安全性** | 较高 (受限工具) | 需要沙箱 |
| **并行执行** | 支持多 tool 并行 | 代码内自行控制 |
| **适用场景** | 结构化任务 | 复杂数据处理 |

---

## 四、记忆系统设计

### 4.1 记忆结构

**文件位置**: `memory.py`

```python
class AgentMemory:
    """Agent 记忆管理"""
    
    def __init__(self, system_prompt: SystemPromptStep):
        self.system_prompt = system_prompt
        self.steps: list[MemoryStep] = []  # 核心：步骤列表
```

**MemoryStep 类型**:

```python
MemoryStep (ABC)
├── SystemPromptStep    # 系统提示
├── TaskStep            # 任务定义
├── PlanningStep        # 规划步骤
├── ActionStep          # 动作步骤 (核心)
└── FinalAnswerStep     # 最终答案
```

**ActionStep 结构**:

```python
@dataclass
class ActionStep(MemoryStep):
    step_number: int                    # 步骤序号
    model_input_messages: list          # 输入给模型的消息
    model_output_message: ChatMessage   # 模型输出
    model_output: str                   # 输出文本
    token_usage: TokenUsage             # Token 使用量
    
    # Tool/Code 执行相关
    tool_calls: list[ToolCall]          # Tool 调用列表
    code_action: str                    # CodeAgent 的代码
    action_output: Any                  # 执行输出
    observations: str                   # 观察结果
    
    # 错误处理
    error: AgentError                   # 执行错误
    
    # 时间追踪
    timing: Timing                      # 执行时间
```

### 4.2 记忆流转

![smolagents-记忆系统图.svg](graphviz/smolagents-记忆系统图.svg)

```
┌────────────────────────────────────────────────────────────────┐
│                      记忆流转流程                               │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   SystemPromptStep                                             │
│         │                                                      │
│         ▼                                                      │
│   TaskStep (用户任务)                                           │
│         │                                                      │
│         ▼                                                      │
│   PlanningStep (可选规划)                                       │
│         │                                                      │
│         ▼                                                      │
│   ActionStep (Step 1) ──▶ Observation ──▶ 添加到 memory        │
│         │                                                      │
│         ▼                                                      │
│   ActionStep (Step 2) ──▶ Observation ──▶ 添加到 memory        │
│         │                                                      │
│        ...                                                     │
│         │                                                      │
│         ▼                                                      │
│   FinalAnswerStep                                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 4.3 记忆转消息

```python
def write_memory_to_messages(self) -> list[ChatMessage]:
    """将记忆转换为模型输入消息"""
    messages = [self.system_prompt.to_chat_message()]
    
    for step in self.steps:
        if isinstance(step, TaskStep):
            messages.append(step.to_chat_message())
        elif isinstance(step, ActionStep):
            # 添加模型输出 (Assistant)
            messages.append(step.model_output_message)
            # 添加观察结果 (User)
            messages.append(ChatMessage(role=MessageRole.USER, content=step.observations))
    
    return messages
```

---

## 五、工具系统设计

### 5.1 工具定义

**文件位置**: `tools.py`

```python
class Tool:
    """工具基类"""
    
    name: str
    description: str
    inputs: dict  # JSON Schema 格式
    output_type: str
    
    def __call__(self, *args, **kwargs):
        """执行工具"""
        return self.forward(*args, **kwargs)
    
    def forward(self, *args, **kwargs):
        """子类实现具体逻辑"""
        raise NotImplementedError
```

### 5.2 @tool 装饰器

```python
@tool
def search_web(query: str) -> str:
    """
    Search the web for information.
    
    Args:
        query: The search query
    
    Returns:
        Search results as a string
    """
    # 实现代码
    return results
```

装饰器自动：
- 提取函数名作为 tool name
- 解析 docstring 作为 description
- 从 type hints 生成 inputs schema

### 5.3 默认工具

**文件位置**: `default_tools.py`

```python
TOOL_MAPPING = {
    "python_interpreter": PythonInterpreterTool,
    "web_search": DuckDuckGoSearchTool,
    "web_fetch": VisitWebpageTool,
    "final_answer": FinalAnswerTool,
}
```

---

## 六、代码执行器设计

### 6.1 执行器类型

CodeAgent 支持多种代码执行环境：

| 执行器 | 类型 | 适用场景 | 安全性 |
|--------|------|---------|--------|
| `LocalPythonExecutor` | 本地 | 开发/测试 | 低 (依赖白名单) |
| `E2BExecutor` | 云端沙箱 | 生产 | 高 |
| `DockerExecutor` | 容器 | 生产 | 高 |
| `WasmExecutor` | WebAssembly | 浏览器 | 高 |
| `ModalExecutor` | Serverless | 生产 | 高 |

### 6.2 LocalPythonExecutor

**文件位置**: `local_python_executor.py`

```python
class LocalPythonExecutor(PythonExecutor):
    """
    本地 Python 代码执行器，通过白名单控制 import
    """
    
    def __init__(self, additional_authorized_imports: list[str], ...):
        self.authorized_imports = set(BASE_BUILTIN_MODULES) | set(additional_authorized_imports)
        self.state: dict = {}  # 执行状态保持
    
    def __call__(self, code: str) -> CodeOutput:
        """执行代码"""
        # 1. 语法检查
        # 2. 白名单检查
        # 3. 执行代码
        # 4. 返回结果
```

**白名单机制**:

```python
BASE_BUILTIN_MODULES = [
    "math", "random", "datetime", "collections", 
    "itertools", "json", "re", "statistics", 
    # ... 其他安全模块
]

# 危险模块被禁止
DANGEROUS_MODULES = ["os", "sys", "subprocess", "importlib", ...]
```

---

## 七、监控与日志

### 7.1 AgentLogger

**文件位置**: `monitoring.py`

```python
class AgentLogger:
    """Rich 格式的日志输出"""
    
    def log(self, content, level=LogLevel.INFO):
        # 使用 Rich 库美化输出
        
    def log_task(self, content, subtitle, level=LogLevel.INFO):
        # 打印任务信息
        
    def log_code(self, title, content, level=LogLevel.INFO):
        # 打印代码块
```

### 7.2 Monitor

```python
class Monitor:
    """监控 token 使用量和成本"""
    
    def __init__(self, model, logger):
        self.model = model
        self.token_usages: list[TokenUsage] = []
    
    def get_total_token_usage(self) -> TokenUsage:
        # 汇总所有步骤的 token 使用
```

---

## 八、与我们项目的启示

### 8.1 值得借鉴的设计

1. **极简架构**: 1800 行代码实现完整功能，避免过度设计
2. **两种 Agent 模式**: ToolCalling 和 Code 满足不同场景
3. **记忆系统**: Step-based 记忆清晰追踪执行过程
4. **流式执行**: Generator 模式支持实时反馈
5. **多种执行器**: 本地/云端/容器适应不同安全需求

### 8.2 推荐实现

```python
# 我们的项目可以这样设计
class OurAgent:
    def __init__(self, tools, model, executor_type="local"):
        self.tools = {tool.name: tool for tool in tools}
        self.model = model
        self.memory = AgentMemory()
        self.executor = create_executor(executor_type)
    
    def run(self, task: str) -> Result:
        self.memory.add_task(task)
        
        for step in range(self.max_steps):
            # 1. 构建 prompt
            messages = self.memory.to_messages()
            
            # 2. 调用模型
            response = self.model.generate(messages)
            
            # 3. 解析 action
            action = self.parse_action(response)
            
            # 4. 执行 action
            if action.type == "tool_call":
                result = self.execute_tool(action)
            elif action.type == "code":
                result = self.executor.execute(action.code)
            
            # 5. 更新记忆
            self.memory.add_step(action, result)
            
            # 6. 检查是否完成
            if result.is_final_answer:
                return result.output
```

### 8.3 与现有分析项目对比

| 特性 | smolagents | TaskWeaver | PandasAI | PremSQL |
|------|-----------|------------|----------|---------|
| **简洁度** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **功能性** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **可扩展** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **安全性** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

---

## 九、总结

### 9.1 核心亮点

1. **1800 行代码**实现完整 Agent 框架，极简高效
2. **双模式 Agent**: ToolCalling (结构化) + CodeAgent (灵活)
3. **Step-based 记忆**: 清晰的 ReAct 循环追踪
4. **多种执行器**: 从本地到云端的安全执行环境
5. **流式执行**: Generator 模式支持实时反馈

### 9.2 适用场景

- **快速原型**: 几行代码创建 Agent
- **教育场景**: 代码简洁易懂
- **轻量级应用**: 不需要 TaskWeaver 的复杂度
- **代码生成任务**: CodeAgent 模式非常强大

### 9.3 局限性

- 无复杂的多 Agent 协作 (只有简单的 ManagedAgent)
- 无依赖注入，扩展性受限
- 无持久化存储 (每次运行重新开始)
- 企业级功能较少
