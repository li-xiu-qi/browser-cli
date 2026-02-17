# smolagents 监控与日志系统分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/monitoring.py

## 一、AgentLogger设计

### 1.1 核心职责

AgentLogger是smolagents的日志门面，封装了所有输出到控制台的逻辑。它基于Rich库构建，提供美观的终端输出效果。

```python
class AgentLogger:
    def __init__(self, level: LogLevel = LogLevel.INFO, console: Console | None = None):
        self.level = level
        if console is None:
            self.console = Console(highlight=False)
        else:
            self.console = console
```

设计特点：
- 支持自定义Console实例，便于测试和扩展
- 默认关闭语法高亮，避免干扰
- 通过level属性控制输出粒度

### 1.2 日志级别系统

LogLevel使用IntEnum实现四级控制：

| 级别 | 数值 | 含义 | 使用场景 |
|------|------|------|----------|
| OFF | -1 | 完全关闭 | 生产环境静默运行 |
| ERROR | 0 | 仅错误 | 关键问题追踪 |
| INFO | 1 | 正常输出 | 默认级别，显示执行流程 |
| DEBUG | 2 | 详细输出 | 调试开发 |

级别比较逻辑：
```python
if level <= self.level:
    self.console.print(*args, **kwargs)
```

只有当日志级别小于等于设定级别时才会输出。例如设置level=INFO时，ERROR和INFO级别的日志会显示，DEBUG不会。

### 1.3 专用输出方法

#### log_code: 代码块展示

使用Panel包裹代码，配合Syntax实现语法高亮：

```python
def log_code(self, title: str, content: str, level: int = LogLevel.INFO) -> None:
    self.log(
        Panel(
            Syntax(content, lexer="python", theme="monokai", word_wrap=True),
            title="[bold]" + title,
            title_align="left",
            box=box.HORIZONTALS,
        ),
        level=level,
    )
```

参数设计：
- title: 面板标题，左对齐加粗显示
- content: Python代码内容
- level: 日志级别控制

#### log_task: 任务面板

专用于展示任务信息，使用醒目的黄色边框：

```python
def log_task(self, content: str, subtitle: str, title: str | None = None, level: LogLevel = LogLevel.INFO) -> None:
    self.log(
        Panel(
            f"\n[bold]{escape_code_brackets(content)}\n",
            title="[bold]New run" + (f" - {title}" if title else ""),
            subtitle=subtitle,
            border_style=YELLOW_HEX,  # #d4b702
            subtitle_align="left",
        ),
        level=level,
    )
```

设计亮点：
- escape_code_brackets处理特殊字符，防止Rich误解析
- 黄色边框突出任务边界
- subtitle显示模型信息

#### log_rule: 分隔线

用于标记步骤边界：

```python
def log_rule(self, title: str, level: int = LogLevel.INFO) -> None:
    self.log(
        Rule("[bold white]" + title, characters="━", style=YELLOW_HEX),
        level=LogLevel.INFO,
    )
```

使用粗横线字符"━"和黄色样式，视觉上清晰划分不同阶段。

#### log_markdown: Markdown渲染

支持Markdown语法的高亮显示：

```python
def log_markdown(self, content: str, title: str | None = None, level=LogLevel.INFO, style=YELLOW_HEX) -> None:
    markdown_content = Syntax(content, lexer="markdown", theme="github-dark", word_wrap=True)
    if title:
        self.log(
            Group(
                Rule("[bold italic]" + title, align="left", style=style),
                markdown_content,
            ),
            level=level,
        )
    else:
        self.log(markdown_content, level=level)
```

适用场景：显示LLM的输出内容、计划文本等。

### 1.4 错误处理

```python
def log_error(self, error_message: str) -> None:
    self.log(escape_code_brackets(error_message), style="bold red", level=LogLevel.ERROR)
```

特点：
- 强制红色加粗样式
- 使用ERROR级别，确保在各级别下都可见
- 转义特殊字符避免渲染问题

## 二、Monitor监控

### 2.1 核心职责

Monitor负责追踪Agent执行过程中的性能指标，主要包括：
- Token使用量统计
- 执行时间追踪
- 累计指标计算

### 2.2 数据结构

```python
class Monitor:
    def __init__(self, tracked_model, logger):
        self.step_durations = []           # 每步执行时长列表
        self.tracked_model = tracked_model # 追踪的模型
        self.logger = logger               # 日志器
        self.total_input_token_count = 0   # 输入token累计
        self.total_output_token_count = 0  # 输出token累计
```

### 2.3 TokenUsage数据类

```python
@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int = field(init=False)

    def __post_init__(self):
        self.total_tokens = self.input_tokens + self.output_tokens

    def dict(self):
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }
```

设计要点：
- __post_init__自动计算总量
- dict方法支持序列化
- 用于单个步骤或整体统计

### 2.4 Timing数据类

```python
@dataclass
class Timing:
    start_time: float
    end_time: float | None = None

    @property
    def duration(self):
        return None if self.end_time is None else self.end_time - self.start_time

    def dict(self):
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
        }
```

用途：记录每个步骤的起止时间和耗时。

