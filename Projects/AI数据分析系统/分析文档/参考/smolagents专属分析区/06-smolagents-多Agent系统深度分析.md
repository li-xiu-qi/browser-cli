# smolagents 多Agent系统深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/agents.py

## 一、总体架构设计

### 1.1 层级结构模型

smolagents 的多Agent系统采用**Manager-Managed**层级模式，形成树形调用结构：

```
Manager Agent (CodeAgent)
    ├── Code Interpreter Tool
    └── Web Search Agent (ToolCallingAgent) [managed_agent]
            ├── Web Search Tool
            └── Visit Webpage Tool
```

**核心设计原则**：

1. **单一管理入口**：每个Manager Agent统一管理其下属的managed_agents
2. **透明调用**：子Agent对父Agent而言如同普通Tool
3. **职责分离**：Manager负责决策规划，Managed Agent负责专项执行
4. **结果封装**：子Agent的执行结果被包装为字符串返回

### 1.2 与单Agent架构的关系

多Agent系统并非独立架构，而是建立在单Agent基础上的扩展：

```
MultiStepAgent (基类)
    ├── managed_agents: dict[str, MultiStepAgent]
    ├── tools: dict[str, Tool]
    └── _setup_managed_agents()  ← 关键初始化方法
```

这种设计意味着**任何Agent都可以同时充当Manager和Managed**两种角色，形成灵活的层级嵌套。

---

## 二、ManagedAgent机制详解

### 2.1 初始化与注册

**关键代码**：`agents.py:294-340`

```python
def __init__(
    self,
    tools: list[Tool],
    model: Model,
    managed_agents: list | None = None,  # 关键参数
    name: str | None = None,             # 被管理时必须
    description: str | None = None,      # 被管理时必须
    ...
):
    self._setup_managed_agents(managed_agents)
    self._setup_tools(tools, add_base_tools)
    self._validate_tools_and_managed_agents(tools, managed_agents)
```

**初始化流程**：

1. **参数校验**：`name`和`description`对Managed Agent是必需的
2. **字典映射**：通过`_setup_managed_agents`将列表转为name-to-agent字典
3. **属性注入**：为每个子Agent添加Tool-like的输入输出定义
4. **名称冲突检查**：确保tools和managed_agents之间无重名

### 2.2 _setup_managed_agents方法

**关键代码**：`agents.py:369-387`

```python
def _setup_managed_agents(self, managed_agents: list | None = None) -> None:
    self.managed_agents = {}
    if managed_agents:
        # 校验：所有子Agent必须有name和description
        assert all(agent.name and agent.description for agent in managed_agents)
        
        # 构建字典：name -> agent
        self.managed_agents = {agent.name: agent for agent in managed_agents}
        
        # 为每个子Agent添加Tool-like接口
        for agent in self.managed_agents.values():
            agent.inputs = {
                "task": {"type": "string", "description": "..."},
                "additional_args": {"type": "object", "nullable": True},
            }
            agent.output_type = "string"
```

**核心作用**：

| 步骤 | 操作 | 目的 |
|------|------|------|
| 1 | 校验name和description | 确保可被LLM识别和调用 |
| 2 | 构建字典映射 | 实现O(1)的名称查找 |
| 3 | 注入inputs属性 | 定义调用参数schema |
| 4 | 设置output_type | 声明返回类型为字符串 |

### 2.3 _validate_tools_and_managed_agents方法

**关键代码**：`agents.py:404-414`

```python
def _validate_tools_and_managed_agents(self, tools, managed_agents):
    tool_and_managed_agent_names = [tool.name for tool in tools]
    if managed_agents is not None:
        tool_and_managed_agent_names += [agent.name for agent in managed_agents]
    if self.name:
        tool_and_managed_agent_names.append(self.name)
    
    # 检查重复名称
    if len(tool_and_managed_agent_names) != len(set(tool_and_managed_agent_names)):
        raise ValueError("Each tool or managed_agent should have a unique name!")
```

**验证逻辑说明**：

- Tools和Managed Agents共享同一个命名空间
- 名称重复会导致LLM无法区分调用目标
- 甚至Manager Agent自身的name也被纳入检查，防止自调用循环

### 2.4 子Agent定义时的可见性控制

**关键问题**：当定义一个子Agent时，哪些信息会被主Agent看见？

#### 可见性字典

