# smolagents 多 Agent 流式输出机制深度分析

**文档版本**: 1.1.0  
**更新内容**: 补充 step_callbacks 回调机制，说明如何通过回调获取子 Agent 输出  
**分析对象**: smolagents 源码  
**核心文件**: 
- [[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]]
- [[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/memory.py|memory.py]]

---

## 核心结论

> smolagents 的流式输出机制基于 Python Generator 实现，通过 `_run_stream` 方法逐级 yield 事件对象，实现多 Agent 场景下的事件透传与层级追踪。

---

## 一、多 Agent 流式输出架构

### 1.1 流式输出的层级传播机制

smolagents 的流式输出采用**嵌套 Generator 模式**，Manager Agent 在调用 Managed Agent 时，将子 Agent 的流式事件透传给上层。

**事件传播层级结构**

```
Manager Agent.run_stream()
    ├── yield PlanningStep              # 规划步骤事件
    ├── yield ActionStep                # 动作步骤事件
    │       └── 调用 Managed Agent
    │               └── Managed Agent.run_stream()
    │                       ├── yield ActionStep    # 子 Agent 步骤
    │                       ├── yield ToolOutput    # 工具输出
    │                       └── yield FinalAnswerStep
    ├── yield ChatMessageStreamDelta    # 流式文本片段
    └── yield FinalAnswerStep           # 最终答案
```

**关键代码位置**

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]] 第 540-611 行的 `_run_stream` 方法：

```python
def _run_stream(
    self, task: str, max_steps: int, images: list["PIL.Image.Image"] | None = None
) -> Generator[ActionStep | PlanningStep | FinalAnswerStep | ChatMessageStreamDelta]:
    self.step_number = 1
    returned_final_answer = False
    while not returned_final_answer and self.step_number <= max_steps:
        # 运行规划步骤
        if self.planning_interval is not None:
            for element in self._generate_planning_step(task, ...):
                yield element    # 透传 PlanningStep
                
        # 运行动作步骤
        action_step = ActionStep(...)
        for output in self._step_stream(action_step):
            yield output         # 透传 ActionStep 及其子事件
            
        yield action_step        # 步骤结束时再次 yield
```

### 1.2 流式事件的来源

**Manager Agent 自身产生的事件**

| 事件类型 | 产生位置 | 说明 |
|----------|----------|------|
| PlanningStep | `_generate_planning_step` | 规划阶段产生 |
| ActionStep | `_run_stream` | 每个动作步骤产生 |
| ChatMessageStreamDelta | `_step_stream` | 模型流式输出片段 |
| FinalAnswerStep | `_run_stream` 结尾 | 最终答案包装 |

**Managed Agent 产生的事件透传**

当 Manager Agent 调用 Managed Agent 时，子 Agent 的事件通过 `__call__` 方法返回，而非直接透传流式事件：

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]] 第 868-890 行：

```python
def __call__(self, task: str, **kwargs):
    """Managed Agent 的调用入口"""
    full_task = populate_template(
        self.prompt_templates["managed_agent"]["task"],
        variables=dict(name=self.name, task=task),
    )
    result = self.run(full_task, **kwargs)    # 内部调用，非流式透传
    # 包装返回结果
    answer = populate_template(
        self.prompt_templates["managed_agent"]["report"], 
        variables=dict(name=self.name, final_answer=report)
    )
    return answer
```

**重要发现**

> smolagents 当前版本的 Managed Agent **不会直接透传流式事件**，而是将子 Agent 的执行结果作为 Observation 返回给父 Agent。这意味着前端无法直接观察到子 Agent 的执行过程，只能看到最终结果。

### 1.3 通过回调获取子 Agent 输出

虽然 Managed Agent 的流式事件不会自动透传给父 Agent，但可以通过 **step_callbacks** 回调机制来获取子 Agent 的中间输出。

#### step_callbacks 机制

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]] 第 282-434 行定义了 step_callbacks 的实现：

