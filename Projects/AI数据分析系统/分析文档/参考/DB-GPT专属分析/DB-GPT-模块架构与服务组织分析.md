# DB-GPT 模块架构与服务组织深度分析

**分析日期**: 2026-02-05  
**项目版本**: DB-GPT v0.7.0  
**核心结论**: **基于 Monorepo 的组件化架构（Component-Based Architecture）**，通过 SystemApp 统一管理组件生命周期，AWEL 实现工作流编排

---

## 一、架构总体定位

### 1.1 一句话定义

> **DB-GPT 是基于 Monorepo 的组件化架构，通过 SystemApp 统一管理组件生命周期，各模块以 BaseComponent 形式注册到系统中，通过依赖注入获取其他组件。核心特点是：代码分层清晰、组件可插拔、AWEL 工作流编排、统一模型服务管理。**

### 1.2 架构对比

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    架构类型对比                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  传统单体 (Monolith)        微服务 (Microservices)      DB-GPT (组件化架构)   │
│  ┌───────────────┐          ┌─┐ ┌─┐ ┌─┐ ┌─┐            ┌─────────────────┐  │
│  │  Web+Biz+Data │          │W│ │B│ │D│ │S│            │  Monorepo 结构   │  │
│  │   紧耦合      │          │e│ │i│ │a│ │e│            ├─────────────────┤  │
│  │               │          │b│ │z│ │t│ │a│            │  dbgpt-core     │  │
│  │  单进程部署   │          │ │ │ │ │a│ │r│            │  (核心组件)      │  │
│  └───────────────┘          │ │ │ │ │ │ │c│            ├─────────────────┤  │
│                             │ │ │ │ │ │ │ │            │  dbgpt-serve    │  │
│  缺点：                      │ │ │ │ │ │ │ │            │  (服务层)        │  │
│  • 代码膨胀                  └─┘ └─┘ └─┘ └─┘            ├─────────────────┤  │
│  • 无法独立扩展                 ↑ ↑ ↑ ↑                 │  dbgpt-app      │  │
│  • 技术栈单一                   网络通信                 │  (应用层)        │  │
│  • 缺乏复用性                                          │  dbgpt-ext      │  │
│                                                        │  (扩展)          │  │
│                                                                             │
│  微服务缺点：                   DB-GPT特点：                                │
│  • 运维复杂度高                 • 代码分层清晰（Monorepo）                   │
│  • 分布式事务                   • 组件可插拔（Component机制）                │
│  • 网络延迟                     • 统一模型服务管理                          │
│  • 服务治理成本高               • AWEL 工作流编排                           │
│                                 • 类型安全（Python 泛型）                   │
│                                 • 易于测试和扩展                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、Monorepo 包结构

