# DB-GPT 分布式架构实现详解

**分析日期**: 2026-02-05  
**项目版本**: DB-GPT v0.7.0  
**核心结论**: **基于 Controller-Worker 模式的分布式模型服务架构，支持独立扩缩容、负载均衡和多模型并行部署**

---

## 一、分布式架构概览

### 1.1 架构拓扑

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DB-GPT 分布式架构全景                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         接入层（可横向扩展）                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │   │
│  │  │  WebServer  │  │  WebServer  │  │  WebServer  │  ...           │   │
│  │  │  Port:5670  │  │  Port:5671  │  │  Port:5672  │                │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                │   │
│  │         └─────────────────┴─────────────────┘                      │   │
│  │                           │                                         │   │
│  │                      ┌────┴────┐                                    │   │
│  │                      │  Nginx  │  ← 负载均衡                        │   │
│  │                      │ 或 K8s  │                                    │   │
│  │                      └────┬────┘                                    │   │
│  └───────────────────────────┼────────────────────────────────────────┘   │
│                              │                                              │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      控制层（Controller）★                           │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                   Model Controller                           │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │   │
│  │  │  │   Registry  │  │   Health    │  │   Router    │          │   │   │
│  │  │  │  模型注册表  │  │   健康检查   │  │   路由分发   │          │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │   │
│  │  │                                                              │   │   │
│  │  │  • 维护 Worker 注册信息                                       │   │   │
│  │  │  • 心跳检测与故障剔除                                         │   │   │
│  │  │  • 模型实例路由                                               │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────┬────────────────────────────────────┘   │
│                                   │                                         │
│          ┌────────────────────────┼────────────────────────┐               │
│          │                        │                        │               │
│          ▼                        ▼                        ▼               │
│  ┌───────────────┐        ┌───────────────┐        ┌───────────────┐      │
│  │   Worker-1    │        │   Worker-2    │        │   Worker-N    │      │
│  │  (GPU Node 1) │        │  (GPU Node 2) │        │  (GPU Node N) │      │
│  │               │        │               │        │               │      │
│  │ • LLM Model   │        │ • Embedding   │        │ • Reranker    │      │
│  │ • Qwen-72B    │        │ • bge-large   │        │ • bge-rerank  │      │
│  │               │        │               │        │               │      │
│  │ Port: 8001    │        │ Port: 8002    │        │ Port: 8003    │      │
│  └───────┬───────┘        └───────┬───────┘        └───────┬───────┘      │
│          │                        │                        │               │
│          └────────────────────────┼────────────────────────┘               │
│                                   │                                         │
│                              ┌────┴────┐                                    │
│                              │  MySQL  │  ← 共享元数据                       │
│                              │  Redis  │  ← 缓存/消息队列                    │
│                              └─────────┘                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 四种服务角色

| 服务角色 | 启动命令 | 核心职责 | 部署特性 |
|---------|----------|----------|----------|
| **Controller** | `dbgpt start controller` | 模型注册中心、服务发现、健康检查 | 单点/集群均可 |
| **Worker** | `dbgpt start worker` | 模型加载、推理计算 | 多实例、GPU节点 |
| **WebServer** | `dbgpt start webserver` | HTTP API、Web UI、业务逻辑 | 可横向扩展 |
| **APIServer** | `dbgpt start apiserver` | OpenAI-compatible API | 轻量级、无Web |

---

## 二、核心组件详解

### 2.1 Controller（模型注册中心）

Controller 是分布式架构的核心，负责 Worker 的注册发现和服务治理。

```python
# packages/dbgpt-core/src/dbgpt/model/cluster/controller/controller.py

class BaseModelController(BaseComponent):
    """模型控制器基类"""
    name = ComponentType.MODEL_CONTROLLER

    @abstractmethod
    async def register_instance(self, instance: ModelInstance) -> bool:
        """注册 Worker 实例"""

    @abstractmethod
    async def deregister_instance(self, instance: ModelInstance) -> bool:
        """注销 Worker 实例"""

    @abstractmethod
    async def get_all_instances(self, model_name: str) -> List[ModelInstance]:
        """获取所有模型实例"""

    @abstractmethod
    async def send_heartbeat(self, instance: ModelInstance) -> bool:
        """接收心跳"""
```

