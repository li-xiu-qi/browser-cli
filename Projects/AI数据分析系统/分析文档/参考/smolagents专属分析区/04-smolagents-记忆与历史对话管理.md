# smolagents 记忆与历史对话管理深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/memory.py, agent_types.py

---

## 一、MemoryStep类型体系

### 1.1 类型继承结构

smolagents 的记忆系统基于面向对象设计，采用类型化步骤记录执行过程：

```
MemoryStep (抽象基类)
├── SystemPromptStep    # 系统提示
├── TaskStep            # 任务定义  
├── PlanningStep        # 规划步骤
├── ActionStep          # 动作步骤 (核心)
└── FinalAnswerStep     # 最终答案
```

所有步骤类型均继承自 `MemoryStep`，该基类定义了统一的接口：

```python
@dataclass
class MemoryStep:
    def dict(self):
        """将步骤序列化为字典"""
        return asdict(self)

    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        """将步骤转换为聊天消息格式，用于模型输入"""
        raise NotImplementedError
```

### 1.2 SystemPromptStep: 系统提示

用于存储Agent的系统提示信息，是每次对话的起始点：

```python
@dataclass
class SystemPromptStep(MemoryStep):
    system_prompt: str

    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        if summary_mode:
            return []  # 摘要模式下省略系统提示
        return [ChatMessage(role=MessageRole.SYSTEM, content=[...])]
```

在 `summary_mode=True` 时返回空列表，这意味着规划步骤不需要重复接收系统提示。

### 1.3 TaskStep: 任务定义

记录用户输入的任务描述，支持多模态输入：

```python
@dataclass
class TaskStep(MemoryStep):
    task: str
    task_images: list["PIL.Image.Image"] | None = None

    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        content = [{"type": "text", "text": f"New task:\n{self.task}"}]
        if self.task_images:
            content.extend([{"type": "image", "image": image} for image in self.task_images])
        return [ChatMessage(role=MessageRole.USER, content=content)]
```

### 1.4 PlanningStep: 规划步骤

在规划间隔触发时生成，用于Agent制定或更新执行计划：

```python
@dataclass
class PlanningStep(MemoryStep):
    model_input_messages: list[ChatMessage]
    model_output_message: ChatMessage
    plan: str
    timing: Timing
    token_usage: TokenUsage | None = None
```

其 `to_messages` 方法设计有特点：

```python
def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
    if summary_mode:
        return []  # 摘要模式下完全省略规划步骤
    return [
        ChatMessage(role=MessageRole.ASSISTANT, content=[{"type": "text", "text": self.plan.strip()}]),
        ChatMessage(role=MessageRole.USER, content=[{"type": "text", "text": "Now proceed and carry out this plan."}]),
    ]
```

注释说明了第二条消息的作用：**防止模型继续生成规划内容而不执行**，通过角色切换强制模型进入执行模式。

### 1.5 FinalAnswerStep: 最终答案

标记对话结束，存储最终结果：

```python
@dataclass
class FinalAnswerStep(MemoryStep):
    output: Any
```

注意该类未实现 `to_messages` 方法，因为它仅用于结果返回，不进入对话历史。

---

## 二、ActionStep详细解析

### 2.1 完整字段结构

`ActionStep` 是整个记忆系统的核心，记录了ReAct循环中单个步骤的完整信息：

```python
@dataclass
class ActionStep(MemoryStep):
    step_number: int                           # 步骤序号
    timing: Timing                             # 执行时间记录
    model_input_messages: list[ChatMessage] | None = None      # 输入给模型的消息
    tool_calls: list[ToolCall] | None = None                   # 工具调用列表
    error: AgentError | None = None                            # 执行错误
    model_output_message: ChatMessage | None = None            # 模型原始输出
    model_output: str | list[dict[str, Any]] | None = None     # 解析后的输出
    code_action: str | None = None                             # CodeAgent的代码
    observations: str | None = None                            # 观察结果文本
    observations_images: list["PIL.Image.Image"] | None = None # 观察结果图片
    action_output: Any = None                                  # 动作输出
    token_usage: TokenUsage | None = None                      # Token使用量
    is_final_answer: bool = False                              # 是否为最终答案
```

