# smolagents vs TaskWeaver 架构对比

> 分析日期: 2026-02-06
> 对比项目: smolagents vs TaskWeaver

---

## 一、总体架构对比

### 1.1 架构模式差异

| 维度 | smolagents | TaskWeaver |
|------|------------|------------|
| 核心模式 | ReAct + Tool/Code | Planner-Worker |
| 代码量 | 约6000行 | 约20000行 |
| 架构复杂度 | 极简 | 复杂 |
| 组件耦合 | 紧耦合 | 松耦合 |
| 配置方式 | Python代码 | YAML声明式 |

### 1.2 架构图示

**smolagents 架构**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        smolagents 核心架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                    MultiStepAgent (抽象基类)                         │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │  │
│   │  │    Tools    │  │    Model    │  │   Memory    │  │  Executor  │ │  │
│   │  │   工具集合   │  │   模型接口   │  │   记忆系统   │  │  代码执行器 │ │  │
│   │  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘ │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│           ┌──────────────────┼──────────────────┐                          │
│           ▼                  ▼                  ▼                          │
│   ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                 │
│   │ ToolCallingAgent│  │   CodeAgent   │  │  ManagedAgent │                 │
│   │  (JSON Tool Call)│  │ (Python Code) │  │  (子Agent)    │                 │
│   └───────────────┘  └───────────────┘  └───────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**TaskWeaver 架构**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TaskWeaver App Layer                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │  TaskWeaverApp  │───▶│ SessionManager  │───▶│      Session(s)         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Dependency Injection Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │PluginModule │ │LoggingModule│ │RoleModule   │ │ExecutionServiceModule│   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘   │
│                              (injector 库实现)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent Core Layer                                   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                         Planner (Role)                          │      │
│   │  ┌──────────────────────────────────────────────────────────┐   │      │
│   │  │  - 接收用户请求，制定执行计划                              │   │      │
│   │  │  - 决策调用哪个 Worker                                    │   │      │
│   │  │  - 管理对话流程                                           │   │      │
│   │  └──────────────────────────────────────────────────────────┘   │      │
│   └────────────────────────────┬────────────────────────────────────┘      │
│                                │                                            │
│           ┌────────────────────┼────────────────────┐                       │
│           ▼                    ▼                    ▼                       │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                │
│   │CodeInterpreter│   │WebExplorer    │   │   ...其他      │                │
│   │   (Worker)    │   │   (Worker)    │   │   Worker      │                │
│   └───────────────┘   └───────────────┘   └───────────────┘                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 核心差异总结

smolagents 采用**扁平化设计**，所有功能围绕 MultiStepAgent 基类展开。开发者通过组合 Tools 和选择 Agent 类型来构建应用。

TaskWeaver 采用**分层设计**，明确划分 Planner、Worker、Role 三个层次。Planner 负责决策，Worker 负责执行，Role 定义统一接口。这种设计带来更强的扩展性，但也增加了复杂度。

---

## 二、Agent设计对比

### 2.1 smolagents Agent体系

smolagents 的 Agent 设计围绕 **MultiStepAgent** 抽象基类展开：

```python
class MultiStepAgent(ABC):
    """
    Agent class that solves the given task step by step, using the ReAct framework:
    While the objective is not reached, the agent will perform a cycle of 
    action (given by the LLM) and observation (obtained from the environment).
    """
```

**核心属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| tools | dict[str, Tool] | 工具字典，key 为工具名 |
| model | Model | LLM 模型接口 |
| memory | AgentMemory | 记忆系统 |
| max_steps | int | 最大执行步数，默认 20 |
| managed_agents | dict | 子 Agent 字典 |
| python_executor | PythonExecutor | Python 代码执行器 |

**两种具体实现**

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| ToolCallingAgent | 使用 JSON 格式的 Tool Call，利用 LLM 原生 tool calling 能力 | 结构化任务，需要并行执行多个工具 |
| CodeAgent | 工具调用以 Python 代码形式表达，然后解析执行 | 复杂数据处理，需要灵活代码执行 |

### 2.2 TaskWeaver Agent体系

TaskWeaver 的 Agent 设计基于 **Role-Planner-Worker** 三层架构：

**Role 基类**

