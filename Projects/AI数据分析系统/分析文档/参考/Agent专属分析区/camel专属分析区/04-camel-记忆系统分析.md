---
title: CAMEL 记忆系统分析
description: CAMEL框架记忆存储和检索机制深入分析
tags: [CAMEL, 记忆系统, 向量检索, Agent架构]
created: 2026-02-06
version: 1.0.0
---

# CAMEL 记忆系统分析

本文档分析 CAMEL 框架的记忆存储和检索机制，包括基类设计、记忆类型、向量记忆实现、检索策略和存储后端。

---

## 1. 记忆系统架构概览

CAMEL 的记忆系统采用分层架构设计，核心组件包括：

- **记忆记录层**：定义数据结构和序列化机制
- **记忆块层**：提供基础存储操作
- **Agent 记忆层**：面向 Agent 的高级接口
- **存储后端层**：对接各种存储系统

![camel-记忆类图.svg](camel-记忆类图.svg)

---

## 2. 记忆基类设计

### 2.1 MemoryBlock 抽象基类

`MemoryBlock` 是记忆系统的最基础组件，定义了写入和清除操作的接口。

```python
class MemoryBlock(ABC):
    @abstractmethod
    def write_records(self, records: List[MemoryRecord]) -> None:
        # 批量写入记忆记录
        pass
    
    def write_record(self, record: MemoryRecord) -> None:
        # 单条写入，默认调用批量写入
        self.write_records([record])
    
    def pop_records(self, count: int) -> List[MemoryRecord]:
        # 移除并返回最近期的记录
        raise NotImplementedError
    
    def remove_records_by_indices(
        self, indices: List[int]
    ) -> List[MemoryRecord]:
        # 按索引移除记录
        raise NotImplementedError
    
    @abstractmethod
    def clear(self) -> None:
        # 清空所有记忆
        pass
```

设计要点：

- 刻意不定义检索接口，因为不同记忆块的检索方式差异很大
- `write_records` 作为批量操作，减少存储 I/O 次数
- `pop_records` 和 `remove_records_by_indices` 提供可选的记录管理功能

### 2.2 AgentMemory 抽象基类

`AgentMemory` 继承自 `MemoryBlock`，专门用于与 Agent 集成，增加了检索和上下文创建功能。

```python
class AgentMemory(MemoryBlock, ABC):
    @property
    @abstractmethod
    def agent_id(self) -> Optional[str]:
        # Agent 唯一标识符
        pass
    
    @abstractmethod
    def retrieve(self) -> List[ContextRecord]:
        # 检索用于创建模型上下文的记录
        pass
    
    @abstractmethod
    def get_context_creator(self) -> BaseContextCreator:
        # 获取上下文创建器
        pass
    
    def get_context(self) -> Tuple[List[OpenAIMessage], int]:
        # 获取格式化后的聊天上下文和 Token 数量
        return self.get_context_creator().create_context(self.retrieve())
```

设计要点：

- `agent_id` 支持多 Agent 场景下的记忆隔离
- `retrieve` 返回 `ContextRecord` 列表，包含相关性评分
- `get_context` 将记忆记录转换为模型可用的消息格式

### 2.3 BaseContextCreator 抽象基类

上下文创建器负责将记忆记录组装成模型可用的上下文。

```python
class BaseContextCreator(ABC):
    @property
    @abstractmethod
    def token_counter(self) -> BaseTokenCounter:
        # Token 计数器
        pass
    
    @property
    @abstractmethod
    def token_limit(self) -> int:
        # Token 上限
        pass
    
    @abstractmethod
    def create_context(
        self,
        records: List[ContextRecord],
    ) -> Tuple[List[OpenAIMessage], int]:
        # 创建对话上下文
        pass
```

---

## 3. 记忆记录数据结构

### 3.1 MemoryRecord 记忆记录

`MemoryRecord` 是记忆系统的基本存储单元，封装了单条消息的所有信息。