### 2.1 包分层架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     DB-GPT Monorepo 包结构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L1: 应用层 (dbgpt-app)                                             │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  职责：Web 服务、API 路由、场景管理、业务流程编排            │   │   │
│  │  │  路径：packages/dbgpt-app/src/dbgpt_app/                     │   │   │
│  │  │  ├── openapi/api_v1/        # API 路由                      │   │   │
│  │  │  ├── scene/                 # 聊天场景（ChatWithDbExecute等）│   │   │
│  │  │  ├── knowledge/             # 知识库管理                   │   │   │
│  │  │  ├── operators/             # AWEL 场景算子                │   │   │
│  │  │  └── initialization/        # 系统初始化                   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L2: 服务层 (dbgpt-serve)                                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  职责：业务服务、数据访问、外部接口封装                      │   │   │
│  │  │  路径：packages/dbgpt-serve/src/dbgpt_serve/                 │   │   │
│  │  │  ├── agent/                 # Agent 服务                   │   │   │
│  │  │  ├── rag/                   # RAG 服务                     │   │   │
│  │  │  ├── conversation/          # 对话管理                     │   │   │
│  │  │  ├── datasource/            # 数据源管理                   │   │   │
│  │  │  ├── flow/                  # AWEL Flow 服务              │   │   │
│  │  │  ├── model/                 # 模型部署服务                 │   │   │
│  │  │  ├── prompt/                # Prompt 管理                 │   │   │
│  │  │  └── file/                  # 文件管理                    │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L3: 核心层 (dbgpt-core) ★ 最核心                                   │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  职责：基础组件、AWEL 引擎、模型抽象、存储抽象               │   │   │
│  │  │  路径：packages/dbgpt-core/src/dbgpt/                        │   │   │
│  │  │  ├── core/awel/             # ★ AWEL 工作流引擎            │   │   │
│  │  │  │   ├── dag/               # DAG 管理                     │   │   │
│  │  │  │   ├── operators/         # 算子实现                     │   │   │
│  │  │  │   ├── trigger/           # 触发器（HTTP等）             │   │   │
│  │  │  │   └── runner/            # 执行引擎                     │   │   │
│  │  │  ├── agent/                # Agent 框架                   │   │   │
│  │  │  ├── model/                # 模型管理                     │   │   │
│  │  │  │   ├── cluster/           # 模型集群管理                 │   │   │
│  │  │  │   ├── proxy/             # 代理模型                    │   │   │
│  │  │  │   └── adapters/          # 模型适配器                  │   │   │
│  │  │  ├── rag/                  # RAG 核心                     │   │   │
│  │  │  │   ├── embedding/         # Embedding 工厂              │   │   │
│  │  │  │   ├── retriever/         # 检索器                      │   │   │
│  │  │  │   └── operators/         # RAG 算子                   │   │   │
│  │  │  ├── storage/              # 存储抽象                     │   │   │
│  │  │  ├── datasource/           # 数据源抽象                   │   │   │
│  │  │  └── component.py          # ★ 组件基类                  │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L4: 扩展层 (dbgpt-ext)                                             │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  职责：第三方集成、具体实现、可选依赖                        │   │   │
│  │  │  路径：packages/dbgpt-ext/src/dbgpt_ext/                     │   │   │
│  │  │  ├── datasource/            # 数据源连接器（MySQL/PG等）     │   │   │
│  │  │  ├── storage/vector_store/ # 向量存储实现                  │   │   │
│  │  │  ├── rag/                  # RAG 扩展实现                   │   │   │
│  │  │  └── ...                   # 其他扩展                      │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  L5: 客户端层 (dbgpt-client)                                        │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  职责：对外 SDK、CLI 工具、API 客户端                        │   │   │
│  │  │  路径：packages/dbgpt-client/src/dbgpt_client/               │   │   │
│  │  │  ├── _cli.py                # CLI 入口                      │   │   │
│  │  │  ├── flow.py                # Flow API 客户端              │   │   │
│  │  │  └── schema.py              # 数据模型                     │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 包依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                    包依赖关系图                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   dbgpt-client                                              │
│        ↓                                                     │
│   dbgpt-app  ←────── 依赖 ──────→  dbgpt-serve              │
│        ↓                              ↓                      │
│        └──────────────────┬───────────┘                      │
│                           ↓                                  │
│                      dbgpt-core ★ 核心                       │
│                           ↓                                  │
│                      dbgpt-ext (可选)                        │
│                                                              │
│   说明：                                                     │
│   • 上层包依赖下层包                                         │
│   • dbgpt-core 是核心，不依赖其他业务包                     │
│   • dbgpt-ext 提供具体实现，可替换                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、组件系统（SystemApp）

### 3.1 核心概念

**SystemApp** 是 DB-GPT 的组件管理核心，负责组件的注册、初始化和生命周期管理。

```python
# packages/dbgpt-core/src/dbgpt/component.py

class SystemApp(LifeCycle):
    """Main System Application class that manages the lifecycle and registration of
    components."""

    def __init__(self, asgi_app: Optional["FastAPI"] = None):
        self.components: Dict[str, BaseComponent] = {}  # 组件注册表
        self._asgi_app = asgi_app
        self._stop_event = threading.Event()

    def register(self, component: Type[T], *args, **kwargs) -> T:
        """Register a new component by its type."""
        # 创建组件实例并注册
        component_instance = component(self, *args, **kwargs)
        self.components[component.name] = component_instance
        return component_instance

    def get_component(self, name: str, component_type: Type[T], ...) -> T:
        """Get a component by its name."""
        # 从注册表获取组件
        return self.components.get(name)
```

