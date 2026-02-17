# SmolagentsInstrumentor OpenTelemetry上下文传播机制

> 项目: openinference-instrumentation-smolagents
> 分析日期: 2026-02-06
> 源码位置: [[../../../参考项目/openinference-instrumentation/python/instrumentation/openinference-instrumentation-smolagents/src/openinference/instrumentation/smolagents/_wrappers.py|_wrappers.py]]

---

## 一、OpenTelemetry上下文基础

### 1.1 Context 是什么

> Context 是 OpenTelemetry 中传递追踪信息的载体，它让分布式追踪中的各个环节能够关联起来。

在 OTel 中的作用：

| 作用 | 说明 |
|------|------|
| 传递 TraceId | 确保一次请求的所有 Span 属于同一 Trace |
| 传递 SpanId | 建立父子关系，形成调用链 |
| 传递 Baggage | 携带业务自定义的上下文信息 |
| 跨边界传播 | 在进程内、线程间、网络间传递 |

Context 的数据结构：

```python
# Context 本质上是一个不可变的键值对映射
# 内部使用 _Context 类实现
{
    "current_span": Span,           # 当前活跃的 Span
    "baggage": Baggage,             # 业务 baggage 数据
    "_SUPPRESS_INSTRUMENTATION": bool,  # 是否抑制追踪
    # ... 其他 OTel 内部键
}
```

线程本地存储 vs 上下文变量：

| 特性 | 线程本地存储 | 上下文变量 |
|------|-------------|-----------|
| API | `threading.local` | `contextvars.ContextVar` |
| 异步支持 | 不支持 | 原生支持 asyncio |
| 使用场景 | 纯同步代码 | 同步+异步混合 |
| OTel 默认 | 早期版本使用 | 当前版本使用 |

OTel Python 使用 `contextvars` 实现 Context，这使得它在异步场景下也能正确工作。

### 1.2 SpanContext 的结构

SpanContext 是 Span 的不可变标识符，包含追踪所需的核心信息：

```python
from opentelemetry.trace import SpanContext

SpanContext(
    trace_id: int,      # 128位整数，唯一标识一次完整请求
    span_id: int,       # 64位整数，唯一标识一个 Span
    is_remote: bool,    # 是否从远程传播而来
    trace_flags: TraceFlags,  # 采样标志，如是否记录
    trace_state: TraceState,  # 供应商特定的追踪状态
)
```

字段详解：

| 字段 | 类型 | 说明 |
|------|------|------|
| trace_id | 128位整数 | 十六进制表示为 32 位字符串，如 `a1b2c3d4e5f6...` |
| span_id | 64位整数 | 十六进制表示为 16 位字符串 |
| is_remote | bool | True 表示从上游服务传播而来，False 表示本地生成 |
| trace_flags | TraceFlags | 目前仅使用最低位表示是否采样 |
| trace_state | TraceState | 键值对列表，用于传递供应商特定信息 |

### 1.3 TraceId/SpanId 的生成和传播

生成新的 TraceId：

```python
from opentelemetry.sdk.trace import RandomIdGenerator

generator = RandomIdGenerator()
trace_id = generator.generate_trace_id()  # 128位随机数
span_id = generator.generate_span_id()    # 64位随机数
```

从上下文中获取当前 Span：

```python
from opentelemetry import trace as trace_api

current_span = trace_api.get_current_span()

# 检查 Span 是否有效
if current_span.get_span_context().is_valid:
    trace_id = current_span.get_span_context().trace_id
    span_id = current_span.get_span_context().span_id
```

父子关系的建立：

```python
# 方式1: 使用 start_as_current_span 自动建立
with tracer.start_as_current_span("child"):
    # 内部自动将当前 Span 设为 parent
    pass

# 方式2: 手动指定 parent
parent_span = trace_api.get_current_span()
with tracer.start_as_current_span("child", parent=parent_span):
    pass

# 方式3: 从 Context 中继承
context = trace_api.set_span_in_context(parent_span)
token = context_api.attach(context)
# 此后创建的 Span 自动继承 context 中的 parent
```

---

## 二、上下文传播的核心代码

### 2.1 基本流程

在 [[../../../参考项目/openinference-instrumentation/python/instrumentation/openinference-instrumentation-smolagents/src/openinference/instrumentation/smolagents/_wrappers.py|_wrappers.py]] 中，上下文传播遵循标准模式：