```python
class Role:
    @inject
    def __init__(
        self,
        config: RoleConfig,
        logger: TelemetryLogger,
        tracing: Tracing,
        event_emitter: SessionEventEmitter,
        role_entry: Optional[RoleEntry] = None,
    ):
```

所有 Agent 都继承 Role 基类，通过依赖注入获取所需组件。

**Planner 角色**

```python
class Planner(Role):
    @inject
    def __init__(
        self,
        config: PlannerConfig,
        logger: TelemetryLogger,
        tracing: Tracing,
        event_emitter: SessionEventEmitter,
        llm_api: LLMApi,
        workers: Dict[str, Role],        # 关键：持有所有 Worker
        round_compressor: Optional[RoundCompressor],
        post_translator: PostTranslator,
        experience_generator: Optional[ExperienceGenerator] = None,
    ):
```

Planner 是系统的决策中心，负责：
- 接收用户请求并制定执行计划
- 决策调用哪个 Worker
- 管理对话流程，最多 max_self_ask_num=3 次自校正

**Worker 角色**

```python
class CodeInterpreter(Role, Interpreter):
    @inject
    def __init__(
        self,
        generator: CodeGenerator,      # 代码生成器
        executor: CodeExecutor,        # 代码执行器
        logger: TelemetryLogger,
        tracing: Tracing,
        event_emitter: SessionEventEmitter,
        config: CodeInterpreterConfig,
        role_entry: RoleEntry,
    ):
```

Worker 是具体执行者，如 CodeInterpreter 负责代码生成和执行。

### 2.3 Agent设计差异对比

| 维度 | smolagents | TaskWeaver |
|------|------------|------------|
| 继承关系 | 继承 MultiStepAgent | 继承 Role |
| 依赖注入 | 无 | 使用 injector 库 |
| 配置方式 | Python 参数 | YAML 配置文件 |
| 决策位置 | 每个 Agent 自主决策 | Planner 统一决策 |
| 自我校正 | 无内置机制 | 最多 3 次自校正 |
| 角色扩展 | 运行时动态配置 | 声明式 YAML 配置 |

---

## 三、代码执行对比

### 3.1 smolagents 执行器体系

smolagents 支持 **6种执行器**，覆盖本地到云端的各种场景：

| 执行器 | 类型 | 适用场景 | 安全性 |
|--------|------|---------|--------|
| LocalPythonExecutor | 本地 | 开发/测试 | 低，依赖白名单 |
| E2BExecutor | 云端沙箱 | 生产 | 高 |
| DockerExecutor | 容器 | 生产 | 高 |
| WasmExecutor | WebAssembly | 浏览器 | 高 |
| ModalExecutor | Serverless | 生产 | 高 |
| BlaxelExecutor | Serverless | 生产 | 高 |

**LocalPythonExecutor 安全机制**

```python
BASE_BUILTIN_MODULES = [
    "math", "random", "datetime", "collections", 
    "itertools", "json", "re", "statistics", 
    # 其他安全模块
]

# 危险模块被禁止
DANGEROUS_MODULES = ["os", "sys", "subprocess", "importlib", ...]
```

通过白名单机制控制可导入的模块，防止恶意代码执行。

### 3.2 TaskWeaver 执行体系

TaskWeaver 使用 **IPython Kernel** 作为唯一的代码执行后端：

```
┌─────────────────────────────────────────────────────────────┐
│                     CodeExecutor                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐      ┌─────────────────────────────┐   │
│  │   exec_mgr      │─────▶│     Session Client          │   │
│  │ (Manager 接口)   │      │  - 管理 IPython Kernel      │   │
│  └─────────────────┘      │  - 保持执行状态              │   │
│                           └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   IPython Kernel (ces)                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           TaskWeaverContextMagic (Magic)            │    │
│  │  - _taskweaver_update_session_var (更新变量)        │    │
│  │  - _taskweaver_session_init (初始化上下文)          │    │
│  │  - _taskweaver_plugin_register (注册插件)           │    │
│  │  - _taskweaver_plugin_load (加载插件)               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**IPython Magic 状态保持**

```python
@cell_magic
def _taskweaver_update_session_var(self, line: str, cell: str):
    """更新会话变量到 IPython 命名空间"""
    json_dict_str = cell
    session_var_dict = json.loads(json_dict_str)
    self.executor.update_session_var(session_var_dict)
    return fmt_response(True, "Session var updated.", self.executor.session_var)
