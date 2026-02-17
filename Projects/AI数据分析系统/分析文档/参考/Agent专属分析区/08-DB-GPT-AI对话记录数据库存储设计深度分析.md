# DB-GPT AI 对话记录数据库存储设计深度分析

> **分析目标**: 深入理解 DB-GPT 如何设计数据库来存储 AI 对话记录  
> **分析日期**: 2026-02-06  
> **源码位置**: `packages/dbgpt-core/src/dbgpt/storage/chat_history/`  
> **数据库**: SQLAlchemy + 支持 SQLite/MySQL/PostgreSQL

---

## 一、总体架构设计

### 1.1 三层存储架构

DB-GPT 采用**分层存储架构**，将对话数据分散在三个核心表中：

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DB-GPT 对话存储三层架构                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Layer 1: 对话元数据层 (chat_history)                                        │
│   ├── 对话唯一标识 (conv_uid)                                                 │
│   ├── 对话摘要 (summary)                                                      │
│   ├── 用户标识 (user_name)                                                    │
│   └── 应用标识 (app_code)                                                     │
│                                                                             │
│   Layer 2: 用户消息层 (chat_history_message)                                  │
│   ├── 消息索引 (index)                                                        │
│   ├── 消息轮次 (round_index)                                                  │
│   └── 消息详情 JSON (message_detail)                                          │
│                                                                             │
│   Layer 3: Agent 执行层 (gpts_messages)                                       │
│   ├── 发送者/接收者 (sender/receiver)                                         │
│   ├── 当前目标 (current_goal)                                                 │
│   └── 动作报告 JSON (action_report)                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 设计哲学

| 设计决策 | 说明 | 优势 |
|---------|------|------|
| **分表存储** | 用户消息与 Agent 消息分离 | 便于权限控制、查询优化 |
| **JSON 字段** | 动态字段用 JSON 存储 | 灵活扩展、无需迁移 |
| **独立索引** | message 表独立存储 | 支持分页、快速查询 |
| **双模式支持** | 支持合并/独立存储 | 兼容旧版本、灵活部署 |

---

## 二、核心表结构详解

### 2.1 chat_history - 对话主表

**文件位置**: `packages/dbgpt-core/src/dbgpt/storage/chat_history/chat_history_db.py:25-61`

```python
class ChatHistoryEntity(Model):
    __tablename__ = "chat_history"
    
    # 主键与唯一标识
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_uid = Column(String(255), nullable=False, comment="对话唯一ID")
    
    # 对话元数据
    chat_mode = Column(String(255), nullable=False, comment="对话场景模式")
    summary = Column(Text(length=2**31 - 1), nullable=False, comment="对话摘要")
    user_name = Column(String(255), nullable=True, comment="用户")
    
    # 消息存储（旧模式，现主要用 chat_history_message 表）
    messages = Column(Text(length=2**31 - 1), nullable=True, comment="对话详情")
    message_ids = Column(Text(length=2**31 - 1), nullable=True, comment="消息ID列表")
    
    # 系统标识
    sys_code = Column(String(128), index=True, nullable=True, comment="系统代码")
    app_code = Column(String(255), nullable=True, comment="应用代码")
    
    # 时间戳
    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now)
```

**字段设计解析**:

| 字段 | 类型 | 说明 | 设计意图 |
|------|------|------|---------|
| `conv_uid` | String(255) | UUID v1 生成 | 全局唯一、时间有序 |
| `summary` | Long Text | 对话前 250 字符 | 列表展示、快速预览 |
| `chat_mode` | String | chat/dialogue/awel | 区分对话类型 |
| `app_code` | String | 应用唯一码 | 多应用隔离 |

**索引设计**:

```python
Index("idx_q_user", "user_name")      # 按用户查询
Index("idx_q_mode", "chat_mode")      # 按模式筛选
Index("idx_q_conv", "summary")        # 摘要搜索
Index("idx_chat_his_app_code", "app_code")  # 应用统计
```

### 2.2 chat_history_message - 用户消息表

**文件位置**: `packages/dbgpt-core/src/dbgpt/storage/chat_history/chat_history_db.py:63-86`

