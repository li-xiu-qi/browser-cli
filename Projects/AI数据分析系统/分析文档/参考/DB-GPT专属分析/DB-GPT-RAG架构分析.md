# DB-GPT RAG 架构分析

**分析日期**: 2026-02-05  
**分析版本**: DB-GPT v0.6.x  
**分析范围**: RAG/检索/知识库架构

---

## 1. RAG 架构总览

### 1.1 核心架构设计

DB-GPT 的 RAG 架构采用**分层模块化设计**，核心分为以下几层：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        应用层 (Application)                         │
│         Chat UI / API / Agent / Data Analysis                       │
├─────────────────────────────────────────────────────────────────────┤
│                        检索层 (Retriever)                           │
│    ┌──────────────┬──────────────┬──────────────┬──────────────┐   │
│    │  Embedding   │    BM25      │    Graph     │   Hybrid     │   │
│    │  Retriever   │  Retriever   │  Retriever   │  Retriever   │   │
│    └──────────────┴──────────────┴──────────────┴──────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        存储层 (Storage)                             │
│    ┌──────────────┬──────────────┬──────────────┬──────────────┐   │
│    │    Chroma    │    Milvus    │ Elasticsearch│   TuGraph    │   │
│    │  VectorStore │  VectorStore │  VectorStore │   Graph DB   │   │
│    └──────────────┴──────────────┴──────────────┴──────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        处理层 (Processor)                           │
│    ┌──────────────┬──────────────┬──────────────┬──────────────┐   │
│    │ TextSplitter │   Embedder   │   ReRanker   │Query Rewrite │   │
│    └──────────────┴──────────────┴──────────────┴──────────────┘   │
├─────────────────────────────────────────────────────────────────────┤
│                        数据源层 (Data Source)                       │
│    ┌──────────┬──────────┬──────────┬──────────┬──────────┐        │
│    │   PDF    │   DOCX   │   CSV    │ Database │   URL    │        │
│    └──────────┴──────────┴──────────┴──────────┴──────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心组件位置

| 组件 | 核心路径 |
|------|----------|
| RAG 核心 | `packages/dbgpt-core/src/dbgpt/rag/` |
| RAG 扩展 | `packages/dbgpt-ext/src/dbgpt_ext/rag/` |
| 向量存储 | `packages/dbgpt-ext/src/dbgpt_ext/storage/vector_store/` |
| 知识图谱 | `packages/dbgpt-ext/src/dbgpt_ext/storage/knowledge_graph/` |
| 嵌入模型 | `packages/dbgpt-core/src/dbgpt/rag/embedding/` |

### 1.3 Assembler 模式

DB-GPT 采用 **Assembler（装配器）模式** 作为 RAG 管道的核心抽象：

- **EmbeddingAssembler**: 向量检索装配器
- **BM25Assembler**: 全文检索装配器
- **SummaryAssembler**: 摘要生成装配器
- **DBSchemaAssembler**: 数据库结构装配器

Assembler 负责协调：
1. 知识加载 (Knowledge Loading)
2. 文本分块 (Text Splitting)
3. 嵌入生成 (Embedding)
4. 存储持久化 (Persistence)
5. 检索器创建 (Retriever Creation)

---

## 2. 向量存储和检索

### 2.1 支持的向量数据库

| 数据库 | 实现文件 | 特点 |
|--------|----------|------|
| **Chroma** | `chroma_store.py` | 本地嵌入式，轻量级，适合开发测试 |
| **Milvus** | `milvus_store.py` | 企业级，分布式，支持混合检索 |
| **Elasticsearch** | `elastic_store.py` | 支持向量+全文混合检索 |
| **Weaviate** | `weaviate_store.py` | GraphQL接口，多模态支持 |
| **OceanBase** | `oceanbase_store.py` | 国产分布式数据库 |
| **PGVector** | `pgvector_store.py` | PostgreSQL 扩展 |

### 2.2 向量存储基类设计

```python
class VectorStoreBase(IndexStoreBase, ABC):
    """向量存储基类"""
    
    @abstractmethod
    def similar_search(self, text, topk, filters) -> List[Chunk]:
        """相似度搜索"""
        
    @abstractmethod
    def similar_search_with_scores(self, text, topk, score_threshold, filters) -> List[Chunk]:
        """带分数的相似度搜索"""
        
    def filter_by_score_threshold(self, chunks, score_threshold) -> List[Chunk]:
        """按分数阈值过滤"""
```

### 2.3 Milvus 详细实现

Milvus 是 DB-GPT 的主力向量数据库，支持以下特性：

**索引配置**:
```python
self.index_params = {
    "index_type": "HNSW",      # HNSW 图索引
    "metric_type": "COSINE",   # 余弦相似度
}

# 支持的索引类型
self.index_params_map = {
    "IVF_FLAT": {"params": {"nprobe": 10}},
    "IVF_SQ8": {"params": {"nprobe": 10}},
    "HNSW": {"params": {"M": 8, "efConstruction": 64}},
    "ANNOY": {"params": {"search_k": 10}},
}
```