### 2.2 序列化实现

`ActionStep` 重写了 `dict` 方法，实现自定义序列化逻辑：

```python
def dict(self):
    return {
        "step_number": self.step_number,
        "timing": self.timing.dict(),
        "model_input_messages": [
            make_json_serializable(get_dict_from_nested_dataclasses(msg)) 
            for msg in self.model_input_messages
        ] if self.model_input_messages else None,
        "tool_calls": [tc.dict() for tc in self.tool_calls] if self.tool_calls else [],
        "error": self.error.dict() if self.error else None,
        "model_output_message": make_json_serializable(...),
        "model_output": self.model_output,
        "code_action": self.code_action,
        "observations": self.observations,
        "observations_images": [image.tobytes() for image in self.observations_images]
            if self.observations_images else None,
        "action_output": make_json_serializable(self.action_output),
        "token_usage": asdict(self.token_usage) if self.token_usage else None,
        "is_final_answer": self.is_final_answer,
    }
```

关键处理点：
- 图片数据被转换为字节数组存储
- 使用 `make_json_serializable` 确保复杂对象可JSON序列化
- 嵌套dataclass通过 `get_dict_from_nested_dataclasses` 处理

### 2.3 消息转换逻辑

`to_messages` 方法是核心转换逻辑，将步骤信息转换为模型可理解的对话格式：

```python
def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
    messages = []
    
    # 1. 添加模型输出 (非摘要模式)
    if self.model_output is not None and not summary_mode:
        messages.append(
            ChatMessage(role=MessageRole.ASSISTANT, content=[...])
        )

    # 2. 添加工具调用信息
    if self.tool_calls is not None:
        messages.append(
            ChatMessage(
                role=MessageRole.TOOL_CALL,
                content=[{"type": "text", "text": "Calling tools:\n" + ...}]
            )
        )

    # 3. 添加观察图片
    if self.observations_images:
        messages.append(
            ChatMessage(role=MessageRole.USER, content=[{"type": "image", ...}])
        )

    # 4. 添加观察文本
    if self.observations is not None:
        messages.append(
            ChatMessage(role=MessageRole.TOOL_RESPONSE, content=[...])
        )
    
    # 5. 添加错误信息
    if self.error is not None:
        error_message = (
            "Error:\n" + str(self.error)
            + "\nNow let's retry: take care not to repeat previous errors! "
            + "If you have retried several times, try a completely different approach.\n"
        )
        messages.append(
            ChatMessage(role=MessageRole.TOOL_RESPONSE, content=[...])
        )

    return messages
```

消息角色设计：
- `ASSISTANT`: 模型输出
- `TOOL_CALL`: 工具调用声明
- `USER`: 图片输入
- `TOOL_RESPONSE`: 工具执行结果或错误反馈

---

## 三、记忆流转机制

### 3.1 记忆写入消息流程

`write_memory_to_messages` 方法负责将整个记忆系统转换为模型输入消息序列：

```python
def write_memory_to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
    """
    从记忆中读取历史输出、动作和观察/错误信息，
    转换为LLM输入消息序列。添加关键词如 PLAN、error 等帮助LLM理解。
    """
    messages = self.memory.system_prompt.to_messages(summary_mode=summary_mode)
    for memory_step in self.memory.steps:
        messages.extend(memory_step.to_messages(summary_mode=summary_mode))
    return messages
```

### 3.2 序列化流程图示