### 3.2 组件类型枚举

```python
class ComponentType(str, Enum):
    """预定义的组件类型标识"""
    
    WORKER_MANAGER = "dbgpt_worker_manager"           # 模型 Worker 管理
    MODEL_CONTROLLER = "dbgpt_model_controller"       # 模型控制器
    MODEL_REGISTRY = "dbgpt_model_registry"           # 模型注册表
    AGENT_MANAGER = "dbgpt_agent_manager"             # Agent 管理器
    AWEL_DAG_MANAGER = "dbgpt_awel_dag_manager"       # AWEL DAG 管理
    AWEL_TRIGGER_MANAGER = "dbgpt_awel_trigger_manager"  # AWEL 触发器
    RAG_STORAGE_MANAGER = "dbgpt_rag_storage_manager" # RAG 存储管理
    CONNECTOR_MANAGER = "dbgpt_connector_manager"     # 数据源连接器
    VARIABLES_PROVIDER = "dbgpt_variables_provider"   # 变量提供器
    EXECUTOR_DEFAULT = "dbgpt_thread_pool_default"    # 线程池执行器
    TRACER = "dbgpt_tracer"                           # 追踪器
```

### 3.3 组件生命周期

```
┌─────────────────────────────────────────────────────────────┐
│                    组件生命周期                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   创建 ──→ 初始化 ──→ 启动前 ──→ 启动后 ──→ 停止前 ──→ 停止  │
│    │         │          │          │          │        │    │
│    │         │          │          │          │        │    │
│    ▼         ▼          ▼          ▼          ▼        ▼    │
│  __init__  on_init()  before_start() after_start() ...      │
│            after_init() async_before_start()                │
│                                                              │
│   代码示例：                                                 │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ class MyComponent(BaseComponent):                   │   │
│   │     name = "my_component"                           │   │
│   │                                                     │   │
│   │     def on_init(self):                              │   │
│   │         # 初始化配置                                │   │
│   │         pass                                        │   │
│   │                                                     │   │
│   │     def after_init(self):                           │   │
│   │         # 初始化数据库连接                          │   │
│   │         pass                                        │   │
│   │                                                     │   │
│   │     async def async_before_start(self):             │   │
│   │         # 启动前异步初始化                          │   │
│   │         pass                                        │   │
│   │                                                     │   │
│   │     def before_stop(self):                          │   │
│   │         # 优雅关闭                                  │   │
│   │         pass                                        │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 组件使用示例

```python
# 1. 定义组件
class MyService(BaseComponent):
    name = "my_service"  # 组件唯一标识
    
    def __init__(self, system_app):
        super().__init__(system_app)
        self.db = None
    
    def after_init(self):
        # 初始化数据库连接
        self.db = create_db_connection()
    
    def do_something(self):
        return self.db.query(...)

# 2. 注册组件
system_app = SystemApp(app)
system_app.register(MyService)

# 3. 获取组件使用
my_service = system_app.get_component("my_service", MyService)
result = my_service.do_something()

# 4. 在 AWEL 算子中使用
class MyOperator(MapOperator):
    async def map(self, input_value):
        # 从 DAG 上下文获取 SystemApp
        system_app = self.system_app
        my_service = system_app.get_component("my_service", MyService)
        return my_service.do_something(input_value)
