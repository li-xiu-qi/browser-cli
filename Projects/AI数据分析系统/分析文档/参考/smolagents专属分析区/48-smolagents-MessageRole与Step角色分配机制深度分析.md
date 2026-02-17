# smolagents MessageRole与Step角色分配机制深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/memory.py, src/smolagents/models.py

---

## 一、MessageRole枚举体系

### 1.1 标准角色与自定义角色

smolagents 定义了 5 种消息角色，其中 3 种是 OpenAI 标准角色，2 种是框架自定义扩展。

```python
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant" 
    SYSTEM = "system"
    TOOL_CALL = "tool-call"          # smolagents 自定义
    TOOL_RESPONSE = "tool-response"  # smolagents 自定义
```

**OpenAI 标准角色**

| 角色 | 值 | 用途 |
|------|-----|------|
| USER | "user" | 用户输入，包括任务描述、观察结果图片等 |
| ASSISTANT | "assistant" | 模型输出，包括思考过程、最终答案 |
| SYSTEM | "system" | 系统提示，设定 Agent 行为模式 |

**smolagents 自定义角色**

| 角色 | 值 | 用途 |
|------|-----|------|
| TOOL_CALL | "tool-call" | 标识工具调用动作，记录调用的工具和参数 |
| TOOL_RESPONSE | "tool-response" | 标识工具执行结果，包括观察结果和错误信息 |

**为什么需要自定义 role**

1. **语义清晰**: 在内部表示中区分工具调用和工具响应，与普通的 assistant/user 消息分离
2. **灵活转换**: 不同模型 API 对 role 的支持不同，内部使用自定义 role 便于统一处理后再转换
3. **调试友好**: 在日志和监控中可以清晰识别工具交互环节
4. **多模态支持**: 工具响应可能包含图片等多模态内容，需要特殊处理

### 1.2 Role 转换机制

```python
tool_role_conversions = {
    MessageRole.TOOL_CALL: MessageRole.ASSISTANT,
    MessageRole.TOOL_RESPONSE: MessageRole.USER,
}
```

**转换的目的**

TOOL_CALL 和 TOOL_RESPONSE 是 smolagents 内部使用的自定义 role，在发送给 LLM API 之前需要转换为标准 role，原因如下：

1. **TOOL_CALL → ASSISTANT**: 工具调用是模型生成的输出，本质上是 assistant 角色产生的动作决策。OpenAI 等标准 API 将工具调用视为 assistant 消息的一部分。

2. **TOOL_RESPONSE → USER**: 工具执行结果是外部系统返回给模型的输入，相当于 user 提供给模型的上下文信息。标准 API 通常用 user 或 tool 角色表示。

**哪些模型需要转换**

几乎所有模型都需要转换，但转换目标可能不同：

- **OpenAI/GPT 系列**: 转换为 assistant/user/tool
- **Anthropic/Claude 系列**: 转换为 assistant/user
- **Amazon Bedrock**: 所有 role 都转换为 user，因为 Bedrock 对 role 限制最严格
- **本地模型**: 根据 chat template 灵活处理

**转换的实际效果**

转换发生在 `get_clean_message_list()` 函数中，在准备 API 请求参数时完成。转换后的消息序列符合标准对话格式，确保模型能正确理解对话流程。

![Role转换机制图](smolagents-Role转换机制图.svg)

---

## 二、Step到Message的映射

smolagents 使用 MemoryStep 作为对话历史的基本单元，每种 Step 类型都有对应的 `to_messages()` 方法，将其转换为 ChatMessage 列表。

### 2.1 SystemPromptStep

```python
def to_messages(self, summary_mode: bool = False):
    if summary_mode:
        return []
    return [ChatMessage(
        role=MessageRole.SYSTEM, 
        content=[{"type": "text", "text": self.system_prompt}]
    )]
```

**为什么 summary_mode 时返回空**

summary_mode 用于生成对话摘要，目的是压缩历史消息以节省 token。系统提示通常包含大量指令性内容，在摘要中可以省略，因为：

1. 摘要关注任务执行过程，而非初始设定
2. 系统提示在每次请求都会发送，摘要中不需要重复
3. 省略系统提示可以显著减少 token 消耗

**SYSTEM role 的作用和限制**

- 作用: 设定 Agent 的身份、能力边界、行为规则、输出格式
- 限制: 某些模型不支持 system role，如早期的一些开源模型，需要通过 role conversion 转换为 user

### 2.2 TaskStep

```python
def to_messages(self, summary_mode: bool = False):
    content = [{"type": "text", "text": f"New task:\n{self.task}"}]
    if self.task_images:
        content.extend([{"type": "image", "image": image} for image in self.task_images])
    return [ChatMessage(role=MessageRole.USER, content=content)]
```