```
┌─────────────────────────────────────────────────────────────────────┐
│                     记忆到消息的转换流程                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   AgentMemory                                                        │
│   ├── system_prompt: SystemPromptStep ──────▶ system message        │
│   └── steps: list[MemoryStep]                                        │
│       │                                                             │
│       ├── TaskStep ─────────────────────────▶ user message          │
│       │         "New task: ..."                                      │
│       │                                                             │
│       ├── PlanningStep ─────────────────────▶ assistant + user      │
│       │         "Here is the plan..." + "Now proceed..."            │
│       │                                                             │
│       └── ActionStep ───────────────────────▶ multi messages        │
│                 ├── model_output ──────────▶ assistant              │
│                 ├── tool_calls ────────────▶ tool_call              │
│                 ├── observations_images ───▶ user (images)          │
│                 └── observations/error ────▶ tool_response          │
│                                                                     │
│   最终输出: list[ChatMessage] 用于模型输入                          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 上下文长度管理策略

smolagents采用 **摘要模式** 来控制上下文长度，主要通过两种方式：

**方式一：规划时的摘要模式**

在更新规划时，使用 `summary_mode=True` 来精简历史：

```python
# _generate_planning_step 方法中
memory_messages = self.write_memory_to_messages(summary_mode=True)
```

在摘要模式下：
- `SystemPromptStep` 返回空列表
- `PlanningStep` 返回空列表 (避免历史规划干扰新规划)
- 只有 `TaskStep` 和 `ActionStep` 的核心信息保留

**方式二：目前无自动截断机制**

与DB-GPT等不同，smolagents **没有内置的上下文截断或压缩机制**。当对话历史超过模型上下文窗口时，会由底层模型API处理或抛出错误。

---

## 四、对话生命周期

### 4.1 完整生命周期图示

```
┌─────────────────────────────────────────────────────────────────────┐
│                       对话生命周期流程                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  初始化阶段                                                          │
│  ============                                                        │
│  ┌──────────────┐                                                   │
│  │ 创建Agent实例 │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│  ┌──────▼───────┐                                                   │
│  │ AgentMemory  │  初始化 system_prompt                             │
│  │   __init__   │  steps = []                                       │
│  └──────────────┘                                                   │
│                                                                     │
│  启动阶段                                                            │
│  =========                                                           │
│         │                                                           │
│  ┌──────▼───────┐     ┌─────────────────┐                          │
│  │  agent.run   │────▶│   TaskStep      │  用户任务进入记忆          │
│  │   (task)     │     │  task, images   │                          │
│  └──────────────┘     └─────────────────┘                          │
│                                                                     │
│  执行阶段 (ReAct循环)                                                │
│  ===================                                                 │
│         │                                                           │
│  ┌──────▼───────┐     规划间隔到达时触发                              │
│  │ PlanningStep │────────────────────────────────────┐              │
│  │  (可选)      │                                    │              │
│  └──────────────┘                                    │              │
│                                                      │              │
│  ┌──────────────┐     每个执行步骤                    │              │
│  │  ActionStep  │◀───────────────────────────────────┘              │
│  │ step_number  │                                                   │
│  │ model_input  │────▶ 模型生成                                     │
│  │ model_output │◀──── 返回结果                                     │
│  │ tool_calls   │────▶ 执行工具                                     │
│  │ observations │◀──── 观察结果                                     │
│  │ token_usage  │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         │ 错误处理                                                   │
│         │ ────────▶ error 字段记录异常信息                            │
│         │           循环继续                                         │
│         │                                                           │
│         │ 是否完成?                                                  │
│         │ ────────────────────────────────────▶ 否: 继续循环         │
│         │                                                           │
│  结束阶段                                                            │
│  =========                                                           │
│         │ 是                                                        │
│  ┌──────▼───────┐                                                   │
│  │ FinalAnswer  │  标记最终结果                                      │
│  │    Step      │                                                   │
│  └──────────────┘                                                   │
│         │                                                           │
│  ┌──────▼───────┐                                                   │
│  │  RunResult   │  返回完整执行结果                                  │
│  │   output     │  包含 steps, token_usage, timing                  │
│  └──────────────┘                                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 代码级别的生命周期

**初始化阶段** (`__init__`):

```python
def __init__(self, system_prompt: str):
    self.system_prompt: SystemPromptStep = SystemPromptStep(system_prompt=system_prompt)
    self.steps: list[TaskStep | ActionStep | PlanningStep] = []
```

**启动阶段** (`run` 方法):