```

---

## 四、模块间通信机制

### 4.1 通信方式总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      模块间通信机制                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. 组件依赖注入（SystemApp）★ 最常用                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Operator → SystemApp → Component                                  │   │
│  │      ↓          ↓           ↓                                      │   │
│  │  获取依赖    注册表查找    返回实例                                 │   │
│  │                                                                     │   │
│  │  特点：                                                           │   │
│  │  • 同进程内直接调用（函数/方法调用）                                │   │
│  │  • 类型安全，支持泛型                                               │   │
│  │  • 生命周期由 SystemApp 管理                                        │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  2. AWEL 工作流编排 ★ 业务逻辑编排                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Trigger → Operator A → Operator B → Operator C                    │   │
│  │      ↓          ↓           ↓            ↓                         │   │
│  │  HTTP请求    数据转换      模型调用       结果解析                  │   │
│  │                                                                     │   │
│  │  特点：                                                           │   │
│  │  • 声明式 DAG 定义                                                  │   │
│  │  • 异步执行                                                         │   │
│  │  • 可视化编排                                                       │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  3. 模型服务通信（Worker Manager）                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Web Server          Worker Manager          Model Worker          │   │
│  │  ┌─────────┐        ┌─────────────┐          ┌─────────────┐      │   │
│  │  │ 请求推理 │───────→│ 路由/负载均衡 │─────────→│ 加载模型    │      │   │
│  │  │         │        │ 健康检查     │          │ 执行推理    │      │   │
│  │  └─────────┘        └─────────────┘          └─────────────┘      │   │
│  │       ↑                                              │             │   │
│  │       └──────────────────────────────────────────────┘             │   │
│  │                    返回生成结果                                     │   │
│  │                                                                     │   │
│  │  通信方式：HTTP / gRPC（可配置）                                    │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  4. 数据库共享状态                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  模块 A ←──→ MySQL/SQLite ←──→ 模块 B                              │   │
│  │  ┌─────────┐        ┌─────────┐          ┌─────────────┐           │   │
│  │  │ 写入状态 │───────→│  task   │─────────→│  读取状态    │           │   │
│  │  │  table  │        │  table  │          │  更新状态    │           │   │
│  │  └─────────┘        └─────────┘          └─────────────┘           │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 SystemApp 依赖注入详解

```python
# 实际代码示例：从 API 层到服务层的调用

# packages/dbgpt-app/src/dbgpt_app/openapi/api_v1/api_v1.py
@router.post("/v1/chat/completions")
async def chat_completions(
    request: CommonLLMHttpRequestBody,
):
    # 1. 从全局 Config 获取 SystemApp
    system_app = CFG.SYSTEM_APP
    
    # 2. 获取 WorkerManager（模型服务）
    worker_manager = system_app.get_component(
        ComponentType.WORKER_MANAGER_FACTORY, 
        WorkerManagerFactory
    ).create()
    
    # 3. 获取 DAGManager（AWEL 工作流）
    dag_manager = DAGManager.get_instance(system_app)
    
    # 4. 获取执行器
    executor = system_app.get_component(
        ComponentType.EXECUTOR_DEFAULT,
        ExecutorFactory
    ).create()
    
    # 5. 执行业务逻辑
    ...

# 实际代码示例：AWEL 算子中获取组件
# packages/dbgpt-app/src/dbgpt_app/scene/operators/app_operator.py
class AppChatComposerOperator(MapOperator):
    async def map(self, input_value: ChatComposerInput) -> ModelRequest:
        # 从算子基类获取 system_app
        system_app = self.system_app
        
        # 获取 Agent 管理器
        agent_manager = system_app.get_component(
            ComponentType.AGENT_MANAGER, 
            AgentManager
        )
        
        # 获取变量提供器
        variables_provider = system_app.get_component(
            ComponentType.VARIABLES_PROVIDER,
            VariablesProvider
        )
        
        # 执行业务逻辑
        ...
```

### 4.3 AWEL 工作流通信

```python
# packages/dbgpt-core/src/dbgpt/core/awel/dag/base.py

class DAG:
    """DAG（有向无环图）是 AWEL 的核心数据结构"""
    
    def __init__(self, dag_id: str):
        self._dag_id = dag_id
        self.node_map: Dict[str, DAGNode] = {}  # 节点映射
        self._root_nodes: List[DAGNode] = []     # 根节点
        self._leaf_nodes: List[DAGNode] = []     # 叶子节点
        
    def _append_node(self, node: DAGNode):
        """添加节点到 DAG"""
        self.node_map[node.node_id] = node