```python
class MemoryRecord(BaseModel):
    message: BaseMessage                    # 消息内容
    role_at_backend: OpenAIBackendRole      # 后端角色类型
    uuid: UUID = Field(default_factory=uuid4)  # 唯一标识
    extra_info: Dict[str, str] = Field(default_factory=dict)  # 附加信息
    timestamp: float                        # 时间戳，纳秒级精度
    agent_id: str = Field(default="")       # 关联的 Agent ID
```

关键特性：

- 使用 Pydantic 模型确保数据验证
- 自动分配 UUID 和时间戳
- 支持 `to_dict` 和 `from_dict` 序列化
- 支持图像和视频数据的 Base64 编码存储

### 3.2 ContextRecord 上下文记录

`ContextRecord` 表示记忆检索的结果，在 `MemoryRecord` 基础上增加了相关性评分。

```python
class ContextRecord(BaseModel):
    memory_record: MemoryRecord    # 原始记忆记录
    score: float                   # 相关性评分
    timestamp: float               # 检索时间戳
```

设计意图：

- 评分用于上下文筛选和排序
- 时间戳记录检索时机，支持时序分析

---

## 4. 记忆块实现

### 4.1 ChatHistoryBlock 对话历史块

`ChatHistoryBlock` 管理对话历史，支持滑动窗口检索。

```python
class ChatHistoryBlock(MemoryBlock):
    def __init__(
        self,
        storage: Optional[BaseKeyValueStorage] = None,
        keep_rate: float = 0.9,  # 历史消息保留率
    ) -> None:
        self.storage = storage or InMemoryKeyValueStorage()
        self.keep_rate = keep_rate
```

**检索逻辑**：

```python
def retrieve(self, window_size: Optional[int] = None) -> List[ContextRecord]:
    # 1. 从存储加载所有记录
    record_dicts = self.storage.load()
    
    # 2. 保留系统消息，截断历史消息
    if window_size is not None:
        preserved = record_dicts[:start_index]  # 系统消息
        sliding = record_dicts[start_index:]     # 历史消息
        truncated = sliding[-window_size:]       # 取最近 window_size 条
        final_records = preserved + truncated
    
    # 3. 计算评分：越新的消息评分越高
    score = 1.0
    for record in reversed(chat_records):
        if record.role_at_backend == SYSTEM:
            score = 1.0  # 系统消息永远保留
        else:
            score *= self.keep_rate  # 按保留率递减
```

关键特性：

- 滑动窗口机制控制上下文长度
- 系统消息始终保留在开头
- 评分按时间衰减，支持基于相关性的上下文筛选

### 4.2 VectorDBBlock 向量数据库块

`VectorDBBlock` 使用向量嵌入实现语义检索。

```python
class VectorDBBlock(MemoryBlock):
    def __init__(
        self,
        storage: Optional[BaseVectorStorage] = None,
        embedding: Optional[BaseEmbedding] = None,
    ) -> None:
        self.embedding = embedding or OpenAIEmbedding()
        self.vector_dim = self.embedding.get_output_dim()
        self.storage = storage or QdrantStorage(vector_dim=self.vector_dim)
```

**检索流程**：

```python
def retrieve(self, keyword: str, limit: int = 3) -> List[ContextRecord]:
    # 1. 将查询关键词转换为向量
    query_vector = self.embedding.embed(keyword)
    
    # 2. 在向量数据库中搜索相似向量
    results = self.storage.query(
        VectorDBQuery(query_vector=query_vector, top_k=limit)
    )
    
    # 3. 返回带相似度评分的上下文记录
    return [
        ContextRecord(
            memory_record=MemoryRecord.from_dict(result.record.payload),
            score=result.similarity,
            timestamp=result.record.payload['timestamp'],
        )
        for result in results
    ]
```

**写入流程**：

```python
def write_records(self, records: List[MemoryRecord]) -> None:
    # 1. 过滤空内容记录
    valid_records = [r for r in records if r.message.content.strip()]
    
    # 2. 将消息内容转换为向量
    v_records = [
        VectorRecord(
            vector=self.embedding.embed(record.message.content),
            payload=record.to_dict(),
            id=str(record.uuid),
        )
        for record in valid_records
    ]
    
    # 3. 写入向量数据库
    self.storage.add(v_records)
```

