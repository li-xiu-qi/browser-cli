# smolagents 架构重构设计方案

> 项目: smolagents 架构重构  
> 版本: 1.0.0  
> 日期: 2026-02-06  
> 关联文档: [[17-smolagents-类图与依赖关系分析]], [[01-smolagents-Agent架构深度分析]]

---

## 执行摘要

本文档为 smolagents 框架设计一套全面的架构重构方案，目标是在保持现有功能完整性的前提下，通过引入依赖注入、插件化架构和事件驱动模式，解决当前架构中的耦合度高、扩展性差和测试困难等问题。

---

## 一、当前架构问题分析

### 1.1 耦合度分析

#### 模块间依赖关系

当前 smolagents 的模块依赖呈现以下特征：

| 模块对 | 耦合类型 | 问题描述 |
|--------|----------|----------|
| agents → models | 直接实例化 | Agent 内部直接创建 Model 实例 |
| agents → tools | 字典传递 | 工具集合以字典形式注入，缺乏抽象 |
| agents → executors | 条件创建 | CodeAgent 根据字符串参数创建执行器 |
| models → tools | 导入依赖 | Model 需要了解 Tool 的具体实现 |

> 核心问题：组件创建逻辑与业务逻辑混合，导致依赖关系隐藏在代码深处。

#### 循环依赖识别

经代码审查，当前架构未发现明显的循环依赖问题。各模块依赖方向遵循：agents → 业务领域 models/tools/memory → 基础设施 utils/monitoring。

但存在以下潜在风险点：

- models.py 导入 tools.py 的 Tool 类
- memory.py 导入 models.py 的 ChatMessage
- 未来扩展时容易形成循环依赖

### 1.2 扩展性限制

#### 新增 Agent 类型的难度

当前新增 Agent 类型需要完成以下步骤：

**第一步**：继承 MultiStepAgent 基类
**第二步**：实现 `initialize_system_prompt` 方法
**第三步**：实现 `_step_stream` 方法
**第四步**：在 AGENT_REGISTRY 中注册

问题在于：
- AGENT_REGISTRY 是全局字典，需要修改源码
- 缺乏运行时动态注册机制
- 无法通过配置文件扩展

#### 新增 Executor 的难度

当前新增代码执行器需要修改 `CodeAgent.create_python_executor` 方法：

```python
def create_python_executor(self, executor_type: str):
    if executor_type == "local":
        return LocalPythonExecutor(...)
    elif executor_type == "e2b":
        return E2BExecutor(...)
    # 新增类型需要在这里添加分支
```

这种设计违反了开闭原则，每新增一种执行器都需要修改源码。

### 1.3 可测试性问题

#### 单元测试难度

当前架构的测试难点：

| 测试目标 | 困难点 | 原因 |
|----------|--------|------|
| MultiStepAgent | 高 | 依赖 Model、Tool、Memory 等多个具体实现 |
| CodeAgent | 高 | 内部创建 PythonExecutor，无法注入 Mock |
| Tool | 中 | 基类设计合理，但验证逻辑耦合在类内部 |
| Model | 高 | 需要真实的 API Key 或模型文件 |

#### Mock 复杂度

以测试 ToolCallingAgent 为例：

```python
# 当前方式：需要 Mock 整个调用链
agent = ToolCallingAgent(
    tools=[mock_tool],  # 可以 Mock
    model=mock_model,   # 需要完整模拟 generate 方法
    # 无法注入 Mock 的 Memory 或 Monitor
)
```

缺乏依赖注入容器，导致：
- 需要构建完整的依赖树才能测试
- 无法隔离单个组件进行单元测试
- 集成测试与单元测试界限模糊

---

## 二、重构目标

### 2.1 核心目标

| 目标 | 具体指标 | 验证方式 |
|------|----------|----------|
| 降低耦合 | 模块间依赖数减少 50% | 依赖图分析 |
| 提高扩展性 | 新增组件零源码修改 | 插件机制验证 |
| 改善可测试性 | 单元测试覆盖率提升至 80% | 测试报告 |
| 向后兼容 | 现有 API 100% 兼容 | 回归测试通过 |

### 2.2 设计原则

