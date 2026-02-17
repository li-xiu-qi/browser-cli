# WrenAI - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | 主打语义建模层 (MDL) 的 GenBI AI 引擎，解决复杂多表关联查询 |
| Star/Fork | 13.8k / 1k+ |
| 维护状态 | 活跃 (开源 + 商业云服务并行) |
| 许可证 | AGPL-3.0 (开源) |

## 2. 核心能力速览
- 主要功能:
  - 语义建模层 (MDL) 定义 schema、metrics、joins
  - 自然语言 → 精确 SQL → 图表/报告
  - GenBI 洞察生成 (AI 撰写的摘要、图表)
  - API 嵌入能力 (支持 Streamlit 等)
  - 支持 12+ 数据源
- 技术亮点:
  - 语义引擎设计：将业务语义与物理 schema 分离
  - Haystack + Hamilton 构建的 Pipeline 架构
  - 支持计算字段、指标定义、JSON 字段处理

## 3. 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    WrenAI 架构                               │
├─────────────────────────────────────────────────────────────┤
│  前端层 (wren-ui/)                                           │
│  ├── Next.js + TypeScript                                   │
│  ├── Apollo GraphQL Client/Server                           │
│  └── 组件: 图表、代码、数据预览、模型编辑器                    │
├─────────────────────────────────────────────────────────────┤
│  API 层 (wren-ai-service/src/web/)                          │
│  └── v1/ - RESTful API 端点                                 │
├─────────────────────────────────────────────────────────────┤
│  Pipeline 层 (wren-ai-service/src/pipelines/)               │
│  ├── indexing/     - 元数据索引                              │
│  ├── retrieval/    - 检索 (sql_functions, sql_knowledge)    │
│  └── generation/   - 生成 (sql_generation, chart...)        │
├─────────────────────────────────────────────────────────────┤
│  核心层 (wren-ai-service/src/core/)                         │
│  ├── engine/       - 执行引擎                                │
│  └── pipeline/     - Pipeline 抽象                           │
├─────────────────────────────────────────────────────────────┤
│  Provider 层 (wren-ai-service/src/providers/)               │
│  ├── llm/          - LLM 提供商集成                          │
│  ├── embedder/     - 嵌入模型                                │
│  ├── document_store/ - Qdrant 向量存储                      │
│  └── engine/       - 查询引擎                                │
├─────────────────────────────────────────────────────────────┤
│  语义层 (wren-mdl/)                                         │
│  └── MDL (Model Definition Language) - 语义模型定义          │
├─────────────────────────────────────────────────────────────┤
│  引擎层 (wren-engine/)                                      │
│  └── 查询执行与优化                                          │
└─────────────────────────────────────────────────────────────┘
```

- 后端: Python 3.12, FastAPI, Haystack 2.7, Hamilton, Poetry
- 前端: Next.js, TypeScript, Apollo GraphQL
- LLM 集成: OpenAI, Azure, DeepSeek, Gemini, Anthropic, Bedrock, Ollama 等

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 5 | Pipeline + Provider 架构设计优秀 |
| 代码复用 | 3 | AGPL 许可证限制，代码不能直接复用 |
| 集成潜力 | 3 | 可作为独立服务部署，API 调用 |
| 学习价值 | 5 | 语义层设计、Pipeline 架构、MDL 思想 |

### 4.1 值得借鉴的设计
- **MDL 语义建模层**: 将业务语义 (metrics、dimensions) 与物理 schema 解耦
- **Haystack + Hamilton Pipeline**: 声明式 Pipeline 构建，便于测试和可视化
- **分层 Provider 设计**: llm/embedder/document_store/engine 四层抽象
- **SQL 生成后处理**: SQLGenPostProcessor 的校验与优化逻辑
- **Langfuse 可观测性**: 内置追踪与成本统计

### 4.2 可学习的代码/模块 (注意 AGPL 许可)
- `wren-ai-service/src/pipelines/generation/sql_generation.py` - SQL 生成 Pipeline
- `wren-ai-service/src/pipelines/retrieval/` - 检索逻辑
- `wren-ai-service/src/providers/` - Provider 抽象设计
- `wren-mdl/` - MDL 语义模型定义
- `wren-ui/src/components/chart/` - 图表组件设计

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| `wren-ai-service/src/pipelines/generation/sql_generation.py` | SQL 生成 Pipeline |
| `wren-ai-service/src/pipelines/generation/utils/sql.py` | SQL 生成工具函数 |
| `wren-ai-service/src/providers/llm/` | LLM Provider 实现 |
| `wren-ai-service/src/core/pipeline.py` | Pipeline 抽象基类 |
| `wren-mdl/` | MDL 语义建模层 |
| `wren-ui/src/components/` | UI 组件集合 |
| `wren-ai-service/pyproject.toml` | 依赖配置 (Haystack, Hamilton, Qdrant) |
| `wren-ai-service/docs/config_examples/` | LLM 配置示例 |

## 6. 优先级判定
- [x] 高优先级 - 重点研究
- [ ] 中优先级 - 参考借鉴
- [ ] 低优先级 - 了解即可

**推荐理由**:
1. **独特的语义层设计**: MDL (Model Definition Language) 是核心差异化能力，将业务语义与物理表结构解耦，大幅提升复杂查询准确率
2. **Pipeline 架构最佳实践**: Haystack + Hamilton 的组合是现代化 AI Pipeline 的优秀范例，可观测性好、易于测试
3. **技术栈先进**: Python 3.12、Poetry、Pydantic v2、Haystack 2.x，技术选型前卫
4. **企业级完整**: 从语义建模到图表生成的完整 GenBI 闭环
5. **⚠️ 许可证限制**: AGPL-3.0 意味着直接复用代码需要开源衍生作品，建议学习设计理念而非直接复用代码
6. **架构参考重点**:
   - MDL 语义层设计思想
   - Pipeline 编排模式
   - Provider 分层抽象
   - 后处理校验机制