```python
# 子Agent定义时的可见性映射
visibility_map = {
    # 完全可见：传入主Agent的system prompt
    "name": "search_agent",                    # ✓ 可见 - 函数名
    "description": "网络搜索Agent",             # ✓ 可见 - 函数docstring
    "inputs": {                                # ✓ 可见 - 参数schema
        "task": {"type": "string", ...},
        "additional_args": {"type": "object", ...}
    },
    "output_type": "string",                   # ✓ 可见 - 返回类型
    
    # 完全不可见：主Agent无法感知
    "model": "gpt-4",                          # ✗ 不可见 - 使用什么模型
    "tools": [WebSearchTool(), ...],           # ✗ 不可见 - 内部工具
    "max_steps": 10,                           # ✗ 不可见 - 最大步数
    "planning_interval": 3,                    # ✗ 不可见 - 规划频率
    "memory": {...},                           # ✗ 不可见 - 记忆内容
    "system_prompt": "...",                    # ✗ 不可见 - 内部prompt
    
    # 部分可见：通过return_full_result控制
    "steps": [...],                            # △ 可选 - 执行步骤
    "token_usage": {...},                      # △ 可选 - Token使用
    "timing": {...},                           # △ 可选 - 执行时间
}
```

#### 可见性层次说明

| 层次 | 可见性 | 内容 | 作用 |
|------|--------|------|------|
| **接口层** | 100%可见 | name, description, inputs, output_type | 主Agent知道如何调用 |
| **实现层** | 0%可见 | model, tools, max_steps, planning_interval, memory | 完全封装，黑盒处理 |
| **监控层** | 可选 | steps, token_usage, timing | 需设置return_full_result=True |

#### 代码示例

```python
# 定义子Agent
search_agent = ToolCallingAgent(
    # 接口层 - 主Agent可见
    name="search_agent",
    description="This is an agent that can do web search.",
    
    # 实现层 - 主Agent不可见
    model=OpenAIServerModel("gpt-4"),
    tools=[WebSearchTool(), VisitWebpageTool()],
    max_steps=10,
    planning_interval=3,
    
    # 监控层 - 可选可见
    return_full_result=True,  # 开启后父Agent可获取统计信息
)

# 主Agent只看到这个
available_tools = {
    "search_agent": {
        "callable": search_agent.__call__,
        "description": "This is an agent that can do web search.",
        "inputs": {
            "task": {"type": "string", "description": "..."},
            "additional_args": {"type": "object", "nullable": True}
        },
        "output_type": "string"
    }
}
```

**设计哲学**：
- **封装性**：子Agent的内部实现细节完全封装
- **契约性**：只暴露调用契约（name, description, inputs, outputs）
- **灵活性**：子Agent可独立演进，不影响父Agent

---

## 三、子Agent调用流程

### 3.1 Tool-like调用机制

Managed Agent被设计为**可调用对象**，对外暴露与Tool相同的接口：

```python
# 父Agent眼中的子Agent就像一个Tool
tool_name = "search_agent"
arguments = {"task": "查找2024年美国GDP增长率"}
result = tool(**arguments)  # 实际调用子Agent的__call__方法
```

### 3.2 tools_and_managed_agents属性

**关键代码**：`agents.py:1261-1263`

```python
@property
def tools_and_managed_agents(self):
    """Returns a combined list of tools and managed agents."""
    return list(self.tools.values()) + list(self.managed_agents.values())
```

**设计意图**：

- LLM无需区分Tool和Managed Agent
- 统一传入`tools_to_call_from`参数
- 返回列表顺序：先Tools后Managed Agents

### 3.3 execute_tool_call中的分支逻辑

**关键代码**：`agents.py:1453-1502`

```python
def execute_tool_call(self, tool_name: str, arguments: dict[str, str] | str) -> Any:
    # 1. 合并可用工具字典
    available_tools = {**self.tools, **self.managed_agents}
    
    # 2. 获取目标
    tool = available_tools[tool_name]
    
    # 3. 关键判断：是否为Managed Agent
    is_managed_agent = tool_name in self.managed_agents
    
    # 4. 执行调用
    if isinstance(arguments, dict):
        return tool(**arguments) if is_managed_agent else tool(**arguments, sanitize_inputs_outputs=True)
    else:
        return tool(arguments) if is_managed_agent else tool(arguments, sanitize_inputs_outputs=True)
```

**差异化处理**：

| 特性 | 普通Tool | Managed Agent |
|------|----------|---------------|
| 参数处理 | 需要sanitize_inputs_outputs | 直接传递 |
| 错误提示 | "Error executing tool" | "Error executing request to team member" |
| 返回值 | 原始类型 | 字符串包装 |

