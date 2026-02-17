# smolagents Callback与事件机制深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/agents.py, memory.py

## 一、CallbackRegistry设计

### 1.1 核心数据结构

[[memory.py]] 中的 CallbackRegistry 类实现了回调注册表的核心功能：

```python
class CallbackRegistry:
    """Registry for callbacks that are called at each step of the agent's execution."""

    def __init__(self):
        self._callbacks: dict[Type[MemoryStep], list[Callable]] = {}
```

设计要点：

- 使用字典将 MemoryStep 类型映射到回调函数列表
- 支持同一类型注册多个回调函数
- 回调函数按注册顺序依次执行

### 1.2 register方法实现

```python
def register(self, step_cls: Type[MemoryStep], callback: Callable):
    """Register a callback for a step class."""
    if step_cls not in self._callbacks:
        self._callbacks[step_cls] = []
    self._callbacks[step_cls].append(callback)
```

该方法的特点：

- 延迟初始化：首次注册某类型时才创建列表
- 支持重复注册：同一回调可被多次注册
- 类型安全：使用 Type[MemoryStep] 确保注册到正确的步骤类型

### 1.3 __call__方法：回调触发逻辑

```python
def callback(self, memory_step, **kwargs):
    """Call callbacks registered for a step type."""
    # For compatibility with old callbacks that only take the step as an argument
    for cls in memory_step.__class__.__mro__:
        for cb in self._callbacks.get(cls, []):
            cb(memory_step) if len(inspect.signature(cb).parameters) == 1 else cb(memory_step, **kwargs)
```

关键设计决策：

- 使用 MRO：遍历类的整个继承链，支持父类回调
- 向后兼容：通过 inspect.signature 检测参数数量，兼容旧版单参数回调
- 灵活传参：支持传递额外参数如 agent 实例

## 二、step_callbacks机制

### 2.1 MultiStepAgent初始化参数

[[agents.py]] 第 282 行、304 行定义了 step_callbacks 参数：

```python
def __init__(
    self,
    ...
    step_callbacks: list[Callable] | dict[Type[MemoryStep], Callable | list[Callable]] | None = None,
    ...
):
```

参数类型支持两种格式：

- list 格式：所有回调仅针对 ActionStep
- dict 格式：键为步骤类型，值为回调或回调列表

### 2.2 _setup_step_callbacks方法实现

[[agents.py]] 第 416-434 行的实现：

```python
def _setup_step_callbacks(self, step_callbacks):
    # Initialize step callbacks registry
    self.step_callbacks = CallbackRegistry()
    if step_callbacks:
        # Register callbacks list only for ActionStep for backward compatibility
        if isinstance(step_callbacks, list):
            for callback in step_callbacks:
                self.step_callbacks.register(ActionStep, callback)
        # Register callbacks dict for specific step classes
        elif isinstance(step_callbacks, dict):
            for step_cls, callbacks in step_callbacks.items():
                if not isinstance(callbacks, list):
                    callbacks = [callbacks]
                for callback in callbacks:
                    self.step_callbacks.register(step_cls, callback)
        else:
            raise ValueError("step_callbacks must be a list or a dict")
    # Register monitor update_metrics only for ActionStep for backward compatibility
    self.step_callbacks.register(ActionStep, self.monitor.update_metrics)
```

配置逻辑解析：

- 始终初始化 CallbackRegistry 实例
- list 格式：为向后兼容，默认注册到 ActionStep
- dict 格式：允许精细控制不同步骤类型的回调
- 自动注册：monitor.update_metrics 被自动注册到 ActionStep

### 2.3 使用示例

list 格式用法：

```python
agent = CodeAgent(
    tools=[...],
    model=model,
    step_callbacks=[my_callback]  # 仅对 ActionStep 生效
)
```

dict 格式用法：

```python
agent = CodeAgent(
    tools=[...],
    model=model,
    step_callbacks={
        ActionStep: [callback1, callback2],
        PlanningStep: plan_callback,
        FinalAnswerStep: final_callback
    }
)
```

## 三、回调触发时机

### 3.1 _finalize_step方法

[[agents.py]] 第 620-623 行定义了回调触发点：

```python
def _finalize_step(self, memory_step: ActionStep | PlanningStep | FinalAnswerStep):
    if not isinstance(memory_step, FinalAnswerStep):
        memory_step.timing.end_time = time.time()
    self.step_callbacks.callback(memory_step, agent=self)
```

触发特点：

- 在每个步骤结束时触发
- FinalAnswerStep 不记录结束时间
- 总是传入 agent=self 供回调使用

### 3.2 各步骤类型的触发场景

#### ActionStep 触发点

[[agents.py]] 第 569-604 行的 _run_stream 方法：

```python
action_step = ActionStep(
    step_number=self.step_number,
    timing=Timing(start_time=action_step_start_time),
    observations_images=images,
)
...
try:
    for output in self._step_stream(action_step):
        ...
except AgentError as e:
    action_step.error = e
finally:
    self._finalize_step(action_step)  # 触发回调
    self.memory.steps.append(action_step)
```

