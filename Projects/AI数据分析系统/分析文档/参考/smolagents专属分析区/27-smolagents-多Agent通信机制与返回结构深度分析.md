# smolagents 多Agent通信机制与返回结构深度分析

> 项目: smolagents  
> 分析日期: 2026-02-06  
> 源码位置: src/smolagents/agents.py, memory.py  
> 补充文档: [[06-smolagents-多Agent系统深度分析]]

---

## 一、通信机制总览

### 1.1 通信模型

smolagents的多Agent系统采用**同步函数调用**模型，而非消息队列或事件总线：

```
Manager Agent                        Managed Agent
     │                                    │
     │  1. 生成tool_call                  │
     │  {name: "sub_agent",               │
     │   arguments: {task: "..."}}        │
     │ ─────────────────────────────────>│
     │                                    │
     │  2. 调用__call__方法               │
     │     run() 执行完整Agent循环        │
     │                                    │
     │  3. 返回字符串结果                 │
     │ <─────────────────────────────────│
     │     result: str                    │
```

**关键特点**：

| 特性 | 说明 |
|------|------|
| 通信方式 | 同步函数调用 |
| 调用协议 | Tool-like接口，通过__call__方法 |
| 参数传递 | task字符串 + 可选additional_args |
| 返回类型 | 字符串 |
| 上下文隔离 | 子Agent独立维护自己的memory |

### 1.2 与Tool的通信对比

| 维度 | Tool调用 | Managed Agent调用 |
|------|----------|-------------------|
| 调用方式 | tool(**arguments) | agent.__call__(**arguments) |
| 执行时间 | 通常毫秒级 | 秒级到分钟级 |
| 状态保持 | 无状态 | 有状态，独立memory |
| 返回类型 | 任意类型 | 字符串 |
| 复杂度 | 简单函数执行 | 完整Agent循环 |
| Token消耗 | 低 | 高 |

---

## 二、调用流程详解

### 2.1 完整调用链

```python
# 步骤1: Manager生成调用决策
# Manager的模型输出：
tool_calls = [
    {
        "name": "search_agent",  # 子Agent名称
        "arguments": {
            "task": "搜索2024年电动车销量数据",
            "additional_args": None
        }
    }
]

# 步骤2: 调用execute_tool_call
result = manager.execute_tool_call("search_agent", {
    "task": "搜索2024年电动车销量数据"
})

# 步骤3: 内部调用链
execute_tool_call
    └─> is_managed_agent = True  # 识别为子Agent
    └─> tool = managed_agents["search_agent"]
    └─> tool(task="...")  # 调用__call__
        └─> MultiStepAgent.__call__  # agents.py line 193
            └─> build_managed_agent_prompt
            └─> self.run(full_task)  # 执行完整Agent循环
                └─> _run_stream / run
                    └─> 生成PlanningStep
                    └─> 生成ActionStep
                    └─> 生成FinalAnswerStep
            └─> 提取result.output
            └─> 格式化为report字符串

# 步骤4: 返回Manager
# result类型: str
# 内容示例: "根据搜索结果，2024年电动车销量为..."
```

### 2.2 关键代码分析

#### Manager侧调用代码

```python
# agents.py line 1464-1492
def execute_tool_call(self, tool_name: str, arguments):
    # 1. 获取tool或managed_agent
    available_tools = {**self.tools, **self.managed_agents}
    tool = available_tools[tool_name]
    
    # 2. 判断是否为managed_agent
    is_managed_agent = tool_name in self.managed_agents
    
    # 3. 参数处理差异
    if is_managed_agent:
        # 子Agent：直接传递参数
        return tool(**arguments)
    else:
        # 普通Tool：需要sanitize
        return tool(**arguments, sanitize_inputs_outputs=True)
```

#### 子Agent包装代码

```python
# agents.py line 193-215
class MultiStepAgent:
    def __call__(self, task: str, **kwargs):
        """
        当Agent作为Managed Agent被调用时执行
        添加额外prompting，运行Agent，包装输出
        """
        # 1. 构建完整任务描述
        full_task = self.prompt_templates["managed_agent"]["task"].format(
            name=self.name,
            task=task
        )
        
        # 2. 执行完整Agent循环
        result = self.run(full_task, **kwargs)
        
        # 3. 提取输出
        if isinstance(result, RunResult):
            report = result.output
        else:
            report = result
        
        # 4. 格式化为报告
        return self.prompt_templates["managed_agent"]["report"].format(
            name=self.name,
            final_answer=report
        )
```

---

## 三、返回结构深度解析

### 3.1 RunResult结构

