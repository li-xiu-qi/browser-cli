# SmolagentsInstrumentor RunWrapper与StepWrapper实现分析

> 项目: openinference-instrumentation-smolagents
> 分析日期: 2026-02-06
> 源码位置: [[../../../参考项目/openinference-instrumentation/python/instrumentation/openinference-instrumentation-smolagents/src/openinference/instrumentation/smolagents/_wrappers.py|_wrappers.py]]

---

## 一、_RunWrapper详解

### 1.1 Span命名策略

代码位置: _wrappers.py 第 117 行

```python
span_name = f"{getattr(agent, 'name', None) or agent.__class__.__name__}.run"
```

#### 为什么优先使用 agent.name

| 优先级 | 值来源 | 场景 |
|--------|--------|------|
| 1 | agent.name | 用户为 Agent 设置了自定义名称 |
| 2 | agent.__class__.__name__ | 使用默认类名 |

优先使用 agent.name 的原因：

1. **可读性**: 用户设置的名称通常更具业务语义，如 `DataAnalysisAgent` 比 `CodeAgent` 更清晰
2. **区分度**: 多个同类型 Agent 实例可以通过名称区分，如 `WeatherAgent` 和 `StockAgent`
3. **追踪友好**: 在追踪系统中，有意义的名称便于快速定位问题

#### 回退到类名的场景

当以下情况发生时回退到类名：
- Agent 未设置 name 属性
- name 属性值为 None
- name 属性值为空字符串

#### 命名对可读性的影响

命名示例对比：

| Agent 定义 | Span 名称 | 评价 |
|------------|-----------|------|
| `CodeAgent(name="WeatherAgent")` | WeatherAgent.run | 清晰表达业务意图 |
| `CodeAgent()` | CodeAgent.run | 仅知道是代码执行类型 |
| `ToolCallingAgent(name="SearchAgent")` | SearchAgent.run | 明确搜索专用 Agent |

---

### 1.2 属性收集逻辑

代码位置: _wrappers.py 第 65-98 行

```python
def _smolagent_run_attributes(agent, arguments):
    # task
    # additional_args
    # max_steps
    # tools_names
    # managed_agents.{index}.name/description/...
```

#### 每个属性的用途

| 属性名 | 来源 | 用途 |
|--------|------|------|
| smolagents.task | agent.task | 记录 Agent 执行的任务描述 |
| smolagents.additional_args | arguments | 记录额外的运行时参数 |
| smolagents.max_steps | agent.max_steps | 记录最大执行步数限制 |
| smolagents.tools_names | agent.tools | 记录可用工具列表 |
| smolagents.managed_agents.{i}.name | agent.managed_agents | 记录托管 Agent 名称 |
| smolagents.managed_agents.{i}.description | agent.managed_agents | 记录托管 Agent 描述 |

#### 如何从agent对象中提取

属性提取代码详解：

```python
if task := agent.task:
    yield "smolagents.task", task
```

使用赋值表达式的优势：
- 简洁：一行完成获取和判断
- 安全：仅当值存在时才设置属性
- 高效：避免重复访问属性

工具名称的提取：

```python
yield "smolagents.tools_names", list(agent.tools.keys())
```

将字典 keys 转为列表的原因：
- Span 属性必须是 JSON 可序列化的基本类型
- dict_keys 对象不能直接序列化
- 列表形式便于在追踪系统中展示

#### 托管Agent属性的特殊处理

代码逻辑：

```python
for managed_agent_index, managed_agent in enumerate(agent.managed_agents.values()):
    yield f"smolagents.managed_agents.{managed_agent_index}.name", managed_agent.name
    yield f"smolagents.managed_agents.{managed_agent_index}.description", managed_agent.description
    # ... 其他属性
```

这种扁平化命名方式：
- 符合 OpenTelemetry 属性命名规范
- 支持任意数量的托管 Agent
- 便于追踪系统索引和查询

属性的序列化处理：

```python
if additional_args := arguments.get("additional_args"):
    yield "smolagents.additional_args", safe_json_dumps(additional_args)
```