```python
class ChatHistoryMessageEntity(Model):
    __tablename__ = "chat_history_message"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_uid = Column(String(255), nullable=False, comment="对话唯一ID")
    
    # 消息序号（关键设计）
    index = Column(Integer, nullable=False, comment="消息索引")
    round_index = Column(Integer, nullable=False, comment="消息轮次索引")
    
    # JSON 存储消息详情
    message_detail = Column(
        Text(length=2**31 - 1), 
        nullable=True, 
        comment="消息详情, json format"
    )
    
    gmt_created = Column(DateTime, default=datetime.now)
    gmt_modified = Column(DateTime, default=datetime.now)
    
    # 联合唯一索引
    __table_args__ = (
        UniqueConstraint("conv_uid", "index", name="uk_conversation_message"),
    )
```

**关键设计：index + round_index**

```
对话轮次示例:
Round 0: index=0, round_index=0 (HumanMessage: "你好")
Round 0: index=1, round_index=0 (AIMessage: "你好！有什么可以帮助你？")
Round 1: index=2, round_index=1 (HumanMessage: "分析数据")
Round 1: index=3, round_index=1 (AIMessage: "好的，我来分析...")
```

**存储模式对比**:

| 模式 | 存储位置 | 适用场景 | 优缺点 |
|------|---------|---------|--------|
| **独立存储** (推荐) | chat_history_message 表 | 新部署 | 查询快、分页易 |
| **合并存储** | chat_history.messages 字段 | 兼容旧版 | 简单但查询慢 |

切换方式:
```python
save_message_independent: bool = True  # 控制存储模式
```

### 2.3 gpts_messages - Agent 执行消息表

**文件位置**: `packages/dbgpt-serve/src/dbgpt_serve/agent/db/gpts_messages_db.py:22-84`

```python
class GptsMessagesEntity(Model):
    __tablename__ = "gpts_messages"
    
    id = Column(Integer, primary_key=True)
    conv_id = Column(String(255), nullable=False, comment="对话唯一ID")
    
    # 发送者/接收者（多 Agent 协作关键）
    sender = Column(String(255), nullable=False, comment="发送者")
    receiver = Column(String(255), nullable=False, comment="接收者")
    
    # 对话轮次
    rounds = Column(Integer, nullable=False, comment="对话轮次")
    
    # 消息内容
    content = Column(Text(length=2**31 - 1), nullable=True, comment="内容")
    role = Column(String(255), nullable=True, comment="角色")
    
    # Agent 特有字段
    current_goal = Column(Text, nullable=True, comment="当前目标")
    action_report = Column(Text(length=2**31 - 1), nullable=True, comment="动作报告")
    resource_info = Column(Text, nullable=True, comment="资源信息")
    context = Column(Text, nullable=True, comment="上下文")
    review_info = Column(Text, nullable=True, comment="审核信息")
    
    # 模型与执行状态
    model_name = Column(String(255), nullable=True, comment="生成模型")
    is_success = Column(Boolean, default=True, comment="是否成功")
    
    # 应用标识
    app_code = Column(String(255), nullable=False, comment="应用代码")
    app_name = Column(String(255), nullable=False, comment="应用名称")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**核心字段解析**:

#### 2.3.1 action_report - 代码执行记录

**不是标准的 Function Call 格式**，而是 DB-GPT 自定义的 Action 报告：

```json
{
  "action": "code_execution",
  "name": "python_code_interpreter",
  "input": {
    "code": "import pandas as pd\ndf = pd.read_csv('data.csv')\ndf.head()"
  },
  "output": {
    "stdout": "   col1  col2\n0     1     4\n1     2     5",
    "stderr": "",
    "exit_code": 0
  },
  "resource": {
    "cpu_time": 0.5,
    "memory_mb": 128
  },
  "is_success": true
}
```

#### 2.3.2 sender/receiver - 多 Agent 协作

```
对话场景: User -> Planner -> CodeInterpreter -> User

消息流转:
1. sender="User", receiver="Planner", content="分析数据"
2. sender="Planner", receiver="CodeInterpreter", content="请生成代码"
3. sender="CodeInterpreter", receiver="Planner", action_report="{执行结果}"
4. sender="Planner", receiver="User", content="分析完成..."
```

#### 2.3.3 current_goal - 意图分组

支持多话题并行追踪：

```
话题A: current_goal="数据分析"
  - rounds=0: "加载数据"
  - rounds=1: "分析趋势"

