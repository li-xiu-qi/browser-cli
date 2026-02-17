# CAMEL 流式输出机制分析

> 项目: CAMEL  
> 分析日期: 2026-02-08  
> 源码位置: camel/agents/chat_agent.py, camel/models/base_model.py

---

## 核心结论

> CAMEL 的流式输出机制非常完善，支持同步/异步流式、工具调用流式、DeepSeek reasoning_content，相比 smolagents 更加成熟和强大。

| 特性 | CAMEL | smolagents |
|------|-------|-----------|
| **流式模式** | 同步 + 异步 | 仅同步 Generator |
| **工具调用流式** |  支持流式返回 |  不支持 |
| **reasoning_content** |  支持 DeepSeek |  不支持 |
| **流式内容累积** |  可配置 |  不支持 |
| **流式工具执行** |  支持 |  不支持 |

---

## 一、流式输出架构

### 1.1 整体架构

```
用户调用 step(stream=True)
       │
       ▼
┌─────────────────────────────┐
│   ChatAgent.step()          │
│   - 检查 stream 配置        │
│   - 返回 StreamingChatAgentResponse │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   _stream() / _astream()    │
│   - 流式生成器核心          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   _stream_response()        │
│   - 处理流式响应            │
│   - 支持 reasoning_content  │
│   - 支持工具调用流式        │
└─────────────────────────────┘
```

### 1.2 关键组件

| 组件 | 文件位置 | 职责 |
|------|----------|------|
| `StreamingChatAgentResponse` | chat_agent.py:228 | 流式响应包装器 |
| `AsyncStreamingChatAgentResponse` | chat_agent.py:306 | 异步流式响应包装器 |
| `StreamContentAccumulator` | chat_agent.py:175 | 流式内容累积器 |
| `_SyncStreamWrapper` | base_model.py:121 | 同步流式包装器 |
| `_AsyncStreamWrapper` | base_model.py:158 | 异步流式包装器 |

---

## 二、流式输出类型

### 2.1 同步流式

```python
# chat_agent.py 第 2798-2827 行
def step(
    self,
    input_message: Union[BaseMessage, str],
    ...
) -> Union[ChatAgentResponse, StreamingChatAgentResponse]:
    
    # 从模型配置中读取 stream 设置
    stream = self.model_backend.model_config_dict.get("stream", False)
    
    if stream:
        # 返回流式响应包装器
        generator = self._stream(input_message, response_format)
        return StreamingChatAgentResponse(generator)
```

**使用示例**：

```python
# 启用流式输出
agent = ChatAgent(
    system_message=system_message,
    model=model,
    model_config={"stream": True}  # 启用流式
)

# 获取流式响应
response = agent.step(user_message)

# 迭代获取流式内容
for partial_response in response:
    print(partial_response.msgs[0].content)
```

### 2.2 异步流式

```python
# chat_agent.py 第 3089-3151 行
async def astep(
    self,
    input_message: Union[BaseMessage, str],
    ...
) -> Union[ChatAgentResponse, AsyncStreamingChatAgentResponse]:
    
    stream = self.model_backend.model_config_dict.get("stream", False)
    
    if stream:
        # 返回异步流式响应包装器
        async_generator = self._astream(input_message, response_format)
        return AsyncStreamingChatAgentResponse(async_generator)
```

**使用示例**：

```python
# 异步流式
response = await agent.astep(user_message)

async for partial_response in response:
    print(partial_response.msgs[0].content)
```

### 2.3 流式响应包装器

**StreamingChatAgentResponse**（chat_agent.py:228-305）：

```python
class StreamingChatAgentResponse:
    """流式响应包装器，兼容非流式代码"""
    
    def __init__(self, generator):
        self._generator = generator
        self._final_response = None
        
    def __iter__(self):
        """支持迭代"""
        for partial in self._generator:
            self._final_response = partial
            yield partial
            
    def __getattr__(self, name):
        """支持访问最终响应属性"""
        if self._final_response is None:
            # 消费整个流以获取最终响应
            for partial in self:
                pass
        return getattr(self._final_response, name)
```