class DAGNode(DependencyMixin):
    """DAG 节点基类"""
    
    def __init__(self):
        self._upstream: List["DAGNode"] = []    # 上游节点
        self._downstream: List["DAGNode"] = []  # 下游节点
        self._system_app: Optional[SystemApp] = None
        
    def set_upstream(self, nodes):
        """设置上游节点"""
        for node in nodes:
            self._upstream.append(node)
            node._downstream.append(self)

# 工作流执行示例
with DAG("my_workflow") as dag:
    # 1. 定义触发器
    trigger = HttpTrigger("/api/chat", methods="POST")
    
    # 2. 定义算子
    parse_op = RequestParseOperator()
    llm_op = LLMOperator(model_name="gpt-4")
    output_op = MapOperator(lambda x: x.to_dict())
    
    # 3. 连接 DAG
    trigger >> parse_op >> llm_op >> output_op

# 运行时执行流程：
# 1. HTTP 请求触发 trigger
# 2. trigger 输出传递给 parse_op
# 3. parse_op 输出传递给 llm_op
# 4. llm_op 调用模型服务生成回复
# 5. 最终结果传递给 output_op 格式化
```

### 4.4 模型服务通信

```python
# packages/dbgpt-core/src/dbgpt/model/cluster/worker/manager.py

class LocalWorkerManager(WorkerManager):
    """本地 Worker 管理器"""
    
    def __init__(self):
        self.workers: Dict[str, List[WorkerRunData]] = dict()  # Worker 注册表
        self.model_registry: ModelRegistry = None  # 模型注册表
        
    async def start_worker(self, worker_params: ModelWorkerParameters):
        """启动模型 Worker"""
        # 1. 创建 Worker 实例
        worker = self._create_worker(worker_params)
        
        # 2. 注册到本地注册表
        worker_key = self._worker_key(worker_params.worker_type, worker_params.model_name)
        self.workers[worker_key] = worker
        
        # 3. 启动 Worker
        await worker.start()
        
    async def generate(self, model_name: str, prompt: str) -> ModelOutput:
        """调用模型生成"""
        # 1. 查找可用的 Worker
        worker = self._get_worker(model_name)
        
        # 2. 发送生成请求
        return await worker.generate(prompt)
        
    async def embeddings(self, model_name: str, texts: List[str]) -> List[List[float]]:
        """调用 Embedding 模型"""
        worker = self._get_worker(model_name)
        return await worker.embeddings(texts)
```

---

## 五、核心服务详解

### 5.1 服务基类设计

```python
# packages/dbgpt-serve/src/dbgpt_serve/core/service.py

class BaseService(BaseComponent, Generic[T, REQ, RES], ABC):
    """服务层基类"""
    
    name = "dbgpt_serve_base_service"
    _dag_manager: Optional[DAGManager] = None
    _system_app: Optional[SystemApp] = None

    def __init__(self, system_app):
        super().__init__(system_app)
        self._system_app = system_app

    @property
    @abstractmethod
    def dao(self) -> BaseDao[T, REQ, RES]:
        """数据访问对象"""
        
    @property
    @abstractmethod
    def config(self) -> BaseServeConfig:
        """服务配置"""
        
    def create(self, request: REQ) -> RES:
        """创建实体"""
        return self.dao.create(request)
        
    def get(self, id: str) -> Optional[RES]:
        """获取实体"""
        return self.dao.get_by_id(id)
        
    def update(self, id: str, request: REQ) -> RES:
        """更新实体"""
        return self.dao.update(id, request)
        
    def delete(self, id: str) -> None:
        """删除实体"""
        return self.dao.delete(id)
```

### 5.2 服务注册与发现

```python
# 服务注册示例
class FlowService(BaseService):
    name = "flow_service"
    
    def init_app(self, system_app: SystemApp):
        super().init_app(system_app)
        # 注册到 SystemApp
        system_app.register(FlowService, self)

# 服务获取示例
class SomeOperator(MapOperator):
    async def map(self, input_value):
        # 方式1：通过 SystemApp 获取
        flow_service = self.system_app.get_component(
            "flow_service", 
            FlowService
        )
        
        # 方式2：通过 get_instance 静态方法获取
        flow_service = FlowService.get_instance(self.system_app)
        
        # 使用服务
        flow = flow_service.get(flow_id)
        ...