```python
from opentelemetry import trace as trace_api, context as context_api

# 第一步: 创建 Span
span = self._tracer.start_span(span_name, attributes=...)

# 第二步: 设置上下文
context = trace_api.set_span_in_context(span)
token = context_api.attach(context)

# 第三步: 在上下文中执行
try:
    result = wrapped(*args, **kwargs)
finally:
    # 第四步: 清理上下文
    context_api.detach(token)
    span.end()
```

完整代码示例来自 `_RunWrapper.__call__`：

```python
def __call__(self, wrapped, instance, args, kwargs):
    # 创建 Span
    span = self._tracer.start_span(
        span_name,
        attributes=dict(...),
    )
    
    # 设置上下文
    context = trace_api.set_span_in_context(span)
    token = context_api.attach(context)
    
    try:
        agent_output = wrapped(*args, **kwargs)
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace_api.StatusCode.ERROR)
        raise
    
    # ... 处理输出 ...
    
    finally:
        span.end()
        context_api.detach(token)
```

### 2.2 关键 API 详解

**set_span_in_context**

```python
context = trace_api.set_span_in_context(span, parent_context=None)
```

- 将 Span 设置到 Context 中
- 返回新的 Context 对象，原 Context 不变
- 如果提供 parent_context，则基于它创建；否则使用当前 Context

**context_api.attach**

```python
token = context_api.attach(context)
```

- 将 Context 激活为当前上下文
- 返回 token，用于后续 detach
- 内部将 Context 压入上下文栈

**context_api.detach**

```python
context_api.detach(token)
```

- 使用 token 恢复到之前的上下文
- 必须与 attach 配对使用
- 必须使用 try-finally 确保调用

### 2.3 两种上下文管理方式对比

| 方式 | 代码示例 | 适用场景 |
|------|----------|----------|
| 手动 attach/detach | `attach` + `try-finally` + `detach` | 需要精细控制、Generator 场景 |
| 上下文管理器 | `with start_as_current_span` | 简单同步代码 |

`_RunWrapper` 使用手动方式的原因：

1. 需要处理 Generator 流式输出
2. 需要在 finally 中记录监控数据
3. 需要区分流式和非流式两种场景

`_StepWrapper` 和 `_ModelWrapper` 使用上下文管理器的原因：

1. 逻辑简单，无特殊需求
2. 代码更简洁

---

## 三、父子关系建立

### 3.1 自动父子关系

当使用 `start_as_current_span` 或 `start_span` 配合已设置 Span 的 Context 时，OTel 自动建立父子关系：

```python
# 父 Span
with tracer.start_as_current_span("parent"):
    # 当前 Context 中包含 parent Span
    
    # 子 Span 自动继承 parent
    with tracer.start_as_current_span("child"):
        # child.parent_span_id == parent.span_id
        pass
```

内部机制：

1. `start_as_current_span` 检查当前 Context
2. 如果 Context 中有有效的 Span，将其设为 parent
3. 如果没有，创建新的 Root Span

### 3.2 _has_active_llm_parent_span 的作用

在 [[../../../参考项目/openinference-instrumentation/python/instrumentation/openinference-instrumentation-smolagents/src/openinference/instrumentation/smolagents/_wrappers.py|_wrappers.py]] 第 550-560 行：

```python
def _has_active_llm_parent_span() -> bool:
    current_span = trace_api.get_current_span()
    return (
        current_span.get_span_context().is_valid
        and current_span.is_recording()
        and isinstance(current_span, ReadableSpan)
        and (current_span.attributes or {}).get(OPENINFERENCE_SPAN_KIND) == LLM
    )
```

这个函数在 `_ModelWrapper.__call__` 中被调用：

```python
def __call__(self, wrapped, instance, args, kwargs):
    if _has_active_llm_parent_span():
        return wrapped(*args, **kwargs)  # 跳过创建新 Span
    
    # 正常创建 LLM Span
    with self._tracer.start_as_current_span(...) as span:
        ...
```

为什么需要这个检查：

1. **防止嵌套 LLM Span**: Tool 内部可能调用 LLM，不需要重复记录
2. **避免重复追踪**: 某些场景下 LLM 可能递归调用自身
3. **保持 Trace 清晰**: 每个 LLM 调用只记录一次

检查条件详解：