**设计优势**：
- 既可以迭代获取流式内容
- 又可以像普通响应一样访问属性
- 完全兼容非流式代码

---

## 三、流式内容累积器

### 3.1 StreamContentAccumulator

**源码位置**: chat_agent.py 第 175-225 行

```python
class StreamContentAccumulator:
    """管理流式响应内容累积，确保所有响应包含完整累积内容"""
    
    def __init__(self):
        self.base_content = ""           # 工具调用前的内容
        self.current_content = []        # 累积的流式片段
        self.tool_status_messages = []   # 累积的工具状态消息
        self.reasoning_content = []      # 累积的推理内容
        self.is_reasoning_phase = True   # 是否处于推理阶段
        
    def add_streaming_content(self, new_content: str):
        """添加新的流式内容"""
        self.current_content.append(new_content)
        self.is_reasoning_phase = False  # 收到内容后，推理阶段结束
        
    def add_reasoning_content(self, new_reasoning: str):
        """添加新的推理内容"""
        self.reasoning_content.append(new_reasoning)
        
    def add_tool_status(self, status_message: str):
        """添加工具状态消息"""
        self.tool_status_messages.append(status_message)
        
    def get_full_content(self) -> str:
        """获取完整累积内容"""
        tool_messages = "".join(self.tool_status_messages)
        current = "".join(self.current_content)
        return self.base_content + tool_messages + current
        
    def get_full_reasoning_content(self) -> str:
        """获取完整累积的推理内容"""
        return "".join(self.reasoning_content)
```

### 3.2 累积模式配置

```python
# chat_agent.py 第 454-455 行
stream_accumulate: Optional[bool] = None  # 默认 False
```

**两种模式对比**：

| 模式 | stream_accumulate | 输出内容 | 适用场景 |
|------|-------------------|----------|----------|
| **增量模式** | False | 仅返回新增内容 | 前端打字机效果 |
| **累积模式** | True | 返回累积的完整内容 | 需要完整内容的场景 |

**配置示例**：

```python
agent = ChatAgent(
    system_message=system_message,
    model=model,
    model_config={"stream": True},
    stream_accumulate=False  # 增量模式（默认）
)
```

---

## 四、Reasoning Content 支持

### 4.1 DeepSeek Reasoner 支持

CAMEL 支持 DeepSeek-R1 等 reasoning 模型的 `reasoning_content`：

```python
# chat_agent.py 第 4471-4490 行
# Handle reasoning content streaming (for DeepSeek reasoner)
if (
    hasattr(delta, 'reasoning_content')
    and delta.reasoning_content
):
    content_accumulator.add_reasoning_content(
        delta.reasoning_content
    )
    # 返回包含 reasoning 的部分响应
    partial_response = (
        self._create_streaming_response_with_accumulator(
            content_accumulator,
            "",  # 还没有常规内容
            step_token_usage,
            getattr(chunk, 'id', ''),
            tool_call_records.copy(),
            reasoning_delta=delta.reasoning_content,  # 推理内容
        )
    )
    yield partial_response
```

### 4.2 Reasoning Content 处理流程

```
模型返回 chunk
    │
    ├── delta.reasoning_content ──→ 累积到 reasoning_content
    │                                 ↓
    │                              返回推理内容给前端
    │
    └── delta.content ────────────→ 累积到 current_content
                                      ↓
                                   返回正式内容给前端
```

### 4.3 与 smolagents 对比

| 特性 | CAMEL | smolagents |
|------|-------|-----------|
| **reasoning_content 检测** |  自动检测 |  不支持 |
| **推理内容存储** |  StreamContentAccumulator |  不支持 |
| **推理阶段追踪** |  is_reasoning_phase |  不支持 |
| **前端展示** |  可分别展示推理和正式内容 |  无此功能 |

---

## 五、工具调用流式支持

### 5.1 工具调用流式流程

