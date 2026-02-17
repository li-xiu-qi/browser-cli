# AIASys 后端架构分析

来源：AIASys 项目代码分析  
分析日期：2026-02-08  
版本：基于 v0.1.4

---

## 文档说明

本文档对 AIASys 后端进行深度架构分析，涵盖技术栈、模块结构、Agent 系统、Jupyter 集成、数据库设计、API 设计、异步任务和代码质量工具等方面。

---

## 一、后端技术栈总览

### 1.1 核心框架与依赖

| 类别 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| Web 框架 | FastAPI | >=0.128.0 | REST API 与 SSE 流式输出 |
| Agent 框架 | smolagents | >=1.24.0 | LLM Agent 核心实现 |
| LLM 接口 | LiteLLM | >=1.80.11 | 统一多厂商模型调用 |
| 代码执行 | Jupyter Client | >=8.7.0 | Kernel 管理与代码执行 |
| 数据科学 | pandas, numpy, polars | 最新 | 数据处理与分析 |
| 可视化 | matplotlib, seaborn, plotly | 最新 | 图表生成 |
| 机器学习 | scikit-learn, scipy | 最新 | 统计分析 |
| 任务队列 | Celery + Redis | >=5.6.2 | 异步任务处理 |
| 类型验证 | Pydantic | >=2.12.5 | 数据模型与配置 |

### 1.2 Python 版本与包管理

**Python 版本要求**：>= 3.10

**包管理器**：uv

AIASys 采用 uv 作为包管理器，这是新一代极速 Python 包管理工具。uv.lock 文件确保依赖版本锁定，pyproject.toml 定义项目配置。

**开发依赖**：

| 工具 | 用途 |
|------|------|
| black | 代码格式化，行宽 79 字符 |
| isort | 导入语句排序 |
| mypy | 静态类型检查 |
| pylint | 代码质量检查 |

### 1.3 异步架构设计

FastAPI 原生支持异步，AIASys 充分利用这一特性：

**同步执行路径**：本地调试模式，请求直接处理，通过 SSE 流式返回

**异步执行路径**：生产环境，请求提交到 Celery 队列，通过 Redis Pub/Sub 返回 SSE 流

---

## 二、核心模块结构

### 2.1 目录组织

```
app/
├── api/              # API 路由层
│   ├── smol_router.py        # 核心数据分析接口
│   ├── history_router.py     # 会话历史接口
│   ├── tasks_router.py       # 异步任务接口
│   ├── skill_router.py       # 技能管理接口
│   ├── notebook_router.py    # Notebook 回放接口
│   ├── export_router.py      # 文档导出接口
│   ├── auth_router.py        # 认证接口
│   └── file_routers.py       # 文件管理接口
├── agents/           # Agent 工具实现
├── core/             # 核心配置
│   ├── config.py             # Settings 配置类
│   └── logging.py            # 日志设置
├── models/           # 数据模型
│   ├── protocol.py           # 通信协议
│   ├── host_models.py        # Host 相关模型
│   └── task_models.py        # 任务模型
├── services/         # 业务服务
│   ├── file_storage.py       # 文件存储服务
│   └── pandoc_service.py     # 文档导出服务
├── session_manager/  # 会话管理
│   ├── session_manager.py    # 核心管理器
│   ├── history_manager.py    # 历史记录管理
│   └── execution_models.py   # 执行模型
├── smol_agents/      # smolagents 集成
│   ├── agents/               # Agent 实现
│   │   ├── data_analysis_team.py
│   │   ├── compressed_agents.py
│   │   └── compressed_host.py
│   ├── compaction/           # 上下文压缩
│   │   ├── manager.py
│   │   ├── config.py
│   │   └── steps.py
│   ├── executors/            # 代码执行器
│   │   ├── jupyter_executor.py
│   │   └── kernel_manager.py
│   ├── tools/                # 工具集
│   │   ├── workspace_tools.py
│   │   ├── document_tools.py
│   │   └── notebook_tools.py
│   └── utils/                # 工具函数
│       ├── model_factory.py
│       ├── streaming_adapter.py
│       └── telemetry.py
├── skill_manager/    # 技能管理
├── skill_manager/    # 技能管理器
├── tasks/            # Celery 任务
│   ├── celery.py
│   └── analysis.py
└── utils/            # 通用工具
```

