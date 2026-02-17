# DB-GPT Agent/LLM 架构分析

## 1. Agent架构总览

### 1.1 整体架构设计理念

DB-GPT 的 Agent 架构采用**分层设计**理念，核心思想是：

1. **角色驱动（Role-Based）**：每个 Agent 都有明确的角色定义（Role），包含名称、目标、约束条件等
2. **动作封装（Action-Oriented）**：Agent 的能力通过 Action 封装，实现业务逻辑与 Agent 框架解耦
3. **资源抽象（Resource Abstraction）**：数据库、知识库、工具等都抽象为 Resource，统一接口管理
4. **记忆分层（Hierarchical Memory）**：借鉴人类记忆机制，分为感官记忆、短期记忆和长期记忆

### 1.2 核心架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                        Agent System                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Agent     │  │   Agent     │  │       ManagerAgent      │  │
│  │  (Role)     │  │  (Role)     │  │       (Team管理)         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │               │
│         └────────────────┴──────────────────────┘               │
│                          │                                      │
│                   ┌──────▼──────┐                               │
│                   │ Conversable │                               │
│                   │Agent(基类)   │                               │
│                   └──────┬──────┘                               │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Profile    │  │   Action    │  │   Memory    │              │
│  │  (角色配置)  │  │  (动作执行)  │  │  (记忆管理)  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                      Resource Layer                      │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │   │
│  │  │   DB    │ │Knowledge│ │  Tool   │ │  File   │ ...   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 核心模块位置

```
dbgpt-core/src/dbgpt/agent/
├── __init__.py                 # 模块入口
├── core/                       # 核心模块
│   ├── agent.py               # Agent 抽象接口
│   ├── base_agent.py          # ConversableAgent 基类
│   ├── base_team.py           # Team/ManagerAgent 多Agent管理
│   ├── user_proxy_agent.py    # 用户代理Agent
│   ├── role.py                # Role 角色定义
│   ├── schema.py              # 状态枚举定义
│   ├── agent_manage.py        # Agent 注册管理
│   ├── action/                # 动作模块
│   │   ├── base.py           # Action 基类
│   │   └── blank_action.py   # 空动作
│   ├── memory/                # 记忆模块
│   │   ├── base.py           # Memory 抽象
│   │   ├── agent_memory.py   # AgentMemory 实现
│   │   ├── gpts/             # GPTs 记忆存储
│   │   └── ...               # 长短记忆实现
│   ├── plan/                  # 计划模块
│   │   ├── planner_agent.py  # 规划Agent
│   │   ├── team_auto_plan.py # 自动计划管理
│   │   └── plan_action.py    # 计划动作
│   └── profile/               # 角色配置
│       └── base.py           # Profile 配置
├── expand/                     # 扩展Agent实现
│   ├── react_agent.py        # ReAct Agent
│   ├── tool_assistant_agent.py # 工具助手
│   ├── data_scientist_agent.py # 数据分析师
│   ├── simple_assistant_agent.py # 简单助手
│   └── actions/              # 扩展动作
└── resource/                   # 资源管理
    ├── base.py               # Resource 基类
    ├── tool/                 # 工具资源
    ├── database.py           # 数据库资源
    └── knowledge.py          # 知识库资源
```

---

## 2. 核心模块分析

### 2.1 Agent 抽象层 (agent.py)

**Agent** 是顶层抽象接口，定义了 Agent 的基本行为契约：

| 方法 | 职责 |
|------|------|
| `send()` | 向其他 Agent 发送消息 |
| `receive()` | 接收其他 Agent 的消息 |
| `generate_reply()` | 生成回复（核心决策逻辑）|
| `thinking()` | 基于 LLM 进行推理思考 |
| `review()` | 审查内容合法性 |
| `act()` | 执行动作 |
| `verify()` | 验证执行结果 |

**核心数据结构**：