> 重构遵循三项核心原则：不破坏现有功能、渐进式演进、保持接口稳定。

**原则一：开闭原则
新增功能通过扩展而非修改实现。

**原则二：单一职责
每个模块只负责一项明确的职责。

**原则三：依赖倒置
高层模块依赖抽象，不依赖具体实现。

---

## 三、重构方案

### 3.1 依赖注入框架引入

#### 为什么需要 DI

当前架构的问题根源在于组件自己创建依赖：

```python
# 当前方式：组件自己创建依赖
class CodeAgent(MultiStepAgent):
    def __init__(self, ...):
        # 内部创建执行器，无法外部注入
        self.python_executor = self.create_python_executor(executor_type)
```

引入 DI 后，依赖由外部容器提供：

```python
# DI 方式：依赖由容器注入
class CodeAgent(MultiStepAgent):
    def __init__(self, python_executor: PythonExecutor, ...):
        self.python_executor = python_executor  # 外部注入
```

DI 带来的好处：
- 组件不再关心依赖如何创建
- 便于替换实现，如测试时使用 Mock
- 依赖关系显性化，便于分析

#### DI 框架选择

对比三个候选方案：

| 框架 | 优点 | 缺点 | 适用性 |
|------|------|------|--------|
| python-dependency-injector | 功能完整、文档丰富 | 外部依赖 | 高 |
| injector | 轻量、类型安全 | 社区较小 | 中 |
| 自研 DI 容器 | 无外部依赖 | 维护成本 | 低 |

**推荐方案**：python-dependency-injector

理由：
- 支持多种注入模式：构造函数、属性、方法
- 与类型注解良好集成
- 支持容器嵌套和覆盖，便于测试
- 社区活跃，文档完善

#### 改造计划

**阶段一：定义抽象接口**

创建 `smolagents/abc/` 目录，放置所有抽象基类：

```
smolagents/abc/
├── __init__.py
├── agent.py          # Agent 抽象接口
├── model.py          # Model 抽象接口  
├── tool.py           # Tool 抽象接口
├── executor.py       # Executor 抽象接口
├── memory.py         # Memory 抽象接口
└── monitor.py        # Monitor 抽象接口
```

**阶段二：实现 DI 容器**

创建 `smolagents/container.py`：

```python
from dependency_injector import containers, providers

class SmolagentsContainer(containers.DeclarativeContainer):
    # 配置
    config = providers.Configuration()
    
    # 基础设施
    logger = providers.Singleton(AgentLogger)
    monitor = providers.Singleton(Monitor, logger=logger)
    
    # 执行器工厂
    executor_factory = providers.FactoryAggregate(
        local=providers.Factory(LocalPythonExecutor),
        e2b=providers.Factory(E2BExecutor),
        docker=providers.Factory(DockerExecutor),
    )
    
    # Agent 工厂
    agent_factory = providers.FactoryAggregate(
        tool_calling=providers.Factory(ToolCallingAgent),
        code=providers.Factory(CodeAgent),
    )
```

**阶段三：改造组件构造函数**

以 CodeAgent 为例：

```python
class CodeAgent(MultiStepAgent):
    def __init__(
        self,
        tools: dict[str, Tool],
        model: Model,
        python_executor: PythonExecutor,  # DI 注入
        memory: AgentMemory | None = None,  # DI 注入
        monitor: Monitor | None = None,  # DI 注入
        logger: AgentLogger | None = None,  # DI 注入
        ...
    ):
        super().__init__(tools, model, memory, monitor, logger)
        self.python_executor = python_executor
```

### 3.2 插件化架构设计

#### 插件接口设计

定义插件需要实现的接口：

```python
from abc import ABC, abstractmethod
from typing import Any

class SmolagentsPlugin(ABC):
    """smolagents 插件基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件唯一标识名"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本号"""
        pass
    
    def initialize(self, context: PluginContext) -> None:
        """插件初始化，注册组件"""
        pass
    
    def shutdown(self) -> None:
        """插件卸载时清理资源"""
        pass

class AgentPlugin(SmolagentsPlugin):
    """Agent 类型插件"""
    
    @abstractmethod
    def get_agent_class(self) -> type[MultiStepAgent]:
        """返回 Agent 类"""
        pass
    
    @abstractmethod
    def get_agent_config_schema(self) -> dict:
        """返回配置 JSON Schema"""
        pass

class ExecutorPlugin(SmolagentsPlugin):
    """执行器类型插件"""
    
    @abstractmethod
    def get_executor_class(self) -> type[PythonExecutor]:
        """返回 Executor 类"""
        pass
```