话题B: current_goal="报表生成"  
  - rounds=2: "生成图表"
  - rounds=3: "导出PDF"
```

---

## 三、消息类型与存储策略

### 3.1 消息类型体系

**文件位置**: `packages/dbgpt-core/src/dbgpt/core/interface/message.py`

```python
BaseMessage (ABC)
├── HumanMessage    # 用户消息
├── AIMessage       # AI 回复
├── SystemMessage   # 系统提示
└── ViewMessage     # 仅前端展示，不传给模型

@property
def pass_to_model(self) -> bool:
    """是否传递给 LLM"""
    return True  # ViewMessage 返回 False
```

### 3.2 存储策略矩阵

| 消息类型 | 存储表 | pass_to_model | 用途 |
|---------|--------|---------------|------|
| HumanMessage | chat_history_message |  | 用户输入 |
| AIMessage | chat_history_message |  | AI 回复 |
| SystemMessage | chat_history_message |  | 系统提示 |
| ViewMessage | chat_history_message |  | 前端渲染 |
| AgentMessage | gpts_messages |  | Agent 间通信 |
| ActionReport | gpts_messages.action_report |  | 执行记录 |

### 3.3 消息序列化格式

```python
# message_detail JSON 结构
{
  "type": "human",           # 消息类型
  "data": {
    "content": "分析数据",
    "additional_kwargs": {}
  },
  "index": 0,
  "round_index": 0
}
```

---

## 四、关键操作与查询模式

### 4.1 消息追加流程

**文件位置**: `packages/dbgpt-serve/src/dbgpt_serve/agent/db/gpts_messages_db.py:86-111`

```python
def append(self, entity: dict):
    """追加消息"""
    message = GptsMessagesEntity(
        conv_id=entity.get("conv_id"),
        sender=entity.get("sender"),
        receiver=entity.get("receiver"),
        content=entity.get("content"),
        is_success=entity.get("is_success", True),
        role=entity.get("role"),
        rounds=entity.get("rounds"),
        action_report=entity.get("action_report"),  # JSON 序列化
        ...
    )
    session.add(message)
    session.commit()
```

### 4.2 常见查询模式

#### 4.2.1 获取对话历史

```python
# 获取完整对话历史
def get_by_conv_id(self, conv_id: str) -> List[GptsMessagesEntity]:
    return session.query(GptsMessagesEntity) \
        .filter(GptsMessagesEntity.conv_id == conv_id) \
        .order_by(GptsMessagesEntity.rounds) \
        .all()
```

#### 4.2.2 获取 Agent 间通信

```python
# 获取两个 Agent 之间的消息
def get_between_agents(
    self, conv_id: str, agent1: str, agent2: str, current_goal: Optional[str] = None
):
    return session.query(GptsMessagesEntity) \
        .filter(GptsMessagesEntity.conv_id == conv_id) \
        .filter(
            or_(
                and_(sender=agent1, receiver=agent2),
                and_(sender=agent2, receiver=agent1),
            )
        ) \
        .filter(GptsMessagesEntity.current_goal == current_goal) \
        .order_by(GptsMessagesEntity.rounds) \
        .all()
```

#### 4.2.3 获取最近对话

```python
# 获取最近 20 条对话
def list_last_20(self, user_name: Optional[str] = None):
    return session.query(ChatHistoryEntity) \
        .filter(ChatHistoryEntity.user_name == user_name) \
        .order_by(ChatHistoryEntity.id.desc()) \
        .limit(20) \
        .all()
