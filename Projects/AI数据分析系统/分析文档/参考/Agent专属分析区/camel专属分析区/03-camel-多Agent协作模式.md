# CAMEL 多 Agent 协作模式

分析 CAMEL 框架中多 Agent 协作的实现机制，包括 Society 架构、RolePlaying 模式、角色定义和任务分配策略。

---

## 1. Society 架构

### 1.1 概念与设计

CAMEL 使用 **RolePlaying** 类作为多 Agent 社会的基础实现。与传统的主从架构不同，CAMEL 采用**平等对话**模式：

> 两个 Agent 通过自然语言进行协作，没有层级管理关系。

**核心设计原则**

| 原则 | 说明 |
|------|------|
| 角色驱动 | Agent 行为由角色定义决定 |
| 对话循环 | 通过消息传递推进任务 |
| 可选增强 | Critic、Task Planner 等可选组件 |
| 灵活配置 | 支持自定义 Agent 和系统消息 |

### 1.2 核心组件

```python
class RolePlaying:
    def __init__(
        self,
        assistant_role_name: str,      # 助手角色名称
        user_role_name: str,            # 用户角色名称
        task_prompt: str = "",          # 任务描述
        with_task_specify: bool = True, # 是否使用任务明确化
        with_task_planner: bool = False,# 是否使用任务规划
        with_critic_in_the_loop: bool = False,  # 是否启用批评者
        ...
    )
```

**Agent 成员构成**

| Agent 类型 | 职责 | 是否必需 |
|------------|------|----------|
| Assistant Agent | 执行具体任务 | 是 |
| User Agent | 提出需求和指令 | 是 |
| Critic Agent | 评估和选择响应 | 否 |
| Task Specify Agent | 明确化任务描述 | 否 |
| Task Planner Agent | 分解任务步骤 | 否 |

### 1.3 架构图

![Society架构图](camel-Society架构图.svg)

---

## 2. RolePlaying 实现

### 2.1 初始化流程

RolePlaying 的初始化分为四个阶段：

**第一步：任务处理**

```python
# 任务明确化：将模糊任务转换为具体指令
self._init_specified_task_prompt(...)

# 任务规划：将任务分解为可执行步骤
self._init_planned_task_prompt(...)
```

**第二步：系统消息生成**

```python
sys_msg_generator = SystemMessageGenerator(task_type=self.task_type)
init_assistant_sys_msg, init_user_sys_msg = sys_msg_generator.from_dicts(
    meta_dicts=sys_msg_meta_dicts,
    role_tuples=[
        (assistant_role_name, RoleType.ASSISTANT),
        (user_role_name, RoleType.USER),
    ],
)
```

**第三步：Agent 初始化**

```python
self._init_agents(
    init_assistant_sys_msg,
    init_user_sys_msg,
    ...
)
```

**第四步：Critic 初始化**

```python
if self.with_critic_in_the_loop:
    self._init_critic(...)
```

### 2.2 对话循环

**step 方法的核心逻辑**

```python
def step(self, assistant_msg: BaseMessage) -> Tuple[ChatAgentResponse, ChatAgentResponse]:
    # 1. User Agent 处理 Assistant 的消息
    user_response = self.user_agent.step(assistant_msg)
    user_msg = self._reduce_message_options(user_response.msgs)
    
    # 2. Assistant Agent 处理 User 的响应
    assistant_response = self.assistant_agent.step(user_msg)
    assistant_msg = self._reduce_message_options(assistant_response.msgs)
    
    return assistant_response, user_response
```

**对话流程图**

![角色扮演流程图](camel-角色扮演流程图.svg)

**异步支持**

```python
async def astep(self, assistant_msg: BaseMessage) -> Tuple[ChatAgentResponse, ChatAgentResponse]:
    user_response = await self.user_agent.astep(assistant_msg)
    # ... 同步逻辑相同
```

### 2.3 任务完成判断

**终止条件来源**

- Agent 自身返回 terminated=True
- ChatAgentResponse 中的 terminated 标志
- BabyAGI 模式：所有子任务完成

---

## 3. 多 Agent 对话循环

### 3.1 消息传递机制

**消息格式**