![后端模块依赖图](assets/aiasys-后端模块依赖图.svg)

### 2.2 模块职责划分

**API 层**：处理 HTTP 请求、参数校验、认证授权、响应封装

**服务层**：封装业务逻辑，提供文件存储、文档导出等服务

**Agent 层**：实现 Host-Worker 双 Agent 架构，处理对话与代码执行

**执行器层**：管理 Jupyter Kernel，提供代码沙箱执行环境

**会话管理层**：持久化对话历史、管理会话生命周期

---

## 三、Agent 系统实现

### 3.1 Host-Worker 架构

AIASys 采用双 Agent 协作架构：

**Host Agent**：CompressedToolCallingAgent

> 负责与用户对话、理解意图、拆解任务、调度 Worker

特性：
- 使用 ToolCallingAgent 基类
- 支持工具调用和 managed_agents 管理
- 具备上下文自动压缩能力
- 优先处理简单任务，复杂任务委托 Worker

**Worker Agent**：CompressedCodeAgent

> 负责在 Jupyter 环境中编写和执行 Python 代码

特性：
- 使用 CodeAgent 基类
- 专注于数据分析和可视化
- 自动配置中文字体支持
- 具备上下文自动压缩能力

![Agent 调用链图](assets/aiasys-Agent调用链图.svg)

### 3.2 压缩 Agent 设计

**CompressedToolCallingAgent** 和 **CompressedCodeAgent** 继承自 smolagents 的基类，增加了三层压缩机制：

**第一层：Microcompaction 微压缩**

- 截断旧步骤的 observations
- 保留最近 N 步完整内容
- 控制单次观察输出规模

**第二层：Auto-compaction 自动压缩**

- Token 达到阈值时触发
- 生成结构化摘要替换历史步骤
- 支持增量压缩，避免重复计算

**第三层：Manual compact 手动压缩**

- API 端点手动触发
- 可指定聚焦点，控制摘要重点
- 支持强制完全重新压缩

**压缩配置参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| max_context_tokens | 128000 | 模型最大上下文窗口 |
| output_reserve_tokens | 32000 | 预留输出空间 |
| auto_compact_threshold | 78% | 自动压缩触发比例 |
| microcompact_full_steps | 3 | 保留完整内容的步数 |
| tool_results_budget_tokens | 40000 | 工具输出预算 |

### 3.3 Agent 间通信机制

**任务委托流程**：

1. Host 通过 managed_agents 列表访问 Worker
2. Host 调用 Worker 的 run 方法，传入任务描述
3. Worker 在独立线程中执行，通过 Queue 向 Host 透传事件
4. Host 将 Worker 的事件合并到自己的输出流
5. 最终由 Host 整合结果，通过 final_answer 返回

**流式输出实现**：

```python
# DataAnalysisTeam.stream 方法核心逻辑
def stream(self, task: str) -> Generator:
    event_queue = queue.Queue()
    self._current_event_queue = event_queue
    
    # Worker 回调将事件放入队列
    def worker_callback(step):
        event_queue.put((self.worker.name, step))
    
    # Host 在独立线程运行
    def run_host_thread():
        for step in self.host.run(task, stream=True):
            event_queue.put((self.host.name, step))
        event_queue.put(None)  # 结束信号
    
    thread = threading.Thread(target=run_host_thread)
    thread.start()
    
    # 主线程消费队列，yield 给调用方
    while True:
        event = event_queue.get(timeout=300)
        if event is None:
            break
        yield event
```

---

## 四、smolagents 集成