```python
@dataclass
class AgentMessage:
    content: Optional[str]           # 消息内容
    name: Optional[str]              # Agent名称
    rounds: int = 0                  # 对话轮次
    context: Optional[Dict] = None   # 上下文信息
    action_report: Optional[ActionOutput] = None  # 动作报告
    review_info: Optional[AgentReviewInfo] = None # 审查信息
    current_goal: Optional[str] = None  # 当前目标
    model_name: Optional[str] = None    # 使用的模型
    role: Optional[str] = None          # 角色
    success: bool = True                # 是否成功

@dataclass
class AgentContext:
    conv_id: str                     # 会话ID
    gpts_app_code: Optional[str]     # GPTs应用编码
    max_chat_round: int = 100        # 最大对话轮数
    max_retry_round: int = 10        # 最大重试次数
    max_new_tokens: int = 1024       # 最大生成token数
    temperature: float = 0.5         # 温度参数
    enable_vis_message: bool = True  # 是否启用VIS消息模式
```

### 2.2 可对话 Agent 基类 (base_agent.py)

**ConversableAgent** 是大多数 Agent 的基类，实现了完整的对话循环：

**核心执行流程（generate_reply）**：

```
┌─────────────────┐
│  1. 初始化回复消息 │
└────────┬────────┘
         ▼
┌─────────────────┐
│  2. 加载思考消息  │◄─────────────────────┐
└────────┬────────┘                      │
         ▼                               │
┌─────────────────┐     失败/需要重试     │
│  3. LLM 推理思考  │──────────────────────┘
└────────┬────────┘
         ▼
┌─────────────────┐
│  4. 审查内容     │
└────────┬────────┘
         ▼
┌─────────────────┐
│  5. 执行动作     │
└────────┬────────┘
         ▼
┌─────────────────┐
│  6. 验证结果     │
└────────┬────────┘
         ▼
┌─────────────────┐
│  7. 写入记忆     │
└────────┬────────┘
         ▼
┌─────────────────┐
│  8. 返回回复消息  │
└─────────────────┘
```

**关键设计**：
- **重试机制**：`max_retry_count` 控制最大重试次数，失败时自动优化提示
- **资源预加载**：`preload_resource()` 在初始化时预加载所需资源
- **LLM 选择策略**：支持优先级策略和默认策略，支持多模型切换

### 2.3 角色系统 (role.py)

**Role** 类管理 Agent 的角色配置和提示词生成：

```python
class Role(ABC, BaseModel):
    profile: ProfileConfig          # 角色配置
    memory: AgentMemory            # 记忆
    language: str = "en"           # 语言
    is_human: bool = False         # 是否人类
    is_team: bool = False          # 是否团队
```

**ProfileConfig** 配置项：
- `name`: Agent 名称
- `role`: 角色标识
- `goal`: 目标描述
- `retry_goal`: 重试时的目标描述
- `constraints`: 约束条件列表
- `retry_constraints`: 重试时的约束
- `expand_prompt`: 扩展提示
- `examples`: 示例
- `system_prompt_template`: 系统提示模板
- `user_prompt_template`: 用户提示模板
- `write_memory_template`: 记忆写入模板

### 2.4 Action 动作系统 (action/base.py)

**Action** 是 Agent 执行的具体行为，采用泛型设计：

```python
class Action(ABC, Generic[T]):
    @property
    def resource_need(self) -> Optional[ResourceType]:
        """所需资源类型"""
        
    @property
    def ai_out_schema(self) -> Optional[str]:
        """AI输出格式Schema"""
        
    @abstractmethod
    async def run(self, ai_message: str, ...) -> ActionOutput:
        """执行动作"""
```

**ActionOutput** 输出结构：
```python
class ActionOutput(BaseModel):
    content: str                    # 输出内容
    is_exe_success: bool = True     # 执行是否成功
    view: Optional[str] = None      # 可视化展示
    resource_type: Optional[str] = None  # 资源类型
    resource_value: Optional[Any] = None # 资源值
    action: Optional[str] = None    # 动作名称
    action_input: Optional[str] = None   # 动作输入
    thoughts: Optional[str] = None  # 思考过程
    observations: Optional[str] = None   # 观察结果
    have_retry: Optional[bool] = True    # 是否可重试
    ask_user: Optional[bool] = False     # 是否需要询问用户
    next_speakers: Optional[List[str]] = None  # 下一个发言者
    terminate: Optional[bool] = None     # 是否终止
    memory_fragments: Optional[Dict] = None  # 记忆片段
```

---

## 3. 多Agent协作机制

### 3.1 团队管理架构