#### 插件注册机制

采用基于 entry_points 的自动发现机制：

**setup.py 配置**：

```python
setup(
    name="my-smolagents-plugin",
    entry_points={
        "smolagents.plugins": [
            "custom_agent = my_plugin:CustomAgentPlugin",
            "custom_executor = my_plugin:CustomExecutorPlugin",
        ]
    }
)
```

**PluginRegistry 实现**：

```python
import importlib.metadata
from typing import dict, Type

class PluginRegistry:
    """插件注册中心"""
    
    _agents: dict[str, Type[MultiStepAgent]] = {}
    _executors: dict[str, Type[PythonExecutor]] = {}
    _models: dict[str, Type[Model]] = {}
    
    @classmethod
    def discover_plugins(cls) -> None:
        """自动发现所有安装的插件"""
        for entry_point in importlib.metadata.entry_points(
            group="smolagents.plugins"
        ):
            plugin_class = entry_point.load()
            plugin = plugin_class()
            plugin.initialize(PluginContext(registry=cls))
    
    @classmethod
    def register_agent(cls, name: str, agent_class: Type[MultiStepAgent]) -> None:
        cls._agents[name] = agent_class
    
    @classmethod
    def register_executor(cls, name: str, executor_class: Type[PythonExecutor]) -> None:
        cls._executors[name] = executor_class
    
    @classmethod
    def get_agent(cls, name: str) -> Type[MultiStepAgent]:
        if name not in cls._agents:
            raise PluginNotFoundError(f"Agent plugin '{name}' not found")
        return cls._agents[name]
    
    @classmethod
    def list_agents(cls) -> list[str]:
        return list(cls._agents.keys())
```

#### 插件生命周期

```
安装阶段
    │
    ▼
发现阶段 → 调用 discover_plugins 扫描 entry_points
    │
    ▼
初始化阶段 → 调用 plugin.initialize 注册组件
    │
    ▼
运行阶段 → 组件可被正常使用
    │
    ▼
卸载阶段 → 调用 plugin.shutdown 清理资源
```

### 3.3 事件驱动模式

#### 事件总线设计

实现轻量级事件总线：

```python
from typing import Callable, Type
from collections import defaultdict
import asyncio

class EventBus:
    """事件总线，支持同步和异步事件"""
    
    def __init__(self):
        self._handlers: dict[Type, list[Callable]] = defaultdict(list)
        self._async_handlers: dict[Type, list[Callable]] = defaultdict(list)
    
    def subscribe(self, event_type: Type, handler: Callable) -> None:
        """订阅事件"""
        self._handlers[event_type].append(handler)
    
    def subscribe_async(self, event_type: Type, handler: Callable) -> None:
        """订阅异步事件"""
        self._async_handlers[event_type].append(handler)
    
    def publish(self, event: object) -> None:
        """发布同步事件"""
        event_type = type(event)
        for handler in self._handlers[event_type]:
            handler(event)
    
    async def publish_async(self, event: object) -> None:
        """发布异步事件"""
        event_type = type(event)
        # 并行执行所有异步处理器
        await asyncio.gather(*[
            handler(event) for handler in self._async_handlers[event_type]
        ])
```

#### 事件类型定义

定义标准事件类型：