### 3.4 子Agent执行结果返回

**关键代码**：`agents.py:868-890`

```python
def __call__(self, task: str, **kwargs):
    """Adds additional prompting for the managed agent, runs it, and wraps the output."""
    
    # 1. 包装任务：添加managed_agent task模板
    full_task = populate_template(
        self.prompt_templates["managed_agent"]["task"],
        variables=dict(name=self.name, task=task),
    )
    
    # 2. 执行子Agent
    result = self.run(full_task, **kwargs)
    
    # 3. 提取输出
    if isinstance(result, RunResult):
        report = result.output
    else:
        report = result
    
    # 4. 包装结果：添加managed_agent report模板
    answer = populate_template(
        self.prompt_templates["managed_agent"]["report"],
        variables=dict(name=self.name, final_answer=report)
    )
    
    # 5. 可选：添加执行摘要
    if self.provide_run_summary:
        answer += "\n\nFor more detail, find below a summary of this agent's work..."
    
    return answer
```

#### 返回结果包裹结构

子Agent返回的结果被多层包装，最终变成一个字符串返回给父Agent：

```python
# 包装层次结构
wrapped_result = {
    "layer_1_original": {
        # 子Agent内部执行产生的原始结果
        "output": "原始输出内容",
        "state": "success",
        "steps": [...],           # 中间步骤详情
        "token_usage": {
            "input_tokens": 1500,
            "output_tokens": 800
        },
        "timing": {
            "start_time": 1234567890.0,
            "end_time": 1234567920.0,
            "duration": 30.0
        }
    },
    "layer_2_extracted": "原始输出内容",  # 从RunResult中提取的output字段
    "layer_3_wrapped": """
        Here is the final answer from your managed agent 'search_agent':
        原始输出内容
        
        For more detail, find below a summary of this agent's work:
        Steps taken: 5
        Token used: 2300
        Time taken: 30.0s
    """  # 添加managed_agent.report模板 + 可选的执行摘要
}

# 最终返回给父Agent的就是这个字符串
final_answer = wrapped_result["layer_3_wrapped"]
```

#### 返回结果内容变化示例

假设子Agent执行了一个搜索任务，各层内容变化如下：

```
【Layer 1】子Agent内部RunResult
{
    "output": "2024年美国GDP增长率为2.8%...",
    "state": "success",
    "steps": [
        {"type": "action", "tool": "web_search", "input": "2024年美国GDP增长率"},
        {"type": "observation", "output": "搜索结果..."},
        {"type": "final_answer", "output": "2024年美国GDP增长率为2.8%..."}
    ],
    "token_usage": {"input_tokens": 1200, "output_tokens": 500},
    "timing": {"duration": 15.5}
}

【Layer 2】提取output字段
"2024年美国GDP增长率为2.8%，根据世界银行数据..."

【Layer 3】包装后最终返回给父Agent的字符串
"""
Here is the final answer from your managed agent 'search_agent':
2024年美国GDP增长率为2.8%，根据世界银行数据...

For more detail, find below a summary of this agent's work:
Steps taken: 3
Token used: 1700
Time taken: 15.5s
"""
```

#### 信息丢失与保留

| 信息类型 | Layer 1 | Layer 2 | Layer 3 | 说明 |
|----------|---------|---------|---------|------|
| 最终输出 | ✓ | ✓ | ✓ | 核心信息始终保留 |
| 执行状态 | ✓ | ✗ | ✗ | 成功/失败状态丢失 |
| 执行步骤 | ✓ | ✗ | △ | 默认丢失，provide_run_summary可保留摘要 |
| Token使用 | ✓ | ✗ | △ | 默认丢失，provide_run_summary可保留统计 |
| 执行时间 | ✓ | ✗ | △ | 默认丢失，provide_run_summary可保留统计 |
| 工具调用详情 | ✓ | ✗ | ✗ | 具体调用了哪些工具完全丢失 |
| 中间思考过程 | ✓ | ✗ | ✗ | ReAct循环的思考过程丢失 |

**关键设计意图**：
- **简化接口**：父Agent只需要最终结果，不需要了解子Agent的执行细节
- **上下文控制**：避免子Agent的详细执行历史撑爆父Agent的上下文窗口
- **可控透传**：通过`provide_run_summary`参数控制是否透传执行摘要

