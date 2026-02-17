# DB-GPT 目录结构分析

**分析日期**: 2026-02-05  
**项目版本**: DB-GPT v0.7.0  
**分析目标**: 深入理解 DB-GPT Monorepo 代码组织方式

---

## 一、Monorepo 结构概览

```
db-gpt/
├── .github/                # GitHub 工作流配置
├── assets/                 # 静态资源
│   └── schema/             # 数据库 Schema
├── configs/                # 配置文件
├── docker/                 # Docker 配置
│   ├── allinone/           # 一体化部署
│   ├── base/               # 基础镜像
│   └── examples/           # 示例配置
├── docs/                   # 文档
├── examples/               # 使用示例
│   ├── agents/             # Agent 示例
│   ├── awel/               # AWEL 工作流示例
│   ├── client/             # 客户端示例
│   ├── rag/                # RAG 示例
│   └── sdk/                # SDK 示例
├── i18n/                   # 国际化
├── packages/               # ★ Monorepo 核心包
│   ├── dbgpt-app/          # 应用层
│   ├── dbgpt-client/       # 客户端
│   ├── dbgpt-core/         # 核心层
│   ├── dbgpt-ext/          # 扩展层
│   └── dbgpt-serve/        # 服务层
├── pilot/                  # 核心后端代码
├── requirements/           # 依赖文件
├── scripts/                # 脚本工具
├── tests/                  # 测试
└── web/                    # Next.js 前端
```

---

## 二、Packages 详解

### 2.1 packages/dbgpt-core/ - 核心层

```
dbgpt-core/
└── src/dbgpt/
    ├── agent/                # Agent 框架
    │   ├── core/             # Agent 核心
    │   │   ├── agent.py      # Agent 基类
    │   │   ├── agent_manage.py # Agent 管理器
    │   │   ├── action/       # Action 动作系统
    │   │   ├── memory/       # 记忆系统
    │   │   └── plan/         # 规划系统
    │   ├── expand/           # 预置 Agent
    │   │   ├── tool_assistant_agent.py
    │   │   ├── code_assistant_agent.py
    │   │   └── data_scientist_agent.py
    │   └── resource/         # 资源管理
    │       └── mcp.py        # MCP 资源
    ├── cli/                  # 命令行工具
    ├── configs/              # 配置管理
    ├── core/                 # 核心组件
    │   ├── awel/             # ★ AWEL 工作流引擎
    │   │   ├── dag/          # DAG 管理
    │   │   ├── operators/    # 算子实现
    │   │   ├── trigger/      # 触发器
    │   │   └── runner/       # 执行引擎
    │   ├── interface/        # 接口定义
    │   ├── operators/        # 核心算子
    │   └── schema/           # 数据模型
    ├── datasource/           # 数据源抽象
    ├── experimental/         # 实验性功能
    ├── model/                # 模型管理
    │   ├── adapter/          # 模型适配器
    │   ├── cluster/          # 模型集群
    │   ├── proxy/            # 代理模型
    │   └── operators/        # 模型算子
    ├── rag/                  # RAG 核心
    │   ├── embedding/        # Embedding 工厂
    │   ├── retriever/        # 检索器
    │   ├── operators/        # RAG 算子
    │   └── evaluation/       # RAG 评估
    ├── storage/              # 存储抽象
    │   ├── cache/            # 缓存
    │   ├── metadata/         # 元数据管理
    │   └── vector_store/     # 向量存储基类
    ├── train/                # 训练模块
    ├── util/                 # 通用工具
    └── vis/                  # 可视化
```

### 2.2 packages/dbgpt-serve/ - 服务层

```
dbgpt-serve/
└── src/dbgpt_serve/
    ├── agent/                # Agent 服务
    │   ├── agents/           # Agent 控制器
    │   ├── db/               # Agent 数据模型
    │   └── team/             # Agent 团队协作
    ├── conversation/         # 对话服务
    ├── core/                 # 服务基类
    │   └── service.py        # BaseService
    ├── datasource/           # 数据源服务
    │   ├── manages/          # 连接管理
    │   └── service/          # 数据源服务
    ├── dbgpts/               # DB-GPT 插件
    ├── evaluate/             # 评估服务
    ├── feedback/             # 反馈服务
    ├── file/                 # 文件服务
    ├── flow/                 # AWEL Flow 服务
    │   ├── api/              # Flow API
    │   ├── service/          # Flow 服务
    │   └── templates/        # 预置模板
    ├── libro/                # Notebook 服务
    ├── model/                # 模型部署服务
    ├── prompt/               # Prompt 服务
    ├── rag/                  # RAG 服务
    │   ├── operators/        # RAG 算子
    │   └── service/          # RAG 服务
    └── utils/                # 服务工具
```