**混合检索支持** (Milvus 2.5.0+):
```python
def full_text_search(self, text: str, topk: int = 10) -> List[Chunk]:
    # 使用 BM25 稀疏向量进行全文检索
    results = self._milvus_client.search(
        anns_field=self.sparse_vector,
        metric_type="BM25",
    )
```

### 2.4 检索策略

**RetrieverStrategy 枚举**:
```python
class RetrieverStrategy(str, Enum):
    EMBEDDING = "embedding"    # 向量检索
    SEMANTIC = "semantic"      # 语义检索
    GRAPH = "graph"            # 图谱检索
    Tree = "tree"              # 树形检索
    KEYWORD = "keyword"        # 关键词检索
    HYBRID = "hybrid"          # 混合检索
```

### 2.5 ReRank 机制

DB-GPT 支持多种 ReRank 策略：

| ReRanker | 说明 | 适用场景 |
|----------|------|----------|
| **DefaultRanker** | 按分数排序 | 基础排序 |
| **CrossEncoderRanker** | 交叉编码器重排 | 高精度需求 |
| **RerankEmbeddingsRanker** | 嵌入重排 | 延迟敏感 |
| **RRFRanker** | 倒数排序融合 | 多路召回融合 |

**CrossEncoder 重排示例**:
```python
ranker = CrossEncoderRanker(
    topk=4,
    model="BAAI/bge-reranker-base",
    device="cpu"
)
# 对候选结果进行重排序
reranked_chunks = ranker.rank(candidates, query)
```

### 2.6 查询重写 (Query Rewrite)

```python
class QueryRewrite:
    """查询重写 - 生成多个相关搜索查询"""
    
    async def rewrite(
        self, 
        origin_query: str, 
        context: Optional[str], 
        nums: int = 1
    ) -> List[str]:
        # 基于 LLM 生成多个相关查询变体
        # 支持中英文
```

---

## 3. 文档处理流程

### 3.1 支持的文档类型

| 类型 | 处理器 | 说明 |
|------|--------|------|
| PDF | `PDFKnowledge` | PyPDF2/PDFMiner 解析 |
| Word (.docx) | `DocxKnowledge` | python-docx |
| Word (.doc) | `Word97DocKnowledge` | olefile 解析旧格式 |
| Excel | `ExcelKnowledge` | pandas/openpyxl |
| CSV | `CSVKnowledge` | pandas |
| Markdown | `MarkdownKnowledge` | 保留标题结构 |
| HTML | `HTMLKnowledge` | BeautifulSoup |
| PPT | `PPTXKnowledge` | python-pptx |
| 数据库 | `DatasourceKnowledge` | SQL 元数据 |
| URL | `URLKnowledge` | 网页抓取 |

### 3.2 Knowledge Factory 模式

```python
# 统一的知识创建工厂
knowledge = KnowledgeFactory.create(
    datasource="path/to/document.pdf",
    knowledge_type=KnowledgeType.DOCUMENT
)
```

### 3.3 文本分块策略

**ChunkStrategy 枚举**:

| 策略 | 分词器 | 特点 |
|------|--------|------|
| **CHUNK_BY_SIZE** | `RecursiveCharacterTextSplitter` | 递归字符分块，默认策略 |
| **CHUNK_BY_PAGE** | `PageTextSplitter` | 按页分块 |
| **CHUNK_BY_PARAGRAPH** | `ParagraphTextSplitter` | 按段落分块 |
| **CHUNK_BY_SEPARATOR** | `SeparatorTextSplitter` | 按分隔符分块 |
| **CHUNK_BY_MARKDOWN_HEADER** | `MarkdownHeaderTextSplitter` | Markdown 标题分块 |

**RecursiveCharacterTextSplitter 实现**:
```python
class RecursiveCharacterTextSplitter(TextSplitter):
    def __init__(self, separators=None, **kwargs):
        self._separators = separators or ["###", "\n", " ", ""]
        
    def split_text(self, text: str) -> List[str]:
        # 1. 按优先级尝试不同的分隔符
        # 2. 对超长块递归分割
        # 3. 合并小块达到目标大小
```

### 3.4 元数据过滤

```python
class MetadataFilters(BaseModel):
    condition: FilterCondition = FilterCondition.AND
    filters: List[MetadataFilter]

class MetadataFilter(BaseModel):
    key: str
    operator: FilterOperator  # EQ, GT, LT, IN, etc.
    value: Union[str, int, float, List]
```

---

## 4. 数据源接入

### 4.1 数据库元数据接入

**DatasourceKnowledge** 专门处理数据库接入：