#### provide_run_summary参数详解

```python
# 在子Agent初始化时设置
search_agent = ToolCallingAgent(
    name="search_agent",
    description="网络搜索Agent",
    model=model,
    tools=[WebSearchTool()],
    provide_run_summary=False,  # 默认False，只返回简单包装结果
)

# 或设置为True，添加执行统计信息
search_agent = ToolCallingAgent(
    ...,
    provide_run_summary=True,   # 添加步骤数、Token使用、执行时间统计
)
```

**provide_run_summary=False时的返回**：
```
Here is the final answer from your managed agent 'search_agent':
2024年美国GDP增长率为2.8%...
```

**provide_run_summary=True时的返回**：
```
Here is the final answer from your managed agent 'search_agent':
2024年美国GDP增长率为2.8%...

For more detail, find below a summary of this agent's work:
Steps taken: 3
Token used: 1700
Time taken: 15.5s
```

#### 执行流程图解

```
父Agent调用子Agent
       │
       ▼
┌─────────────────┐
│ 包装任务prompt  │  ← 添加managed_agent.task模板
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 子Agent.run()   │  ← 独立执行ReAct循环
│                 │  ← 产生RunResult对象
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 提取最终结果    │  ← 从RunResult.output提取
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 包装结果prompt  │  ← 添加managed_agent.report模板
│                 │  ← 可选添加执行摘要
└────────┬────────┘
         │
         ▼
返回字符串给父Agent
```

---

## 四、调用链追踪与监控

### 4.1 RunResult数据结构

**关键代码**：`agents.py:195-254`

```python
@dataclass
class RunResult:
    output: Any | None                    # 最终输出
    state: Literal["success", "max_steps_error"]  # 执行状态
    steps: list[dict]                     # 步骤记录
    token_usage: TokenUsage | None        # Token使用量
    timing: Timing                        # 时间信息
```

**TokenUsage结构**：

```python
@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
```

**Timing结构**：

```python
@dataclass  
class Timing:
    start_time: float
    end_time: float
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
```

### 4.2 跨Agent调用链追踪

**示例分析**：`inspect_multiagent_run.py`

```python
# 1. 初始化OpenTelemetry追踪
register()
SmolagentsInstrumentor().instrument(skip_dep_check=True)

# 2. 创建子Agent
search_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=model,
    name="search_agent",
    description="This is an agent that can do web search.",
    return_full_result=True,  # 关键：返回完整RunResult
)

# 3. 创建父Agent
manager_agent = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[search_agent],
    return_full_result=True,
)

# 4. 执行并获取统计
run_result = manager_agent.run("...")
print("Token usage:", run_result.token_usage)
print("Timing:", run_result.timing)
```

**追踪原理**：

1. **OpenTelemetry集成**：通过`SmolagentsInstrumentor`自动注入追踪点
2. **父子关联**：每次子Agent调用生成独立的span，通过trace ID关联
3. **指标聚合**：父Agent的token_usage仅包含自身，子Agent需单独统计

### 4.3 监控限制

**当前设计的局限**：

- **无自动聚合**：父Agent的RunResult不包含子Agent的TokenUsage
- **手动统计**：需要遍历所有子Agent的RunResult进行累加
- **时间计算**：子Agent执行时间计入父Agent总时间，但无细分 breakdown

---

## 五、Prompt工程

### 5.1 ManagedAgentPromptTemplate结构

**定义位置**：`agents.py:140-151`

```python
class ManagedAgentPromptTemplate(TypedDict):
    task: str    # 子Agent接收任务的prompt模板
    report: str  # 子Agent返回结果的prompt模板
```

### 5.2 子Agent任务Prompt

**模板来源**：`prompts/toolcalling_agent.yaml:217-234`

```yaml
managed_agent:
  task: |-
      You're a helpful agent named '{{name}}'.
      You have been submitted this task by your manager.
      ---
      Task:
      {{task}}
      ---
      You're helping your manager solve a wider task: so make sure to not provide a one-line answer, but give as much information as possible to give them a clear understanding of the answer.

      Your final_answer WILL HAVE to contain these parts:
      ### 1. Task outcome (short version):
      ### 2. Task outcome (extremely detailed version):
      ### 3. Additional context (if relevant):
```

**设计意图**：

1. **身份声明**：明确告知子Agent其角色和名称
2. **上下文传递**：让子Agent理解其工作在更大任务中的位置
3. **输出规范**：强制要求结构化输出，避免简单回复
4. **容错导向**：即使失败也要返回详细信息供父Agent决策