```

---

## 五、索引设计与性能优化

### 5.1 索引策略

| 表 | 索引 | 用途 |
|----|------|------|
| chat_history | `idx_q_user` | 用户对话列表查询 |
| chat_history | `idx_q_mode` | 按模式筛选 |
| chat_history | `idx_chat_his_app_code` | 应用热度统计 |
| chat_history_message | `uk_conversation_message` | 联合唯一约束 |
| gpts_messages | `idx_q_messages` | (conv_id, rounds, sender) |

### 5.2 性能考虑

**消息量估算**:
- 单对话平均消息数: 20-50 条
- 日活用户对话: 1000 次
- 年消息量: 1000 × 365 × 35 ≈ 1277 万条

**优化策略**:
1. **分页查询**: 使用 `round_index` 限制历史消息数量
2. **归档策略**: 超过 90 天的对话自动归档
3. **分表策略**: 按 user_name 哈希分表（未来扩展）

---

## 六、与 Function Call 的对比

### 6.1 设计差异

| 特性 | OpenAI Function Call | DB-GPT ActionReport |
|------|---------------------|---------------------|
| **触发方式** | LLM 输出 function_call | Agent 代码显式调用 |
| **存储位置** | message.tool_calls | message.action_report |
| **格式** | OpenAI 标准格式 | 自定义 JSON |
| **执行控制** | LLM 决定 | Agent 代码决定 |
| **可追溯性** | 依赖 LLM 输出 | 完整记录输入输出 |

### 6.2 DB-GPT 的优势

1. **更详细的执行记录**: 包含 stdout/stderr/exit_code
2. **多 Agent 协作**: sender/receiver 追踪消息流转
3. **意图追踪**: current_goal 支持多话题并行
4. **资源监控**: CPU/内存使用记录

---

## 七、对我们项目的启示

### 7.1 推荐表结构

```sql
-- 对话主表
CREATE TABLE conversations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    conv_uid VARCHAR(64) UNIQUE NOT NULL,
    user_id VARCHAR(64) NOT NULL,
    title VARCHAR(255),
    model_name VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
);

-- 消息表
CREATE TABLE messages (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    conv_uid VARCHAR(64) NOT NULL,
    seq_num INT NOT NULL,           -- 消息序号
    round_num INT NOT NULL,         -- 对话轮次
    role ENUM('human', 'ai', 'system', 'tool') NOT NULL,
    content TEXT,
    tool_calls JSON,                -- Function Call 格式
    tool_outputs JSON,              -- 执行结果
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_conv_seq (conv_uid, seq_num),
    INDEX idx_conv_round (conv_uid, round_num)
);

-- Agent 执行记录表（可选）
CREATE TABLE agent_executions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    message_id BIGINT NOT NULL,
    agent_name VARCHAR(64),
    action_type VARCHAR(32),
    input_params JSON,
    output_result JSON,
    execution_time_ms INT,
    is_success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (message_id) REFERENCES messages(id)
);
```

### 7.2 关键设计要点

| 要点 | DB-GPT 实践 | 我们的建议 |
|------|------------|-----------|
| **消息序号** | `index` + `round_index` | 使用 `seq_num` + `round_num` |
| **代码执行** | `action_report` JSON | `tool_calls` + `tool_outputs` |
| **多 Agent** | `sender`/`receiver` | 单独的 `agent_executions` 表 |
| **分页查询** | 按 `index` 分页 | 按 `seq_num` 分页 |
| **归档策略** | 无自动归档 | 90 天自动归档 |

---

## 八、总结

### 8.1 核心设计亮点

1. **三层存储架构**: 清晰分离元数据、用户消息、Agent 消息
2. **JSON 灵活扩展**: action_report 存储动态执行结果
3. **多 Agent 支持**: sender/receiver 支持复杂协作
4. **双模式兼容**: 独立/合并存储兼容不同场景

### 8.2 使用场景匹配

| 场景 | DB-GPT 设计 | 适用性 |
|------|------------|--------|
| 单用户对话 | chat_history_message | ⭐⭐⭐⭐⭐ |
| 多 Agent 协作 | gpts_messages | ⭐⭐⭐⭐⭐ |
| 代码执行追踪 | action_report | ⭐⭐⭐⭐ |
| 复杂工作流 | current_goal 分组 | ⭐⭐⭐⭐ |

### 8.3 可借鉴实践

1. **消息序号体系**: index + round_index 设计
2. **JSON 字段存储**: 灵活记录代码执行结果
3. **多表分离**: 用户消息与 Agent 消息分离存储
4. **联合索引**: (conv_uid, index) 保证查询性能