```

---

## 六、服务部署架构

### 6.1 部署模式

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      部署模式对比                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  模式1: All-in-One（开发/测试）                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  单进程部署                                                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │   │
│  │  │ Web Server  │  │  AWEL DAG   │  │ Model Worker│                 │   │
│  │  │  (FastAPI)  │  │   Runner    │  │  (本地加载)  │                 │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                 │   │
│  │         │                │                │                        │   │
│  │         └────────────────┴────────────────┘                        │   │
│  │                          │                                         │   │
│  │                   ┌──────┴──────┐                                  │   │
│  │                   │  SystemApp  │                                  │   │
│  │                   │  (组件管理)  │                                  │   │
│  │                   └──────┬──────┘                                  │   │
│  │                          │                                         │   │
│  │         ┌────────────────┼────────────────┐                        │   │
│  │         ↓                ↓                ↓                        │   │
│  │    ┌─────────┐     ┌─────────┐     ┌─────────┐                    │   │
│  │    │  MySQL  │     │  Redis  │     │ ChromaDB│                    │   │
│  │    └─────────┘     └─────────┘     └─────────┘                    │   │
│  │                                                                     │   │
│  │  特点：启动简单，适合开发调试                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  模式2: Web + Worker 分离（生产）                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Web Server 容器                      Model Worker 容器             │   │
│  │  ┌─────────────────────┐              ┌─────────────────────┐      │   │
│  │  │ FastAPI             │              │ Worker Manager      │      │   │
│  │  │ - API 路由          │◄────────────►│ - 模型加载          │      │   │
│  │  │ - AWEL Trigger      │   HTTP/gRPC  │ - 推理服务          │      │   │
│  │  │ - SystemApp         │              │ - 心跳上报          │      │   │
│  │  └─────────────────────┘              └─────────────────────┘      │   │
│  │           │                                    │                   │   │
│  │           └────────────────┬───────────────────┘                   │   │
│  │                            │                                       │   │
│  │                      ┌─────┴──────┐                                │   │
│  │                      │   MySQL    │                                │   │
│  │                      │   Redis    │                                │   │
│  │                      └────────────┘                                │   │
│  │                                                                     │   │
│  │  特点：Web 和 Worker 可独立扩缩容，Worker 可部署在 GPU 节点           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  模式3: 集群模式（大规模生产）                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │   ┌─────────┐    ┌─────────┐    ┌─────────┐                      │   │
│  │   │ Web-1   │    │ Web-2   │    │ Web-N   │   # 负载均衡         │   │
│  │   │ (FastAPI)    │ (FastAPI)    │ (FastAPI)                      │   │
│  │   └────┬────┘    └────┬────┘    └────┬────┘                      │   │
│  │        └───────────────┼───────────────┘                          │   │
│  │                        │                                          │   │
│  │                   ┌────┴────┐                                      │   │
│  │                   │  Nginx  │  # 反向代理                          │   │
│  │                   └────┬────┘                                      │   │
│  │        ┌───────────────┼───────────────┐                          │   │
│  │        ↓               ↓               ↓                          │   │
│  │   ┌─────────┐     ┌─────────┐     ┌─────────┐                    │   │
│  │   │Worker-1 │     │Worker-2 │     │Worker-N │   # GPU 集群       │   │
│  │   │(LLM)    │     │(Embed)  │     │(Rerank) │                    │   │
│  │   └─────────┘     └─────────┘     └─────────┘                    │   │
│  │                                                                     │   │
│  │  特点：高可用、可扩展、支持多种模型类型部署                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Docker Compose 部署

```yaml
# docker-compose.yml 核心服务定义