### 4.1 模型工厂

**ModelFactory** 封装 LiteLLM 模型创建：

```python
def create_model(model_id: str = None):
    model_id = model_id or settings.llm_model
    provider = settings.llm_provider
    
    # 自动拼接 provider/model_id 格式
    if "/" not in model_id and provider:
        model_id = f"{provider}/{model_id}"
    
    return LiteLLMModel(
        model_id=model_id,
        api_key=settings.llm_provider_api_key,
        api_base=settings.llm_provider_base_url,
        temperature=0.2,
    )
```

### 4.2 Agent 类型选择

**ToolCallingAgent vs CodeAgent 的选择逻辑**：

| 维度 | Host 使用 ToolCallingAgent | Worker 使用 CodeAgent |
|------|---------------------------|----------------------|
| 主要职责 | 对话理解、任务协调 | 代码编写、数据分析 |
| 核心能力 | 工具调用、Agent 管理 | Python 代码生成与执行 |
| 输出形式 | 文本回复 + 工具调用 | 代码块 + 执行结果 |
| 思考方式 | 规划任务、选择工具 | 编写代码、处理数据 |

### 4.3 记忆管理策略

**Memory 结构**：

- smolagents 原生 MemoryStep 列表
- 支持 ActionStep、FinalAnswerStep、TaskStep 等类型
- 自定义 SummaryStep 和 ContinuationStep 用于压缩

**持久化机制**：

- SessionManager 保存到 JSON 文件
- 存储路径：storage/sessions/{user_id}/{session_id}/
- 包含 metadata.json 和 chat_history.json

**记忆加载流程**：

1. DataAnalysisTeam 初始化时调用 _load_memory
2. SessionManager.load_smol_steps 读取历史
3. 过滤兼容的步骤类型
4. 恢复到 Host.memory.steps
5. CompactionManager 从 SummaryStep 恢复压缩状态

### 4.4 规划机制配置

当前实现采用简单的 Host-Worker 两层架构，未启用复杂的 PlanningAgent。

**Host 的规划能力通过 Prompt 实现**：

- 系统 Prompt 中定义任务拆解指导
- Host 自主决定何时委托 Worker
- 避免过度拆分，确保任务高效完成

---

## 五、Jupyter 集成

### 5.1 Jupyter Kernel 管理

**MultiKernelInterpreterManager**：

- 基于 jupyter_client.MultiKernelManager
- 每个 session_id 对应独立 Kernel
- 支持创建、获取、关闭、列出内核

**Kernel 生命周期**：

```
创建流程：
1. MultiKernelManager.start_kernel() 启动新内核
2. 获取 kernel 实例和 client
3. 创建 JupyterKernelInterpreter 包装器
4. 以 session_id 为 key 存储到 interpreters 字典

关闭流程：
1. 从字典中移除 interpreter
2. 调用 kernel_manager.shutdown_kernel(kernel_id)
```

### 5.2 代码执行沙箱

**JupyterExecutorAdapter**：

- 实现 smolagents.PythonExecutor 接口
- 将代码发送到 Jupyter Kernel 执行
- 捕获输出、错误、图片等资源

**安全配置**：

```python
# 允许的导入模块白名单
authorized_imports = [
    "pandas", "numpy", "matplotlib", "seaborn",
    "polars", "scipy", "sklearn", "statsmodels",
    "plotly", "openpyxl", "PIL", "requests",
    "random", "json", "datetime", ...
]
```

**代码执行流程**：

1. 验证代码安全性
2. 记录导入语句到执行状态
3. 通过 client.execute 发送代码
4. 轮询 iopub 通道获取输出
5. 处理 stream、execute_result、display_data、error 等消息类型
6. 图片自动保存到会话目录，返回 URL 引用

### 5.3 Notebook 回放机制

**执行历史记录**：

- 每次代码执行记录到 execution_state
- 包含代码、输出、原始消息、错误信息

