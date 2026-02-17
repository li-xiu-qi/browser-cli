# smolagents CodeAgent与ToolCallingAgent协作模式

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/agents.py

---

## 一、协作架构设计

### 1.1 Manager-Managed 模式

smolagents 采用层级化的 Manager-Managed 架构实现多Agent协作。在这一架构中，CodeAgent 通常扮演 Manager 角色，负责复杂推理和任务规划；ToolCallingAgent 扮演 Managed Agent 角色，负责具体工具的执行。

```python
# Manager: CodeAgent 负责复杂推理
manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[search_agent, calculator_agent],
)

# Managed: ToolCallingAgent 负责具体工具调用
search_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=model,
    name="search_agent",
    description="执行网络搜索并返回结果",
)
```

### 1.2 架构层级关系

```
Manager CodeAgent
    ├── 推理规划层：分析任务、制定策略
    ├── 代码执行层：执行复杂计算
    └── 子Agent调度层：调用 managed_agents
            │
            ├── ToolCallingAgent A: 并行搜索
            │       ├── WebSearchTool
            │       └── VisitWebpageTool
            │
            └── ToolCallingAgent B: 数据查询
                    ├── SQLQueryTool
                    └── APICallTool
```

### 1.3 为什么这种架构有效

| 角色 | 核心能力 | 典型任务 |
|------|----------|----------|
| CodeAgent | 复杂推理、代码生成、状态保持 | 数据分析、算法实现、任务规划 |
| ToolCallingAgent | 并行工具调用、API调用、结构化输出 | 搜索、查询、外部服务调用 |
| 组合效果 | 复杂推理 + 高效执行 | 研究任务、多维度数据收集 |

这种分工基于两种 Agent 的本质差异：

- CodeAgent 生成 Python 代码，可以在执行器内保持变量状态，适合需要多步推理和数据处理的场景
- ToolCallingAgent 利用 LLM 原生 tool calling 能力，一次可生成多个 tool calls 并行执行，适合 I/O 密集型任务

---

## 二、协作机制详解

### 2.1 注册与发现

#### 2.1.1 子Agent如何注册为可调用工具

源码位置：agents.py:369-387

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
                "task": {"type": "string", "description": "Long detailed description of the task."},
                "additional_args": {"type": "object", "nullable": True},
            }
            agent.output_type = "string"
```

#### 2.1.2 Manager如何看到子Agent的能力

源码位置：agents.py:1261-1263

```python
@property
def tools_and_managed_agents(self):
    """Returns a combined list of tools and managed agents."""
    return list(self.tools.values()) + list(self.managed_agents.values())
```

这个属性将 tools 和 managed_agents 合并为一个列表，传递给 LLM 的 `tools_to_call_from` 参数。对 LLM 而言，调用子Agent和调用普通工具使用完全相同的机制。

#### 2.1.3 名称冲突检查

源码位置：agents.py:404-414

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

### 2.2 调用流程

完整的调用流程如下：

```
步骤1: Manager CodeAgent 分析任务
    │
    ▼
步骤2: 决定需要调用子Agent
    │   生成 tool_call: {"name": "search_agent", "arguments": {"task": "..."}}
    ▼
步骤3: 执行 tool_call
    │   调用子Agent的__call__方法
    ▼
步骤4: ToolCallingAgent 执行任务
    │   独立执行 ReAct 循环
    │   可能调用多个 tools 并行执行
    ▼
步骤5: 返回结果给 Manager
    │   结果被包装为字符串
    ▼
步骤6: Manager 基于结果继续推理
    │   结果添加到 observation
    │   进入下一轮 ReAct 循环
    ▼
循环直到任务完成
```

#### 2.2.1 调用执行的核心代码

源码位置：agents.py:1453-1502

```python
def execute_tool_call(self, tool_name: str, arguments: dict[str, str] | str) -> Any:
    # 合并可用工具字典
    available_tools = {**self.tools, **self.managed_agents}
    
    # 获取目标
    tool = available_tools[tool_name]
    
    # 关键判断：是否为Managed Agent
    is_managed_agent = tool_name in self.managed_agents
    
    # 执行调用
    if isinstance(arguments, dict):
        return tool(**arguments) if is_managed_agent else tool(**arguments, sanitize_inputs_outputs=True)
    else:
        return tool(arguments) if is_managed_agent else tool(arguments, sanitize_inputs_outputs=True)
```

注意差异化处理：
- 普通 Tool 调用需要 `sanitize_inputs_outputs=True` 进行输入输出清理
- Managed Agent 直接传递参数，不需要清理

### 2.3 数据传递

#### 2.3.1 任务描述传递

子Agent被调用时，任务描述会被包装：

源码位置：agents.py:868-890

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
    
    # 4. 包装结果
    answer = populate_template(
        self.prompt_templates["managed_agent"]["report"], 
        variables=dict(name=self.name, final_answer=report)
    )
    
    return answer
```

#### 2.3.2 子Agent任务Prompt模板

```yaml
managed_agent:
  task: |-
      You're a helpful agent named '{{name}}'.
      You have been submitted this task by your manager.
      ---
      Task:
      {{task}}
      ---
      You're helping your manager solve a wider task: so make sure to not 
      provide a one-line answer, but give as much information as possible.

      Your final_answer WILL HAVE to contain these parts:
      ### 1. Task outcome (short version):
      ### 2. Task outcome (extremely detailed version):
      ### 3. Additional context (if relevant):
```

这个模板确保：
- 子Agent明确自己的角色和名称
- 理解自己在更大任务中的位置
- 返回结构化输出而非简单回复

#### 2.3.3 上下文共享

Manager 可以通过 `additional_args` 传递额外上下文：

```python
# Manager 调用子Agent时传递上下文
result = search_agent(
    task="分析这张图片",
    additional_args={"image": image_data}
)
```

子Agent会在其 prompt 中看到：

```
You have been provided with these additional arguments, that you can 
access directly using the keys as variables:
{'image': <PIL.Image.Image object>}
```

#### 2.3.4 结果返回格式

子Agent的结果会被包装为统一格式：

```
Here is the final answer from your managed agent 'search_agent':
<子Agent的输出内容>
```

这使得 Manager 可以清楚知道结果的来源。

### 2.4 错误处理

#### 2.4.1 子Agent执行错误

源码位置：agents.py:1490-1502

```python
try:
    if isinstance(arguments, dict):
        return tool(**arguments) if is_managed_agent else tool(**arguments, sanitize_inputs_outputs=True)
    else:
        return tool(arguments) if is_managed_agent else tool(arguments, sanitize_inputs_outputs=True)
except Exception as e:
    if is_managed_agent:
        error_msg = (
            f"Error executing request to team member '{tool_name}' with arguments {str(arguments)}: {e}\n"
            "Please try again or request to another team member"
        )
    else:
        error_msg = (
            f"Error executing tool '{tool_name}' with arguments {str(arguments)}: {type(e).__name__}: {e}\n"
            "Please try again or use another tool"
        )
    raise AgentToolExecutionError(error_msg, self.logger) from e
```