```python
class BaseMessage:
    role_name: str       # 发送者角色名
    role_type: RoleType  # 角色类型：ASSISTANT/USER/CRITIC
    content: str         # 消息内容
    meta_dict: Dict      # 元数据
```

**传递流程**

```
Assistant Agent → BaseMessage → User Agent
                                     ↓
Assistant Agent ← BaseMessage ← User Response
```

### 3.2 对话状态管理

**状态维护**

每个 Agent 维护自己的消息历史：

```python
self.assistant_agent.memory  # Assistant 的记忆
self.user_agent.memory       # User 的记忆
```

**重置机制**

```python
def init_chat(self, init_msg_content: Optional[str] = None) -> BaseMessage:
    self.assistant_agent.reset()  # 清空记忆
    self.user_agent.reset()
    # 返回初始消息
```

### 3.3 多响应处理

当 Agent 生成多个候选响应时，Critic 介入选择：

```python
def _reduce_message_options(self, messages: Sequence[BaseMessage]) -> BaseMessage:
    if len(messages) > 1 and self.with_critic_in_the_loop:
        # 使用 Critic 选择最优响应
        critic_response = self.critic.reduce_step(messages)
        return critic_response.msg
    else:
        # 直接返回第一个响应
        return messages[0]
```

---

## 4. 角色定义

### 4.1 Persona 类

**核心属性**

```python
class Persona(BaseModel):
    name: Optional[str] = None              # 角色名称
    description: Optional[str] = None       # 角色描述
    _id: uuid.UUID                          # 唯一标识符
    text_to_persona_prompt: Union[TextPrompt, str]      # 文本生成角色的提示词
    persona_to_persona_prompt: Union[TextPrompt, str]   # 角色扩展的提示词
```

### 4.2 系统消息生成

SystemMessageGenerator 根据角色类型生成系统消息：

```python
class SystemMessageGenerator:
    def __init__(self, task_type: TaskType = TaskType.AI_SOCIETY):
        # 加载不同角色的提示词模板
        self.sys_prompts[RoleType.ASSISTANT] = assistant_prompt_template
        self.sys_prompts[RoleType.USER] = user_prompt_template
        self.sys_prompts[RoleType.CRITIC] = critic_prompt_template
        
    def from_dict(self, meta_dict: Dict, role_tuple: Tuple) -> BaseMessage:
        # 使用模板和元数据生成系统消息
        sys_prompt = self.sys_prompts[role_type].format(**meta_dict)
        return BaseMessage(role_name=role_name, content=sys_prompt)
```

**角色类型枚举**

```python
class RoleType(Enum):
    ASSISTANT = "assistant"    # 助手
    USER = "user"              # 用户
    SYSTEM = "system"          # 系统
    CRITIC = "critic"          # 批评者
    EMBODIMENT = "embodiment"  # 具身智能
    DEFAULT = "default"        # 默认
```

### 4.3 角色行为约束

**约束来源**

| 来源 | 说明 |
|------|------|
| 系统消息 | 定义角色的身份和行为准则 |
| 任务类型 | AI_SOCIETY、CODE、MISALIGNMENT 等 |
| 输出语言 | 指定 Agent 的输出语言 |
| 模型配置 | 温度、最大token等参数 |

### 4.4 PersonaHub 角色仓库

PersonaHub 提供大规模角色管理能力：

```python
class PersonaHub:
    def __init__(self, model: Optional[BaseModelBackend] = None):
        self.personas: Dict[uuid.UUID, Persona] = {}
    
    def text_to_persona(self, text: str, action: str = "read") -> Persona:
        # 从文本推断合适的角色
        
    def persona_to_persona(self, persona: Persona) -> Dict[uuid.UUID, Persona]:
        # 基于人际关系扩展更多角色
        
    def deduplicate(self, similarity_threshold: float = 0.85):
        # 基于语义相似度去重
```

---

## 5. 任务分配策略

### 5.1 基于角色的任务分配

**Task Specify Agent**

将模糊任务转换为具体可执行的指令：

```python
task_specify_meta_dict = {
    "assistant_role": assistant_role_name,
    "user_role": user_role_name,
    "task": self.task_prompt,
}
specified_task = task_specify_agent.run(
    self.task_prompt, 
    meta_dict=task_specify_meta_dict
)
```

**Task Planner Agent**