```python
def run(self, task: str, ...):
    self.memory.system_prompt = SystemPromptStep(system_prompt=self.system_prompt)
    if reset:
        self.memory.reset()          # 清空历史步骤
        self.monitor.reset()
    
    # 添加任务步骤
    self.memory.steps.append(TaskStep(task=self.task, task_images=images))
```

**执行阶段** (`_run_stream` 方法):

```python
def _run_stream(self, task: str, max_steps: int):
    self.step_number = 1
    returned_final_answer = False
    
    while not returned_final_answer and self.step_number <= max_steps:
        # 规划步骤 (可选)
        if self.planning_interval is not None and should_plan:
            planning_step = self._generate_planning_step(task, ...)
            self.memory.steps.append(planning_step)
        
        # 动作步骤
        action_step = ActionStep(step_number=self.step_number, ...)
        try:
            for output in self._step_stream(action_step):
                yield output
                if isinstance(output, ActionOutput) and output.is_final_answer:
                    returned_final_answer = True
                    action_step.is_final_answer = True
        except AgentError as e:
            action_step.error = e          # 记录错误但不中断
        finally:
            self._finalize_step(action_step)
            self.memory.steps.append(action_step)
            self.step_number += 1
```

**结束阶段**:

```python
# 达到最终答案或最大步数
final_answer_step = FinalAnswerStep(handle_agent_output_types(final_answer))
self._finalize_step(final_answer_step)
yield final_answer_step
```

### 4.3 错误处理机制

错误被捕获并记录在 `ActionStep.error` 字段，而不是终止整个对话：

```python
except AgentGenerationError as e:
    # 生成错误是代码问题，需要抛出
    raise e
except AgentError as e:
    # 其他Agent错误是模型问题，记录后继续
    action_step.error = e
```

这种设计允许Agent在出错后自我修正，继续尝试完成任务。

---

## 五、记忆重放与查看

### 5.1 replay方法

`AgentMemory` 提供 `replay` 方法用于可视化查看执行历史：

```python
def replay(self, logger: AgentLogger, detailed: bool = False):
    """
    打印Agent步骤的美观回放
    
    Args:
        logger: 用于打印日志的日志器
        detailed: 为True时显示每个步骤的详细内存信息
            注意: 会指数级增加日志长度，仅用于调试
    """
    logger.console.log("Replaying the agent's steps:")
    logger.log_markdown(title="System prompt", content=self.system_prompt.system_prompt, level=LogLevel.ERROR)
    
    for step in self.steps:
        if isinstance(step, TaskStep):
            logger.log_task(step.task, "", level=LogLevel.ERROR)
        elif isinstance(step, ActionStep):
            logger.log_rule(f"Step {step.step_number}", level=LogLevel.ERROR)
            if detailed and step.model_input_messages is not None:
                logger.log_messages(step.model_input_messages, level=LogLevel.ERROR)
            if step.model_output is not None:
                logger.log_markdown(title="Agent output:", content=step.model_output, level=LogLevel.ERROR)
        elif isinstance(step, PlanningStep):
            logger.log_rule("Planning step", level=LogLevel.ERROR)
            if detailed and step.model_input_messages is not None:
                logger.log_messages(step.model_input_messages, level=LogLevel.ERROR)
            logger.log_markdown(title="Agent output:", content=step.plan, level=LogLevel.ERROR)
```

### 5.2 获取步骤数据

**获取简略步骤** (`get_succinct_steps`):

```python
def get_succinct_steps(self) -> list[dict]:
    """返回简略的步骤表示，排除model_input_messages以节省空间"""
    return [
        {key: value for key, value in step.dict().items() if key != "model_input_messages"}
        for step in self.steps
    ]
```

**获取完整步骤** (`get_full_steps`):

```python
def get_full_steps(self) -> list[dict]:
    """返回完整的步骤表示，包括model_input_messages"""
    if len(self.steps) == 0:
        return []
    return [step.dict() for step in self.steps]
```

### 5.3 代码提取功能