ActionStep 触发时机：

- 无论成功或失败都在 finally 块中触发
- 步骤数据已完整填充，包括 tool_calls、observations、error 等
- 步骤尚未加入 memory.steps

#### PlanningStep 触发点

[[agents.py]] 第 553-567 行：

```python
for element in self._generate_planning_step(task, ...):
    yield element
    planning_step = element
...
planning_step.timing = Timing(start_time=planning_start_time, end_time=planning_end_time)
self._finalize_step(planning_step)  # 触发回调
self.memory.steps.append(planning_step)
```

PlanningStep 触发时机：

- 规划步骤生成完成后触发
- timing 信息已设置
- 回调可在步骤加入 memory 前修改数据

#### FinalAnswerStep 触发点

[[agents.py]] 第 609-611 行：

```python
final_answer_step = FinalAnswerStep(handle_agent_output_types(final_answer))
self._finalize_step(final_answer_step)
yield final_answer_step
```

FinalAnswerStep 触发时机：

- 最终答案生成后触发
- 不设置 timing.end_time
- 允许回调在最终答案返回前做最后处理

### 3.3 最大步骤数处理时的回调

[[agents.py]] 第 625-637 行的 _handle_max_steps_reached 方法：

```python
def _handle_max_steps_reached(self, task: str) -> Any:
    action_step_start_time = time.time()
    final_answer = self.provide_final_answer(task)
    final_memory_step = ActionStep(
        step_number=self.step_number,
        error=AgentMaxStepsError("Reached max steps.", self.logger),
        timing=Timing(start_time=action_step_start_time, end_time=time.time()),
        token_usage=final_answer.token_usage,
    )
    final_memory_step.action_output = final_answer.content
    self._finalize_step(final_memory_step)  # 触发回调
    self.memory.steps.append(final_memory_step)
    return final_answer.content
```

此场景特点：

- 步骤带有 AgentMaxStepsError 错误
- 仍触发回调，允许记录或处理超限情况
- 回调可访问 action_output 中的最终答案

## 四、回调函数签名

### 4.1 标准签名

推荐的双参数签名：

```python
def callback(memory_step: ActionStep, agent: MultiStepAgent) -> None:
    ...
```

兼容的单参数签名：

```python
def callback(memory_step: ActionStep) -> None:
    ...
```

### 4.2 访问和修改 agent.memory

回调函数可通过 agent 参数访问和修改记忆：

```python
def my_callback(memory_step: ActionStep, agent: MultiStepAgent) -> None:
    # 访问历史步骤
    for step in agent.memory.steps:
        if isinstance(step, ActionStep):
            print(f"Step {step.step_number}: {step.observations}")
    
    # 修改当前步骤
    memory_step.observations += "\n[Callback added note]"
    
    # 访问系统提示
    system_prompt = agent.memory.system_prompt.system_prompt
```

### 4.3 步骤数据的访问路径

ActionStep 数据字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| step_number | int | 步骤序号 |
| timing | Timing | 时间统计 |
| model_input_messages | list[ChatMessage] | 模型输入 |
| tool_calls | list[ToolCall] | 工具调用 |
| error | AgentError | 错误信息 |
| model_output_message | ChatMessage | 模型输出消息 |
| model_output | str | 模型输出文本 |
| code_action | str | 代码动作 |
| observations | str | 观察结果 |
| observations_images | list[PIL.Image] | 观察图像 |
| action_output | Any | 动作输出 |
| token_usage | TokenUsage | Token 使用统计 |
| is_final_answer | bool | 是否最终答案 |

## 五、实际应用案例

### 5.1 vision_web_browser中的update_screenshot

[[vision_web_browser.py]] 第 66-84 行的 save_screenshot 回调：

```python
def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
    sleep(1.0)  # Let JavaScript animations happen before taking the screenshot
    driver = helium.get_driver()
    current_step = memory_step.step_number
    if driver is not None:
        # Remove previous screenshots from logs for lean processing
        for previous_memory_step in agent.memory.steps:
            if isinstance(previous_memory_step, ActionStep) and previous_memory_step.step_number <= current_step - 2:
                previous_memory_step.observations_images = None
        png_bytes = driver.get_screenshot_as_png()
        image = PIL.Image.open(BytesIO(png_bytes))
        print(f"Captured a browser screenshot: {image.size} pixels")
        memory_step.observations_images = [image.copy()]

    # Update observations with current URL
    url_info = f"Current url: {driver.current_url}"
    memory_step.observations = (
        url_info if memory_step.observations is None else memory_step.observations + "\n" + url_info
    )
    return
```

应用场景分析：

- 浏览器自动化：每次步骤后自动截图
- Token 优化：删除两步之前的截图，控制上下文大小
- 信息增强：追加当前 URL 到观察结果

