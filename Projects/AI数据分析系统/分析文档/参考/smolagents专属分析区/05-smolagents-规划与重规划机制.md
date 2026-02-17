# smolagents 规划与重规划机制深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/agents.py, memory.py, prompts/code_agent.yaml

## 一、PlanningStep设计

### 1.1 数据类定义

[[memory.py]] 第153-184行定义了 PlanningStep 的核心结构：

```python
@dataclass
class PlanningStep(MemoryStep):
    model_input_messages: list[ChatMessage]
    model_output_message: ChatMessage
    plan: str
    timing: Timing
    token_usage: TokenUsage | None = None
```

与 ActionStep 相比，PlanningStep 的结构更加精简：

| 字段 | PlanningStep | ActionStep |
|------|-------------|------------|
| 输入消息 | model_input_messages | model_input_messages |
| 输出消息 | model_output_message | model_output_message |
| 核心内容 | plan 字符串 | code_action, observations |
| 工具调用 | 无 | tool_calls |
| 错误处理 | 无 | error |
| 执行结果 | 无 | action_output |

### 1.2 关键设计：summary_mode过滤

[[memory.py]] 第174-183行的 to_messages 方法实现了关键过滤逻辑：

```python
def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
    if summary_mode:
        return []
    return [
        ChatMessage(role=MessageRole.ASSISTANT, content=[{"type": "text", "text": self.plan.strip()}]),
        ChatMessage(
            role=MessageRole.USER, content=[{"type": "text", "text": "Now proceed and carry out this plan."}]
        ),
    ]
```

**设计意图**：当 summary_mode=True 时，PlanningStep 返回空列表，这意味着历史规划内容不会传入下一次规划生成。这避免了旧规划对新规划的干扰，让模型每次都能基于当前执行状态重新评估。

### 1.3 规划内容的格式

[[agents.py]] 第678-680行和第736-738行展示了规划的最终格式：

```python
# 初始规划格式
plan = textwrap.dedent(
    f"""Here are the facts I know and the plan of action that I will follow to solve the task:\n```\n{plan_message_content}\n```"""
)

# 更新规划格式
plan = textwrap.dedent(
    f"""I still need to solve the task I was given:\n```\n{self.task}\n```\n\nHere are the facts I know and my new/updated plan of action to solve the task:\n```\n{plan_message_content}\n```"""
)
```

规划被包装为 Markdown 代码块，便于在日志中清晰展示。

## 二、planning_interval机制

### 2.1 参数定义

[[agents.py]] 第305行在 MultiStepAgent.__init__ 中定义：

```python
planning_interval: int | None = None,
```

该参数控制规划触发的频率：
- None：禁用规划功能
- 1：每一步都进行规划
- N：每 N 步进行一次规划

### 2.2 触发逻辑

[[agents.py]] 第549-567行实现了规划触发判断：

```python
# Run a planning step if scheduled
if self.planning_interval is not None and (
    self.step_number == 1 or (self.step_number - 1) % self.planning_interval == 0
):
    planning_start_time = time.time()
    planning_step = None
    for element in self._generate_planning_step(
        task, is_first_step=len(self.memory.steps) == 1, step=self.step_number
    ):
        yield element
        planning_step = element
    assert isinstance(planning_step, PlanningStep)
    planning_end_time = time.time()
    planning_step.timing = Timing(
        start_time=planning_start_time,
        end_time=planning_end_time,
    )
    self._finalize_step(planning_step)
    self.memory.steps.append(planning_step)
```

**触发条件分析**：

| step_number | planning_interval=2 | planning_interval=3 | 说明 |
|-------------|---------------------|---------------------|------|
| 1 | 触发 | 触发 | 初始规划必须执行 |
| 2 | 不触发 | 不触发 | - |
| 3 | 触发 | 不触发 | 3-1=2，2%2=0，触发 |
| 4 | 不触发 | 触发 | 4-1=3，3%3=0，触发 |
| 5 | 触发 | 不触发 | 5-1=4，4%2=0，触发 |

### 2.3 重规划的本质

重规划并非条件触发，而是**时间触发**。无论任务进展如何，只要满足 planning_interval 的间隔条件，就会重新生成规划。这种设计的优缺点：

**优点**：
- 实现简单，无需复杂的成功/失败判断
- 确保模型定期回顾整体目标，防止陷入局部最优
- 适应长任务中环境变化的情况

**缺点**：
- 可能在不必要时进行重规划，增加 token 消耗
- 无法针对特定错误场景立即重规划

## 三、规划生成流程

### 3.1 _generate_planning_step方法全貌

[[agents.py]] 第639-747行实现了完整的规划生成逻辑：

```python
def _generate_planning_step(
    self, task, is_first_step: bool, step: int
) -> Generator[ChatMessageStreamDelta | PlanningStep]:
```

该方法返回一个生成器，支持流式输出规划内容。

### 3.2 初始规划 vs 更新规划

| 阶段 | is_first_step | 核心差异 |
|------|---------------|----------|
| 初始规划 | True | 直接使用任务描述，无需历史上下文 |
| 更新规划 | False | 需要 summary_mode 提取执行历史，重新评估 |