**为什么 Task 是 USER role**

任务描述是用户向 Agent 发起的要求，属于外部输入，因此标记为 USER role。这符合对话直觉：

1. 用户提出问题/任务
2. Agent 作为 assistant 响应
3. 保持 user-assistant 交替的对话模式

**多模态支持**

TaskStep 支持 `task_images` 参数，允许用户在任务中附加图片。图片以特殊的 content 格式嵌入：

```python
{"type": "image", "image": image_object}
```

这种格式在 `get_clean_message_list()` 中会被进一步处理，转换为 base64 编码或 image_url，取决于模型要求。

### 2.3 PlanningStep

```python
def to_messages(self, summary_mode: bool = False):
    if summary_mode:
        return []
    return [
        ChatMessage(role=MessageRole.ASSISTANT, content=[{"type": "text", "text": self.plan.strip()}]),
        ChatMessage(
            role=MessageRole.USER, 
            content=[{"type": "text", "text": "Now proceed and carry out this plan."}]
        ),
    ]
```

**为什么有两条消息**

PlanningStep 产生两条消息，这是 smolagents 的设计巧思：

1. **第一条 ASSISTANT**: 记录模型生成的计划内容
2. **第二条 USER**: 一条固定的指令 "Now proceed and carry out this plan."

**第二条消息的目的**

注释中明确说明: "This second message creates a role change to prevent models from simply continuing the plan message"

这解决了 LLM 的一个常见问题：模型可能会继续生成计划内容，而不是执行计划。通过插入一条 USER 消息强制角色切换，告诉模型 "计划已经结束，现在需要执行"。

### 2.4 ActionStep（最复杂）

ActionStep 是 smolagents 中最复杂的 Step 类型，可能产生 0-4 条消息：

```python
def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
    messages = []
    
    # 1. 模型输出（Thought）
    if self.model_output is not None and not summary_mode:
        messages.append(ChatMessage(
            role=MessageRole.ASSISTANT, 
            content=[{"type": "text", "text": self.model_output.strip()}]
        ))
    
    # 2. 工具调用
    if self.tool_calls is not None:
        messages.append(ChatMessage(
            role=MessageRole.TOOL_CALL,
            content=[{"type": "text", "text": "Calling tools:\n" + str([tc.dict() for tc in self.tool_calls])}]
        ))
    
    # 3. 观察结果图片
    if self.observations_images:
        messages.append(ChatMessage(
            role=MessageRole.USER,
            content=[{"type": "image", "image": image} for image in self.observations_images]
        ))
    
    # 4. 观察结果文本
    if self.observations is not None:
        messages.append(ChatMessage(
            role=MessageRole.TOOL_RESPONSE,
            content=[{"type": "text", "text": f"Observation:\n{self.observations}"}]
        ))
    
    # 5. 错误信息
    if self.error is not None:
        messages.append(ChatMessage(
            role=MessageRole.TOOL_RESPONSE, 
            content=[{"type": "text", "text": message_content}]
        ))
    
    return messages
```

**为什么 ActionStep 可能产生多条消息**

ActionStep 代表一个完整的行动-观察循环，包含多个环节：

1. **Thought**: 模型的思考过程，ASSISTANT role
2. **Tool Call**: 调用工具的决策，TOOL_CALL role
3. **Observation Images**: 工具返回的图片结果，USER role
4. **Observation Text**: 工具返回的文本结果，TOOL_RESPONSE role
5. **Error**: 执行过程中的错误，TOOL_RESPONSE role

这些消息按顺序排列，形成完整的交互记录。

**图片为什么是 USER role**

观察结果图片是工具执行后返回给模型的输入，类似于用户上传的图片，因此使用 USER role。这与 TaskStep 中的 task_images 保持一致的处理逻辑。

**Error 为什么是 TOOL_RESPONSE**

错误信息是工具执行或 Agent 运行的结果反馈，与正常的观察结果性质相同，都是外部系统返回给模型的信息，因此统一使用 TOOL_RESPONSE role。

![Step到Message映射关系图](smolagents-Step到Message映射关系图.svg)

---

## 三、消息序列的构建流程

### 3.1 AgentMemory如何组装消息

```python
class AgentMemory:
    def __init__(self, system_prompt: str):
        self.system_prompt: SystemPromptStep = SystemPromptStep(system_prompt)
        self.steps: list[TaskStep | ActionStep | PlanningStep] = []
    
    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        messages = self.system_prompt.to_messages(summary_mode)
        for step in self.steps:
            messages.extend(step.to_messages(summary_mode))
        return messages
```