使用 safe_json_dumps 而非标准 json.dumps：
- 处理不可序列化的对象
- 避免序列化异常中断追踪
- 提供更稳定的输出

---

### 1.3 流式vs非流式处理

代码位置: _wrappers.py 第 151-200 行

#### 流式检测

```python
is_generator = isinstance(agent_output, Generator)

if is_generator:
    # 返回包装后的 Generator
    return wrapped_generator()
else:
    # 直接设置输出
    span.set_attribute(OUTPUT_VALUE, str(agent_output))
```

#### 流式处理的复杂性

流式处理的核心挑战是 Generator 的延迟执行特性：

```python
def wrapped_generator():
    output_chunks = []
    try:
        for chunk in agent_output:
            output_chunks.append(str(chunk))
            yield chunk
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace_api.StatusCode.ERROR)
        raise
    finally:
        # 从 agent.monitor 获取最终结果
        steps = getattr(agent.monitor, "steps", [])
        history = getattr(agent.monitor, "history", [])
        
        if steps:
            observation = getattr(steps[-1], "observations", None)
        elif history:
            observation = getattr(history[-1], "observations", None)
        elif output_chunks:
            observation = "".join(output_chunks)
            
        span.set_attribute(OUTPUT_VALUE, observation)
        span.set_attribute(LLM_TOKEN_COUNT_PROMPT, agent.monitor.total_input_token_count)
        span.set_attribute(LLM_TOKEN_COUNT_COMPLETION, agent.monitor.total_output_token_count)
        span.end()
        context_api.detach(token)
```

#### 为什么需要在finally中设置输出

流式 Generator 的生命周期：

```
_RunWrapper.__call__
    ↓
创建 Span
    ↓
执行 wrapped → 返回 Generator 对象
    ↓
返回 wrapped_generator
    ↓
调用方开始迭代
    ↓
第一次 yield → 返回数据给调用方
    ↓
... 多次 yield ...
    ↓
最后一次 yield
    ↓
Generator 结束 → finally 执行
    ↓
设置 OUTPUT_VALUE、Token 统计
    ↓
关闭 Span、detach Context
```

关键点：
1. 返回 Generator 时原始方法已经执行完毕
2. 但真正的输出数据还在 Generator 内部
3. 必须在 Generator 完全迭代后才能获取最终结果
4. finally 块保证无论正常结束还是异常都会执行清理

#### 如何获取最终结果

结果获取的三级回退策略：

```python
# 第一优先级：从 steps 获取最后一步的观察结果
steps = getattr(agent.monitor, "steps", [])
if steps:
    observation = getattr(steps[-1], "observations", None)

# 第二优先级：从 history 获取
elif history:
    observation = getattr(history[-1], "observations", None)

# 第三优先级：从收集的 chunks 拼接
elif output_chunks:
    observation = "".join(output_chunks)
```

这种回退策略的原因：
- agent.monitor.steps 是最准确的结果来源
- history 是兼容性考虑，某些版本使用不同属性名
- output_chunks 是最终兜底，确保总有输出记录

---

### 1.4 Token统计获取

代码位置: _wrappers.py 第 183-194 行

```python
span.set_attribute(LLM_TOKEN_COUNT_PROMPT, agent.monitor.total_input_token_count)
span.set_attribute(LLM_TOKEN_COUNT_COMPLETION, agent.monitor.total_output_token_count)
span.set_attribute(
    LLM_TOKEN_COUNT_TOTAL,
    agent.monitor.total_input_token_count + agent.monitor.total_output_token_count,
)
```

#### agent.monitor是什么

agent.monitor 是 smolagents 内置的监控对象，负责：
- 记录每个步骤的输入输出
- 统计 token 使用量
- 维护执行历史

Monitor 的主要属性：

| 属性 | 类型 | 说明 |
|------|------|------|
| steps | List[StepLog] | 每一步的执行日志 |
| history | List[Any] | 执行历史记录 |
| total_input_token_count | int | 输入 token 总数 |
| total_output_token_count | int | 输出 token 总数 |