错误信息区分了：
- 子Agent失败：提示 "Error executing request to team member"
- 普通工具失败：提示 "Error executing tool"

---

## 三、适用场景分析

### 3.1 场景1：复杂研究任务

**需求**：研究一个主题，需要多维度信息收集

**协作方式**：
- Manager CodeAgent：分析研究问题，制定搜索策略
- Managed ToolCallingAgent：并行执行多个搜索
- Manager CodeAgent：整合结果，生成报告

**示例代码**：

```python
from smolagents import CodeAgent, ToolCallingAgent, WebSearchTool, VisitWebpageTool, HfApiModel

model = HfApiModel()

# 创建多个搜索子Agent
search_web_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=model,
    name="search_web",
    description="执行网络搜索并访问网页获取详细信息",
    max_steps=5,
)

search_news_agent = ToolCallingAgent(
    tools=[WebSearchTool()],
    model=model,
    name="search_news",
    description="搜索最新新闻和动态",
    max_steps=5,
)

search_scholar_agent = ToolCallingAgent(
    tools=[WebSearchTool()],
    model=model,
    name="search_scholar",
    description="搜索学术论文和研究报告",
    max_steps=5,
)

# 创建Manager
research_manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[search_web_agent, search_news_agent, search_scholar_agent],
    additional_authorized_imports=["pandas", "json"],
    max_steps=10,
)

# 执行研究任务
result = research_manager.run("""
研究2024年电动汽车市场，从以下维度收集信息：
1. 主要厂商的市场份额
2. 最新技术发展趋势  
3. 消费者评价和反馈
4. 未来市场预测

整合所有信息生成一份综合分析报告。
""")
```

**协作流程**：

```
Manager分析任务
    │
    ├── 调用 search_web: "2024年电动汽车市场份额"
    │       └── 并行搜索多个网页
    │
    ├── 调用 search_news: "2024电动汽车技术趋势"
    │       └── 并行搜索新闻源
    │
    ├── 调用 search_scholar: "电动汽车市场预测 2025"
    │       └── 并行搜索学术资料
    │
    ▼
整合所有结果
    │
    ▼
生成分析报告
```

### 3.2 场景2：数据分析 + 多数据源查询

**需求**：从多个数据源获取数据，进行复杂分析

**协作方式**：
- Manager CodeAgent：制定分析计划，编写分析代码
- Managed ToolCallingAgent：并行查询多个数据库或API
- Manager CodeAgent：加载数据，执行分析，生成图表

**示例代码**：

```python
from smolagents import CodeAgent, ToolCallingAgent, HfApiModel
from smolagents.tools import Tool

model = HfApiModel()

# 定义数据源查询工具
@Tool
def query_taobao_api(start_date: str, end_date: str) -> dict:
    """查询淘宝店铺销售数据"""
    # 实际实现调用淘宝API
    return {"total_sales": 100000, "orders": 500}

@Tool
def query_jingdong_api(start_date: str, end_date: str) -> dict:
    """查询京东店铺销售数据"""
    return {"total_sales": 80000, "orders": 400}

@Tool
def query_pdd_api(start_date: str, end_date: str) -> dict:
    """查询拼多多店铺销售数据"""
    return {"total_sales": 60000, "orders": 600}

# 创建数据查询子Agent
taobao_agent = ToolCallingAgent(
    tools=[query_taobao_api],
    model=model,
    name="taobao_query",
    description="查询淘宝店铺销售数据",
    max_steps=3,
)

jd_agent = ToolCallingAgent(
    tools=[query_jingdong_api],
    model=model,
    name="jd_query",
    description="查询京东店铺销售数据",
    max_steps=3,
)

pdd_agent = ToolCallingAgent(
    tools=[query_pdd_api],
    model=model,
    name="pdd_query",
    description="查询拼多多店铺销售数据",
    max_steps=3,
)

# 创建数据分析Manager
analysis_manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[taobao_agent, jd_agent, pdd_agent],
    additional_authorized_imports=["pandas", "matplotlib", "numpy"],
    max_steps=15,
)

# 执行分析任务
result = analysis_manager.run("""
分析2024年Q1各电商平台的销售表现：
1. 从三个平台获取销售数据
2. 对比各平台的销售额和订单量
3. 计算平台占比
4. 生成可视化图表
5. 输出分析报告
""")
```

### 3.3 场景3：代码生成 + 并行测试

**需求**：生成代码并测试多种实现方案

**协作方式**：
- Manager CodeAgent：生成多种算法实现
- Managed ToolCallingAgent：并行测试不同实现的性能
- Manager CodeAgent：比较结果，选择最优方案

**示例代码**：

```python
from smolagents import CodeAgent, ToolCallingAgent, HfApiModel

model = HfApiModel()

@Tool
def benchmark_sort(algorithm: str, data_size: int) -> dict:
    """测试排序算法性能"""
    import time
    import random
    
    data = [random.randint(1, 1000000) for _ in range(data_size)]
    
    start = time.time()
    if algorithm == "quick_sort":
        sorted(data)  # 实际实现快速排序
    elif algorithm == "merge_sort":
        sorted(data)
    elif algorithm == "heap_sort":
        sorted(data)
    elapsed = time.time() - start
    
    return {"algorithm": algorithm, "data_size": data_size, "time_ms": elapsed * 1000}

# 创建性能测试子Agent
benchmark_agent = ToolCallingAgent(
    tools=[benchmark_sort],
    model=model,
    name="benchmark",
    description="测试算法性能，支持不同数据规模",
    max_tool_threads=4,  # 启用并行测试
    max_steps=5,
)

# 创建代码生成Manager
code_manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[benchmark_agent],
    additional_authorized_imports=["time", "random"],
    max_steps=10,
)

# 执行代码优化任务
result = code_manager.run("""
为大数据排序任务选择最优算法：
1. 生成快速排序、归并排序、堆排序的实现代码
2. 使用benchmark工具在以下数据规模测试：
   - 1000条数据
   - 10000条数据
   - 100000条数据
3. 比较各算法在不同规模下的表现
4. 推荐最适合大数据场景的算法
""")
```

### 3.4 场景4：复杂决策 + 多维度评估

**需求**：基于多个维度做出决策

**协作方式**：
- Manager CodeAgent：制定评估框架
- Managed ToolCallingAgent：并行评估不同选项的各个维度
- Manager CodeAgent：综合评估，给出决策建议

**示例代码**：