AgentMemory 是消息序列的管理中心，采用组合模式：

1. **初始化时**: 创建 SystemPromptStep 作为基础
2. **运行时**: 逐步添加 TaskStep、PlanningStep、ActionStep
3. **生成请求时**: 遍历所有 step，调用各自的 to_messages()，合并成完整列表

### 3.2 完整消息序列示例

一个典型的对话流程产生的消息序列如下：

```
[Step 0] SystemPromptStep → SYSTEM
[Step 1] TaskStep → USER (任务)
[Step 2] ActionStep → ASSISTANT (Thought) + TOOL_CALL (调用)
[Step 3] ActionStep → USER (图片) + TOOL_RESPONSE (结果)
[Step 4] ActionStep → ASSISTANT (Thought) + TOOL_CALL (调用)
[Step 5] ActionStep → TOOL_RESPONSE (结果)
[Step 6] ActionStep → ASSISTANT (最终答案)
```

**序列特点**

1. 始终以 SYSTEM 开头，设定 Agent 行为
2. 然后是 USER 任务描述
3. 进入 ASSISTANT-TOOL_CALL-TOOL_RESPONSE 循环
4. 最终以 ASSISTANT 输出结束

这种结构确保模型始终清楚自己在对话中的位置和下一步该做什么。

![消息序列构建流程图](smolagents-消息序列构建流程图.svg)

---

## 四、ToolCallingAgent与CodeAgent的差异

### 4.1 ToolCallingAgent

ToolCallingAgent 使用结构化的工具调用格式：

- **tool_calls**: 结构化的 JSON，包含工具名称和参数
- **TOOL_CALL role**: 清晰标记工具调用动作
- **TOOL_RESPONSE role**: 接收工具执行结果
- **优点**: 格式规范，易于解析，适合需要精确参数的场景

### 4.2 CodeAgent

CodeAgent 使用代码作为行动表达方式：

- **code_action**: 代码字符串作为 Action
- **model_output**: 包含代码的完整 assistant 输出
- **observations**: 代码执行结果，通常是 print 输出或返回值
- **优点**: 灵活性强，可以利用 Python 的全部能力

**CodeAgent 的消息特点**

在 CodeAgent 中，代码本身作为 ASSISTANT 输出的一部分，不需要单独的 TOOL_CALL 消息。观察结果仍然使用 TOOL_RESPONSE，但内容可能是代码执行的标准输出。

---

## 五、实际消息流转案例

### 5.1 ToolCallingAgent案例

用户输入: "查询北京天气"

```
SYSTEM: "你是一个天气查询助手..."
USER: "New task:\n查询北京天气"
ASSISTANT: "我来帮您查询北京的天气情况"
TOOL_CALL: "Calling tools: [{get_weather, args: {city: '北京'}}]"
TOOL_RESPONSE: "Observation:\n{'temperature': 25, 'weather': '晴天', 'humidity': 60%}"
ASSISTANT: "北京今天晴天，气温25度，湿度60%，非常适合外出"
```

### 5.2 CodeAgent案例

用户输入: "计算 1+2+...+100"

```
SYSTEM: "你是一个Python代码执行助手..."
USER: "New task:\n计算 1+2+...+100"
ASSISTANT: "我来用Python计算这个等差数列的和：\n```python\nresult = sum(range(1, 101))\nprint(result)\n```"
TOOL_RESPONSE: "Observation:\n5050"
ASSISTANT: "计算结果是 5050"
```

**对比分析**

| 特性 | ToolCallingAgent | CodeAgent |
|------|------------------|-----------|
| 行动表达 | 结构化 JSON | Python 代码 |
| 消息复杂度 | 需要 TOOL_CALL 消息 | 代码在 ASSISTANT 中 |
| 灵活性 | 受限于预定义工具 | 任意 Python 代码 |
| 适用场景 | 明确工具调用 | 复杂计算和逻辑 |

---

## 六、消息格式与模型兼容性

### 6.1 OpenAI格式

OpenAI 标准格式支持以下 role：

```json
{
    "role": "assistant" | "user" | "system" | "tool",
    "content": "..."
}
```

### 6.2 smolagents格式转换

在 `get_clean_message_list()` 函数中完成转换：

```python
def get_clean_message_list(
    message_list: list[ChatMessage | dict],
    role_conversions: dict[MessageRole, MessageRole] = {},
    convert_images_to_image_urls: bool = False,
    flatten_messages_as_text: bool = False,
) -> list[dict[str, Any]]:
```

转换包括：