### 3.3 初始规划流程

[[agents.py]] 第643-680行：

```python
if is_first_step:
    input_messages = [
        ChatMessage(
            role=MessageRole.USER,
            content=[
                {
                    "type": "text",
                    "text": populate_template(
                        self.prompt_templates["planning"]["initial_plan"],
                        variables={"task": task, "tools": self.tools, "managed_agents": self.managed_agents},
                    ),
                }
            ],
        )
    ]
```

输入消息结构：
- role: USER
- content: 填充后的 initial_plan 模板

### 3.4 更新规划流程

[[agents.py]] 第681-738行展示了更新规划的核心逻辑：

```python
# Summary mode removes the system prompt and previous planning messages output by the model.
# Removing previous planning messages avoids influencing too much the new plan.
memory_messages = self.write_memory_to_messages(summary_mode=True)
plan_update_pre = ChatMessage(
    role=MessageRole.SYSTEM,
    content=[...],  # update_plan_pre_messages 模板
)
plan_update_post = ChatMessage(
    role=MessageRole.USER,
    content=[...],  # update_plan_post_messages 模板，包含 remaining_steps
)
input_messages = [plan_update_pre] + memory_messages + [plan_update_post]
```

**关键设计**：
1. summary_mode=True 过滤掉系统提示和历史规划消息
2. 使用 SYSTEM + 历史消息 + USER 的三段式结构
3. remaining_steps 变量提醒模型剩余步数限制

### 3.5 summary_mode的作用机制

[[agents.py]] 第758-770行的 write_memory_to_messages 方法：

```python
def write_memory_to_messages(
    self,
    summary_mode: bool = False,
) -> list[ChatMessage]:
    messages = self.memory.system_prompt.to_messages(summary_mode=summary_mode)
    for memory_step in self.memory.steps:
        messages.extend(memory_step.to_messages(summary_mode=summary_mode))
    return messages
```

summary_mode 的传播路径：
1. write_memory_to_messages 传递给每个 memory_step
2. SystemPromptStep.to_messages(summary_mode=True) 返回空列表
3. PlanningStep.to_messages(summary_mode=True) 返回空列表
4. ActionStep.to_messages 不受 summary_mode 影响

**结果**：更新规划时，模型看到的历史是：
- 无系统提示
- 无历史规划内容
- 保留所有 ActionStep 的执行记录

## 四、Prompt工程

### 4.1 PlanningPromptTemplate结构

[[agents.py]] 第125-138行定义了模板结构：

```python
class PlanningPromptTemplate(TypedDict):
    initial_plan: str
    update_plan_pre_messages: str
    update_plan_post_messages: str
```

### 4.2 初始规划Prompt

[[code_agent.yaml]] 第176-231行：

```yaml
initial_plan: |-
  You are a world expert at analyzing a situation to derive facts, and plan 
  accordingly towards solving a task.
  Below I will present you a task. You will need to:
  1. build a survey of facts known or needed to solve the task, then
  2. make a plan of action to solve the task.

  ## 1. Facts survey
  You will build a comprehensive preparatory survey of which facts we have at 
  our disposal and which ones we still need.
  These "facts" will typically be specific names, dates, values, etc. 
  Your answer should use the below headings:

  ### 1.1. Facts given in the task
  List here the specific facts given in the task that could help you 
  (there might be nothing here).

  ### 1.2. Facts to look up
  List here any facts that we may need to look up.
  Also list where to find each of these, for instance a website, a file... 
  - maybe the task contains some sources that you should re-use here.

  ### 1.3. Facts to derive
  List here anything that we want to derive from the above by logical 
  reasoning, for instance computation or simulation.

  Don't make any assumptions. For each item, provide a thorough reasoning. 
  Do not add anything else on top of three headings above.

  ## 2. Plan
  Then for the given task, develop a step-by-step high-level plan taking into 
  account the above inputs and list of facts.
  This plan should involve individual tasks based on the available tools, 
  that if executed correctly will yield the correct answer.
  Do not skip steps, do not add any superfluous steps. 
  Only write the high-level plan, DO NOT DETAIL INDIVIDUAL TOOL CALLS.
  After writing the final step of the plan, write the '<end_plan>' tag 
  and stop there.
```

**核心要素**：
1. **事实调查**：显式分离已知事实、待查事实、推导事实
2. **分层结构**：1.1 / 1.2 / 1.3 的强制分类
3. **高层规划**：强调不写具体工具调用，只写步骤
4. **终止标记**：<end_plan> 标签控制生成停止

### 4.3 更新规划Prompt

[[code_agent.yaml]] 第232-245行定义前置消息：

```yaml
update_plan_pre_messages: |-
  You are a world expert at analyzing a situation, and plan accordingly 
  towards solving a task.
  You have been given the following task:
  ```
  {{task}}
  ```

  Below you will find a history of attempts made to solve this task.
  You will first have to produce a survey of known and unknown facts, 
  then propose a step-by-step high-level plan to solve the task.
  If the previous tries so far have met some success, your updated plan 
  can build on these results.
  If you are stalled, you can make a completely new plan starting from scratch.
```