```python
from dataclasses import dataclass
from typing import Any
from datetime import datetime

@dataclass
class AgentEvent:
    """Agent 相关事件基类"""
    agent_id: str
    timestamp: datetime

@dataclass
class StepStartedEvent(AgentEvent):
    """步骤开始事件"""
    step_number: int
    step_type: str  # "planning" | "action"

@dataclass
class StepCompletedEvent(AgentEvent):
    """步骤完成事件"""
    step_number: int
    duration_ms: int
    success: bool

@dataclass
class ToolCalledEvent(AgentEvent):
    """工具调用事件"""
    tool_name: str
    arguments: dict[str, Any]

@dataclass
class ToolCompletedEvent(AgentEvent):
    """工具完成事件"""
    tool_name: str
    output: Any
    error: str | None

@dataclass
class ModelCalledEvent(AgentEvent):
    """模型调用事件"""
    messages: list[dict]
    model_name: str

@dataclass
class ModelCompletedEvent(AgentEvent):
    """模型完成事件"""
    output: str
    token_usage: dict
    latency_ms: int
```

#### 订阅发布机制

示例：如何使用事件总线实现可观测性：

```python
class MonitoringPlugin:
    """监控插件，订阅事件并记录指标"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.metrics = MetricsCollector()
        self._subscribe_events()
    
    def _subscribe_events(self):
        # 订阅步骤完成事件
        self.event_bus.subscribe(
            StepCompletedEvent, 
            self._on_step_completed
        )
        # 订阅工具调用事件
        self.event_bus.subscribe(
            ToolCalledEvent,
            self._on_tool_called
        )
    
    def _on_step_completed(self, event: StepCompletedEvent):
        self.metrics.record_step_duration(
            event.step_number, 
            event.duration_ms
        )
    
    def _on_tool_called(self, event: ToolCalledEvent):
        self.metrics.increment_tool_counter(event.tool_name)
```

### 3.4 分层架构优化

#### 核心层 Core Layer

职责：定义抽象接口和领域模型

```
smolagents/core/
├── __init__.py
├── agent.py          # Agent 抽象基类
├── model.py          # Model 抽象基类
├── tool.py           # Tool 抽象基类
├── executor.py       # Executor 抽象基类
├── memory.py         # Memory 抽象基类
├── events.py         # 事件类型定义
├── exceptions.py     # 异常体系
└── types.py          # 共享类型定义
```

核心层特点：
- 无任何外部依赖
- 只包含抽象类和数据类
- 被所有其他层依赖

#### 扩展层 Extension Layer

职责：提供具体实现

```
smolagents/extensions/
├── __init__.py
├── agents/
│   ├── __init__.py
│   ├── tool_calling.py    # ToolCallingAgent
│   └── code.py            # CodeAgent
├── models/
│   ├── __init__.py
│   ├── openai.py          # OpenAIModel
│   ├── transformers.py    # TransformersModel
│   └── ...
├── executors/
│   ├── __init__.py
│   ├── local.py           # LocalPythonExecutor
│   ├── e2b.py             # E2BExecutor
│   └── ...
└── tools/
    ├── __init__.py
    └── default.py         # 默认工具集
```

扩展层特点：
- 依赖核心层
- 实现核心层定义的接口
- 通过插件机制注册

#### 适配层 Adapter Layer

职责：与外部系统集成

```
smolagents/adapters/
├── __init__.py
├── langchain.py      # LangChain 集成
├── mcp.py            # MCP 协议适配
├── hub.py            # Hugging Face Hub 适配
└── monitoring/
    ├── __init__.py
    ├── prometheus.py   # Prometheus 指标导出
    └── opentelemetry.py # OpenTelemetry 追踪
```

适配层特点：
- 隔离外部系统变化
- 提供统一的集成接口
- 可选依赖，不影响核心功能

---

## 四、新架构设计

### 4.1 组件关系图

![新架构组件关系图](./graphviz/smolagents-重构后架构图.svg)

### 4.2 架构对比

![新旧架构对比图](./graphviz/smolagents-架构对比图.svg)

**对比说明**：

| 维度 | 当前架构 | 重构后架构 |
|------|----------|------------|
| 依赖创建 | 组件内部创建 | DI 容器注入 |
| 扩展方式 | 修改源码 | 插件动态注册 |
| 组件关系 | 紧密耦合 | 依赖抽象接口 |
| 可观测性 | 回调函数 | 事件总线 |
| 测试难度 | 高 | 低 |

### 4.2 接口定义

#### Agent 接口

