# RAGFlow 模块架构详解

**版本**: RAGFlow v0.23.1  
**核心问题**: 代码模块如何组织？是微服务还是单体？调用关系怎样？

---

## 一、一句话结论

> **RAGFlow 是「模块化单体架构」**：
> - 代码层面：按功能分模块（api/rag/agent/deepdoc），通过 Python import 调用
> - 运行时：多个 Python 进程跑在同一容器里，通过 Redis 队列做异步任务分发
> - 不是微服务：没有独立的 Service 进程，没有 RPC/HTTP 服务间调用

---

## 二、代码模块组织

### 2.1 目录结构 = 模块划分

```
ragflow/                    # 项目根目录
│
├── api/                    # 【API层】对外接口
│   ├── apps/               #   Flask/Quart Blueprint路由
│   │   ├── canvas_app.py   #   Agent/工作流API
│   │   ├── conversation_app.py  # 对话API
│   │   ├── document_app.py #   文档API
│   │   └── sdk/            #   对外SDK接口
│   ├── db/                 #   数据层
│   │   ├── db_models.py    #   数据模型定义
│   │   └── services/       #   业务服务类
│   └── utils/              #   工具函数
│
├── rag/                    # 【RAG核心】检索引擎
│   ├── nlp/                #   NLP处理
│   │   ├── search.py       #   ★ 检索核心（BM25+向量混合）
│   │   └── rag_tokenizer.py#   分词器
│   ├── graphrag/           #   GraphRAG知识图谱
│   ├── flow/               #   文档处理流水线
│   │   ├── parser/         #     解析器
│   │   └── splitter/       #     文本切分
│   ├── svr/                #   服务端进程
│   │   └── task_executor.py#   ★ 任务执行器（独立进程）
│   └── llm/                #   LLM模型封装
│
├── agent/                  # 【Agent引擎】工作流编排
│   ├── canvas.py           #   ★ Canvas DSL引擎
│   ├── component/          #   工作流组件
│   │   ├── base.py
│   │   ├── retrieval.py
│   │   └── llm.py
│   └── tools/              #   外部工具
│
├── deepdoc/                # 【文档解析】DeepDoc
│   ├── parser/             #   文档解析器
│   │   ├── pdf_parser.py
│   │   └── docx_parser.py
│   └── vision/             #   视觉/OCR
│       └── ocr.py
│
├── common/                 # 【公共】工具库
│   ├── doc_store/          #   ES/Infinity存储适配
│   └── data_source/        #   数据源连接器
│
└── web/                    # 【前端】React应用
    └── src/
```

### 2.2 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        模块依赖关系图                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   上层模块              调用关系              下层模块                        │
│   ──────────           ──────────            ──────────                      │
│                                                                              │
│   ┌─────────┐         import                ┌─────────┐                     │
│   │api/apps/│  ──────────────────────────►  │api/db/  │                     │
│   │(API层)  │                               │(数据层) │                     │
│   └────┬────┘                               └─────────┘                     │
│        │                                                                     │
│        │ import                               ┌─────────┐                     │
│        └──────────────────────────────────►   │ agent/  │                     │
│        │                                      │(Agent)  │                     │
│        │                                      └────┬────┘                     │
│        │                                           │                         │
│        │ import         ┌─────────┐               │ import                    │
│        └────────────────►│  rag/   │◄──────────────┘                         │
│                          │ (RAG)   │                                        │
│                          └────┬────┘                                        │
│                               │                                             │
│                               │ import       ┌─────────┐                    │
│                               └─────────────►│deepdoc/ │                    │
│                                              │(解析)   │                    │
│                                              └─────────┘                    │
│                                                                              │
│   所有模块都可能 import common/                                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**依赖规则**：
- 上层可以 import 下层
- 同层之间尽量不互相 import
- `common/` 是基础，所有模块都可以 import

---

## 三、运行时架构（重点）