### 5.3 父Agent对子Agent的认知

**System Prompt渲染**：`agents.py:1265-1274`

```python
def initialize_system_prompt(self) -> str:
    system_prompt = populate_template(
        self.prompt_templates["system_prompt"],
        variables={
            "tools": self.tools,
            "managed_agents": self.managed_agents,  # 传递给模板
            ...
        },
    )
    return system_prompt
```

**模板渲染结果**：`prompts/code_agent.yaml:139-154`

```yaml
{%- if managed_agents and managed_agents.values() | list %}
You can also give tasks to team members.
Calling a team member works similarly to calling a tool: provide the task description as the 'task' argument. Since this team member is a real human, be as detailed and verbose as necessary in your task description.
You can also include any relevant variables or context using the 'additional_args' argument.
Here is a list of the team members that you can call:
{{code_block_opening_tag}}
{%- for agent in managed_agents.values() %}
def {{ agent.name }}(task: str, additional_args: dict[str, Any]) -> str:
    """{{ agent.description }}

    Args:
        task: Long detailed description of the task.
        additional_args: Dictionary of extra inputs to pass to the managed agent, e.g. images, dataframes, or any other contextual data it may need.
    """
{% endfor %}
{{code_block_closing_tag}}
{%- endif %}
```

**认知注入效果**：

父Agent的system prompt中，子Agent被描述为：
- **可调用函数**：`def search_agent(task: str, additional_args: dict) -> str`
- **团队成员**：被描述为"team members"或"human"
- **详细指令**：要求父Agent提供详细的任务描述

### 5.4 子Agent结果报告Prompt

**模板定义**：`prompts/code_agent.yaml:305-307`

```yaml
report: |-
    Here is the final answer from your managed agent '{{name}}':
    {{final_answer}}
```

**作用**：

- 为父Agent的结果添加来源标注
- 便于在多子Agent场景区分不同来源
- 保持对话上下文的连贯性

---

## 六、与TaskWeaver对比

### 6.1 架构模式对比

| 维度 | smolagents Manager-Managed | TaskWeaver Planner-Worker |
|------|---------------------------|--------------------------|
| **关系类型** | 树形层级 | 星形辐射 |
| **通信方式** | 同步函数调用 | 异步消息传递 |
| **决策机制** | Manager自主决策 | Planner统一调度 |
| **状态共享** | 通过additional_args显式传递 | 通过共享内存隐式共享 |
| **角色定义** | 运行时动态配置 | 声明式YAML配置 |

### 6.2 调用流程对比

**smolagents调用流程**：

```
Manager Agent
    │
    ├─ Tool Call: search_agent(task="...")
    │      │
    │      ▼
    │   Managed Agent.run()
    │      │
    │      ▼
    │   返回字符串结果
    │
    ▼
继续下一步...
```

**TaskWeaver调用流程**：

```
User Query
    │
    ▼
Planner.reply() ──plan──▶ CodeInterpreter.reply()
    ▲                          │
    └────────result────────────┘
    │
    ▼
Planner整合输出
```

### 6.3 优劣分析

**smolagents优势**：

1. **实现简单**：Managed Agent本质是可调用的Agent实例
2. **学习成本低**：无需理解复杂的角色系统
3. **灵活组合**：任意Agent都可以成为Manager或Managed
4. **透明调用**：对LLM而言Tool和Agent调用语法一致

**smolagents劣势**：

1. **无状态隔离**：子Agent执行不保持跨调用状态
2. **缺乏协调**：多个子Agent之间无法直接通信
3. **监控分散**：需要手动聚合多Agent的指标
4. **容错有限**：子Agent失败不自动触发重试或切换

**TaskWeaver优势**：

1. **状态持久**：IPython Kernel保持执行状态
2. **消息驱动**：基于Post的异步通信支持复杂交互
3. **经验学习**：内置RAG从历史对话学习
4. **角色扩展**：通过YAML声明式定义新Worker

**TaskWeaver劣势**：

1. **架构复杂**：依赖注入、角色系统增加理解门槛
2. **配置分散**：配置分散在多个YAML文件
3. **单点瓶颈**：所有决策经过Planner

