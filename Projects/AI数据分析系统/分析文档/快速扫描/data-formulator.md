# Data Formulator - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | 微软研究院出品的 AI 驱动数据可视化工具，通过概念驱动的方式创建丰富图表，支持从数据提取到可视化生成的完整工作流 |
| Star/Fork | 14.8k / ~800 |
| 维护状态 | 活跃（最新版本 0.6，2025-01-25 发布） |
| 许可证 | MIT |

## 2. 核心能力速览
- **主要功能**:
  - 4级数据探索模式（UI拖拽 → NL+UI → AI推荐 → Agent自动探索）
  - 概念驱动可视化：通过拖拽字段架(Encoding Shelf)构建图表
  - AI Agent 数据转换：自动生成 Python/SQL 代码转换数据
  - 实时数据连接：支持 URL/数据库自动刷新
  - 多表联合分析：自动处理表关联
  - 报告生成：基于图表自动生成 Markdown 报告

- **技术亮点**:
  - 基于 Vega-Lite 的可视化引擎，支持 20+ 图表类型
  - 混合交互模式：UI + 自然语言无缝切换
  - DuckDB 大数据处理支持（内置本地数据库）
  - 数据锚定(Data Anchoring)机制管理分析分支

## 3. 架构概览
- **前端框架**: React 18 + TypeScript + Vite
- **UI 组件库**: Material-UI (MUI) v7 + Redux Toolkit 状态管理
- **可视化库**: Vega 6.2 + Vega-Lite 6.4.1 + vega-embed
- **AI 集成**: LiteLLM 统一接口，支持 OpenAI/Anthropic/Azure/Ollama
- **后端**: Python Flask + DuckDB
- **核心模块**:
  - `src/views/VisualizationView.tsx`: 可视化渲染核心
  - `src/components/ChartTemplates.tsx`: 图表模板定义
  - `py-src/agents/`: AI Agent 实现（探索/转换/清洗）

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 5 | React+Vega 架构成熟，多层级交互模式设计优秀 |
| 代码复用 | 3 | 前端图表模板可借鉴，但强耦合 MUI/Vega |
| 集成潜力 | 4 | Python 包形式易集成，提供 pip install 部署 |
| 学习价值 | 5 | 概念驱动可视化理念先进，AI Agent 设计模式值得学习 |

### 4.1 值得借鉴的设计
- **Encoding Shelf 模式**: 拖拽字段到可视化通道的设计，平衡了灵活性与易用性
- **多级探索模式**: Level 1-4 渐进式控制设计，满足不同用户需求
- **数据锚定机制**: 中间结果锚定避免重复计算，支持分析分支管理
- **AI 代码解释**: 自动生成并展示数据转换代码，增强可解释性

### 4.2 可复用的代码/模块
- `ChartTemplates.tsx`: 图表模板定义模式，支持自定义 postProcessor
- `agent_exploration.py`: Agent 探索决策逻辑，包含 present/continue 状态机
- Vega-Lite 图表装配逻辑 (`assembleVegaChart`)
- 数据采样与虚拟表处理机制

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| `src/views/VisualizationView.tsx` | 可视化渲染主组件，图表交互核心 |
| `src/components/ChartTemplates.tsx` | 20+ 图表类型模板定义 |
| `src/views/EncodingShelfThread.tsx` | 字段拖拽架组件 |
| `py-src/agents/agent_exploration.py` | AI 探索决策 Agent |
| `py-src/agents/agent_concept_derive.py` | 概念派生 Agent |
| `py-src/data_loader/` | 多数据源加载器（DB/S3/Blob） |
| `src/app/dfSlice.tsx` | Redux 状态管理定义 |

## 6. 优先级判定
- [x] 高优先级 - 重点研究

**推荐理由**:
1. **微软研究院背书**: 学术与工程结合，论文发表在 IEEE TVCG / ACL
2. **先进交互范式**: 概念驱动可视化 + 混合 UI/NL 交互是当前最佳实践
3. **完整数据工作流**: 从数据加载 → 转换 → 可视化 → 报告，闭环设计
4. **可扩展架构**: 插件式数据加载器、Agent 规则可配置
5. **开源友好**: MIT 协议，代码质量高，文档完善

---
**重点研究方向**:
- Encoding Shelf 交互模式在我们的产品中如何适配
- Agent 探索决策逻辑（何时呈现 vs 继续探索）
- Vega-Lite 图表模板化设计模式