#### 统计数据的准确性

Token 统计在 smolagents 中的实现位置：
- Model 层：每次调用 LLM 时记录输入输出 token 数
- Agent 层：累加所有步骤的 token 使用量
- Monitor 层：提供聚合后的统计数据

准确性保证：
1. 底层模型返回的 token 用量通常来自 API 响应
2. 累加逻辑在 Agent 内部完成，Instrumentor 只读取结果
3. 如果模型不提供 token 统计，该值可能为 0

#### 不同执行模式下的表现

| 执行模式 | Token 统计时机 | 说明 |
|----------|----------------|------|
| 非流式 | 方法返回后立即获取 | 完整执行已完成，数据准确 |
| 流式 | Generator 结束时获取 | 确保所有步骤已执行完毕 |

---

### 1.5 错误处理

代码位置: _wrappers.py 第 144-149 行、第 203-226 行

```python
try:
    agent_output = wrapped(*args, **kwargs)
except Exception as e:
    span.record_exception(e)
    span.set_status(trace_api.StatusCode.ERROR)
    raise
```

#### 异常记录的方式

`span.record_exception(e)` 的作用：
- 将异常信息添加到 Span 的 events 中
- 包含异常类型、消息、堆栈跟踪
- 便于在追踪系统中查看错误详情

#### Span状态设置

`span.set_status(trace_api.StatusCode.ERROR)` 的作用：
- 将 Span 的整体状态标记为错误
- 影响追踪系统的错误率统计
- 在 UI 中通常以红色或警告标识显示

#### 异常传播

处理完异常后的 `raise` 语句：
- 重新抛出原始异常，不吞没错误
- 保持业务代码的异常行为不变
- Instrumentor 仅记录，不干预执行流程

异常处理流程：

```
发生异常
    ↓
捕获异常
    ↓
record_exception → 记录到 Span events
    ↓
set_status(ERROR) → 标记 Span 状态
    ↓
raise → 重新抛出，继续传播
    ↓
finally → 执行清理
    ↓
span.end()
context_api.detach(token)
```

---

## 二、_StepWrapper详解

### 2.1 Step命名

代码位置: _wrappers.py 第 304 行

```python
span_name = f"Step {agent.step_number}"
```

#### 使用step_number的好处

命名示例：
- Step 1
- Step 2
- Step 3

这种命名方式的优势：

1. **顺序清晰**: 从名称直接看出执行顺序
2. **简洁明确**: 不需要额外解析，人类和机器都易读
3. **与代码一致**: step_number 是 smolagents 内部的实际计数器

#### 命名对追踪可读性的影响

在追踪系统中的展示效果：

```
Manager.run
├── Step 1
├── Step 2
├── Step 3
└── Step 4
```

对比其他可能的命名方式：

| 命名方式 | 示例 | 问题 |
|----------|------|------|
| 使用 uuid | step-a1b2c3d4 | 无法看出顺序 |
| 使用时间戳 | step-1707200000 | 冗长且不易读 |
| 使用描述 | step-web_search | 可能重复或不准确 |
| 使用序号 | Step 1 | 简洁、有序、可读 |

---

### 2.2 Span Kind选择

代码位置: _wrappers.py 第 308 行

```python
OPENINFERENCE_SPAN_KIND: CHAIN
```

#### 为什么是CHAIN而不是AGENT

OpenInference 定义的 Span Kind 语义：

| Span Kind | 语义 | 适用场景 |
|-----------|------|----------|
| AGENT | 智能体整体执行 | MultiStepAgent.run |
| CHAIN | 执行链中的一个环节 | Agent 的单个步骤 |
| LLM | 大模型调用 | Model.generate |
| TOOL | 工具调用 | Tool.__call__ |

Step 使用 CHAIN 的原因：