`return_full_code` 方法用于提取CodeAgent执行的所有代码：

```python
def return_full_code(self) -> str:
    """返回Agent步骤中所有代码动作的拼接结果"""
    return "\n\n".join([
        step.code_action 
        for step in self.steps 
        if isinstance(step, ActionStep) and step.code_action is not None
    ])
```

### 5.4 回调注册机制

`CallbackRegistry` 支持在特定步骤类型触发时执行回调：

```python
class CallbackRegistry:
    def __init__(self):
        self._callbacks: dict[Type[MemoryStep], list[Callable]] = {}

    def register(self, step_cls: Type[MemoryStep], callback: Callable):
        """为特定步骤类型注册回调"""
        if step_cls not in self._callbacks:
            self._callbacks[step_cls] = []
        self._callbacks[step_cls].append(callback)

    def callback(self, memory_step, **kwargs):
        """执行注册在步骤类型上的所有回调"""
        for cls in memory_step.__class__.__mro__:
            for cb in self._callbacks.get(cls, []):
                cb(memory_step) if len(inspect.signature(cb).parameters) == 1 else cb(memory_step, **kwargs)
```

在Agent初始化时，默认注册监控回调：

```python
def _setup_step_callbacks(self, step_callbacks):
    self.step_callbacks = CallbackRegistry()
    # ... 注册用户回调 ...
    # 默认注册监控回调
    self.step_callbacks.register(ActionStep, self.monitor.update_metrics)
```

---

## 六、持久化策略

### 6.1 当前设计：无内置持久化

**关键发现**：smolagents的记忆系统完全是**内存中**的，不提供内置的持久化机制。

证据：
- `AgentMemory` 类没有保存/加载方法
- `steps` 列表是纯Python列表，进程结束即丢失
- 每次调用 `run(reset=True)` 会清空历史

### 6.2 临时状态管理

虽然Agent本身不提供持久化，但提供了运行级别的结果返回：

```python
@dataclass
class RunResult:
    output: Any | None
    state: Literal["success", "max_steps_error"]
    steps: list[dict]           # 完整步骤数据
    token_usage: TokenUsage | None
    timing: Timing
```

通过 `return_full_result=True` 可以获取：

```python
result = agent.run("任务", return_full_result=True)
# result.steps 包含所有步骤的序列化数据
```

### 6.3 外部持久化方案

**方案一：手动保存RunResult**

```python
import json

result = agent.run("任务", return_full_result=True)

# 保存到文件
with open("conversation.json", "w") as f:
    json.dump(result.dict(), f, indent=2)

# 从文件恢复
with open("conversation.json", "r") as f:
    data = json.load(f)
```

**方案二：步骤回调实时保存**

```python
def save_step_callback(step: ActionStep):
    with open("steps.log", "a") as f:
        f.write(json.dumps(step.dict()) + "\n")

agent = CodeAgent(tools=[...], model=..., step_callbacks=[save_step_callback])
```

**方案三：自定义记忆类**

```python
class PersistentAgentMemory(AgentMemory):
    def __init__(self, system_prompt: str, storage_path: str):
        super().__init__(system_prompt)
        self.storage_path = storage_path
        self._load()
    
    def _load(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                # 反序列化步骤...
    
    def _save(self):
        with open(self.storage_path, "w") as f:
            json.dump(self.get_full_steps(), f)
    
    def append(self, step: MemoryStep):
        self.steps.append(step)
        self._save()  # 实时保存
```

---

## 七、对我们项目的启示

### 7.1 值得借鉴的设计

**1. 类型化的步骤系统**

smolagents使用具体的dataclass而非松散的字典来存储步骤，优势：
- 编译时类型检查
- IDE自动补全
- 清晰的字段语义

**2. 双模式消息转换**

```python
def to_messages(self, summary_mode: bool = False)
```

这种设计允许在规划时精简历史，减少干扰，同时保留完整历史用于执行。

**3. 错误内聚而非中断**

将错误记录在步骤中而非立即终止，支持Agent自我修正：