```python
# chat_agent.py 第 4243-4618 行
def _stream_response(self, ...):
    """处理带工具调用的流式响应"""
    
    content_accumulator = StreamContentAccumulator()
    
    # 获取流式响应
    response = self.model_backend.run(...)
    
    for chunk in response:
        delta = chunk.choices[0].delta
        
        # 1. 处理 reasoning_content
        if hasattr(delta, 'reasoning_content'):
            ...
            
        # 2. 处理常规内容
        if delta.content:
            ...
            yield partial_response
            
        # 3. 处理工具调用
        if delta.tool_calls:
            tool_calls_complete = self._accumulate_tool_calls(
                delta.tool_calls, accumulated_tool_calls
            )
            
            if tool_calls_complete:
                # 执行工具
                tool_results = self._execute_tool_from_stream_data(...)
                
                # 重置累积器，准备下一轮
                content_accumulator.reset_streaming_content()
```

### 5.2 流式工具执行

CAMEL 支持在流式输出过程中执行工具：

```python
# chat_agent.py 第 4822-4876 行
def _execute_tool_from_stream_data(self, ...):
    """从累积的流数据执行工具"""
    
    # 创建工具状态消息
    tool_status = f"\n\nExecuting tool: {tool_name}...\n"
    content_accumulator.add_tool_status(tool_status)
    
    # 执行工具（同步或异步）
    result = self.execute_tool(tool_name, tool_args, ...)
    
    # 添加工具结果状态
    result_status = f"Tool {tool_name} completed.\n"
    content_accumulator.add_tool_status(result_status)
```

### 5.3 与 smolagents 对比

| 特性 | CAMEL | smolagents |
|------|-------|-----------|
| **工具调用流式** |  支持，可在流中执行工具 |  不支持 |
| **工具状态流式** |  流式显示工具执行状态 |  不支持 |
| **多轮工具流式** |  支持多轮工具调用 |  不支持 |
| **工具结果流式** |  工具结果实时返回 |  不支持 |

---

## 六、模型层流式支持

### 6.1 模型基类流式接口

```python
# models/base_model.py 第 536-584 行
def run(
    self,
    messages: List[OpenAIMessage],
    ...
) -> Union[
    ChatCompletion,
    Stream[ChatCompletionChunk],  # 流式返回
    ChatCompletionStreamManager[BaseModel],  # 结构化流式
]:
    """运行模型查询"""
    
async def arun(
    self,
    messages: List[OpenAIMessage],
    ...
) -> Union[
    ChatCompletion,
    AsyncStream[ChatCompletionChunk],  # 异步流式
    AsyncChatCompletionStreamManager[BaseModel],
]:
    """异步运行模型查询"""
```

### 6.2 流式日志包装

```python
# models/base_model.py 第 121-155 行
class _SyncStreamWrapper:
    """同步流式包装器，带日志记录"""
    
    def __init__(self, stream, ...):
        self._stream = stream
        
    def __iter__(self):
        for chunk in self._stream:
            # 记录日志
            self._log_chunk(chunk)
            yield chunk
            
class _AsyncStreamWrapper:
    """异步流式包装器，带日志记录"""
    
    async def __anext__(self):
        chunk = await self._stream.__anext__()
        self._log_chunk(chunk)
        return chunk
```

### 6.3 支持的模型后端

几乎所有 CAMEL 支持的模型都支持流式输出：

- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- Google (Gemini)
- DeepSeek (含 reasoning_content)
- Azure OpenAI
- AWS Bedrock
- 本地模型 (Ollama, vLLM, LM Studio)
- ... 40+ 模型平台

---

## 七、使用示例

### 7.1 基础流式输出

```python
from camel.agents import ChatAgent
from camel.models import ModelFactory

# 创建支持流式的 Agent
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
    model_config_dict={"stream": True}  # 启用流式
)

agent = ChatAgent(system_message="You are a helpful assistant.")

# 流式调用
response = agent.step("Hello, how are you?")

for partial in response:
    content = partial.msgs[0].content
    print(content, end="", flush=True)  # 实时输出
```

