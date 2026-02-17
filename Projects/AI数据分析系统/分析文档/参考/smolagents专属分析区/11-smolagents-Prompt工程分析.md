# smolagents Prompt工程分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/prompts/*.yaml, agents.py

## 一、Prompt模板结构

smolagents 使用 TypedDict 定义了一套完整的 Prompt 模板结构，位于 [[agents.py]] 文件中。

### 1.1 核心类型定义

```python
class PlanningPromptTemplate(TypedDict):
    """规划阶段的 Prompt 模板"""
    initial_plan: str                    # 初始规划 Prompt
    update_plan_pre_messages: str        # 更新规划前置消息
    update_plan_post_messages: str       # 更新规划后置消息

class ManagedAgentPromptTemplate(TypedDict):
    """被管理 Agent 的 Prompt 模板"""
    task: str      # 任务 Prompt
    report: str    # 报告 Prompt

class FinalAnswerPromptTemplate(TypedDict):
    """最终答案的 Prompt 模板"""
    pre_messages: str    # 前置消息
    post_messages: str   # 后置消息

class PromptTemplates(TypedDict):
    """完整的 Agent Prompt 模板集合"""
    system_prompt: str
    planning: PlanningPromptTemplate
    managed_agent: ManagedAgentPromptTemplate
    final_answer: FinalAnswerPromptTemplate
```

### 1.2 结构特点

- **分层设计**: 将 Prompt 按功能划分为系统提示、规划、子 Agent 管理和最终答案四个模块
- **可替换性**: 通过 `prompt_templates` 参数允许用户完全自定义 Prompt
- **完整性校验**: 初始化时会检查所有必需的子键是否存在

### 1.3 模板加载方式

```python
# ToolCallingAgent 加载方式
prompt_templates = yaml.safe_load(
    importlib.resources.files("smolagents.prompts").joinpath("toolcalling_agent.yaml").read_text()
)

# CodeAgent 加载方式
prompt_templates = yaml.safe_load(
    importlib.resources.files("smolagents.prompts").joinpath("code_agent.yaml").read_text()
)
```

---

## 二、CodeAgent Prompt详解

CodeAgent 使用 YAML 文件 [[code_agent.yaml]] 定义 Prompt 模板，核心特点是让 LLM 以 Python 代码形式调用工具。

### 2.1 System Prompt 核心结构

系统 Prompt 采用"角色定义 + 工作流说明 + 示例 + 工具列表 + 规则"的五段式结构：

**第一段: 角色与能力定义**
```
You are an expert assistant who can solve any task using code blobs.
```

**第二段: 工作流说明**
- 采用 Thought -> Code -> Observation 的循环模式
- Thought 序列用于解释推理过程
- Code 序列使用特定标签包裹
- Observation 来自代码执行结果

**第三段: 多示例教学**
包含 7 个精心设计的示例，覆盖以下场景：
1. 工具链式调用: document_qa -> image_generator
2. 纯 Python 计算: 数学运算
3. 变量传递: 使用 additional_args 传入的参数
4. 错误重试: 搜索查询失败后调整策略
5. 循环处理: 遍历多个城市查询数据
6. 数据验证: 交叉验证 Wikipedia 和 Web 搜索结果
7. 多步骤推理: 复杂问题的逐步解决

**第四段: 动态工具列表**
通过 Jinja2 循环动态注入可用工具：
```yaml
{%- for tool in tools.values() %}
{{ tool.to_code_prompt() }}
{% endfor %}
```

**第五段: 执行规则**
共 11 条规则，核心包括：
- 规则 1: 必须提供 Thought 和 Code 序列
- 规则 2: 只能使用已定义的变量
- 规则 3: 禁止以字典形式传递参数
- 规则 4-5: 区分有无 JSON Schema 的工具调用策略
- 规则 6: 禁止重复调用相同参数的工具
- 规则 9: 限制只能使用授权的 import
- 规则 10: 状态在代码执行间持久化

### 2.2 Planning Prompt 设计

Planning 分为初始规划和计划更新两个阶段。

**初始规划 Prompt 结构**:
```
1. Facts survey
   1.1. Facts given in the task
   1.2. Facts to look up
   1.3. Facts to derive

2. Plan
   - 步骤 1
   - 步骤 2
   ...
   <end_plan>
```

