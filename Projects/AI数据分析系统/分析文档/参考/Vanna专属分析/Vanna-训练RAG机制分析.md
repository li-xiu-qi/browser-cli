# Vanna 训练（Training）与 RAG 机制深度分析

> **文档版本**: 1.0  
> **分析日期**: 2026-02-05  
> **分析对象**: Vanna v0.7.x 版本代码库

---

## 1. 训练机制总览

### 1.1 核心设计思想

Vanna 的训练机制采用**三层数据融合策略**，让 LLM 能够理解特定数据库的结构和业务语义：

```
┌─────────────────────────────────────────────────────────────┐
│                    Vanna 训练数据层                          │
├──────────────┬──────────────┬───────────────────────────────┤
│   DDL 层     │  SQL示例层    │      文档层                  │
│  (结构)      │  (模式)       │     (语义)                   │
├──────────────┼──────────────┼───────────────────────────────┤
│ CREATE TABLE │ Q: 销售额?   │ 业务术语解释                  │
│ 语句         │ S: SELECT... │ 表关系说明                    │
│ 表结构定义   │ 问答对       │ 计算口径                      │
└──────────────┴──────────────┴───────────────────────────────┘
```

### 1.2 训练数据类型

| 数据类型 | 存储内容 | 向量化对象 | 用途 |
|---------|---------|-----------|------|
| **DDL** | CREATE TABLE/VIEW 语句 | DDL 文本本身 | 提供表结构、字段类型、约束信息 |
| **SQL示例** | 问题-SQL 问答对 | `question + sql` JSON | 提供问题到 SQL 的映射模式 |
| **Documentation** | 业务文档、表说明 | 文档文本 | 提供业务语义、计算逻辑 |

### 1.3 核心训练 API

```python
# VannaBase 抽象基类定义的训练接口
class VannaBase(ABC):
    @abstractmethod
    def add_question_sql(self, question: str, sql: str) -> str:
        """添加问题-SQL 对到向量存储"""
        pass
    
    @abstractmethod
    def add_ddl(self, ddl: str) -> str:
        """添加 DDL 语句到向量存储"""
        pass
    
    @abstractmethod
    def add_documentation(self, documentation: str) -> str:
        """添加文档到向量存储"""
        pass
```

---

## 2. 自动训练流程

### 2.1 自动训练入口

Vanna 提供 `train()` 方法作为统一训练入口，支持多种训练模式：

```python
def train(
    self,
    question: str = None,
    sql: str = None,
    ddl: str = None,
    documentation: str = None,
    plan: TrainingPlan = None,
):
    """
    训练模式优先级：
    1. documentation → 直接添加文档
    2. sql (+ question) → 添加问答对（question 可自动生成）
    3. ddl → 添加 DDL
    4. plan → 批量执行训练计划
    5. 无参数 → 尝试从连接的数据库自动提取元数据
    """
```

### 2.2 数据库元数据自动提取

Vanna 支持从连接的数据库自动提取训练数据：

```python
# Snowflake 自动训练计划示例
def get_training_plan_snowflake(
    self,
    filter_databases: List[str] = None,
    filter_schemas: List[str] = None,
    include_information_schema: bool = False,
    use_historical_queries: bool = True,
) -> TrainingPlan:
```

**自动提取流程**：

```
用户调用 train() 无参数
        ↓
检查是否已连接数据库
        ↓
尝试获取 INFORMATION_SCHEMA.COLUMNS
        ↓
按 database → schema → table 分组
        ↓
为每个表生成文档：
"The following columns are in the {table} table:
| COLUMN_NAME | DATA_TYPE | COMMENT |"
        ↓
存入 Documentation Collection
```

### 2.3 历史查询自动学习（Snowflake 特性）

```python
# 从历史查询记录中提取有价值的 SQL
if use_historical_queries:
    df_history = self.run_sql("""
        SELECT * FROM table(information_schema.query_history(
            result_limit => 5000
        )) ORDER BY start_time
    """)
    # 筛选产生结果的查询，生成问答对训练数据
```

### 2.4 TrainingPlan 训练计划

```python
@dataclass
class TrainingPlanItem:
    item_type: str      # "sql" | "ddl" | "is"
    item_group: str     # 分组标识
    item_name: str      # 名称
    item_value: str     # 实际内容

class TrainingPlan:
    _plan: List[TrainingPlanItem]
    
    def get_summary(self) -> List[str]:
        """获取训练计划摘要，支持人工审核"""
        
    def remove_item(self, item: str):
        """移除不需要的训练项"""
```

