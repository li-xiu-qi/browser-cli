# RATH - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | 自动化的增强分析工具，专注于数据模式自动发现、因果分析及可视化仪表盘生成 |
| Star/Fork | 4.6k / ~500 |
| 维护状态 | 活跃（Kanaries 团队主力产品，与 PyGWalker 同源） |
| 许可证 | AGPL 3.0 |

## 2. 核心能力速览
- **主要功能**:
  - AutoPilot：一键自动数据探索，发现模式与洞察
  - Copilot：半自动化探索，AI 学习用户意图并推荐
  - Data Painter：通过直接着色数据进行交互式分析
  - 因果分析：因果发现、图形模型编辑、What-if 分析
  - 自动化仪表盘：智能生成多维度可视化仪表盘
  - 数据整理：预测性转换操作推荐

- **技术亮点**:
  - 基于最小视觉感知误差生成可视化
  - 集成视觉洞察(Visual Insights)算法库
  - 自定义 Vega 渲染器（WebGL 加速）
  - 多数据源连接（20+ 数据库）

## 3. 架构概览
- **前端框架**: React 17 + TypeScript，MobX 状态管理
- **UI 组件库**: Fluent UI React（Microsoft 设计体系）
- **可视化引擎**: Vega 5.2 + Vega-Lite 5.6 + 自定义 vega-renderer
- **核心算法**: @kanaries/loa (Lineup Oriented Analytics) + visual-insights
- **微服务架构**: causal-service / connector / prediction / narrative 等 Python 服务
- **核心模块**:
  - `pages/megaAutomation/`: 全自动分析引擎
  - `pages/semiAutomation/`: 半自动 Copilot 模式
  - `pages/causal/`: 因果分析模块
  - `queries/distVis.ts`: 分布式可视化推荐

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 4 | 复杂应用架构，微服务设计，状态管理模式值得参考 |
| 代码复用 | 3 | 与 Graphic Walker 共享部分组件，但紧耦合 Kanaries 生态 |
| 集成潜力 | 2 | 完整应用形态，AGPL 协议限制商用集成 |
| 学习价值 | 5 | 自动化分析算法、可视化推荐逻辑、因果分析实现 |

### 4.1 值得借鉴的设计
- **自动可视化算法**: distVis/labDistVis 基于视觉感知误差最小化的推荐逻辑
- **双模式设计**: AutoPilot（全自动）vs Copilot（半自动）满足不同用户需求
- **Data Painter 交互**: 直接在数据上着色进行交互式探索的创新模式
- **因果分析工作流**: 因果发现 → 模型编辑 → What-if 分析的完整链条
- **主题系统**: 内置 Excel/ggplot2/Tableau 等多种可视化主题

### 4.2 可复用的代码/模块
- `queries/distVis.ts`: 自动可视化推荐核心算法
- `queries/distribution/bot.ts`: 自动标记/统计/编码逻辑
- `pages/semiAutomation/autoVis.ts`: 半自动可视化状态管理
- `store/semiAutomation/`: MobX 状态管理模式
- `workers/`: Web Worker 计算密集型任务处理

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| `packages/rath-client/src/queries/distVis.ts` | 自动可视化推荐入口 |
| `packages/rath-client/src/queries/distribution/bot.ts` | 图表类型自动选择算法 |
| `packages/rath-client/src/pages/megaAutomation/index.tsx` | 全自动分析模式主组件 |
| `packages/rath-client/src/pages/semiAutomation/autoVis.ts` | 半自动可视化逻辑 |
| `packages/rath-client/src/pages/painter/index.tsx` | Data Painter 交互组件 |
| `packages/rath-client/src/pages/causal/index.tsx` | 因果分析模块 |
| `services/causal-service/`| 因果分析 Python 微服务 |
| `services/connector/`| 数据库连接微服务 |

## 6. 优先级判定
- [ ] 高优先级 - 重点研究
- [x] 中优先级 - 参考借鉴
- [ ] 低优先级 - 了解即可

**推荐理由**:
1. **算法先进**: 自动化可视化和因果分析算法有学术深度
2. **产品创新**: Data Painter 等交互创新值得关注
3. **架构完整**: 复杂数据分析应用的架构设计参考

**局限性**:
- AGPL 协议限制（开源传染性）
- 与 PyGWalker 存在功能重叠，但后者集成更友好
- 架构较重，微服务模式对小项目可能过度设计

---
**重点研究方向**:
- 自动可视化推荐算法（distVis 实现逻辑）
- AutoPilot vs Copilot 双模式的产品设计权衡
- Data Painter 的交互创新模式
- 因果分析的可视化呈现方式

---
**与 PyGWalker 关系说明**:
RATH 和 PyGWalker 同属 Kanaries 团队，RATH 是完整的分析应用（AGPL），PyGWalker 是可复用的组件（Apache）。建议优先研究 PyGWalker 的架构，RATH 作为算法参考。