DB-GPT 支持多 Agent 协作，核心组件包括：

```
┌──────────────────────────────────────────────────────────┐
│                      Team 团队                            │
├──────────────────────────────────────────────────────────┤
│  agents: List[Agent]      # Agent列表                     │
│  messages: List[Dict]     # 团队消息记录                   │
│  max_round: int          # 最大对话轮数                    │
├──────────────────────────────────────────────────────────┤
│  hire(agents)            # 招募Agent                      │
│  select_speaker()        # 选择下一个发言者                │
│  reset()                 # 重置对话                       │
└──────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────┐
│                 ManagerAgent 管理Agent                    │
├──────────────────────────────────────────────────────────┤
│  继承 ConversableAgent + Team                            │
│  协调多个 Agent 完成任务                                  │
└──────────────────────────────────────────────────────────┘
```

### 3.2 自动计划模式 (AutoPlanChatManager)

**AutoPlanChatManager** 是多 Agent 协作的核心实现，采用**计划驱动**的协作模式：

**工作流程**：

```
用户输入
   │
   ▼
┌──────────────────┐     无计划    ┌──────────────────┐
│ 检查是否存在任务计划 │─────────────▶│  PlannerAgent    │
└────────┬─────────┘              │  生成任务计划      │
         │有计划                    └────────┬─────────┘
         ▼                                   │
┌──────────────────┐                        │
│ 获取待执行计划步骤  │◄───────────────────────┘
└────────┬─────────┘
         ▼
┌──────────────────┐
│ select_speaker() │  根据计划步骤选择合适的Agent
│ 选择执行Agent    │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ process_rely_msg()│  处理依赖消息（前后步骤依赖）
│ 处理依赖关系      │
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Agent执行并返回   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 更新计划状态      │
│ (完成/失败)      │
└────────┬─────────┘
         │
         └──────────▶ 循环执行直到所有计划完成
```

**关键特性**：
- **计划生成**：PlannerAgent 基于 LLM 自动生成任务执行计划
- **依赖处理**：支持步骤间的依赖关系（`rely` 字段）
- **动态选人**：根据任务内容动态选择最合适的 Agent
- **状态追踪**：每个计划步骤有独立的状态管理（TODO/RUNNING/COMPLETE/FAILED）

### 3.3 内置 Agent 类型

| Agent 类型 | 职责 | 所在文件 |
|-----------|------|---------|
| **SimpleAssistantAgent** | 通用对话助手 | `expand/simple_assistant_agent.py` |
| **ReActAgent** | ReAct 工具调用 | `expand/react_agent.py` |
| **ToolAssistantAgent** | 工具执行专家 | `expand/tool_assistant_agent.py` |
| **DataScientistAgent** | 数据分析/SQL生成 | `expand/data_scientist_agent.py` |
| **CodeAssistantAgent** | 代码生成 | `expand/code_assistant_agent.py` |
| **DashboardAssistantAgent** | 报表生成 | `expand/dashboard_assistant_agent.py` |
| **SummaryAssistantAgent** | 文本摘要 | `expand/summary_assistant_agent.py` |
| **ExcelTableAgent** | Excel处理 | `expand/excel_table_agent.py` |
| **PlannerAgent** | 任务规划 | `core/plan/planner_agent.py` |
| **AutoPlanChatManager** | 计划管理 | `core/plan/team_auto_plan.py` |
| **UserProxyAgent** | 用户代理 | `core/user_proxy_agent.py` |

---

## 4. 工具调用实现

### 4.1 工具定义

DB-GPT 采用装饰器模式定义工具：

```python
from dbgpt.agent.resource.tool.base import tool

@tool
def calculator(expression: str) -> str:
    """Calculate mathematical expression"""
    return str(eval(expression))

@tool("search", description="Search web content")
async def search_tool(query: str, limit: int = 5) -> List[str]:
    """Search tool with custom name"""
    return await search_api(query, limit)
```

### 4.2 工具基类架构

```
┌─────────────────────────┐
│      BaseTool           │
├─────────────────────────┤
│  name: str              │
│  description: str       │
│  args: Dict[str, ToolParameter] │
├─────────────────────────┤
│  get_prompt()           │
│  execute()              │
│  async_execute()        │
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    ▼               ▼
┌──────────┐   ┌──────────┐
│FunctionTool│  │CustomTool│
└──────────┘   └──────────┘
```

