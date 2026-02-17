# RAGFlow 目录结构分析

**分析日期**: 2026-02-05  
**项目版本**: RAGFlow v0.23.1  
**分析目标**: 深入理解 RAGFlow 代码组织方式

---

## 一、顶层目录概览

```
ragflow/
├── .github/                # GitHub 工作流配置
├── admin/                  # 管理后台模块
├── agent/                  # Agent 框架
├── api/                    # 主 API 层
├── common/                 # 全局通用代码
├── conf/                   # 配置文件
├── deepdoc/                # 文档解析引擎
├── docker/                 # Docker 配置
├── docs/                   # 文档
├── example/                # 使用示例
├── helm/                   # Kubernetes Helm 配置
├── intergrations/          # 第三方集成
├── mcp/                    # Model Context Protocol
├── memory/                 # 记忆系统
├── rag/                    # RAG 核心引擎
├── sandbox/                # 沙箱环境
├── sdk/                    # SDK
├── test/                   # 测试
├── tools/                  # 工具脚本
└── web/                    # 前端 Web 应用
```

---

## 二、核心目录详解

### 2.1 api/ - API 层

```
api/api/
├── apps/                   # 业务应用模块
│   ├── canvas_app.py       # Agent/工作流 API
│   ├── conversation_app.py # 对话 API
│   ├── document_app.py     # 文档管理 API
│   ├── file_app.py         # 文件管理 API
│   ├── kb_app.py           # 知识库 API
│   ├── sdk/                # SDK API
│   └── user_app.py         # 用户管理 API
├── common/                 # API 通用工具
├── db/                     # 数据库层
│   ├── db_models.py        # 数据模型定义
│   ├── db_utils.py         # 数据库工具
│   └── services/           # 数据服务
└── utils/                  # API 工具函数
```

### 2.2 agent/ - Agent 框架

```
agent/
├── component/              # 工作流组件
│   ├── base.py            # 组件基类
│   ├── begin.py           # 开始节点
│   ├── retrieval.py       # 检索节点
│   ├── generate.py        # 生成节点
│   ├── llm.py             # LLM 节点
│   ├── switch.py          # 条件分支
│   ├── loop.py            # 循环节点
│   └── agent_with_tools.py # 工具 Agent
├── plugin/                # 插件系统
├── sandbox/               # 代码执行沙箱
├── templates/             # 预置模板
├── test/                  # Agent 测试
└── tools/                 # 工具定义
```

### 2.3 rag/ - RAG 核心引擎

```
rag/
├── app/                   # 领域特定解析器
│   ├── naive.py          # 通用解析
│   ├── paper.py          # 学术论文
│   ├── resume.py         # 简历
│   └── laws.py           # 法律文档
├── flow/                  # 文档处理流水线
│   ├── parser/           # 解析器
│   ├── splitter/         # 文本切分
│   └── tokenizer/        # 分词
├── graphrag/             # GraphRAG 知识图谱
│   ├── general/          # 完整版
│   └── light/            # 轻量版
├── llm/                  # LLM 封装
│   ├── chat_model.py     # 对话模型
│   ├── embedding_model.py # 嵌入模型
│   └── rerank_model.py   # 重排序模型
├── nlp/                  # NLP 处理
│   ├── search.py         # 检索核心
│   └── rag_tokenizer.py  # RAG 分词器
├── prompts/              # Prompt 模板
├── svr/                  # 服务层
│   └── task_executor.py  # 任务执行器
└── utils/                # 工具函数
```

### 2.4 deepdoc/ - 文档解析引擎

```
deepdoc/
├── parser/               # 文档解析器
│   ├── pdf_parser.py     # PDF 解析
│   ├── docx_parser.py    # Word 解析
│   ├── excel_parser.py   # Excel 解析
│   ├── ppt_parser.py     # PPT 解析
│   └── resume/           # 简历解析
└── vision/               # 视觉理解
    ├── ocr.py            # OCR 识别
    ├── layout_recog.py   # 版面分析
    └── table_structure.py # 表格结构识别
```

