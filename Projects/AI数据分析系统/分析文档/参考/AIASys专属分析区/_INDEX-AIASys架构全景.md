# AIASys 架构全景索引

**项目路径**: `C:\Users\ke\Documents\文件\work\AIASys`  
**分析日期**: 2026-02-08  
**分析文档数**: 5 篇  
**架构图**: 15 个

---

## 项目概述

**AIASys** 是面向工业制造的智能数据分析平台，采用 **Host-Worker 双 Agent 架构**。

### 核心定位

> **AIASys = 工业数据分析 + Host-Worker 双 Agent + smolagents 扩展 + Jupyter 执行**

### 核心功能

- **设备数据分析** - 振动分析、频谱分析、趋势分析、异常检测
- **智能故障诊断** - 故障检测、分类、严重性评估、维护建议
- **参数预测优化** - 时间序列预测、参数辨识预测、参数优化
- **智能对话** - 基于大语言模型的自然语言交互
- **Notebook 回放** - 分析过程可追溯、可复现

### 支持设备

- 轧机 (Rolling Mill)
- 电机 (Motor)
- 减速器 (Reducer)
- 轴承 (Bearing)

---

## 分析文档目录

| 序号 | 文档 | 核心内容 | 大小 |
|------|------|----------|------|
| 01 | [[01-AIASys-整体架构分析]] | 系统架构、双 Agent 设计、技术栈选型 | 25KB |
| 02 | [[02-AIASys-后端架构分析]] | FastAPI、Agent 系统、Jupyter 集成、API 设计 | 30KB |
| 03 | [[03-AIASys-前端架构分析]] | React 19、Vite 7、SSE 流式、状态管理 | 25KB |
| 04 | [[04-AIASys-Agent系统分析]] | Host-Worker 架构、压缩机制、工具系统 | 28KB |
| 05 | [[05-AIASys-项目管理分析]] | AI 技能库、文档体系、开发规范 | 20KB |

---

## 技术栈总览

| 层级 | 技术 | 版本 |
|------|------|------|
| **后端** | FastAPI | 现代版本 |
| | smolagents | 扩展定制 |
| | Jupyter Client | 代码执行 |
| | Celery + Redis | 异步任务 |
| | uv | 包管理 |
| **前端** | React | 19 |
| | TypeScript | 5.9 |
| | Vite | 7 |
| | Tailwind CSS | 4 |
| | shadcn/ui | 组件库 |
| **数据库** | Supabase | PostgreSQL |
| **容器** | Docker | Compose |

---

## 架构图目录

位于 `graphviz/` 和 `assets/` 文件夹：

### 整体架构图

| 图表 | 类型 | 说明 |
|------|------|------|
| aiasys-系统架构图.svg | 架构图 | 六层系统架构 |
| aiasys-双Agent架构图.svg | 架构图 | Host-Worker 协作关系 |
| aiasys-数据流图.svg | 数据流图 | 数据从输入到输出的流向 |

### 后端架构图

| 图表 | 类型 | 说明 |
|------|------|------|
| aiasys-后端模块依赖图.svg | 依赖图 | 后端模块间依赖关系 |
| aiasys-Agent调用链图.svg | 调用链图 | Host-Worker 调用流程 |
| aiasys-API架构图.svg | 架构图 | API 路由结构 |

### 前端架构图

| 图表 | 类型 | 说明 |
|------|------|------|
| aiasys-前端组件架构图.svg | 组件图 | 组件层次结构 |
| aiasys-状态管理图.svg | 状态图 | 状态流设计 |
| aiasys-前后端交互图.svg | 交互图 | API 通信与 SSE 流 |

### Agent 系统图

| 图表 | 类型 | 说明 |
|------|------|------|
| aiasys-HostWorker架构图.svg | 架构图 | Host-Worker 详细架构 |
| aiasys-压缩机制流程图.svg | 流程图 | 三层压缩机制 |
| aiasys-Agent工具链图.svg | 工具图 | 工具注册与调用流程 |