---

## 5. Agent 记忆实现

### 5.1 ChatHistoryMemory 对话历史记忆

包装 `ChatHistoryBlock`，为 Agent 提供对话历史管理功能。

```python
class ChatHistoryMemory(AgentMemory):
    def __init__(
        self,
        context_creator: BaseContextCreator,
        storage: Optional[BaseKeyValueStorage] = None,
        window_size: Optional[int] = None,  # 窗口大小
        agent_id: Optional[str] = None,
    ) -> None:
        self._chat_history_block = ChatHistoryBlock(storage=storage)
        self._window_size = window_size
```

**特殊功能**：

```python
def clean_tool_calls(self) -> None:
    # 清理工具调用相关消息，节省 Token
    # - 移除 FUNCTION/TOOL 角色的消息
    # - 移除包含 tool_calls 的 ASSISTANT 消息
```

### 5.2 VectorDBMemory 向量数据库记忆

包装 `VectorDBBlock`，基于当前话题进行语义检索。

```python
class VectorDBMemory(AgentMemory):
    def __init__(
        self,
        context_creator: BaseContextCreator,
        storage: Optional[BaseVectorStorage] = None,
        retrieve_limit: int = 3,  # 检索数量限制
        agent_id: Optional[str] = None,
    ) -> None:
        self._vectordb_block = VectorDBBlock(storage=storage)
        self._retrieve_limit = retrieve_limit
        self._current_topic: str = ""  # 当前话题
```

话题跟踪：

```python
def write_records(self, records: List[MemoryRecord]) -> None:
    # 假设最后一条用户输入是当前话题
    for record in records:
        if record.role_at_backend == OpenAIBackendRole.USER:
            self._current_topic = record.message.content
    
    # 写入向量数据库
    self._vectordb_block.write_records(records)

def retrieve(self) -> List[ContextRecord]:
    # 使用当前话题作为查询关键词
    return self._vectordb_block.retrieve(
        self._current_topic,
        limit=self._retrieve_limit,
    )
```

### 5.3 LongtermAgentMemory 长期记忆

组合 `ChatHistoryBlock` 和 `VectorDBBlock`，实现混合记忆。

```python
class LongtermAgentMemory(AgentMemory):
    def __init__(
        self,
        context_creator: BaseContextCreator,
        chat_history_block: Optional[ChatHistoryBlock] = None,
        vector_db_block: Optional[VectorDBBlock] = None,
        retrieve_limit: int = 3,
        agent_id: Optional[str] = None,
    ) -> None:
        self.chat_history_block = chat_history_block or ChatHistoryBlock()
        self.vector_db_block = vector_db_block or VectorDBBlock()
```

**混合检索策略**：

```python
def retrieve(self) -> List[ContextRecord]:
    chat_history = self.chat_history_block.retrieve()
    vector_db_retrieve = self.vector_db_block.retrieve(
        self._current_topic,
        self.retrieve_limit,
    )
    # 组合：最近消息 + 语义相关历史 + 其余对话
    return chat_history[:1] + vector_db_retrieve + chat_history[1:]
```

组合逻辑：

- 保留最近一条消息确保上下文连续性
- 插入语义相关的历史记忆
- 追加剩余对话历史

---

## 6. 上下文创建器实现

### 6.1 ScoreBasedContextCreator

基于评分的上下文创建器，支持 Token 计数缓存优化。

```python
class ScoreBasedContextCreator(BaseContextCreator):
    def __init__(
        self, 
        token_counter: BaseTokenCounter, 
        token_limit: int
    ) -> None:
        self._token_counter = token_counter
        self._token_limit = token_limit
        # Token 计数缓存
        self._cached_token_count: Optional[int] = None
        self._cached_message_count: int = 0
```

**Token 估计优化**：