### 2.3 packages/dbgpt-app/ - 应用层

```
dbgpt-app/
└── src/dbgpt_app/
    ├── initialization/       # 系统初始化
    │   ├── db_model_initialization.py
    │   └── serve_initialization.py
    ├── knowledge/            # 知识库管理
    │   ├── api.py            # 知识库 API
    │   └── service.py        # 知识库服务
    ├── openapi/              # OpenAPI 定义
    │   ├── api_v1/           # API v1
    │   └── api_v2/           # API v2
    ├── operators/            # 应用层算子
    ├── scene/                # 聊天场景
    │   ├── base.py           # ChatScene 枚举
    │   ├── chat_factory.py   # ChatFactory
    │   ├── base_chat.py      # BaseChat 基类
    │   ├── chat_normal/      # 普通对话
    │   ├── chat_knowledge/   # 知识库对话
    │   ├── chat_db/          # 数据库对话
    │   ├── chat_dashboard/   # 仪表板对话
    │   ├── chat_excel/       # Excel 对话
    │   └── operators/        # 场景算子
    ├── static/               # 静态资源
    └── tests/                # 应用测试
```

### 2.4 packages/dbgpt-ext/ - 扩展层

```
dbgpt-ext/
└── src/dbgpt_ext/
    ├── datasource/           # 数据源实现
    │   ├── rdbms/            # 关系型数据库
    │   │   ├── conn_mysql.py
    │   │   ├── conn_postgresql.py
    │   │   ├── conn_sqlite.py
    │   │   └── ...
    │   └── conn_tugraph.py   # 图数据库
    ├── llms/                 # LLM 实现
    ├── rag/                  # RAG 扩展
    │   ├── chunk_manager.py
    │   └── operators/
    └── storage/
        ├── graph_store/      # 图存储
        ├── vector_store/     # 向量存储实现
        │   ├── chroma_store.py
        │   ├── milvus_store.py
        │   └── pgvector_store.py
        └── knowledge_graph/  # 知识图谱
```

### 2.5 packages/dbgpt-client/ - 客户端

```
dbgpt-client/
└── src/dbgpt_client/
    ├── _cli.py               # CLI 入口
    ├── flow.py               # Flow API 客户端
    ├── schema.py             # 数据模型
    └── ...
```

---

## 三、前端目录结构

### 3.1 web/ - Next.js 前端

```
web/
├── app/                    # App Router (Next.js 13+)
├── client/                 # 客户端代码
├── components/             # React 组件
│   ├── flow/               # Flow 画布组件
│   ├── chat/               # 聊天组件
│   └── common/             # 通用组件
├── hooks/                  # React Hooks
├── lib/                    # 工具库
├── locales/                # 国际化
├── pages/                  # Pages Router
│   ├── construct/          # 构建页面
│   │   ├── flow/           # Flow 编排
│   │   ├── app/            # App 管理
│   │   └── knowledge/      # 知识库
│   └── mobile/             # 移动端
├── public/                 # 静态资源
├── styles/                 # 样式
├── types/                  # TypeScript 类型
└── utils/                  # 工具函数
```

---

## 四、目录组织原则

### 4.1 Monorepo 分层架构

```
┌─────────────────────────────────────┐
│  L1: 客户端层 (dbgpt-client)        │
├─────────────────────────────────────┤
│  L2: 应用层 (dbgpt-app)             │
│      - Web API, 场景管理            │
├─────────────────────────────────────┤
│  L3: 服务层 (dbgpt-serve)           │
│      - 业务服务, 数据访问           │
├─────────────────────────────────────┤
│  L4: 核心层 (dbgpt-core) ★          │
│      - AWEL, Agent, 模型, RAG       │
├─────────────────────────────────────┤
│  L5: 扩展层 (dbgpt-ext)             │
│      - 具体实现, 可选依赖           │
└─────────────────────────────────────┘
```

