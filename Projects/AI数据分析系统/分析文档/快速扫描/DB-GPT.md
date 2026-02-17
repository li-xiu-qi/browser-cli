# DB-GPT - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | 开源 AI 原生数据应用开发框架，集成多模型管理、RAG、Text-to-SQL 及 Agent 工作流编排 |
| Star/Fork | 18.1k / 2k+ |
| 维护状态 | 活跃 (最新 v0.7.0 支持 MCP 协议、DeepSeek R1、QwQ-32B) |
| 许可证 | MIT |

## 2. 核心能力速览
- 主要功能:
  - RAG 框架与知识库应用构建
  - GBI (生成式 BI) 报表分析与业务洞察
  - Text-to-SQL 微调框架 (Spider 准确率 82.5%)
  - 数据驱动的 Multi-Agents 协作框架
  - AWEL (Agentic Workflow Expression Language) 工作流编排
  - 多模型管理 (SMMF) 支持 20+ 开源/闭源模型
- 技术亮点:
  - 模块化包设计: dbgpt-core/app/serve/client/ext/sandbox/accelerator
  - 支持 DeepSeek、Qwen、Llama、GLM 等主流模型
  - DB-GPT-Hub 子项目专注 Text-to-SQL 微调

## 3. 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     DB-GPT 架构                              │
├─────────────────────────────────────────────────────────────┤
│  前端层 (web/)                                               │
│  ├── React/Vue Web UI                                       │
│  └── GPT-Vis 可视化协议                                      │
├─────────────────────────────────────────────────────────────┤
│  应用层 (packages/dbgpt-app/)                               │
│  ├── 知识库管理 (knowledge/)                                │
│  ├── 场景应用 (scene/)                                      │
│  └── 算子编排 (operators/)                                  │
├─────────────────────────────────────────────────────────────┤
│  核心层 (packages/dbgpt-core/src/dbgpt/)                    │
│  ├── agent/    - Multi-Agents 框架                          │
│  ├── rag/      - RAG 检索增强生成                            │
│  ├── model/    - 多模型管理 (SMMF)                          │
│  ├── datasource/ - 数据源连接器                             │
│  ├── train/    - 微调训练框架                               │
│  └── vis/      - 可视化组件                                 │
├─────────────────────────────────────────────────────────────┤
│  服务层 (packages/dbgpt-serve/)                             │
│  └── API 服务与部署                                          │
├─────────────────────────────────────────────────────────────┤
│  扩展层 (packages/dbgpt-ext/)                               │
│  └── 第三方扩展与插件                                        │
└─────────────────────────────────────────────────────────────┘
```

- 后端: Python 3.10+, FastAPI, SQLAlchemy, Alembic
- 前端: React/Vue (Web), 支持可视化对话界面
- LLM 集成: 支持 OpenAI、Azure、DeepSeek、Qwen、Llama、GLM 等 20+ 模型

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 5 | 模块化包设计、清晰的职责分离，可直接借鉴 |
| 代码复用 | 4 | 核心模块设计良好，部分代码可直接复用 |
| 集成潜力 | 3 | 作为完整框架较重，适合参考而非直接集成 |
| 学习价值 | 5 | 涵盖 Text-to-SQL 全流程，学术/工程价值高 |

### 4.1 值得借鉴的设计
- **模块化包结构**: dbgpt-core/app/serve/client/ext 的分层设计
- **SMMF 多模型管理**: 统一的模型接入抽象层
- **AWEL 工作流编排**: 声明式 Agent 工作流定义
- **RAG + Text-to-SQL 融合**: 知识库与 SQL 生成的协同
- **微调框架设计**: DB-GPT-Hub 的流水线式微调方案

### 4.2 可复用的代码/模块
- `packages/dbgpt-core/src/dbgpt/rag/` - RAG 框架实现
- `packages/dbgpt-core/src/dbgpt/agent/` - Agent 框架
- `packages/dbgpt-core/src/dbgpt/datasource/` - 数据源连接器
- `packages/dbgpt-ext/src/dbgpt_ext/rag/` - RAG 扩展组件

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| `packages/dbgpt-core/src/dbgpt/__init__.py` | 核心模块入口，定义懒加载机制 |
| `packages/dbgpt-core/src/dbgpt/rag/` | RAG 框架核心实现 |
| `packages/dbgpt-core/src/dbgpt/agent/` | Multi-Agent 框架 |
| `packages/dbgpt-core/src/dbgpt/datasource/` | 数据源连接器集合 |
| `packages/dbgpt-app/src/dbgpt_app/scene/` | 场景应用实现 |
| `examples/` | 使用示例与 Demo |
| `web/` | 前端 Web 界面 |

## 6. 优先级判定
- [x] 高优先级 - 重点研究
- [ ] 中优先级 - 参考借鉴
- [ ] 低优先级 - 了解即可

**推荐理由**:
1. **架构设计最佳实践**: 模块化包结构清晰，6 大核心包职责分明，非常适合作为中大型项目的架构参考
2. **技术覆盖面广**: 涵盖 Text-to-SQL、RAG、Agent、微调等全链路技术，一站式学习资源
3. **生态完善**: 子项目 DB-GPT-Hub 专注微调，dbgpts 提供算子市场，可借鉴生态建设思路
4. **中文友好**: 中文文档完善，社区活跃 (B站、Slack、Discord)
5. **工业级落地**: 支持 MCP 协议、私有化部署、多数据源接入，企业级特性完整