```python
# Agent 初始化时传入回调
managed_agent = ToolCallingAgent(
    name="search_agent",
    description="搜索Agent",
    model=model,
    tools=[WebSearchTool()],
    # 方式1：列表形式，所有ActionStep都会触发
    step_callbacks=[callback_function],
    
    # 方式2：字典形式，按事件类型分发
    step_callbacks={
        ActionStep: [on_action_step],
        PlanningStep: [on_planning_step],
        FinalAnswerStep: [on_final_answer],
    }
)
```

#### 回调函数签名

```python
def step_callback(
    memory_step: ActionStep | PlanningStep | FinalAnswerStep,
    agent: MultiStepAgent
) -> None:
    """
    步骤回调函数
    
    Args:
        memory_step: 当前步骤的信息
        agent: 产生该步骤的Agent实例
    """
    # 获取步骤类型
    step_type = type(memory_step).__name__
    
    # 获取Agent名称
    agent_name = agent.name if hasattr(agent, 'name') else 'unknown'
    
    # 处理不同类型的步骤
    if isinstance(memory_step, ActionStep):
        print(f"[{agent_name}] ActionStep {memory_step.step_number}")
        if memory_step.model_output:
            print(f"  Thought: {memory_step.model_output}")
        if memory_step.tool_calls:
            print(f"  Tool calls: {len(memory_step.tool_calls)}")
        if memory_step.observations:
            print(f"  Observations: {memory_step.observations[:100]}...")
    
    elif isinstance(memory_step, PlanningStep):
        print(f"[{agent_name}] PlanningStep")
        print(f"  Plan: {memory_step.plan}")
    
    elif isinstance(memory_step, FinalAnswerStep):
        print(f"[{agent_name}] FinalAnswerStep")
        print(f"  Output: {memory_step.output}")
```

#### 多 Agent 回调路由

在多 Agent 场景下，通过回调可以区分事件来源：

```python
class MultiAgentEventRouter:
    def __init__(self):
        self.events = []
        
    def create_callback(self, agent_name: str):
        """为特定Agent创建回调函数"""
        def callback(memory_step, agent):
            event = {
                'agent_name': agent_name,
                'step_type': type(memory_step).__name__,
                'step_number': getattr(memory_step, 'step_number', None),
                'timestamp': time.time(),
                'data': self._extract_step_data(memory_step)
            }
            self.events.append(event)
            
            # 实时发送到前端
            self._send_to_frontend(event)
        
        return callback
    
    def _extract_step_data(self, memory_step):
        """提取步骤数据"""
        if isinstance(memory_step, ActionStep):
            return {
                'thought': memory_step.model_output,
                'tool_calls': [tc.dict() for tc in memory_step.tool_calls] if memory_step.tool_calls else [],
                'observations': memory_step.observations,
                'error': str(memory_step.error) if memory_step.error else None,
            }
        elif isinstance(memory_step, PlanningStep):
            return {'plan': memory_step.plan}
        elif isinstance(memory_step, FinalAnswerStep):
            return {'output': str(memory_step.output)}
        return {}

# 使用
router = MultiAgentEventRouter()

# 为每个子Agent创建带名称标识的回调
search_agent = ToolCallingAgent(
    name="search_agent",
    step_callbacks=[router.create_callback("search_agent")]
)

code_agent = CodeAgent(
    name="code_agent", 
    step_callbacks=[router.create_callback("code_agent")]
)

# 父Agent
manager = CodeAgent(
    managed_agents=[search_agent, code_agent]
)
```

#### 回调触发时机

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]] 第 620-623 行：

```python
def _finalize_step(self, memory_step: ActionStep | PlanningStep | FinalAnswerStep):
    """步骤完成时触发回调"""
    if not isinstance(memory_step, FinalAnswerStep):
        memory_step.timing.end_time = time.time()
    self.step_callbacks.callback(memory_step, agent=self)
```

**触发时机说明**

| 事件类型 | 触发时机 | 数据完整性 |
|----------|----------|------------|
| PlanningStep | 规划完成后 | 完整，包含plan内容 |
| ActionStep | 动作完成后 | 完整，包含thought/tool_calls/observations |
| FinalAnswerStep | 最终答案生成后 | 完整，包含output |

**关键特点**
- 回调在步骤**完成后**触发，而非实时流式
- 回调接收的是 MemoryStep 对象，包含该步骤的完整信息
- 通过 agent 参数可以区分是哪个 Agent 产生的事件