### 4.2 包依赖关系

```
dbgpt-client
    ↓
dbgpt-app ←──────→ dbgpt-serve
    ↓                   ↓
    └───────────────────┘
            ↓
        dbgpt-core ★ 核心
            ↓
        dbgpt-ext (可选)
```

### 4.3 关键设计特点

| 特点 | 说明 | 示例 |
|------|------|------|
| **Monorepo** | 多包统一管理 | packages/* |
| **分层清晰** | 职责分离 | app/ serve/ core/ ext/ |
| **组件化** | SystemApp 管理 | BaseComponent |
| **类型安全** | Python 泛型 | Generic[T, REQ, RES] |
| **可插拔** | 扩展层可替换 | dbgpt-ext |

---

## 五、关键文件定位

### 5.1 入口文件

| 入口 | 路径 | 说明 |
|------|------|------|
| Web Server | `packages/dbgpt-app/src/dbgpt_app/base.py` | 服务启动 |
| CLI | `packages/dbgpt-core/src/dbgpt/cli/` | 命令行 |
| Component | `packages/dbgpt-core/src/dbgpt/component.py` | 组件基类 |

### 5.2 核心配置

| 配置 | 路径 | 说明 |
|------|------|------|
| 主配置 | `configs/` | TOML 配置文件 |
| 模型配置 | `packages/dbgpt-core/src/dbgpt/configs/` | 模型参数 |
| Docker | `docker/` | 多镜像构建 |

### 5.3 核心模型

| 模型 | 路径 | 说明 |
|------|------|------|
| 组件 | `component.py` | SystemApp 组件 |
| AWEL | `core/awel/` | 工作流引擎 |
| Agent | `agent/core/agent.py` | Agent 基类 |
| RAG | `rag/` | RAG 核心 |

---

## 六、代码依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                    代码依赖关系                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  web/ (Next.js)                                             │
│       ↓ REST API                                            │
│  dbgpt-app/openapi/                                         │
│       ↓                                                     │
│  dbgpt-app/scene/ ←────── ChatFactory                       │
│       │                                                     │
│       ├───→ dbgpt-serve/flow/                               │
│       │              ↓                                       │
│       │         FlowService                                 │
│       │              ↓                                       │
│       └───→ dbgpt-core/awel/ ★                             │
│                     ↓                                        │
│              DAGManager, Operators                          │
│                     ↓                                        │
│              dbgpt-core/component.py                        │
│                     ↓                                        │
│              SystemApp (组件注册表)                          │
│                     ↓                                        │
│       ┌─────────────┼─────────────┐                         │
│       ↓             ↓             ↓                         │
│  dbgpt-serve/  dbgpt-core/   dbgpt-ext/                    │
│  (服务层)      (核心层)       (扩展层)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 七、总结

### 7.1 目录结构特点

| 特点 | 说明 | 优势 |
|------|------|------|
| **Monorepo** | 多包统一管理 | 依赖管理简化 |
| **分层架构** | 5 层清晰分离 | 职责明确 |
| **组件化** | SystemApp 管理 | 可插拔扩展 |
| **类型安全** | 大量使用泛型 | 代码健壮 |
| **DuckDB** | 轻量级部署 | 开箱即用 |

### 7.2 可借鉴实践

| 实践 | 适用场景 |
|------|----------|
| Monorepo + uv | 大型 Python 项目 |
| 组件化架构 | 需要扩展点的系统 |
| 分层服务 | 企业级应用 |
| Python 泛型 | 类型敏感项目 |

### 7.3 与 RAGFlow/Vanna 对比

| 维度 | DB-GPT | RAGFlow | Vanna |
|------|--------|---------|-------|
| **结构** | Monorepo | 单体目录 | 扁平库 |
| **分层** | 5 层 | 3-4 层 | 2 层 |
| **包数** | 5+ 包 | 1 包 | 1 包 |
| **复杂度** | 高 | 中 | 低 |
| **适用** | 框架平台 | 完整产品 | 工具库 |