```python
# agent_types.py 或 agents.py
@dataclass
class RunResult:
    output: Any                    # 最终输出内容
    token_usage: TokenUsage        # Token使用量
    timing: Timing                 # 时间统计
    steps: list[MemoryStep]        # 完整执行步骤

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int

@dataclass
class Timing:
    start_time: float
    end_time: float
    total_seconds: float
```

### 3.2 返回数据流转

```
子Agent执行完成
    │
    ├─> RunResult.output         # 提取最终答案
    │       │
    │       ▼
    │   prompt_templates["managed_agent"]["report"]  # 包装模板
    │       │
    │       ▼
    │   "Agent search_agent已完成任务。\n\n最终答案:\n{output}"
    │       │
    │       ▼
    └─> 字符串返回给Manager  # 类型: str

Manager接收
    │
    ├─> 将字符串作为observation  # 加入ActionStep.observations
    │
    ├─> 继续下一步推理
```

### 3.3 返回内容包装模板

```yaml
# agents.py line 873-882
managed_agent:
  task: |
    你是{name}，被Manager Agent调用。
    你的任务是：{task}
    请专注于完成这个具体任务，不要处理其他问题。
    
  report: |
    Agent {name} 已完成任务。
    
    最终答案:
    {final_answer}
```

**关键设计**：返回结果被包装为自然语言描述，便于Manager的LLM理解。

---

## 四、上下文与状态管理

### 4.1 Memory隔离

```python
# Manager和Managed Agent各自独立维护memory

Manager Agent Memory:
    SystemPromptStep
    TaskStep: "分析电动车市场"  # Manager的任务
    ActionStep 1:
        - tool_call: search_agent(task="搜索销量")
        - observation: "Agent search_agent已完成...最终答案:..."  # 子Agent返回
    ActionStep 2:
        - 继续Manager的推理

Managed Agent Memory:  # 完全隔离
    SystemPromptStep
    TaskStep: "你是search_agent...搜索销量"  # 子Agent的任务
    PlanningStep: 子Agent的规划
    ActionStep 1:
        - tool_call: web_search
        - observation: 搜索结果
    ActionStep 2:
        - tool_call: visit_webpage
        - observation: 页面内容
    FinalAnswerStep: "2024年销量为..."
```

**重要特性**：子Agent的完整执行历史对Manager不可见，Manager只能看到包装后的结果字符串。

### 4.2 上下文传递方式

| 传递方式 | 实现 | 用途 |
|----------|------|------|
| task字符串 | 通过arguments.task | 传递子任务描述 |
| additional_args | 通过arguments.additional_args | 传递额外上下文数据 |
| memory替换 | agent.memory.steps = ... | 完全替换子Agent的历史 |

**advanced_args示例**：

```python
# 传递额外上下文
result = manager.run(
    "分析数据",
    additional_args={
        "context": "这是额外背景信息",
        "user_id": "12345"
    }
)

# 在子Agent中通过callback访问
monitoring_callback(memory_step, agent):
    context = agent.task_additional_args  # 获取传递的上下文
```

---

## 五、调用链追踪与监控

### 5.1 Token使用追踪

```python
# 子Agent执行后的RunResult
run_result = managed_agent.run(task)

# Token使用统计
print(f"子Agent消耗: {run_result.token_usage.total_tokens} tokens")
# 输出: 子Agent消耗: 1523 tokens

# 注意：此统计不会自动汇总到Manager
# 需要手动实现跨Agent统计
```

### 5.2 OpenTelemetry集成

```python
# examples/inspect_multiagent_run.py
from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from phoenix.otel import register

register()
SmolagentsInstrumentor().instrument(skip_dep_check=True)

# 运行后会显示完整的调用链
# 可以看到Manager调用search_agent的span
# 以及search_agent内部执行的详细span
```

### 5.3 自定义监控方案

```python
# 跨Agent Token统计
def create_monitoring_callback(agent_name: str):
    def callback(memory_step, agent):
        if isinstance(memory_step, FinalAnswerStep):
            print(f"[{agent_name}] 完成，Token使用: {memory_step.token_usage}")
    return callback

# 为每个子Agent添加监控
search_agent = ToolCallingAgent(
    step_callbacks=[create_monitoring_callback("search_agent")]
)
```

---

## 六、错误处理与重试

### 6.1 子Agent失败处理

```python
# 场景：子Agent执行失败
# 结果：子Agent返回错误信息作为字符串

try:
    result = managed_agent(task)
except AgentError as e:
    # 子Agent内部错误
    error_msg = str(e)
    # 返回给Manager
    # Manager需要在Prompt中指导如何处理错误
```

### 6.2 超时处理

```python
# 子Agent执行可能耗时很长
# 当前设计没有内置超时机制
# 需要外部实现

import signal

def run_with_timeout(agent, task, timeout=60):
    def handler(signum, frame):
        raise TimeoutError("Agent执行超时")
    
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(timeout)
    
    try:
        result = agent(task)
        return result
    finally:
        signal.alarm(0)
```