#### 与 run_stream 的区别

| 特性 | run_stream Generator | step_callbacks 回调 |
|------|----------------------|---------------------|
| 触发方式 | 实时 yield | 步骤完成后回调 |
| 数据粒度 | 细粒度（token级别） | 粗粒度（step级别） |
| 适用场景 | 单Agent流式展示 | 多Agent监控、日志、追踪 |
| 实现复杂度 | 简单 | 需要额外路由逻辑 |
| 前端体验 | 打字机效果 | 步骤卡片更新 |

**推荐方案**
- **单 Agent 交互**：使用 `run_stream` 的 Generator 模式
- **多 Agent 监控**：使用 `step_callbacks` 回调模式
- **混合方案**：父 Agent 用 Generator，子 Agent 用回调透传

---

## 二、流式事件类型全解析

### 2.1 核心事件类型定义

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]] 第 256-265 行定义了流式事件的类型别名：

```python
StreamEvent: TypeAlias = Union[
    ChatMessageStreamDelta,    # 流式文本片段
    ChatMessageToolCall,       # 工具调用消息
    ActionOutput,              # 动作输出
    ToolCall,                  # 工具调用
    ToolOutput,                # 工具输出
    PlanningStep,              # 规划步骤
    ActionStep,                # 动作步骤
    FinalAnswerStep,           # 最终答案
]
```

**事件类型详解**

| 事件类型 | 定义位置 | 核心用途 |
|----------|----------|----------|
| ActionStep | [[memory.py]] 第 51 行 | 记录单个动作步骤的完整信息 |
| PlanningStep | [[memory.py]] 第 154 行 | 记录规划阶段的输入输出 |
| FinalAnswerStep | [[memory.py]] 第 210 行 | 包装最终答案 |
| ChatMessageStreamDelta | [[models.py]] | 模型流式输出的文本片段 |
| ToolCall | [[memory.py]] 第 25 行 | 工具调用请求 |
| ToolOutput | [[agents.py]] 第 117 行 | 工具执行结果 |
| ActionOutput | [[agents.py]] 第 111 行 | 动作执行结果 |

### 2.2 事件类详细属性

**ActionStep 完整属性**

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/memory.py|memory.py]] 第 51-65 行：

```python
@dataclass
class ActionStep(MemoryStep):
    step_number: int                    # 步骤序号
    timing: Timing                      # 执行时间
    model_input_messages: list[ChatMessage] | None = None   # 模型输入
    tool_calls: list[ToolCall] | None = None                # 工具调用列表
    error: AgentError | None = None     # 错误信息
    model_output_message: ChatMessage | None = None         # 模型输出消息
    model_output: str | list[dict[str, Any]] | None = None  # 模型输出内容
    code_action: str | None = None      # CodeAgent 的代码动作
    observations: str | None = None     # 观察结果
    observations_images: list["PIL.Image.Image"] | None = None  # 观察图片
    action_output: Any = None           # 动作输出
    token_usage: TokenUsage | None = None                   # Token 使用量
    is_final_answer: bool = False       # 是否为最终答案
```

**PlanningStep 完整属性**

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/memory.py|memory.py]] 第 154-159 行：

```python
@dataclass
class PlanningStep(MemoryStep):
    model_input_messages: list[ChatMessage]   # 模型输入消息
    model_output_message: ChatMessage         # 模型输出消息
    plan: str                                 # 规划内容
    timing: Timing                            # 执行时间
    token_usage: TokenUsage | None = None     # Token 使用量
```

**ToolCall 属性**

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/memory.py|memory.py]] 第 25-28 行：

```python
@dataclass
class ToolCall:
    name: str           # 工具名称
    arguments: Any      # 工具参数
    id: str             # 调用 ID
```

**ToolOutput 属性**

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]] 第 117-123 行：

```python
@dataclass
class ToolOutput:
    id: str             # 调用 ID
    output: Any         # 输出内容
    is_final_answer: bool   # 是否为最终答案
    observation: str    # 观察描述
    tool_call: ToolCall # 对应的工具调用
```

---

## 三、事件来源标识机制

### 3.1 Agent 名称追踪