```python
def _estimate_message_tokens(self, message: OpenAIMessage) -> int:
    # 使用字符数估计 Token 数量
    # ~2 字符/Token，兼顾 ASCII 和中文
    content = message.get("content", "")
    token_estimate = 4  # 消息开销
    
    if isinstance(content, list):
        # 多模态内容
        for part in content:
            if part.get("type") == "image_url":
                token_estimate += 1500  # 图像 Token 估计
            else:
                token_estimate += len(str(part)) // 2
    else:
        token_estimate += len(str(content)) // 2
    
    return token_estimate
```

**缓存机制**：

```python
def create_context(self, records: List[ContextRecord]):
    # 缓存命中：消息数量相同，直接返回缓存值
    if current_count == self._cached_message_count:
        return messages, self._cached_token_count
    
    # 增量估计：新消息使用字符估计
    elif current_count > self._cached_message_count:
        new_messages = messages[self._cached_message_count:]
        estimated_new_tokens = sum(
            self._estimate_message_tokens(msg) for msg in new_messages
        )
        return messages, self._cached_token_count + estimated_new_tokens
    
    # 缓存失效：重新计算所有 Token
    total_tokens = self.token_counter.count_tokens_from_messages(messages)
```

---

## 7. 存储后端

### 7.1 键值存储

#### BaseKeyValueStorage 接口

```python
class BaseKeyValueStorage(ABC):
    @abstractmethod
    def save(self, records: List[Dict[str, Any]]) -> None:
        pass
    
    @abstractmethod
    def load(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def clear(self) -> None:
        pass
```

#### 实现列表

| 存储类型 | 类名 | 特点 |
|---------|------|------|
| 内存存储 | `InMemoryKeyValueStorage` | 程序退出数据丢失，适合临时使用 |
| JSON 文件 | `JsonKeyValueStorage` | 持久化到本地文件 |
| Redis | `RedisStorage` | 分布式缓存，支持过期时间 |
| Mem0 Cloud | `Mem0Storage` | 云端记忆服务集成 |

### 7.2 向量存储

#### BaseVectorStorage 接口

```python
class BaseVectorStorage(ABC):
    @abstractmethod
    def add(self, records: List[VectorRecord]) -> None:
        # 添加向量记录
        pass
    
    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        # 删除向量
        pass
    
    @abstractmethod
    def query(self, query: VectorDBQuery) -> List[VectorDBQueryResult]:
        # 相似度查询
        pass
    
    @abstractmethod
    def status(self) -> VectorDBStatus:
        # 返回数据库状态
        pass
    
    @abstractmethod
    def clear(self) -> None:
        # 清空数据
        pass
```

#### 向量记录结构

```python
class VectorRecord(BaseModel):
    vector: List[float]              # 向量数据
    id: str                          # 唯一标识
    payload: Optional[Dict[str, Any]]  # 附加数据

class VectorDBQuery(BaseModel):
    query_vector: List[float]        # 查询向量
    top_k: int = 1                   # 返回数量

class VectorDBQueryResult(BaseModel):
    record: VectorRecord             # 匹配的记录
    similarity: float                # 相似度分数
```

#### 支持的向量数据库

| 数据库 | 类名 | 特点 |
|--------|------|------|
| Qdrant | `QdrantStorage` | 默认选项，支持本地/远程/内存模式 |
| Chroma | `ChromaStorage` | 轻量级，适合快速原型 |
| Milvus | `MilvusStorage` | 企业级，支持大规模数据 |
| Faiss | `FaissStorage` | Meta 开源，纯内存高性能 |
| Weaviate | `WeaviateStorage` | 支持 GraphQL 查询 |
| PGVector | `PGVectorStorage` | PostgreSQL 扩展 |
| TiDB | `TiDBStorage` | 分布式 SQL 数据库 |
| OceanBase | `OceanBaseStorage` | 国产分布式数据库 |

#### QdrantStorage 详细分析

Qdrant 是 CAMEL 的默认向量存储，支持三种运行模式：