| 条件 | 作用 |
|------|------|
| `is_valid` | 确保 SpanContext 有效，不是无效占位符 |
| `is_recording` | 确保 Span 仍在记录中，未结束 |
| `isinstance(current_span, ReadableSpan)` | 确保是可读的 Span 对象 |
| `attributes.get(...) == LLM` | 确认父 Span 类型是 LLM |

---

## 四、异步场景的上下文

### 4.1 Generator 的上下文保持

在 `_RunWrapper` 中，流式输出使用 Generator 模式：

```python
def wrapped_generator() -> Generator[str, None, None]:
    try:
        # Collect chunks for final output
        for chunk in agent_output:
            output_chunks.append(str(chunk))
            yield chunk
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace_api.StatusCode.ERROR)
        raise
    finally:
        # Generator 结束时清理
        span.set_attribute(OUTPUT_VALUE, ...)
        span.set_attribute(LLM_TOKEN_COUNT_PROMPT, ...)
        span.set_status(trace_api.StatusCode.OK)
        span.end()
        context_api.detach(token)

return wrapped_generator()
```

关键点：

1. **延迟清理**: detach 不在 `__call__` 中执行，而在 Generator 的 finally 中
2. **跨 yield 保持**: token 通过闭包保存在 wrapped_generator 中
3. **异常处理**: Generator 内部异常也需要清理上下文

### 4.2 流式输出的上下文传递

Generator 的执行流程：

```
调用方代码
    ↓
_RunWrapper.__call__
    ↓
attach Context → 返回 wrapped_generator
    ↓
调用方迭代 Generator
    ↓
每次 yield 保持 Context 不变
    ↓
Generator 结束 → finally 中 detach
```

为什么这种方式有效：

- Python Generator 在 yield 之间保持函数栈帧
- 闭包中的 token 不会丢失
- 调用方在迭代期间始终处于正确的 Context 中

### 4.3 多线程/异步的上下文

对于 asyncio 场景，OTel 的 `contextvars` 实现自动处理：

```python
import asyncio
from opentelemetry import context as context_api

async def async_task():
    # 自动继承调用方的 Context
    current_span = trace_api.get_current_span()
    ...

# Context 在 await 之间保持
await async_task()
```

对于线程池场景，需要显式传播：

```python
from opentelemetry.context import attach, detach, get_current

# 获取当前 Context
current_context = get_current()

def worker_func():
    # 在新线程中重新附加 Context
    token = attach(current_context)
    try:
        # 执行工作
        ...
    finally:
        detach(token)

# 提交到线程池
executor.submit(worker_func)
```

在 smolagents 中，如果使用了多线程，需要确保 Context 正确传递。目前源码主要针对单线程同步和异步 Generator 场景。

---

## 五、上下文隔离与清理

### 5.1 为什么必须 detach

不清理上下文的后果：

| 问题 | 原因 | 症状 |
|------|------|------|
| 上下文泄漏 | Context 栈不断增长 | 内存持续增长 |
| Trace 错乱 | 后续 Span 关联到错误的 parent | 调用链断裂或混乱 |
| 性能下降 | 查找当前 Context 变慢 | 响应时间增加 |

上下文栈的运作方式：

```
初始状态: [RootContext]

attach(A): [RootContext, A]
    ↓
attach(B): [RootContext, A, B]
    ↓
detach(B_token): [RootContext, A]  # 恢复到 A
    ↓
detach(A_token): [RootContext]      # 恢复到 Root
```

如果忘记 detach，栈会变成：

```
预期: [RootContext]
实际: [RootContext, A, B, ...]  # 不断增长
```

### 5.2 try-finally 的使用模式

正确的异常处理模式：

```python
try:
    result = wrapped(*args, **kwargs)
except Exception as e:
    # 记录异常信息
    span.record_exception(e)
    span.set_status(trace_api.StatusCode.ERROR)
    raise  # 重新抛出，不吞异常
finally:
    # 无论是否异常，都要执行清理
    span.end()
    context_api.detach(token)
```

`_RunWrapper` 的完整异常处理：

```python
try:
    agent_output = wrapped(*args, **kwargs)
except Exception as e:
    span.record_exception(e)
    span.set_status(trace_api.StatusCode.ERROR)
    raise

# 处理输出...

# 非流式场景的最终清理
finally:
    span.set_status(trace_api.StatusCode.OK)
    span.end()
    context_api.detach(token)
```

注意：流式场景的清理在 `wrapped_generator` 的 finally 中。

