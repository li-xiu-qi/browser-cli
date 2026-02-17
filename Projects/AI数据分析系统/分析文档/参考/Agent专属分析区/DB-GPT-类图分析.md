# DB-GPT 核心类关系分析

> **分析日期**: 2026-02-05  
> **分析重点**: 记忆系统、对话管理、Agent 架构的类继承与组合关系

---

## 1. 记忆系统类图

### 1.1 核心继承结构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           记忆系统核心类继承关系                                │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────────┐
                            │   <<abstract>>   │
                            │  MemoryFragment  │
                            │   (base.py:41)   │
                            └────────┬─────────┘
                                     │ ▲
                                     │ │ (real_memory_fragment_class)
                                     │ │
                            ┌────────▼─────────┐
                            │  <<abstract>>    │
                            │  Memory<T>       │
                            │  (base.py:338)   │
                            └────────┬─────────┘
                                     │
            ┌────────────────────────┼────────────────────────┐
            │                        │                        │
            ▼                        ▼                        ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│   SensoryMemory     │  │   ShortTermMemory   │  │    LongTermMemory   │
│    (base.py:620)    │  │    (base.py:705)    │  │   (long_term.py:181)│
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ - _buffer_size: int │  │ - _buffer_size: int │  │ - vector_store      │
│ - _fragments: List  │  │ - _fragments: List  │  │ - memory_retriever  │
│ - _lock: asyncio.Lock│ │ - _lock: asyncio.Lock│ │ - aggregate_importance│
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│ + write()           │  │ + write()           │  │ + write()           │
│ + read()            │  │ + read()            │  │ + read()            │
│ + handle_overflow() │  │ + transfer_to_long()│  │ + fetch_memories()  │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
            │                        │                        │
            │                        ▼                        │
            │            ┌─────────────────────┐              │
            │            │ EnhancedShortTerm   │              │
            │            │    (short_term.py)  │              │
            │            ├─────────────────────┤              │
            │            │ - _embeddings       │              │
            │            │ - short_embeddings  │              │
            │            │ - enhance_cnt: List │              │
            │            │ - enhance_memories  │              │
            │            │ - enhance_threshold │              │
            │            ├─────────────────────┤              │
            │            │ + handle_overflow() │              │
            │            │   (按重要性淘汰)     │              │
            │            └─────────────────────┘              │
            │                                                 │
            └─────────────────────┬───────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────────┐
                    │        HybridMemory         │
                    │     (hybrid.py:31)          │
                    ├─────────────────────────────┤
                    │ - _sensory_memory           │
                    │ - _short_term_memory        │
                    │ - _long_term_memory         │
                    │ - _default_insight_extractor│
                    ├─────────────────────────────┤
                    │ + write()                   │
                    │ + read()                    │
                    │ + write_batch()             │
                    │ + fetch_memories()          │
                    └─────────────────────────────┘
