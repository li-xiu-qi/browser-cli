# RAGFlow Agent 架构深度分析

> **分析日期**: 2026-02-05  
> **项目版本**: RAGFlow (最新主干版本)  
> **分析重点**: RAG 架构、超长文本上下文管理、Chunk 策略、检索与生成流程

---

## 1. 项目概述与核心特点

### 1.1 RAGFlow 定位

RAGFlow 是一个深度文档理解 + RAG (检索增强生成) 的开源框架，由 InfiniFlow 团队开发。与常规 RAG 框架相比，其核心优势在于：

| 特性 | RAGFlow 实现 | 传统 RAG |
|------|-------------|----------|
| **文档解析** | DeepDoc 深度解析，支持版面分析、表格识别、OCR | 简单文本提取 |
| **Chunk 策略** | 语义分块 + 重叠控制 + 层级结构 | 固定大小分块 |
| **上下文管理** | 动态 Token 预算 + 智能截断 | 静态截断 |
| **引用溯源** | 自动引用标注 + 混合相似度验证 | 简单来源标注 |
| **多模态支持** | 文本 + 图片 + 表格统一处理 | 仅文本 |

### 1.2 核心架构组件

![RAGFlow-核心流程图.svg](graphviz/RAGFlow-核心流程图.svg)

RAGFlow 采用分层架构设计：