### 3.1 进程拓扑

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RAGFlow 运行时进程架构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Docker 容器（ragflow）                          │   │
│  │                                                                      │   │
│  │  ┌─────────────┐     ┌─────────────┐     ┌─────────────────────┐   │   │
│  │  │   nginx     │────►│ Web Server  │────►│  Python 代码模块    │   │   │
│  │  │   :80       │     │  :9380      │     │                     │   │   │
│  │  │             │     │ (Flask/Quart)│    │  • api/apps/*       │   │   │
│  │  │ 反向代理    │     │             │     │  • api/db/*         │   │   │
│  │  └─────────────┘     └─────────────┘     │  • agent/*          │   │   │
│  │                                          │  • rag/*            │   │   │
│  │                                          │  • deepdoc/*        │   │   │
│  │                                          └─────────────────────┘   │   │
│  │                                                    │                 │   │
│  │                                          函数调用   │                 │   │
│  │                                          (import)  │                 │   │
│  │                                                    ▼                 │   │
│  │                                          ┌─────────────────────┐   │   │
│  │                                          │     MySQL/ES        │   │   │
│  │                                          └─────────────────────┘   │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐│   │
│  │  │                    Task Executor（独立进程）                    ││   │
│  │  │                                                                 ││   │
│  │  │   进程1: python rag/svr/task_executor.py host_0               ││   │
│  │  │   进程2: python rag/svr/task_executor.py host_1               ││   │
│  │  │   进程3: python rag/svr/task_executor.py host_2               ││   │
│  │  │                                                                 ││   │
│  │  │   这些进程做什么：                                               ││   │
│  │  │   • 文档解析（调用 deepdoc/）                                    ││   │
│  │  │   • 生成 Embedding（调用 rag/nlp/）                              ││   │
│  │  │   • GraphRAG构建（调用 rag/graphrag/）                           ││   │
│  │  │                                                                 ││   │
│  │  │   它们怎么知道要做什么？                                          ││   │
│  │  │   Redis 队列 ◄── 任务消息                                         ││   │
│  │  │                                                                 ││   │
│  │  └────────────────────────────────────────────────────────────────┘│   │
│  │                                                                      │   │
│  │  ┌────────────────────────────────────────────────────────────────┐│   │
│  │  │                    Data Sync（可选进程）                        ││   │
│  │  │   python rag/svr/sync_data_source.py                          ││   │
│  │  │   定时同步外部数据源（Confluence/Notion/S3等）                   ││   │
│  │  └────────────────────────────────────────────────────────────────┘│   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│         ┌──────────────────────────┼──────────────────────────┐              │
│         ▼                          ▼                          ▼              │
│    ┌─────────┐               ┌─────────┐               ┌─────────┐          │
│    │  MySQL  │               │  Redis  │               │   ES    │          │
│    │ (主存储)│               │ (任务队列)│              │ (检索)  │          │
│    └─────────┘               └─────────┘               └─────────┘          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 关键问题解答

| 问题 | 答案 |
|------|------|
| **是微服务吗？** |  不是。没有独立部署的服务单元，所有代码在同一进程空间（除Task Executor外） |
| **Task Executor是微服务吗？** |  不是。它是 Worker 进程，不是独立服务，无API接口 |
| **模块间怎么通信？** | 两种：<br>1. **同步**：Python 函数调用（`import` + 函数调用）<br>2. **异步**：Redis 队列（生产者→Redis→消费者） |
| **为什么这样设计？** | 简单高效：函数调用比RPC快10-100倍，适合RAG这种计算密集型场景 |

---

## 四、调用链路详解

### 4.1 同步调用链路（API请求）

```python
# 场景：用户发起对话请求

┌──────────┐      HTTP        ┌──────────────┐      函数调用      ┌──────────────┐
│  用户    │ ───────────────► │ conversation │ ────────────────► │ DialogService│
│ 浏览器   │   POST /api/chat │   _app.py     │    (import)       │   (api/db/)   │
└──────────┘                  └──────────────┘                   └──────┬───────┘
                                                                         │
                                                                         │ 函数调用
                                                                         ▼
                                                                  ┌──────────────┐
                                                                  │   rag/nlp/   │
                                                                  │  search.py   │
                                                                  │  (检索核心)   │
                                                                  └──────────────┘

详细调用链：

conversation_app.py
    │
    ├──► DialogService.query()              [api/db/services/dialog_service.py]
    │       │
    │       ├──► KnowledgebaseService.get() [查知识库]
    │       │
    │       ├──► search.deal_search()       [rag/nlp/search.py - 混合检索]
    │       │       │
    │       │       ├──► 向量检索 (ES/Infinity)
    │       │       └──► 全文检索 (BM25)
    │       │
    │       └──► LLMBundle.chat()           [调LLM生成回答]
    │
    └──► 返回JSON给用户
```

### 4.2 异步调用链路（文档上传）

```python
# 场景：用户上传PDF文档

┌──────────┐     HTTP Upload    ┌──────────────┐     写DB+Redis    ┌──────────┐
│  用户    │ ─────────────────► │ document_app │ ────────────────► │  MySQL   │
│         │                    │   _app.py     │   创建任务记录    │          │
└──────────┘                    └──────────────┘                   └──────────┘
                                        │
                                        │ LPUSH 任务消息
                                        ▼
                                ┌──────────────┐
                                │  Redis Queue │
                                │ rag:task_q   │
                                └──────┬───────┘
                                       │
                              BRPOP    │     多进程消费
                              ┌────────┴────────┐
                              ▼                 ▼
                    ┌─────────────────┐   ┌─────────────────┐
                    │ Task Executor 0 │   │ Task Executor 1 │
                    │  (独立Python进程)│   │  (独立Python进程)│
                    └────────┬────────┘   └────────┬────────┘
                             │                     │
                             └─────────┬───────────┘
                                       ▼
                            ┌──────────────────────┐
                            │   task_executor.py   │
                            │                      │
                            │  1. 从Redis取任务    │
                            │  2. 调用PDF解析      │ ──► deepdoc/parser/pdf_parser.py
                            │  3. 调用文本切分     │ ──► rag/flow/splitter/
                            │  4. 调用向量化       │ ──► rag/llm/embedding_model.py
                            │  5. 写入ES          │
                            │  6. 更新任务状态    │ ──► MySQL
                            └──────────────────────┘
```

### 4.3 代码示例：从API到数据库

```python
# 1. API入口层
# api/apps/document_app.py

from api.db.services.document_service import DocumentService

@document_blueprint.route('/', methods=['POST'])
@login_required
async def upload():
    file = request.files['file']
    
    # 调用Service层
    doc = await DocumentService.create_document(
        tenant_id=current_user.id,
        filename=file.filename,
        file_bytes=file.read()
    )
    
    return jsonify({"doc_id": doc.id})


# 2. Service业务层
# api/db/services/document_service.py

from deepdoc.parser.pdf_parser import RAGFlowPdfParser
from rag.nlp import search

class DocumentService:
    @classmethod
    async def create_document(cls, tenant_id, filename, file_bytes):
        # 保存文件到MinIO
        file_path = save_to_minio(file_bytes)
        
        # 创建数据库记录
        doc = Document.create(
            id=get_uuid(),
            tenant_id=tenant_id,
            name=filename,
            location=file_path,
            status=StatusEnum.PENDING  # 待处理状态
        )
        
        # 创建任务（写入Redis队列）
        queue_task(
            tenant_id=tenant_id,
            doc_id=doc.id,
            task_type="parse"
        )
        
        return doc
    
    @classmethod
    def parse_document(cls, doc_id):
        # 被 Task Executor 调用
        doc = Document.get_by_id(doc_id)
        
        # 调用DeepDoc解析
        parser = RAGFlowPdfParser()
        chunks = parser.parse(doc.location)
        
        # 调用RAG模块生成向量
        embeddings = generate_embeddings(chunks)
        
        # 写入ES
        search.index_document(doc.tenant_id, chunks, embeddings)


# 3. 底层模块
# deepdoc/parser/pdf_parser.py

class RAGFlowPdfParser:
    def parse(self, file_path):
        # PDF解析逻辑
        # 布局分析 + OCR + 表格识别
        ...
        return chunks
```

---

## 五、架构类型判定

### 5.1 不是微服务的证据

| 微服务特征 | RAGFlow | 结论 |
|-----------|---------|------|
| 独立部署单元 |  所有代码在同一容器 | 不是微服务 |
| 服务间HTTP/RPC通信 |  只有函数调用和Redis | 不是微服务 |
| 独立数据库 |  共享MySQL+ES | 不是微服务 |
| 服务注册发现 |  无 | 不是微服务 |
| 独立团队维护 |  单一开源项目 | 不是微服务 |

### 5.2 是模块化单体的证据

| 特征 | RAGFlow | 结论 |
|------|---------|------|
| 单一可执行程序 |  同一Python解释器（除Task Executor） | 单体 |
| 代码按模块组织 |  api/rag/agent/deepdoc 目录分离 | 模块化 |
| 模块间明确接口 |  Service层定义清晰接口 | 模块化 |
| 可独立扩展Worker |  Task Executor可多进程 | 可扩展 |

### 5.3 准确描述

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAGFlow 架构类型                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   类型：模块化单体（Modular Monolith）                           │
│                                                                  │
│   特点：                                                         │
│   • 代码分模块（api/rag/agent/deepdoc）                          │
│   • 运行时是单体（同一代码库，同一进程）                          │
│   • 异步任务多进程（Task Executor Worker）                       │
│   • 共享数据存储（MySQL+ES）                                      │
│                                                                  │
│   与微服务的区别：                                               │
│   ┌────────────────────┬────────────────────┐                   │
│   │      微服务        │    RAGFlow         │                   │
│   ├────────────────────┼────────────────────┤                   │
│   │ 服务A ──HTTP──► 服务B │ 模块A ──import──► 模块B │              │
│   │ 独立数据库         │ 共享数据库         │                   │
│   │ 独立部署           │ 统一部署           │                   │
│   │ 服务间网络通信     │ 进程内函数调用     │                   │
│   └────────────────────┴────────────────────┘                   │
│                                                                  │
│   为什么这样设计？                                               │
│   • RAG是计算密集型，函数调用比RPC快10-100倍                     │
│   • 避免微服务的数据一致性复杂性                                  │
│   • 开源项目，简化部署门槛                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 六、扩展架构（可选进程）

### 6.1 独立部署场景

```
小部署（开发/测试）                    大部署（生产）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
┌─────────────┐                      ┌─────────────┐
│   ragflow   │                      │  Web Server │
│   单容器    │                      │  (多副本)   │
│             │                      └──────┬──────┘
│ ┌─────────┐ │                             │
│ │ Web     │ │                      ┌──────┴──────┐
│ │ Task    │ │                      │   Redis     │
│ │ Sync    │ │                      │   队列      │
│ └─────────┘ │                      └──────┬──────┘
└─────────────┘                             │
                                      ┌─────┴─────┐
                                      │  Task     │
                                      │ Executor  │
                                      │  (多副本) │
                                      └───────────┘

入口脚本通过参数控制启动哪些进程：
• --disable-taskexecutor → 只启动Web
• --disable-webserver → 只启动Task Executor
```

### 6.2 代码入口

```python
# docker/entrypoint.sh 控制启动哪些进程

# 默认全部启动
ENABLE_WEBSERVER=1
ENABLE_TASKEXECUTOR=1
ENABLE_DATASYNC=1

# 解析参数
if [[ "$1" == "--disable-taskexecutor" ]]; then
    ENABLE_TASKEXECUTOR=0
fi

# 启动Web（Flask/Quart）
if [[ "${ENABLE_WEBSERVER}" -eq 1 ]]; then
    python api/ragflow_server.py &
fi

# 启动Task Executor（多进程）
if [[ "${ENABLE_TASKEXECUTOR}" -eq 1 ]]; then
    for i in {1..4}; do
        python rag/svr/task_executor.py "worker_$i" &
    done
fi
```

---

## 七、总结

### 7.1 架构全景图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RAGFlow 架构全景                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   前端 (React)                                                               │
│      │                                                                       │
│      │ HTTP                                                                   │
│      ▼                                                                       │
│   Nginx ──► Flask/Quart (api/apps/)                                         │
│                  │                                                           │
│      ┌───────────┼───────────┬───────────┐                                   │
│      │ import    │ import    │ import    │                                   │
│      ▼           ▼           ▼           ▼                                   │
│   api/db/     agent/        rag/       deepdoc/                              │
│   (Service)   (Canvas)     (Search)    (Parser)                              │
│                  │           │                                               │
│      ┌───────────┴───────────┘                                               │
│      │ Redis LPUSH (异步任务)                                                  │
│      ▼                                                                        │
│   rag/svr/task_executor.py                                                   │
│   (独立Python进程，多实例)                                                    │
│                                                                              │
│   所有模块共享：MySQL + ES + MinIO                                            │
│                                                                              │
│   架构类型：模块化单体（Modular Monolith）                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 关键结论

| 问题 | 答案 |
|------|------|
| 是微服务吗？ | **不是**。没有服务拆分，没有RPC调用 |
| 模块怎么组合？ | **Python import + Redis队列**。同步用函数调用，异步用队列 |
| 能独立部署吗？ | **能**。通过启动参数可以只跑Web或只跑Task Executor |
| 怎么扩展？ | **水平扩展Task Executor进程**，或部署多个Web实例 |

### 7.3 与其他架构对比

| 项目 | 架构类型 | 模块通信 |
|------|----------|----------|
| **RAGFlow** | 模块化单体 | Python import + Redis |
| Dify | 模块化单体 | Python import + Celery |
| FastGPT | 微服务 | HTTP API |
| LangChain | 库/SDK | 函数调用 |