**计划更新 Prompt 结构**:
```
1. Updated facts survey
   1.1. Facts given in the task
   1.2. Facts that we have learned
   1.3. Facts still to look up
   1.4. Facts still to derive

2. Plan
   - 更新后的步骤
   ...
   <end_plan>
```

关键设计点：
- 使用 `<end_plan>` 作为停止序列，控制输出长度
- 计划更新时引入 `remaining_steps` 变量，让模型感知剩余步数
- 禁止详细描述单个工具调用，只关注高层步骤

### 2.3 Managed Agent Prompt

子 Agent 的 Prompt 强制要求三部分输出结构：
```
### 1. Task outcome (short version):
### 2. Task outcome (extremely detailed version):
### 3. Additional context (if relevant):
```

这种设计确保子 Agent 返回的信息既有摘要又有详细内容，便于父 Agent 决策。

### 2.4 代码块标签配置

CodeAgent 支持自定义代码块标签，默认为 `<code>` 和 `</code>`，也可配置为 Markdown 格式：

```python
# Markdown 格式
code_block_tags = ("```python", "```")

# 自定义标签
code_block_tags = ("<execute>", "</execute>")
```

标签选择会影响：
1. System Prompt 中的示例格式
2. 代码解析时的正则匹配
3. 停止序列的设置

---

## 三、ToolCallingAgent Prompt详解

ToolCallingAgent 使用 [[toolcalling_agent.yaml]]，采用 JSON 格式的工具调用。

### 3.1 与 CodeAgent 的核心差异

| 维度 | CodeAgent | ToolCallingAgent |
|------|-----------|------------------|
| 调用格式 | Python 代码 | JSON 对象 |
| 执行方式 | Python 解释器 | 直接函数调用 |
| 灵活性 | 支持代码逻辑 | 单一工具调用 |
| 并行能力 | 顺序执行 | 支持并行 |
| 适用模型 | 通用模型 | 原生支持 tool calling 的模型 |

### 3.2 System Prompt 结构

ToolCallingAgent 的 System Prompt 更简洁：

**第一段: 角色定义**
```
You are an expert assistant who can solve any task using tool calls.
```

**第二段: Action/Observation 模式**
```
Action -> Observation 可以重复 N 次
Observation 始终是字符串格式
```

**第三段: 工具调用格式**
```json
{
  "name": "tool_name",
  "arguments": {"arg1": "value1"}
}
```

**第四段: 示例**
包含 3 个示例，展示：
1. 简单工具调用链
2. Python 解释器调用
3. 并行搜索对比

**第五段: 规则**
仅 4 条核心规则：
1. 必须提供工具调用
2. 使用值而非变量名作为参数
3. 只在需要时调用工具
4. 禁止重复调用

### 3.3 工具描述格式

ToolCallingAgent 使用 `to_tool_calling_prompt` 方法生成工具描述：

```yaml
{%- for tool in tools.values() %}
- {{ tool.to_tool_calling_prompt() }}
{%- endfor %}
```

相比 CodeAgent 的 Python 函数签名格式，ToolCallingAgent 使用列表形式描述工具，更适合 JSON 调用风格。

### 3.4 并行工具调用支持

ToolCallingAgent 通过 `max_tool_threads` 参数支持并行执行：

```python
with ThreadPoolExecutor(self.max_tool_threads) as executor:
    futures = []
    for tool_call in parallel_calls.values():
        ctx = copy_context()
        futures.append(executor.submit(ctx.run, process_single_tool_call, tool_call))
```

这要求模型在一次响应中返回多个 tool_calls，适用于需要同时获取多个独立数据的场景。

---

## 四、Prompt变量替换

smolagents 使用 Jinja2 作为模板引擎，实现动态 Prompt 生成。

### 4.1 核心函数

```python
from jinja2 import StrictUndefined, Template

def populate_template(template: str, variables: dict[str, Any]) -> str:
    compiled_template = Template(template, undefined=StrictUndefined)
    try:
        return compiled_template.render(**variables)
    except Exception as e:
        raise Exception(f"Error during jinja template rendering: {type(e).__name__}: {e}")
```

使用 `StrictUndefined` 确保所有变量必须被正确定义，避免静默使用空值。

### 4.2 变量注入时机