### 4.3 ReAct 工具调用流程

**ReActAgent** 实现了经典的 ReAct（Reasoning + Acting）模式：

```
┌─────────────────────────────────────────────────────────┐
│ Thought: 分析任务和当前环境，推理下一步动作              │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Action: 选择工具名称（从ACTION SPACE中）                 │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Action Input: 构造工具参数（JSON格式）                   │
└─────────────────────────┬───────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────┐
│ Observation: 执行工具，获取结果                          │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │  任务完成？  │
                   └──────┬──────┘
                   是 /    \ 否
                     /      \
                    ▼        ▼
            ┌──────────┐  ┌────────────────┐
            │ 终止(Terminate)│ │ 继续下一轮思考  │
            └──────────┘  └────────────────┘
```

**ReActAgent 配置**：
```python
class ReActAgent(ConversableAgent):
    max_retry_count: int = 15      # 最大思考-行动轮数
    run_mode: AgentRunMode = AgentRunMode.LOOP  # 循环模式
    
    profile: ProfileConfig = ProfileConfig(
        name="ReAct",
        role="ReActToolMaster",
        goal="通过选择正确的ACTION解决问题",
        system_prompt_template=_REACT_SYSTEM_TEMPLATE,
    )
```

### 4.4 工具调用通用流程 (ToolAction)

```python
class ToolAction(Action[ToolInput]):
    async def run(self, ai_message: str, ...) -> ActionOutput:
        # 1. 解析 LLM 输出为结构化参数
        param: ToolInput = self._input_convert(ai_message, ToolInput)
        
        # 2. 查找并执行工具
        return await run_tool(
            param.tool_name,
            param.args,
            self.resource,
            self.render_protocol,
        )
```

### 4.5 资源与工具的绑定

Agent 通过 `bind()` 方法绑定资源：

```python
agent = (
    await DataScientistAgent()
    .bind(agent_context)        # 绑定上下文
    .bind(llm_config)           # 绑定LLM配置
    .bind(memory)               # 绑定记忆
    .bind(resource)             # 绑定资源（数据库/工具等）
    .build()                    # 构建Agent
)
```

---

## 5. Memory机制

### 5.1 记忆分层架构

DB-GPT 的记忆系统设计参考人类记忆机制，分为三层：

```
┌─────────────────────────────────────────────────────────────┐
│                    长期记忆 (Long-Term)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • 持久化存储 (向量数据库/关系数据库)                   │   │
│  │  • 重要性评分筛选后的记忆                              │   │
│  │  • Insights (洞察/抽象知识)                           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ 转移 (当短期记忆溢出时)
┌─────────────────────────────────────────────────────────────┐
│                    短期记忆 (Short-Term)                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • 内存存储 (Python对象)                              │   │
│  │  • buffer_size 限制 (默认5条)                        │   │
│  │  • 支持重要性评分和Insight提取                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │ 转移 (当感官记忆评分达标)
┌─────────────────────────────────────────────────────────────┐
│                    感官记忆 (Sensory)                         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • 原始输入缓存                                       │   │
│  │  • 高重要性权重 (0.9)                                 │   │
│  │  • 快速过滤低重要性信息                                │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 核心记忆类

```python
# 记忆片段
class AgentMemoryFragment(MemoryFragment):
    memory_id: int                 # 唯一ID（Snowflake算法）
    observation: str               # 原始观察内容
    _embeddings: List[float]       # 向量嵌入
    _importance: float             # 重要性分数
    _is_insight: bool              # 是否为洞察
    _last_accessed_time: datetime  # 最后访问时间

# Agent 记忆包装器
class AgentMemory(Memory[AgentMemoryFragment]):
    memory: Memory[AgentMemoryFragment]  # 底层记忆存储
    gpts_memory: GptsMemory             # GPTs 记忆（计划和消息）
```

### 5.3 GPTs 记忆存储

**GptsMemory** 专门用于存储多 Agent 协作的对话历史：

```python
class GptsMemory:
    plans_memory: GptsPlansMemory      # 计划记忆
    message_memory: GptsMessageMemory  # 消息记忆
    
    # 核心方法
    async def append_message(conv_id: str, message: GptsMessage)
    async def get_messages(conv_id: str) -> List[GptsMessage]
    async def get_agent_history_memory(conv_id: str, agent_role: str) -> List[ActionOutput]