**导出 Notebook**：

```python
def export_notebook(self) -> str:
    """导出为 .ipynb 格式字符串"""
    cells = []
    for record in execution_history:
        # 代码单元
        cells.append({
            "cell_type": "code",
            "source": record["code"],
            "outputs": record["raw_outputs"],
            ...
        })
    return json.dumps({"cells": cells, ...})
```

**重运行机制**：

- replay_notebook 工具允许 Agent 重运行历史 Notebook
- 恢复之前的变量状态和数据环境
- 支持部分重运行，提高效率

---

## 六、数据存储设计

### 6.1 存储架构

**文件系统存储方案**：

```
storage/
├── sessions/                    # 会话数据
│   └── {user_id}/
│       └── {session_id}/
│           ├── metadata.json         # 会话元数据
│           ├── chat_history.json     # 对话历史
│           └── workspace/            # 工作空间
│               ├── input/            # 用户上传文件
│               ├── outputs/          # 分析产出
│               └── .smolagents_cache/# 压缩卸载目录
├── users/                       # 用户数据
│   └── users.json
└── jupyter_runtime/            # Jupyter 运行时
    └── kernel-*.json
```

**日志目录**：

```
logs/
├── backend.json                # 主应用日志
├── debug/                      # 调试日志
└── traces/                     # Agent 轨迹
    └── {session_id}/
        ├── Host_*.md
        ├── Worker_*.md
        └── *_steps.json
```

### 6.2 数据模型

**SessionMetadata**：

```python
class SessionMetadata(BaseModel):
    session_id: str           # 会话唯一标识
    title: str               # 会话标题
    created_at: str          # 创建时间
    updated_at: str          # 更新时间
    mode: str                # 会话模式
    message_count: int       # 消息数量
    workspace_file_count: int # 工作区文件数
```

**StructuredMessage**：

```python
class StructuredMessage(BaseModel):
    id: str                  # 消息 ID
    role: str                # user/assistant
    content: str             # 消息内容
    agent_id: Optional[str]  # Agent 标识
    steps: List[ExecutionStep]  # 执行步骤
    status: StepStatus       # 完成状态
    timestamp: str           # 时间戳
```

**ExecutionStep**：

```python
class ExecutionStep(BaseModel):
    step_id: str             # 步骤 ID
    message_id: str          # 关联消息 ID
    type: StepType           # 步骤类型
    agent_name: str          # Agent 名称
    agent_role: str          # host/worker
    content: Optional[str]   # 内容
    tool_name: Optional[str] # 工具名
    code: Optional[str]      # 代码
    input_args: Optional[dict]  # 输入参数
    output: Optional[str]    # 输出结果
    model_output: Optional[str]  # 模型输出
    status: StepStatus       # 状态
    artifacts: List[Artifact]    # 产出物
```

### 6.3 会话管理

**SessionManager 核心方法**：

| 方法 | 功能 |
|------|------|
| create_session | 创建新会话 |
| get_session | 获取会话元数据 |
| list_sessions | 列出用户会话 |
| delete_session | 删除会话 |
| add_message | 添加消息 |
| get_messages | 获取消息列表 |
| save_smol_steps | 保存 Agent 步骤 |
| load_smol_steps | 加载 Agent 步骤 |
| get_workspace_dir | 获取工作目录 |

**安全加固**：

- user_id 格式校验，只允许字母数字下划线
- 路径解析后检查，防止目录遍历攻击
- 强制使用 resolve 获取绝对路径

---

## 七、API 设计

### 7.1 路由结构

![API 架构图](assets/aiasys-API架构图.svg)

**核心路由清单**：

| 路由前缀 | 模块 | 说明 |
|----------|------|------|
| /api/smol | smol_router | 数据分析核心 |
| /api/files | file_router | 文件管理 |
| /api/history | history_router | 历史记录 |
| /api/tasks | tasks_router | 异步任务 |
| /api/skills | skill_router | 技能管理 |
| /api/notebook | notebook_router | Notebook 操作 |
| /api/export | export_router | 文档导出 |
| /api/auth | auth_router | 用户认证 |
| /api/health | main.py | 健康检查 |