```python
from smolagents import CodeAgent, ToolCallingAgent, HfApiModel, WebSearchTool

model = HfApiModel()

# 创建评估子Agent
pricing_agent = ToolCallingAgent(
    tools=[WebSearchTool()],
    model=model,
    name="pricing_eval",
    description="评估云服务价格，比较不同服务商的定价模式",
    max_steps=5,
)

performance_agent = ToolCallingAgent(
    tools=[WebSearchTool()],
    model=model,
    name="performance_eval",
    description="评估云服务性能，包括计算、存储、网络性能",
    max_steps=5,
)

services_agent = ToolCallingAgent(
    tools=[WebSearchTool()],
    model=model,
    name="services_eval",
    description="评估云服务商的产品丰富度和支持服务",
    max_steps=5,
)

# 创建决策Manager
decision_manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[pricing_agent, performance_agent, services_agent],
    additional_authorized_imports=["pandas"],
    max_steps=12,
)

# 执行决策任务
result = decision_manager.run("""
为公司选择2024年最佳云服务提供商：

评估对象：AWS、Azure、Google Cloud

评估维度：
1. 价格：计算实例、存储、带宽的定价比较
2. 性能：基准测试数据、SLA保障
3. 服务：产品丰富度、技术支持、生态集成

输出要求：
- 生成决策矩阵
- 为每个维度打分1-10
- 计算加权总分
- 给出最终推荐和理由
""")
```

---

## 四、实现细节

### 4.1 子Agent配置最佳实践

```python
# ToolCallingAgent作为子Agent的最佳配置
search_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=fast_model,  # 可以使用更快的模型
    max_steps=10,  # 限制步数，防止无限循环
    name="search_agent",
    # 重要：Manager通过此了解子Agent能力
    description="""
    执行网络搜索并访问网页获取详细信息。
    擅长：信息检索、网页内容提取、多源数据收集。
    输入：具体的搜索查询字符串。
    输出：结构化的搜索结果摘要。
    """,
    return_full_result=True,  # 返回完整结果供分析
    provide_run_summary=True,  # 提供执行摘要
)
```

关键配置项说明：

| 参数 | 说明 | 建议值 |
|------|------|--------|
| `name` | 子Agent标识符 | 简短、描述性的英文名称 |
| `description` | 能力描述 | 详细说明擅长什么、输入输出格式 |
| `max_steps` | 最大执行步数 | 5-10，防止无限循环 |
| `model` | 使用的模型 | 子Agent可用轻量级模型 |
| `return_full_result` | 返回RunResult | True，便于获取元数据 |

### 4.2 Manager配置最佳实践

```python
# CodeAgent作为Manager的配置
manager = CodeAgent(
    tools=[],  # Manager通常不需要直接工具，通过子Agent调用
    model=reasoning_model,  # 使用更强的推理模型
    managed_agents=[search_agent, calculator_agent, data_agent],
    additional_authorized_imports=["pandas", "numpy", "matplotlib"],
    max_steps=15,  # 更多步数用于复杂推理
    planning_interval=3,  # 每3步进行一次规划更新
)
```

### 4.3 Prompt工程要点

#### 4.3.1 子Agent能力描述

子Agent的 `description` 是 Manager 理解其能力的唯一途径，应该包含：

```python
description="""
【角色定位】
你是一个专门处理XX任务的子Agent。

【核心能力】
- 能力1：详细描述
- 能力2：详细描述

【输入要求】
- task参数：需要具体的、包含上下文的任务描述
- additional_args：可传递图片、数据框等上下文

【输出格式】
返回结构化的结果，包含：
1. 简短结果摘要
2. 详细执行报告
3. 相关上下文信息

【使用场景】
适合处理XXX类型的任务，不适合处理YYY类型的任务。
"""
```

#### 4.3.2 父Agent对子Agent的认知

源码位置：查看 code_agent.yaml 模板

父Agent的 system prompt 中，子Agent被描述为可调用函数：

```
You can also give tasks to team members.
Calling a team member works similarly to calling a tool: provide the task 
description as the 'task' argument. Since this team member is a real human, 
be as detailed and verbose as necessary in your task description.

Here is a list of the team members that you can call:
def search_agent(task: str, additional_args: dict[str, Any]) -> str:
    """执行网络搜索并返回结果"""
    
def calculator_agent(task: str, additional_args: dict[str, Any]) -> str:
    """执行数学计算"""
```

这种设计让 LLM 以调用函数的方式调用子Agent。

#### 4.3.3 Prompt模板原文与翻译

**源码位置**: `src/smolagents/prompts/code_agent.yaml` 第 139-154 行

**英文原文**:
```yaml
{%- if managed_agents and managed_agents.values() | list %}
You can also give tasks to team members.
Calling a team member works similarly to calling a tool: provide the task 
description as the 'task' argument. Since this team member is a real human, 
be as detailed and verbose as necessary in your task description.
You can also include any relevant variables or context using the 
'additional_args' argument.

Here is a list of the team members that you can call:
{{code_block_opening_tag}}
{%- for agent in managed_agents.values() %}
def {{ agent.name }}(task: str, additional_args: dict[str, Any]) -> str:
    """{{ agent.description }}"""
    ...
{% endfor %}
{{code_block_closing_tag}}
{%- endif %}
```

**中文翻译**:
```
你也可以给团队成员分配任务。
调用团队成员的方式类似于调用工具：将任务描述作为 'task' 参数传入。
由于这个团队成员是一个真实的人类，所以在任务描述中要尽可能详细和冗长。
你也可以使用 'additional_args' 参数包含任何相关的变量或上下文。

以下是你可以调用的团队成员列表：
```
def search_agent(task: str, additional_args: dict[str, Any]) -> str:
    """执行网络搜索并返回结果"""
    
def calculator_agent(task: str, additional_args: dict[str, Any]) -> str:
    """执行数学计算"""
```
```

**设计意图解析**:
1. **类比工具调用**：将子Agent包装成函数签名，LLM 以相同方式理解
2. **强调详细描述**："real human" 暗示需要提供更多上下文
3. **参数说明**：明确 task 和 additional_args 的用途
4. **类型提示**：使用 Python 类型注解帮助 LLM 理解参数类型

#### 4.3.4 子Agent Description最佳实践

**反例：糟糕的Description**:
```python
#  太简短，没有区分度
description="搜索工具"

#  过于笼统
description="这个Agent可以处理各种任务"

#  包含实现细节
description="使用Google API进行搜索，最大返回10个结果，支持中英文..."
```

**正例：优秀的Description**:
```python
#  明确能力边界
description="""
执行网络搜索，获取最新公开信息。
适合查找：新闻、事实数据、公开资料、网站内容。
不适合：本地文件查询、数学计算、代码执行。
"""

#  说明输入要求
description="""
分析数据文件并生成可视化图表。
输入要求：
- task：描述分析目标，如'分析销售趋势并预测下季度'
- additional_args：必须包含'file_path'或'dataframe'
输出：图表文件路径和分析报告。
"""

#  包含使用示例
description="""
执行Python代码进行数据分析和科学计算。
示例任务：
- '计算这组数据的统计描述'
- '用matplotlib绘制折线图'
- '执行线性回归分析'
注意：需要明确的输入数据和具体的分析目标。
"""
```