```python
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator
from dataclasses import dataclass

@dataclass
class RunResult:
    """Agent 执行结果"""
    output: Any
    steps: list[MemoryStep]
    token_usage: TokenUsage
    duration_ms: int

class Agent(ABC):
    """Agent 抽象接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def run(self, task: str, **kwargs) -> RunResult:
        """同步执行"""
        pass
    
    @abstractmethod
    def run_stream(self, task: str, **kwargs) -> Iterator[StreamEvent]:
        """流式执行"""
        pass
    
    @abstractmethod
    async def run_async(self, task: str, **kwargs) -> RunResult:
        """异步执行"""
        pass
```

#### Model 接口

```python
class Model(ABC):
    """模型抽象接口"""
    
    @abstractmethod
    def generate(
        self, 
        messages: list[ChatMessage],
        tools: list[Tool] | None = None,
        **kwargs
    ) -> ChatMessage:
        pass
    
    @abstractmethod
    def generate_stream(
        self,
        messages: list[ChatMessage],
        **kwargs
    ) -> Iterator[ChatMessageStreamDelta]:
        pass
    
    @property
    @abstractmethod
    def model_id(self) -> str:
        """模型唯一标识"""
        pass
```

### 4.3 数据流向

```
用户输入
    │
    ▼
┌─────────────────┐
│   Agent.run     │◀── DI 注入 Model、Tools、Executor
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Memory.to_messages │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Model.generate │────▶│   EventBus      │──▶监控/日志
└────────┬────────┘     └─────────────────┘
         │
         ▼
┌─────────────────┐
│  Tool/Executor  │────▶ 执行具体操作
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  结果返回给用户  │
└─────────────────┘
```

### 4.4 扩展点设计

| 扩展点 | 扩展方式 | 示例 |
|--------|----------|------|
| 新增 Agent 类型 | 继承 Agent + 插件注册 | 自定义推理 Agent |
| 新增 Model | 继承 Model + 插件注册 | 本地私有化部署模型 |
| 新增 Executor | 继承 Executor + 插件注册 | Kubernetes 执行器 |
| 新增 Tool | 继承 Tool | 数据库查询工具 |
| 新增监控适配器 | 订阅事件 | Prometheus 导出器 |
| 自定义 Memory | 继承 Memory | Redis 持久化存储 |

---

## 五、迁移路径

### 5.1 渐进式迁移策略

采用版本迭代方式逐步迁移：

**v1.x：当前版本**
- 保持现有架构稳定
- 添加抽象接口层，与现有实现共存

**v2.0：双模式版本**
- 引入 DI 容器，支持新旧两种创建方式
- 新增插件注册机制
- 原有代码完全兼容

**v2.1：事件系统**
- 添加事件总线
- 回调机制迁移到事件订阅
- 原有回调 API 保持兼容

**v2.2：完整新架构**
- 默认使用新架构
- 旧 API 标记为 deprecated
- 提供迁移指南

**v3.0：移除旧代码**
- 移除已废弃的旧 API
- 完全基于新架构

### 5.2 版本兼容性保证

**向后兼容策略**：

```python
class MultiStepAgent:
    """保持原有构造函数兼容"""
    
    def __init__(
        self,
        tools: list[Tool] | dict[str, Tool],
        model: Model,
        # 新增可选参数，默认 None 时内部创建
        memory: AgentMemory | None = None,
        monitor: Monitor | None = None,
        logger: AgentLogger | None = None,
        **kwargs
    ):
        # 如果未提供，则按原有方式创建
        self.memory = memory or AgentMemory()
        self.monitor = monitor or Monitor()
        self.logger = logger or AgentLogger()
        # ... 其余初始化
```

**兼容性测试**：
- 所有现有测试用例必须通过
- 添加兼容性测试套件
- CI 中同时测试新旧 API

### 5.3 测试策略

**测试金字塔**：

```
        /\
       /  \
      / E2E \      # 端到端测试：完整 Agent 工作流
     /--------\
    / Integration \  # 集成测试：多组件协作
   /----------------\
  /    Unit Tests    \  # 单元测试：单个组件
 /----------------------\
```

**各层测试重点**：

| 层级 | 重点 | 占比 |
|------|------|------|
| 单元测试 | 各组件独立测试，Mock 依赖 | 70% |
| 集成测试 | DI 容器、插件系统、事件总线 | 20% |
| 端到端 | 完整任务执行流程 | 10% |