**系统 Prompt 初始化**:
```python
def initialize_system_prompt(self) -> str:
    return populate_template(
        self.prompt_templates["system_prompt"],
        variables={
            "tools": self.tools,
            "managed_agents": self.managed_agents,
            "authorized_imports": str(self.authorized_imports),
            "custom_instructions": self.instructions,
            "code_block_opening_tag": self.code_block_tags[0],
            "code_block_closing_tag": self.code_block_tags[1],
        },
    )
```

**规划阶段**:
```python
# 初始规划
populate_template(
    self.prompt_templates["planning"]["initial_plan"],
    variables={"task": task, "tools": self.tools, "managed_agents": self.managed_agents}
)

# 计划更新
populate_template(
    self.prompt_templates["planning"]["update_plan_post_messages"],
    variables={
        "task": task,
        "tools": self.tools,
        "managed_agents": self.managed_agents,
        "remaining_steps": self.max_steps - step,
    }
)
```

**子 Agent 调用**:
```python
full_task = populate_template(
    self.prompt_templates["managed_agent"]["task"],
    variables=dict(name=self.name, task=task)
)
```

### 4.3 Jinja2 语法应用

**条件渲染**:
```yaml
{%- if managed_agents and managed_agents.values() | list %}
You can also give tasks to team members...
{%- endif %}
```

**循环渲染**:
```yaml
{%- for tool in tools.values() %}
{{ tool.to_code_prompt() }}
{% endfor %}
```

**变量过滤**:
```yaml
{{authorized_imports}}
```

### 4.4 动态内容生成

工具描述通过工具类的方法动态生成：

```python
# CodeAgent 使用 to_code_prompt
def to_code_prompt(self) -> str:
    """生成 Python 函数签名格式的描述"""
    return f"""def {self.name}({self._generate_signature()}) -> {self.output_type}:
    \"\"\"{self.description}\"\"\""""

# ToolCallingAgent 使用 to_tool_calling_prompt  
def to_tool_calling_prompt(self) -> str:
    """生成列表项格式的描述"""
    return f"{self.name}: {self.description}\n  Inputs: {self.inputs}\n  Output: {self.output_type}"
```

---

## 五、Prompt优化技巧

通过分析 smolagents 的 Prompt 设计，可以总结出以下优化技巧。

### 5.1 减少幻觉的策略

**策略 1: 强制输出格式**
```
You should first explain your reasoning... then in the Code sequence you should write the code...
```

通过明确要求分步输出，约束模型的响应结构。

**策略 2: 详尽的示例**
smolagents 提供了 7 个 CodeAgent 示例和 3 个 ToolCallingAgent 示例，覆盖：
- 正常执行流程
- 错误处理流程
- 多步骤推理
- 变量传递
- 循环处理

**策略 3: 明确的边界约束**
```
Do not skip steps, do not add any superfluous steps.
Only write the high-level plan, DO NOT DETAIL INDIVIDUAL TOOL CALLS.
```

使用明确的否定指令，限制模型的发散行为。

**策略 4: 状态变量校验**
```
Use only variables that you have defined!
Don't name any new variable with the same name as a tool...
Never create any notional variables in our code...
```

通过规则约束，防止模型引用不存在的变量。

### 5.2 代码生成指导技巧

**技巧 1: 代码块标记**
使用特定的开始和结束标签，便于解析：
```
The code sequence must be opened with '{{code_block_opening_tag}}', 
and closed with '{{code_block_closing_tag}}'.
```

**技巧 2: 区分工具类型**
```
For tools WITHOUT JSON output schema: Take care to not chain too many sequential tool calls...
For tools WITH JSON output schema: You can confidently chain multiple tool calls...
```

根据工具返回格式给予不同的编码建议。

**技巧 3: 执行日志利用**
```
During each intermediate step, you can use 'print()' to save whatever important information...
These print outputs will then appear in the 'Observation:' field...
```

指导模型使用 print 传递中间结果。

**技巧 4: 状态持久化提示**
```
The state persists between code executions: so if in one step you've created variables or imported modules, these will all persist.
```

明确告知状态持久化特性，避免重复导入。

### 5.3 错误重试处理

**方式 1: 自动重试机制**
```python
except AgentError as e:
    # 其他 AgentError 类型由模型导致，记录并继续迭代
    action_step.error = e
```

错误会被记录到 memory 中，作为下一步的上下文。