**Controller 的三种实现模式**：

```
┌─────────────────────────────────────────────────────────────┐
│                    Controller 模式                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  模式1: 嵌入式（Embedded）                                   │
│  ┌─────────────────────────────────────┐                    │
│  │  WebServer 进程                      │                    │
│  │  ┌─────────────────────────────┐   │                    │
│  │  │  EmbeddedModelRegistry      │   │                    │
│  │  │  (内存中的注册表)            │   │                    │
│  │  └─────────────────────────────┘   │                    │
│  └─────────────────────────────────────┘                    │
│  适用：单机部署、开发测试                                    │
│                                                              │
│  模式2: 独立进程（Standalone）                              │
│  ┌─────────────────────────────────────┐                    │
│  │  Controller 进程                     │                    │
│  │  ┌─────────────────────────────┐   │                    │
│  │  │  LocalModelController       │   │                    │
│  │  │  + EmbeddedModelRegistry    │   │                    │
│  │  └─────────────────────────────┘   │                    │
│  └─────────────────────────────────────┘                    │
│  适用：中小规模生产                                          │
│                                                              │
│  模式3: 远程模式（Remote）                                   │
│  ┌─────────────────────────────────────┐                    │
│  │  WebServer/Worker                   │                    │
│  │  ┌─────────────────────────────┐   │                    │
│  │  │  _RemoteModelController     │   │                    │
│  │  │  (HTTP 客户端)               │   │                    │
│  │  └─────────────────────────────┘   │                    │
│  │           │                        │                    │
│  │           ▼ HTTP                   │                    │
│  │  ┌─────────────────────────────┐   │                    │
│  │  │  Controller 服务 (远端)      │   │                    │
│  │  └─────────────────────────────┘   │                    │
│  └─────────────────────────────────────┘                    │
│  适用：大规模分布式                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Worker（模型推理服务）

Worker 是实际承载模型推理的节点，支持多种模型类型。

```python
# packages/dbgpt-core/src/dbgpt/model/cluster/worker/manager.py

class LocalWorkerManager(WorkerManager):
    """本地 Worker 管理器"""
    
    def __init__(self):
        # Worker 注册表：model_name -> [WorkerRunData]
        self.workers: Dict[str, List[WorkerRunData]] = dict()
        self.executor = ThreadPoolExecutor(max_workers=os.cpu_count() * 5)
        self.model_registry: ModelRegistry = None
        
    async def start_worker(self, worker_params: ModelWorkerParameters):
        """启动模型 Worker"""
        # 1. 创建 Worker 实例
        worker = self._create_worker(worker_params)
        
        # 2. 注册到本地
        worker_key = self._worker_key(worker_params.worker_type, 
                                       worker_params.model_name)
        self.workers[worker_key] = worker
        
        # 3. 向 Controller 注册
        await self.register_func(worker.run_data)
        
        # 4. 启动心跳
        asyncio.create_task(self._send_heartbeat(worker.run_data))

# Worker 类型枚举
class WorkerType(Enum):
    LLM = "llm"                    # 大语言模型
    TEXT2VEC = "text2vec"          # Embedding 模型
    RERANKER = "reranker"          # 重排序模型
    SPEECH2TEXT = "speech2text"    # 语音识别
    TEXT2IMAGE = "text2image"      # 文生图
    IMAGE2TEXT = "image2text"      # 图生文
