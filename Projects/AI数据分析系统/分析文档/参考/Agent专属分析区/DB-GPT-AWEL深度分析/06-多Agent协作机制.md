# 06-多 Agent 协作机制

**分析对象**: DB-GPT Multi-Agent 框架  
**分析日期**: 2026-02-08

---

## TL;DR

DB-GPT 采用 **数据驱动的自演进 Multi-Agent 框架**，核心组件：**Agent 定义** → **消息总线** → **协作协议** → **执行编排**。

---

## 1. Agent 定义

### 1.1 ConversableAgent

```python
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

class AgentRole(Enum):
    """Agent 角色类型"""
    ASSISTANT = "assistant"
    USER_PROXY = "user_proxy"
    EXECUTOR = "executor"
    PLANNER = "planner"
    CRITIC = "critic"

@dataclass
class AgentCapability:
    """Agent 能力描述"""
    name: str
    description: str
    tools: List[str]
    llm_model: Optional[str] = None

class ConversableAgent:
    """
    可对话 Agent 基类
    
    类似于 AutoGen 的 ConversableAgent，但深度集成 DB-GPT 的数据能力
    """
    
    def __init__(
        self,
        name: str,
        role: AgentRole,
        system_message: str,
        llm_config: Optional[Dict] = None,
        function_map: Optional[Dict[str, Callable]] = None,
        human_input_mode: str = "NEVER",  # ALWAYS, TERMINATE, NEVER
        max_consecutive_auto_reply: int = 10,
    ):
        self.name = name
        self.role = role
        self.system_message = system_message
        self.llm_config = llm_config or {}
        self.function_map = function_map or {}
        self.human_input_mode = human_input_mode
        self.max_consecutive_auto_reply = max_consecutive_auto_reply
        
        # 消息历史
        self.chat_history: List[Message] = []
        
        # 可管理的子 Agent (类似 AutoGen)
        self._managed_agents: List[ConversableAgent] = []
        
        # 回复生成函数
        self._reply_func_list: List[Callable] = []
        self._register_reply_functions()
    
    def _register_reply_functions(self):
        """注册回复生成函数，按优先级排序"""
        self._reply_func_list = [
            self._check_human_input,
            self._generate_function_call_reply,
            self._generate_llm_reply,
        ]
    
    async def generate_reply(
        self,
        messages: Optional[List[Message]] = None,
        sender: Optional["ConversableAgent"] = None,
        **kwargs
    ) -> Reply:
        """
        生成回复
        
        核心流程：
        1. 检查是否需要人类输入
        2. 尝试函数调用
        3. 调用 LLM 生成回复
        """
        if messages is None:
            messages = self.chat_history
        
        for reply_func in self._reply_func_list:
            reply = await reply_func(messages, sender, **kwargs)
            if reply is not None:
                return reply
        
        return Reply(content="", type="none")
    
    async def _generate_llm_reply(
        self,
        messages: List[Message],
        sender: Optional["ConversableAgent"],
        **kwargs
    ) -> Optional[Reply]:
        """使用 LLM 生成回复"""
        # 调用 LLM
        response = await llm_client.chat.completions.create(
            model=self.llm_config.get("model", "gpt-4"),
            messages=[
                {"role": "system", "content": self.system_message},
                *[m.to_dict() for m in messages]
            ],
            functions=list(self.function_map.keys()) if self.function_map else None,
        )
        
        content = response.choices[0].message.content
        function_call = response.choices[0].message.function_call
        
        if function_call:
            return Reply(
                content=content,
                type="function_call",
                function_call=function_call
            )
        
        return Reply(content=content, type="text")
    
    async def _generate_function_call_reply(
        self,
        messages: List[Message],
        sender: Optional["ConversableAgent"],
        **kwargs
    ) -> Optional[Reply]:
        """执行函数调用并返回结果"""
        last_message = messages[-1] if messages else None
        
        if last_message and last_message.function_call:
            func_name = last_message.function_call.name
            func_args = last_message.function_call.arguments
            
            if func_name in self.function_map:
                func = self.function_map[func_name]
                result = await func(**func_args)
                return Reply(
                    content=str(result),
                    type="function_result"
                )
        
        return None
    
    def _check_human_input(
        self,
        messages: List[Message],
        sender: Optional["ConversableAgent"],
        **kwargs
    ) -> Optional[Reply]:
        """检查是否需要人类输入"""
        if self.human_input_mode == "ALWAYS":
            # 请求人类输入
            return None  # 实际实现会阻塞等待输入
        
        if self.human_input_mode == "TERMINATE":
            # 检查是否需要终止并询问人类
            if self._should_terminate(messages):
                return None  # 请求人类确认
        
        return None
    
    def register_function(self, func: Callable):
        """注册工具函数"""
        self.function_map[func.__name__] = func
    
    def add_managed_agent(self, agent: "ConversableAgent"):
        """添加管理的子 Agent"""
        self._managed_agents.append(agent)
```