### 5.3 异常场景的处理

异常时的 Span 状态：

```python
except Exception as e:
    span.record_exception(e)           # 记录异常详情
    span.set_status(trace_api.StatusCode.ERROR)  # 设置错误状态
    raise                               # 继续传播异常
```

为什么异常时也要 detach：

1. 异常只影响当前调用，不影响后续操作
2. 如果不清理，后续所有 Span 都会关联到错误的 parent
3. 可能导致整个 Trace 无法正确结束

---

## 六、自定义属性传播

### 6.1 从上下文中获取属性

```python
from openinference.instrumentation import get_attributes_from_context

attributes = {
    **dict(get_attributes_from_context()),
    # 其他属性...
}
```

`get_attributes_from_context` 的作用：

- 从当前 Context 中提取预置的属性
- 通常包含 session_id、user_id 等全局信息
- 这些属性可能由上游中间件设置

### 6.2 设置自定义属性

```python
span.set_attribute("custom.key", value)
```

在 `_RunWrapper` 中设置 smolagents 特有属性：

```python
span = self._tracer.start_span(
    span_name,
    attributes=dict(
        _flatten({
            OPENINFERENCE_SPAN_KIND: AGENT,
            INPUT_VALUE: ...,
            "smolagents.task": agent.task,
            "smolagents.max_steps": agent.max_steps,
            "smolagents.tools_names": list(agent.tools.keys()),
            **dict(get_attributes_from_context()),
        })
    ),
)
```

### 6.3 属性的作用域

| 作用域 | 说明 | 示例 |
|--------|------|------|
| Span 级别 | 仅对当前 Span 有效 | `span.set_attribute` |
| Context 级别 | 通过 Context 传递，影响下游 | `get_attributes_from_context` |
| Baggage | 可跨服务传播 | `set_baggage`, `get_baggage` |

属性继承链：

```
Baggage → Context → Span Attributes
```

- Baggage 可配置跨服务传播
- Context 属性在同进程内传递
- Span Attributes 最终记录到追踪系统

---

## 七、多 Agent 调用的上下文传播

### 7.1 Manager-Managed 架构的上下文

在 smolagents 的 Manager-Managed 架构中，上下文传播形成树状结构：

![Span父子关系图](graphviz/smolagents-instrumentor-Span父子关系图.svg)

Trace 结构示例：

```
Trace: trace_id=abc123
├── Span: Manager.run (AGENT)
│   ├── Span: Step 1 (CHAIN)
│   │   ├── Span: Tool.web_search (TOOL)
│   │   └── Span: LLM.generate (LLM)
│   ├── Span: Step 2 (CHAIN)
│   │   ├── Span: Tool.web_search (TOOL)
│   │   └── Span: LLM.generate (LLM)
│   └── Span: Step 3 (CHAIN)
│       └── Span: Tool.managed_agent (TOOL)
│           └── Span: ManagedAgent.run (AGENT)
│               ├── Span: Step 1 (CHAIN)
│               │   └── Span: LLM.generate (LLM)
│               └── ...
```

上下文传播过程：

1. Manager.run 创建 Span，attach 到 Context
2. 执行 Step，自动继承 Manager 的 Span 作为 parent
3. Step 中调用 Tool，Tool Span 的 parent 是 Step
4. Tool 中调用 LLM，LLM Span 的 parent 是 Tool
5. 如果 Tool 是 ManagedAgent，新建的 AGENT Span 继续作为 parent

### 7.2 跨 Agent 的 TraceId 保持

全链路追踪的关键：所有 Span 共享同一个 TraceId。

```python
# Manager.run 中创建第一个 Span
manager_span = tracer.start_span("Manager.run")
# TraceId = abc123, SpanId = span001

# 设置到 Context
context = trace_api.set_span_in_context(manager_span)
context_api.attach(context)

# Step 中创建子 Span
step_span = tracer.start_span("Step 1")
# TraceId = abc123, SpanId = span002, ParentId = span001

# Tool 中创建子 Span
tool_span = tracer.start_span("Tool.web_search")
# TraceId = abc123, SpanId = span003, ParentId = span002

# ManagedAgent 中创建子 Span
managed_span = tracer.start_span("ManagedAgent.run")
# TraceId = abc123, SpanId = span004, ParentId = span003
```

通过 Context 的传递，TraceId 始终保持一致，形成完整的调用链。

---