---

## 3. 向量存储架构

### 3.1 双轨架构设计

Vanna 实现了**双轨向量存储架构**：

```
┌──────────────────────────────────────────────────────────────┐
│                    Vanna 向量存储架构                          │
├─────────────────────────┬────────────────────────────────────┤
│      Legacy 轨道         │        Modern 轨道                  │
│   (VannaBase 继承)       │    (AgentMemory 能力)               │
├─────────────────────────┼────────────────────────────────────┤
│ - ChromaDB_VectorStore  │ - ChromaAgentMemory                 │
│ - Milvus_VectorStore    │ - PineconeAgentMemory               │
│ - PineconeDB_VectorStore│ - DemoAgentMemory                   │
│ - ...                   │                                     │
├─────────────────────────┼────────────────────────────────────┤
│ 用于：SQL生成上下文检索   │ 用于：Agent 工具使用学习             │
└─────────────────────────┴────────────────────────────────────┘
```

### 3.2 Legacy 轨道 - VannaBase 向量存储

#### 3.2.1 抽象接口

```python
class VannaBase(ABC):
    # 存储接口
    @abstractmethod
    def add_question_sql(self, question: str, sql: str) -> str: pass
    
    @abstractmethod
    def add_ddl(self, ddl: str) -> str: pass
    
    @abstractmethod
    def add_documentation(self, documentation: str) -> str: pass
    
    # 检索接口
    @abstractmethod
    def get_similar_question_sql(self, question: str) -> list: pass
    
    @abstractmethod
    def get_related_ddl(self, question: str) -> list: pass
    
    @abstractmethod
    def get_related_documentation(self, question: str) -> list: pass
    
    # 嵌入生成
    @abstractmethod
    def generate_embedding(self, data: str) -> List[float]: pass
```

#### 3.2.2 ChromaDB 实现示例

```python
class ChromaDB_VectorStore(VannaBase):
    def __init__(self, config=None):
        # 三个独立的 Collection
        self.documentation_collection = chroma_client.get_or_create_collection(
            name="documentation"
        )
        self.ddl_collection = chroma_client.get_or_create_collection(
            name="ddl"
        )
        self.sql_collection = chroma_client.get_or_create_collection(
            name="sql"
        )
    
    def add_question_sql(self, question: str, sql: str) -> str:
        # 存储为 JSON: {"question": "...", "sql": "..."}
        question_sql_json = json.dumps({"question": question, "sql": sql})
        id = deterministic_uuid(question_sql_json) + "-sql"
        self.sql_collection.add(
            documents=question_sql_json,
            embeddings=self.generate_embedding(question_sql_json),
            ids=id
        )
```

### 3.3 支持的向量数据库

| 数据库 | 实现类 | 适用场景 | 特性 |
|-------|-------|---------|------|
| **ChromaDB** | `ChromaDB_VectorStore` | 本地开发、小规模 | 默认嵌入模型，持久化存储 |
| **Milvus** | `Milvus_VectorStore` | 企业级大规模 | 支持 AUTOINDEX，L2 距离 |
| **Pinecone** | `PineconeDB_VectorStore` | 云原生应用 | Serverless/Pod 模式，命名空间隔离 |
| **Weaviate** | `Weaviate_VectorStore` | 混合搜索 | GraphQL 接口 |
| **Qdrant** | `Qdrant_VectorStore` | 高性能检索 | Rust 实现，过滤丰富 |
| **FAISS** | `FAISS_VectorStore` | 研究实验 | Meta 开源，纯内存 |
| **OpenSearch** | `OpenSearch_VectorStore` | AWS 生态 | 与 ELK 集成 |
| **Azure Search** | `AzureSearch_VectorStore` | Azure 生态 | 语义搜索 |
| **Oracle** | `Oracle_VectorStore` | 企业 Oracle 用户 | 23c+ 向量支持 |
| **PGVector** | `PGVector_VectorStore` | Postgres 用户 | pgvector 扩展 |
| **Marqo** | `Marqo_VectorStore` | 端到端搜索 | 内置嵌入模型 |
| **VannaDB** | `VannaDB_VectorStore` | 无运维负担 | 官方托管服务 |