### 1.2 专业化 Agent 子类

```python
class DataAnalystAgent(ConversableAgent):
    """数据分析 Agent"""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(
            name=name,
            role=AgentRole.ASSISTANT,
            system_message="""你是一个专业的数据分析师。
            
            你的职责：
            1. 理解用户的分析需求
            2. 编写 SQL 或 Python 代码进行数据分析
            3. 解释分析结果并提供洞察
            
            工具：
            - execute_sql: 执行 SQL 查询
            - execute_python: 执行 Python 代码
            - visualize: 生成可视化图表
            """,
            **kwargs
        )
        
        # 注册专业工具
        self.register_function(self.execute_sql)
        self.register_function(self.execute_python)
        self.register_function(self.visualize)
    
    async def execute_sql(self, query: str) -> str:
        """执行 SQL"""
        # 实现...
        pass
    
    async def execute_python(self, code: str) -> str:
        """执行 Python"""
        # 实现...
        pass
    
    async def visualize(self, data: str, chart_type: str) -> str:
        """生成图表"""
        # 实现...
        pass

class SQLGeneratorAgent(ConversableAgent):
    """SQL 生成 Agent"""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(
            name=name,
            role=AgentRole.ASSISTANT,
            system_message="你是一个 SQL 专家，擅长将自然语言转换为精确的 SQL 查询。",
            **kwargs
        )

class SchemaExpertAgent(ConversableAgent):
    """Schema 专家 Agent"""
    
    def __init__(self, name: str, **kwargs):
        super().__init__(
            name=name,
            role=AgentRole.ASSISTANT,
            system_message="你是数据库 Schema 专家，熟悉表结构、字段含义和关系。",
            **kwargs
        )
```

---

## 2. 消息系统

### 2.1 消息模型

```python
from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class Message:
    """Agent 间消息"""
    id: str
    sender: str           # 发送者 Agent 名称
    receiver: str         # 接收者 Agent 名称
    content: str          # 消息内容
    type: str            # 消息类型: text, function_call, function_result
    
    # 可选字段
    function_call: Optional[Dict] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 会话追踪
    conversation_id: Optional[str] = None
    round_index: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "role": "user" if self.receiver != self.sender else "assistant",
            "content": self.content,
            "name": self.sender,
        }

@dataclass
class GptsMessage:
    """
    GPTs 风格的消息 (DB-GPT 扩展)
    
    支持更丰富的元数据和意图追踪
    """
    conv_id: str
    sender: str
    receiver: str
    role: str
    content: str
    
    # 意图追踪
    current_goal: Optional[str] = None  # 当前意图/目标
    action_report: Optional[str] = None  # 行动报告
    
    # 模型信息
    model_name: Optional[str] = None
    
    # 轮次追踪
    rounds: int = 0
    
    created_at: datetime = field(default_factory=datetime.now)
```

### 2.2 消息总线