### 7.2 RESTful API 规范

**标准响应格式**：

```python
# 成功响应
{
    "success": True,
    "data": {...},
    "message": "操作成功"
}

# 错误响应
{
    "detail": "错误描述"
}
```

**资源操作规范**：

| 操作 | HTTP 方法 | URL 模式 | 说明 |
|------|-----------|----------|------|
| 列表查询 | GET | /resources | 获取资源列表 |
| 详情查询 | GET | /resources/{id} | 获取单个资源 |
| 创建 | POST | /resources | 创建资源 |
| 更新 | PUT/PATCH | /resources/{id} | 更新资源 |
| 删除 | DELETE | /resources/{id} | 删除资源 |

### 7.3 SSE 流式输出

**核心端点**：POST /api/smol/data_analysis/stream

**SSE 事件类型**：

| 事件类型 | 说明 |
|----------|------|
| message | 普通消息/思考过程 |
| tool_call | 工具调用信息 |
| code_execution | 代码执行 |
| final_answer | 最终结果 |
| error | 错误信息 |

**流式输出实现**：

```python
async def redis_stream_generator(target_run_id: str):
    r = get_redis_client()
    pubsub = r.pubsub()
    channel = f"analysis_stream:{target_run_id}"
    pubsub.subscribe(channel)
    
    while True:
        message = pubsub.get_message(
            ignore_subscribe_messages=True, 
            timeout=1.0
        )
        if message:
            data = message["data"]
            if data == "STOP_STREAM":
                break
            yield data

return StreamingResponse(
    redis_stream_generator(run_id),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    },
)
```

### 7.4 认证授权

**JWT Token 认证**：

```python
def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    if not settings.auth_enabled:
        return settings.default_user_id
    
    payload = jwt.decode(
        token, 
        settings.auth_jwt_secret, 
        algorithms=["HS256"]
    )
    return payload.get("sub")
```

**依赖注入**：

- 受保护路由使用 Depends(get_current_user)
- 自动注入当前用户标识到处理函数
- 支持禁用认证的开发模式

---

## 八、Celery + Redis 异步任务

### 8.1 架构设计

**两种执行模式**：

| 模式 | 配置 | 适用场景 |
|------|------|----------|
| 同步模式 | enable_redis_queue = False | 开发调试 |
| 异步模式 | enable_redis_queue = True | 生产环境 |

**同步模式**：

- 使用 Eager 模式，任务立即执行
- 不依赖 Redis，便于本地开发
- 直接返回 StreamingResponse

**异步模式**：

- 任务提交到 Celery 队列
- Worker 进程异步执行
- 通过 Redis Pub/Sub 流式返回结果

### 8.2 任务队列配置

**Celery 配置**：

```python
def create_celery_app():
    if settings.enable_redis_queue:
        c_app = Celery(
            "agent_backend",
            broker=settings.celery_broker_url,
            backend=settings.celery_result_backend,
            include=["app.tasks.analysis"],
        )
    else:
        # Eager 模式
        c_app = Celery("agent_backend")
        c_app.conf.update(
            task_always_eager=True,
            task_eager_propagates=True,
        )
    return c_app
```

**Redis 配置**：

```python
@property
def celery_broker_url(self) -> str:
    if self.redis_password:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
    return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
```

### 8.3 任务分发机制

**任务提交流程**：

1. smol_router 接收请求
2. 检查 enable_redis_queue 配置
3. 异步模式：调用 run_analysis_task.delay() 提交任务
4. 创建 Redis Pub/Sub 订阅
5. 返回 SSE 流，从 Redis 读取事件

**任务执行流程**：