```

### 1.2 记忆片段类

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AgentMemoryFragment 类                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                    AgentMemoryFragment                         │
│                   (agent_memory.py:38)                         │
├────────────────────────────────────────────────────────────────┤
│ 属性                                                           │
├────────────────────────────────────────────────────────────────┤
│ - observation: str              # 原始观察内容                  │
│ - _embeddings: List[float]      # 向量表示                      │
│ - memory_id: int                # 雪花算法ID                   │
│ - _importance: float            # 重要性分数 (0-10)             │
│ - _last_accessed_time: datetime # 最后访问时间                  │
│ - _is_insight: bool             # 是否为洞察                   │
├────────────────────────────────────────────────────────────────┤
│ 方法                                                           │
├────────────────────────────────────────────────────────────────┤
│ + build_from(...) → AgentMemoryFragment    # 工厂方法          │
│ + update_importance(score) → float         # 更新重要性        │
│ + update_embeddings(embeddings)            # 更新向量          │
│ + calculate_current_embeddings(func)       # 计算向量          │
│ + update_accessed_time(now)                # 更新时间戳        │
│ + copy() → AgentMemoryFragment             # 深拷贝            │
│ + reduce(fragments) → AgentMemoryFragment  # 合并多个片段      │
└────────────────────────────────────────────────────────────────┘
                                   ▲
                                   │
                                   │
┌──────────────────────────────────┴──────────────────────────────┐
│              StructuredAgentMemoryFragment                      │
│                   (agent_memory.py:187)                         │
├─────────────────────────────────────────────────────────────────┤
│ - _structured_observation: Union[dict, List[dict]]              │
├─────────────────────────────────────────────────────────────────┤
│ + to_raw_observation(obs) → str       # JSON 序列化             │
│ + reduce(fragments) → ...             # 结构化合并              │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 GPTs 消息记忆类

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GPTs 消息记忆体系                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                       GptsMessage                              │
│                   (gpts/base.py:52)                            │
├────────────────────────────────────────────────────────────────┤
│ - conv_id: str                                                 │
│ - sender: str                                                  │
│ - receiver: str                                                │
│ - role: str                                                    │
│ - content: str                                                 │
│ - rounds: int = 0                                              │
│ - current_goal: Optional[str]      # 意图追踪关键字段          │
│ - action_report: Optional[str]                                 │
│ - model_name: Optional[str]                                    │
│ - created_at: datetime                                         │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                    <<interface>>                               │
│                   GptsMessageMemory                            │
│                   (gpts/base.py:194)                           │
├────────────────────────────────────────────────────────────────┤
│ + append(message)                                              │
│ + get_by_agent(conv_id, agent) → List[GptsMessage]             │
│ + get_between_agents(conv_id, a1, a2) → List[GptsMessage]      │
│ + get_by_conv_id(conv_id) → List[GptsMessage]                  │
│ + get_last_message(conv_id) → Optional[GptsMessage]            │
│ + delete_by_conv_id(conv_id)                                   │
└────────────────────────────────────────────────────────────────┘
                               ▲
                               │ implements
                               │
                    ┌──────────┴──────────┐
                    │  DefaultGptsMessageMemory
                    │  (gpts/default_gpts_memory.py)
                    └─────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                         GptsMemory                             │
│                   (gpts/gpts_memory.py:24)                     │
├────────────────────────────────────────────────────────────────┤
│ - _plans_memory: GptsPlansMemory                               │
│ - _message_memory: GptsMessageMemory                           │
│ - messages_cache: defaultdict                                  │
│ - channels: defaultdict<asyncio.Queue>    # 流式消息队列       │
│ - enable_vis_map: defaultdict                                  │
├────────────────────────────────────────────────────────────────┤
│ + init(conv_id, ...)                                           │
│ + append_message(conv_id, message)                             │
│ + get_messages(conv_id) → List[GptsMessage]                    │
│ + push_message(conv_id) → 推送到流式队列                       │
│ + chat_messages(conv_id) → AsyncGenerator  # SSE 流            │
│ + app_link_chat_message(conv_id) → str   # 按目标分组渲染      │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. 对话系统类图

### 2.1 消息类型体系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           消息类型继承体系                                    │
└─────────────────────────────────────────────────────────────────────────────┘

                            ┌──────────────────┐
                            │  <<abstract>>    │
                            │   BaseMessage    │
                            │(message.py:24)   │
                            ├──────────────────┤
                            │ - content        │
                            │ - index: int     │
                            │ - round_index    │
                            │ - additional_kwargs
                            ├──────────────────┤
                            │ + type() -> str  │
                            │ + to_dict()      │
                            │ + last_text      │
                            └────────┬─────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   HumanMessage   │      │    AIMessage     │      │  SystemMessage   │
│(message.py:124)  │      │ (message.py:135) │      │ (message.py:165) │
├──────────────────┤      ├──────────────────┤      ├──────────────────┤
│ type = "human"   │      │ type = "ai"      │      │ type = "system"  │
│ example: bool    │      │ example: bool    │      └──────────────────┘
└──────────────────┘      └──────────────────┘
                                   │
                                   │ extends
                                   ▼
                          ┌──────────────────┐
                          │   ViewMessage    │
                          │(message.py:146)  │
                          ├──────────────────┤
                          │ type = "view"    │
                          │ pass_to_model =  │
                          │   False          │
                          └──────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                      ModelMessage                              │
│                   (message.py:183)                             │
├────────────────────────────────────────────────────────────────┤
│ 用于与 LLM Server 通信的标准化消息格式                           │
├────────────────────────────────────────────────────────────────┤
│ - role: str                   # system/human/ai/view           │
│ - content: Union[str, List[MediaContent]]                      │
│ - round_index: int                                             │
├────────────────────────────────────────────────────────────────┤
│ + from_base_messages(messages) → List[ModelMessage]            │
│ + from_openai_messages(messages) → List[ModelMessage]          │
│ + to_common_messages(messages) → List[Dict]                    │
│ + messages_to_string(...) → str                                │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 对话管理类

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OnceConversation 类                                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                    OnceConversation                            │
│                   (message.py:713)                             │
├────────────────────────────────────────────────────────────────┤
│ 状态属性                                                       │
├────────────────────────────────────────────────────────────────┤
│ - chat_mode: str                    # 对话模式                 │
│ - user_name: Optional[str]                                     │
│ - sys_code: Optional[str]                                      │
│ - summary: Optional[str]                                       │
│ - app_code: Optional[str]                                      │
│ - messages: List[BaseMessage]       # 消息列表                 │
│ - start_date: str                                              │
│ - chat_order: int = 0               # 当前轮次                 │
│ - _message_index: int = 0           # 消息序号                 │
│ - model_name: str                                              │
│ - tokens: int                                                  │
│ - cost: int                                                    │
├────────────────────────────────────────────────────────────────┤
│ 轮次管理                                                       │
├────────────────────────────────────────────────────────────────┤
│ + start_new_round()                    # 开始新轮次            │
│ + end_current_round()                  # 结束当前轮次          │
├────────────────────────────────────────────────────────────────┤
│ 消息操作                                                       │
├────────────────────────────────────────────────────────────────┤
│ + add_user_message(message)                                │
│ + add_ai_message(message, update_if_exist=False)           │
│ + add_system_message(message)                              │
│ + add_view_message(message)                                │
│ + _append_message(message)                                 │
├────────────────────────────────────────────────────────────────┤
│ 轮次感知查询                                                   │
├────────────────────────────────────────────────────────────────┤
│ + get_messages_by_round(round_index) → List[BaseMessage]     │
│ + get_latest_round() → List[BaseMessage]                     │
│ + get_messages_with_round(round_count) → List[BaseMessage]   │
└────────────────────────────────────────────────────────────────┘
```