### 2.5 指标更新机制

```python
def update_metrics(self, step_log):
    step_duration = step_log.timing.duration
    self.step_durations.append(step_duration)
    console_outputs = f"[Step {len(self.step_durations)}: Duration {step_duration:.2f} seconds"

    if step_log.token_usage is not None:
        self.total_input_token_count += step_log.token_usage.input_tokens
        self.total_output_token_count += step_log.token_usage.output_tokens
        console_outputs += (
            f"| Input tokens: {self.total_input_token_count:,} | Output tokens: {self.total_output_token_count:,}"
        )
    console_outputs += "]"
    self.logger.log(Text(console_outputs, style="dim"), level=1)
```

输出示例：
```
[Step 1: Duration 2.34 seconds| Input tokens: 1,234 | Output tokens: 567]
```

特点：
- 使用dim样式，低调显示不干扰主输出
- 数字格式化带千分位逗号
- 动态判断token_usage是否存在

### 2.6 获取累计统计

```python
def get_total_token_counts(self) -> TokenUsage:
    return TokenUsage(
        input_tokens=self.total_input_token_count,
        output_tokens=self.total_output_token_count,
    )
```

便于在运行结束时获取整体统计。

### 2.7 重置机制

```python
def reset(self):
    self.step_durations = []
    self.total_input_token_count = 0
    self.total_output_token_count = 0
```

在Agent重新运行前清空历史数据。

## 三、日志输出格式

### 3.1 视觉层次设计

smolagents使用Rich库构建了清晰的视觉层次：

1. **任务级别**：黄色边框Panel，最大视觉权重
2. **步骤级别**：白色粗体分隔线，中等权重
3. **代码级别**：带标题的Panel，语法高亮
4. **信息级别**：普通文本，dim样式

### 3.2 颜色规范

```python
YELLOW_HEX = "#d4b702"  # 主题色，用于边框和强调
```

使用场景：
- 任务面板边框
- 分隔线样式
- Markdown标题线

### 3.3 Panel组件应用

代码展示面板：
- 使用box.HORIZONTALS样式，简洁水平线边框
- 左对齐标题
- Python语法高亮，monokai主题

任务展示面板：
- 全边框，黄色强调
- 左对齐副标题显示模型信息
- 内嵌内容自动转义特殊字符

### 3.4 文本处理

escape_code_brackets工具函数：
- 处理方括号，防止Rich将其解析为样式标签
- 确保原始内容正确显示

## 四、监控指标详解

### 4.1 指标来源

Token使用量来自模型响应：

```python
# 在_step_stream中记录
memory_step.token_usage = chat_message.token_usage
```

chat_message.token_usage由具体模型实现填充，不同类型模型的统计方式可能不同。

### 4.2 时间追踪流程

```python
# 1. 步骤开始时记录
action_step_start_time = time.time()
action_step = ActionStep(
    step_number=self.step_number,
    timing=Timing(start_time=action_step_start_time),
    ...
)

# 2. 步骤结束时填充
memory_step.timing.end_time = time.time()

# 3. 计算持续时间
step_duration = step_log.timing.duration
```

### 4.3 运行结果统计

RunResult包含完整的运行统计：

```python
@dataclass
class RunResult:
    output: Any | None                    # 最终输出
    state: Literal["success", "max_steps_error"]  # 运行状态
    steps: list[dict]                     # 步骤历史
    token_usage: TokenUsage | None        # Token使用统计
    timing: Timing                        # 时间统计
```

token_usage计算逻辑：

```python
total_input_tokens = 0
total_output_tokens = 0
correct_token_usage = True
for step in self.memory.steps:
    if isinstance(step, (ActionStep, PlanningStep)):
        if step.token_usage is None:
            correct_token_usage = False
            break
        else:
            total_input_tokens += step.token_usage.input_tokens
            total_output_tokens += step.token_usage.output_tokens
```

遍历所有ActionStep和PlanningStep累加token使用量。

## 五、与回调集成

### 5.1 回调注册架构

CallbackRegistry支持按步骤类型注册回调：

```python
class CallbackRegistry:
    def __init__(self):
        self._callbacks: dict[Type[MemoryStep], list[Callable]] = {}

    def register(self, step_cls: Type[MemoryStep], callback: Callable):
        if step_cls not in self._callbacks:
            self._callbacks[step_cls] = []
        self._callbacks[step_cls].append(callback)
```

### 5.2 Monitor作为Step Callback

在Agent初始化时自动注册：

```python
def _setup_step_callbacks(self, step_callbacks):
    self.step_callbacks = CallbackRegistry()
    if step_callbacks:
        if isinstance(step_callbacks, list):
            for callback in step_callbacks:
                self.step_callbacks.register(ActionStep, callback)
        elif isinstance(step_callbacks, dict):
            for step_cls, callbacks in step_callbacks.items():
                if not isinstance(callbacks, list):
                    callbacks = [callbacks]
                for callback in callbacks:
                    self.step_callbacks.register(step_cls, callback)
    # 自动注册Monitor的update_metrics
    self.step_callbacks.register(ActionStep, self.monitor.update_metrics)
```