```python
def _create_client(
    self,
    url_and_api_key: Optional[Tuple[str, str]],
    path: Optional[str],
    **kwargs: Any,
) -> None:
    if url_and_api_key is not None:
        # 模式1：远程服务器
        self._client = QdrantClient(
            url=url_and_api_key[0],
            api_key=url_and_api_key[1],
            **kwargs,
        )
    elif path is not None:
        # 模式2：本地持久化
        # 使用单例模式避免重复创建客户端
        if path in _qdrant_local_client_map:
            self._client, count = _qdrant_local_client_map[path]
            _qdrant_local_client_map[path] = (self._client, count + 1)
        else:
            self._client = QdrantClient(path=path, **kwargs)
            _qdrant_local_client_map[path] = (self._client, 1)
    else:
        # 模式3：纯内存
        self._client = QdrantClient(":memory:", **kwargs)
```

距离度量支持：

```python
distance_map = {
    VectorDistance.DOT: Distance.DOT,           # 点积
    VectorDistance.COSINE: Distance.COSINE,     # 余弦相似度
    VectorDistance.EUCLIDEAN: Distance.EUCLID,  # 欧氏距离
}
```

---

## 8. 嵌入模型集成

### 8.1 BaseEmbedding 接口

```python
class BaseEmbedding(ABC, Generic[T]):
    @abstractmethod
    def embed_list(self, objs: list[T], **kwargs) -> list[list[float]]:
        # 批量嵌入
        pass
    
    def embed(self, obj: T, **kwargs) -> list[float]:
        # 单条嵌入，默认调用批量接口
        return self.embed_list([obj], **kwargs)[0]
    
    @abstractmethod
    def get_output_dim(self) -> int:
        # 获取输出维度
        pass
```

### 8.2 支持的嵌入模型

| 提供商 | 类名 | 典型维度 |
|--------|------|---------|
| OpenAI | `OpenAIEmbedding` | 1536 / 3072 |
| Azure OpenAI | `AzureOpenAIEmbedding` | 1536 |
| Cohere | `CohereEmbedding` | 1024 |
| Mistral | `MistralEmbedding` | 1024 |
| Qwen | `QwenEmbedding` | 1536 |
| Jina | `JinaEmbedding` | 768 |
| Sentence Transformers | `SentenceTransformerEncoder` | 可配置 |

---

## 9. 记忆检索流程

![camel-记忆检索流程图.svg](camel-记忆检索流程图.svg)

### 9.1 对话历史检索流程

```
Agent.get_context()
  ↓
AgentMemory.retrieve()
  ↓
ChatHistoryBlock.retrieve(window_size)
  ↓
BaseKeyValueStorage.load()
  ↓
按时间排序 + 保留率评分
  ↓
ScoreBasedContextCreator.create_context()
  ↓
转换为 OpenAIMessage 列表
```

### 9.2 向量记忆检索流程

```
Agent.get_context()
  ↓
VectorDBMemory.retrieve()
  ↓
VectorDBBlock.retrieve(current_topic)
  ↓
BaseEmbedding.embed(keyword)
  ↓
BaseVectorStorage.query(VectorDBQuery)
  ↓
返回相似度排序的 ContextRecord
```

### 9.3 混合记忆检索流程

```
LongtermAgentMemory.retrieve()
  ↓
并行执行：
  ├─ ChatHistoryBlock.retrieve() → 最近对话
  └─ VectorDBBlock.retrieve(topic) → 相关历史
  ↓
合并策略：最近 + 相关历史 + 剩余对话
  ↓
ScoreBasedContextCreator.create_context()
```

---

## 10. 与 smolagents 记忆对比

| 特性 | CAMEL Memory | smolagents Memory |
|------|--------------|-------------------|
| **记忆类型** | 多种类型：对话历史、向量记忆、混合记忆 | 单一 MemoryStep 列表 |
| **数据结构** | MemoryRecord + ContextRecord | MemoryStep 基类 |
| **检索方式** | 滑动窗口 + 向量语义检索 | 线性遍历全部记录 |
| **存储后端** | 内存、JSON、Redis、向量数据库等 | 仅内存存储 |
| **嵌入集成** | 支持多种嵌入模型 | 无嵌入支持 |
| **Token 管理** | TokenCounter + 缓存优化 | 无专门管理 |
| **持久化** | 支持多种持久化方案 | 无持久化 |
| **扩展性** | 高，可自定义 MemoryBlock 和 Storage | 低，简单继承 |
| **多 Agent 支持** | agent_id 隔离 | 无原生支持 |
| **工具调用清理** | clean_tool_calls 方法 | 无专门处理 |