### 2.3 存储抽象接口

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         存储接口体系                                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                   <<interface>>                                │
│               StorageInterface<T, TData>                       │
│                  (storage.py:193)                              │
├────────────────────────────────────────────────────────────────┤
│ + save(data: T)                                                │
│ + update(data: T)                                              │
│ + save_or_update(data: T)                                      │
│ + load(resource_id, cls) → Optional[T]                         │
│ + delete(resource_id)                                          │
│ + query(spec, cls) → List[T]                                   │
│ + count(spec, cls) → int                                       │
│ + paginate_query(page, page_size, cls, spec)                   │
└────────────────────────────────────────────────────────────────┘
                               ▲
                               │ extends
                               │
                    ┌──────────┴──────────┐
                    │   InMemoryStorage   │
                    │  (storage.py:410)   │
                    ├─────────────────────┤
                    │ - _data: Dict[str,  │
                    │         bytes]      │
                    └─────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                   StorageConversation                          │
│                   (conversation.py)                            │
├────────────────────────────────────────────────────────────────┤
│ 对话存储封装，组合 conv_storage + message_storage               │
├────────────────────────────────────────────────────────────────┤
│ - conv_uid: str                                                │
│ - chat_mode: str                                               │
│ - conv_storage: StorageInterface                               │
│ - message_storage: StorageInterface                            │
├────────────────────────────────────────────────────────────────┤
│ + save()                                                       │
│ + load()                                                       │
│ + delete()                                                     │
│ + clear()                                                      │
└────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent 架构类图

