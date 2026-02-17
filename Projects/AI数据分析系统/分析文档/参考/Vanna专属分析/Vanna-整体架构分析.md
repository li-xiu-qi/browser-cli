# Vanna 2.0 整体架构分析

## 1. 项目概述

### 一句话定义
Vanna 是一个**面向企业级数据查询的 AI Agent 框架**，通过自然语言生成 SQL 并执行，提供完整的交互式数据分析体验。

### 项目定位
- **核心目标**: 让非技术人员能够通过自然语言查询数据库，获得即时的数据洞察
- **设计理念**: "Web-First, User-Aware" - 以 Web 为先，全链路用户感知
- **适用场景**: 数据分析师、业务人员、管理者需要自助式数据查询的场合

### 解决的问题
| 问题 | Vanna 的解决方案 |
|------|-----------------|
| 技术人员瓶颈 | 业务人员自助查询，无需等待开发排期 |
| 数据访问安全 | 行级权限控制、审计日志、用户感知执行 |
| 交互体验差 | 预构建 `<vanna-chat>` Web 组件，流式响应 |
| 多数据源支持 | 统一抽象支持 10+ 种数据库 |
| LLM 厂商绑定 | 支持 OpenAI、Anthropic、Google、Ollama 等 |

---

## 2. 目录结构分析

```
vanna/
├── src/vanna/                    # 核心源码
│   ├── core/                     # 核心框架层
│   │   ├── agent/                # Agent 主实现
│   │   ├── tool/                 # 工具抽象接口
│   │   ├── llm/                  # LLM 服务抽象
│   │   ├── user/                 # 用户身份与权限
│   │   ├── workflow/             # 工作流处理
│   │   ├── storage/              # 对话存储
│   │   ├── middleware/           # LLM 中间件
│   │   ├── lifecycle/            # 生命周期钩子
│   │   ├── observability/        # 可观测性
│   │   └── audit/                # 审计日志
│   ├── components/               # UI 组件系统
│   │   ├── rich/                 # 富交互组件
│   │   │   ├── data/             # 数据展示(表格、图表)
│   │   │   ├── feedback/         # 反馈组件(状态、进度)
│   │   │   ├── interactive/      # 交互组件(按钮)
│   │   │   └── containers/       # 容器组件
│   │   └── simple/               # 简单组件
│   ├── capabilities/             # 能力抽象层
│   │   ├── agent_memory/         # Agent 记忆(RAG)
│   │   ├── sql_runner/           # SQL 执行器抽象
│   │   └── file_system/          # 文件系统抽象
│   ├── tools/                    # 内置工具实现
│   │   ├── run_sql.py            # SQL 执行工具
│   │   ├── visualize_data.py     # 数据可视化
│   │   ├── agent_memory.py       # 记忆工具
│   │   └── python.py             # Python 代码执行
│   ├── integrations/             # 第三方集成
│   │   ├── openai/               # OpenAI LLM
│   │   ├── anthropic/            # Claude LLM
│   │   ├── google/               # Gemini LLM
│   │   ├── ollama/               # 本地 LLM
│   │   ├── postgres/             # PostgreSQL
│   │   ├── mysql/                # MySQL
│   │   ├── snowflake/            # Snowflake
│   │   ├── bigquery/             # BigQuery
│   │   ├── chromadb/             # Chroma 向量存储
│   │   └── ...                   # 其他集成
│   ├── servers/                  # 服务器实现
│   │   ├── fastapi/              # FastAPI 路由
│   │   ├── flask/                # Flask 路由
│   │   └── base/                 # 基础服务抽象
│   ├── legacy/                   # 1.x 兼容层
│   └── examples/                 # 示例代码
├── frontends/                    # 前端组件
├── tests/                        # 测试用例
├── notebooks/                    # Jupyter 示例
└── img/                          # 架构图资源
```

### 架构分层解读

| 层级 | 职责 | 关键模块 |
|------|------|----------|
| **接入层** | Web 界面、API 路由 | `servers/`, `frontends/` |
| **编排层** | Agent 核心、工作流管理 | `core/agent/`, `core/workflow/` |
| **能力层** | 工具抽象、记忆、SQL执行 | `capabilities/`, `tools/` |
| **适配层** | LLM/数据库/向量存储集成 | `integrations/` |
| **展示层** | 流式 UI 组件 | `components/` |

---

## 3. 核心技术栈

