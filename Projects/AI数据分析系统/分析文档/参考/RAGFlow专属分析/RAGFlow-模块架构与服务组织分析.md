# RAGFlow 模块架构与服务组织深度分析

**分析日期**: 2026-02-05  
**项目版本**: RAGFlow v0.23.1  
**核心结论**: **模块化单体架构（Modular Monolith）**，非微服务，通过多进程+Redis队列实现异步处理

---

## 一、架构总体定位

### 1.1 一句话定义

> **RAGFlow 是模块化单体应用（Modular Monolith），而非微服务架构。核心特点是：同一代码库、多进程部署、Redis队列异步通信、共享数据存储。**

### 1.2 架构对比

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    架构类型对比                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  传统单体 (Monolith)        微服务 (Microservices)      RAGFlow (模块化单体)  │
│  ┌───────────────┐          ┌─┐ ┌─┐ ┌─┐ ┌─┐            ┌─────────────────┐  │
│  │  Web+Biz+Data │          │W│ │B│ │D│ │S│            │   Web Server    │  │
│  │   紧耦合      │          │e│ │i│ │a│ │e│            ├─────────────────┤  │
│  │               │          │b│ │z│ │t│ │a│            │  Task Executor  │  │
│  │  单进程部署   │          │ │ │ │ │a│ │r│            │  (多进程)        │  │
│  └───────────────┘          │ │ │ │ │ │ │c│            ├─────────────────┤  │
│                             │ │ │ │ │ │ │h│            │  Data Sync      │  │
│  缺点：                      │ │ │ │ │ │ │ │            │  (可选)          │  │
│  • 代码膨胀                  └─┘ └─┘ └─┘ └─┘            ├─────────────────┤  │
│  • 无法独立扩展                 ↑ ↑ ↑ ↑                 │  Admin Server   │  │
│  • 技术栈单一                   网络通信                 │  (可选)          │  │
│                                                              ...            │  │
│                                                                             │  │
│  微服务缺点：                   RAGFlow特点：                                │  │
│  • 运维复杂度高                 • 代码模块化清晰                             │  │
│  • 分布式事务                   • 部署灵活（可合可分）                       │  │
│  • 网络延迟                     • 共享数据存储（简化一致性）                 │  │
│  • 服务治理成本高               • Redis轻量级队列通信                        │  │
│                                 • 单机/多机均可部署                          │  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、进程架构设计

### 2.1 核心进程拓扑

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAGFlow 进程架构                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Docker 容器层                                 │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                   ragflow 主容器                             │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │   │
│  │  │  │   Nginx     │  │Web Server   │  │   Task Executor     │  │   │   │
│  │  │  │   (反向代理) │  │(Python)     │  │   (多进程)           │  │   │   │
│  │  │  │             │  │             │  │   ┌───┐ ┌───┐ ┌───┐  │  │   │   │
│  │  │  │  Port: 80   │  │ Port: 9380  │  │   │T1 │ │T2 │ │T3 │  │  │   │   │
│  │  │  └──────┬──────┘  └──────┬──────┘  │   └───┘ └───┘ └───┘  │  │   │   │
│  │  │         └────────────────┘         └─────────────────────┘  │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                              │                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              可选进程（同容器或独立容器）                   │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │   │
│  │  │  │ Admin Server│  │ MCP Server  │  │   Data Sync         │  │   │   │
│  │  │  │ Port: 9381  │  │ Port: 9382  │  │   (数据源同步)       │  │   │   │
│  │  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      依赖服务层（Docker Compose）                    │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │   │
│  │  │  MySQL  │  │  Redis  │  │   ES    │  │  MinIO  │  │Infinity │  │   │
│  │  │ (主存储) │  │ (队列)  │  │(全文检索)│  │(对象存储)│  │(可选)   │  │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 进程职责详解

| 进程 | 入口文件 | 职责 | 部署方式 |
|------|----------|------|----------|
| **Web Server** | `api/ragflow_server.py` | HTTP API服务、WebSocket、业务逻辑 | 主容器必需 |
| **Task Executor** | `rag/svr/task_executor.py` | 文档解析、Embedding、GraphRAG构建 | 多进程并行 |
| **Data Sync** | `rag/svr/sync_data_source.py` | 外部数据源同步（数据库/文件等） | 可选 |
| **Admin Server** | `admin/server/admin_server.py` | 管理后台API | 可选 |
| **MCP Server** | `mcp/server/server.py` | MCP协议服务端 | 可选 |