### 3.1 Agent 核心接口

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent 接口体系                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                   <<interface>>                                │
│                       Agent                                    │
│                    (agent.py:16)                               │
├────────────────────────────────────────────────────────────────┤
│ 核心消息方法                                                   │
├────────────────────────────────────────────────────────────────┤
│ + send(message, recipient, reviewer, request_reply, ...)       │
│ + receive(message, sender, reviewer, request_reply, ...)       │
│ + generate_reply(received_message, sender, reviewer, ...)      │
├────────────────────────────────────────────────────────────────┤
│ 思考与行动                                                     │
├────────────────────────────────────────────────────────────────┤
│ + thinking(messages, sender, prompt) → Tuple[str, str]         │
│ + review(message, censored) → Tuple[bool, Any]                 │
│ + act(message, sender, reviewer, ...) → ActionOutput           │
│ + verify(message, sender, reviewer) → Tuple[bool, str]         │
├────────────────────────────────────────────────────────────────┤
│ 属性                                                           │
├────────────────────────────────────────────────────────────────┤
│ + name → str                                                   │
│ + role → str                                                   │
│ + desc → Optional[str]                                         │
└────────────────────────────────────────────────────────────────┘
                               ▲
                               │ extends
                               │
                    ┌──────────┴──────────────────┐
                    │      ConversableAgent       │
                    │   (base_agent.py:37)        │
                    ├─────────────────────────────┤
                    │ - agent_context: AgentContext
                    │ - actions: List[Action]     │
                    │ - llm_config: LLMConfig     │
                    │ - memory: AgentMemory       │
                    │ - max_retry_count: int = 3  │
                    │ - max_timeout: int = 600    │
                    │ - stream_out: bool = True   │
                    ├─────────────────────────────┤
                    │ + build() → ConversableAgent│
                    │ + bind(target) → ...        │
                    │ + initiate_chat(...)        │
                    │ + prepare_act_param(...)    │
                    │ + adjust_final_message(...) │
                    └─────────────────────────────┘
```

### 3.2 Agent 上下文类

```
┌────────────────────────────────────────────────────────────────┐
│                      AgentContext                              │
│                    (agent.py:195)                              │
├────────────────────────────────────────────────────────────────┤
│ - conv_id: str                        # 会话唯一标识           │
│ - gpts_app_code: Optional[str]                                 │
│ - gpts_app_name: Optional[str]                                 │
│ - language: Optional[str]                                      │
│ - max_chat_round: int = 100           # 最大对话轮次           │
│ - max_retry_round: int = 10           # 最大重试轮次           │
│ - max_new_tokens: int = 1024          # 最大生成长度           │
│ - temperature: float = 0.5            # 采样温度               │
│ - enable_vis_message: bool = True     # 是否启用 VIS 协议      │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                      AgentMessage                              │
│                    (agent.py:273)                              │
├────────────────────────────────────────────────────────────────┤
│ - content: Optional[str]                                       │
│ - name: Optional[str]                                          │
│ - rounds: int = 0                                              │
│ - context: Optional[MessageContextType]                        │
│ - action_report: Optional[ActionReportType]                    │
│ - review_info: Optional[AgentReviewInfo]                       │
│ - current_goal: Optional[str]          # 当前目标/意图         │
│ - model_name: Optional[str]                                    │
│ - role: Optional[str]                                          │
│ - success: bool = True                                         │
│ - resource_info: Optional[ResourceReferType]                   │
├────────────────────────────────────────────────────────────────┤
│ + to_dict() → Dict                                             │
│ + to_llm_message() → Dict                                      │
│ + copy() → AgentMessage                                        │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                     AgentReviewInfo                            │
│                    (agent.py:256)                              │
├────────────────────────────────────────────────────────────────┤
│ - approve: bool = False                                        │
│ - comments: Optional[str]                                      │
└────────────────────────────────────────────────────────────────┘
```

### 3.3 AgentMemory 封装类

```
┌────────────────────────────────────────────────────────────────┐
│                      AgentMemory                               │
│                   (agent_memory.py:275)                        │
├────────────────────────────────────────────────────────────────┤
│ 组合关系                                                       │
├────────────────────────────────────────────────────────────────┤
│ - memory: Memory[AgentMemoryFragment]    # 核心记忆接口        │
│ - importance_scorer: ImportanceScorer    # 重要性评分器        │
│ - insight_extractor: InsightExtractor    # 洞察提取器          │
│ - gpts_memory: GptsMemory                # GPTs 消息记忆       │
├────────────────────────────────────────────────────────────────┤
│ 代理方法                                                       │
├────────────────────────────────────────────────────────────────┤
│ + write(memory_fragment)                                       │
│ + write_batch(memory_fragments)                                │
│ + read(observation) → List[AgentMemoryFragment]                │
│ + clear()                                                      │
├────────────────────────────────────────────────────────────────┤
│ 便捷访问                                                       │
├────────────────────────────────────────────────────────────────┤
│ + plans_memory → GptsPlansMemory                               │
│ + message_memory → GptsMessageMemory                           │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. 召回器类图