```

**GptsMessage** 结构：
```python
class GptsMessage:
    conv_id: str           # 会话ID
    sender: str            # 发送者
    receiver: str          # 接收者
    role: str              # 角色
    rounds: int            # 轮次
    content: str           # 内容
    context: str           # 上下文（JSON）
    action_report: str     # 动作报告（JSON）
    model_name: str        # 模型名称
    current_goal: str      # 当前目标
```

### 5.4 记忆读写流程

```python
# 写入记忆
async def write_memories(self, question, ai_message, action_output, ...):
    # 1. 构造记忆内容
    memory_map = {
        "thought": mem_thoughts,
        "action": action,
        "observation": observation,
    }
    
    # 2. 使用模板渲染
    memory_content = self._render_template(write_memory_template, **memory_map)
    
    # 3. 创建记忆片段
    fragment = AgentMemoryFragment(memory_content)
    
    # 4. 写入底层记忆
    await self.memory.write(fragment)

# 读取记忆
async def read_memories(self, question: str):
    memories = await self.memory.read(question)
    return [m.raw_observation for m in memories]
```

### 5.5 记忆检索算法

记忆检索综合考虑三个维度（可配置权重）：

```
score = α * recency_score + β * relevance_score + γ * importance_score

其中：
- α (recency): 时间衰减因子，越新的记忆分数越高
- β (relevance): 向量相似度，与查询内容越相关分数越高
- γ (importance): 重要性分数，存储时由LLM评分
```

---

## 6. 与 RAGFlow Agent 的对比

### 6.1 架构差异对比

| 维度 | DB-GPT Agent | RAGFlow Agent/Canvas |
|------|-------------|---------------------|
| **核心理念** | 角色驱动 + 计划驱动 | 工作流编排 + 画布可视化 |
| **协作模式** | 多Agent自动协作（AutoPlan） | 预定义工作流节点连接 |
| **Agent定义** | Python类继承，代码定义 | 画布拖拽 + 配置定义 |
| **工具调用** | 装饰器 + ReAct模式 | 组件节点方式 |
| **记忆设计** | 三层记忆（感官/短期/长期） | 会话上下文存储 |
| **扩展性** | 强（代码级扩展） | 中等（配置级扩展） |

### 6.2 优劣分析

#### DB-GPT Agent 优势

1. **更灵活的角色定义**
   - 通过 `ProfileConfig` 可以精细定义 Agent 的角色、目标、约束
   - 支持动态提示词模板（Jinja2）
   - 支持国际化（中英文动态切换）

2. **强大的计划驱动协作**
   - PlannerAgent 自动生成任务计划
   - 支持步骤间依赖关系处理
   - 动态 Agent 选择（select_speaker）

3. **完善的记忆系统**
   - 三层记忆架构（感官/短期/长期）
   - 重要性评分机制
   - Insight 提取能力
   - 记忆持久化存储

4. **代码级扩展能力**
   - 通过继承 `ConversableAgent` 自定义 Agent
   - 通过继承 `Action` 定义新动作
   - 通过装饰器 `@tool` 快速定义工具

5. **内置丰富 Agent 类型**
   - 数据分析师（DataScientist）
   - ReAct 工具专家
   - 报表生成专家
   - 代码助手等

#### DB-GPT Agent 劣势

1. **学习曲线陡峭**
   - 需要理解 Python 类和异步编程
   - 概念较多（Role/Action/Resource/Memory）

2. **可视化能力弱**
   - 主要通过代码定义工作流
   - 缺少拖拽式画布编辑

3. **调试复杂**
   - 多 Agent 协作时追踪困难
   - 需要依赖日志和追踪系统

4. **部署依赖重**
   - 依赖完整的 DB-GPT 框架
   - 需要配置数据库、向量存储等

#### RAGFlow Agent/Canvas 优势

1. **低代码/无代码**
   - 画布拖拽方式编排工作流
   - 配置驱动，无需编程

2. **可视化强**
   - 直观的节点连接图
   - 实时查看执行流程

3. **与RAG深度集成**
   - 原生支持检索增强生成
   - 知识库即插即用

4. **上手简单**
   - 非技术人员也能快速构建
   - 模板化组件

#### RAGFlow Agent/Canvas 劣势

1. **灵活性受限**
   - 受限于预定义节点类型
   - 复杂逻辑难以实现

2. **扩展性有限**
   - 自定义组件需要开发
   - 不如代码级扩展灵活

3. **记忆系统简单**
   - 主要依赖会话上下文
   - 缺少长期记忆机制

4. **多Agent协作弱**
   - 主要是工作流编排
   - 缺少动态协作能力

### 6.3 适用场景建议

| 场景 | 推荐方案 | 原因 |
|------|---------|------|
| 复杂数据分析任务 | **DB-GPT** | DataScientist + PlannerAgent 协作 |
| 多步骤工具调用 | **DB-GPT** | ReAct 模式 + 自动计划 |
| 需要长期记忆的场景 | **DB-GPT** | 三层记忆系统 |
| 快速原型验证 | **RAGFlow** | 低代码，快速搭建 |
| 知识库问答 | **RAGFlow** | RAG 原生深度集成 |
| 固定流程自动化 | **RAGFlow** | 工作流编排直观 |
| 企业级Agent平台 | **DB-GPT** | 扩展性和定制性强 |

### 6.4 技术选型的关键考量

```
选择 DB-GPT Agent 如果你需要：
✓ 复杂的 Agent 间协作逻辑
✓ 自定义 Agent 行为和推理过程
✓ 企业级的扩展性和定制化
✓ 深度集成数据分析能力
✓ 长期记忆和知识积累