将任务分解为步骤化的执行计划：

```python
planned_task_prompt = task_planner_agent.run(self.task_prompt)
# 追加到原始任务后
self.task_prompt = f"{self.task_prompt}\n{planned_task_prompt}"
```

### 5.2 BabyAGI 模式

BabyAGI 实现了动态任务管理：

```python
class BabyAGI:
    def step(self) -> ChatAgentResponse:
        # 1. 获取最高优先级任务
        task_name = self.subtasks.popleft()
        
        # 2. 执行任务
        assistant_response = self.assistant_agent.step(task_msg)
        
        # 3. 基于结果创建新任务
        new_subtask_list = self.task_creation_agent.run(task_list=past_tasks)
        
        # 4. 重新排序任务优先级
        prioritized_subtask_list = self.task_prioritization_agent.run(new_subtask_list)
        self.subtasks = deque(prioritized_subtask_list)
```

**任务状态管理**

| 状态 | 说明 |
|------|------|
| subtasks | 待处理任务队列 |
| solved_subtasks | 已完成任务列表 |
| MAX_TASK_HISTORY | 历史任务窗口大小 |

### 5.3 协作任务分解

**多 Agent 协作场景**

```
原始任务
    ↓
Task Specify Agent → 明确化任务
    ↓
Task Planner Agent → 分解为子任务
    ↓
Assistant Agent 执行 ←→ User Agent 反馈
    ↓
Critic Agent 评估结果
    ↓
任务完成 / 继续迭代
```

---

## 6. 与 smolagents 多 Agent 对比

| 维度 | CAMEL Society | smolagents Multi-Agent |
|------|---------------|------------------------|
| 协作模式 | 平等对话 | Manager-Managed |
| 通信方式 | 自然语言 | 工具调用包装 |
| 角色定义 | 丰富的 Persona | 简单的 name/description |
| 任务分解 | Task Planner + BabyAGI | 通过 Manager 委托 |
| 状态管理 | Agent 各自维护记忆 | 共享状态或工具结果 |
| Critic 机制 | 内置 CriticAgent | 需自行实现 |
| 适用场景 | 复杂角色扮演 | 任务委托执行 |
| 学习曲线 | 较陡 | 较平缓 |

### 6.1 架构差异

**CAMEL：去中心化对话**

```
Agent A ←→ Agent B
   ↕         ↕
Agent C ←→ Agent D
```

**smolagents：中心化委托**

```
    Manager Agent
    /     |     \
 Agent A Agent B Agent C
```

### 6.2 选择建议

| 场景 | 推荐框架 |
|------|----------|
| 需要丰富的角色定义 | CAMEL |
| 角色扮演研究 | CAMEL |
| 快速任务执行 | smolagents |
| 工具调用链 | smolagents |
| 多 Agent 自主协作 | CAMEL |
| 与现有系统集成 | smolagents |

---

## 7. 代码示例

### 7.1 基础 RolePlaying

```python
from camel.societies import RolePlaying

# 创建角色扮演会话
society = RolePlaying(
    assistant_role_name="Python 程序员",
    user_role_name="产品经理",
    task_prompt="开发一个数据可视化工具",
    with_task_specify=True,
    with_task_planner=True,
)

# 初始化对话
init_msg = society.init_chat()

# 运行对话循环
assistant_response, user_response = society.step(init_msg)
```

### 7.2 使用 Critic

```python
society = RolePlaying(
    assistant_role_name="作家",
    user_role_name="编辑",
    task_prompt="写一篇关于 AI 的文章",
    with_critic_in_the_loop=True,
    critic_role_name="文学评论家",
    critic_criteria="文章逻辑性和可读性",
)
```

### 7.3 BabyAGI 任务管理

```python
from camel.societies import BabyAGI

baby_agi = BabyAGI(
    assistant_role_name="研究员",
    user_role_name="导师",
    task_prompt="研究 Transformer 架构的演进",
    max_task_history=10,
)

# 执行一步
response = baby_agi.step()
```

---

## 8. 关联文档

- [[01-camel-项目总览]]
- [[02-camel-单Agent机制]]
- [[04-camel-工具集成]]

---

## 标签

框架：CAMEL  
主题：多 Agent 协作、角色扮演  
来源：源码分析