```

TaskWeaver 通过 IPython Magic 命令实现状态保持，这是其核心优势之一。

### 3.3 代码执行对比总结

| 维度 | smolagents | TaskWeaver |
|------|------------|------------|
| 执行器数量 | 6种 | 1种 |
| 执行环境 | 本地/云端/容器/WebAssembly | 仅本地 IPython |
| 状态保持 | 无，每次执行独立 | 有，IPython Kernel 保持变量 |
| 安全机制 | 白名单/沙箱 | 代码验证+模块白名单 |
| 云端部署 | 原生支持 | 需要额外封装 |
| 适用场景 | 需要灵活部署 | 需要状态连续性 |

---

## 四、多Agent对比

### 4.1 smolagents 多Agent机制

smolagents 采用 **Manager-Managed** 层级结构：

```
Manager Agent (CodeAgent)
    ├── Code Interpreter Tool
    └── Web Search Agent (ToolCallingAgent) [managed_agent]
            ├── Web Search Tool
            └── Visit Webpage Tool
```

**核心设计原则**

1. **单一管理入口**：每个 Manager Agent 统一管理其下属的 managed_agents
2. **透明调用**：子 Agent 对父 Agent 而言如同普通 Tool
3. **职责分离**：Manager 负责决策规划，Managed Agent 负责专项执行
4. **结果封装**：子 Agent 的执行结果被包装为字符串返回

**子 Agent 调用流程**

```
父Agent调用子Agent
       │
       ▼
┌─────────────────┐
│ 包装任务prompt  │  ← 添加managed_agent.task模板
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 子Agent.run()   │  ← 独立执行ReAct循环
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 提取最终结果    │  ← 从RunResult或原始输出
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 包装结果prompt  │  ← 添加managed_agent.report模板
└────────┬────────┘
         │
         ▼
返回字符串给父Agent
```

### 4.2 TaskWeaver 多Agent机制

TaskWeaver 采用 **Planner-Worker** 协作模式：

```
User Query
    │
    ▼
Planner.reply() ──plan──▶ CodeInterpreter.reply()
    ▲                          │
    └────────result────────────┘
    │
    ▼
Planner整合输出
```

**消息驱动架构**

TaskWeaver 通过 Post 消息实现多 Agent 通信：

```python
@dataclass
class Post:
    id: str
    send_from: RoleName      # 发送者
    send_to: RoleName        # 接收者
    message: str             # 文本消息
    attachment_list: List[Attachment]  # 附件列表
```

**共享内存机制**

Planner 通过 SharedMemoryEntry 向 Workers 传递计划信息，实现跨 Agent 状态共享。

### 4.3 多Agent机制对比

| 维度 | smolagents Manager-Managed | TaskWeaver Planner-Worker |
|------|---------------------------|--------------------------|
| 关系类型 | 树形层级 | 星形辐射 |
| 通信方式 | 同步函数调用 | 异步消息传递 |
| 决策机制 | Manager 自主决策 | Planner 统一调度 |
| 状态共享 | 通过 additional_args 显式传递 | 通过共享内存隐式共享 |
| 角色定义 | 运行时动态配置 | 声明式 YAML 配置 |
| 子Agent并行 | 不支持 | 不支持 |

### 4.4 优劣分析

**smolagents 优势**

1. 实现简单：Managed Agent 本质是可调用的 Agent 实例
2. 学习成本低：无需理解复杂的角色系统
3. 灵活组合：任意 Agent 都可以成为 Manager 或 Managed
4. 透明调用：对 LLM 而言 Tool 和 Agent 调用语法一致

**smolagents 劣势**

1. 无状态隔离：子 Agent 执行不保持跨调用状态
2. 缺乏协调：多个子 Agent 之间无法直接通信
3. 监控分散：需要手动聚合多 Agent 的指标
4. 容错有限：子 Agent 失败不自动触发重试或切换

**TaskWeaver 优势**

1. 状态持久：IPython Kernel 保持执行状态
2. 消息驱动：基于 Post 的异步通信支持复杂交互
3. 经验学习：内置 RAG 从历史对话学习
4. 角色扩展：通过 YAML 声明式定义新 Worker

**TaskWeaver 劣势**

1. 架构复杂：依赖注入、角色系统增加理解门槛
2. 配置分散：配置分散在多个 YAML 文件
3. 单点瓶颈：所有决策经过 Planner

---

## 五、扩展性对比

### 5.1 smolagents 扩展机制

**@tool 装饰器**

```python
@tool
def search_web(query: str) -> str:
    """
    Search the web for information.
    
    Args:
        query: The search query
    
    Returns:
        Search results as a string
    """
    # 实现代码
    return results