```python
action_step.error = e
# 继续循环，让模型有机会重试
```

**4. 丰富的元数据追踪**

每个步骤记录：
- `timing`: 执行时间
- `token_usage`: Token消耗
- `model_input_messages`: 完整输入上下文

这些对后续分析和优化非常有价值。

### 7.2 需要改进的方面

**1. 缺乏上下文管理**

smolagents没有实现：
- 上下文窗口检测
- 历史截断策略
- Token预算管理

我们的项目应该考虑实现这些功能：

```python
class ContextManager:
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
    
    def prepare_messages(self, memory: AgentMemory) -> list[ChatMessage]:
        messages = memory.to_messages()
        total_tokens = sum(self.estimate_tokens(m) for m in messages)
        
        while total_tokens > self.max_tokens:
            # 策略：移除最早的ActionStep，保留TaskStep
            messages = self._compress(messages)
            total_tokens = sum(self.estimate_tokens(m) for m in messages)
        
        return messages
```

**2. 缺乏持久化抽象**

应该提供可选的持久化接口：

```python
class MemoryStorage(ABC):
    @abstractmethod
    def save(self, memory: AgentMemory): ...
    
    @abstractmethod
    def load(self) -> AgentMemory: ...

class SQLiteStorage(MemoryStorage): ...
class RedisStorage(MemoryStorage): ...
```

**3. 规划步骤的持久化问题**

当前规划步骤在 `summary_mode=True` 时被完全省略，可能丢失重要上下文。我们的项目可以考虑：
- 保留规划摘要而非完全省略
- 或者提供独立的规划历史追踪

### 7.3 推荐实现架构

基于smolagents的设计，建议我们的项目采用**分离式架构**，不直接继承 smolagents 的 `AgentMemory`，而是独立实现一个可复用的记忆管理类：

**设计原则**：
1. **分离式而非耦合式**：`ConversationMemory` 不继承 smolagents 的类，保持独立可复用
2. **组合而非继承**：通过组合 `MemoryStep` 对象来存储历史，而非继承框架类
3. **适配器模式**：通过适配器将 `ConversationMemory` 转换为 smolagents 需要的格式