smolagents 通过 `agent.name` 属性区分不同 Agent：

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]] 第 332 行：

```python
self.name = self._validate_name(name)   # Agent 名称，用于标识
```

**Managed Agent 的注册**

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py]] 第 369-376 行：

```python
def _setup_managed_agents(self, managed_agents: list | None = None) -> None:
    self.managed_agents = {}
    if managed_agents:
        assert all(agent.name and agent.description for agent in managed_agents)
        self.managed_agents = {agent.name: agent for agent in managed_agents}
```

### 3.2 事件来源识别方案

由于 smolagents 原生未在事件中嵌入 Agent 标识，前端需要**自行维护调用栈**来追踪事件来源：

```python
class StreamingEventRouter:
    def __init__(self):
        self.agent_stack = []       # Agent 调用栈
        self.current_agent = None   # 当前 Agent
        
    def on_managed_agent_call(self, agent_name: str):
        """子 Agent 调用开始时入栈"""
        self.agent_stack.append(agent_name)
        self.current_agent = agent_name
        
    def on_managed_agent_end(self):
        """子 Agent 调用结束时出栈"""
        if self.agent_stack:
            self.agent_stack.pop()
        self.current_agent = self.agent_stack[-1] if self.agent_stack else None
        
    def get_event_source(self, event) -> dict:
        """获取事件来源信息"""
        return {
            "agent_name": self.current_agent,
            "level": len(self.agent_stack),    # 嵌套层级
            "is_root": len(self.agent_stack) == 0
        }
```

---

## 四、前端展示设计

### 4.1 事件分类展示策略

| 事件类型 | 展示方式 | 特殊处理 |
|----------|----------|----------|
| PlanningStep | 折叠面板 | 默认可收起，显示规划内容 |
| ActionStep - Thought | 气泡对话 | 思考过程，灰色显示 |
| ActionStep - Tool Call | 工具卡片 | 显示工具名和参数，可展开 |
| ActionStep - Observation | 结果面板 | 代码块/表格/图片 |
| FinalAnswerStep | 高亮卡片 | 绿色边框，醒目显示 |
| ChatMessageStreamDelta | 打字机效果 | 逐字显示，实时更新 |
| ToolOutput | 输出卡片 | 显示执行结果 |

### 4.2 多 Agent 层级展示设计

**树形层级结构**

```
【Manager Agent】
├─ 正在分析任务...
├─ 调用 search_agent ▼
│  ├─ [search_agent] 正在搜索...
│  ├─ [search_agent] 调用工具: web_search
│  └─ [search_agent] 搜索结果: ...
├─ 调用 code_agent ▼
│  ├─ [code_agent] 生成代码...
│  └─ [code_agent] 执行结果: ...
└─ 最终答案: ...
```

**层级缩进规则**

| 层级 | 缩进 | 视觉标识 |
|------|------|----------|
| 根 Agent | 0px | 主色调边框 |
| 一级子 Agent | 24px | 左侧细线 |
| 二级子 Agent | 48px | 左侧虚线 |

### 4.3 最终答案的特殊处理

**视觉设计要点**

- 颜色区分：使用醒目的主题色边框
- 图标标识：使用对勾图标表示完成
- 操作按钮：复制、导出、分享
- 内容渲染：Markdown 完整渲染、代码高亮

**交互设计**

| 功能 | 触发方式 | 反馈 |
|------|----------|------|
| 复制 | 点击复制按钮 | Toast 提示已复制 |
| 导出 | 点击导出按钮 | 下载 Markdown 文件 |
| 展开/收起 | 点击卡片头部 | 平滑动画 |

---

## 五、特殊事件处理

### 5.1 FinalAnswerStep 检测与处理

**检测逻辑**

```python
# 方式一：通过 ActionStep 的 is_final_answer 标记
if isinstance(event, ActionStep) and event.is_final_answer:
    handle_final_answer(event.action_output)

# 方式二：通过 FinalAnswerStep 类型
if isinstance(event, FinalAnswerStep):
    handle_final_answer(event.output)

# 方式三：通过 ActionOutput 标记
if isinstance(event, ActionOutput) and event.is_final_answer:
    handle_final_answer(event.output)
```