```

装饰器自动：
- 提取函数名作为 tool name
- 解析 docstring 作为 description
- 从 type hints 生成 inputs schema

**Callback 系统**

```python
agent.run("任务", on_step_start=my_callback)
```

**MCP 集成**

smolagents 支持通过 MCP 协议集成外部工具服务。

### 5.2 TaskWeaver 扩展机制

**依赖注入扩展**

```python
# 创建新 Worker 的步骤
class MyWorker(Role):
    @inject
    def __init__(self, config: MyConfig, ...):
        super().__init__(config, ...)
    
    def reply(self, memory: Memory, **kwargs) -> Post:
        # 实现核心逻辑
        pass
```

**YAML 声明式配置**

```yaml
# my_worker.role.yaml
alias: "MyWorker"
module: "my_module.MyWorker"
intro: "A custom worker that..."
```

**Plugin 系统**

```python
class Plugin(ABC):
    def __init__(self, name: str, ctx: PluginContext, config: Dict[str, Any]):
        self.name = name
        self.ctx = ctx
        self.config = config
    
    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """插件入口点"""
```

TaskWeaver 通过 IPython Magic 动态加载插件到执行环境。

### 5.3 扩展性对比

| 维度 | smolagents | TaskWeaver |
|------|------------|------------|
| 工具扩展 | @tool 装饰器 | Plugin 系统 |
| Agent扩展 | 运行时配置 | YAML声明式+继承Role |
| 依赖管理 | 手动传递 | 依赖注入自动管理 |
| 配置方式 | Python代码 | YAML+JSON |
| 扩展复杂度 | 低 | 高 |
| 企业级特性 | 少 | 多 |

---

## 六、适用场景对比

### 6.1 场景推荐表

| 场景 | 推荐选择 | 理由 |
|------|---------|------|
| 快速原型 | smolagents | 代码简洁，几行代码即可搭建 Agent |
| 复杂数据管道 | TaskWeaver | Planner-Worker 更适合多阶段处理 |
| 多 Agent 协作 | TaskWeaver | Plugin 系统和消息驱动更完善 |
| 教育场景 | smolagents | 代码易读，架构清晰 |
| 生产部署 | 两者皆可 | smolagents 更简单，TaskWeaver 更强大 |
| 云端执行 | smolagents | 支持 E2B/Docker/Modal 等多种执行器 |
| 状态连续性 | TaskWeaver | IPython Kernel 保持变量状态 |
| 经验学习 | TaskWeaver | 内置 RAG 经验检索机制 |

### 6.2 详细场景分析

**快速原型场景**

smolagents 更适合快速验证想法：

```python
from smolagents import CodeAgent, HfApiModel