**Description编写原则**:

| 原则 | 说明 | 示例 |
|------|------|------|
| **能力明确** | 清晰说明能做什么 | "执行网络搜索，获取最新信息" |
| **边界清晰** | 说明不能做什么 | "不适合处理本地文件" |
| **输入规范** | 描述参数要求 | "task需要包含具体的上下文" |
| **输出说明** | 预期返回格式 | "返回结构化的JSON结果" |
| **场景示例** | 提供使用示例 | "适合处理：数据分析、图表生成" |

#### 4.3.5 实际案例分析

**案例1：数据分析团队**

```python
# 数据搜索Agent
data_search_agent = ToolCallingAgent(
    name="data_search_agent",
    description="""
    在公开数据源中搜索和获取数据。
    
    核心能力：
    - 搜索公开数据集（Kaggle、政府开放数据等）
    - 获取最新统计数据
    - 查找行业报告
    
    输入要求：
    - task：描述需要的数据类型、时间范围、地域范围
    - additional_args：可选，可传递上次搜索的上下文
    
    输出格式：
    返回数据源的URL、数据概览、可用字段说明。
    
    使用示例：
    - "搜索2024年中国新能源汽车销量数据"
    - "查找北京市过去5年的空气质量数据"
    """,
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=model,
)

# 数据分析Agent
data_analysis_agent = CodeAgent(
    name="data_analysis_agent",
    description="""
    执行Python代码进行数据清洗、分析和可视化。
    
    核心能力：
    - 数据清洗和预处理（pandas）
    - 统计分析（scipy、statsmodels）
    - 数据可视化（matplotlib、seaborn）
    - 机器学习基础分析（sklearn）
    
    输入要求：
    - task：明确的分析目标，包含具体的分析方法
    - additional_args：必须包含'dataset'或'file_path'
    
    输出格式：
    1. 分析结论摘要
    2. 可视化图表（保存为文件）
    3. 详细的数据洞察
    
    适合场景：
    - 销售数据分析
    - 用户行为分析
    - 趋势预测
    - 相关性分析
    
    不适合场景：
    - 获取实时数据（应使用data_search_agent）
    - 需要外部API认证的数据
    """,
    tools=[PythonInterpreterTool()],
    model=model,
    additional_authorized_imports=["pandas", "numpy", "matplotlib", "seaborn"],
)
```

**案例2：内容创作团队**

```python
# 研究Agent
research_agent = ToolCallingAgent(
    name="research_agent",
    description="""
    进行深度研究，收集写作素材和背景信息。
    
    核心能力：
    - 多来源信息收集
    - 事实核查
    - 资料整理
    
    输入要求：
    - task：研究主题，需要明确的研究方向和问题
    - additional_args：可选，可包含初步思路或重点关注点
    
    输出格式：
    结构化的研究报告，包含：
    1. 核心发现摘要
    2. 详细资料和引用来源
    3. 推荐的内容角度
    
    使用场景：
    写作前的资料收集、主题研究、事实核实。
    """,
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=model,
)

# 写作Agent
writing_agent = ToolCallingAgent(
    name="writing_agent",
    description="""
    基于提供的资料撰写高质量文章。
    
    核心能力：
    - 撰写各类文章（博客、报告、新闻稿）
    - 内容结构优化
    - 风格调整
    
    输入要求：
    - task：写作要求，包含主题、目标读者、风格、字数
    - additional_args：必须包含'research_materials'或'topic_outline'
    
    输出格式：
    完整的文章内容，包含标题和正文。
    
    注意：
    本Agent不直接搜索网络，需要research_agent提供研究资料。
    """,
    tools=[TextEditorTool()],
    model=model,
)
```

#### 4.3.6 常见陷阱与解决方案

**陷阱1：Description与实现不匹配**
```python
#  问题：Description说可以处理图片，但工具不支持
description="分析图片内容并生成描述"
tools=[WebSearchTool()]  # 没有图片处理工具

#  解决：Description与工具能力保持一致
description="搜索网络上的图片资源"  # 修改描述
tools=[WebSearchTool()]
```

**陷阱2：Manager和子Agent职责重叠**
```python
#  问题：Manager和子Agent都有搜索能力
manager = CodeAgent(
    tools=[WebSearchTool()],  # Manager有搜索工具
    managed_agents=[
        ToolCallingAgent(
            name="search_agent",
            tools=[WebSearchTool()],  # 子Agent也有搜索工具
            description="执行网络搜索"
        )
    ]
)

#  解决：明确分工
manager = CodeAgent(
    tools=[],  # Manager专注于协调
    managed_agents=[search_agent, analysis_agent, writing_agent]
)
```

**陷阱3：任务分配不清晰**
```python
#  问题：两个子Agent能力描述相似
agent1 = ToolCallingAgent(
    name="data_agent",
    description="处理数据相关任务"
)
agent2 = ToolCallingAgent(
    name="analysis_agent", 
    description="处理数据分析任务"
)
# Manager无法区分该调用哪个

#  解决：明确区分职责边界
agent1 = ToolCallingAgent(
    name="data_collection_agent",
    description="从外部来源收集和获取数据"
)
agent2 = CodeAgent(
    name="data_processing_agent",
    description="对已有数据进行清洗、转换和分析"
)
```

#### 4.3.7 Prompt调试技巧

**技巧1：查看实际Prompt**
```python
# 打印Manager的实际system prompt
print(manager.system_prompt)

# 检查子Agent的描述是否正确渲染
for name, agent in manager.managed_agents.items():
    print(f"Agent: {name}")
    print(f"Description: {agent.description}")
    print("---")
```

**技巧2：测试子Agent调用**
```python
# 单独测试子Agent的响应
result = search_agent.run("测试任务")
print(result)

# 检查是否符合Description中承诺的能力
```

**技巧3：监控Manager的决策**
```python
# 使用回调监控Manager如何调用子Agent
def on_action_step(step):
    if step.tool_calls:
        for tc in step.tool_calls:
            print(f"调用: {tc.function.name}")
            print(f"参数: {tc.function.arguments}")

manager = CodeAgent(
    managed_agents=[search_agent, analysis_agent],
    step_callbacks=[on_action_step]
)
```

---

## 五、性能优化

### 5.1 并行执行

#### 5.1.1 ToolCallingAgent的并行配置

```python
search_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=model,
    max_tool_threads=4,  # 最多4个线程并行执行tools
)
```

#### 5.1.2 并行执行机制

源码位置：agents.py:1416-1434

```python
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

#### 5.1.3 限制说明

当前设计限制：
- Manager 不能并行调用多个子Agent
- 子Agent内部可以并行执行多个 tools
- 需要异步执行可考虑使用 `asyncio`

### 5.2 Token优化

#### 5.2.1 减少上下文传递

```python
# 不好的做法：传递大量原始数据
result = data_agent(
    task="分析数据",
    additional_args={"raw_data": huge_dataframe}  # 占用大量token
)

