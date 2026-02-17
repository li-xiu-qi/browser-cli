# smolagents 规划 Prompt 翻译版

> 原文档: [[05-smolagents-规划与重规划机制]]
> 翻译目的: 方便中文阅读和理解
> 注意: 这是翻译版本，实际使用时需要使用英文原文

---

## 一、初始规划 Prompt

### 英文原文

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

### 中文翻译

```
你是分析情况、推导事实并据此制定解决方案的世界级专家。
下面我将给你一个任务。你需要：
1. 建立一个已知或需要的事实调查清单
2. 制定一个行动计划来解决问题

## 1. 事实调查
你需要建立一个全面的预备调查，包括我们已经掌握的事实和仍然需要的事实。
这些"事实"通常包括具体的名称、日期、数值等。你的回答应该使用以下标题：

### 1.1. 任务中给出的事实
列出任务中给出的、可能对你有帮助的具体事实（这里可能什么都没有）。

### 1.2. 需要查找的事实
列出任何我们需要查找的事实。
同时列出在哪里可以找到这些事实，例如一个网站、一个文件... 
- 也许任务中包含了一些你可以在这里重复使用的来源。

### 1.3. 需要推导的事实
列出任何我们想通过上述内容用逻辑推理推导出来的东西，例如计算或模拟。

不要做任何假设。对每一项都要提供充分的推理。
不要在上面的三个标题之外添加任何其他内容。

## 2. 计划
然后针对给定的任务，根据上述输入和事实清单，制定一个逐步的高层计划。
这个计划应该包含基于可用工具的独立任务，如果这些任务执行正确，将得出正确答案。
不要跳过步骤，不要添加多余的步骤。
只写高层计划，不要详细说明单个工具调用。
在写完计划的最后一步后，写上'<end_plan>'标签并停止。
```

---

## 二、更新规划前置 Prompt

### 英文原文

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

### 中文翻译

```
你是分析情况并据此制定任务解决方案的世界级专家。
你被赋予了以下任务：
```
{{task}}
```

下面你会发现解决这个任务的历史尝试记录。
你首先需要做一个已知和未知事实的调查，
然后提出一个逐步的高层计划来解决任务。
如果之前的尝试到目前为止取得了一些成功，你的更新计划可以基于这些结果继续。
如果你卡住了，你可以完全从头开始制定一个新计划。
```

---

## 三、更新规划后置 Prompt

### 英文原文

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

### 中文翻译

```
现在根据上述历史记录，在下面写出你更新后的事实：

## 1. 更新后的事实调查
### 1.1. 任务中给出的事实
### 1.2. 我们已经学到的事实
### 1.3. 仍然需要查找的事实
### 1.4. 仍然需要推导的事实

然后写一个逐步的高层计划来解决上述任务。

## 2. 计划
### 2.1. ...
以此类推。

这个计划应该包含基于可用工具的独立任务，
如果执行正确将得出正确答案。
注意你还剩 {remaining_steps} 步。
不要跳过步骤，不要添加多余的步骤。
只写高层计划，不要详细说明单个工具调用。
在写完计划的最后一步后，写上'<end_plan>'标签并停止。
```

---

## 四、Prompt 结构对比

| 组件 | 初始规划 | 更新规划 |
|------|----------|----------|
| **角色设定** | 世界级专家 | 世界级专家 |
| **任务来源** | 新任务 | 重新陈述原任务 |
| **事实分类** | 3类：给出/待查/需推导 | 4类：增加"已学到" |
| **灵活性** | 从零开始 | 可基于结果或完全重来 |
| **约束提醒** | 无 | 提醒剩余步数 |
| **终止标记** | `<end_plan>` | `<end_plan>` |

---

## 五、关键设计要点

### 1. 事实分类框架

```
初始规划：              更新规划：
├─ 任务中给出的事实      ├─ 任务中给出的事实
├─ 需要查找的事实        ├─ 我们已经学到的事实  ← 新增
├─ 需要推导的事实        ├─ 仍然需要查找的事实
                         └─ 仍然需要推导的事实
```

### 2. 高层规划原则

- **要写**：步骤意图、工具选择、执行顺序
- **不写**：具体参数、详细调用代码、实现细节

### 3. 特殊标记

- `{{task}}`：任务内容变量
- `{{remaining_steps}}`：剩余步数变量
- `<end_plan>`：强制停止生成的终止标记

---

## 六、使用建议

### 何时使用初始规划

- 任务开始时（step 1）
- 完全重新开始时
- 任务描述发生变化时

### 何时使用更新规划

- 每 N 步重规划时（planning_interval）
- 执行受阻需要调整时
- 获得重要新信息时

### 生产环境注意事项

1. **变量替换**：确保 `{{task}}` 和 `{{remaining_steps}}` 被正确替换
2. **工具列表**：在 prompt 中动态注入当前可用工具
3. **长度控制**：长任务时考虑压缩历史记录

---

*本文档为 [[05-smolagents-规划与重规划机制]] 的补充翻译版本*
