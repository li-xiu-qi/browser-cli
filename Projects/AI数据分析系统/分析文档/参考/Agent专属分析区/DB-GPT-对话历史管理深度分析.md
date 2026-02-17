# DB-GPT 对话历史管理深度分析

**分析日期**: 2026-02-05  
**分析对象**: DB-GPT 项目对话历史管理机制  
**分析重点**: 前端对话记录管理、后端 Agent 运行时对话历史管理、数据库存储层

---

## 目录

1. [架构总览](#1-架构总览)
2. [前端对话管理架构](#2-前端对话管理架构)
3. [后端 Agent 运行时历史管理](#3-后端-agent-运行时历史管理)
4. [数据库存储设计](#4-数据库存储设计)
5. [多轮对话流程时序](#5-多轮对话流程时序)
6. [关键代码分析](#6-关键代码分析)
7. [对我们项目的启示](#7-对我们项目的启示)

---

## 1. 架构总览

### 1.1 整体架构图

### 1.2 核心概念区分

| 概念 | 说明 | 对应代码 |
|------|------|----------|
| **前端展示的对话记录** | UI 层渲染的消息列表，包含 view 类型消息用于展示 | `web/pages/chat/index.tsx` 中的 `history` 状态 |
| **Agent 实际使用的对话历史** | Agent 内部运行的消息流，使用 GptsMessage 结构 | `packages/dbgpt-core/src/dbgpt/agent/core/memory/gpts/base.py` |
| **持久化存储的对话历史** | 数据库存储的消息记录，支持消息独立存储 | `chat_history` 和 `chat_history_message` 表 |

---

## 2. 前端对话管理架构

### 2.1 前端状态管理

**核心文件**: `web/app/chat-context.tsx` (第 12-76 行)

```typescript
// 前端对话状态核心结构
interface IChatContext {
  chatId: string;                    // 当前对话 ID (从 URL 获取)
  scene: string;                     // 当前场景 (chat_mode)
  history: ChatHistoryResponse;      // 当前对话历史记录
  setHistory: (val: ChatHistoryResponse) => void;
  dialogueList?: DialogueListResponse; // 对话列表
  // ... 其他状态
}
```

**对话历史状态定义** (`web/types/chat.ts`):
```typescript
type ChatHistoryResponse = Array<{
  role: 'human' | 'ai' | 'view' | 'system';
  context: string;
  order: number;
  model_name?: string;
  time_stamp?: number;
  thinking?: boolean;
  feedback?: Record<string, any>;
}>;
```

### 2.2 对话列表管理

**API 调用** (`web/client/api/request.ts` 第 104-106 行):
```typescript
export const getDialogueList = () => {
  return GET<null, DialogueListResponse>('/api/v1/chat/dialogue/list');
};
```

**前端缓存策略**:
- 对话列表通过 `useRequest` hook 获取并缓存
- 当前对话历史仅在进入对话时加载 (`web/pages/chat/index.tsx` 第 326-336 行)
- 历史记录按 `role === 'view'` 过滤显示

### 2.3 消息渲染逻辑

**消息类型处理** (`web/pages/chat/index.tsx` 第 184-188 行):
```typescript
// 从历史记录中过滤 view 类型的消息用于显示
const viewList = res?.filter(item => item.role === 'view');
if (viewList && viewList.length > 0) {
  order.current = viewList[viewList.length - 1].order + 1;
}
```

### 2.4 前后端状态同步机制

**获取历史记录** (`web/client/api/request.ts` 第 116-118 行):
```typescript
export const getChatHistory = (convId: string) => {
  return GET<null, ChatHistoryResponse>(`/api/v1/chat/dialogue/messages/history?con_uid=${convId}`);
};
```

**实时消息流** (`web/hooks/use-chat.ts` 第 25-124 行):
- 使用 SSE (Server-Sent Events) 接收流式响应
- 支持 `chat_agent` 场景下的可视化消息 (`parsedData.vis`)
- 消息结束标记: `[DONE]`

---

## 3. 后端 Agent 运行时历史管理

![DB-GPT-后端服务架构图.svg](graphviz/DB-GPT-后端服务架构图.svg)

### 3.1 Agent 内存架构

**核心类**: `GptsMemory` (`packages/dbgpt-core/src/dbgpt/agent/core/memory/gpts/gpts_memory.py` 第 24-44 行)

```python
class GptsMemory:
    """GPTs memory."""
    
    def __init__(
        self,
        plans_memory: Optional[GptsPlansMemory] = None,
        message_memory: Optional[GptsMessageMemory] = None,
        executor: Optional[Executor] = None,
    ):
        self._plans_memory: GptsPlansMemory = ...
        self._message_memory: GptsMessageMemory = ...
        self._executor = executor or ThreadPoolExecutor(max_workers=2)
        
        # 内存缓存结构
        self.messages_cache: defaultdict = defaultdict(list)  # conv_id -> messages
        self.channels: defaultdict = defaultdict(Queue)       # conv_id -> Queue
        self.enable_vis_map: defaultdict = defaultdict(bool)  # conv_id -> bool
        self.start_round_map: defaultdict = defaultdict(int)  # conv_id -> int
```

### 3.2 Agent 消息模型

**GptsMessage 结构** (`packages/dbgpt-core/src/dbgpt/agent/core/memory/gpts/base.py` 第 52-101 行):

```python
@dataclasses.dataclass
class GptsMessage:
    """Gpts message."""
    
    conv_id: str              # 对话 ID
    sender: str               # 发送者角色
    receiver: str             # 接收者角色
    role: str                 # 消息角色
    content: str              # 消息内容
    rounds: int = 0           # 轮次
    is_success: bool = True   # 是否成功
    app_code: Optional[str] = None
    app_name: Optional[str] = None
    current_goal: Optional[str] = None  # 当前目标
    context: Optional[str] = None       # 上下文
    review_info: Optional[str] = None   # 审核信息
    action_report: Optional[str] = None # 动作报告
    model_name: Optional[str] = None    # 模型名称
    resource_info: Optional[str] = None # 资源信息
    created_at: datetime = ...
    updated_at: datetime = ...
```

### 3.3 Agent 如何获取对话历史

**从内存缓存获取** (`packages/dbgpt-core/src/dbgpt/agent/core/memory/gpts/gpts_memory.py` 第 132-139 行):
```python
async def get_messages(self, conv_id: str) -> List[GptsMessage]:
    """Get message by conv_id."""
    messages = self.messages_cache[conv_id]
    if not messages:
        messages = await blocking_func_to_async(
            self._executor, self.message_memory.get_by_conv_id, conv_id
        )
    return messages
```

**获取特定 Agent 的历史** (`packages/dbgpt-core/src/dbgpt/agent/core/memory/gpts/gpts_memory.py` 第 152-179 行):
```python
async def get_agent_history_memory(
    self, conv_id: str, agent_role: str
) -> List[ActionOutput]:
    """Get agent history memory."""
    agent_messages = await blocking_func_to_async(
        self._executor, self.message_memory.get_by_agent, conv_id, agent_role
    )
    # 将消息转换为 ActionOutput 列表
    ...
```

### 3.4 Agent 执行时如何更新对话历史

**消息追加流程** (`packages/dbgpt-core/src/dbgpt/agent/core/base_agent.py` 第 756-809 行):
```python
async def _a_append_message(
    self, message: AgentMessage, role, sender: Agent
) -> bool:
    """追加消息到内存和存储."""
    gpts_message: GptsMessage = GptsMessage(
        conv_id=self.not_null_agent_context.conv_id,
        sender=sender.role,
        receiver=self.role,
        role=role,
        rounds=message.rounds,
        is_success=message.success,
        # ... 其他字段
    )
    
    # 保存到 GptsMemory
    await self.memory.gpts_memory.append_message(
        self.not_null_agent_context.conv_id, gpts_message
    )
```

**消息追加到缓存和存储** (`packages/dbgpt-core/src/dbgpt/agent/core/memory/gpts/gpts_memory.py` 第 122-130 行):
```python
async def append_message(self, conv_id: str, message: GptsMessage):
    """Append message."""
    # 1. 追加到内存缓存
    self.messages_cache[conv_id].append(message)
    
    # 2. 异步保存到持久化存储
    await blocking_func_to_async(
        self._executor, self.message_memory.append, message
    )
    
    # 3. 推送消息到前端
    await self.push_message(conv_id)
```

### 3.5 多轮对话中历史如何传递给 LLM

**Agent 思考过程** (`packages/dbgpt-core/src/dbgpt/agent/core/base_agent.py` 第 554-603 行):
```python
async def thinking(
    self,
    messages: List[AgentMessage],
    sender: Optional[Agent] = None,
    prompt: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """思考过程 - 将消息传递给 LLM."""
    # 转换为 LLM 消息格式
    llm_messages = [message.to_llm_message() for message in messages]
    
    # 调用 LLM
    response = await self.llm_client.create(
        context=llm_messages[-1].pop("context", None),
        messages=llm_messages,
        llm_model=llm_model,
        # ... 其他参数
    )
```

### 3.6 对话历史的裁剪/压缩策略

**StorageConversation 的轮次管理** (`packages/dbgpt-core/src/dbgpt/core/interface/message.py` 第 918-965 行):
```python
def get_messages_with_round(self, round_count: int) -> List[BaseMessage]:
    """获取指定轮数的消息.
    
    如果 round_count 为 1, 则不包含历史消息.
    """
    latest_round_index = self.chat_order
    start_round_index = max(1, latest_round_index - round_count + 1)
    messages = []
    for round_index in range(start_round_index, latest_round_index + 1):
        messages.extend(self.get_messages_by_round(round_index))
    return messages
```

**获取模型消息** (`packages/dbgpt-core/src/dbgpt/core/interface/message.py` 第 967-1024 行):
```python
def get_model_messages(self) -> List[ModelMessage]:
    """获取传递给模型的消息.
    
    只包含 pass_to_model=True 的消息 (human, ai, system)
    不包含 view 类型消息
    """
    messages = []
    for message in self.messages:
        if message.pass_to_model:
            messages.append(
                ModelMessage(
                    role=message.type,
                    content=message.content,
                    round_index=message.round_index,
                )
            )
    return messages
```

### 3.7 并发对话隔离机制

**对话 ID 隔离**:
- 每个对话通过 `conv_uid` (UUID) 唯一标识
- `GptsMemory` 使用 `defaultdict` 按 `conv_id` 隔离缓存
- 数据库层通过 `conv_uid` 字段隔离不同对话的消息

**Agent 上下文隔离** (`packages/dbgpt-core/src/dbgpt/agent/core/base_agent.py` 第 165-179 行):
```python
async def build(self, is_retry_chat: bool = False) -> "ConversableAgent":
    """构建 Agent."""
    real_conv_id, _ = parse_conv_id(self.not_null_agent_context.conv_id)
    
    # 为每个 Agent 创建独立的内存会话
    memory_session = f"{real_conv_id}_{self.role}_{self.name}"
    self.memory.initialize(
        self.name,
        self.llm_config.llm_client,
        importance_scorer=self.memory_importance_scorer,
        insight_extractor=self.memory_insight_extractor,
        session_id=memory_session,
    )
```

---

## 4. 数据库存储设计

![DB-GPT-数据库模型图.svg](graphviz/DB-GPT-数据库模型图.svg)

### 4.1 数据库表结构

**对话主表**: `chat_history` (`packages/dbgpt-core/src/dbgpt/storage/chat_history/chat_history_db.py` 第 25-61 行)

```python
class ChatHistoryEntity(Model):
    """Chat history entity."""
    
    __tablename__ = "chat_history"
    __table_args__ = (UniqueConstraint("conv_uid", name="uk_conv_uid"),)
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_uid = Column(String(255), unique=False, nullable=False, comment="对话唯一ID")
    chat_mode = Column(String(255), nullable=False, comment="对话场景模式")
    summary = Column(Text(length=2**31 - 1), nullable=False, comment="对话摘要")
    user_name = Column(String(255), nullable=True, comment="用户")
    messages = Column(Text(length=2**31 - 1), nullable=True, comment="对话详情(旧格式)")
    message_ids = Column(Text(length=2**31 - 1), nullable=True, comment="消息ID列表")
    sys_code = Column(String(128), index=True, nullable=True, comment="系统代码")
    app_code = Column(String(255), nullable=True, comment="应用代码")
    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now)
    
    # 索引
    Index("idx_q_user", "user_name")
    Index("idx_q_mode", "chat_mode")
    Index("idx_q_conv", "summary")
    Index("idx_chat_his_app_code", "app_code")
```

**消息独立存储表**: `chat_history_message` (`packages/dbgpt-core/src/dbgpt/storage/chat_history/chat_history_db.py` 第 63-86 行)

```python
class ChatHistoryMessageEntity(Model):
    """Chat history message entity."""
    
    __tablename__ = "chat_history_message"
    __table_args__ = (
        UniqueConstraint("conv_uid", "index", name="uk_conversation_message"),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_uid = Column(String(255), nullable=False, comment="对话唯一ID")
    index = Column(Integer, nullable=False, comment="消息索引")
    round_index = Column(Integer, nullable=False, comment="消息轮次索引")
    message_detail = Column(Text(length=2**31 - 1), nullable=True, comment="消息详情(JSON)")
    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now)
```

### 4.2 Message 模型字段设计

**核心消息模型** (`packages/dbgpt-core/src/dbgpt/core/interface/message.py` 第 24-172 行):

```python
class BaseMessage(BaseModel, ABC):
    """Message object."""
    
    content: MessageContentType           # 消息内容 (str 或 MediaContent 列表)
    index: int = 0                        # 消息索引
    round_index: int = 0                  # 消息轮次
    additional_kwargs: dict = Field(default_factory=dict)  # 额外参数

class HumanMessage(BaseMessage):
    """用户消息."""
    example: bool = False
    @property
    def type(self) -> str: return "human"

class AIMessage(BaseMessage):
    """AI 消息."""
    example: bool = False
    @property
    def type(self) -> str: return "ai"

class ViewMessage(BaseMessage):
    """视图消息 - 仅用于前端展示，不传给模型."""
    @property
    def pass_to_model(self) -> bool: return False
    @property
    def type(self) -> str: return "view"

class SystemMessage(BaseMessage):
    """系统消息."""
    @property
    def type(self) -> str: return "system"
```

### 4.3 对话与消息的关联关系

![DB-GPT-数据库模型图.svg](graphviz/DB-GPT-数据库模型图.svg)

**存储适配器** (`packages/dbgpt-core/src/dbgpt/storage/chat_history/storage_adapter.py`):
- `DBStorageConversationItemAdapter`: 对话对象 ↔ 数据库实体转换
- `DBMessageStorageItemAdapter`: 消息对象 ↔ 数据库实体转换

### 4.4 存储策略

**独立存储模式** (`packages/dbgpt-core/src/dbgpt/core/interface/message.py` 第 1223 行):
```python
def __init__(
    self,
    conv_uid: str,
    save_message_independent: bool = True,  # 是否独立存储消息
    conv_storage: Optional[StorageInterface] = None,
    message_storage: Optional[StorageInterface] = None,
    **kwargs
):
```

- `save_message_independent=True`: 消息独立存储到 `chat_history_message` 表
- `save_message_independent=False`: 消息作为 JSON 存储在 `chat_history.messages` 字段 (旧模式)

---

## 5. 多轮对话流程时序

完整的多轮对话时序图展示了以下流程：
1. 新建对话流程
2. 获取历史记录流程
3. 发送消息主流程（SSE 流式响应）
4. 多轮对话历史传递

### 5.1 新建对话流程

### 5.2 发送消息完整流程

### 5.3 获取历史记录流程

---

## 6. 关键代码分析

### 6.1 前端关键代码

**ChatContext 状态管理** (`web/app/chat-context.tsx` 第 12-76 行)
```typescript
interface IChatContext {
  chatId: string;                    // 当前对话 ID
  scene: IChatDialogueSchema['chat_mode'];
  history: ChatHistoryResponse;      // 对话历史
  setHistory: (val: ChatHistoryResponse) => void;
  dialogueList?: DialogueListResponse;
  // ...
}
```

**useChat Hook** (`web/hooks/use-chat.ts` 第 25-124 行)
```typescript
const useChat = ({ queryAgentURL = '/api/v1/chat/completions', app_code }: Props) => {
  const chat = useCallback(async ({ data, chatId, onMessage, onClose, onDone, onError, ctrl }: ChatParams) => {
    // SSE 流式请求
    await fetchEventSource(`${process.env.API_BASE_URL ?? ''}${queryAgentURL}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', [HEADER_USER_ID_KEY]: getUserId() ?? '' },
      body: JSON.stringify({ conv_uid: chatId, app_code, ...data }),
      signal: ctrl ? ctrl.signal : null,
      onmessage: event => {
        // 处理流式消息
        let message = event.data;
        // ... 解析消息
        if (message === '[DONE]') {
          onDone?.();
        } else {
          onMessage?.(message);
        }
      },
    });
  }, [queryAgentURL, app_code, scene]);
  
  return { chat, ctrl };
};
```

### 6.2 后端关键代码

**Conversation Service** (`packages/dbgpt-serve/src/dbgpt_serve/conversation/service/service.py` 第 187-230 行)
```python
def get_history_messages(
    self, request: Union[ServeRequest, Dict[str, Any]]
) -> List[MessageVo]:
    """获取对话历史消息."""
    conv: StorageConversation = self.create_storage_conv(request)
    result = []
    messages = _append_view_messages(conv.messages)  # 添加 view 消息用于展示
    
    for msg in messages:
        result.append(
            MessageVo(
                role=msg.type,
                context=vis_name_change(msg.get_view_markdown_text(file_serve.replace_uri)),
                order=msg.round_index,
                model_name=self.config.default_model,
                feedback=feedback,
            )
        )
    return result
```

**Agent 消息保存** (`packages/dbgpt-core/src/dbgpt/agent/core/base_agent.py` 第 756-809 行)
```python
async def _a_append_message(
    self, message: AgentMessage, role, sender: Agent
) -> bool:
    """追加消息到内存和存储."""
    gpts_message: GptsMessage = GptsMessage(
        conv_id=self.not_null_agent_context.conv_id,
        sender=sender.role,
        receiver=self.role,
        content=message.content if message.content else "",
        rounds=message.rounds,
        is_success=message.success,
        current_goal=message.current_goal,
        action_report=(
            json.dumps(message.action_report.to_dict(), ensure_ascii=False)
            if message.action_report else None
        ),
        model_name=message.model_name,
    )
    
    # 保存到 GptsMemory
    await self.memory.gpts_memory.append_message(
        self.not_null_agent_context.conv_id, gpts_message
    )
```

**StorageConversation 存储** (`packages/dbgpt-core/src/dbgpt/core/interface/message.py` 第 1273-1288 行)
```python
def save_to_storage(self) -> None:
    """Save the conversation to the storage."""
    # 获取消息项
    message_list = self._get_message_items()
    self._message_ids = [
        message.identifier.str_identifier for message in message_list
    ]
    
    # 只保存新增的消息
    messages_to_save = message_list[self._has_stored_message_index + 1 :]
    self._has_stored_message_index = len(message_list) - 1
    
    if self.save_message_independent:
        # 独立存储消息
        self.message_storage.save_list(messages_to_save)
    
    # 保存对话
    if self.summary is not None and len(self.summary) > 4000:
        self.summary = self.summary[0:4000]
    self.conv_storage.save_or_update(self)
```

### 6.3 数据库关键代码

**存储适配器** (`packages/dbgpt-core/src/dbgpt/storage/chat_history/storage_adapter.py` 第 22-48 行)
```python
class DBStorageConversationItemAdapter(
    StorageItemAdapter[StorageConversation, ChatHistoryEntity]
):
    """Adapter for chat history storage."""
    
    def to_storage_format(self, item: StorageConversation) -> ChatHistoryEntity:
        """Convert to storage format."""
        message_ids = ",".join(item.message_ids)
        messages = None
        if not item.save_message_independent and item.messages:
            message_dict_list = [_conversation_to_dict(item)]
            messages = json.dumps(message_dict_list, ensure_ascii=False)
        
        # 自动生成摘要
        summary = item.summary
        latest_user_message = item.get_latest_user_message()
        if not summary and latest_user_message is not None:
            summary = latest_user_message.last_text[:250]
        
        return ChatHistoryEntity(
            conv_uid=item.conv_uid,
            chat_mode=item.chat_mode,
            summary=summary,
            user_name=item.user_name,
            messages=messages,  # 旧格式兼容
            message_ids=message_ids,
            sys_code=item.sys_code,
            app_code=item.app_code,
        )
```

---

## 7. 对我们项目的启示

### 7.1 架构设计建议

#### 7.1.1 分层存储策略

DB-GPT 采用了**三层存储架构**：

| 层级 | 用途 | 实现方式 |
|------|------|----------|
| **内存缓存** | Agent 运行时快速访问 | `GptsMemory.messages_cache` |
| **持久化存储** | 对话历史保存 | `chat_history_message` 表 |
| **前端状态** | UI 渲染 | React `history` 状态 |

**建议**: 我们的项目应采用类似的分层架构：
- 内存层: 使用 Redis 或内存缓存加速 Agent 访问
- 存储层: PostgreSQL 存储对话和消息
- 前端层: React Context 管理当前对话状态

#### 7.1.2 消息模型设计

DB-GPT 的消息模型设计值得借鉴：

```typescript
// 建议的消息模型
interface Message {
  id: string;              // 消息唯一ID
  conversation_id: string; // 所属对话ID
  role: 'human' | 'ai' | 'system' | 'view';
  content: string | MediaContent[];
  round_index: number;     // 对话轮次
  index: number;           // 消息序号
  metadata?: {
    model_name?: string;
    tokens?: number;
    latency?: number;
    action_report?: any;   // Agent 动作报告
  };
  created_at: Date;
}
```

#### 7.1.3 独立消息存储

DB-GPT 支持两种存储模式：
- **独立存储** (`save_message_independent=True`): 每条消息单独一行，便于查询和分页
- **合并存储** (`save_message_independent=False`): 消息作为 JSON 数组存储

**建议**: 采用独立存储模式，优势：
- 支持消息级别分页
- 便于单独更新某条消息
- 更好的索引和查询性能

### 7.2 前后端数据流设计

#### 7.2.1 区分展示消息和模型消息

DB-GPT 的 `ViewMessage` 设计非常重要：
- `pass_to_model=False`: 仅用于前端展示
- 可包含渲染后的 Markdown、图表等
- 不占用 LLM 上下文窗口

**建议在我们的项目中实现**: 
```typescript
// 展示消息 (仅前端)
interface ViewMessage extends Message {
  role: 'view';
  render_type: 'markdown' | 'chart' | 'table' | 'code';
  pass_to_model: false;
}

// 模型消息 (传递给 LLM)
interface ModelMessage extends Message {
  role: 'human' | 'ai' | 'system';
  pass_to_model: true;
}
```

#### 7.2.2 SSE 流式响应

DB-GPT 使用 SSE 实现流式响应，优势：
- 实时展示 Agent 思考过程
- 支持大模型逐字输出
- 可中途取消请求

**建议实现**:
```typescript
// 前端使用 EventSource
const eventSource = new EventSource('/api/chat/stream');
eventSource.onmessage = (event) => {
  if (event.data === '[DONE]') {
    eventSource.close();
  } else {
    appendMessage(event.data);
  }
};
```

### 7.3 Agent 历史管理建议

#### 7.3.1 Agent 内存隔离

DB-GPT 通过 `conv_id` + `agent_role` + `agent_name` 实现 Agent 级别隔离：

```python
memory_session = f"{real_conv_id}_{self.role}_{self.name}"
```

**建议**: 在我们的多 Agent 系统中：
- 每个 Agent 有独立的内存命名空间
- 支持 Agent 间消息共享 (通过公共 conv_id)
- 支持 Agent 私有记忆

#### 7.3.2 历史消息裁剪策略

DB-GPT 提供了灵活的裁剪接口：

```python
def get_messages_with_round(self, round_count: int) -> List[BaseMessage]:
    """获取最近 N 轮的消息"""
    
def get_model_messages(self) -> List[ModelMessage]:
    """获取传给模型的消息 (过滤 view 类型)"""
```

**建议实现策略**:
1. **轮次裁剪**: 只保留最近 N 轮对话
2. **Token 裁剪**: 根据 Token 数量裁剪
3. **重要性裁剪**: 基于消息重要性评分

```python
# 建议的裁剪接口
class ConversationHistory:
    def get_recent_messages(self, max_rounds: int = 10) -> List[Message]:
        """获取最近 N 轮消息"""
        
    def get_messages_by_token_limit(self, max_tokens: int = 4000) -> List[Message]:
        """根据 Token 限制获取消息"""
        
    def summarize_old_messages(self, threshold_rounds: int = 5) -> str:
        """对旧消息进行摘要"""
```

### 7.4 数据表设计建议

基于 DB-GPT 的设计，建议我们的数据表结构：

```sql
-- 对话表
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    conv_uid UUID UNIQUE NOT NULL,
    title VARCHAR(255),
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 消息表 (独立存储)
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conv_uid UUID REFERENCES conversations(conv_uid),
    message_index INTEGER NOT NULL,
    round_index INTEGER NOT NULL,
    role VARCHAR(50) NOT NULL,  -- human, ai, system, view
    content TEXT,
    metadata JSONB,  -- 模型名、Token数、动作报告等
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(conv_uid, message_index)
);

-- Agent 消息表 (用于多 Agent 场景)
CREATE TABLE agent_messages (
    id SERIAL PRIMARY KEY,
    conv_uid UUID REFERENCES conversations(conv_uid),
    sender VARCHAR(255),    -- Agent 角色名
    receiver VARCHAR(255),  -- 接收者角色名
    content TEXT,
    current_goal VARCHAR(255),
    action_report JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX idx_messages_conv_uid ON messages(conv_uid);
CREATE INDEX idx_messages_round ON messages(conv_uid, round_index);
CREATE INDEX idx_agent_messages_conv ON agent_messages(conv_uid);
```

### 7.5 关键实现要点

| 要点 | DB-GPT 实现 | 我们的项目建议 |
|------|-------------|----------------|
| **对话 ID** | UUID v1 (`uuid.uuid1()`) | 使用 UUID v4 或 Snowflake ID |
| **消息序号** | 全局自增 `index` | 每个对话内自增，避免全局锁 |
| **轮次管理** | `round_index` 显式标记 | 按消息对 (human+ai) 自动计算 |
| **并发控制** | `defaultdict` 按 conv_id 隔离 | 使用 Redis 分布式锁 |
| **存储模式** | 支持独立/合并两种模式 | 采用独立存储，简化逻辑 |
| **摘要生成** | 截取用户输入前 250 字符 | 使用 LLM 自动生成摘要 |
| **消息类型** | `human/ai/system/view` | 扩展 `tool/observation` 等 |

---

## 8. 总结

### 8.1 DB-GPT 对话历史管理的核心特点

1. **分层存储**: 内存缓存 → 持久化存储 → 前端状态
2. **消息分类**: 区分模型消息 (pass_to_model) 和展示消息 (view)
3. **独立存储**: 支持消息级别的独立存储，便于查询和分页
4. **Agent 隔离**: 通过 `conv_id` 和 `memory_session` 实现多 Agent 隔离
5. **灵活裁剪**: 支持按轮次、Token 数等多种方式裁剪历史

### 8.2 对我们项目的核心借鉴

1. **前后端分离的消息模型**: 前端展示和 Agent 运行使用不同的消息格式
2. **独立消息存储**: 每条消息单独存储，支持更灵活的查询
3. **SSE 流式响应**: 实时展示 Agent 执行过程和 LLM 输出
4. **内存缓存 + 持久化**: 两层存储架构平衡性能和可靠性
5. **Agent 内存隔离**: 多 Agent 场景下的内存隔离策略

---

**文档结束**