# 好的做法：传递数据引用
result = data_agent(
    task="分析data.csv文件中的销售数据",
    additional_args={"file_path": "data.csv"}  # 只传递路径
)
```

#### 5.2.2 结果摘要策略

```python
# 启用执行摘要，减少返回给Manager的信息量
search_agent = ToolCallingAgent(
    tools=[WebSearchTool()],
    model=model,
    name="search_agent",
    provide_run_summary=False,  # 关闭详细摘要，只返回核心结果
)
```

### 5.3 缓存策略

#### 5.3.1 子Agent结果缓存

```python
class CachedToolCallingAgent(ToolCallingAgent):
    def __init__(self, *args, cache=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cache = cache or {}
    
    def __call__(self, task: str, **kwargs):
        # 使用任务描述作为缓存键
        cache_key = hash(task)
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = super().__call__(task, **kwargs)
        self.cache[cache_key] = result
        return result
```

#### 5.3.2 避免重复查询

Manager 应该追踪已查询的内容：

```python
# Manager跟踪查询历史
if "广州人口" not in self.query_history:
    result = search_agent(task="广州人口")
    self.query_history.add("广州人口")
```

---

## 六、错误处理

### 6.1 子Agent失败

#### 6.1.1 Manager如何检测子Agent失败

子Agent失败会抛出 `AgentToolExecutionError`，Manager 可以捕获并处理：

```python
# 在自定义Manager中处理子Agent失败
def safe_call_managed_agent(self, agent_name: str, task: str, max_retries: int = 2):
    agent = self.managed_agents.get(agent_name)
    if not agent:
        return f"Agent {agent_name} not found"
    
    for attempt in range(max_retries):
        try:
            return agent(task=task)
        except AgentToolExecutionError as e:
            if attempt < max_retries - 1:
                continue
            return f"Agent {agent_name} failed after {max_retries} attempts: {e}"
```

#### 6.1.2 重试策略

```python
# 指数退避重试
import time

def call_with_retry(agent, task: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return agent(task=task)
        except Exception as e:
            wait_time = 2 ** attempt  # 指数退避
            time.sleep(wait_time)
            if attempt == max_retries - 1:
                raise
```

#### 6.1.3 降级方案

```python
# 主Agent失败时切换到备用Agent
def search_with_fallback(self, query: str):
    try:
        # 先尝试web搜索
        return self.web_search_agent(task=query)
    except:
        try:
            # 失败后尝试本地知识库
            return self.kb_search_agent(task=query)
        except:
            # 最后返回提示
            return "搜索服务暂时不可用，请稍后重试"
```

### 6.2 超时处理

#### 6.2.1 子Agent执行超时

```python
import signal
from functools import wraps

def timeout(seconds: int):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def handler(signum, frame):
                raise TimeoutError(f"Function execution timed out after {seconds} seconds")
            
            # 设置超时
            old_handler = signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
            
            return result
        return wrapper
    return decorator

# 使用装饰器包装子Agent调用
@timeout(60)
def call_managed_agent(agent, task: str):
    return agent(task=task)
```

#### 6.2.2 Manager等待超时

```python
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

def call_with_timeout(agent, task: str, timeout_sec: int = 60):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(agent, task=task)
        try:
            return future.result(timeout=timeout_sec)
        except FutureTimeoutError:
            return f"Agent execution timed out after {timeout_sec} seconds"
```

#### 6.2.3 部分结果处理

```python
# 即使部分失败也返回已有结果
def call_with_partial_result(agent, tasks: list[str]):
    results = []
    for task in tasks:
        try:
            result = agent(task=task)
            results.append({"task": task, "status": "success", "result": result})
        except Exception as e:
            results.append({"task": task, "status": "failed", "error": str(e)})
    
    # 统计成功率和失败项
    success_count = sum(1 for r in results if r["status"] == "success")
    return {
        "total": len(tasks),
        "success": success_count,
        "failed": len(tasks) - success_count,
        "results": results
    }
```

---

## 七、最佳实践

### 7.1 子Agent粒度

#### 7.1.1 何时应该拆分为子Agent

| 情况 | 建议 |
|------|------|
| 任务涉及完全不同的工具集 | 拆分为独立子Agent |
| 任务可由不同模型处理 | 子Agent使用更适合的轻量模型 |
| 需要并行执行的部分 | 拆分为可并行调用的子Agent |
| 需要复用的功能模块 | 封装为独立子Agent |

#### 7.1.2 子Agent粒度控制

**粒度过细的问题**：
- 增加调用开销
- 上下文切换频繁
- 增加系统复杂度

**粒度过粗的问题**：
- 子Agent内部逻辑复杂
- 难以复用
- 错误影响范围大

**推荐原则**：

```python
# 好的拆分：按功能领域
search_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()],
    name="search",
    description="信息检索"
)

calculation_agent = ToolCallingAgent(
    tools=[CalculatorTool(), MathTool()],
    name="calculation",
    description="数学计算"
)

# 不好的拆分：按单个工具
web_search_agent = ToolCallingAgent(tools=[WebSearchTool()], name="web_search")
visit_page_agent = ToolCallingAgent(tools=[VisitWebpageTool()], name="visit_page")
```

### 7.2 通信协议

#### 7.2.1 任务描述的最佳格式

```python
# 不好的任务描述
result = search_agent(task="搜索一下")

# 好的任务描述：包含具体要求和上下文
result = search_agent(task="""
任务：搜索2024年中国新能源汽车销量数据

要求：
1. 查找官方统计数据
2. 包含各品牌销量排行
3. 数据需要标注来源

输出格式：
- 总销量数字
- TOP5品牌及销量
- 数据来源链接
""")
```

#### 7.2.2 结果返回的标准化

建议子Agent返回结构化数据：

```python
# 定义结果结构
result_template = """
### 执行结果

【状态】：成功/部分成功/失败

【核心发现】：
- 发现1
- 发现2

【详细数据】：
```json
{
    "key": "value"
}
```

【来源引用】：
- 来源1：URL
- 来源2：URL

【置信度】：高/中/低
"""
```

#### 7.2.3 错误信息传递

```python
# 标准化的错误格式
error_format = """
### 执行失败

【失败原因】：具体错误描述

【尝试过的方案】：
1. 方案A - 失败原因
2. 方案B - 失败原因

【建议】：
- 可以尝试的调整
- 备选方案
"""
```

### 7.3 监控与调试

#### 7.3.1 追踪跨Agent调用

```python
from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from phoenix.otel import register

# 启用OpenTelemetry追踪
register()
SmolagentsInstrumentor().instrument(skip_dep_check=True)

# 创建Agent并执行
manager = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[search_agent],
    return_full_result=True,  # 获取完整结果用于分析
)