1. **层级关系**: Step 是 Agent 执行的子环节，AGENT 包含多个 CHAIN
2. **语义准确**: Step 是 Agent 决策-执行链中的一环
3. **可观测性**: 区分 Agent 整体和单个步骤的追踪粒度

#### Span Kind的语义区别

Trace 结构示例：

```
Trace: trace_id=abc123
├── Span: WeatherAgent.run (AGENT) ← Agent 整体
│   ├── Span: Step 1 (CHAIN) ← 第一步
│   │   ├── Span: LLM.generate (LLM)
│   │   └── Span: Tool.web_search (TOOL)
│   ├── Span: Step 2 (CHAIN) ← 第二步
│   │   └── Span: LLM.generate (LLM)
│   └── Span: Step 3 (CHAIN) ← 第三步
│       └── Span: Tool.final_answer (TOOL)
```

语义层次：
- AGENT: 一个完整的任务执行
- CHAIN: 任务执行中的一个决策-行动环节
- LLM/TOOL: CHAIN 中的具体操作

---

### 2.3 观察结果提取

代码位置: _wrappers.py 第 229-249 行

```python
def _finalize_step_span(span, step_log):
    observations = getattr(step_log, "observations", None)
    if observations is not None:
        span.set_attribute(OUTPUT_VALUE, str(observations))
```

Step 的输出是什么：

在 smolagents 中，一个 Step 的典型输出包括：
- observations: Agent 观察到的事实或执行结果
- error: 如果执行出错，记录错误信息
- tool_calls: 调用的工具及其参数

observations 通常包含：
- 工具调用的返回值
- LLM 的思考过程
- 环境反馈信息

---

### 2.4 错误分类处理

代码位置: _wrappers.py 第 252-277 行

```python
def _record_step_error(span, error):
    error_type = error.__class__.__name__
    expected_error_types = {"AgentToolCallError", "AgentToolExecutionError"}
    
    if error_type in expected_error_types:
        # 预期错误，标记为 recoverable
        span.add_event(name="agent.step_recovery", attributes={...})
        span.set_status(trace_api.StatusCode.OK)
    else:
        # 意外错误
        span.record_exception(error)
        span.set_status(trace_api.StatusCode.ERROR)
```

#### 为什么区分预期错误和意外错误

错误分类的目的：

| 错误类型 | 示例 | 处理策略 |
|----------|------|----------|
| 预期错误 | AgentToolCallError | Agent 可以恢复，继续执行下一步 |
| 预期错误 | AgentToolExecutionError | 工具执行失败，但 Agent 可以尝试其他方式 |
| 意外错误 | ValueError、RuntimeError | Agent 无法正常恢复，需要人工介入 |

这种区分的意义：
1. **错误率统计**: 预期错误不应计入真正的错误率
2. **告警策略**: 只对意外错误发送告警
3. **用户体验**: 预期错误是正常流程的一部分

#### step_recovery事件的意义

```python
span.add_event(
    name="agent.step_recovery",
    attributes={**error_attrs, "severity": "expected"},
)
```

event 在追踪系统中的作用：
- 标记这是一个可恢复的错误
- 记录错误的详细信息
- 便于后续分析和统计

#### 错误恢复的设计哲学

Agent 的容错设计理念：

```
用户请求
    ↓
Step 1: 尝试工具 A → 失败，记录 recovery 事件
    ↓
Step 2: 尝试工具 B → 成功
    ↓
Step 3: 完成任务
```

关键设计决策：
- 单步失败不等于整体失败
- 让 Agent 有机会自我修复
- 记录恢复过程用于分析

---

## 三、流式Generator的复杂处理

### 3.1 Generator的生命周期

Generator 的完整生命周期：

```python
def wrapped_generator():
    # 1. yield 前：准备工作，但不执行
    output_chunks = []
    
    try:
        # 2. yield 时：返回数据给调用方
        for chunk in agent_output:
            output_chunks.append(str(chunk))
            yield chunk  # ← 每次执行到这里暂停，返回数据
    except Exception as e:
        # 3. 异常时：记录并传播
        span.record_exception(e)
        span.set_status(trace_api.StatusCode.ERROR)
        raise
    finally:
        # 4. finally：无论正常或异常都执行
        span.set_attribute(OUTPUT_VALUE, observation)
        span.end()
        context_api.detach(token)
```