### 2.5 web/ - 前端应用

```
web/
├── src/
│   ├── components/       # React 组件
│   ├── hooks/            # React Hooks
│   ├── pages/            # 页面
│   ├── services/         # API 服务
│   ├── stores/           # 状态管理
│   └── utils/            # 工具函数
└── public/               # 静态资源
```

---

## 三、目录组织原则

### 3.1 垂直模块化

RAGFlow 按照**业务功能垂直切分**，每个模块包含完整的功能实现：

```
api/        → HTTP 接口、路由、请求处理
agent/      → Agent 框架、工作流、工具
rag/        → RAG 引擎、检索、向量化
deepdoc/    → 文档解析、OCR、版面分析
memory/     → 记忆系统、上下文管理
```

### 3.2 分层架构

```
┌─────────────────────────────────────┐
│  接入层 (api/apps/)                 │
├─────────────────────────────────────┤
│  服务层 (api/db/services/)          │
├─────────────────────────────────────┤
│  核心业务层 (agent/, rag/, deepdoc/) │
├─────────────────────────────────────┤
│  数据访问层 (api/db/)               │
├─────────────────────────────────────┤
│  基础设施层 (common/)               │
└─────────────────────────────────────┘
```

### 3.3 关键设计特点

| 特点 | 说明 | 示例 |
|------|------|------|
| **功能垂直** | 按业务功能划分目录 | agent/, rag/, deepdoc/ |
| **前后端分离** | web/ 和 api/ 完全独立 | React + Flask |
| **模块化设计** | 每个模块内部自治 | agent/component/ |
| **沙箱隔离** | sandbox/ 目录确保代码安全 | 代码执行隔离 |
| **文档引擎独立** | deepdoc/ 可单独迭代 | 解析器插件化 |

---

## 四、关键文件定位

### 4.1 入口文件

| 入口 | 路径 | 说明 |
|------|------|------|
| Web Server | `api/ragflow_server.py` | Flask 主服务 |
| Task Executor | `rag/svr/task_executor.py` | 任务执行器 |
| Data Sync | `rag/svr/sync_data_source.py` | 数据同步 |
| Admin Server | `admin/server/admin_server.py` | 管理后台 |
| MCP Server | `mcp/server/server.py` | MCP 服务 |

### 4.2 配置文件

| 配置 | 路径 | 说明 |
|------|------|------|
| 主配置 | `conf/` | 各环境配置文件 |
| Docker | `docker/` | Dockerfile + Compose |
| K8s | `helm/` | Helm Charts |

### 4.3 核心模型

| 模型 | 路径 | 说明 |
|------|------|------|
| 数据模型 | `api/db/db_models.py` | Peewee/SQLAlchemy 模型 |
| Agent 组件 | `agent/component/` | 工作流组件定义 |
| RAG 检索 | `rag/nlp/search.py` | 检索核心实现 |

---

## 五、代码依赖关系

```
┌─────────────────────────────────────────────────────────────┐
│                    代码依赖关系                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  api/apps/  ────────────────────────────────────────────────┐│
│       ↓                                                     ││
│  api/db/services/  ─────────────────────────────────────┐   ││
│       ↓                                                  │   ││
│  agent/, rag/, deepdoc/  ←───────────────────────────────┘   ││
│       ↓                                                      ││
│  api/db/  ←──────────────────────────────────────────────────┘│
│       ↓                                                      │
│  common/                                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、总结

### 6.1 目录结构特点

1. **垂直模块化**：按业务功能划分，职责清晰
2. **分层明确**：接入层 → 服务层 → 业务层 → 数据层
3. **沙箱隔离**：sandbox/ 确保代码执行安全
4. **文档引擎独立**：deepdoc/ 可独立演进

### 6.2 可借鉴实践

| 实践 | 适用场景 |
|------|----------|
| 功能垂直切分 | 中大型项目 |
| 前后端分离 | 现代 Web 应用 |
| 模块内部自治 | 团队协作开发 |
| 沙箱隔离 | 代码执行场景 |