result = manager.run("任务")
print("Token使用:", result.token_usage)
print("执行时间:", result.timing.duration)
```

#### 7.3.2 调用链可视化

```python
def visualize_call_chain(agent, indent=0):
    """递归打印Agent调用链"""
    prefix = "  " * indent
    print(f"{prefix}└─ {agent.name or agent.__class__.__name__}")
    
    for tool_name, tool in agent.tools.items():
        print(f"{prefix}   └─ [Tool] {tool_name}")
    
    for agent_name, sub_agent in agent.managed_agents.items():
        print(f"{prefix}   └─ [Agent] {agent_name}")
        visualize_call_chain(sub_agent, indent + 2)

# 使用
visualize_call_chain(manager)
```

输出示例：

```
└─ Manager
   └─ [Tool] final_answer
   └─ [Agent] search_agent
      └─ [Tool] web_search
      └─ [Tool] visit_webpage
   └─ [Agent] calculator_agent
      └─ [Tool] calculator
```

#### 7.3.3 性能监控

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class AgentMetrics:
    call_count: int = 0
    total_duration: float = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    errors: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class MonitoredAgent:
    def __init__(self, agent):
        self.agent = agent
        self.metrics = AgentMetrics()
    
    def __call__(self, task: str, **kwargs):
        import time
        start = time.time()
        
        try:
            result = self.agent(task=task, **kwargs)
            
            # 记录成功
            self.metrics.call_count += 1
            self.metrics.total_duration += time.time() - start
            
            # 如果有RunResult，记录token
            if hasattr(result, 'token_usage') and result.token_usage:
                self.metrics.total_input_tokens += result.token_usage.input_tokens
                self.metrics.total_output_tokens += result.token_usage.output_tokens
            
            return result
        except Exception as e:
            self.metrics.errors.append({"task": task, "error": str(e)})
            raise
```

---

## 八、实际案例

### 8.1 研究助手完整实现

```python
"""
研究助手：研究一个主题并生成报告
"""
from smolagents import CodeAgent, ToolCallingAgent, HfApiModel
from smolagents.tools import DuckDuckGoSearchTool, VisitWebpageTool

class ResearchAssistant:
    def __init__(self, model):
        self.model = model
        self._create_agents()
    
    def _create_agents(self):
        # 信息收集子Agent
        self.info_collector = ToolCallingAgent(
            tools=[DuckDuckGoSearchTool(), VisitWebpageTool()],
            model=self.model,
            name="info_collector",
            description="""
            收集指定主题的详细信息。擅长网络搜索、网页内容提取。
            输入：研究主题和具体要求
            输出：结构化的信息收集结果
            """,
            max_steps=8,
            max_tool_threads=4,
        )
        
        # 事实核查子Agent
        self.fact_checker = ToolCallingAgent(
            tools=[DuckDuckGoSearchTool()],
            model=self.model,
            name="fact_checker",
            description="""
            核查信息的真实性和准确性。擅长交叉验证多个来源。
            输入：需要核查的事实陈述
            输出：核查结果和可信度评估
            """,
            max_steps=5,
        )
        
        # Manager Agent
        self.manager = CodeAgent(
            tools=[],
            model=self.model,
            managed_agents=[self.info_collector, self.fact_checker],
            additional_authorized_imports=["json", "re"],
            max_steps=15,
            planning_interval=5,
        )
    
    def research(self, topic: str, depth: str = "standard") -> str:
        """
        执行研究任务
        
        Args:
            topic: 研究主题
            depth: 研究深度 (brief/standard/deep)
        """
        depth_config = {
            "brief": {"sources": 3, "word_count": 500},
            "standard": {"sources": 5, "word_count": 1000},
            "deep": {"sources": 10, "word_count": 2000},
        }
        config = depth_config.get(depth, depth_config["standard"])
        
        prompt = f"""
        研究主题：{topic}
        
        任务要求：
        1. 使用info_collector收集至少{config['sources']}个可靠来源的信息
        2. 对关键数据使用fact_checker进行交叉验证
        3. 生成约{config['word_count']}字的研究报告
        
        报告结构：
        1. 摘要
        2. 背景介绍
        3. 主要发现（分点列出，每点标注来源）
        4. 数据验证结果
        5. 结论与建议
        """
        
        return self.manager.run(prompt)

# 使用示例
if __name__ == "__main__":
    model = HfApiModel()
    assistant = ResearchAssistant(model)
    
    report = assistant.research(
        topic="2024年生成式AI在医疗领域的应用进展",
        depth="deep"
    )
    print(report)
```

### 8.2 数据分析助手完整实现

```python
"""
数据分析助手：多数据源分析
"""
from smolagents import CodeAgent, ToolCallingAgent, HfApiModel
from smolagents.tools import Tool
import pandas as pd

@Tool
def query_database(source: str, query: str) -> str:
    """
    查询数据库，支持多种数据源。
    
    Args:
        source: 数据源名称 (sales_db/user_db/product_db)
        query: SQL查询语句
    
    Returns:
        查询结果CSV格式字符串
    """
    # 实际实现会连接真实数据库
    # 这里返回模拟数据
    mock_data = {
        "sales_db": "date,amount,category\n2024-01,1000,A\n2024-02,1200,A",
        "user_db": "user_id,age,city\n1,25,Beijing\n2,30,Shanghai",
        "product_db": "product_id,name,price\n1,ProductA,100\n2,ProductB,200",
    }
    return mock_data.get(source, "")

class DataAnalysisAssistant:
    def __init__(self, model):
        self.model = model
        self._create_agents()
    
    def _create_agents(self):
        # 数据查询子Agent
        self.query_agent = ToolCallingAgent(
            tools=[query_database],
            model=self.model,
            name="data_querier",
            description="""
            从多个数据源查询数据。支持sales_db、user_db、product_db。
            输入：数据源名称和SQL查询
            输出：CSV格式的查询结果
            """,
            max_steps=5,
        )
        
        # 数据分析Manager
        self.analyzer = CodeAgent(
            tools=[],
            model=self.model,
            managed_agents=[self.query_agent],
            additional_authorized_imports=[
                "pandas", "numpy", "matplotlib.pyplot", 
                "seaborn", "json"
            ],
            max_steps=20,
        )
    
    def analyze(self, task_description: str) -> dict:
        """
        执行数据分析任务
        
        Returns:
            包含分析结果和可视化的字典
        """
        prompt = f"""
        {task_description}
        
        可用数据源：
        - sales_db: 销售数据表，包含date, amount, category字段
        - user_db: 用户数据表，包含user_id, age, city字段
        - product_db: 产品数据表，包含product_id, name, price字段
        
        分析流程：
        1. 使用data_querier获取所需数据
        2. 使用pandas进行数据清洗和处理
        3. 进行统计分析和可视化
        4. 生成分析结论
        
        输出要求：
        - 关键统计指标
        - 趋势分析
        - 生成的图表（保存为文件）
        - 业务建议
        """
        
        return self.analyzer.run(prompt)

# 使用示例
if __name__ == "__main__":
    model = HfApiModel()
    assistant = DataAnalysisAssistant(model)
    
    result = assistant.analyze("""
    分析2024年Q1销售数据：
    1. 从不同品类获取销售数据
    2. 计算月度销售额和增长率
    3. 找出销量最高的品类
    4. 生成销售趋势图
    """)
```

