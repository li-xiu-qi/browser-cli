# Evidence - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | 代码优先的 BI 框架，用 SQL 和 Markdown 构建数据产品和仪表盘 |
| Star/Fork | 5.9k Star / 稳定增长 |
| 维护状态 | 活跃 (Evidence Studio 商业化推进中) |
| 许可证 | MIT |

## 2. 核心能力速览
- 主要功能:
  - Markdown 中嵌入 SQL 查询语句
  - 自动生成数据可视化组件
  - 模板化页面生成 (多维度数据展示)
  - 支持条件渲染与循环控制
  - 多种数据源连接器 (DuckDB、Postgres、Snowflake 等)
- 技术亮点:
  - Svelte 响应式前端框架
  - Universal SQL (USQL) 跨数据源抽象
  - Apache Arrow + Parquet 高性能数据格式
  - ECharts 深度集成可视化

## 3. 架构概览
- 核心抽象:
  - **Markdown + SQL**: 文档即数据源，SQL 即查询语言
  - **USQL (Universal SQL)**: 统一的数据查询抽象层
  - **DataSource Connectors**: 多数据源适配器 (15+ 类型)
  - **Component System**: Svelte 组件化可视化
  - **Build System**: 基于 Vite 的静态站点生成
  
- 数据处理流程:
  ```
  Markdown 文件 → 提取 SQL → 数据源查询 → Arrow/Parquet 转换 
  → DuckDB 缓存 → 前端 Store → Svelte 组件渲染
  ```
  
- 输出格式:
  - 静态网站 (HTML/CSS/JS)
  - 响应式仪表盘
  - 可交互图表 (ECharts)
  - 数据表格

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 3 | 前端架构差异较大，但数据流设计有参考价值 |
| 代码复用 | 2 | 技术栈不同 (Node.js vs Python)，难以直接复用 |
| 集成潜力 | 3 | 可作为前端展示层参考，或集成为报表模块 |
| 学习价值 | 4 | SQL 优先的 BI 设计理念、组件化可视化思路值得学习 |

### 4.1 值得借鉴的设计
1. **SQL + Markdown 融合**: 文档与数据查询的无缝结合，降低 BI 报告编写门槛
2. **Universal SQL 抽象**: 统一的数据查询层屏蔽底层数据源差异
3. **Apache Arrow + Parquet**: 高性能列式数据存储与传输格式选择
4. **响应式数据流**: Svelte Store + 查询缓存的响应式数据更新机制
5. **组件化可视化**: 预置图表组件 + ECharts 深度定制

### 4.2 可复用的代码/模块
- `packages/lib/universal-sql/src/build-parquet.js`: Parquet 构建逻辑
- `packages/lib/component-utilities/src/echarts.js`: ECharts 封装
- `packages/lib/component-utilities/src/buildQuery.js`: 查询构建逻辑
- `packages/datasources/`: 数据源连接器设计模式

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| packages/lib/universal-sql/src/build-parquet.js | Arrow/Parquet 数据转换 |
| packages/lib/universal-sql/src/client-duckdb/ | DuckDB 客户端封装 |
| packages/lib/component-utilities/src/buildQuery.js | SQL 查询构建器 |
| packages/lib/component-utilities/src/echarts.js | ECharts 图表封装 |
| packages/datasources/*/index.js | 各数据源连接器 |
| packages/ui/core-components/ | 核心可视化组件 |

## 6. 优先级判定
- [ ] 高优先级 - 重点研究
- [x] 中优先级 - 参考借鉴
- [ ] 低优先级 - 了解即可

**推荐理由**:
1. **SQL 优先的 BI 理念**: "Code-first BI" 的设计思路对构建数据报告功能有启发意义
2. **可视化组件设计**: ECharts 集成、响应式图表等实现可作为前端展示层参考
3. **数据格式选择**: Arrow + Parquet 的高性能数据方案值得考虑
4. **局限性**: 项目基于 Node.js/Svelte 技术栈，与我们的 Python 后端架构差异较大，难以深度集成

**建议关注领域**:
- 可视化组件设计与交互模式
- 数据源抽象与连接层设计
- 查询缓存与响应式更新机制