选择 RAGFlow Canvas 如果你需要：
✓ 快速搭建简单的 Agent 工作流
✓ 非技术用户参与构建
✓ 以 RAG 为核心的应用场景
✓ 可视化调试和监控
✓ 轻量级部署
```

---

## 7. 总结

### 7.1 DB-GPT Agent 架构核心亮点

1. **分层清晰**：Role/Action/Resource/Memory 各司其职，职责边界明确
2. **可扩展性强**：通过继承和组合方式轻松扩展
3. **计划驱动协作**：Planner + Manager 模式实现复杂任务分解
4. **记忆系统完善**：三层记忆 + 重要性评分 + Insight 提取
5. **工具生态丰富**：装饰器方式快速定义工具，ReAct 模式成熟

### 7.2 关键源码文件索引

| 功能 | 核心文件 |
|------|---------|
| Agent 基类 | `packages/dbgpt-core/src/dbgpt/agent/core/agent.py` |
| 可对话 Agent | `packages/dbgpt-core/src/dbgpt/agent/core/base_agent.py` |
| 团队管理 | `packages/dbgpt-core/src/dbgpt/agent/core/base_team.py` |
| 角色配置 | `packages/dbgpt-core/src/dbgpt/agent/core/profile/base.py` |
| 动作基类 | `packages/dbgpt-core/src/dbgpt/agent/core/action/base.py` |
| 记忆基类 | `packages/dbgpt-core/src/dbgpt/agent/core/memory/base.py` |
| Agent 记忆 | `packages/dbgpt-core/src/dbgpt/agent/core/memory/agent_memory.py` |
| GPTs 记忆 | `packages/dbgpt-core/src/dbgpt/agent/core/memory/gpts/gpts_memory.py` |
| 计划管理 | `packages/dbgpt-core/src/dbgpt/agent/core/plan/team_auto_plan.py` |
| 规划 Agent | `packages/dbgpt-core/src/dbgpt/agent/core/plan/planner_agent.py` |
| ReAct Agent | `packages/dbgpt-core/src/dbgpt/agent/expand/react_agent.py` |
| 工具基类 | `packages/dbgpt-core/src/dbgpt/agent/resource/tool/base.py` |
| 资源基类 | `packages/dbgpt-core/src/dbgpt/agent/resource/base.py` |
| Agent 管理 | `packages/dbgpt-core/src/dbgpt/agent/core/agent_manage.py` |

---

*文档生成时间：2026-02-06*
*分析对象：DB-GPT Agent/LLM 架构*
*版本：基于源码分析*