### 8.3 代码优化助手完整实现

```python
"""
代码优化助手：生成+测试+选择最优方案
"""
from smolagents import CodeAgent, ToolCallingAgent, HfApiModel
from smolagents.tools import Tool
import time
import random

@Tool
def benchmark_code(code: str, test_data: str, iterations: int = 3) -> dict:
    """
    测试代码性能
    
    Args:
        code: 要测试的Python代码
        test_data: 测试数据（JSON格式）
        iterations: 测试迭代次数
    
    Returns:
        性能测试结果
    """
    try:
        exec_times = []
        for _ in range(iterations):
            start = time.time()
            # 实际执行代码
            exec(code)
            exec_times.append(time.time() - start)
        
        return {
            "avg_time": sum(exec_times) / len(exec_times),
            "min_time": min(exec_times),
            "max_time": max(exec_times),
            "iterations": iterations,
            "status": "success"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

class CodeOptimizationAssistant:
    def __init__(self, model):
        self.model = model
        self._create_agents()
    
    def _create_agents(self):
        # 性能测试子Agent
        self.benchmark_agent = ToolCallingAgent(
            tools=[benchmark_code],
            model=self.model,
            name="benchmarker",
            description="""
            测试代码性能。执行代码并返回执行时间统计。
            输入：代码字符串、测试数据、迭代次数
            输出：性能指标（平均时间、最小/最大时间）
            """,
            max_steps=5,
        )
        
        # 代码生成和优化Manager
        self.optimizer = CodeAgent(
            tools=[],
            model=self.model,
            managed_agents=[self.benchmark_agent],
            additional_authorized_imports=[
                "time", "random", "statistics",
                "functools", "itertools"
            ],
            max_steps=25,
        )
    
    def optimize(self, problem: str, constraints: dict = None) -> dict:
        """
        优化代码实现
        
        Args:
            problem: 问题描述
            constraints: 约束条件
        
        Returns:
            优化结果，包含多个实现和性能对比
        """
        constraints = constraints or {}
        
        prompt = f"""
        优化问题：{problem}
        
        约束条件：
        {constraints}
        
        任务：
        1. 生成至少3种不同的实现方案
        2. 使用benchmarker测试每种方案的性能
        3. 比较各方案的时间复杂度和空间复杂度
        4. 选择最优方案并解释原因
        
        输出要求：
        - 各方案的代码实现
        - 性能测试结果表格
        - 复杂度分析
        - 最终推荐方案
        """
        
        return self.optimizer.run(prompt)

# 使用示例
if __name__ == "__main__":
    model = HfApiModel()
    assistant = CodeOptimizationAssistant(model)
    
    result = assistant.optimize(
        problem="实现一个高效的数组去重函数，处理百万级数据",
        constraints={
            "memory": "限制内存使用不超过100MB",
            "time": "处理100万数据应在1秒内完成"
        }
    )
    print(result)
```

---

## 九、局限性

### 9.1 当前设计的限制

#### 9.1.1 不支持远程执行器与子Agent共存

源码位置：agents.py:1608-1609

```python
if self.executor_type != "local":
    if self.managed_agents:
        raise Exception("Managed agents are not yet supported with remote code execution.")
```

这意味着使用 E2B、Docker、Modal 等远程执行器时，无法使用子Agent功能。

#### 9.1.2 子Agent调用无状态保持

每次调用子Agent都是独立的 `run()` 调用，子Agent内部状态不会跨调用保持：

```python
# 第一次调用
result1 = search_agent(task="搜索A")  # 子Agent记忆包含搜索A的过程

# 第二次调用
result2 = search_agent(task="搜索B")  # 子Agent记忆重置，不知道搜索A
```

#### 9.1.3 不支持并行调用多个子Agent

Manager 一次只能调用一个子Agent，无法并行执行多个子Agent：

```python
# 无法实现这种并行调用
# result1 = search_agent1(task="...")  # 需要等待
# result2 = search_agent2(task="...")  # 需要等待
```

#### 9.1.4 监控数据分散

父Agent的 `RunResult` 不包含子Agent的 TokenUsage 和 Timing 信息，需要手动聚合：

```python
# 只能获取Manager自身的指标
result = manager.run("task")
print(result.token_usage)  # 仅Manager的token

# 子Agent的指标需要单独获取
print(search_agent.metrics)  # 需要额外实现
```

### 9.2 不适用场景

| 场景 | 原因 | 替代方案 |
|------|------|----------|
| 需要子Agent间直接通信 | 子Agent彼此隔离 | 使用共享内存或消息队列 |
| 需要长期状态保持 | 每次调用独立 | 在外部存储状态 |
| 需要复杂工作流编排 | 层级架构限制 | 使用专用工作流引擎 |
| 高频低延迟调用 | 每次调用开销较大 | 合并为单次调用 |

### 9.3 未来改进方向

1. **支持远程执行器**：解除 remote executor 与 managed_agents 的互斥限制
2. **状态持久化**：支持子Agent跨调用的状态保持
3. **并行子Agent调用**：支持 Manager 同时调用多个子Agent
4. **统一监控**：自动聚合父子Agent的监控指标
5. **Agent间通信**：支持子Agent之间的消息传递

---

## 十、对我们项目的启示

### 10.1 AI数据分析系统中的应用场景

#### 10.1.1 推荐架构设计

基于 smolagents 的协作模式，我们的 AI数据分析系统 可以采用以下架构：

```
Orchestrator Agent (CodeAgent)
    ├── 规划模块：分析用户需求，制定分析计划
    ├── 执行模块：执行复杂数据处理代码
    └── 子Agent调度
            │
            ├── DataQueryAgent (ToolCallingAgent)
            │       ├── SQLQueryTool
            │       ├── APICallTool
            │       └── FileReaderTool
            │
            ├── VisualizationAgent (ToolCallingAgent)
            │       ├── ChartTool
            │       └── DashboardTool
            │
            ├── ReportAgent (ToolCallingAgent)
            │       ├── DocumentTool
            │       └── ExportTool
            │
            └── ValidationAgent (ToolCallingAgent)
                    ├── SchemaValidator
                    └── DataQualityChecker
```

#### 10.1.2 角色分工