### 6.4 适用场景对比

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| 快速原型验证 | smolagents | 代码简洁，5行代码搭建多Agent |
| 企业级数据分析 | TaskWeaver | 状态保持、安全验证、经验复用 |
| 教育演示 | smolagents | 架构清晰，易于理解 |
| 复杂工作流编排 | TaskWeaver | 消息驱动支持复杂流程 |
| 需要云端执行 | smolagents | 支持E2B/Docker/Modal等多种执行器 |

---

## 七、对我们项目的启示

### 7.1 可借鉴的设计

**1. Tool-like Agent封装**

```python
# 我们的实现可以这样设计
class DataAnalysisAgent:
    def __init__(self, name: str, description: str, tools: list[Tool]):
        self.name = name
        self.description = description
        self.tools = tools
        # 注入Tool-like接口
        self.inputs = {
            "task": {"type": "string", "description": "数据分析任务描述"},
            "data": {"type": "object", "description": "输入数据"},
        }
        self.output_type = "string"
    
    def __call__(self, task: str, data: dict = None) -> str:
        # 包装任务、执行、包装结果
        return self.execute(task, data)
```

**2. 统一的调用接口**

```python
# 统一处理Tool和Sub-Agent调用
def execute_call(self, target_name: str, arguments: dict):
    available_targets = {**self.tools, **self.sub_agents}
    target = available_targets[target_name]
    
    is_sub_agent = target_name in self.sub_agents
    if is_sub_agent:
        return target(**arguments)
    else:
        return target(**arguments, sanitize=True)
```

**3. 结构化的子Agent输出**

借鉴smolagents的task模板设计，强制要求子Agent返回：
- 简短结果摘要
- 详细执行报告
- 额外上下文信息

### 7.2 需要增强的方面

**1. 跨Agent状态管理**

当前smolagents仅通过`additional_args`传递上下文，我们的系统可以考虑：
- 引入共享内存机制
- 支持变量引用和传递
- 实现跨Agent的数据流追踪

**2. 调用链聚合监控**

```python
@dataclass
class AggregatedMetrics:
    total_input_tokens: int
    total_output_tokens: int
    agent_breakdown: dict[str, TokenUsage]
    total_duration: float
    agent_durations: dict[str, float]
```

**3. 失败恢复机制**

- 子Agent失败时自动重试
- 支持切换到备选Agent
- 记录失败原因供后续分析

### 7.3 推荐架构设计

结合两者优势，我们的项目可以采用**混合模式**：

```
Orchestrator (类似TaskWeaver Planner)
    ├── 状态管理器 (保持跨Agent状态)
    ├── 经验学习模块 (RAG检索)
    └── Agent调度器
            │
            ├── DataAgent (smolagents风格)
            │       └── tools: [sql_tool, viz_tool]
            │
            ├── CodeAgent (smolagents风格)
            │       └── executor: DockerExecutor
            │
            └── SearchAgent (smolagents风格)
                    └── tools: [web_search, crawler]
```

**核心思想**：

- 使用TaskWeaver的**分层思想**进行高层规划
- 使用smolagents的**轻量设计**实现具体Agent
- 自定义**状态管理层**解决跨Agent数据共享
- 保留**代码执行器**的多种后端选择

---

## 八、总结

### 8.1 smolagents多Agent系统核心特点

1. **极简实现**：Managed Agent机制仅需约100行代码实现核心逻辑
2. **函数式调用**：子Agent通过`__call__`方法实现Tool-like调用
3. **Prompt驱动**：通过模板系统注入子Agent能力和输出规范
4. **层级透明**：父Agent对子Agent的存在无感知差异

### 8.2 关键代码索引

| 功能 | 文件 | 行号 |
|------|------|------|
| Managed Agent初始化 | agents.py | 369-387 |
| 名称验证 | agents.py | 404-414 |
| Tool+Agent统一列表 | agents.py | 1261-1263 |
| 执行分支判断 | agents.py | 1473, 1486-1492 |
| Agent调用入口 | agents.py | 868-890 |
| Prompt模板定义 | agents.py | 140-151 |
| RunResult结构 | agents.py | 195-254 |
| 示例代码 | inspect_multiagent_run.py | 全文 |

### 8.3 技术债务与局限

1. **远程执行限制**：`CodeAgent.create_python_executor`中明确不支持remote executor与managed_agents共存
2. **状态隔离**：子Agent每次调用都是独立的run，无法保持内部状态
3. **无并行子Agent**：不支持同时调用多个子Agent
4. **监控粒度**：缺乏细粒度的跨Agent调用追踪

这些局限为我们的项目提供了明确的改进方向。