**处理流程**

```
检测到最终答案
    ├── 停止流式接收
    ├── 渲染最终答案卡片
    ├── 启用复制按钮
    ├── 启用导出按钮
    └── 触发完成回调
```

### 5.2 错误事件处理

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/memory.py|memory.py]] 第 56 行的 error 属性：

```python
# 错误检测
if isinstance(event, ActionStep) and event.error:
    show_error_message({
        "type": type(event.error).__name__,
        "message": str(event.error),
        "step_number": event.step_number
    })
    
# 重试机制
if should_retry(event.error):
    show_retry_button()
```

**错误类型映射**

| 错误类型 | 来源 | 处理方式 |
|----------|------|----------|
| AgentGenerationError | 模型生成失败 | 提示重试 |
| AgentParsingError | 解析失败 | 显示原始输出 |
| AgentToolExecutionError | 工具执行失败 | 显示错误详情 |
| AgentMaxStepsError | 达到最大步数 | 提示简化任务 |

### 5.3 图片事件处理

[[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/memory.py|memory.py]] 第 61 行的 observations_images：

```python
# 图片检测与显示
if isinstance(event, ActionStep) and event.observations_images:
    for idx, image in enumerate(event.observations_images):
        display_image({
            "id": f"step_{event.step_number}_img_{idx}",
            "data": image,    # PIL.Image 对象
            "alt": f"步骤 {event.step_number} 的图片 {idx + 1}"
        })
```

### 5.4 工具调用事件处理

```python
# ToolCall 渲染
if isinstance(event, ToolCall):
    render_tool_call_card({
        "name": event.name,
        "arguments": event.arguments,
        "id": event.id
    })

# ToolOutput 渲染  
if isinstance(event, ToolOutput):
    render_tool_output_card({
        "output": event.output,
        "observation": event.observation,
        "is_final_answer": event.is_final_answer
    })
```

---

## 六、多 Agent 事件路由

### 6.1 事件路由核心逻辑

```python
class StreamingEventRouter:
    def __init__(self, ui_callbacks: dict):
        self.agent_stack = []
        self.ui = ui_callbacks
        
    def route_event(self, event, agent_name: str = None):
        """路由事件到对应的 UI 组件"""
        source = agent_name or self.current_agent or "root"
        level = len(self.agent_stack)
        
        # 根据事件类型分发
        if isinstance(event, PlanningStep):
            self.ui.render_planning(event, source, level)
        elif isinstance(event, ActionStep):
            self.ui.render_action_step(event, source, level)
        elif isinstance(event, FinalAnswerStep):
            self.ui.render_final_answer(event, source, level)
        elif isinstance(event, ChatMessageStreamDelta):
            self.ui.append_stream_text(event.content, source, level)
        elif isinstance(event, ToolCall):
            self.ui.render_tool_call(event, source, level)
        elif isinstance(event, ToolOutput):
            self.ui.render_tool_output(event, source, level)
```

### 6.2 嵌套层级控制

**最大嵌套深度限制**

```python
MAX_NESTING_DEPTH = 3   # 最大嵌套层数

def check_nesting_depth(self) -> bool:
    if len(self.agent_stack) >= MAX_NESTING_DEPTH:
        self.ui.show_warning("已达到最大嵌套深度，子 Agent 将以非流式方式执行")
        return False
    return True
```

**层级视觉编码**

| 层级 | 左边距 | 边框样式 | 字体大小 |
|------|--------|----------|----------|
| 0 | 0px | 实线 2px | 16px |
| 1 | 24px | 实线 1px | 15px |
| 2 | 48px | 虚线 1px | 14px |

---

## 七、实现示例

### 7.1 前端 React 组件设计

**事件分发器组件**