```

**Worker 启动流程**：

```
┌─────────────────────────────────────────────────────────────┐
│                    Worker 启动流程                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 解析参数                                                  │
│     ├── model_name: 模型名称（如 qwen-72b）                  │
│     ├── model_path: 模型路径                                 │
│     ├── worker_type: llm/text2vec/reranker                  │
│     ├── port: 服务端口号                                     │
│     └── controller_addr: Controller 地址                     │
│         │                                                    │
│         ▼                                                    │
│  2. 加载模型                                                  │
│     ├── 下载/加载模型权重                                    │
│     ├── 初始化 tokenizer                                    │
│     └── 预热（可选）                                         │
│         │                                                    │
│         ▼                                                    │
│  3. 启动 HTTP 服务                                            │
│     ├── FastAPI 应用                                         │
│     ├── /generate 接口                                       │
│     ├── /embeddings 接口                                     │
│     └── /health 健康检查                                     │
│         │                                                    │
│         ▼                                                    │
│  4. 向 Controller 注册                                        │
│     POST /api/controller/models                              │
│     {                                                        │
│       "model_name": "qwen-72b",                              │
│       "host": "192.168.1.10",                                │
│       "port": 8001,                                          │
│       "healthy": true                                        │
│     }                                                        │
│         │                                                    │
│         ▼                                                    │
│  5. 启动心跳                                                  │
│     每 20 秒发送心跳                                         │
│     POST /api/controller/heartbeat                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、服务注册与发现

### 3.1 注册表实现

```python
# packages/dbgpt-core/src/dbgpt/model/cluster/registry.py

class EmbeddedModelRegistry(ModelRegistry):
    """嵌入式模型注册表（内存实现）"""
    
    def __init__(self):
        # 注册表结构: {model_name: [ModelInstance, ...]}
        self.registry: Dict[str, List[ModelInstance]] = defaultdict(list)
        
        # 心跳配置
        self.heartbeat_interval_secs = 60    # 检查间隔
        self.heartbeat_timeout_secs = 120    # 超时时间
        
        # 启动心跳检查线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_checker)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    async def register_instance(self, instance: ModelInstance) -> bool:
        """注册模型实例"""
        model_name = instance.model_name.strip()
        host = instance.host.strip()
        port = instance.port
        
        # 检查是否已存在
        instances, exist_ins = self._get_instances(model_name, host, port)
        
        if exist_ins:
            # 更新已有实例
            ins = exist_ins[0]
            ins.weight = instance.weight
            ins.healthy = True
            ins.last_heartbeat = datetime.now()
        else:
            # 添加新实例
            instance.healthy = True
            instance.last_heartbeat = datetime.now()
            instances.append(instance)
        return True

    def _heartbeat_checker(self):
        """后台心跳检查线程"""
        while True:
            for instances in self.registry.values():
                for instance in instances:
                    # 检查是否超时
                    if (datetime.now() - instance.last_heartbeat > 
                        timedelta(seconds=self.heartbeat_timeout_secs)):
                        instance.healthy = False  # 标记为不健康
            time.sleep(self.heartbeat_interval_secs)
```

### 3.2 ModelInstance 结构

```python
# packages/dbgpt-core/src/dbgpt/model/base.py

class ModelInstance(BaseModel):
    """模型实例信息"""
    model_name: str              # 模型名称
    model_version: str           # 模型版本
    host: str                    # 主机地址
    port: int                    # 端口号
    healthy: bool = True         # 健康状态
    enabled: bool = True         # 是否启用
    weight: int = 1              # 权重（负载均衡用）
    last_heartbeat: datetime     # 最后心跳时间
    check_healthy: bool = True   # 是否检查健康
    
    # 扩展信息
    prompt_template: str = None  # Prompt 模板
    context_length: int = None   # 上下文长度
    max_concurrency: int = 5     # 最大并发
```

### 3.3 服务发现流程

```
┌─────────────────────────────────────────────────────────────┐
│                    服务发现流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  WebServer 需要调用 qwen-72b 模型                            │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────┐                                │
│  │  1. 查询 Controller      │                                │
│  │     GET /api/controller/models?qwen-72b                  │
│  └─────────────────────────┘                                │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────┐                                │
│  │  2. Registry 查询        │                                │
│  │     registry["qwen-72b"] │                                │
│  │     → [Instance1, Instance2, Instance3]                  │
│  └─────────────────────────┘                                │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────┐                                │
│  │  3. 健康过滤             │                                │
│  │     instances = [i for i in instances if i.healthy]      │
│  │     → [Instance1, Instance3]  # Instance2 已下线         │
│  └─────────────────────────┘                                │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────┐                                │
│  │  4. 负载均衡选择         │                                │
│  │     selected = random.choice(instances)                  │
│  │     → Instance3 (host: 192.168.1.12, port: 8003)         │
│  └─────────────────────────┘                                │
│         │                                                    │
│         ▼                                                    │
│  ┌─────────────────────────┐                                │
│  │  5. 发起推理请求         │                                │
│  │     POST http://192.168.1.12:8003/generate               │
│  └─────────────────────────┘                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 四、负载均衡策略

### 4.1 随机选择（Random）

```python
# packages/dbgpt-core/src/dbgpt/model/cluster/registry.py