### 3.1 基础框架
| 技术 | 版本要求 | 用途 |
|------|----------|------|
| Python | ≥3.9 | 运行环境 |
| Pydantic | ≥2.0 | 数据验证与序列化 |
| FastAPI | ≥0.68 | 高性能 API 服务 |
| Flask | ≥2.0 | 轻量级服务选项 |
| pandas | - | 数据处理 |
| SQLAlchemy | - | ORM 与数据库抽象 |

### 3.2 LLM 集成支持
```python
# 支持的 LLM 提供商
LLM_PROVIDERS = [
    "openai",           # GPT-4, GPT-5
    "anthropic",        # Claude 3.7+
    "google",           # Gemini 2.5+
    "azureopenai",      # Azure OpenAI
    "ollama",           # 本地模型
    "bedrock",          # AWS Bedrock
    "mistralai",        # Mistral
    "zhipuai",          # 智谱 AI
    "qianfan",          # 百度千帆
    # ... 更多
]
```

### 3.3 数据库支持
```python
# 支持的数据库
DATABASES = [
    "PostgreSQL",       # psycopg2
    "MySQL",            # PyMySQL
    "Snowflake",        # snowflake-connector
    "BigQuery",         # google-cloud-bigquery
    "DuckDB",           # duckdb
    "SQLite",           # 内置支持
    "ClickHouse",       # clickhouse_connect
    "Oracle",           # oracledb
    "SQL Server",       # pyodbc
    "Redshift",         # 通过 PostgreSQL
    "Presto/Trino",     # pyhive
]
```

### 3.4 向量存储(RAG)
```python
# 支持的向量数据库
VECTOR_STORES = [
    "ChromaDB",         # chromadb
    "Pinecone",         # pinecone
    "Milvus",           # pymilvus
    "Qdrant",           # qdrant-client
    "Weaviate",         # weaviate-client
    "OpenSearch",       # opensearch-py
    "Azure Search",     # azure-search-documents
    "FAISS",            # faiss-cpu/gpu
    "Marqo",            # marqo
    # ... 更多
]
```

### 3.5 RAG 机制
Vanna 的 RAG 采用 **Agent Memory** 模式：

```
┌─────────────────────────────────────────────┐
│              Agent Memory (RAG)              │
├─────────────────────────────────────────────┤
│  Tool Usage Memory                           │
│  ├── 问题 → 工具名称 → 参数 → 结果          │
│  └── 用于相似问题快速匹配                    │
│                                              │
│  Text Memory                                 │
│  ├── 自由文本知识                            │
│  └── DDL、文档、业务规则                     │
├─────────────────────────────────────────────┤
│  相似度搜索 → 检索历史成功案例 → 增强 Prompt │
└─────────────────────────────────────────────┘
```

---

## 4. 核心功能特性

### 4.1 企业级安全特性
| 特性 | 说明 |
|------|------|
| **User Resolver** | 从 Cookie/JWT/Header 解析用户身份 |
| **行级安全** | SQL 执行自动应用用户权限过滤 |
| **审计日志** | 每个查询按用户追踪，合规审计 |
| **访问组控制** | 基于用户组的工具/UI 功能访问控制 |
| **速率限制** | 通过生命周期钩子实现每用户配额 |

### 4.2 流式响应组件
```
用户提问
    ↓
流式输出:
├── StatusBarUpdate (处理状态)
├── TaskTrackerUpdate (任务进度)
├── StatusCard (工具执行状态)
├── DataFrameComponent (表格结果)
├── ChartComponent (可视化图表)
├── RichTextComponent (Markdown 总结)
└── ChatInputUpdate (重新启用输入)
```

### 4.3 内置工具集
| 工具 | 功能 |
|------|------|
| `run_sql` | 执行 SQL 查询，返回 DataFrame |
| `visualize_data` | 生成 Plotly 图表 |
| `search_saved_correct_tool_uses` | 搜索历史成功案例 |
| `save_question_tool_args` | 保存成功查询到记忆 |
| `python` | 执行 Python 代码 |
| `file_system` | 文件读写操作 |

### 4.4 可扩展性点
```python
Agent(
    # 1. 生命周期钩子
    lifecycle_hooks=[QuotaCheckHook(), AuditHook()],
    
    # 2. LLM 中间件
    llm_middlewares=[CachingMiddleware(), CostTrackingMiddleware()],
    
    # 3. 错误恢复策略
    error_recovery_strategy=RetryWithBackoff(),
    
    # 4. 上下文增强器
    context_enrichers=[RagEnricher(), BusinessContextEnricher()],
    
    # 5. LLM 上下文增强
    llm_context_enhancer=DefaultLlmContextEnhancer(agent_memory),
    
    # 6. 对话过滤器
    conversation_filters=[PiiFilter(), SensitiveDataFilter()],
    
    # 7. 可观测性
    observability_provider=OpenTelemetryProvider(),
)
```