1. Celery Worker 接收任务
2. 创建 DataAnalysisTeam 实例
3. 执行数据分析
4. 通过 Redis 发布流式事件
5. 发送 STOP_STREAM 信号结束

### 8.4 任务管理 API

| 端点 | 方法 | 功能 |
|------|------|------|
| /api/tasks/submit | POST | 提交任务 |
| /api/tasks/status/{task_id} | GET | 查询任务状态 |

**任务状态**：PENDING、STARTED、SUCCESS、FAILURE、RETRY、REVOKED

---

## 九、代码质量工具

### 9.1 Black 代码格式化

**配置**：

```toml
[tool.black]
line-length = 79
```

**使用**：

```bash
uv run black app/
```

特性：
- 统一代码风格
- 行宽限制 79 字符
- 自动处理换行和缩进

### 9.2 isort 导入排序

**配置**：

```toml
[tool.isort]
profile = "black"
line_length = 79
```

**使用**：

```bash
uv run isort app/
```

特性：
- 按标准库、第三方库、本地库分组
- 与 Black 兼容的配置
- 自动排序导入语句

### 9.3 mypy 类型检查

**配置**：

```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
show_error_codes = true
```

**使用**：

```bash
uv run mypy app/
```

特性：
- 渐进式类型检查
- 发现潜在类型错误
- 提升代码可维护性

### 9.4 pylint Linter

**配置**：

```toml
[tool.flake8]
max-line-length = 79
extend-ignore = ["E203", "W503"]
```

**使用**：

```bash
uv run pylint app/
```

特性：
- 代码风格检查
- 潜在问题检测
- 代码复杂度分析

---

## 十、关键设计决策

### 10.1 为何选择 smolagents

| 优势 | 说明 |
|------|------|
| 轻量级 | 代码简洁，易于理解和定制 |
| 模块化 | Agent、Tool、Memory 分离清晰 |
| 流式支持 | 原生支持流式输出 |
| LiteLLM 集成 | 统一接口调用多厂商模型 |
| 可扩展 | 易于继承和扩展基类 |

### 10.2 上下文压缩的必要性

**问题**：长对话导致上下文窗口溢出，成本增加，响应变慢

**解决方案**：

1. 微压缩控制单次输出规模
2. 自动压缩在阈值触发时摘要历史
3. 增量压缩避免重复处理
4. 磁盘卸载保存大工具结果

**效果**：将数万 token 的历史压缩为数千 token 的摘要

### 10.3 Jupyter Kernel vs Docker Sandbox

**开发环境**：本地 Kernel，便于调试

**生产环境**：Docker Sandbox，增强隔离性

配置项 executor_backend 控制执行后端选择

### 10.4 文件系统存储 vs 数据库存储

**选择文件系统的原因**：

- 会话数据天然适合文件组织
- Notebook、图片等二进制文件易于存储
- 简化部署，无需数据库依赖
- 便于调试和查看原始数据

---

## 附录

### A. 核心文件索引

| 文件 | 职责 |
|------|------|
| app/main.py | FastAPI 应用入口 |
| app/core/config.py | 全局配置 |
| app/api/smol_router.py | 核心 API 路由 |
| app/smol_agents/agents/data_analysis_team.py | Host-Worker 团队 |
| app/smol_agents/compaction/manager.py | 压缩管理器 |
| app/smol_agents/executors/jupyter_executor.py | Jupyter 适配器 |
| app/session_manager/session_manager.py | 会话管理 |
| app/tasks/celery.py | Celery 配置 |

### B. 相关文档

- [[03-AIASys-Agent系统分析]]
- [[04-AIASys-前端架构分析]]
- [[05-AIASys-部署与运维]]

### C. 参考资源

- smolagents 官方文档：https://github.com/huggingface/smolagents
- FastAPI 文档：https://fastapi.tiangolo.com
- Jupyter Client 文档：https://jupyter-client.readthedocs.io

---

标签：AIASys 后端架构 FastAPI smolagents 系统设计