class EmbeddedModelRegistry(ModelRegistry):
    async def select_one_health_instance(self, model_name: str) -> ModelInstance:
        """选择一个健康的实例（随机算法）"""
        # 1. 获取健康实例
        instances = await self.get_all_instances(model_name, healthy_only=True)
        
        # 2. 过滤启用的实例
        instances = [i for i in instances if i.enabled]
        
        if not instances:
            return None
        
        # 3. 随机选择
        return random.choice(instances)
```

### 4.2 WorkerManager 层负载均衡

```python
# packages/dbgpt-core/src/dbgpt/model/cluster/worker/manager.py

class LocalWorkerManager(WorkerManager):
    async def select_one_instance(
        self, 
        worker_type: WorkerType, 
        model: str, 
        healthy_only: bool = True
    ) -> WorkerRunData:
        """选择一个 Worker 实例"""
        worker_key = self._worker_key(worker_type, model)
        worker_instances = self.workers.get(worker_key, [])
        
        if healthy_only:
            worker_instances = [w for w in worker_instances if w.healthy]
        
        if not worker_instances:
            raise Exception(f"No worker found for {worker_key}")
        
        # 随机选择一个
        return random.choice(worker_instances)
```

### 4.3 负载均衡策略对比

| 策略 | 实现 | 适用场景 |
|------|------|----------|
| **Random** | `random.choice()` | 默认策略，简单有效 |
| **Weight** | 按权重随机 | 不同配置的服务器 |
| **Round Robin** | 轮询（可实现） | 均匀分配 |
| **Least Conn** | 最少连接（可实现） | 长连接场景 |

---

## 五、通信机制

### 5.1 HTTP REST API

Controller、Worker、WebServer 之间通过 HTTP REST API 通信：

```python
# packages/dbgpt-core/src/dbgpt/model/cluster/controller/controller.py

class _RemoteModelController(APIMixin, BaseModelController):
    """远程 Controller 客户端"""
    
    def __init__(self, urls: str):
        self.urls = urls  # Controller 地址
        
    @api_remote(path="/api/controller/models", method="POST")
    async def register_instance(self, instance: ModelInstance) -> bool:
        """向远程 Controller 注册"""
        pass
    
    @api_remote(path="/api/controller/models", method="DELETE")
    async def deregister_instance(self, instance: ModelInstance) -> bool:
        """向远程 Controller 注销"""
        pass
    
    @api_remote(path="/api/controller/models")
    async def get_all_instances(self, model_name: str) -> List[ModelInstance]:
        """查询模型实例列表"""
        pass
    
    @api_remote(path="/api/controller/heartbeat", method="POST")
    async def send_heartbeat(self, instance: ModelInstance) -> bool:
        """发送心跳"""
        pass
```

### 5.2 关键 API 接口

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/controller/models` | POST | Worker 注册 |
| `/api/controller/models` | DELETE | Worker 注销 |
| `/api/controller/models` | GET | 查询模型实例 |
| `/api/controller/heartbeat` | POST | 心跳上报 |
| `/generate` | POST | 模型推理 |
| `/embeddings` | POST | Embedding |
| `/health` | GET | 健康检查 |

### 5.3 通信流程示例