---

## 5. 工作流程

### 5.1 从用户输入到 SQL 输出的完整流程

```
┌──────────────┐
│   用户提问    │  "Show Q4 sales"
└──────┬───────┘
       │
       ▼
┌──────────────────────────────┐
│  1. Frontend                 │  <vanna-chat> Web 组件
│     - 捕获用户输入           │
│     - 发送 SSE 请求          │  POST /api/vanna/v2/chat_sse
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  2. Server (FastAPI/Flask)   │
│     - 提取 RequestContext    │  cookies, headers, JWT
│     - 调用 ChatHandler       │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  3. User Resolver            │  自定义用户解析
│     - 解析 JWT/Cookie        │
│     - 返回 User 对象         │  id, email, group_memberships
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  4. Workflow Handler         │  预处理工作流
│     - /help, /status 命令?   │
│     - 是 → 直接响应          │
│     - 否 → 进入 LLM 流程     │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  5. System Prompt Builder    │  构建系统提示
│     - 用户身份与权限         │
│     - 可用工具列表           │
│     - 数据库 Schema (可选)   │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  6. LLM Context Enhancer     │  RAG 增强
│     - 搜索相似历史查询       │  Agent Memory
│     - 检索相关 DDL/文档      │  注入 Prompt
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  7. LLM Service              │  LLM 调用
│     - 发送请求               │  OpenAI/Anthropic/etc
│     - 流式响应               │  yield chunks
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  8. Tool Call Loop           │  工具执行循环
│     - LLM 返回 tool_calls    │  如: run_sql
│     - 执行前权限检查         │  user.access_groups
│     - 执行工具               │  SqlRunner
│     - 应用行级过滤           │  WHERE user_id = ?
│     - 返回结果给 LLM         │
│     - (循环直到完成)         │
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  9. Component Generation     │  UI 组件生成
│     - SQL 代码块             │  RichTextComponent
│     - 数据表格               │  DataFrameComponent
│     - 可视化图表             │  ChartComponent
│     - 自然语言总结           │  RichTextComponent
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────┐
│  10. Streaming to Frontend   │  SSE 流式传输
│     - 实时更新 UI            │
│     - 状态栏更新             │
│     - 最终完成信号           │  data: [DONE]
└──────┬───────────────────────┘
       │
       ▼
┌──────────────┐
│   用户看到   │  交互式结果(表+图+文字)
└──────────────┘
```

### 5.2 关键代码流程示意

```python
# Agent.send_message() 核心流程
async def send_message(request_context, message):
    # 1. 解析用户
    user = await user_resolver.resolve_user(request_context)
    
    # 2. 工作流预处理
    workflow_result = await workflow_handler.try_handle(agent, user, conversation, message)
    if workflow_result.should_skip_llm:
        return workflow_result.components
    
    # 3. 获取工具Schema
    tool_schemas = await tool_registry.get_schemas(user)  # 权限过滤
    
    # 4. 构建系统提示
    system_prompt = await system_prompt_builder.build_system_prompt(user, tool_schemas)
    system_prompt = await llm_context_enhancer.enhance_system_prompt(system_prompt, message, user)
    
    # 5. LLM 请求
    request = await _build_llm_request(conversation, tool_schemas, user, system_prompt)
    
    # 6. 工具执行循环
    while tool_iterations < config.max_tool_iterations:
        response = await llm_service.send_request(request)
        
        if response.is_tool_call():
            for tool_call in response.tool_calls:
                # 执行工具
                result = await tool_registry.execute(tool_call, context)
                # 生成 UI 组件
                yield result.ui_component
                # 添加到对话历史
                conversation.add_message(Message(role="tool", content=result.result_for_llm))
        else:
            # 最终响应
            yield UiComponent(rich_component=RichTextComponent(content=response.content))
            break
```

---

## 6. 与 DB-GPT/RAGFlow 的对比

### 6.1 三者定位对比

