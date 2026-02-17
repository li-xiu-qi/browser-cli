# premsql - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | 端到端本地优先的 Text-to-SQL 库，支持小语言模型构建安全的数据库查询 |
| Star/Fork | 431 Star |
| 维护状态 | 中等活跃（PremAI 团队维护） |
| 许可证 | MIT License |

## 2. 核心能力速览
- 主要功能:
  - Text-to-SQL 生成（支持多种 LLM 后端）
  - 小语言模型微调（LoRA/QLoRA）
  - 端到端 Pipeline（Dataset + Generator + Executor + Evaluator）
  - Agent 框架（查询/分析/绘图）
  - Playground UI（Streamlit）
  - 执行引导解码（Execution Guided Decoding）
- 技术亮点:
  - 本地优先，支持 Prem-1B-SQL 小模型
  - 完整的 Text-to-SQL 评估体系
  - 支持多种 LLM 后端（OpenAI、Ollama、HuggingFace、MLX）

## 3. 架构概览
- 部署形态: Python 库 + Playground（Streamlit）
- 技术栈: 
  - 语言: Python 3.10+
  - 核心依赖: LangChain、SQLAlchemy、Transformers、FastAPI
  - UI: Streamlit
  - 后端: Django + DRF（Playground API）
- 数据库支持: SQLite、PostgreSQL、MySQL

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 4 | 端到端 Pipeline 设计完整，组件拆分清晰 |
| 代码复用 | 5 | Python 技术栈完全匹配，大量组件可直接使用 |
| 集成潜力 | 4 | MIT 协议，模块化设计易于集成 |
| 学习价值 | 4 | Text-to-SQL 微调、评估体系、Agent 设计 |

### 4.1 值得借鉴的设计
- 模块化组件设计（Generator/Executor/Evaluator/Tuner）
- 执行引导解码（Execution Guided Decoding）机制
- 错误数据集生成与自校正训练
- Agent 工作流（Text2SQL/Analyser/Plotter/Followup）
- 多 LLM 后端统一抽象层

### 4.2 可复用的代码/模块
- premsql/generators/ - Text-to-SQL 生成器（支持多种后端）
- premsql/executors/ - SQL 执行器（SQLite、LangChain）
- premsql/evaluator/ - 评估框架（Accuracy、VES）
- premsql/datasets/ - 数据集处理（Bird、Spider）
- premsql/agents/ - Agent 框架与工具
- premsql/tuner/ - 模型微调（LoRA/QLoRA）

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| pyproject.toml | Poetry 依赖配置 |
| premsql/generators/ | Text-to-SQL 生成器模块 |
| premsql/executors/ | SQL 执行器模块 |
| premsql/evaluator/ | 评估器模块 |
| premsql/agents/ | Agent 框架 |
| premsql/playground/ | Playground UI（Streamlit + Django） |
| premsql/datasets/ | 数据集处理 |

## 6. 优先级判定
- [x] 高优先级 - 重点研究
- [ ] 中优先级 - 参考借鉴
- [ ] 低优先级 - 了解即可

**推荐理由**: 
1. **技术栈完全匹配**：Python + LangChain + SQLAlchemy，代码复用价值极高
2. **模块化设计优秀**：Generator/Executor/Evaluator/Tuner/Agent 拆分清晰，易于按需集成
3. **Text-to-SQL 专业化**：专注 Text-to-SQL 领域，包含完整的训练和评估流程
4. **小模型支持**：支持 Prem-1B-SQL 等端侧小模型，适合私有化部署场景
5. **执行引导解码**：通过执行反馈循环优化 SQL 生成，提升准确率
6. **Agent 框架完整**：提供 BaselineAgent，支持查询、分析、绘图多功能组合
7. 虽然 Star 数较少（431），但代码质量高，专注领域明确，是值得深挖的宝藏项目