```
┌─────────────────────────────────────────────────────────────┐
│                    推理请求通信流程                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  用户 ──→ WebServer ──→ WorkerManager ──→ Worker           │
│                                                              │
│  1. 用户请求                                                 │
│     POST /v1/chat/completions                                │
│     {                                                        │
│       "model": "qwen-72b",                                   │
│       "messages": [...]                                      │
│     }                                                        │
│         │                                                    │
│         ▼                                                    │
│  2. WebServer 处理                                           │
│     ├─ 从请求中解析 model_name                               │
│     ├─ 调用 WorkerManagerFactory.create()                   │
│     └─ 获取 WorkerManager 实例                               │
│         │                                                    │
│         ▼                                                    │
│  3. WorkerManager 路由                                       │
│     ├─ 查询 Controller 获取可用实例                          │
│     ├─ 执行负载均衡选择                                      │
│     └─ 返回 Worker 地址 (192.168.1.10:8001)                 │
│         │                                                    │
│         ▼                                                    │
│  4. 调用 Worker                                              │
│     POST http://192.168.1.10:8001/generate                   │
│     {                                                        │
│       "model": "qwen-72b",                                   │
│       "prompt": "...",                                       │
│       "temperature": 0.7                                     │
│     }                                                        │
│         │                                                    │
│         ▼                                                    │
│  5. Worker 推理                                              │
│     ├─ 加载模型（已预加载）                                  │
│     ├─ 执行 generate()                                       │
│     └─ 返回生成结果                                          │
│         │                                                    │
│         ▼                                                    │
│  6. 返回用户                                                 │
│     {                                                        │
│       "choices": [{"message": {"content": "..."}}]           │
│     }                                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、心跳与健康检查

### 6.1 心跳机制

```python
# Worker 端心跳发送
async def _async_heartbeat_sender(
    worker_run_data: WorkerRunData,
    heartbeat_interval: int = 20,  # 每 20 秒
    send_heartbeat_func: SendHeartbeatFunc,
):
    """Worker 心跳发送器"""
    while not worker_run_data.stop_event.is_set():
        try:
            await send_heartbeat_func(worker_run_data)
        except Exception as e:
            logger.warning(f"Send heartbeat failed: {e}")
        finally:
            await asyncio.sleep(heartbeat_interval)

# Controller 端心跳处理
async def send_heartbeat(self, instance: ModelInstance) -> bool:
    """接收心跳，更新实例状态"""
    instances, exist_ins = self._get_instances(
        instance.model_name, 
        instance.host, 
        instance.port
    )
    if exist_ins:
        ins = exist_ins[0]
        ins.healthy = True
        ins.last_heartbeat = datetime.now()  # 更新时间戳
        return True
    return False
```

### 6.2 故障检测

```python
def _heartbeat_checker(self):
    """Controller 故障检测线程"""
    while True:
        for model_name, instances in self.registry.items():
            for instance in instances:
                # 计算时间差
                time_diff = datetime.now() - instance.last_heartbeat
                
                # 超过 120 秒未收到心跳，标记为不健康
                if time_diff > timedelta(seconds=self.heartbeat_timeout_secs):
                    if instance.healthy:
                        logger.warning(
                            f"Worker {instance.host}:{instance.port} "
                            f"heartbeat timeout, mark as unhealthy"
                        )
                        instance.healthy = False
        
        time.sleep(self.heartbeat_interval_secs)  # 每 60 秒检查一次
```

### 6.3 故障恢复

```
┌─────────────────────────────────────────────────────────────┐
│                    故障检测与恢复                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────┐                               ┌──────────────┐               │
│  │ Worker-1 │── Heartbeat (每 20s) ────────→│  Controller  │               │
│  │ (Healthy)│                               │              │               │
│  └──────────┘                               └──────────────┘               │
│         │                                          │                        │
│         │  网络故障/进程崩溃                        │  心跳检测线程           │
│         │  （心跳停止）                             │  （每 60s）             │
│         ▼                                          ▼                        │
│  ┌──────────┐                               ┌──────────────┐               │
│  │ Worker-1 │  X 心跳超时 120s                │ 标记 unhealthy │              │
│  │ (DOWN)   │◄──────────────────────────────│              │               │
│  └──────────┘                               └──────────────┘               │
│                                                       │                      │
│                                                       ▼                      │
│                                               ┌──────────────┐              │
│                                               │ 新请求路由到其他 Worker │              │
│                                               └──────────────┘              │
│                                                                              │
│  恢复流程：                                                                   │
│  1. Worker-1 重启                                                            │
│  2. 重新向 Controller 注册                                                    │
│  3. 开始发送心跳                                                              │
│  4. Controller 标记为 healthy                                                 │
│  5. 新请求可以路由到 Worker-1                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 七、部署模式详解