执行流程时间线：

```
时间点    调用方代码                    _RunWrapper 内部
─────────────────────────────────────────────────────────────
T1        agent.run("task")  →        __call__ 开始
                                       ↓
T2                                    创建 Span
                                       ↓
T3                                    执行 wrapped
                                       ↓
T4                                    返回 Generator
                                       ↓
T5        for chunk in result: ←     返回 wrapped_generator
          开始迭代
                                       ↓
T6        获取第一个 chunk ←          yield chunk
                                       ↓
T7        处理 chunk                  暂停，等待下一次迭代
                                       ↓
T8        获取第二个 chunk ←          yield chunk
          ...                         ...
                                       ↓
T9        获取最后一个 chunk ←        yield chunk
                                       ↓
T10       迭代结束                    finally 执行
                                       ↓
T11                                   span.end()
                                      context_api.detach(token)
```

### 3.2 上下文保持

跨 yield 的上下文一致性：

```python
def wrapped_generator():
    # token 通过闭包捕获
    token = context_api.attach(context)
    
    try:
        for chunk in agent_output:
            yield chunk
            # 每次 yield 后，Context 仍然有效
    finally:
        # 确保 detach 执行
        context_api.detach(token)
```

为什么 Context 不会丢失：
1. Python Generator 保持函数栈帧
2. 局部变量 token 在栈帧中
3. 每次恢复执行时，栈帧状态完整恢复

### 3.3 异常处理

Generator 中的异常传播：

```python
try:
    for chunk in agent_output:
        yield chunk
except Exception as e:
    # 捕获 Generator 内部异常
    span.record_exception(e)
    span.set_status(trace_api.StatusCode.ERROR)
    raise  # 重新抛出，调用方也能收到
finally:
    # 保证执行，即使发生异常
    span.end()
    context_api.detach(token)
```

异常场景分析：

| 场景 | 处理方式 | 结果 |
|------|----------|------|
| 正常结束 | finally 执行 | Span 正常关闭 |
| Generator 内部异常 | except 捕获 → finally 执行 | Span 标记错误后关闭 |
| 调用方中断迭代 | finally 仍执行 | Span 正常关闭 |

finally 块的执行保证：
- Python 保证 finally 块总是执行
- 即使发生未捕获的异常，也会先执行 finally
- 这是资源清理的关键机制

---

## 四、与非流式处理的对比

| 维度 | 流式 | 非流式 |
|------|------|--------|
| 返回值类型 | Generator | 具体值 |
| Span 结束时机 | Generator 消费完毕时 | 方法返回时 |
| 输出获取 | 从 monitor/history 聚合 | 直接序列化 |
| 异常处理 | Generator 内部捕获 | 直接 try-except |
| 上下文清理 | 延迟到 finally | 立即清理 |
| 代码复杂度 | 高，需要包装 Generator | 低，直接处理 |

### 流程差异图

```
非流式处理：
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ 创建Span │ → │ 执行方法 │ → │ 设置属性 │ → │ 结束Span │
└─────────┘     └─────────┘     └─────────┘     └─────────┘

流式处理：
┌─────────┐     ┌─────────┐     ┌─────────┐
│ 创建Span │ → │ 执行方法 │ → │ 返回    │
└─────────┘     └─────────┘     │ Generator│
                                └────┬────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ↓                ↓                ↓
               ┌─────────┐     ┌─────────┐     ┌─────────┐
               │ yield 1 │     │ yield 2 │     │ yield N │
               └────┬────┘     └────┬────┘     └────┬────┘
                    │                │                │
                    └────────────────┴────────────────┘
                                     ↓
                              ┌─────────────┐
                              │ finally清理  │
                              │ 结束Span    │
                              └─────────────┘
```

---

## 五、代码流程图

### 5.1 RunWrapper完整流程