### 项目管理图

| 图表 | 类型 | 说明 |
|------|------|------|
| aiasys-文档体系图.svg | 体系图 | 五层文档架构 |
| aiasys-AI协作流程图.svg | 流程图 | AI-人类协作流程 |
| aiasys-开发工作流图.svg | 工作流图 | 完整开发流程 |

---

## 核心架构洞察

### 1. Host-Worker 双 Agent 架构

```
用户 → Host Agent → Worker Agent → Jupyter Kernel
         ↓              ↓
    对话协调      代码执行
    任务分配      数据分析
```

- **Host Agent**：ToolCallingAgent，负责对话协调和任务分配
- **Worker Agent**：CodeAgent，负责代码执行和数据分析

### 2. 三层上下文压缩机制

| 层级 | 名称 | 触发条件 | 作用 |
|------|------|----------|------|
| 1 | Microcompaction | 每步执行后 | 截断旧 observations |
| 2 | Auto-compaction | Token 阈值 | 生成结构化摘要 |
| 3 | Manual compact | 手动触发 | 聚焦特定内容 |

### 3. 与 smolagents 的关系

| 维度 | smolagents | AIASys 扩展 |
|------|-----------|-------------|
| Agent 架构 | Manager-Managed | Host-Worker |
| 记忆管理 | 基础 Memory | 三层压缩 |
| 代码执行 | Local/E2B | Jupyter Kernel |
| 前端 | Gradio | React + SSE |

---

## 快速导航

### 按角色

| 角色 | 推荐阅读 |
|------|----------|
| **架构师** | 01、04 |
| **后端开发** | 02、04 |
| **前端开发** | 03 |
| **项目管理** | 05 |
| **AI 工程师** | 04、02 |

### 按主题

| 主题 | 相关文档 |
|------|----------|
| **系统架构** | 01 |
| **后端设计** | 02 |
| **前端设计** | 03 |
| **Agent 系统** | 04 |
| **项目管理** | 05 |

---

## 参考代码位置

```
AIASys/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── agents/
│   │   │   │   ├── core/
│   │   │   │   │   ├── host.py              # Host Agent
│   │   │   │   │   ├── compressed_agents.py # 压缩 Agent
│   │   │   │   │   └── team.py              # Agent 团队
│   │   │   │   ├── compaction/              # 压缩机制
│   │   │   │   │   └── manager.py
│   │   │   │   └── executor/
│   │   │   │       └── jupyter.py           # Jupyter 集成
│   │   │   └── api/
│   │   │       └── v1/
│   │   │           └── chat.py              # SSE 流式接口
│   │   └── docs/                            # 后端文档
│   └── web/
│       ├── src/
│       │   ├── components/                  # React 组件
│       │   ├── hooks/                       # 自定义 Hooks
│       │   └── lib/
│       │       └── api.ts                   # API 客户端
│       └── docs/                            # 前端文档
├── docs/
│   ├── ai/                                  # AI 编程提示词
│   ├── guides/                              # 开发指南
│   └── implementation-status/               # 功能状态
└── .agents/
    └── skills/                              # AI 技能库
```

---

## 与 smolagents 分析文档的关系

AIASys 是基于 smolagents 构建的工业应用项目，建议配合阅读：

| smolagents 文档 | AIASys 关联 |
|----------------|------------|
| [[01-smolagents-Agent架构深度分析]] | Agent 基础 |
| [[04-smolagents-记忆与历史对话管理]] | 压缩机制基础 |
| [[46-smolagents-生产级记忆管理与历史对话管理实践指南]] | 生产部署参考 |
| [[47-smolagents流输出边界情况深度分析]] | SSE 实现参考 |

---

## 维护信息

- **分析者**: AI 协作助手
- **分析完成**: 2026-02-08
- **项目维护者**: li-xiu-qi
- **最后更新**: 2026-02-02

---

*本文档为 AIASys 项目架构分析总入口*