```python
# ============================================
# 核心记忆类 - 完全独立于 smolagents 框架
# ============================================
class ConversationMemory:
    """
    独立实现的对话记忆管理类
    
    设计特点：
    - 不依赖 smolagents.AgentMemory
    - 可复用于任何需要对话管理的场景
    - 通过适配器与 smolagents 集成
    """
    
    def __init__(self, system_prompt: str, storage: MemoryStorage | None = None):
        self.system_prompt = SystemPromptStep(system_prompt)
        self.steps: list[MemoryStep] = []
        self.storage = storage
        if storage:
            self._load()
    
    def add_step(self, step: MemoryStep):
        """添加步骤并自动持久化"""
        self.steps.append(step)
        if self.storage:
            self.storage.save(self)
    
    def to_messages(self, strategy: ContextStrategy = ContextStrategy.FULL) -> list[ChatMessage]:
        """支持多种上下文策略"""
        if strategy == ContextStrategy.FULL:
            return self._to_full_messages()
        elif strategy == ContextStrategy.SUMMARY:
            return self._to_summary_messages()
        elif strategy == ContextStrategy.SLIDING_WINDOW:
            return self._to_window_messages(max_steps=10)
    
    def replay(self) -> Iterator[MemoryStep]:
        """支持迭代器方式回放"""
        yield self.system_prompt
        for step in self.steps:
            yield step
    
    def to_smolagents_memory(self) -> AgentMemory:
        """
        转换为 smolagents 的 AgentMemory
        通过适配器模式实现与框架的集成
        """
        from smolagents.memory import AgentMemory
        memory = AgentMemory(self.system_prompt.system_prompt)
        memory.steps = self.steps.copy()
        return memory
    
    @classmethod
    def from_smolagents_memory(cls, agent_memory: AgentMemory, storage: MemoryStorage | None = None):
        """从 smolagents AgentMemory 创建"""
        instance = cls.__new__(cls)
        instance.system_prompt = agent_memory.steps[0] if agent_memory.steps else None
        instance.steps = [s for s in agent_memory.steps[1:] if hasattr(s, 'step_number')]
        instance.storage = storage
        return instance


# ============================================
# 上下文策略枚举
# ============================================
class ContextStrategy(Enum):
    FULL = "full"                    # 完整历史
    SUMMARY = "summary"              # 摘要模式
    SLIDING_WINDOW = "window"        # 滑动窗口
    TOKEN_BUDGET = "budget"          # Token预算


# ============================================
# 与 smolagents 集成的适配器
# ============================================
class SmolagentsMemoryAdapter:
    """
    适配器：将 ConversationMemory 与 smolagents Agent 集成
    
    使用示例：
        memory = ConversationMemory("你是一个助手", SQLiteStorage("db.sqlite"))
        adapter = SmolagentsMemoryAdapter(memory)
        
        agent = CodeAgent(
            model=model,
            tools=tools,
            memory=adapter.to_smolagents_memory()  # 转换后传入
        )
    """
    
    def __init__(self, conversation_memory: ConversationMemory):
        self.conv_memory = conversation_memory
        
    def to_smolagents_memory(self) -> AgentMemory:
        """转换为 smolagents AgentMemory"""
        return self.conv_memory.to_smolagents_memory()
    
    def sync_from_agent(self, agent_memory: AgentMemory):
        """从 Agent 执行后的记忆同步回来"""
        self.conv_memory.steps = [s for s in agent_memory.steps 
                                   if hasattr(s, 'step_number')]
        if self.conv_memory.storage:
            self.conv_memory.storage.save(self.conv_memory)


# ============================================
# 生产级使用模式
# ============================================
class ProductionCodeAgent:
    """
    生产级 Agent 封装，展示如何结合使用
    """
    
    def __init__(
        self,
        model,
        tools,
        memory: ConversationMemory,  # 使用我们自己的记忆类
        max_steps: int = 10
    ):
        self.model = model
        self.tools = tools
        self.memory = memory
        self.max_steps = max_steps
        self._adapter = SmolagentsMemoryAdapter(memory)
        
    def run(self, task: str) -> str:
        """执行并同步记忆"""
        # 创建 smolagents Agent，传入转换后的记忆
        agent = CodeAgent(
            model=self.model,
            tools=self.tools,
            memory=self._adapter.to_smolagents_memory(),
            max_steps=self.max_steps
        )
        
        # 执行
        result = agent.run(task)
        
        # 同步记忆回我们的系统
        self._adapter.sync_from_agent(agent.memory)
        
        return result
```

---

## 八、总结

### 8.1 核心设计特点

| 特性 | smolagents设计 | 评价 |
|------|---------------|------|
| **类型系统** | 使用dataclass定义具体步骤类型 | 清晰、类型安全 |
| **消息转换** | `to_messages` 方法实现步骤到消息转换 | 灵活、可扩展 |
| **摘要模式** | `summary_mode` 参数控制历史精简 | 简洁但功能有限 |
| **错误处理** | 错误记录在步骤中，循环继续 | 支持自我修正 |
| **持久化** | 无内置持久化 | 需要外部实现 |
| **元数据** | timing、token_usage等丰富追踪 | 便于分析 |

### 8.2 关键代码位置速查

| 功能 | 文件 | 行号 |
|------|------|------|
| MemoryStep基类 | memory.py | 42-47 |
| ActionStep定义 | memory.py | 51-65 |
| AgentMemory类 | memory.py | 214-277 |
| replay方法 | memory.py | 248-271 |
| write_memory_to_messages | agents.py | 758-770 |
| _run_stream生命周期 | agents.py | 540-611 |

### 8.3 相关参考文档

- [[01-smolagents-Agent架构深度分析]]
- [[smolagents-ReAct循环实现分析]]
- [[AI数据分析系统-对话管理设计]]

---

*文档生成时间: 2026-02-06*
*分析基于 smolagents 1.12.0 版本源码*