### 7.2 带工具调用的流式

```python
from camel.toolkits import SearchToolkit

# 创建带工具的 Agent
search_toolkit = SearchToolkit()
agent = ChatAgent(
    system_message="You are a helpful assistant with search capability.",
    tools=search_toolkit.get_tools(),
    model_config={"stream": True}
)

# 流式调用，工具执行状态也会流式返回
response = agent.step("Search for the latest AI news.")

for partial in response:
    print(partial.msgs[0].content, end="", flush=True)
    # 输出示例：
    # I'll search for the latest AI news for you.
    # 
    # Executing tool: google_search...
    # Tool google_search completed.
    # 
    # Here are the latest AI news: ...
```

### 7.3 DeepSeek Reasoning 流式

```python
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType

# 使用 DeepSeek-R1
model = ModelFactory.create(
    model_platform=ModelPlatformType.DEEPSEEK,
    model_type=ModelType.DEEPSEEK_REASONER,  # R1 模型
    model_config_dict={"stream": True}
)

agent = ChatAgent(system_message="You are a helpful assistant.")

response = agent.step("Solve this math problem: 23 * 47")

for partial in response:
    msg = partial.msgs[0]
    
    # 访问 reasoning_content
    if hasattr(msg, 'reasoning_content') and msg.reasoning_content:
        print(f"[思考] {msg.reasoning_content}")
    
    # 访问正式内容
    if msg.content:
        print(f"[回答] {msg.content}")
```

---

## 八、与 smolagents 详细对比

### 8.1 流式机制对比

| 维度 | CAMEL | smolagents |
|------|-------|-----------|
| **流式架构** | 包装器模式 | Python Generator |
| **异步支持** |  原生支持 |  不支持 |
| **流式类型** | 同步 + 异步 | 仅同步 |
| **内容累积** |  可配置 |  不支持 |
| **工具流式** |  支持 |  不支持 |
| **reasoning** |  支持 |  不支持 |

### 8.2 代码实现对比

**CAMEL 流式调用**：
```python
# 灵活的配置方式
response = agent.step(message)
for partial in response:
    print(partial.msgs[0].content)
```

**smolagents 流式调用**：
```python
# 简单的 Generator
for step in agent.run_stream(task):
    if isinstance(step, ActionStep):
        print(step.model_output)
```

### 8.3 适用场景

| 场景 | 推荐框架 | 理由 |
|------|---------|------|
| 生产级流式应用 | **CAMEL** | 异步支持、工具流式、更完善 |
| 快速原型开发 | smolagents | 简单、轻量 |
| 需要 reasoning_content | **CAMEL** | 原生支持 |
| 复杂多工具场景 | **CAMEL** | 工具流式状态展示 |

---

## 九、总结

### CAMEL 流式输出优势

1. **完善的异步支持**：原生支持异步流式，适合高并发场景
2. **工具调用流式**：工具执行状态可以流式返回给用户
3. **reasoning_content 支持**：支持 DeepSeek-R1 等 reasoning 模型
4. **内容累积器**：灵活的累积模式配置
5. **统一的包装器设计**：StreamingChatAgentResponse 兼容非流式代码
6. **40+ 模型平台支持**：几乎所有模型都支持流式

### 对 AIASys 的启示

1. **考虑异步流式**：如果 AIASys 需要高并发支持，可以参考 CAMEL 的异步设计
2. **工具执行状态流式**：在 Worker Agent 执行长时间任务时，可以流式返回执行状态
3. **reasoning_content 展示**：如果使用 DeepSeek-R1，可以参考 CAMEL 的推理内容展示方式
4. **内容累积模式**：根据前端需求选择增量模式或累积模式

---

**相关文档**：
- [[02-camel-Agent系统深度分析]]
- [[50-smolagents-CodeAgent与ToolCallingAgent流式输出对比分析]]
- [[49-smolagents-多Agent流式输出与前端展示设计]]