services:
  # ========== DB-GPT Web 服务 ==========
  webserver:
    image: eosphorosai/dbgpt-openai:latest
    command: dbgpt start webserver --config /app/configs/dbgpt-proxy-siliconflow.toml
    environment:
      - DB_GPT_APP_CONFIG_PATH=/app/configs/dbgpt-proxy-siliconflow.toml
    ports:
      - "5670:5670"
    depends_on:
      - db
      - redis

  # ========== Model Worker（可选分离部署） ==========
  # worker:
  #   image: eosphorosai/dbgpt:latest
  #   command: dbgpt start worker --model_name qwen --model_path /models/qwen
  #   deploy:
  #     resources:
  #       reservations:
  #         devices:
  #           - driver: nvidia
  #             count: 1
  #             capabilities: [gpu]

  # ========== 依赖服务 ==========
  db:
    image: mysql/mysql-server
    environment:
      MYSQL_ROOT_PASSWORD: aa123456
    volumes:
      - dbgpt-myql-db:/var/lib/mysql
      - ./assets/schema/dbgpt.sql:/docker-entrypoint-initdb.d/dbgpt.sql

  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data
```

---

## 七、模块间连接关系图

### 7.1 完整连接关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DB-GPT 模块连接关系全景图                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         API 层 (dbgpt-app)                          │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  FastAPI Router                                              │   │   │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │   │   │
│  │  │  │/v1/chat  │ │/v1/agent │ │/v1/rag   │ │/v1/flow    │  │   │   │
│  │  │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └──────┬──────┘  │   │   │
│  │  │        └─────────────┴─────────────┴──────────────┘         │   │   │
│  │  │                      │                                       │   │   │
│  │  │                      ▼                                       │   │   │
│  │  │              ┌──────────────┐                               │   │   │
│  │  │              │  ChatFactory │──┬── ChatWithDbExecute         │   │   │
│  │  │              │  (场景工厂)   │  ├── ChatKnowledge             │   │   │
│  │  │              └──────────────┘  ├── ChatAgent                 │   │   │
│  │  │                                 └── ChatNormal                │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                          │
│                                   │ SystemApp.get_component()               │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       服务层 (dbgpt-serve)                          │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │FlowService  │ │AgentService │ │RAGService   │ │ModelService │   │   │
│  │  │             │ │             │ │             │ │             │   │   │
│  │  │• 工作流管理 │ │• Agent管理  │ │• 知识库检索 │ │• 模型部署   │   │   │
│  │  │• DAG执行   │ │• 工具调用   │ │• 文档解析   │ │• 推理服务   │   │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘   │   │
│  │         │               │               │               │          │   │
│  │         └───────────────┴───────────────┴───────────────┘          │   │
│  │                                     │                                │   │
│  │                                     ▼                                │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  DAO (数据访问)                                              │   │   │
│  │  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────────┐  │   │   │
│  │  │  │FlowDao    │ │AgentDao   │ │RAGDao     │ │ModelDao     │  │   │   │
│  │  │  └───────────┘ └───────────┘ └───────────┘ └─────────────┘  │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                          │
│                                   │ SystemApp.register() / get_component()  │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       核心层 (dbgpt-core)                           │   │
│  │                                                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐   │   │
│  │  │   AWEL 引擎     │  │   模型管理      │  │    Agent 框架     │   │   │
│  │  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌─────────────┐  │   │   │
│  │  │  │DAGManager │  │  │  │WorkerMgr  │  │  │  │AgentManager │  │   │   │
│  │  │  │TriggerMgr │  │  │  │ModelReg   │  │  │  │ResourceMgr  │  │   │   │
│  │  │  │Operators  │  │  │  │Adapters   │  │  │  │Memory       │  │   │   │
│  │  │  └───────────┘  │  │  └───────────┘  │  │  └─────────────┘  │   │   │
│  │  └─────────────────┘  └─────────────────┘  └───────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐   │   │
│  │  │   RAG 核心      │  │   存储抽象      │  │    组件系统       │   │   │
│  │  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌─────────────┐  │   │   │
│  │  │  │Embedding  │  │  │  │VectorStore│  │  │  │SystemApp    │  │   │   │
│  │  │  │Retriever  │  │  │  │GraphStore │  │  │  │BaseComponent│  │   │   │
│  │  │  │ChunkManager│  │  │  │FullText   │  │  │  │LifeCycle    │  │   │   │
│  │  │  └───────────┘  │  │  └───────────┘  │  │  └─────────────┘  │   │   │
│  │  └─────────────────┘  └─────────────────┘  └───────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                          │
│                                   │ 具体实现                                 │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       扩展层 (dbgpt-ext)                            │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │   │
│  │  │MySQL Connector  │PG Connector  │ChromaDB     │Milvus       │   │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                   │                                          │
│                                   ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       外部依赖                                        │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │  MySQL  │ │  Redis  │ │ ChromaDB│ │ Milvus  │ │  ES     │       │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 八、与 RAGFlow 架构对比

### 8.1 架构差异对比表

| 维度 | RAGFlow | DB-GPT |
|------|---------|--------|
| **架构模式** | 模块化单体 | Monorepo + 组件化 |
| **代码组织** | 单一仓库，目录分层 | 多包结构（packages/*） |
| **模块通信** | Redis 队列 + 函数调用 | SystemApp 组件注入 + AWEL |
| **工作流引擎** | Canvas DSL（JSON 定义） | AWEL（Python DSL） |
| **模型管理** | 集成在 Web Server | Worker Manager 独立 |
| **扩展机制** | Plugin 系统 | Component 可插拔 |
| **部署灵活性** | 多进程合一/分离 | Web + Worker 可独立部署 |

### 8.2 设计理念差异

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    设计理念对比                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  RAGFlow                                                      DB-GPT         │
│                                                                              │
│  ┌───────────────────┐                          ┌───────────────────┐       │
│  │ "产品优先"        │                          │ "框架优先"        │       │
│  │                   │                          │                   │       │
│  │ • 开箱即用        │                          │ • 可扩展性强      │       │
│  │ • 预设场景丰富    │                          │ • 组件可替换      │       │
│  │ • 模板驱动        │                          │ • 编排能力强大    │       │
│  │ • 面向最终用户    │                          │ • 面向开发者      │       │
│  └───────────────────┘                          └───────────────────┘       │
│                                                                              │
│  ┌───────────────────┐                          ┌───────────────────┐       │
│  │ "紧密集成的 RAG"  │                          │ "模型即服务"      │       │
│  │                   │                          │                   │       │
│  │ • 文档处理深度优化│                          │ • 统一模型管理    │       │
│  │ • 检索算法精细    │                          │ • 多模型调度      │       │
│  │ • GraphRAG 内置   │                          │ • 部署模式灵活    │       │
│  └───────────────────┘                          └───────────────────┘       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 九、总结

### 9.1 核心架构特点

| 特性 | 实现方式 | 说明 |
|------|----------|------|
| **架构模式** | Monorepo + 组件化 | 代码分层清晰，模块可插拔 |
| **组件管理** | SystemApp | 统一生命周期管理，依赖注入 |
| **工作流编排** | AWEL | Python DSL，声明式 DAG |
| **模型服务** | Worker Manager | 支持本地/远程/集群部署 |
| **存储抽象** | BaseDAO + Storage | 统一数据访问接口 |
| **扩展机制** | BaseComponent | 插件化开发 |

### 9.2 一句话总结

> **DB-GPT 采用 Monorepo 组件化架构，通过 SystemApp 统一管理组件生命周期，AWEL 实现工作流编排，模型服务通过 Worker Manager 灵活部署。架构核心优势是：组件可插拔、类型安全、易于测试和扩展。**

### 9.3 适用场景

| 场景 | 推荐部署方式 | 说明 |
|------|-------------|------|
| 快速原型开发 | All-in-One | 单进程启动，开发效率高 |
| 企业生产环境 | Web + Worker 分离 | 独立扩缩容，资源隔离 |
| 大规模模型服务 | 集群模式 | 多 Worker 负载均衡 |
| 自定义扩展开发 | Monorepo 组件开发 | 基于 BaseComponent 扩展 |

---

## 十、关联文档

- [[DB-GPT架构分析]]: 系统整体架构设计
- [[DB-GPT-AWEL实现机制详解]]: 工作流编排详解
- [[开源项目目录结构分析]]: 项目代码组织对比
- [[RAGFlow-模块架构与服务组织分析]]: 对比 RAGFlow 架构