### 4.1 时间加权召回器

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         召回器继承体系                                        │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────┐
                    │    EmbeddingRetriever    │
                    │    (embedding.py)        │
                    └───────────┬──────────────┘
                                │ extends
                                ▼
                    ┌──────────────────────────┐
                    │ TimeWeightedEmbeddingRetriever
                    │ (time_weighted.py:47)    │
                    ├──────────────────────────┤
                    │ - memory_stream: List[Chunk]
                    │ - decay_rate: float = 0.01
                    │ - default_salience: Optional[float]
                    │ - _top_k: int = 100
                    │ - _k: int = 4
                    │ - _external_storage
                    ├──────────────────────────┤
                    │ + load_document(chunks)  │
                    │ + _retrieve(query)       │
                    │ + get_salient_docs(query)│
                    │ + _get_combined_score()  │
                    └───────────┬──────────────┘
                                │ extends
                                ▼
                    ┌──────────────────────────┐
                    │   LongTermRetriever      │
                    │ (long_term.py:24)        │
                    ├──────────────────────────┤
                    │ - now: datetime          │
                    │ + _retrieve(query,       │
                    │   filters) → List[Chunk] │
                    │ + _retrieve_vector_      │
                    │   store_only()           │
                    └──────────────────────────┘
```

---

## 5. 数据库模型类图

### 5.1 对话历史实体

```
┌────────────────────────────────────────────────────────────────┐
│                    ChatHistoryEntity                           │
│               (chat_history_db.py:25)                          │
├────────────────────────────────────────────────────────────────┤
│ SQLAlchemy 实体类                                               │
├────────────────────────────────────────────────────────────────┤
│ - id: Integer (PK)                                             │
│ - conv_uid: String(255) (UK)          # 会话唯一ID             │
│ - chat_mode: String(255)              # 对话模式               │
│ - summary: Text                       # 会话摘要               │
│ - user_name: String(255)              # 用户名                 │
│ - messages: Text                      # 消息详情(JSON)         │
│ - message_ids: Text                   # 消息ID列表             │
│ - sys_code: String(128)               # 系统代码               │
│ - app_code: String(255)               # 应用代码               │
│ - gmt_created: DateTime                                        │
│ - gmt_modified: DateTime                                       │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                  ChatHistoryMessageEntity                      │
│               (chat_history_db.py:63)                          │
├────────────────────────────────────────────────────────────────┤
│ - id: Integer (PK)                                             │
│ - conv_uid: String(255)               # 关联会话               │
│ - index: Integer                      # 消息索引               │
│ - round_index: Integer                # 轮次索引               │
│ - message_detail: Text                # 消息详情(JSON)         │
│ - gmt_created: DateTime                                        │
│ - gmt_modified: DateTime                                       │
├────────────────────────────────────────────────────────────────┤
│ UK: (conv_uid, index)                                          │
└────────────────────────────────────────────────────────────────┘
```

---

## 6. 类关系总结

### 6.1 组合关系图

```
AgentMemory (组合)
├── Memory (多态)
│   ├── SensoryMemory
│   ├── ShortTermMemory → EnhancedShortTermMemory
│   └── LongTermMemory (组合) → VectorStore
│
├── ImportanceScorer (可选)
│   └── LLMImportanceScorer
│
├── InsightExtractor (可选)
│   └── LLMInsightExtractor
│
└── GptsMemory (组合)
    ├── GptsPlansMemory
    └── GptsMessageMemory

ConversableAgent (继承 + 组合)
├── Agent (接口)
├── Role (继承)
├── AgentMemory (组合)
├── List<Action> (组合)
├── LLMConfig (组合)
└── AgentContext (组合)

OnceConversation (组合)
├── List<BaseMessage>
│   ├── HumanMessage
│   ├── AIMessage
│   ├── SystemMessage
│   └── ViewMessage
└── metadata (dict)
```

### 6.2 关键设计模式

| 模式 | 应用位置 | 说明 |
|------|----------|------|
| **策略模式** | `Memory[T]` 接口 | 三种记忆实现可互换 |
| **模板方法** | `ConversableAgent.generate_reply()` | 定义算法骨架，子类可扩展 |
| **工厂模式** | `AgentMemoryFragment.build_from()` | 统一创建记忆片段 |
| **观察者模式** | `GptsMemory.channels` | 流式消息推送 |
| **装饰器模式** | `EnhancedShortTermMemory` | 增强短期记忆功能 |
| **代理模式** | `AgentMemory` | 为 `Memory` 提供统一封装 |

---

*分析完成于 2026-02-05*