| Agent | 类型 | 职责 | 工具示例 |
|-------|------|------|----------|
| Orchestrator | CodeAgent | 分析需求、制定计划、整合结果 | pandas, numpy |
| DataQueryAgent | ToolCallingAgent | 数据查询和获取 | SQLQuery, APICall |
| VisualizationAgent | ToolCallingAgent | 生成图表和可视化 | matplotlib, plotly |
| ReportAgent | ToolCallingAgent | 生成报告和文档 | docx, pdf export |
| ValidationAgent | ToolCallingAgent | 数据验证和质量检查 | schema validation |

### 10.2 实现建议

#### 10.2.1 封装数据分析专用子Agent

```python
class DataQueryAgent(ToolCallingAgent):
    """专门用于数据查询的子Agent"""
    
    def __init__(self, model, data_sources: dict):
        tools = [
            SQLQueryTool(data_sources),
            APICallTool(),
            FileReaderTool(),
        ]
        super().__init__(
            tools=tools,
            model=model,
            name="data_querier",
            description="""
            从多种数据源查询数据。支持：
            - SQL数据库查询
            - REST API调用
            - 文件读取（CSV, Excel, JSON）
            
            输入：数据源标识和查询条件
            输出：结构化数据（DataFrame格式）
            """,
            max_steps=8,
            max_tool_threads=4,
        )

class VisualizationAgent(ToolCallingAgent):
    """专门用于可视化的子Agent"""
    
    def __init__(self, model):
        tools = [
            ChartTool(),
            DashboardTool(),
            ExportImageTool(),
        ]
        super().__init__(
            tools=tools,
            model=model,
            name="visualizer",
            description="""
            生成数据可视化图表。支持：
            - 折线图、柱状图、饼图
            - 散点图、热力图
            - 仪表板布局
            
            输入：数据和图表类型要求
            输出：图表文件路径或base64编码
            """,
            max_steps=6,
        )
```

#### 10.2.2 状态管理层

由于 smolagents 的子Agent调用是独立的，我们需要在外部实现状态管理：

```python
class AnalysisContext:
    """分析上下文管理"""
    
    def __init__(self):
        self.data_cache = {}
        self.query_history = []
        self.intermediate_results = {}
    
    def cache_data(self, key: str, data):
        """缓存数据供多个子Agent使用"""
        self.data_cache[key] = data
    
    def get_data(self, key: str):
        """获取缓存数据"""
        return self.data_cache.get(key)
    
    def record_query(self, agent_name: str, query: str, result: str):
        """记录查询历史，避免重复查询"""
        self.query_history.append({
            "agent": agent_name,
            "query": query,
            "result_summary": result[:100]  # 摘要
        })

# 在Manager中使用
context = AnalysisContext()

# 传递上下文给子Agent
result = query_agent(
    task="分析销售数据",
    additional_args={
        "context": context,
        "cached_data": context.data_cache
    }
)
```

#### 10.2.3 统一监控

```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class AnalysisMetrics:
    """完整分析过程的监控指标"""
    
    # Manager指标
    manager_tokens: TokenUsage
    manager_duration: float
    
    # 子Agent指标
    agent_metrics: Dict[str, dict]  # agent_name -> metrics
    
    # 整体指标
    total_tokens: int
    total_duration: float
    tool_calls: List[dict]
    
    def generate_report(self) -> str:
        """生成性能报告"""
        report = f"""
        # 分析执行报告
        
        ## 总体指标
        - 总耗时: {self.total_duration:.2f}秒
        - 总Token: {self.total_tokens}
        
        ## 子Agent调用
        """
        for name, metrics in self.agent_metrics.items():
            report += f"""
        ### {name}
        - 调用次数: {metrics['calls']}
        - 平均耗时: {metrics['avg_duration']:.2f}秒
        - Token消耗: {metrics['tokens']}
            """
        return report

class MonitoredOrchestrator(CodeAgent):
    """带监控的Orchestrator"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.metrics = AnalysisMetrics(
            manager_tokens=TokenUsage(0, 0),
            manager_duration=0,
            agent_metrics={},
            total_tokens=0,
            total_duration=0,
            tool_calls=[]
        )
    
    def run(self, task: str, **kwargs):
        import time
        start = time.time()
        
        result = super().run(task, return_full_result=True, **kwargs)
        
        # 记录指标
        self.metrics.manager_duration = time.time() - start
        if result.token_usage:
            self.metrics.manager_tokens = result.token_usage
        
        # 聚合子Agent指标
        for name, agent in self.managed_agents.items():
            if hasattr(agent, '_metrics'):
                self.metrics.agent_metrics[name] = agent._metrics
        
        return result
```

### 10.3 与现有技术栈的集成

#### 10.3.1 与 SQL 分析模块集成

```python
# 将我们的SQL分析能力封装为子Agent
from our_project.sql_analyzer import SQLAnalyzer

@Tool
def analyze_with_sql(query: str, schema: dict) -> dict:
    """使用我们的SQL分析器进行分析"""
    analyzer = SQLAnalyzer()
    return analyzer.analyze(query, schema)

sql_agent = ToolCallingAgent(
    tools=[analyze_with_sql],
    model=model,
    name="sql_analyzer",
    description="使用专业SQL分析器进行数据库分析",
)
```

#### 10.3.2 与可视化模块集成

```python
from our_project.visualization import ChartGenerator

@Tool
def generate_chart(data: dict, chart_type: str) -> str:
    """使用我们的图表生成器"""
    generator = ChartGenerator()
    return generator.create(data, chart_type)

viz_agent = ToolCallingAgent(
    tools=[generate_chart],
    model=model,
    name="chart_generator",
    description="生成专业数据可视化图表",
)
```

### 10.4 总结

smolagents 的 CodeAgent 与 ToolCallingAgent 协作模式为我们提供了以下启示：

1. **分工明确**：复杂推理和工具执行分离，各自发挥优势
2. **统一接口**：子Agent通过 Tool-like 接口被调用，降低系统复杂度
3. **灵活组合**：任意 Agent 可以既是 Manager 又是 Managed Agent
4. **Prompt驱动**：通过精心设计的 Prompt 模板指导协作流程

在我们的 AI数据分析系统 中，可以借鉴这种架构：
- 使用 CodeAgent 作为 Orchestrator 负责分析流程规划
- 使用多个 ToolCallingAgent 作为专项工具执行者
- 在外部实现状态管理和监控，弥补 smolagents 的局限

这种模式能够有效平衡系统的灵活性和可维护性，适合需要复杂推理和多工具协作的数据分析场景。

---

## 参考文档

- [[01-smolagents-Agent架构深度分析]]
- [[06-smolagents-多Agent系统深度分析]]
- [[25-smolagents-CodeAgent与ToolCallingAgent深度对比]]

## 相关图表

- ![smolagents-CodeAgent与ToolCallingAgent协作架构图.svg](graphviz/smolagents-CodeAgent与ToolCallingAgent协作架构图.svg)
- ![smolagents-协作流程时序图.svg](graphviz/smolagents-协作流程时序图.svg)
- ![smolagents-适用场景决策图.svg](graphviz/smolagents-适用场景决策图.svg)