```typescript
// 流式事件类型定义
type StreamEvent = 
    | { type: 'ActionStep', data: ActionStep }
    | { type: 'PlanningStep', data: PlanningStep }
    | { type: 'FinalAnswerStep', data: FinalAnswerStep }
    | { type: 'ChatMessageStreamDelta', data: ChatMessageStreamDelta }
    | { type: 'ToolCall', data: ToolCall }
    | { type: 'ToolOutput', data: ToolOutput };

// 事件分发器
const EventDispatcher: React.FC = () => {
    const [events, setEvents] = useState<StreamEvent[]>([]);
    const [streamText, setStreamText] = useState('');
    
    useEffect(() => {
        const eventSource = new EventSource('/api/chat/stream');
        
        eventSource.onmessage = (e) => {
            const event: StreamEvent = JSON.parse(e.data);
            
            // 流式文本特殊处理：累积更新
            if (event.type === 'ChatMessageStreamDelta') {
                setStreamText(prev => prev + event.data.content);
            } else {
                setEvents(prev => [...prev, event]);
                setStreamText('');    // 重置流式文本
            }
        };
        
        return () => eventSource.close();
    }, []);
    
    return (
        <div className="event-stream">
            {events.map((event, idx) => (
                <EventRenderer key={idx} event={event} />
            ))}
            {streamText && <StreamTextPreview text={streamText} />}
        </div>
    );
};
```

**事件渲染器**

```typescript
const EventRenderer: React.FC<{event: StreamEvent}> = ({event}) => {
    switch (event.type) {
        case 'ActionStep':
            return <ActionStepCard step={event.data} />;
        case 'PlanningStep':
            return <PlanningStepCard plan={event.data} />;
        case 'FinalAnswerStep':
            return <FinalAnswerCard answer={event.data.output} />;
        case 'ToolCall':
            return <ToolCallCard toolCall={event.data} />;
        case 'ToolOutput':
            return <ToolOutputCard output={event.data} />;
        default:
            return <DefaultEventCard event={event} />;
    }
};
```

### 7.2 最终答案组件

```typescript
const FinalAnswerCard: React.FC<{answer: any}> = ({answer}) => {
    const [copied, setCopied] = useState(false);
    
    const handleCopy = async () => {
        await navigator.clipboard.writeText(String(answer));
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };
    
    const handleExport = () => {
        const blob = new Blob([String(answer)], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'final-answer.md';
        a.click();
    };
    
    return (
        <div className="final-answer-card">
            <div className="final-answer-header">
                <CheckCircleIcon className="success-icon" />
                <span className="title">最终答案</span>
                <button onClick={handleCopy} className="action-btn">
                    {copied ? '已复制' : '复制'}
                </button>
                <button onClick={handleExport} className="action-btn">
                    导出
                </button>
            </div>
            <div className="final-answer-content">
                <MarkdownRenderer content={String(answer)} />
            </div>
        </div>
    );
};
```

### 7.3 Python 后端流式接口

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from smolagents import CodeAgent, HfApiModel
import json

app = FastAPI()

@app.post("/chat/stream")
async def chat_stream(task: str):
    agent = CodeAgent(
        tools=[...],
        model=HfApiModel(...),
        managed_agents=[...]
    )
    
    async def event_generator():
        for event in agent.run(task, stream=True):
            # 序列化事件
            event_data = serialize_event(event)
            yield f"data: {json.dumps(event_data)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )

def serialize_event(event) -> dict:
    """将 smolagents 事件序列化为 JSON"""
    if isinstance(event, ActionStep):
        return {
            "type": "ActionStep",
            "data": {
                "step_number": event.step_number,
                "model_output": event.model_output,
                "observations": event.observations,
                "is_final_answer": event.is_final_answer,
                "error": str(event.error) if event.error else None
            }
        }
    elif isinstance(event, FinalAnswerStep):
        return {
            "type": "FinalAnswerStep",
            "data": {"output": str(event.output)}
        }
    # ... 其他事件类型
```

---

## 八、最佳实践

### 8.1 性能优化

**虚拟滚动**

当事件数量超过 100 时，启用虚拟滚动避免 DOM 过载：

```typescript
import { Virtuoso } from 'react-virtuoso';

<Virtuoso
    data={events}
    itemContent={(index, event) => <EventRenderer event={event} />}
/>
```

**图片懒加载**

```typescript
const ImageComponent: React.FC<{src: string}> = ({src}) => (
    <img 
        src={src} 
        loading="lazy" 
        placeholder="blur"
    />
);
```

**代码块按需高亮**

```typescript
import { highlight } from 'prismjs';