---

## 六、风险与挑战

### 6.1 重构风险识别

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 功能回归 | 高 | 高 | 完整测试覆盖、灰度发布 |
| 性能下降 | 中 | 中 | 基准测试、性能监控 |
| 社区抵触 | 中 | 中 | 保持兼容、充分沟通 |
| 迁移成本 | 高 | 中 | 渐进迁移、详细文档 |
| 引入新 Bug | 中 | 高 | 代码审查、测试驱动 |

### 6.2 缓解措施

**功能回归风险**：
- 建立完整的回归测试套件
- 使用契约测试确保接口稳定
- 分阶段灰度发布

**性能下降风险**：
- 重构前建立性能基线
- 重构后进行对比测试
- DI 容器启用缓存避免重复创建

**社区抵触风险**：
- 提前发布 RFC 征求意见
- 保持 100% 向后兼容
- 提供详细的迁移指南

### 6.3 回滚策略

**代码回滚**：
```bash
# 使用 Git 标签标记稳定版本
git tag v1.x-stable
git push origin v1.x-stable

# 需要回滚时
git revert --no-commit HEAD~3..HEAD
git commit -m "Revert: rollback to stable version"
```

**功能开关**：
```python
# 使用特性开关控制新功能
USE_NEW_ARCHITECTURE = os.getenv("SMOLAGENTS_USE_NEW_ARCH", "false") == "true"

if USE_NEW_ARCHITECTURE:
    from .new import create_agent
else:
    from .legacy import create_agent
```

**数据兼容性**：
- Memory 序列化格式保持兼容
- 提供数据迁移脚本
- 新旧格式双写一段时间

---

## 七、实施计划

### 7.1 里程碑规划

| 里程碑 | 时间 | 交付物 | 验收标准 |
|--------|------|--------|----------|
| M1 | 第 1-2 周 | 抽象接口层 | 所有抽象类定义完成 |
| M2 | 第 3-4 周 | DI 容器 | 可通过 DI 创建所有组件 |
| M3 | 第 5-6 周 | 插件系统 | 可动态注册 Agent/Executor |
| M4 | 第 7-8 周 | 事件总线 | 所有关键操作发布事件 |
| M5 | 第 9-10 周 | 兼容层 | 所有现有测试通过 |
| M6 | 第 11-12 周 | 文档与发布 | 迁移文档、Release Note |

### 7.2 资源需求

| 角色 | 人数 | 职责 |
|------|------|------|
| 架构师 | 1 | 整体设计、代码审查 |
| 核心开发 | 2 | 核心层、DI 容器实现 |
| 测试工程师 | 1 | 测试策略、自动化测试 |
| 技术写作 | 1 | 文档、迁移指南 |

---

## 八、附录

### 8.1 术语表

| 术语 | 定义 |
|------|------|
| DI | Dependency Injection，依赖注入 |
| EventBus | 事件总线，发布订阅模式的实现 |
| Plugin | 插件，可动态加载的扩展模块 |
| Core Layer | 核心层，定义抽象接口 |
| Extension Layer | 扩展层，提供具体实现 |
| Adapter Layer | 适配层，与外部系统集成 |

### 8.2 参考文档

- [[17-smolagents-类图与依赖关系分析]]
- [[01-smolagents-Agent架构深度分析]]
- python-dependency-injector 官方文档
- Pluggy 插件系统设计

### 8.3 决策记录

**ADR-001：DI 框架选择**
- 选项：python-dependency-injector / injector / 自研
- 决策：使用 python-dependency-injector
- 理由：功能完整、文档丰富、社区活跃

**ADR-002：插件发现机制**
- 选项：entry_points / 配置文件 / 目录扫描
- 决策：使用 entry_points
- 理由：符合 Python 生态惯例，自动发现

**ADR-003：事件系统实现**
- 选项：自建 / 使用 asyncio / 使用第三方库
- 决策：自建轻量级实现
- 理由：避免额外依赖，满足基本需求

---

## 标签

主题：架构设计  
类型：技术方案  
项目：AI数据分析系统  
关联：smolagents