```python
class DatasourceKnowledge(Knowledge):
    def __init__(self, connector: BaseConnector, ...):
        # 通过数据库连接器获取元数据
        
    def _load(self) -> List[Document]:
        # 生成表结构摘要
        # 字段信息 + 样本数据
```

**数据库摘要格式**:
```
Table: users
Columns:
- id (INT, PK)
- name (VARCHAR(100))
- email (VARCHAR(255))
Sample: 1000 rows, created 2024-01
```

### 4.2 多数据源 RAG

DB-GPT 支持同时接入多种数据源：

1. **文件知识库**: PDF, Word, Excel 等文档
2. **数据库元数据**: 表结构、字段信息
3. **URL/网页**: 网页内容抓取
4. **文本**: 直接文本输入

### 4.3 数据管道

```
Raw Data → Knowledge → TextSplitter → Chunk → Embedding → VectorStore
                ↓
         DatasourceKnowledge (数据库)
                ↓
         Document → DBSchema Summary → VectorStore
```

---

## 5. GraphRAG 高级特性

### 5.1 知识图谱架构

DB-GPT 内置完整的 **GraphRAG** 实现：

```
┌────────────────────────────────────────────────────────────┐
│                     GraphRAG 架构                          │
├────────────────────────────────────────────────────────────┤
│  图存储层: TuGraph / Neo4j / MemGraph                     │
├────────────────────────────────────────────────────────────┤
│  图谱构建层                                                │
│  ├─ TripletExtractor: 从文本抽取 (subject, relation, object) │
│  ├─ KeywordExtractor: 关键词提取                           │
│  └─ CommunitySummarizer: 社区摘要                          │
├────────────────────────────────────────────────────────────┤
│  图谱检索层                                                │
│  ├─ KeywordBasedGraphRetriever: 基于关键词检索             │
│  ├─ VectorBasedGraphRetriever: 基于向量检索                │
│  ├─ TextBasedGraphRetriever: 基于 Text2GQL 检索            │
│  └─ DocumentGraphRetriever: 文档图检索                     │
└────────────────────────────────────────────────────────────┘
```

### 5.2 图谱构建流程

```python
class BuiltinKnowledgeGraph(KnowledgeGraphBase):
    def load_document(self, chunks: List[Chunk]) -> List[str]:
        # 1. 对每个 Chunk 提取三元组
        triplets = await self._triplet_extractor.extract(chunk.content)
        # 2. 插入图数据库
        for triplet in triplets:
            self._graph_store_adapter.insert_triplet(*triplet)
```

### 5.3 图谱检索策略

**GraphRetriever** 支持多种检索方式：

| 检索器 | 方式 | 说明 |
|--------|------|------|
| **KeywordBased** | 关键词匹配 | 使用提取的关键词搜索实体 |
| **VectorBased** | 向量相似度 | 实体/关系的向量表示 |
| **TextBased** | Text2GQL | LLM 生成图查询语言 |
| **DocumentBased** | 文档图 | 基于文档结构的图 |

**Text2GQL (Text to Graph Query Language)**:
```python
# 支持自然语言转图查询
class Text2GQL:
    async def generate(self, question: str) -> str:
        # 生成如: MATCH (n:Entity)-[r]->(m) WHERE n.name = 'xxx'
```

### 5.4 图谱存储适配器

支持多种图数据库：
- **TuGraph**: 蚂蚁开源高性能图数据库
- **Neo4j**: 最流行的图数据库
- **MemGraph**: 内存优先图数据库

---

## 6. 与 RAGFlow RAG 的对比

### 6.1 架构对比

| 维度 | DB-GPT | RAGFlow |
|------|--------|---------|
| **核心定位** | AI 数据库 + RAG 平台 | 深度文档理解 RAG |
| **架构风格** | 模块化、插件化 | 一体化、Pipeline |
| **Agent 支持** | 内置多 Agent 框架 | 有限 |
| **数据库集成** | 深度集成，支持 Text2SQL | 基础支持 |
| **GraphRAG** | 完整实现 | 基础支持 |

### 6.2 文档处理能力对比

| 特性 | DB-GPT | RAGFlow |
|------|--------|---------|
| DeepDoc (深度解析) |  |  |
| 表格识别 | 基础 | 增强 |
| 版面分析 | 基础 | 深度 |
| OCR | 支持 | 增强 |
| 多格式支持 | 10+ | 20+ |

### 6.3 检索能力对比

| 特性 | DB-GPT | RAGFlow |
|------|--------|---------|
| 向量检索 |  |  |
| 全文检索 (BM25) |  |  |
| 混合检索 |  |  |
| 多路召回 |  |  |
| ReRank | 4种 | 2种 |
| 查询重写 |  |  |
| 知识图谱检索 | 完整 | 基础 |

### 6.4 向量数据库对比