![RunWrapper流程图](graphviz/smolagents-instrumentor-RunWrapper流程图.svg)

流程说明：

1. **检查抑制标志**: 如果设置了 `_SUPPRESS_INSTRUMENTATION_KEY`，直接执行原方法
2. **构建 Span 名称**: 优先使用 agent.name，否则使用类名
3. **收集属性**: 提取 task、tools、managed_agents 等信息
4. **创建 Span**: 启动 AGENT 类型的 Span
5. **设置上下文**: attach Context，获取 token
6. **执行方法**: 调用原始 run 方法
7. **判断输出类型**: 检查是否为 Generator
8. **流式分支**: 创建 wrapped_generator，延迟清理
9. **非流式分支**: 立即设置输出、统计 Token、结束 Span
10. **异常处理**: 记录异常、标记错误状态、传播异常

### 5.2 StepWrapper完整流程

![StepWrapper流程图](graphviz/smolagents-instrumentor-StepWrapper流程图.svg)

流程说明：

1. **检查抑制标志**: 同 RunWrapper
2. **构建 Span 名称**: 使用 step_number 生成 "Step N"
3. **创建 Span**: 启动 CHAIN 类型的 Span
4. **执行步骤**: 使用 yield from 执行原始方法
5. **提取观察结果**: 从 step_log 获取 observations
6. **错误分类**: 区分预期错误和意外错误
7. **事件记录**: 预期错误添加 step_recovery 事件
8. **状态设置**: 预期错误标记 OK，意外错误标记 ERROR
9. **结束 Span**: 使用上下文管理器自动处理

### 5.3 流式处理的特殊路径

流式处理的特殊之处：

```
RunWrapper 检测为 Generator
    ↓
创建 wrapped_generator 函数
    ↓
返回 Generator 对象给调用方
    ↓
调用方迭代消费数据
    ↓
每次 yield 暂停，保持 Context
    ↓
迭代结束触发 finally
    ↓
在 finally 中：
  - 从 monitor 获取最终输出
  - 统计 Token 用量
  - 关闭 Span
  - detach Context
```

---

## 六、关键设计要点总结

### 6.1 RunWrapper设计亮点

| 设计点 | 实现 | 价值 |
|--------|------|------|
| 智能命名 | name or class_name | 兼顾可读性和鲁棒性 |
| 属性回退 | steps → history → chunks | 确保总有输出记录 |
| 流式支持 | 包装 Generator | 支持实时输出场景 |
| 延迟清理 | finally 中 detach | 确保 Span 生命周期正确 |
| Token统计 | 从 monitor 读取 | 复用框架内部统计 |

### 6.2 StepWrapper设计亮点

| 设计点 | 实现 | 价值 |
|--------|------|------|
| 序号命名 | Step N | 清晰展示执行顺序 |
| 错误分类 | expected vs unexpected | 区分可恢复和不可恢复错误 |
| recovery 事件 | agent.step_recovery | 记录容错恢复过程 |
| 观察结果提取 | step_log.observations | 准确记录 Step 输出 |

### 6.3 两者协作关系

```
_RunWrapper (AGENT)
    └── _StepWrapper (CHAIN) × N
            ├── _ModelWrapper (LLM)
            └── _ToolCallWrapper (TOOL)
```

协作特点：
- RunWrapper 负责整体 Agent 执行的追踪
- StepWrapper 负责每个决策步骤的追踪
- 两者形成父子 Span 关系
- 共同构成完整的 Agent 执行链路

---

**参考链接**
- 源码位置: [[../../../参考项目/openinference-instrumentation/python/instrumentation/openinference-instrumentation-smolagents/src/openinference/instrumentation/smolagents/_wrappers.py|_wrappers.py]]
- 架构概览: [[39-SmolagentsInstrumentor-架构概览与核心设计模式|39-架构概览与核心设计模式]]
- 上下文传播: [[41-SmolagentsInstrumentor-OpenTelemetry上下文传播机制|41-上下文传播机制]]