---

## 七、性能特征

### 7.1 延迟分析

| 阶段 | 延迟来源 | 估算时间 |
|------|----------|----------|
| Manager决策 | LLM生成tool_call | 1-3s |
| 子Agent执行 | 完整Agent循环 | 10-60s |
| 结果返回 | 字符串格式化 | <1ms |
| 总计 |  | 11-63s |

### 7.2 Token消耗

| 组件 | Token消耗 | 可优化策略 |
|------|-----------|------------|
| Manager | ~500-1000 | 精简Prompt |
| 子Agent | ~1000-5000 | 限制max_steps |
| 结果包装 | ~50-100 | 固定开销 |
| **总计** | **~1550-6100** | 控制子Agent步数 |

---

## 八、设计优势与局限

### 8.1 优势

| 优势 | 说明 |
|------|------|
| 实现简单 | 同步函数调用，无需消息队列 |
| 易于理解 | 类似普通Tool调用 |
| 类型安全 | 明确输入输出类型 |
| 隔离性好 | 子Agent状态不污染Manager |

### 8.2 局限

| 局限 | 说明 | 改进方向 |
|------|------|----------|
| 上下文有限 | Manager看不到子Agent执行过程 | 增加详细模式返回更多信息 |
| 无并行支持 | 一次只能调用一个子Agent | Manager需多次调用实现并行 |
| 无法中断 | 子Agent一旦开始无法中断 | 添加interrupt机制传递 |
| Token消耗高 | 子Agent独立维护memory | 共享部分上下文 |

---

## 九、对我们项目的启示

### 9.1 推荐架构

```python
# AI数据分析系统多Agent架构
class DataAnalysisSystem:
    def __init__(self):
        # Manager：复杂分析规划
        self.analyzer = CodeAgent(
            model=strong_model,
            managed_agents=[
                self.sql_agent,
                self.api_agent,
                self.chart_agent
            ]
        )
        
        # 子Agent1：SQL查询专家
        self.sql_agent = ToolCallingAgent(
            name="sql_expert",
            description="执行SQL查询，返回结构化数据",
            tools=[SQLQueryTool(), DatabaseSchemaTool()],
            model=fast_model,
            max_steps=5  # 限制步数控制Token
        )
        
        # 子Agent2：API数据获取
        self.api_agent = ToolCallingAgent(
            name="api_fetcher", 
            description="从REST API获取数据",
            tools=[RestAPITool()],
            model=fast_model,
            max_steps=5
        )
        
        # 子Agent3：图表生成
        self.chart_agent = ToolCallingAgent(
            name="chart_generator",
            description="根据数据生成可视化图表",
            tools=[ChartTool()],
            model=fast_model,
            max_steps=3
        )
```

### 9.2 关键设计决策

| 决策 | 建议 |
|------|------|
| Manager选择 | 使用CodeAgent，擅长复杂推理和代码生成 |
| 子Agent选择 | 使用ToolCallingAgent，高效执行具体工具 |
| 模型配置 | Manager用强模型，子Agent可用轻量模型 |
| Token控制 | 限制子Agent的max_steps，减少消耗 |
| 错误处理 | 在Manager Prompt中明确错误处理策略 |
| 超时控制 | 外部实现超时机制，避免子Agent卡住 |

### 9.3 监控建议

```python
# 实现跨Agent调用链追踪
class MultiAgentMonitor:
    def __init__(self):
        self.call_tree = []
    
    def trace_call(self, parent, child, task):
        call_id = len(self.call_tree)
        self.call_tree.append({
            "id": call_id,
            "parent": parent,
            "child": child,
            "task": task,
            "start_time": time.time()
        })
        return call_id
    
    def trace_return(self, call_id, result, token_usage):
        self.call_tree[call_id].update({
            "end_time": time.time(),
            "result": result,
            "token_usage": token_usage
        })
```

---

## 十、总结

smolagents的多Agent通信机制采用**简洁的同步函数调用模型**：

1. **通信方式**：通过`__call__`方法实现Tool-like调用
2. **参数传递**：task字符串 + optional additional_args
3. **返回结构**：字符串（经模板包装后的RunResult.output）
4. **状态隔离**：子Agent维护独立的memory，Manager不可见
5. **调用链**：Manager → execute_tool_call → 子Agent.__call__ → 子Agent.run → 返回字符串

这种设计**简单有效**，但存在上下文传递有限、无法并行调用等局限。在生产环境中需要考虑超时控制、跨Agent监控等增强机制。

---

*补充文档：[[06-smolagents-多Agent系统深度分析]]*