关键点：
- Monitor的update_metrics自动注册到ActionStep
- 用户可传入自定义回调列表或字典
- 支持向后兼容的列表格式

### 5.3 回调触发时机

```python
def _finalize_step(self, memory_step: ActionStep | PlanningStep | FinalAnswerStep):
    if not isinstance(memory_step, FinalAnswerStep):
        memory_step.timing.end_time = time.time()
    self.step_callbacks.callback(memory_step, agent=self)
```

每个步骤结束时触发回调，传入memory_step和agent实例。

### 5.4 回调兼容性处理

```python
def callback(self, memory_step, **kwargs):
    for cls in memory_step.__class__.__mro__:
        for cb in self._callbacks.get(cls, []):
            cb(memory_step) if len(inspect.signature(cb).parameters) == 1 else cb(memory_step, **kwargs)
```

通过inspect检查回调函数签名，兼容旧版单参数回调和新版多参数回调。

## 六、日志级别控制

### 6.1 verbosity_level参数

MultiStepAgent通过verbosity_level控制日志详细程度：

```python
def __init__(
    self,
    ...
    verbosity_level: LogLevel = LogLevel.INFO,
    ...
):
    if logger is None:
        self.logger = AgentLogger(level=verbosity_level)
    else:
        self.logger = logger
```

### 6.2 各级别行为差异

| 级别 | 显示内容 | 适用场景 |
|------|----------|----------|
| OFF | 无任何输出 | 生产静默运行 |
| ERROR | 仅错误信息 | 错误监控 |
| INFO | 任务、步骤、代码执行、工具调用 | 正常使用 |
| DEBUG | 额外包含LLM完整输出、消息详情 | 开发调试 |

### 6.3 级别使用示例

INFO级别的典型输出：
```python
self.logger.log_task(...)           # 任务开始
self.logger.log_rule(f"Step {n}")   # 步骤标记
self.logger.log_code(...)           # 代码执行
self.logger.log(Text(f"Final answer: ..."))  # 结果
```

DEBUG级别的额外输出：
```python
self.logger.log_markdown(
    content=output_text or "",
    title="Output message of the LLM:",
    level=LogLevel.DEBUG,
)
self.logger.log_messages(memory_step.model_input_messages, level=LogLevel.DEBUG)
```

### 6.4 级别字符串转换

log方法支持字符串级别：

```python
def log(self, *args, level: int | str | LogLevel = LogLevel.INFO, **kwargs) -> None:
    if isinstance(level, str):
        level = LogLevel[level.upper()]
    if level <= self.level:
        self.console.print(*args, **kwargs)
```

使用时可传入"INFO"、"DEBUG"等字符串。

## 七、对我们项目的启示

### 7.1 可借鉴的设计

**分层日志系统**

smolagents的四级日志设计清晰明了。在我们的AI数据分析系统中可采用类似分级：
- ERROR：系统错误、API失败
- INFO：分析流程、数据加载、模型调用
- DEBUG：详细prompt、原始响应、中间结果

**统一视觉风格**

通过定义主题色和统一Panel样式，提升用户体验。建议为不同分析阶段定义不同颜色：
- 数据加载：蓝色
- 模型分析：绿色
- 结果输出：黄色

**监控与执行分离**

Monitor与AgentLogger分离的设计值得借鉴：
- Monitor专注指标收集
- Logger专注输出展示
- 通过回调解耦两者

### 7.2 可改进的地方

**结构化日志输出**

smolagents主要面向终端展示，缺乏结构化日志支持。在生产环境中应考虑：
- JSON格式日志输出选项
- 支持日志文件轮转
- 与ELK/Loki等系统集成

**成本计算扩展**

当前只统计token数量，建议扩展：
- 按模型单价计算实际成本
- 分阶段成本分析
- 预算告警机制

**持久化监控数据**

RunResult包含丰富信息，但仅在内存中。建议：
- 可选的数据库存储
- 运行历史查询接口
- 性能趋势分析

### 7.3 实施建议

1. **保留Rich终端输出**：开发调试时使用，提供良好的可读性
2. **增加结构化日志模式**：生产环境使用JSON格式，便于日志收集
3. **扩展监控指标**：除token和时间外，增加API调用次数、缓存命中率等
4. **异步日志写入**：避免I/O阻塞影响主流程性能
5. **可配置的日志目标**：支持同时输出到控制台、文件、远程服务

### 7.4 代码组织参考

```
our_project/
├── monitoring/
│   ├── __init__.py
│   ├── logger.py          # 类似AgentLogger
│   ├── monitor.py         # 类似Monitor
│   ├── metrics.py         # 指标数据类
│   ├── formatters/        # 输出格式化器
│   │   ├── rich_formatter.py
│   │   └── json_formatter.py
│   └── exporters/         # 数据导出器
│       ├── file_exporter.py
│       └── http_exporter.py
```

---

## 参考链接

- 源码: [[参考项目/smolagents/src/smolagents/monitoring.py]]
- Agent实现: [[参考项目/smolagents/src/smolagents/agents.py]]
- 内存管理: [[参考项目/smolagents/src/smolagents/memory.py]]