```python
import asyncio
from typing import AsyncIterator

class MessageBus:
    """
    Agent 间消息总线
    
    实现发布-订阅模式
    """
    
    def __init__(self):
        self._channels: Dict[str, asyncio.Queue] = {}
        self._subscribers: Dict[str, List[str]] = {}  # channel -> [agent_names]
    
    def create_channel(self, channel_id: str) -> asyncio.Queue:
        """创建消息通道"""
        if channel_id not in self._channels:
            self._channels[channel_id] = asyncio.Queue()
            self._subscribers[channel_id] = []
        return self._channels[channel_id]
    
    def subscribe(self, channel_id: str, agent_name: str):
        """订阅通道"""
        if channel_id not in self._channels:
            self.create_channel(channel_id)
        self._subscribers[channel_id].append(agent_name)
    
    async def publish(
        self, 
        channel_id: str, 
        message: Message
    ):
        """发布消息到通道"""
        if channel_id in self._channels:
            await self._channels[channel_id].put(message)
    
    async def receive(
        self, 
        channel_id: str, 
        agent_name: str
    ) -> AsyncIterator[Message]:
        """接收消息"""
        queue = self._channels.get(channel_id)
        if not queue:
            return
        
        while True:
            message = await queue.get()
            if message.receiver == agent_name or message.receiver == "*":
                yield message
    
    async def send_direct(
        self, 
        from_agent: str, 
        to_agent: str, 
        message: Message
    ):
        """直接发送消息给特定 Agent"""
        # 创建 Agent 专属通道
        channel_id = f"{from_agent}_{to_agent}"
        await self.publish(channel_id, message)
```

---

## 3. 协作模式

### 3.1 群聊模式 (Group Chat)

```python
class GroupChat:
    """
    多 Agent 群聊
    
    类似 AutoGen 的 GroupChat
    """
    
    def __init__(
        self,
        agents: List[ConversableAgent],
        messages: Optional[List[Message]] = None,
        max_round: int = 10,
        speaker_selection_method: str = "auto",  # auto, round_robin, random
    ):
        self.agents = {agent.name: agent for agent in agents}
        self.messages = messages or []
        self.max_round = max_round
        self.speaker_selection_method = speaker_selection_method
        
        # 注册所有 Agent 到消息总线
        self.message_bus = MessageBus()
        self.channel_id = f"group_chat_{id(self)}"
        
        for agent in agents:
            self.message_bus.subscribe(self.channel_id, agent.name)
    
    async def run(self, init_message: str, sender: str) -> List[Message]:
        """运行群聊"""
        # 添加初始消息
        self.messages.append(Message(
            id=str(uuid.uuid4()),
            sender=sender,
            receiver="*",  # 广播给所有人
            content=init_message,
            type="text"
        ))
        
        current_round = 0
        current_speaker = self._select_next_speaker()
        
        while current_round < self.max_round:
            # 当前发言者生成回复
            reply = await self.agents[current_speaker].generate_reply(
                messages=self.messages,
                sender=None
            )
            
            if reply.type == "none":
                break
            
            # 创建消息
            message = Message(
                id=str(uuid.uuid4()),
                sender=current_speaker,
                receiver="*",
                content=reply.content,
                type=reply.type,
                function_call=reply.function_call
            )
            
            self.messages.append(message)
            
            # 广播消息
            await self.message_bus.publish(self.channel_id, message)
            
            # 选择下一个发言者
            current_speaker = self._select_next_speaker(current_speaker)
            current_round += 1
        
        return self.messages
    
    def _select_next_speaker(self, last_speaker: Optional[str] = None) -> str:
        """选择下一个发言者"""
        if self.speaker_selection_method == "round_robin":
            agent_names = list(self.agents.keys())
            if last_speaker is None:
                return agent_names[0]
            idx = agent_names.index(last_speaker)
            return agent_names[(idx + 1) % len(agent_names)]
        
        elif self.speaker_selection_method == "auto":
            # 使用 LLM 选择最合适的 Agent
            return self._llm_select_speaker()
        
        else:  # random
            return random.choice(list(self.agents.keys()))
```

### 3.2 工作流模式 (Workflow)