### 7.1 单机 All-in-One 模式

```yaml
# 单容器部署，所有服务合一
services:
  dbgpt:
    image: eosphorosai/dbgpt
    command: dbgpt start webserver
    ports:
      - "5670:5670"
```

**特点**：
- EmbeddedModelRegistry（内存注册表）
- Worker 和 WebServer 同进程
- 适合开发/测试

### 7.2 分离部署模式

```yaml
# Controller + Worker + WebServer 分离
services:
  controller:
    image: eosphorosai/dbgpt
    command: dbgpt start controller
    ports:
      - "8000:8000"

  llm-worker:
    image: eosphorosai/dbgpt
    command: >
      dbgpt start worker
      --model_name qwen-72b
      --model_path /models/qwen-72b
      --controller_addr http://controller:8000
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  embedding-worker:
    image: eosphorosai/dbgpt
    command: >
      dbgpt start worker
      --worker_type text2vec
      --model_name bge-large
      --controller_addr http://controller:8000

  webserver:
    image: eosphorosai/dbgpt
    command: >
      dbgpt start webserver
      --controller_addr http://controller:8000
    ports:
      - "5670:5670"
    depends_on:
      - controller
```

### 7.3 高可用集群模式

```yaml
# 高可用部署：多 Controller + 多 Worker
services:
  controller-1:
    command: dbgpt start controller -c /configs/ha.toml
  
  controller-2:
    command: dbgpt start controller -c /configs/ha.toml
  
  llm-worker-1:
    command: dbgpt start worker --controller_addr http://controller-1:8000
  
  llm-worker-2:
    command: dbgpt start worker --controller_addr http://controller-2:8000

  # Nginx 负载均衡
  nginx:
    image: nginx
    config: |
      upstream controllers {
        server controller-1:8000;
        server controller-2:8000;
      }
```

---

## 八、与 RAGFlow 分布式对比

| 特性 | RAGFlow | DB-GPT |
|------|---------|--------|
| **架构** | 多进程单体 | Controller-Worker 分布式 |
| **通信** | Redis 队列 | HTTP REST API |
| **服务发现** | Redis 共享状态 | Controller 注册中心 |
| **负载均衡** | 队列消费 | Random + 健康检查 |
| **故障恢复** | 进程重启 | 心跳检测 + 自动剔除 |
| **扩展粒度** | Task Executor 进程 | 模型级 Worker |
| **适用规模** | 中小规模 | 大规模多模型 |

---

## 九、总结

### 9.1 核心特点

| 特性 | 实现方式 | 优势 |
|------|----------|------|
| **服务注册发现** | Controller + Registry | 集中管理，状态清晰 |
| **负载均衡** | Random + 健康过滤 | 简单有效，支持扩展 |
| **故障检测** | 心跳 + 超时检测 | 自动剔除故障节点 |
| **通信协议** | HTTP REST | 通用，易调试 |
| **部署灵活** | 单机/分布式均可 | 适应不同规模 |

### 9.2 核心组件关系

```
WebServer/APIServer
    ↓ 查询
Controller (Registry + Health Check)
    ↓ 路由
Worker (Model Inference)
```

### 9.3 一句话总结

> **DB-GPT 采用 Controller-Worker 分布式架构，Controller 作为模型注册中心管理所有 Worker 实例，通过心跳检测实现故障自动剔除，支持随机负载均衡，Worker 可按模型类型独立部署和扩缩容，适用于大规模多模型生产环境。**

---

## 十、关联文档

- [[DB-GPT-模块架构与服务组织分析]]: 模块间连接关系
- [[DB-GPT-部署运维分析]]: 部署最佳实践
- [[DB-GPT-Docker镜像构建机制详解]]: 镜像构建分析