### 3.4 向量存储配置对比

```python
# ChromaDB 配置
ChromaDB_VectorStore(config={
    "path": "./chroma_data",           # 持久化路径
    "client": "persistent",            # persistent | in-memory
    "embedding_function": custom_ef,   # 自定义嵌入函数
    "n_results": 10,                   # 默认检索数量
})

# Milvus 配置
Milvus_VectorStore(config={
    "milvus_client": client,           # 或自动创建
    "embedding_function": ef,
    "n_results": 10,
})

# Pinecone 配置
PineconeDB_VectorStore(config={
    "api_key": "...",
    "index_name": "vanna-index",
    "server_type": "serverless",       # serverless | pod
    "dimensions": 384,
    "fastembed_model": "BAAI/bge-small-en-v1.5",
})
```

---

## 4. RAG 检索流程

### 4.1 SQL 生成时的 RAG 流程

```python
def generate_sql(self, question: str, **kwargs) -> str:
    """
    RAG 检索 → 上下文组装 → LLM 生成 的完整流程
    """
    # Step 1: 并行检索三类上下文
    question_sql_list = self.get_similar_question_sql(question)  # 相似问答对
    ddl_list = self.get_related_ddl(question)                     # 相关 DDL
    doc_list = self.get_related_documentation(question)          # 相关文档
    
    # Step 2: 组装 Prompt
    prompt = self.get_sql_prompt(
        question=question,
        question_sql_list=question_sql_list,
        ddl_list=ddl_list,
        doc_list=doc_list,
    )
    
    # Step 3: 提交 LLM 生成 SQL
    llm_response = self.submit_prompt(prompt)
    return self.extract_sql(llm_response)
```

### 4.2 Prompt 组装策略

```python
def get_sql_prompt(self, initial_prompt, question, question_sql_list, 
                   ddl_list, doc_list):
    # 1. 系统提示 + 方言信息
    initial_prompt = f"You are a {self.dialect} expert..."
    
    # 2. 添加 DDL（表结构）- 最先提供，最重要
    initial_prompt = self.add_ddl_to_prompt(initial_prompt, ddl_list)
    
    # 3. 添加业务文档
    initial_prompt = self.add_documentation_to_prompt(initial_prompt, doc_list)
    
    # 4. 添加响应指南
    initial_prompt += "===Response Guidelines\n..."
    
    # 5. Few-shot 示例（问答对作为上下文学习）
    message_log = [self.system_message(initial_prompt)]
    for example in question_sql_list:
        message_log.append(self.user_message(example["question"]))
        message_log.append(self.assistant_message(example["sql"]))
    
    # 6. 当前问题
    message_log.append(self.user_message(question))
    
    return message_log
```

### 4.3 Token 预算管理

```python
def add_ddl_to_prompt(self, initial_prompt: str, ddl_list: list, 
                      max_tokens: int = 14000) -> str:
    """
    控制上下文长度，避免超出 LLM 上下文窗口
    """
    for ddl in ddl_list:
        if (self.str_to_approx_token_count(initial_prompt) + 
            self.str_to_approx_token_count(ddl) < max_tokens):
            initial_prompt += f"{ddl}\n\n"
    return initial_prompt

def str_to_approx_token_count(self, string: str) -> int:
    """简单估算：1 token ≈ 4 字符"""
    return len(string) / 4
```

### 4.4 检索数量配置

```python
# ChromaDB 中可为不同类型配置不同检索数量
class ChromaDB_VectorStore(VannaBase):
    def __init__(self, config=None):
        self.n_results_sql = config.get("n_results_sql", 10)           # SQL 示例数
        self.n_results_documentation = config.get(
            "n_results_documentation", 10)                             # 文档数
        self.n_results_ddl = config.get("n_results_ddl", 10)           # DDL 数
```

---

## 5. 元数据管理

### 5.1 训练数据 ID 生成策略

Vanna 使用**确定性 UUID** 避免重复训练：

```python
def deterministic_uuid(content: Union[str, bytes]) -> str:
    """
    基于内容哈希生成确定性 UUID
    相同内容 → 相同 ID → 自动去重
    """
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    
    hash_object = hashlib.sha256(content_bytes)
    hash_hex = hash_object.hexdigest()
    namespace = uuid.UUID("00000000-0000-0000-0000-000000000000")
    return str(uuid.uuid5(namespace, hash_hex))

# 使用示例
id = deterministic_uuid(ddl_content) + "-ddl"
id = deterministic_uuid(json.dumps({"question": q, "sql": s})) + "-sql"
```

