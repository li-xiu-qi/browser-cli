# SQLBot - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | DataEase 出品的基于大模型和 RAG 的智能问数系统（ChatBI） |
| Star/Fork | 5.4k Star |
| 维护状态 | 活跃（飞致云团队持续迭代） |
| 许可证 | FIT2CLOUD Open Source License（GPLv3 变体，有商业限制） |

## 2. 核心能力速览
- 主要功能:
  - 对话式数据分析（ChatBI）
  - Text-to-SQL 智能转换
  - 基于 RAG 的语义理解
  - 可视化图表生成
  - 多数据源支持
  - MCP 协议支持（模型上下文协议）
- 技术亮点:
  - 开箱即用，Docker 一键部署
  - 工作空间级资源隔离
  - 细粒度数据权限控制
  - 支持 n8n/Dify/MaxKB/DataEase 集成

## 3. 架构概览
- 部署形态: Web 应用（Docker 部署）
- 技术栈: 
  - 后端: Python + FastAPI + LangChain + LangGraph
  - Python 版本: 3.11
  - 向量数据库: pgvector
  - LLM: OpenAI / 通义千问 / HuggingFace
  - 缓存: Redis
- 数据库支持: MySQL、PostgreSQL、SQLServer、Oracle、ClickHouse、Doris、StarRocks 等

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 4 | Python + FastAPI + LangChain 技术栈与我们高度匹配 |
| 代码复用 | 4 | 大量可复用的 RAG 实现、Agent 工作流、Text-to-SQL 逻辑 |
| 集成潜力 | 3 | 支持 MCP 协议，可作为组件集成，但许可证有商业限制 |
| 学习价值 | 5 | 完整的企业级 ChatBI 实现，RAG + Agent 架构设计精良 |

### 4.1 值得借鉴的设计
- LangChain + LangGraph 的 Agent 工作流设计
- RAG 语义检索与 Text-to-SQL 结合架构
- 术语库配置与 SQL 示例校准机制
- 工作空间级别的数据权限隔离
- 多数据源连接管理抽象层

### 4.2 可复用的代码/模块
- Text-to-SQL Generator 实现
- RAG 检索模块（向量存储 + 语义匹配）
- 数据库连接池管理
- 数据权限控制逻辑
- 对话历史管理与多轮对话处理

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| backend/pyproject.toml | Python 依赖配置（FastAPI + LangChain + LangGraph） |
| backend/app/ | 后端核心代码目录 |
| docker-compose.yml | Docker 部署配置 |
| README.md | 部署与使用文档 |

## 6. 优先级判定
- [x] 高优先级 - 重点研究
- [ ] 中优先级 - 参考借鉴
- [ ] 低优先级 - 了解即可

**推荐理由**: 
1. 技术栈高度匹配（Python + FastAPI + LangChain），代码复用价值极高
2. DataEase 团队出品，企业级工程设计规范
3. 完整的 RAG + Agent + Text-to-SQL 实现，架构设计精良
4. 开箱即用的一键部署体验，工程化实践成熟
5. 支持 MCP 协议，可作为组件集成到现有系统
6. 包含术语库、SQL 示例校准等高级功能，有助于提升问数准确性