| 数据库 | DB-GPT | RAGFlow |
|--------|--------|---------|
| Chroma |  |  |
| Milvus |  |  |
| Elasticsearch |  |  |
| Infinity |  |  |
| Redis |  |  |
| PostgreSQL |  |  |

### 6.5 嵌入模型支持

| 类型 | DB-GPT | RAGFlow |
|------|--------|---------|
| HuggingFace |  |  |
| OpenAI |  |  |
| 本地部署 |  |  |
| 重排模型 | 4种 | 2种 |

### 6.6 优势对比总结

**DB-GPT 优势**:
1. **数据库原生集成**: Text2SQL、数据对话是核心能力
2. **Agent 生态**: 完整的 Agent 框架和工具链
3. **知识图谱**: 完整的 GraphRAG 实现
4. **灵活扩展**: 高度模块化的架构
5. **企业级**: 权限、审计、多租户支持

**RAGFlow 优势**:
1. **文档解析**: DeepDoc 的文档理解能力更强
2. **开箱即用**: 预配置更完善，上手更简单
3. **检索效果**: 在复杂文档场景下效果可能更好
4. **社区活跃度**: 文档和社区支持更丰富

### 6.7 适用场景建议

| 场景 | 推荐方案 |
|------|----------|
| 企业知识库 + 数据分析 | **DB-GPT** |
| 复杂文档理解 (论文、财报) | **RAGFlow** |
| Text2SQL/数据对话 | **DB-GPT** |
| 快速原型验证 | **RAGFlow** |
| 需要 GraphRAG | **DB-GPT** |
| 需要多 Agent 协作 | **DB-GPT** |

---

## 7. 代码结构总结

### 7.1 核心目录结构

```
db-gpt/packages/
├── dbgpt-core/src/dbgpt/
│   ├── rag/
│   │   ├── embedding/          # 嵌入模型接口
│   │   ├── knowledge/          # 知识基类
│   │   ├── retriever/          # 检索器基类
│   │   ├── text_splitter/      # 文本分块
│   │   └── transformer/        # 转换器（关键词提取等）
│   └── storage/
│       ├── vector_store/       # 向量存储基类
│       └── knowledge_graph/    # 知识图谱基类
│
└── dbgpt-ext/src/dbgpt_ext/
    ├── rag/
    │   ├── assembler/          # 装配器实现
    │   ├── knowledge/          # 各种知识类型实现
    │   ├── retriever/          # 检索器实现
    │   │   └── graph_retriever/# 图谱检索器
    │   └── transformer/        # 图谱转换器
    └── storage/
        ├── vector_store/       # 各向量数据库实现
        └── knowledge_graph/    # 图谱存储实现
```

### 7.2 扩展机制

DB-GPT 使用 **Factory 模式** 实现插件化扩展：

- `KnowledgeFactory`: 知识类型扩展
- `GraphStoreFactory`: 图数据库扩展
- `VectorStoreFactory`: 向量数据库扩展
- `GraphStoreAdapterFactory`: 图存储适配器扩展

---

## 8. 关键配置参数

### 8.1 向量检索参数

```python
# Embedding 配置
EMBEDDING_MODEL = "text2vec"  # 或其他 HuggingFace 模型
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOP_K = 4
SCORE_THRESHOLD = 0.3

# Milvus 配置
MILVUS_URL = "localhost"
MILVUS_PORT = "19530"
INDEX_TYPE = "HNSW"
METRIC_TYPE = "COSINE"
```

### 8.2 GraphRAG 参数

```python
# 图谱构建
TRIPLET_GRAPH_ENABLED = True
DOCUMENT_GRAPH_ENABLED = True
KNOWLEDGE_GRAPH_EXTRACT_SEARCH_TOP_SIZE = 5

# 图谱检索
KNOWLEDGE_GRAPH_CHUNK_SEARCH_TOP_SIZE = 5
KNOWLEDGE_GRAPH_SIMILARITY_SEARCH_TOP_SIZE = 5
KNOWLEDGE_GRAPH_EXTRACT_SEARCH_RECALL_SCORE = 0.7

# Text2GQL
TEXT2GQL_MODEL_ENABLED = False
TEXT2GQL_MODEL_NAME = "your-model"
```

---

## 9. 总结

DB-GPT 的 RAG 架构设计特点：

1. **高度模块化**: 分层清晰，组件可插拔
2. **多存储支持**: 6+ 向量数据库，3+ 图数据库
3. **完整 GraphRAG**: 从构建到检索的完整链路
4. **数据库原生**: 深度集成 SQL/数据库能力
5. **企业级**: 支持权限、审计、多租户
6. **可扩展**: Factory 模式便于扩展

与 RAGFlow 相比，DB-GPT 更适合需要 **数据库集成** 和 **Agent 能力** 的企业级场景，而 RAGFlow 更适合需要 **深度文档理解** 的场景。