### 10.1 架构复杂度对比

**CAMEL**：

- 分层抽象：MemoryBlock → AgentMemory → 具体实现
- 存储抽象：支持多种存储后端
- 可插拔设计：嵌入模型、向量数据库可替换

**smolagents**：

- 简单列表存储
- 直接遍历检索
- 适合简单场景

### 10.2 适用场景

| 场景 | 推荐框架 |
|------|---------|
| 简单对话 Agent | smolagents |
| 长期记忆需求 | CAMEL |
| 大规模数据检索 | CAMEL |
| 多 Agent 系统 | CAMEL |
| 快速原型开发 | smolagents |
| 生产级部署 | CAMEL |

---

## 11. 关键设计模式

### 11.1 抽象分层模式

```
Abstract Base Class
    ↓ 定义接口
MemoryBlock / AgentMemory / BaseContextCreator
    ↓ 具体实现
ChatHistoryBlock / VectorDBBlock / ScoreBasedContextCreator
    ↓ 组合使用
ChatHistoryMemory / VectorDBMemory / LongtermAgentMemory
```

### 11.2 策略模式

存储后端和嵌入模型采用策略模式，支持运行时替换：

```python
# 存储策略
storage: BaseKeyValueStorage = InMemoryKeyValueStorage()
# 或
storage: BaseKeyValueStorage = RedisStorage()

# 嵌入策略
embedding: BaseEmbedding = OpenAIEmbedding()
# 或
embedding: BaseEmbedding = SentenceTransformerEncoder()
```

### 11.3 装饰器模式

`LongtermAgentMemory` 组合两种记忆块，实现功能增强：

```python
class LongtermAgentMemory(AgentMemory):
    def __init__(self, ...):
        self.chat_history_block = ChatHistoryBlock()
        self.vector_db_block = VectorDBBlock()
```

---

## 12. 源码文件索引

| 文件路径 | 主要内容 |
|---------|---------|
| `camel/memories/base.py` | MemoryBlock、AgentMemory、BaseContextCreator 基类 |
| `camel/memories/records.py` | MemoryRecord、ContextRecord 数据模型 |
| `camel/memories/blocks/chat_history_block.py` | ChatHistoryBlock 实现 |
| `camel/memories/blocks/vectordb_block.py` | VectorDBBlock 实现 |
| `camel/memories/agent_memories.py` | ChatHistoryMemory、VectorDBMemory、LongtermAgentMemory |
| `camel/memories/context_creators/score_based.py` | ScoreBasedContextCreator 实现 |
| `camel/storages/key_value_storages/base.py` | BaseKeyValueStorage 接口 |
| `camel/storages/key_value_storages/in_memory.py` | 内存存储实现 |
| `camel/storages/vectordb_storages/base.py` | BaseVectorStorage 接口和模型 |
| `camel/storages/vectordb_storages/qdrant.py` | QdrantStorage 实现 |
| `camel/embeddings/base.py` | BaseEmbedding 接口 |

---

## 13. 总结

CAMEL 的记忆系统具有以下核心特点：

**分层架构**：从底层存储到高层 Agent 接口，每层职责清晰

**存储抽象**：统一的存储接口，支持多种后端无缝切换

**检索灵活**：滑动窗口 + 向量语义，支持多种检索策略

**可扩展性**：通过继承和组合，易于添加新的记忆类型

**生产就绪**：支持持久化、多 Agent 隔离、Token 优化等生产级需求

与 smolagents 相比，CAMEL 的记忆系统更加完善和复杂，适合需要长期记忆、大规模检索和多 Agent 协作的场景。smolagents 则更适合快速原型和简单对话场景。