1. **deepdoc/** - 文档解析层：PDF解析、OCR识别、表格提取、版面分析
2. **rag/** - RAG核心层：Chunk管理、向量检索、重排序、引用溯源
3. **agent/** - Agent编排层：Canvas工作流引擎、LLM组件、Retrieval组件
4. **api/** - 服务层：Conversation API、Dialog Service、Chunk API

---

## 2. RAG 架构设计

### 2.1 整体数据流架构

`
文档输入 → DeepDoc解析器 → Chunk分割器 → 向量嵌入 → 文档存储(ES/Infinity/OceanBase)
                                              ↑
查询理解 → 混合检索 → 重排序 → 引用标注 → 上下文组装 → LLM答案生成
`

### 2.2 混合检索策略

**关键代码位置**: 
ag/nlp/search.py:74-171

融合表达式定义：
- **全文检索权重**: 0.05
- **向量检索权重**: 0.95
- **自适应调整**: 当结果为空时，降低相似度阈值重试

### 2.3 重排序机制

**关键代码位置**: 
ag/nlp/search.py:294-331

混合相似度计算，结合向量相似度和关键词匹配分数。

---

## 3. Chunk 管理策略深度分析

### 3.1 Chunk 参数配置

**关键代码位置**: 
ag/flow/splitter/splitter.py:31-49

核心参数：
- chunk_token_size: 512 (默认 Chunk Token 大小)
- delimiters: [\n] (分隔符)
- overlapped_percent: 0 (重叠百分比)
- table_context_size: 0 (表格上下文大小)
- image_context_size: 0 (图片上下文大小)

### 3.2 分块策略详解

**关键代码位置**: 
ag/app/naive.py:737-824

Chunk 处理流程：
1. **文档解析**：提取原始文本，保持段落结构，识别版面元素
2. **初步分割**：按分隔符分割(换行符、标点符号)，保留句子完整性
3. **智能合并**：按 Token 预算合并，控制 Chunk 大小在限制内
4. **重叠处理**：相邻 Chunk 之间设置 overlapped_percent 重叠
5. **元数据附加**：文档名称、位置信息、标题标记、父 Chunk 引用

### 3.3 媒体上下文附加

**关键代码位置**: 
ag/nlp/__init__.py:409-704

ttach_media_context() 函数为表格/图片附加周围文本上下文：
- 按页码、顶部位置排序
- 为每个媒体块查找最近文本块
- 基于位置边界框匹配
- 收集上下文句子并合并到媒体块

---

## 4. 上下文窗口管理机制

### 4.1 Token 预算控制

**关键代码位置**: 
ag/prompts/generator.py:62-96

message_fit_in() 函数确保消息适合 LLM 上下文窗口：

1. **基础保留策略**：保留 system + 最后一条 user 消息
2. **按比例截断**：如果 system 占超过 80%，则截断 system
3. **编码器截断**：使用 encoder.decode(encoder.encode()) 精确截断

### 4.2 知识块 Prompt 组装

**关键代码位置**: 
ag/prompts/generator.py:99-143

kb_prompt() 函数按 Token 预算截断检索结果：
- 累加 Token 直到达到 max_tokens * 0.97
- 格式化引用信息(ID、Title、URL、Content)
- 添加文档元数据

### 4.3 动态上下文截断策略

输入: System Prompt + N 轮历史 + 当前 Query + 检索结果

步骤1: 基础保留策略
- 必须保留: System Prompt (如果超过 80% 则截断)
- 必须保留: 当前 User Query
- 可选保留: 历史对话 (优先保留最近轮次)

步骤2: 检索结果截断
- 按相似度排序 Chunk
- 累加 Token 直到达到预算上限
- 剩余 Chunk 丢弃

步骤3: LLM 调用配置
- 计算剩余可用 Token
- 设置 gen_conf max_tokens

---

## 5. 引用溯源机制深度分析

### 5.1 自动引用插入

**关键代码位置**: 
ag/nlp/search.py:177-265

insert_citations() 方法：
1. 将答案分割成句子
2. 过滤短句(长度小于5)
3. 计算答案片段与 Chunk 的混合相似度
4. 使用阈值(0.63)筛选引用，如失败则降低阈值重试
5. 插入 [ID:X] 引用标记

### 5.2 引用格式修复

**关键代码位置**: pi/db/services/dialog_service.py:238-272

处理多种引用格式变体，统一转换为 [ID:X] 格式。

---

## 6. 检索与生成完整流程

### 6.1 对话服务流程

**关键代码位置**: pi/db/services/dialog_service.py:275-582

sync_chat() 核心流程：
1. 获取模型配置(embedding、rerank、chat、tts)
2. 查询优化(多轮对话精炼)
3. 元数据过滤
4. 执行混合检索
5. 目录增强(可选)
6. 子 Chunk 检索
7. 组装 Prompt (带 Token 预算控制)
8. 生成答案(流式/非流式)

### 6.2 Agent Canvas 工作流

**关键代码位置**: gent/canvas.py:281-369

Canvas 类是 Agent 编排引擎：
- 管理全局变量(sys.query, sys.history 等)
- 执行组件流水线(DAG)
- 支持流式输出(Message 组件)
- 错误处理与分支跳转

### 6.3 Retrieval 组件

**关键代码位置**: gent/tools/retrieval.py:84-246

Retrieval 工具类实现知识库检索：
1. 获取嵌入模型和重排序模型
2. 元数据过滤
3. 跨语言处理(可选)
4. 执行检索
5. 目录增强(可选)
6. 父 Chunk 检索
7. 知识图谱检索(可选)

---

## 7. 超长文本处理策略

### 7.1 超长文档解析

**关键代码位置**: deepdoc/parser/pdf_parser.py:55-106

RAGFlowPdfParser 类支持分页处理大 PDF：
- OCR 识别
- 并行处理限制(asyncio.Semaphore)
- 版面识别(LayoutRecognizer)
- 表格结构识别(TableStructureRecognizer)

### 7.2 流式处理机制

**关键代码位置**: gent/component/llm.py:174-213

_generate_streamly() 方法处理流式输出：
- 处理 think 标签(Reasoning 模型)
- Delta 计算(增量输出)
- 错误处理与重试

---

## 8. 对我们项目的启示

### 8.1 可借鉴的设计模式

| RAGFlow 特性 | 借鉴价值 | 实施建议 |
|-------------|---------|---------|
| DeepDoc 解析 | 版面分析 + 表格识别 + OCR 一体化 | 集成 MinerU/Docling 进行深度解析 |
| 混合检索 | 全文(0.05) + 向量(0.95) 加权融合 | 实现 FusionExpr 融合表达式 |
| 动态截断 | 按比例保留 system/user 消息 | 实现 message_fit_in 机制 |
| 引用溯源 | 混合相似度自动标注 | 实现 insert_citations 方法 |
| Pipeline 编排 | Canvas 工作流引擎 | 设计类似的 DAG 执行引擎 |

### 8.2 上下文管理最佳实践

推荐实现 ContextManager 类：
- System 占用比例: 30%
- 历史对话占用比例: 20%
- 检索上下文占用比例: 50%
- 优先保证 query，按比例截断其他部分

### 8.3 Chunk 策略建议

推荐 Chunk 配置：
- chunk_token_size: 512
- overlapped_percent: 0.1 (10% 重叠)
- delimiters: 换行符、中文标点
- table_context_size: 128
- image_context_size: 64
- enable_hierarchical: True

### 8.4 检索优化建议

推荐检索流程：
1. 查询改写
2. 混合检索(向量+全文)
3. 融合(weighted_sum)
4. 重排序
5. 父 Chunk 扩展
6. 上下文组装(带 Token 预算)

---

## 9. 总结

### 9.1 RAGFlow 核心优势

1. **深度文档理解**: DeepDoc 提供业界领先的版面分析和表格识别
2. **精细 Chunk 管理**: 支持重叠、层级、媒体上下文等多种高级策略
3. **智能上下文管理**: 动态 Token 预算分配，最大化利用 LLM 窗口
4. **可信引用溯源**: 混合相似度验证的自动引用标注
5. **灵活 Agent 编排**: Canvas 工作流引擎支持复杂 RAG 流程

### 9.2 关键代码文件索引

| 功能模块 | 核心文件 | 关键行号 |
|---------|---------|---------|
| Chunk 分割 | rag/flow/splitter/splitter.py | 31-173 |
| 检索核心 | rag/nlp/search.py | 36-702 |
| 上下文管理 | rag/prompts/generator.py | 62-156 |
| 引用溯源 | rag/nlp/search.py | 177-265 |
| 对话服务 | api/db/services/dialog_service.py | 275-582 |
| Agent 编排 | agent/canvas.py | 281-369 |
| LLM 组件 | agent/component/llm.py | 82-351 |
| PDF 解析 | deepdoc/parser/pdf_parser.py | 55-300 |

---

*本分析文档由 AI 深度分析 RAGFlow 源码生成，用于 AI 数据分析系统架构参考。*