### 2.3 进程启动脚本分析

```bash
# docker/entrypoint.sh - 进程编排核心

# 1. Web Server 进程
while true; do
    python3 api/ragflow_server.py &
    wait
    sleep 1  # 崩溃后自动重启
done &

# 2. Data Sync 进程
while true; do
    python3 rag/svr/sync_data_source.py &
    wait
    sleep 1
done &

# 3. Task Executor 多进程
for (( i=0; i<WORKERS; i++ ))
do
    task_exe "${i}" "${HOST_ID}" &
done

# task_exe 函数定义
function task_exe() {
    local consumer_id="$1"
    local host_id="$2"
    
    # 使用jemalloc优化内存分配
    LD_PRELOAD="$JEMALLOC_PATH" \
    python3 rag/svr/task_executor.py "${host_id}_${consumer_id}" &
    wait
    sleep 1
}

# 等待所有子进程
wait
```

---

## 三、代码模块架构

### 3.1 模块分层架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RAGFlow 代码模块分层                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  L1: 接入层 (Presentation Layer)                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  api/apps/                                                          │   │
│  │  ├── canvas_app.py      # Agent/工作流 API                          │   │
│  │  ├── conversation_app.py # 对话 API                                │   │
│  │  ├── document_app.py    # 文档管理 API                             │   │
│  │  ├── kb_app.py          # 知识库 API                               │   │
│  │  ├── file_app.py        # 文件管理 API                             │   │
│  │  ├── sdk/               # 对外SDK API                              │   │
│  │  └── ...                                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  L2: 业务服务层 (Service Layer)                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  api/db/services/                                                   │   │
│  │  ├── canvas_service.py      # Agent服务                            │   │
│  │  ├── dialog_service.py      # 对话服务                             │   │
│  │  ├── document_service.py    # 文档服务                             │   │
│  │  ├── knowledgebase_service.py # 知识库服务                         │   │
│  │  ├── llm_service.py         # LLM服务                              │   │
│  │  ├── tenant_llm_service.py  # 租户LLM配置服务                      │   │
│  │  └── ...                                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  L3: 核心业务层 (Core Business Layer)                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐   │   │
│  │     agent/      │  │      rag/       │  │       deepdoc/          │   │   │
│  │  ┌───────────┐  │  │  ┌───────────┐  │  │  ┌─────────────────┐   │   │   │
│  │  │canvas.py  │  │  │  │ nlp/      │  │  │  │ parser/         │   │   │   │
│  │  │Canvas DSL │  │  │  │ search.py │  │  │  │ ├── pdf_parser  │   │   │   │
│  │  │引擎       │  │  │  │ rag_token │  │  │  │ ├── docx_parser │   │   │   │
│  │  │           │  │  │  │ graphrag/ │  │  │  │ ├── excel_parse │   │   │   │
│  │  │components/│  │  │  │ raptor.py │  │  │  │ └── ...         │   │   │   │
│  │  │tools/     │  │  │  │           │  │  │  │                 │   │   │   │
│  │  │sandbox/   │  │  │  │ flow/     │  │  │  │ vision/         │   │   │   │
│  │  │plugin/    │  │  │  │  ├── parser   │  │  │ ├── ocr.py      │   │   │   │
│  │  │           │  │  │  │  ├── splitter │  │  │ ├── table_struc │   │   │   │
│  │  │           │  │  │  │  └── ...      │  │  │ └── layout_rec  │   │   │   │
│  │  └───────────┘  │  │  └───────────┘  │  │  └─────────────────┘   │   │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │   │
│                                    │                                         │
│                                    ▼                                         │
│  L4: 数据访问层 (Data Access Layer)                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  api/db/                                                            │   │
│  │  ├── db_models.py         # 数据模型定义 (Peewee/SQLAlchemy)        │   │
│  │  ├── db_utils.py          # 数据库工具                             │   │
│  │  ├── init_data.py         # 初始化数据                             │   │
│  │  └── services/            # 数据访问服务                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  L5: 基础设施层 (Infrastructure Layer)                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  common/              # 通用工具                                     │   │
│  │  ├── doc_store/       # 文档存储 (ES/Infinity/OceanBase)            │   │
│  │  ├── data_source/     # 数据源连接器                                │   │
│  │  ├── config_utils.py  # 配置管理                                    │   │
│  │  └── ...                                                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 核心模块详解