1. **Role 转换**: 应用 tool_role_conversions 或其他自定义转换
2. **图片处理**: 转换为 base64 或 image_url 格式
3. **消息合并**: 合并连续相同 role 的消息，减少 token 消耗
4. **格式扁平化**: 某些模型需要纯文本格式

**Amazon Bedrock 的特殊处理**

```python
custom_role_conversions = {
    MessageRole.SYSTEM: MessageRole.USER,
    MessageRole.ASSISTANT: MessageRole.USER,
    MessageRole.TOOL_CALL: MessageRole.USER,
    MessageRole.TOOL_RESPONSE: MessageRole.USER,
}
```

Bedrock 将所有 role 转换为 USER，因为其 API 限制：

1. 只支持 user 和 assistant 两种 role
2. 不允许对话以 assistant 开头
3. 对 role 切换有严格要求

---

## 七、对我们项目的启示

### 7.1 如何扩展新的Step类型

参考 MemoryStep 的实现方式：

```python
@dataclass
class CustomStep(MemoryStep):
    custom_data: str
    
    def to_messages(self, summary_mode: bool = False):
        if summary_mode:
            return []  # 摘要模式下可选择性省略
        return [ChatMessage(
            role=MessageRole.ASSISTANT,
            content=[{"type": "text", "text": self.custom_data}]
        )]
```

**扩展建议**

1. 继承 MemoryStep 基类
2. 实现 to_messages 方法，返回 ChatMessage 列表
3. 考虑 summary_mode 的处理
4. 选择合适的 MessageRole
5. 支持多模态时使用 content 列表格式

### 7.2 如何自定义role转换

可以通过 custom_role_conversions 参数自定义：

```python
from smolagents.models import MessageRole

custom_role_conversions = {
    MessageRole.TOOL_CALL: MessageRole.ASSISTANT,
    MessageRole.TOOL_RESPONSE: MessageRole.TOOL,  # 某些模型支持 tool role
}

model = OpenAIModel(
    model_id="gpt-4",
    custom_role_conversions=custom_role_conversions
)
```

**自定义场景**

1. 对接特殊 API 格式
2. 实验新的消息组织方式
3. 适配企业私有模型

---

## 八、常见问题与陷阱

### 8.1 summary_mode导致信息丢失

**问题**: 启用 summary_mode 后，SystemPromptStep 和 PlanningStep 返回空列表，可能导致模型丢失上下文。

**解决方案**: 在摘要中保留关键信息，或确保摘要本身包含足够的上下文。

### 8.2 TOOL_CALL/TOOL_RESPONSE不被某些模型支持

**问题**: 忘记应用 role_conversions，直接发送自定义 role 给 API。

**解决方案**: 始终在发送前调用 `get_clean_message_list()`，确保 role 已转换。

### 8.3 多模态消息的顺序问题

**问题**: 图片和文本的顺序可能影响模型理解。

**最佳实践**: 按照 smolagents 的设计，图片先于文本，保持统一的顺序模式。

### 8.4 Error消息的角色归属

**问题**: 错误信息可能被误认为是用户输入。

**澄清**: Error 使用 TOOL_RESPONSE role 转换为 USER，这是因为错误是外部系统反馈，与工具执行结果性质相同。

### 8.5 连续相同role的消息合并

**问题**: 某些场景下不希望合并消息。

**注意**: `get_clean_message_list()` 会自动合并连续相同 role，如需分隔，需要插入不同 role 的消息。

---

## 九、总结

smolagents 的 MessageRole 与 Step 角色分配机制是其核心设计之一，具有以下特点：

1. **内部表示与外部格式的分离**: 使用自定义 role 进行内部管理，发送前转换为标准格式

2. **灵活的转换机制**: 通过 role_conversions 字典支持不同模型的要求

3. **清晰的语义分层**: SYSTEM 设定、USER 输入、ASSISTANT 输出、TOOL 交互，职责分明

4. **多模态友好**: content 列表格式支持文本和图片混合

5. **可扩展性强**: MemoryStep 基类设计便于添加新的 Step 类型

对于我们的 AI 数据分析系统项目，这些设计思想具有重要参考价值：

- 可以参考 smolagents 的 role 设计，建立清晰的对话语义
- 学习其转换机制，实现多模型兼容
- 借鉴 Step 模式，设计适合数据分析场景的交互单元
- 使用类似的 content 列表格式，支持图表等多模态内容

---

**参考文档**

- smolagents 源码: src/smolagents/memory.py
- smolagents 源码: src/smolagents/models.py
- 相关图表:
  - [[smolagents-Step到Message映射关系图.svg]]
  - [[smolagents-消息序列构建流程图.svg]]
  - [[smolagents-Role转换机制图.svg]]