### 5.2 训练数据管理

```python
# 获取所有训练数据
def get_training_data(self) -> pd.DataFrame:
    """
    返回包含以下列的 DataFrame:
    - id: 训练数据 ID
    - question: 问题（SQL 类型有值）
    - content: 内容（DDL/SQL/文档）
    - training_data_type: sql | ddl | documentation
    """

# 删除训练数据
def remove_training_data(self, id: str) -> bool:
    """根据 ID 后缀 (-sql/-ddl/-doc) 路由到对应 Collection 删除"""
```

### 5.3 自动训练机制

```python
def ask(self, question: str, auto_train: bool = True, ...):
    """
    用户问答时自动学习有效查询
    """
    sql = self.generate_sql(question)
    df = self.run_sql(sql)
    
    # 自动训练：如果返回结果且 auto_train=True
    if len(df) > 0 and auto_train:
        self.add_question_sql(question=question, sql=sql)
```

---

## 6. 与 DB-GPT/RAGFlow RAG 的对比

### 6.1 架构对比

| 维度 | Vanna | DB-GPT | RAGFlow |
|-----|-------|--------|---------|
| **定位** | SQL 生成专项工具 | 数据智能体平台 | 深度文档理解+RAG |
| **核心能力** | Text2SQL | 多场景数据对话 | 企业级知识库 |
| **RAG 架构** | 轻量级三层检索 | 多源 RAG + Agent | 深度文档解析+多路召回 |
| **向量存储** | 多后端支持 | 支持多种向量库 | 自研+集成 |
| **Schema 理解** | DDL 直接嵌入 | Schema Linking | 表结构文档化 |

### 6.2 训练数据策略对比

```
┌────────────────────────────────────────────────────────────────────┐
│                       训练数据对比                                  │
├──────────────────┬──────────────────┬──────────────────────────────┤
│     Vanna        │    DB-GPT        │      RAGFlow                 │
├──────────────────┼──────────────────┼──────────────────────────────┤
│ DDL 原始文本     │ Schema 元数据    │ 结构化文档块                  │
│ Q-SQL 问答对     │ 样例 SQL 池      │ 问答对（通用）                │
│ 业务文档         │ 领域知识库       │ 深度解析的文档图谱             │
├──────────────────┼──────────────────┼──────────────────────────────┤
│ 特点：           │ 特点：           │ 特点：                        │
│ - 简单直接       │ - 多维度索引     │ - 文档理解深度                │
│ - 向量化存储     │ - Agent 工具集成 │ - 多路召回融合                │
│ - 轻量高效       │ - 复杂推理链     │ - 企业级可控                  │
└──────────────────┴──────────────────┴──────────────────────────────┘
```

### 6.3 RAG 检索机制对比

| 特性 | Vanna | DB-GPT | RAGFlow |
|-----|-------|--------|---------|
| **检索粒度** | 整块 DDL/文档 | 字段级 Schema | 语义块/表格/图片 |
| **召回策略** | 向量相似度 | 多路召回 | 多路+重排序 |
| **上下文组装** | 固定模板 | 动态模板 | 智能压缩 |
| **Schema Linking** | 隐式（DDL 匹配） | 显式（字段选择） | 需预处理 |
| **Self-RAG** | 不支持 | 支持反思迭代 | 支持答案溯源 |

### 6.4 优势与局限

#### Vanna 优势：

1. **极简接入**：3 行代码即可开始训练和使用
2. **多数据库支持**：原生支持 10+ 种数据库
3. **灵活部署**：本地/云端/混合模式
4. **训练简单**：无需复杂的数据预处理

#### Vanna 局限：

1. **无 Schema Linking**：直接检索相关 DDL，不做字段级选择
2. **无多轮推理**：单次 RAG + 生成，无 Self-Correction
3. **文档解析弱**：不支持复杂文档的自动解析
4. **检索粒度粗**：整表 DDL 可能超出上下文窗口

### 6.5 适用场景建议