#### 3.2.1 Agent模块 (`agent/`)

```python
# 核心文件结构
agent/
├── canvas.py              # ★ Canvas DSL引擎 - 工作流执行核心
├── component/             # 工作流组件
│   ├── base.py           # 组件基类
│   ├── begin.py          # 开始节点
│   ├── retrieval.py      # 检索节点
│   ├── generate.py       # 生成节点
│   ├── llm.py            # LLM节点
│   ├── switch.py         # 条件分支
│   ├── loop.py           # 循环节点
│   └── ...               # 30+组件
├── tools/                # 外部工具
│   ├── retrieval.py      # RAG检索工具
│   ├── crawler.py        # 网页抓取
│   ├── email.py          # 邮件发送
│   └── ...               # 20+工具
├── sandbox/              # 代码执行沙箱
│   ├── executor.py       # Python代码执行器
│   └── executor_utils.py # 执行工具
└── plugin/               # 插件系统
    ├── plugin_manager.py # 插件管理
    └── llm_tool_select.py # LLM工具选择
```

#### 3.2.2 RAG模块 (`rag/`)

```python
# 核心文件结构
rag/
├── nlp/
│   ├── search.py         # ★ 检索核心 - BM25+向量混合检索
│   ├── rag_tokenizer.py  # RAG分词器
│   └── query.py          # 查询处理
├── graphrag/             # GraphRAG知识图谱
│   ├── general/          # 完整版GraphRAG
│   │   ├── community_reports.py
│   │   ├── extraction.py
│   │   └── global_search.py
│   └── light/            # 轻量版GraphRAG
├── flow/                 # 文档处理流水线
│   ├── parser/           # 解析器
│   ├── splitter/         # 文本切分
│   └── tokenizer/        # 分词
├── app/                  # 领域特定解析器
│   ├── naive.py          # 通用解析
│   ├── paper.py          # 学术论文
│   ├── resume.py         # 简历
│   ├── laws.py           # 法律文档
│   └── ...               # 12+领域
├── svr/
│   └── task_executor.py  # ★ 任务执行器
├── llm/                  # LLM模型封装
│   ├── chat_model.py     # 对话模型
│   ├── embedding_model.py # 嵌入模型
│   └── rerank_model.py   # 重排序模型
└── raptor.py             # RAPTOR递归摘要
```

#### 3.2.3 DeepDoc模块 (`deepdoc/`)

```python
# 核心文件结构
deepdoc/
├── parser/               # 文档解析器
│   ├── pdf_parser.py     # PDF解析（MinerU/PaddleOCR）
│   ├── docx_parser.py    # Word解析
│   ├── excel_parser.py   # Excel解析
│   ├── ppt_parser.py     # PPT解析
│   ├── html_parser.py    # HTML解析
│   └── resume/           # 简历解析专用
├── vision/               # 视觉理解
│   ├── ocr.py            # OCR识别
│   ├── layout_recog.py   # 版面分析
│   ├── table_structure.py # 表格结构识别
│   └── t_ocr.py          # OCR训练
└── parser/               # 其他格式
    ├── docling/          # Docling集成
    └── mineru/           # MinerU集成
```

---

## 四、模块间通信机制

### 4.1 通信方式总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      模块间通信机制                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. 同步调用（函数/方法调用）                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Web Server → Service → Model                                       │   │
│  │       ↓           ↓        ↓                                        │   │
│  │  API Layer → Business → Data Access                                 │   │
│  │  (同进程内调用，直接函数调用)                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  2. 异步队列（Redis队列）★ 核心通信方式                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Web Server         Redis Queue          Task Executor              │   │
│  │  ┌─────────┐        ┌─────────┐          ┌─────────────┐           │   │
│  │  │ 上传文档 │───────►│  task_  │─────────►│  文档解析    │           │   │
│  │  │         │  LPUSH │ queue   │  BRPOP   │             │           │   │
│  │  │         │───────►│         │─────────►│  向量化      │           │   │
│  │  └─────────┘        └─────────┘          └─────────────┘           │   │
│  │                                                              [独立进程]│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  3. 共享存储（数据库/对象存储）                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Web Server          MySQL/ES          Task Executor                │   │
│  │  ┌─────────┐        ┌─────────┐          ┌─────────────┐           │   │
│  │  │写入任务 │───────►│  task   │          │  读取任务    │           │   │
│  │  │ 状态   │        │  table  │◄─────────│  更新状态    │           │   │
│  │  └─────────┘        └─────────┘          └─────────────┘           │   │
│  │                                                                     │   │
│  │  MinIO对象存储： tenant_id/file_type/date/file_id                   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  4. 进程间信号（Process Signal）                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Entrypoint脚本通过信号管理进程生命周期                              │   │
│  │  SIGINT/SIGTERM → 优雅关闭                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Redis队列通信详解