注册方式 [[vision_web_browser.py]] 第 154 行：

```python
agent = CodeAgent(
    tools=[WebSearchTool(), go_back, close_popups, search_item_ctrl_f],
    model=model,
    additional_authorized_imports=["helium"],
    step_callbacks=[save_screenshot],  # 注册回调
    max_steps=20,
    verbosity_level=2,
)
```

### 5.2 动态修改记忆的典型模式

删除旧截图节省 Token 的核心逻辑：

```python
current_step = memory_step.step_number
for previous_memory_step in agent.memory.steps:
    if isinstance(previous_memory_step, ActionStep) and previous_memory_step.step_number <= current_step - 2:
        previous_memory_step.observations_images = None
```

设计意图：

- 只保留最近两步的截图，避免视觉 Token 过度累积
- 直接修改 memory.steps 中的历史步骤对象
- 不影响当前步骤的截图捕获

### 5.3 监控和日志场景

自定义监控回调示例：

```python
def monitoring_callback(memory_step: ActionStep, agent: MultiStepAgent) -> None:
    """记录步骤执行指标"""
    if memory_step.token_usage:
        print(f"Step {memory_step.step_number}: "
              f"input_tokens={memory_step.token_usage.input_tokens}, "
              f"output_tokens={memory_step.token_usage.output_tokens}")
    
    if memory_step.error:
        print(f"Step {memory_step.step_number} failed: {memory_step.error}")

def planning_monitor(planning_step: PlanningStep, agent: MultiStepAgent) -> None:
    """监控规划步骤"""
    print(f"Planning updated at step {agent.step_number}")
    print(f"Plan content: {planning_step.plan[:100]}...")
```

### 5.4 条件性回调处理

根据步骤状态执行不同逻辑：

```python
def conditional_callback(memory_step: ActionStep, agent: MultiStepAgent) -> None:
    # 只在最终答案步骤执行
    if memory_step.is_final_answer:
        print("Final answer reached!")
        return
    
    # 只在出错时执行
    if memory_step.error:
        print(f"Error occurred: {memory_step.error}")
        # 可以在这里发送告警通知
        return
    
    # 正常步骤的处理
    if memory_step.tool_calls:
        for tc in memory_step.tool_calls:
            print(f"Tool called: {tc.name}")
```

## 六、设计模式分析

### 6.1 与Observer模式的对比

传统 Observer 模式特点：

- 主题维护观察者列表
- 观察者实现统一接口
- 主题状态变化时通知所有观察者
- 观察者被动接收通知

smolagents 的设计差异：

| 特性 | 传统 Observer | smolagents Callback |
|------|--------------|---------------------|
| 注册方式 | 观察者订阅主题 | 按步骤类型注册回调 |
| 触发时机 | 状态变化时 | 步骤结束时 |
| 参数传递 | 推送状态数据 | 传递步骤对象和 agent |
| 回调能力 | 只读观察 | 可修改步骤和 memory |
| 返回值 | 无 | 无 |

### 6.2 smolagents的设计选择

选择 CallbackRegistry 而非 EventEmitter：

- 类型安全：通过 MemoryStep 类型精确控制回调触发范围
- 执行顺序：列表保证回调按注册顺序执行
- 灵活传参：通过 **kwargs 支持扩展参数
- 向后兼容：inspect.signature 检测支持新旧回调共存

选择步骤结束时触发而非事件流：

- 数据完整性：步骤数据已完整填充
- 确定性：每个步骤只触发一次
- 简化模型：避免事件流的复杂性

### 6.3 扩展性和灵活性分析

当前设计的优势：

- 支持任意数量的回调函数
- 回调可修改步骤数据，影响后续执行
- 通过 MRO 支持继承链上的回调
- 参数检测机制支持平滑演进

潜在扩展方向：

- 支持异步回调
- 添加回调优先级机制
- 支持回调链中断
- 添加前置回调钩子

## 七、对我们项目的启示

### 7.1 设计借鉴

CallbackRegistry 模式值得借鉴的方面：

- 类型驱动的回调注册：按步骤类型分组回调
- 向后兼容设计：通过参数检测支持旧接口
- 执行时机选择：在步骤结束时触发，确保数据完整

### 7.2 应用场景映射

在我们的 AI数据分析系统 中可应用的场景：

- 数据访问审计：通过回调记录数据访问日志
- 执行监控：实时跟踪分析步骤的执行状态
- 结果验证：在最终答案前执行数据校验
- Token 管理：动态清理历史上下文控制成本

### 7.3 实现建议

参考 smolagents 的实现要点：

- 定义清晰的步骤类型基类
- 使用 MRO 遍历支持继承
- 通过 inspect 实现参数兼容性
- 在关键生命周期点设置回调触发

---

参考文档：
- [[memory.py|smolagents memory.py 源码]]
- [[agents.py|smolagents agents.py 源码]]
- [[vision_web_browser.py|浏览器自动化示例]]