**方式 2: 计划重新生成**
```
If the previous tries so far have met some success, your updated plan can build on these results.
If you are stalled, you can make a completely new plan starting from scratch.
```

支持基于历史执行结果更新计划。

**方式 3: 最终答案兜底**
```python
def _handle_max_steps_reached(self, task: str) -> Any:
    final_answer = self.provide_final_answer(task)
```

当达到最大步数时，强制生成最终答案。

### 5.4 停止序列优化

```python
stop_sequences = ["Observation:", "Calling tools:"]
if self.code_block_tags[1] not in self.code_block_tags[0]:
    stop_sequences.append(self.code_block_tags[1])
```

通过设置停止序列，在生成完成时及时截断，减少不必要的 token 消耗。

### 5.5 结构化输出增强

CodeAgent 支持 `use_structured_outputs_internally` 模式：

```python
if self._use_structured_outputs_internally:
    additional_args["response_format"] = CODEAGENT_RESPONSE_FORMAT
```

使用 JSON Schema 约束模型输出，提高代码提取的准确性。

---

## 六、对我们项目的启示

### 6.1 Prompt 模板化设计

**建议**: 采用 smolagents 的分层模板结构

```python
# 在我们的 AI数据分析系统 中可设计
class AnalysisPromptTemplates(TypedDict):
    system_prompt: str           # 系统角色定义
    data_understanding: str      # 数据理解阶段
    analysis_planning: str       # 分析规划阶段  
    code_generation: str         # 代码生成阶段
    result_interpretation: str   # 结果解读阶段
```

### 6.2 多示例教学策略

**建议**: 为数据分析场景准备标准示例

```yaml
examples:
  - name: "数据清洗流程"
    description: "处理缺失值和异常值的标准流程"
  - name: "统计检验"
    description: "选择并执行适当的统计检验"
  - name: "可视化生成"
    description: "根据数据类型选择合适的图表"
```

### 6.3 工具调用规范

**建议**: 明确区分代码执行型工具和 API 调用型工具

```python
# 代码执行型 - 使用 CodeAgent 模式
python_executor.run(code)

# API 调用型 - 使用 ToolCallingAgent 模式  
api_client.call(endpoint, params)
```

### 6.4 状态管理提示

**建议**: 在 Prompt 中明确数据流状态

```
数据分析过程中，以下状态会被持久化：
- df: 当前处理的数据框
- analysis_results: 已完成的分析结果
- visualizations: 已生成的图表列表
```

### 6.5 错误恢复机制

**建议**: 实现类似 smolagents 的多层错误处理

```python
class DataAnalysisErrorHandler:
    def handle_code_error(self, error, memory):
        # 记录错误到上下文
        memory.add_error(error)
        # 提供修复建议
        return self.generate_fix_suggestion(error)
    
    def handle_max_steps(self, task, memory):
        # 基于已有结果生成结论
        return self.synthesize_partial_results(memory)
```

### 6.6 动态变量注入

**建议**: 使用 Jinja2 实现灵活的 Prompt 构建

```python
def build_analysis_prompt(template, context):
    """根据数据特征动态构建分析 Prompt"""
    variables = {
        "data_shape": context.df.shape,
        "data_types": context.df.dtypes.to_dict(),
        "available_tools": context.tools,
        "analysis_goal": context.goal,
    }
    return populate_template(template, variables)
```

### 6.7 可复用的设计模式

从 smolagents 可以借鉴以下设计模式到我们的项目：

| 模式 | 应用场景 | 实现方式 |
|------|----------|----------|
| ReAct 循环 | 多步骤数据分析 | Thought -> Code -> Observation |
| 规划-执行分离 | 复杂分析任务 | 先生成计划，再逐步执行 |
| 记忆管理 | 长会话分析 | 按步骤存储执行历史 |
| 工具注册 | 扩展分析能力 | 动态注入可用工具描述 |
| 停止序列 | 控制生成长度 | 设置代码/输出结束标记 |

---

## 参考链接

- [[code_agent.yaml]] - CodeAgent Prompt 模板定义
- [[toolcalling_agent.yaml]] - ToolCallingAgent Prompt 模板定义  
- [[agents.py]] - Agent 实现和 Prompt 渲染逻辑
- [[10-smolagents-核心架构分析]] - smolagents 架构分析
- [[12-smolagents-工具系统设计]] - 工具系统设计分析