const CodeBlock: React.FC<{code: string}> = ({code}) => {
    const [highlighted, setHighlighted] = useState(false);
    
    useEffect(() => {
        // 延迟高亮，优先保证流畅性
        const timer = setTimeout(() => {
            highlight(code);
            setHighlighted(true);
        }, 100);
        return () => clearTimeout(timer);
    }, [code]);
    
    return <pre className={highlighted ? 'highlighted' : ''}>{code}</pre>;
};
```

### 8.2 用户体验优化

**加载状态提示**

| 状态 | 视觉提示 | 说明 |
|------|----------|------|
| 思考中 | 脉冲动画 | 模型正在生成 |
| 调用工具 | 旋转图标 | 工具执行中 |
| 等待子 Agent | 进度条 | 子 Agent 运行中 |
| 流式输出 | 光标闪烁 | 实时接收文本 |

**取消与重试**

```typescript
const StreamController: React.FC = () => {
    const [isRunning, setIsRunning] = useState(false);
    const abortController = useRef<AbortController>();
    
    const handleCancel = () => {
        abortController.current?.abort();
        setIsRunning(false);
    };
    
    const handleRetry = () => {
        // 清空当前事件，重新开始
        setEvents([]);
        startStream();
    };
    
    return (
        <div className="controls">
            {isRunning ? (
                <button onClick={handleCancel} className="cancel-btn">
                    取消
                </button>
            ) : (
                <button onClick={handleRetry} className="retry-btn">
                    重试
                </button>
            )}
        </div>
    );
};
```

### 8.3 错误处理

**优雅降级策略**

```typescript
const ErrorBoundary: React.FC = ({children}) => {
    const [hasError, setHasError] = useState(false);
    
    if (hasError) {
        return (
            <div className="error-fallback">
                <p>界面渲染出错</p>
                <button onClick={() => window.location.reload()}>
                    刷新页面
                </button>
            </div>
        );
    }
    
    return children;
};
```

**断线重连机制**

```typescript
const useEventSource = (url: string) => {
    const [events, setEvents] = useState([]);
    const [retryCount, setRetryCount] = useState(0);
    
    useEffect(() => {
        let eventSource: EventSource;
        
        const connect = () => {
            eventSource = new EventSource(url);
            
            eventSource.onerror = () => {
                eventSource.close();
                if (retryCount < 3) {
                    setTimeout(connect, 1000 * (retryCount + 1));
                    setRetryCount(c => c + 1);
                }
            };
            
            eventSource.onopen = () => setRetryCount(0);
        };
        
        connect();
        return () => eventSource?.close();
    }, [url, retryCount]);
    
    return events;
};
```

---

## 九、Graphviz 图表

### 9.1 多 Agent 流式事件传播图

![[smolagents-多Agent流式事件传播图.svg]]

### 9.2 前端事件处理流程图

![[smolagents-前端事件处理流程图.svg]]

### 9.3 事件展示组件层次图

![[smolagents-事件展示组件层次图.svg]]

---

## 十、总结与建议

### 10.1 smolagents 流式输出特点

**优势**

- Generator 模式实现真正的流式传输
- 事件类型丰富，覆盖完整生命周期
- ActionStep 信息完备，便于调试

**局限**

- Managed Agent 事件不透传，只能看到最终结果
- 事件对象不包含 Agent 标识，需外部维护调用栈
- 缺乏内置的事件序列化机制

### 10.2 前端实现建议

1. **事件追踪**：自行维护 Agent 调用栈，为每个事件标记来源
2. **状态管理**：使用虚拟滚动处理大量事件
3. **错误处理**：实现完善的错误边界和重试机制
4. **性能优化**：图片懒加载、代码高亮延迟执行

### 10.3 扩展改进方向

- 为事件对象添加 agent_id 字段
- 实现 Managed Agent 的流式事件透传
- 提供官方的前端组件库

---

## 关联文档

- [[50-smolagents-源码架构分析]]
- [[51-smolagents-模型接口设计]]
- [[48-smolagents-MultiStepAgent-深入解析]]

---

## 标签

主题：AI Agent  
框架：smolagents  
技术：流式输出、前端设计、事件驱动  
状态：深度分析  