agent = CodeAgent(tools=[], model=HfApiModel())
agent.run("分析销售数据")
```

TaskWeaver 需要配置 YAML 文件和初始化多个组件。

**企业级数据分析场景**

TaskWeaver 更适合：
- 需要保持数据加载状态
- 需要经验复用
- 需要安全验证
- 需要多 Worker 协作

**教育演示场景**

smolagents 更适合：
- 代码量小，学生易于理解
- 架构扁平，无复杂依赖
- 文档简洁，上手快

---

## 七、设计哲学对比

### 7.1 smolagents 设计哲学

**极简主义，够用就好**

smolagents 的核心设计目标是：用最少的代码实现强大的 Agent 功能。

- 核心代码约 1800 行，实现完整 Agent 框架
- 避免过度设计，只保留必要功能
- 清晰的 ReAct 循环实现
- 双模式 Agent 满足不同场景

**设计理念体现**

1. **扁平化**：所有功能围绕 MultiStepAgent 展开
2. **透明性**：Tool 和 Agent 调用语法一致
3. **灵活性**：6种执行器覆盖各种部署场景
4. **简洁性**：@tool 装饰器一行代码定义工具

### 7.2 TaskWeaver 设计哲学

**企业级，功能完备**

TaskWeaver 的设计目标是：构建生产级的数据分析 Agent 系统。

- 分层解耦，Planner-Worker-Role 职责明确
- 依赖注入实现组件解耦
- 经验学习支持从历史对话检索
- 状态保持通过 IPython Kernel 实现

**设计理念体现**

1. **分层架构**：Planner 决策，Worker 执行，Role 定义接口
2. **依赖注入**：使用 injector 库实现组件解耦
3. **声明式配置**：YAML 文件定义角色和配置
4. **企业级特性**：安全验证、经验学习、对话压缩

### 7.3 设计哲学对比表

| 维度 | smolagents | TaskWeaver |
|------|------------|------------|
| 核心目标 | 极简实现 | 企业级完备 |
| 代码量 | 约 1800 行核心代码 | 约 20000 行 |
| 架构风格 | 扁平化 | 分层化 |
| 耦合度 | 紧耦合 | 松耦合 |
| 学习曲线 | 平缓 | 陡峭 |
| 功能覆盖 | 核心功能 | 全功能 |
| 适用规模 | 中小型项目 | 大型项目 |

---

## 八、选型建议

### 8.1 选择 smolagents 的情况

- 需要快速验证 Agent 概念
- 团队技术能力有限，需要简单易懂的框架
- 需要云端或容器化部署
- 教育场景或演示用途
- 项目规模较小，不需要复杂协作

### 8.2 选择 TaskWeaver 的情况

- 构建企业级数据分析系统
- 需要复杂的多 Agent 协作
- 需要状态保持和经验学习
- 有专门的工程团队维护
- 项目规模大，需要长期演进

### 8.3 混合方案建议

对于我们的 AI数据分析系统 项目，可以考虑**混合方案**：

```
Orchestrator (类似TaskWeaver Planner)
    ├── 状态管理器 (保持跨Agent状态)
    ├── 经验学习模块 (RAG检索)
    └── Agent调度器
            │
            ├── DataAgent (smolagents风格)
            │       └── tools: [sql_tool, viz_tool]
            │
            ├── CodeAgent (smolagents风格)
            │       └── executor: DockerExecutor
            │
            └── SearchAgent (smolagents风格)
                    └── tools: [web_search, crawler]
```

**核心思想**

- 使用 TaskWeaver 的**分层思想**进行高层规划
- 使用 smolagents 的**轻量设计**实现具体 Agent
- 自定义**状态管理层**解决跨 Agent 数据共享
- 保留**代码执行器**的多种后端选择

---

## 九、总结

### 9.1 核心差异速查表

| 对比维度 | smolagents | TaskWeaver |
|---------|------------|------------|
| **架构模式** | ReAct + Tool/Code | Planner-Worker |
| **代码量** | 约6000行 | 约20000行 |
| **Agent设计** | MultiStepAgent + 两种实现 | Role + Planner + Worker |
| **代码执行** | 6种执行器 | IPython Kernel |
| **多Agent** | Manager-Managed层级 | Plugin系统 |
| **扩展性** | @tool + Callback + MCP | 依赖注入 + Plugin |
| **设计哲学** | 极简主义 | 企业级完备 |

### 9.2 关键洞察

1. **smolagents 胜在简洁**：1800行核心代码实现完整功能，适合快速上手和原型验证
2. **TaskWeaver 胜在完备**：分层架构、依赖注入、经验学习，适合企业级应用
3. **两者各有侧重**：没有绝对优劣，只有场景适配
4. **可以取长补短**：考虑混合方案，结合两者优势

### 9.3 参考文档

- [[01-smolagents-Agent架构深度分析]]
- [[06-smolagents-多Agent系统深度分析]]
- [[TaskWeaver-Agent架构深度分析]]