```python
class AgentWorkflow:
    """
    Agent 工作流编排
    
    使用 AWEL DAG 编排 Agent 执行
    """
    
    def __init__(self):
        self.dag = DAG("agent_workflow")
        self.agent_nodes: Dict[str, AgentNode] = {}
    
    def add_agent_step(
        self,
        agent: ConversableAgent,
        input_from: Optional[List[str]] = None,
        condition: Optional[Callable] = None
    ) -> "AgentWorkflow":
        """
        添加 Agent 执行步骤
        
        Args:
            agent: 执行的 Agent
            input_from: 输入来源步骤 (前置 Agent)
            condition: 执行条件
        """
        node = AgentNode(agent=agent, condition=condition)
        self.agent_nodes[agent.name] = node
        self.dag.add_node(node)
        
        if input_from:
            for prev_name in input_from:
                if prev_name in self.agent_nodes:
                    self.dag.add_edge(self.agent_nodes[prev_name], node)
        
        return self
    
    async def execute(self, initial_input: str) -> Dict[str, Any]:
        """执行工作流"""
        execution_order = self.dag.topological_sort()
        results: Dict[str, Any] = {}
        
        for node in execution_order:
            # 检查条件
            if node.condition and not node.condition(results):
                continue
            
            # 准备输入
            upstream = self.dag.get_upstream(node)
            if upstream:
                context = "\n".join([
                    f"{self.agent_nodes[n].agent.name}: {results.get(n, '')}"
                    for n in upstream
                ])
                input_msg = f"上下文:\n{context}\n\n任务: {initial_input}"
            else:
                input_msg = initial_input
            
            # 执行 Agent
            reply = await node.agent.generate_reply(
                messages=[Message(
                    id=str(uuid.uuid4()),
                    sender="user",
                    receiver=node.agent.name,
                    content=input_msg,
                    type="text"
                )]
            )
            
            results[node.agent.name] = reply.content
        
        return results
```

### 3.3 层级协作模式

```python
class HierarchicalTeam:
    """
    层级化 Agent 团队
    
    Manager -> Specialists
    """
    
    def __init__(
        self,
        manager: ConversableAgent,
        specialists: List[ConversableAgent]
    ):
        self.manager = manager
        self.specialists = {s.name: s for s in specialists}
        
        # Manager 管理所有 Specialist
        for specialist in specialists:
            self.manager.add_managed_agent(specialist)
    
    async def execute(self, task: str) -> str:
        """
        执行流程：
        1. Manager 分析任务
        2. Manager 分发给 Specialist
        3. Specialist 执行
        4. Manager 整合结果
        """
        # Manager 规划任务
        plan = await self._create_plan(task)
        
        # 并行执行子任务
        subtask_results = await asyncio.gather(*[
            self._execute_subtask(subtask)
            for subtask in plan.subtasks
        ])
        
        # Manager 整合结果
        final_result = await self._integrate_results(
            task, plan, subtask_results
        )
        
        return final_result
    
    async def _create_plan(self, task: str) -> TaskPlan:
        """Manager 创建执行计划"""
        reply = await self.manager.generate_reply(
            messages=[Message(
                id=str(uuid.uuid4()),
                sender="user",
                receiver=self.manager.name,
                content=f"请为以下任务创建执行计划: {task}",
                type="text"
            )]
        )
        # 解析计划...
        pass
    
    async def _execute_subtask(self, subtask: SubTask) -> str:
        """执行子任务"""
        specialist = self.specialists.get(subtask.assigned_to)
        if not specialist:
            raise ValueError(f"Unknown specialist: {subtask.assigned_to}")
        
        reply = await specialist.generate_reply(
            messages=[Message(
                id=str(uuid.uuid4()),
                sender=self.manager.name,
                receiver=specialist.name,
                content=subtask.description,
                type="text"
            )]
        )
        
        return reply.content
```

---

## 4. 与 AIASys 的对比

| 特性 | DB-GPT Multi-Agent | AIASys Host-Worker |
|------|-------------------|-------------------|
| **架构模式** | 多样化 (群聊/工作流/层级) | 固定 Host-Worker |
| **通信方式** | 消息总线 | 函数调用 |
| **灵活性** | 高 (多种协作模式) | 中 (固定结构) |
| **复杂度** | 高 | 低 |
| **适用场景** | 复杂多 Agent 协作 | 简单双 Agent 分析 |
| **消息追踪** | 完整的 GptsMessage | 简单的 step callback |

---

## 5. 总结

DB-GPT Multi-Agent 的核心设计：

1. **ConversableAgent** - 类似 AutoGen 的 Agent 基类
2. **消息总线** - 发布-订阅模式解耦通信
3. **多种协作模式** - 群聊、工作流、层级
4. **与 AWEL 集成** - Agent 可以嵌入 DAG 执行

---

*分析完成于 2026-02-08*