| 场景 | 推荐方案 | 原因 |
|-----|---------|------|
| 快速验证 Text2SQL | **Vanna** | 接入成本最低 |
| 表数量 < 50 | **Vanna** | 上下文可容纳全部 DDL |
| 复杂 Schema（千表级） | **DB-GPT** | 需要 Schema Linking |
| 需要文档理解 | **RAGFlow** | 深度文档解析能力 |
| 企业级生产环境 | **DB-GPT/RAGFlow** | 可控性和可观测性 |

---

## 7. 关键代码路径

### 7.1 核心文件位置

```
vanna/src/vanna/
├── legacy/
│   ├── base/base.py              # VannaBase 抽象基类（训练+检索接口）
│   ├── chromadb/
│   │   └── chromadb_vector.py    # ChromaDB 实现
│   ├── milvus/
│   │   └── milvus_vector.py      # Milvus 实现
│   ├── pinecone/
│   │   └── pinecone_vector.py    # Pinecone 实现
│   └── types/__init__.py         # TrainingPlan 等类型定义
├── capabilities/
│   └── agent_memory/
│       ├── base.py               # AgentMemory 抽象接口
│       └── models.py             # 内存数据模型
└── integrations/
    ├── chromadb/
    │   └── agent_memory.py       # ChromaDB AgentMemory 实现
    ├── pinecone/
    │   └── agent_memory.py       # Pinecone AgentMemory 实现
    └── local/
        └── agent_memory/
            └── in_memory.py      # Demo 内存实现
```

### 7.2 关键流程时序

```
用户提问
    │
    ▼
┌─────────────────┐
│  generate_sql() │
└────────┬────────┘
         │
    ┌────┴────┬────────────┬────────────────┐
    ▼         ▼            ▼                ▼
┌───────┐ ┌────────┐ ┌──────────────┐ ┌──────────┐
│get_   │ │get_    │ │get_related_  │ │generate_ │
│similar│ │related │ │documentation │ │embedding │
│_question│_ddl    │ │              │ │          │
│_sql   │ │        │ │              │ │          │
└───┬───┘ └────┬───┘ └──────┬───────┘ └────┬─────┘
    │          │            │              │
    ▼          ▼            ▼              ▼
┌──────────────────────────────────────────────────┐
│               Vector Store Query                  │
│  (sql_collection / ddl_collection / doc_collection)│
└──────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  get_sql_prompt │ ← 组装上下文 + 系统提示
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  submit_prompt  │ → LLM API
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  extract_sql    │ ← 从响应提取 SQL
└─────────────────┘
```

---

## 8. 最佳实践建议

### 8.1 训练策略

1. **分层训练**：
   - 第一层：核心表 DDL（必须）
   - 第二层：常用业务查询 SQL 示例（推荐）
   - 第三层：业务术语文档（可选）

2. **SQL 示例质量**：
   - 覆盖主要查询模式（聚合、JOIN、子查询）
   - 包含业务术语到字段的映射
   - 定期清理无效示例

3. **DDL 管理**：
   - 优先添加常用表
   - 大表考虑添加字段注释
   - 视图也是有效的训练数据

### 8.2 性能优化

1. **检索数量调优**：
   ```python
   config = {
       "n_results_ddl": 5,            # DDL 不宜过多
       "n_results_sql": 10,           # SQL 示例可稍多
       "n_results_documentation": 3,  # 文档精选
   }
   ```

2. **大 Schema 处理**：
   - 使用 `filter_databases`/`filter_schemas` 限定范围
   - 分模型管理（按业务域拆分）
   - 考虑使用 Milvus 等高性能向量库

3. **嵌入模型选择**：
   - 默认：ChromaDB DefaultEmbeddingFunction
   - 中文场景：考虑使用中文嵌入模型
   - 离线环境：预下载模型或使用本地嵌入服务

---

## 9. 总结

Vanna 的训练和 RAG 机制设计简洁高效，核心特点：

1. **三层数据融合**：DDL + SQL示例 + 文档，覆盖结构、模式、语义
2. **双轨向量架构**：Legacy 轨道用于 SQL 生成，Modern 轨道用于 Agent 学习
3. **多后端支持**：10+ 种向量数据库，灵活适配不同场景
4. **自动训练能力**：从数据库元数据自动提取训练数据
5. **轻量易用**：最小化接入成本，适合快速验证 Text2SQL 场景

对于大规模生产环境，建议评估引入 Schema Linking、Self-RAG 等增强机制。

---

*分析完成于 2026-02-05*