| 维度 | Vanna 2.0 | DB-GPT | RAGFlow |
|------|-----------|--------|---------|
| **核心定位** | SQL Agent 框架 | 数据智能体平台 | RAG 引擎 |
| **主要功能** | NL2SQL + 执行 | 多 Agent + 数据分析 | 文档 RAG |
| **架构模式** | Agent + Tools | Multi-Agent + App | Document → Chunk → RAG |
| **SQL 能力** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **UI 完备度** | ⭐⭐⭐⭐⭐ (内置) | ⭐⭐⭐⭐ (需部署) | ⭐⭐⭐ (API为主) |
| **企业安全** | ⭐⭐⭐⭐⭐ (User-Aware) | ⭐⭐⭐ | ⭐⭐⭐ |
| **扩展性** | ⭐⭐⭐⭐⭐ (7个扩展点) | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **部署复杂度** | 低 (pip install) | 高 (多服务) | 中 (Docker) |

### 6.2 Vanna 的独特优势

#### 优势 1: Web-First 开箱即用
```python
# Vanna: 一行代码获得完整 Web UI
register_chat_routes(app, chat_handler)  # 获得 <vanna-chat> + SSE 流式

# DB-GPT: 需要部署完整平台
# RAGFlow: 主要提供 API，UI 需自行构建
```

#### 优势 2: User-Aware 全链路
```python
# Vanna: 每个层级都知道用户身份
UserResolver → SystemPrompt → ToolAccess → RowLevelFilter → AuditLog

# DB-GPT: 主要关注 Agent 编排，权限控制相对独立
# RAGFlow: 关注检索，不涉及 SQL 权限
```

#### 优势 3: SQL 专项优化
| 特性 | Vanna | DB-GPT | RAGFlow |
|------|-------|--------|---------|
| 专用 SQL 工具链 |  | ⚠️ |  |
| SQL 执行结果流式表格 |  | ⚠️ |  |
| SQL 可视化自动生成 |  | ⚠️ |  |
| 查询记忆与相似匹配 |  | ⚠️ |  |
| 多数据库统一抽象 |   |  |  |

#### 优势 4: 嵌入式架构
```html
<!-- Vanna: 嵌入到现有系统 -->
<vanna-chat 
  sse-endpoint="/api/vanna/v2/chat_sse"
  theme="dark">
</vanna-chat>
<!-- 自动复用现有 Cookie/JWT -->
```

### 6.3 适用场景选择

```
选择 Vanna 当:
├── 需要快速为现有系统添加 NL2SQL 能力
├── 需要企业级用户权限和审计
├── 需要预构建的交互式 Web 界面
├── 技术栈是 Python，希望轻量集成
└── 主要场景是结构化数据查询

选择 DB-GPT 当:
├── 需要多 Agent 协作的复杂数据分析
├── 需要可视化拖拽构建工作流
├── 有足够的资源部署完整平台
└── 需要生态系统(App 市场)

选择 RAGFlow 当:
├── 主要需求是文档问答(RAG)
├── 对检索质量有极高要求
├── 非结构化数据为主
└── 有自研前端能力
```

---

## 7. 架构图

### 7.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Frontend Layer                            │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                   <vanna-chat> Web Component                   │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐  │  │
│  │  │  Chat   │  │  Table  │  │  Chart  │  │  Status Bar     │  │  │
│  │  │  Input  │  │  View   │  │  View   │  │  (Progress)     │  │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ SSE / WebSocket
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            Server Layer                             │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              FastAPI / Flask Routes                            │  │
│  │     POST /api/vanna/v2/chat_sse                               │  │
│  │     WebSocket /api/vanna/v2/chat_websocket                    │  │
│  └───────────────────────────────┬───────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         User-Aware Agent                            │
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────────┐   │
│  │  User Resolver  │───▶│  System Prompt  │───▶│      LLM      │   │
│  │  (JWT/Cookie)   │    │  (User + Tools) │    │ (Tool Calling)│   │
│  └─────────────────┘    └─────────────────┘    └───────┬───────┘   │
│                                                        │           │
│                              ┌─────────────────────────┘           │
│                              ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                      Tool Registry                           │  │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────────────┐  │  │
│  │  │ run_sql  │  │visualize_data│  │  Agent Memory Tools  │  │  │
│  │  └────┬─────┘  └──────┬───────┘  └───────────┬──────────┘  │  │
│  └───────┼───────────────┼──────────────────────┼─────────────┘  │
│          │               │                      │                │
└──────────┼───────────────┼──────────────────────┼────────────────┘
           │               │                      │
           ▼               ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Integration Layer                           │