```python
# rag/utils/redis_conn.py - Redis连接管理

import redis

class RedisDistributedLock:
    """Redis分布式锁 - 用于任务协调"""
    def __init__(self, key, lock_value, timeout=10):
        self.key = f"ragflow:lock:{key}"
        self.lock_value = lock_value
        self.timeout = timeout
        self.redis_conn = REDIS_CONN
    
    def acquire(self):
        # SET key value NX EX timeout
        return self.redis_conn.set(
            self.key, self.lock_value, 
            nx=True, ex=self.timeout
        )
    
    def release(self):
        # Lua脚本保证原子性
        script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        return self.redis_conn.eval(script, 1, self.key, self.lock_value)


# api/db/services/task_service.py - 任务队列

def queue_dataflow(tenant_id: str, flow_id: str, task_id: str, 
                   doc_id: str, file: dict = None, 
                   priority: int = 0, rerun: bool = False):
    """
    将任务加入Redis队列
    
    Args:
        tenant_id: 租户ID
        flow_id: 流水线ID
        task_id: 任务ID
        doc_id: 文档ID
        priority: 优先级（0-10，越大越优先）
        rerun: 是否重跑
    """
    task_msg = {
        "tenant_id": tenant_id,
        "flow_id": flow_id,
        "task_id": task_id,
        "doc_id": doc_id,
        "file": file,
        "priority": priority,
        "rerun": rerun,
        "enqueue_time": time.time()
    }
    
    # 使用Redis List作为队列
    # LPUSH 从左侧加入（头部）
    REDIS_CONN.lpush("ragflow:task_queue", json.dumps(task_msg))
    
    return True, "Task queued"


# rag/svr/task_executor.py - 任务消费者

class TaskExecutor:
    """任务执行器 - 后台进程"""
    
    def run(self):
        """主循环 - 持续消费任务"""
        while True:
            try:
                # BRPOP 阻塞式从右侧弹出（尾部）
                # 支持优先级：多个队列按优先级排序
                result = REDIS_CONN.brpop(
                    ["ragflow:task_queue"], 
                    timeout=5  # 5秒超时
                )
                
                if result:
                    queue_name, task_data = result
                    task = json.loads(task_data)
                    self.process_task(task)
                    
            except Exception as e:
                logging.error(f"Task execution error: {e}")
                time.sleep(1)
    
    def process_task(self, task: dict):
        """处理单个任务"""
        doc_id = task["doc_id"]
        flow_id = task["flow_id"]
        tenant_id = task["tenant_id"]
        
        # 1. 获取文档信息
        doc = DocumentService.get_by_id(doc_id)
        
        # 2. 获取流水线配置
        flow = FlowService.get_by_id(flow_id)
        
        # 3. 执行流水线
        for step in flow.steps:
            # 更新进度到数据库
            TaskService.update_progress(task_id, step.name, "running")
            
            # 执行步骤
            result = self.execute_step(step, doc)
            
            # 保存结果
            TaskService.save_step_result(task_id, step.name, result)
        
        # 4. 更新最终状态
        DocumentService.update_status(doc_id, StatusEnum.VALID)
```

### 4.3 共享数据库通信