第245-260行定义后置消息：

```yaml
update_plan_post_messages: |-
  Now write your updated facts below, taking into account the above history:

  ## 1. Updated facts survey
  ### 1.1. Facts given in the task
  ### 1.2. Facts that we have learned
  ### 1.3. Facts still to look up
  ### 1.4. Facts still to derive

  Then write a step-by-step high-level plan to solve the task above.

  ## 2. Plan
  ### 2.1. ...
  Etc.

  This plan should involve individual tasks based on the available tools, 
  that if executed correctly will yield the correct answer.
  Beware that you have {remaining_steps} steps remaining.
  Do not skip steps, do not add any superfluous steps. 
  Only write the high-level plan, DO NOT DETAIL INDIVIDUAL TOOL CALLS.
  After writing the final step of the plan, write the '<end_plan>' tag 
  and stop there.
```

**设计演进**：

| 维度 | 初始规划 | 更新规划 |
|------|----------|----------|
| 事实分类 | 3类 | 4类，增加已学习的事实 |
| 灵活性 | 从零开始 | 可基于已有结果或完全重来 |
| 约束提醒 | 无 | 明确提醒剩余步数 |

### 4.4 Prompt中的工具展示

初始规划和更新规划都在 prompt 中动态注入可用工具：

工具展示模板（在规划 prompt 中动态注入）：

```
You can leverage these tools, behaving like regular python functions:

```python
{tool.name}(arg1: type1, arg2: type2) -> return_type
"""工具描述"""

{tool.name2}(...) -> ...
...
```
```

这确保规划阶段模型就知道有哪些工具可用，避免规划不可执行的步骤。

## 五、规划与执行协同

### 5.1 主循环中的位置

[[agents.py]] 第540-604行的 _run_stream 方法展示了规划与执行的交替：

```python
while not returned_final_answer and self.step_number <= max_steps:
    # 1. 规划步骤
    if self.planning_interval is not None and (...):
        ...
        for element in self._generate_planning_step(...):
            yield element
        self.memory.steps.append(planning_step)

    # 2. 执行步骤
    action_step = ActionStep(...)
    for output in self._step_stream(action_step):
        yield output
    self.memory.steps.append(action_step)
    self.step_number += 1
```

**执行顺序**：规划 → 执行 → 可能的重规划 → 继续执行...

### 5.2 规划对执行的影响路径

规划内容通过以下路径影响执行：

1. **直接注入对话历史**：PlanningStep.to_messages 返回的消息被加入 memory
2. **隐式指导**：模型在生成 ActionStep 时能看到历史规划
3. **任务提醒**：更新规划时会重新陈述原始任务

### 5.3 执行反馈如何影响重规划

执行结果通过以下方式影响下一次规划：

1. **ActionStep 保留完整记录**：observations, errors, action_output
2. **summary_mode 过滤**：保留执行记录，过滤旧规划
3. **remaining_steps 计算**：基于当前 step_number 和 max_steps 计算

[[agents.py]] 第707行的剩余步数计算：

```python
"remaining_steps": (self.max_steps - step),
```

### 5.4 动态调整策略

smolagents 的规划机制支持以下动态调整：

| 场景 | 调整机制 |
|------|----------|
| 发现新信息 | 更新规划中的 "Facts that we have learned" |
| 执行受阻 | 可 "make a completely new plan starting from scratch" |
| 步数紧张 | remaining_steps 提醒模型压缩后续步骤 |
| 工具不可用 | 重新规划时基于当前 tools 列表生成 |

## 六、对我们项目的启示

### 6.1 可借鉴的设计

1. **summary_mode 模式**：在重规划时过滤历史规划内容，避免旧规划干扰新规划
2. **事实分类框架**：将信息分为已知/待查/需推导/已学习四类，结构化思考
3. **定期重规划机制**：通过 planning_interval 定期重新审视全局，防止局部最优
4. **高层规划原则**：规划只描述步骤意图，不写具体工具调用，保持灵活性

### 6.2 可优化的方向

1. **条件触发重规划**：当前仅支持时间触发，可考虑增加错误触发、信息缺口触发等
2. **规划质量评估**：增加对生成规划的自动验证，检查步骤间依赖关系
3. **规划粒度自适应**：根据任务复杂度动态调整规划的详细程度
4. **规划继承机制**：允许部分保留上一版规划的有效部分，而非完全重新生成

### 6.3 实现建议

对于 AI数据分析系统 的规划模块，建议：

```python
# 伪代码示例
class PlanningModule:
    def should_replan(self, context) -> bool:
        # 多维度触发判断
        if self.steps_since_last_plan >= self.planning_interval:
            return True
        if context.last_error is not None:
            return True
        if context.information_gain > threshold:
            return True
        return False
    
    def generate_plan(self, context, mode: str = "update") -> Plan:
        # mode: "initial" | "update" | "error_recovery"
        messages = self.build_prompt(context, mode)
        return self.llm.generate(messages)
```

---

*本文档基于 smolagents 源码分析生成，供 AI数据分析系统 设计参考。*