│                                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────┐ │
│  │   LLM Providers     │  │  SQL Runners        │  │Vector Stores│ │
│  │  ┌───────────────┐  │  │  ┌───────────────┐  │  │┌───────────┐│ │
│  │  │   OpenAI      │  │  │  │  PostgreSQL   │  │  ││ ChromaDB  ││ │
│  │  │   Anthropic   │  │  │  │  MySQL        │  │  ││ Pinecone  ││ │
│  │  │   Google      │  │  │  │  Snowflake    │  │  ││  Qdrant   ││ │
│  │  │   Ollama      │  │  │  │  BigQuery     │  │  ││   ...     ││ │
│  │  └───────────────┘  │  │  └───────────────┘  │  │└───────────┘│ │
│  └─────────────────────┘  └─────────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.2 请求处理流程图

```
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌─────────────┐
│  User   │────▶│ Frontend │────▶│   Server    │────▶│    Agent    │
└─────────┘     └──────────┘     └─────────────┘     └──────┬──────┘
                                                            │
                    ┌───────────────────────────────────────┼───────┐
                    │                                       │       │
                    ▼                                       ▼       ▼
            ┌──────────────┐    ┌──────────┐    ┌────────────────────────┐
            │User Resolver │    │   LLM    │    │     Tool Registry      │
            └──────┬───────┘    └────┬─────┘    │  ┌────┐ ┌────┐ ┌────┐  │
                   │                 │          │  │SQL │ │Viz │ │Mem │  │
                   │                 │          │  └────┘ └────┘ └────┘  │
                   │                 │          └────────────────────────┘
                   │                 │                      │
                   ▼                 ▼                      ▼
            ┌──────────────────────────────────────────────────────┐
            │                    Response Stream                    │
            │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
            │  │  Status  │─▶│   SQL    │─▶│  Table   │─▶│Summary │ │
            │  │  Update  │  │  Block   │  │   View   │  │  Card  │ │
            │  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
            └──────────────────────────────────────────────────────┘
                                    │
                                    ▼
                              ┌──────────┐
                              │  User    │
                              └──────────┘
```

### 7.3 扩展点架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Core                                  │
│                                                                     │
│  Extensibility Points (7个扩展点):                                  │
│                                                                     │
│  1. lifecycle_hooks:     [QuotaCheck]──[AuditLog]──[RateLimit]      │
│                          消息/工具生命周期钩子                      │
│                                                                     │
│  2. llm_middlewares:     [Cache]──[PromptEng]──[CostTrack]          │
│                          LLM 请求/响应拦截                          │
│                                                                     │
│  3. error_recovery:      [Retry]──[Fallback]──[CircuitBreaker]      │
│                          错误恢复策略                               │
│                                                                     │
│  4. context_enrichers:   [RAG]──[BusinessContext]──[SchemaInfo]     │
│                          工具上下文增强                             │
│                                                                     │
│  5. llm_context_enhancer:[AgentMemory]──[Documentation]             │
│                          Prompt 动态增强                            │
│                                                                     │
│  6. conversation_filters:[PII]──[SensitiveData]──[HistoryCompress]  │
│                          对话历史过滤                               │
│                                                                     │
│  7. observability:       [OpenTelemetry]──[Prometheus]──[Logging]   │
│                          可观测性                                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 8. 总结

### Vanna 2.0 的核心价值

1. **最完整的 NL2SQL 开箱体验**: 从自然语言到 SQL 到可视化，一站式解决
2. **真正的企业级**: 用户感知贯穿全链路，审计、权限、安全一应俱全
3. **现代 Web 架构**: 流式响应、组件化 UI、框架无关的前端
4. **极致可扩展**: 7 个扩展点，适配各种复杂场景
5. **生态兼容性**: 支持主流 LLM、数据库、向量存储

### 技术亮点

- **架构设计**: Clean Architecture 分层清晰，接口与实现分离
- **类型安全**: 全链路 Pydantic 类型，开发体验好
- **异步优先**: 全 async/await 设计，高性能并发
- **可测试性**: 依赖注入设计，易于 Mock 和测试

### 适合借鉴的方面

| 方面 | 可借鉴内容 |
|------|-----------|
| Agent 设计 | Tool + Capability + Integration 三层抽象 |
| 用户权限 | User-Aware 设计理念，从请求到执行的权限传递 |
| 流式 UI | Component-based 流式响应架构 |
| 扩展性设计 | 7 个扩展点的插拔式设计 |
| RAG 集成 | Agent Memory 与 Tool 执行的紧密结合 |