```python
# 数据库作为进程间状态共享中心

# Web Server 写入任务
class DocumentApp:
    @login_required
    async def upload(self):
        # 1. 保存文件到MinIO
        file_id = FileService.upload(tenant_id, file_bytes)
        
        # 2. 创建文档记录
        doc = DocumentService.create(
            tenant_id=tenant_id,
            name=filename,
            status=StatusEnum.PENDING  # 待处理状态
        )
        
        # 3. 创建任务
        task = TaskService.create(
            doc_id=doc.id,
            status=TaskStatus.PENDING
        )
        
        # 4. 加入队列
        queue_dataflow(tenant_id, flow_id, task.id, doc.id)
        
        return jsonify({"doc_id": doc.id, "status": "pending"})


# Task Executor 读取并更新
class TaskExecutor:
    def process_task(self, task_msg):
        task_id = task_msg["task_id"]
        doc_id = task_msg["doc_id"]
        
        # 读取任务
        task = TaskService.get_by_id(task_id)
        doc = DocumentService.get_by_id(doc_id)
        
        # 更新为处理中
        DocumentService.update_status(doc_id, StatusEnum.PARSING)
        TaskService.update_status(task_id, TaskStatus.RUNNING)
        
        try:
            # 执行文档解析
            chunks = self.parse_document(doc)
            
            # 更新进度
            DocumentService.update_progress(doc_id, 50)
            
            # 执行向量化
            embeddings = self.generate_embeddings(chunks)
            
            # 保存到ES
            self.save_to_es(doc.tenant_id, chunks, embeddings)
            
            # 更新为完成
            DocumentService.update_status(doc_id, StatusEnum.VALID)
            TaskService.update_status(task_id, TaskStatus.SUCCESS)
            
        except Exception as e:
            # 更新为失败
            DocumentService.update_status(doc_id, StatusEnum.ERROR)
            TaskService.update_status(task_id, TaskStatus.FAILED)
            TaskService.update_error(task_id, str(e))
```

---

## 五、服务部署架构

### 5.1 Docker Compose部署

```yaml
# docker/docker-compose.yml 结构

services:
  # ========== RAGFlow 核心服务 ==========
  ragflow:
    image: infiniflow/ragflow:latest
    ports:
      - "80:80"      # Web UI (Nginx)
      - "9380:9380"  # API Server
      - "9381:9381"  # Admin Server (可选)
      - "9382:9382"  # MCP Server (可选)
    environment:
      - REDIS_HOST=redis
      - MYSQL_HOST=mysql
      - ES_HOST=es01
    volumes:
      - ./ragflow-logs:/ragflow/logs
      - ./nginx:/etc/nginx/conf.d
    depends_on:
      - mysql
      - redis
      - es01

  # ========== 可选：独立Task Executor ==========
  # executor:
  #   image: infiniflow/ragflow:latest
  #   entrypoint: "/ragflow/entrypoint_task_executor.sh"
  #   depends_on:
  #     - mysql
  #     - redis

  # ========== 基础设施服务 ==========
  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=infini_rag_flow
    volumes:
      - mysql_data:/var/lib/mysql

  redis:
    image: redis:alpine
    volumes:
      - redis_data:/data

  es01:
    image: elasticsearch:8.11.3
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    volumes:
      - esdata01:/usr/share/elasticsearch/data

  minio:
    image: minio/minio
    command: server /data
    volumes:
      - minio_data:/data
```

### 5.2 Kubernetes部署

```yaml
# helm/templates/ 结构

# 1. Web Server Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "ragflow.fullname" . }}-server
spec:
  replicas: {{ .Values.server.replicaCount }}
  selector:
    matchLabels:
      app: ragflow-server
  template:
    spec:
      containers:
        - name: ragflow
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["/bin/bash", "-c", "--disable-taskexecutor"]  # 仅Web
          ports:
            - containerPort: 9380
          env:
            - name: REDIS_HOST
              value: "{{ .Values.redis.host }}"
            - name: MYSQL_HOST
              value: "{{ .Values.mysql.host }}"

---

# 2. Task Executor Deployment（独立扩缩容）
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "ragflow.fullname" . }}-executor
spec:
  replicas: {{ .Values.executor.replicaCount }}  # 可独立扩容
  selector:
    matchLabels:
      app: ragflow-executor
  template:
    spec:
      containers:
        - name: executor
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          command: ["/bin/bash", "-c", "--disable-webserver --workers=4"]
          resources:
            limits:
              nvidia.com/gpu: 1  # GPU资源

---

# 3. 依赖服务（StatefulSet）
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ include "ragflow.fullname" . }}-elasticsearch
spec:
  serviceName: elasticsearch
  replicas: 1
  template:
    spec:
      containers:
        - name: elasticsearch
          image: elasticsearch:8.11.3
          volumeClaimTemplates:
            - metadata:
                name: es-data
              spec:
                accessModes: ["ReadWriteOnce"]
                resources:
                  requests:
                    storage: 100Gi
```

### 5.3 扩缩容策略

| 场景 | 扩容对象 | 触发条件 | 实现方式 |
|------|----------|----------|----------|
| API请求增加 | Web Server | CPU>70%或QPS>1000 | K8s HPA |
| 文档处理积压 | Task Executor | 队列深度>100 | 增加executor副本 |
| 检索性能瓶颈 | ES节点 | 查询延迟>500ms | ES集群扩容 |
| 存储不足 | MinIO | 磁盘使用率>80% | 增加存储卷 |