## 八、常见陷阱与最佳实践

### 8.1 上下文泄漏

**症状**

- 内存持续增长
- Trace 显示为超长调用链
- Span 关联到错误的 parent

**原因**

- 忘记调用 `context_api.detach(token)`
- 异常路径未正确处理
- Generator 未正确结束

**解决方案**

```python
#  正确: 使用 try-finally
token = context_api.attach(context)
try:
    result = wrapped(*args, **kwargs)
finally:
    context_api.detach(token)

#  错误: 忘记 detach
token = context_api.attach(context)
result = wrapped(*args, **kwargs)
# 如果发生异常，detach 不会执行
```

### 8.2 并发问题

**多线程上下文混乱**

```python
#  错误: 新线程丢失 Context
def worker():
    span = trace_api.get_current_span()  # 返回 INVALID_SPAN

thread = threading.Thread(target=worker)
thread.start()

#  正确: 显式传递 Context
from opentelemetry.context import get_current, attach, detach

def worker(context):
    token = attach(context)
    try:
        span = trace_api.get_current_span()
        # ...
    finally:
        detach(token)

current_context = get_current()
thread = threading.Thread(target=worker, args=(current_context,))
thread.start()
```

**异步上下文丢失**

```python
#  错误: 在错误的上下文中创建 Span
async def task():
    asyncio.create_task(subtask())  # subtask 可能丢失 Context

#  正确: 使用 contextvars 传播
async def task():
    ctx = contextvars.copy_context()
    asyncio.create_task(subtask())  # 自动继承 Context
```

### 8.3 性能优化

**减少上下文切换**

```python
#  低效率: 频繁 attach/detach
for item in items:
    with tracer.start_as_current_span("process"):
        process(item)

#  高效率: 批量处理
with tracer.start_as_current_span("batch_process"):
    for item in items:
        process(item)
```

**使用 suppress 控制**

```python
# 在需要跳过追踪的场景
from opentelemetry import context as context_api

if context_api.get_value(context_api._SUPPRESS_INSTRUMENTATION_KEY):
    return wrapped(*args, **kwargs)  # 直接执行，不创建 Span
```

在 `_wrappers.py` 中，每个 Wrapper 都检查了这个标志，避免重复追踪。

---

## 九、总结

### 核心要点

1. **Context 是追踪的纽带**: 通过 Context 传递 TraceId 和 SpanId，建立调用链

2. **必须配对使用 attach/detach**: 使用 try-finally 确保上下文清理，防止泄漏

3. **Generator 需要特殊处理**: 清理逻辑放在 Generator 的 finally 块中，延迟执行

4. **防止重复追踪**: 使用 `_has_active_llm_parent_span` 检查，避免嵌套 LLM Span

5. **异常也要清理**: 无论是否发生异常，detach 必须执行

### 上下文传播流程图

![上下文传播流程图](graphviz/smolagents-instrumentor-上下文传播流程图.svg)

### 关键代码模式

```python
# 标准模式
def wrapper(wrapped, instance, args, kwargs):
    if context_api.get_value(context_api._SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)
    
    span = tracer.start_span(name, attributes=...)
    context = trace_api.set_span_in_context(span)
    token = context_api.attach(context)
    
    try:
        return wrapped(*args, **kwargs)
    except Exception as e:
        span.record_exception(e)
        span.set_status(trace_api.StatusCode.ERROR)
        raise
    finally:
        span.end()
        context_api.detach(token)

# 简洁模式
def wrapper(wrapped, instance, args, kwargs):
    if context_api.get_value(context_api._SUPPRESS_INSTRUMENTATION_KEY):
        return wrapped(*args, **kwargs)
    
    with tracer.start_as_current_span(name, attributes=...) as span:
        return wrapped(*args, **kwargs)
```

### 与其他 Instrumentor 的对比

| 特性 | smolagents | 其他框架 |
|------|------------|----------|
| Generator 支持 | 完整支持，延迟清理 | 部分支持 |
| LLM 嵌套检测 | 有 `_has_active_llm_parent_span` | 通常无 |
| 属性丰富度 | smolagents 特有属性 | 通用属性 |
| 抑制追踪 | 支持 `_SUPPRESS_INSTRUMENTATION_KEY` | 标准支持 |

OpenTelemetry 的上下文传播机制是分布式追踪的基础，理解其工作原理对于开发和调试 Instrumentor 至关重要。