---

## 六、与微服务架构对比

### 6.1 为什么不是微服务？

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RAGFlow 架构决策分析                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  微服务适用场景：                    RAGFlow场景：                           │
│  ┌─────────────────────────┐        ┌─────────────────────────┐             │
│  │ • 团队规模大 (>50人)     │        │ • 开源项目，贡献者分散   │             │
│  │ • 业务模块独立演进       │        │ • 核心模块紧密耦合       │             │
│  │ • 不同技术栈需求         │        │ • 统一Python技术栈       │             │
│  │ • 独立部署需求           │        │ • 统一部署简化运维       │             │
│  │ • 故障隔离要求高         │        │ • 单机/小规模部署为主    │             │
│  └─────────────────────────┘        └─────────────────────────┘             │
│                                                                              │
│  选择模块化单体的原因：                                                      │
│                                                                              │
│  1. 开发效率                                                                 │
│     • 单一代码库，易于贡献和调试                                             │
│     • 函数调用比RPC/消息队列简单                                             │
│     • 类型检查和IDE支持更完整                                                │
│                                                                              │
│  2. 部署简化                                                                 │
│     • docker-compose up 即可启动                                             │
│     • 无需服务发现、配置中心                                                 │
│     • 单容器运行降低使用门槛                                                 │
│                                                                              │
│  3. 性能考虑                                                                 │
│     • 进程内调用比网络调用快10-100倍                                         │
│     • 共享内存减少序列化开销                                                 │
│     • 数据库连接池复用                                                       │
│                                                                              │
│  4. 灵活性                                                                   │
│     • 可合可分：同一镜像支持多种部署模式                                     │
│     • Web+Executor合一（开发/小部署）                                        │
│     • Web/Executor分离（生产大部署）                                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 架构演进路径

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    未来可能的演进方向                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  当前（模块化单体）        中期（进程分离）       远期（可选微服务）          │
│                                                                              │
│  ┌─────────────┐          ┌─────────────┐         ┌─────────────┐          │
│  │  ragflow    │          │   Server    │         │   API GW    │          │
│  │  ┌───────┐  │          │   ┌───────┐ │         │   ┌───────┐ │          │
│  │  │ Web   │  │          │   │ Web   │ │         │   │ Auth  │ │          │
│  │  │ Exec  │  │    →     │   └───────┘ │    →    │   └───────┘ │          │
│  │  │ Sync  │  │          │   ┌───────┐ │         │   ┌───────┐ │          │
│  │  └───────┘  │          │   │Exec xN│ │         │   │Agent  │ │          │
│  │             │          │   └───────┘ │         │   └───────┘ │          │
│  │  同容器/进程 │          │   ┌───────┐ │         │   ┌───────┐ │          │
│  │             │          │   │ Sync  │ │         │   │Parse  │ │          │
│  │             │          │   └───────┘ │         │   └───────┘ │          │
│  └─────────────┘          └─────────────┘         └─────────────┘          │
│                                                                              │
│  适用：小团队/开源        适用：中等规模         适用：大规模SaaS            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 七、总结

### 7.1 核心架构特点

| 特性 | 实现方式 | 说明 |
|------|----------|------|
| **架构模式** | 模块化单体 | 代码模块化，部署灵活 |
| **进程模型** | 多进程协作 | Web/API + Task Executor + Data Sync |
| **通信机制** | Redis队列 | 轻量级异步任务调度 |
| **数据共享** | MySQL + ES + MinIO | 统一存储层 |
| **扩展方式** | 水平扩展Executor | 处理能力提升 |

### 7.2 一句话总结

> **RAGFlow采用模块化单体架构，通过"主进程+多Worker进程+Redis队列"模式实现异步处理，既保持了单体应用的开发和部署简单性，又具备水平扩展能力。适合小到中等规模部署，大型部署可通过K8s分离Web和Executor进程实现扩展。**

### 7.3 适用场景

| 场景 | 推荐部署方式 | 说明 |
|------|-------------|------|
| 个人开发/测试 | 单容器All-in-One | docker-compose up |
| 小团队生产 | 单容器+独立Executor | 分离Web和任务处理 |
| 企业级生产 | K8s + HPA | 自动扩缩容 |
| 大规模SaaS | 服务拆分 | 需二次开发 |
