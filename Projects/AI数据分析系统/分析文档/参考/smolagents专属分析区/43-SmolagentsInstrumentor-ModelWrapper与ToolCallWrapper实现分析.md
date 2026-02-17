# SmolagentsInstrumentor - ModelWrapper与ToolCallWrapper实现分析

---

## 系列定位

本文是 SmolagentsInstrumentor 源码实现深度分析系列的第五篇。

前四篇覆盖内容：
- 第一篇：整体架构与初始化流程
- 第二篇：RunWrapper 实现分析
- 第三篇：StepWrapper 实现分析
- 第四篇：内部辅助函数详解

本文聚焦最后两个核心 Wrapper：
- `_ModelWrapper`：LLM 调用的观测封装
- `_ToolCallWrapper`：工具执行的观测封装

---

## 一、_ModelWrapper 详解

### 1.1 核心职责

`_ModelWrapper` 负责拦截所有 LLM 模型的 `generate` 方法调用，创建符合 OpenInference 语义规范的 LLM Span，记录完整的调用上下文、输入输出消息和 Token 使用量。

### 1.2 LLM Span 的创建

```python
span_name = f"{instance.__class__.__name__}.generate"

attributes = {
    OPENINFERENCE_SPAN_KIND: LLM,
    **_input_value_and_mime_type(arguments),
    **_llm_invocation_parameters(instance, arguments),
    **_llm_input_messages(arguments),
    **dict(get_attributes_from_context()),
}
```

**为什么使用类名而非模型名**

代码使用 `instance.__class__.__name__` 而非 `model_id` 作为 Span 名称的一部分，原因如下：

| 考量维度 | 类名优势 | 模型名劣势 |
|---------|---------|-----------|
| 稳定性 | 类名在运行时确定，不会为 None | 某些模型实例可能未设置 model_id |
| 可读性 | 明确标识代码路径 | 长模型名导致 Span 名称冗长 |
| 一致性 | 同类模型的 Span 命名统一 | 不同实例的 model_id 可能不同 |
| 调试友好 | 快速定位到具体模型类 | 需要额外查找类映射 |

模型名通过 `LLM_MODEL_NAME` 属性单独记录，不影响观测数据的完整性。

**属性收集的完整性**

Span 创建时收集五类属性：

1. **Span 类型标记**：`OPENINFERENCE_SPAN_KIND: LLM`
2. **原始输入**：`_input_value_and_mime_type` 序列化所有参数
3. **调用参数**：`_llm_invocation_parameters` 提取 generation config
4. **输入消息**：`_llm_input_messages` 解析对话历史
5. **上下文属性**：`get_attributes_from_context` 注入用户自定义标签

### 1.3 输入消息解析

```python
def _llm_input_messages(arguments):
    def process_message(idx: int, role: str, content: str):
        yield f"{LLM_INPUT_MESSAGES}.{idx}.{MESSAGE_ROLE}", role
        yield f"{LLM_INPUT_MESSAGES}.{idx}.{MESSAGE_CONTENT}", content

    if isinstance(prompt := arguments.get("prompt"), str):
        # 单轮 prompt 模式
        yield from process_message(0, "user", prompt)
    elif isinstance(messages := arguments.get("messages"), list):
        # 多轮 messages 模式
        for i, message in enumerate(messages):
            if not isinstance(message, dict):
                continue
            role, content = message.get("role"), message.get("content")
            if isinstance(content, list) and role:
                # 多模态内容：content 是列表
                for subcontent in content:
                    if isinstance(subcontent, dict) and (text := subcontent.get("text")):
                        yield from process_message(i, role, text)
```

**支持两种输入格式的必要性**

smolagents 框架支持两类 LLM 调用方式：

| 调用方式 | 参数格式 | 典型场景 |
|---------|---------|---------|
| 简单调用 | `prompt: str` | 单轮对话、代码生成 |
| 标准调用 | `messages: list[dict]` | 多轮对话、Agent 上下文维护 |

不同模型类的 `generate` 方法实现不同：
- `OpenAIServerModel` 使用 `messages` 列表
- 部分轻量模型使用简单 `prompt` 字符串

Wrapper 必须兼容两者才能全面覆盖。

**多模态内容处理**

当 `content` 为列表时，表示多模态输入：

```python
content = [
    {"type": "text", "text": "描述这张图片"},
    {"type": "image_url", "image_url": {"url": "..."}}
]
```

代码只提取 `type: text` 的内容，过滤掉图像等非文本数据。这是合理的取舍：
- 观测系统主要关注文本交互逻辑
- 图像数据体积大，不适合存入 Span 属性
- 图像 URL 或描述已足够用于调试

### 1.4 输出消息解析

```python
def _llm_output_messages(output_message):
    oi_message: oi.Message = {}
    oi_message_contents: list[oi.MessageContent] = []
    
    # 基础字段提取
    if (role := getattr(output_message, "role", None)) is not None:
        oi_message["role"] = role
    if (content := getattr(output_message, "content", None)) is not None:
        oi_message_contents.append(oi.TextMessageContent(type="text", text=content))

    # 深度提取：reasoning_content
    if (raw := getattr(output_message, "raw", None)) is not None:
        if (choices := getattr(raw, "choices", None)) is not None:
            if isinstance(choices, list) and len(choices) > 0:
                if (message := getattr(choices[0], "message", None)) is not None:
                    if (reasoning_content := getattr(message, "reasoning_content", None)) is not None:
                        oi_message_contents.append(
                            oi.TextMessageContent(type="text", text=reasoning_content)
                        )

    # tool_calls 提取
    oi_tool_calls: list[oi.ToolCall] = []
    if isinstance(tool_calls := getattr(output_message, "tool_calls", None), list):
        for tool_call in tool_calls:
            oi_tool_call: oi.ToolCall = {}
            if (tool_call_id := getattr(tool_call, "id", None)) is not None:
                oi_tool_call["id"] = tool_call_id
            if (function := getattr(tool_call, "function", None)) is not None:
                oi_function: oi.ToolCallFunction = {}
                if (name := getattr(function, "name", None)) is not None:
                    oi_function["name"] = name
                if isinstance(arguments := getattr(function, "arguments", None), str):
                    oi_function["arguments"] = arguments
                oi_tool_call["function"] = oi_function
                oi_tool_calls.append(oi_tool_call)
    
    oi_message["tool_calls"] = oi_tool_calls
    return oi.get_llm_output_message_attributes(messages=[oi_message])
```

**Tool Calls 处理**

当模型输出工具调用时，结构如下：

```python
tool_calls = [
    {
        "id": "call_abc123",
        "function": {
            "name": "search",
            "arguments": '{"query": "Python"}'
        }
    }
]
```

代码提取三个关键字段：
- `id`：调用标识，用于匹配后续工具执行结果
- `name`：工具名称，决定调用哪个工具
- `arguments`：参数 JSON 字符串，需解析后传给工具

**Reasoning Content 提取**

DeepSeek R1 等推理模型会在 `raw.choices[0].message.reasoning_content` 中返回思维链内容。代码通过四层嵌套 getattr 安全提取：

```
output_message.raw.choices[0].message.reasoning_content
```

每层都做空值检查，避免 AttributeError。

**为什么需要处理 raw.choices**

不同模型库的输出结构差异大：
- OpenAI 格式：`choices[0].message.content`
- 部分模型将原始响应放在 `raw` 字段
- `choices` 是列表，需取索引 0

处理 `raw.choices` 是为了兼容更多模型提供商的非标准响应格式。

### 1.5 Token 使用量获取的多重策略

```python
token_usage = getattr(output_message, "token_usage", None)
if token_usage:
    # 策略一：从响应对象的 token_usage 字段
    input_tokens = token_usage.input_tokens
    output_tokens = token_usage.output_tokens
    total_tokens = token_usage.total_tokens
else:
    # 策略二：从模型实例的最后统计
    input_tokens = model.last_input_token_count
    output_tokens = model.last_output_token_count
    total_tokens = input_tokens + output_tokens
```

**为什么需要多重策略**

不同模型类的 Token 统计方式不同：

| 模型类 | Token 来源 | 特点 |
|-------|-----------|------|
| OpenAI API | 响应中的 usage 字段 | 精确，包含 prompt/completion/total |
| 本地模型 | 模型实例自行统计 | 近似值，last_*_token_count 属性 |
| 流式输出 | 需累加 | 单次 generate 调用可能无法获取 |

**回退策略的可靠性**

`last_input_token_count` 和 `last_output_token_count` 是 smolagents 模型基类维护的计数器：
- 每次 `generate` 调用后更新
- 单线程场景准确
- 多线程并发时可能混淆

代码优先使用响应对象中的精确值，只有在缺失时才回退到实例属性。这种设计在绝大多数场景下都能获取到合理的 Token 使用量。

### 1.6 LLM Provider 智能识别

Provider 识别采用双重策略：先尝试从类名推断，失败后回退到 Endpoint 分析。

**从类名识别**

```python
def infer_llm_provider_from_class_name(instance):
    class_name = instance.__class__.__name__
    
    # LiteLLM 特殊处理：从 model_id 解析 provider 前缀
    if class_name in ["LiteLLMModel", "LiteLLMRouterModel"]:
        model_id = getattr(instance, "model_id", None)
        if isinstance(model_id, str):
            provider_prefix = model_id.split("/", 1)[0].lower()
            return OpenInferenceLLMProviderValues(provider_prefix)
    
    # InferenceClientModel 无法推断
    if class_name == "InferenceClientModel":
        return None
    
    # 直接映射
    if class_name == "OpenAIServerModel":
        return OpenInferenceLLMProviderValues.OPENAI
    if class_name == "AzureOpenAIServerModel":
        return OpenInferenceLLMProviderValues.AZURE
    if class_name == "AmazonBedrockServerModel":
        return OpenInferenceLLMProviderValues.AWS
    
    return None
```

**从 Endpoint 识别**

```python
def infer_llm_provider_from_endpoint(instance):
    # 收集可能的 endpoint 属性名
    endpoint = (
        getattr(instance, "api_base", None)
        or getattr(instance, "base_url", None)
        or getattr(instance, "endpoint", None)
        or getattr(instance, "host", None)
    )
    
    host = urlparse(endpoint).hostname.lower()
    
    # 域名匹配规则
    if host.endswith("api.openai.com"):
        return OpenInferenceLLMProviderValues.OPENAI
    if "openai.azure.com" in host:
        return OpenInferenceLLMProviderValues.AZURE
    if host.endswith("googleapis.com"):
        return OpenInferenceLLMProviderValues.GOOGLE
    if host.endswith("anthropic.com"):
        return OpenInferenceLLMProviderValues.ANTHROPIC
    if "bedrock" in host or host.endswith("amazonaws.com"):
        return OpenInferenceLLMProviderValues.AWS
    if host.endswith("cohere.ai"):
        return OpenInferenceLLMProviderValues.COHERE
    if host.endswith("mistral.ai"):
        return OpenInferenceLLMProviderValues.MISTRALAI
    if host.endswith("x.ai"):
        return OpenInferenceLLMProviderValues.XAI
    if host.endswith("deepseek.com"):
        return OpenInferenceLLMProviderValues.DEEPSEEK
    
    return None
```

**为什么需要双重识别**

| 识别方式 | 适用场景 | 局限 |
|---------|---------|------|
| 类名 | 标准模型类 | 无法识别自定义子类 |
| Endpoint | 通用 HTTP 客户端 | 需要正确的 endpoint 配置 |

类名识别优先，因为：
- 准确度高，直接对应代码实现
- 不依赖网络配置
- 处理速度快

Endpoint 识别作为回退，覆盖：
- 使用通用客户端的场景
- 自定义模型子类
- 代理或转发 endpoint 场景

**支持的 Provider 列表**

OpenInference 规范支持的 Provider 值：
- OPENAI
- AZURE
- AWS
- ANTHROPIC
- GOOGLE
- COHERE
- MISTRALAI
- XAI
- DEEPSEEK

**识别失败的处理**

当两种方法都失败时，Provider 属性不会被设置。这是可接受的：
- Span 仍然有效，只是缺少 Provider 标签
- 用户可以通过上下文手动注入 Provider 信息
- 观测平台通常能根据 model_id 再次推断

### 1.7 防止 LLM Span 重复创建

```python
def _has_active_llm_parent_span() -> bool:
    current_span = trace_api.get_current_span()
    return (
        current_span.get_span_context().is_valid
        and current_span.is_recording()
        and isinstance(current_span, ReadableSpan)
        and (current_span.attributes or {}).get(OPENINFERENCE_SPAN_KIND) == LLM
    )

# 在 __call__ 中检查
if _has_active_llm_parent_span():
    return wrapped(*args, **kwargs)  # 直接执行，不再创建 Span
```

**什么场景会触发重复**

某些模型实现可能在内部递归调用 `generate`：
- 重试机制：失败时自动重试
- 多阶段生成：先规划后执行
- 工具调用循环：Agent 内部处理工具结果后再次调用模型

**为什么需要防止重复**

重复创建 LLM Span 会导致：
- 观测数据膨胀，一次调用产生多个 Span
- Token 使用量重复统计
- 调用链结构混乱，难以追踪真实调用关系

**判断条件的完整性**

函数检查四个条件：

1. `is_valid`：SpanContext 有效，不是无效的占位符
2. `is_recording`：Span 正在记录，尚未结束
3. `isinstance(current_span, ReadableSpan)`：确保可以读取属性
4. `attributes.get(OPENINFERENCE_SPAN_KIND) == LLM`：确认当前就是 LLM Span

第四个条件是关键：只有当父 Span 也是 LLM 类型时才跳过。这允许 Agent Span 或 Chain Span 下正常创建 LLM Span，只阻止 LLM Span 嵌套 LLM Span。

---

## 二、_ToolCallWrapper 详解

### 2.1 核心职责

`_ToolCallWrapper` 负责拦截所有工具的 `__call__` 方法，创建 TOOL 类型的 Span，记录工具名称、参数和输出结果。

### 2.2 Tool Span 创建

```python
span_name = f"{instance.__class__.__name__}"

attributes = {
    OPENINFERENCE_SPAN_KIND: TOOL,
    INPUT_VALUE: _get_input_value(wrapped, *args, **kwargs),
    **_tools(instance),
    **dict(get_attributes_from_context()),
}
```

**为什么使用类名作为 Span 名**

工具 Span 的命名直接使用工具类名：
- 工具实例通常有 `name` 属性，但类名更稳定
- 类名直接对应代码定义，便于定位
- smolagents 工具通常一个类对应一个功能

**与其他 Wrapper 的命名差异**

| Wrapper | Span 命名方式 | 示例 |
|---------|--------------|------|
| RunWrapper | `agent.name + ".run"` | `MyAgent.run` |
| StepWrapper | `"Step " + step_number` | `Step 3` |
| ModelWrapper | `class_name + ".generate"` | `OpenAIServerModel.generate` |
| ToolCallWrapper | `class_name` | `DuckDuckGoSearchTool` |

### 2.3 工具信息提取

```python
def _tools(tool):
    if tool_name := getattr(tool, "name", None):
        yield TOOL_NAME, tool_name
    if tool_description := getattr(tool, "description", None):
        yield TOOL_DESCRIPTION, tool_description
    yield TOOL_PARAMETERS, safe_json_dumps(tool.inputs)
```

**提取的信息用途**

| 属性 | 来源 | 用途 |
|-----|------|------|
| TOOL_NAME | `tool.name` | 标识具体工具，关联调用记录 |
| TOOL_DESCRIPTION | `tool.description` | 理解工具功能，调试时参考 |
| TOOL_PARAMETERS | `tool.inputs` | 记录输入参数结构，分析参数变化 |

**序列化的必要性**

`tool.inputs` 是字典类型，包含参数名到类型的映射：

```python
{
    "query": {
        "type": "string",
        "description": "搜索关键词"
    }
}
```

OpenTelemetry Span 属性只接受基本类型，必须序列化为 JSON 字符串。

### 2.4 输出类型处理

```python
def _output_value_and_mime_type_for_tool_span(response, output_type):
    if output_type in (
        "string",
        "boolean", 
        "integer",
        "number",
    ) or isinstance(response, str):
        yield OUTPUT_VALUE, response
        yield OUTPUT_MIME_TYPE, TEXT
    else:
        yield OUTPUT_VALUE, safe_json_dumps(response)
        yield OUTPUT_MIME_TYPE, JSON
```

**为什么根据 output_type 区分**

工具输出类型决定了如何存储和展示：

| output_type | 存储方式 | MIME 类型 | 适用场景 |
|------------|---------|----------|---------|
| string | 原样存储 | text/plain | 文本结果、错误信息 |
| boolean | 原样存储 | text/plain | 状态检查 |
| integer/number | 原样存储 | text/plain | 计数、评分 |
| object/array | JSON 序列化 | application/json | 结构化数据 |

**TEXT vs JSON 的选择标准**

选择 TEXT 的条件：
- output_type 明确声明为简单类型
- 返回值本身就是字符串

选择 JSON 的条件：
- output_type 为 object 或 array
- 返回值是复杂结构

这种区分让观测平台能正确渲染输出：TEXT 直接显示，JSON 格式化展示。

---

## 三、工具 Schema 生成

```python
def _llm_tools(tools_to_call_from):
    from smolagents import Tool
    from smolagents.models import get_tool_json_schema

    if not isinstance(tools_to_call_from, list):
        return
    for tool_index, tool in enumerate(tools_to_call_from):
        if isinstance(tool, Tool):
            yield (
                f"{LLM_TOOLS}.{tool_index}.{TOOL_JSON_SCHEMA}",
                safe_json_dumps(get_tool_json_schema(tool)),
            )
```

**为什么需要工具 Schema**

LLM 模型需要知道有哪些工具可用，每个工具的参数结构如何。这个信息通过 `tools` 参数传给模型，格式遵循 OpenAI 的 Function Calling 规范。

**get_tool_json_schema 的作用**

这是 smolagents 提供的工具函数，将 Tool 对象转换为 JSON Schema：

```python
{
    "type": "function",
    "function": {
        "name": "search",
        "description": "搜索网络信息",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                }
            },
            "required": ["query"]
        }
    }
}
```

**序列化后的用途**

Schema 序列化后存入 Span 属性，用于：
- 调试：查看模型实际看到的工具定义
- 审计：验证工具定义是否符合预期
- 回放：复现调用场景时知道可用工具

---

## 四、LLM System 识别

```python
def infer_llm_system_from_model(model_name):
    if not model_name:
        return None

    model = model_name.lower()

    if model.startswith((
        "gpt-", "gpt.", "o1", "o3", "o4",
        "text-embedding",
        "davinci", "curie", "babbage", "ada",
        "azure_openai", "azure_ai", "azure"
    )):
        return OpenInferenceLLMSystemValues.OPENAI

    if model.startswith((
        "anthropic.claude", "anthropic/", "claude-"
    )):
        return OpenInferenceLLMSystemValues.ANTHROPIC

    if model.startswith(("cohere.command", "command", "cohere")):
        return OpenInferenceLLMSystemValues.COHERE

    if model.startswith(("mistralai", "mixtral", "mistral", "pixtral")):
        return OpenInferenceLLMSystemValues.MISTRALAI

    if model.startswith((
        "google_vertexai", "google_genai", "vertexai",
        "vertex_ai", "vertex", "gemini", "google"
    )):
        return OpenInferenceLLMSystemValues.VERTEXAI

    return None
```

**Provider vs System 的区别**

| 维度 | Provider | System |
|-----|----------|--------|
| 含义 | 服务提供商 | 底层模型系统/家族 |
| 示例 | AWS、Azure、OpenAI | GPT、Claude、Gemini |
| 粒度 | 粗，公司级别 | 细，模型系列级别 |
| 用途 | 成本归属、供应商分析 | 模型能力分析、版本对比 |

**为什么需要识别 System**

同一 Provider 可能托管多个 System：
- Azure 上可以同时部署 GPT-4 和 Claude
- AWS Bedrock 支持多种模型家族

区分 System 让分析更精确：
- 比较 GPT-4 vs Claude 3.5 的性能差异
- 追踪不同模型版本的使用趋势
- 优化模型选型决策

---

## 五、流程图

### 5.1 ModelWrapper 执行流程

![[smolagents-instrumentor-ModelWrapper流程图.svg]]

### 5.2 Provider 识别决策树

![[smolagents-instrumentor-Provider识别决策树.svg]]

---

## 六、对比总结

### 6.1 四个 Wrapper 对比

| Wrapper | Span Kind | 核心数据 | 特殊处理 |
|---------|-----------|----------|----------|
| RunWrapper | AGENT | task、tools、managed_agents | 流式处理、Token 汇总 |
| StepWrapper | CHAIN | observations | 错误分类、状态标记 |
| ModelWrapper | LLM | messages、token_usage、provider | Provider 识别、防重复 |
| ToolCallWrapper | TOOL | name、parameters、output | output_type 区分 |

### 6.2 数据流向图

```
┌─────────────────────────────────────────────────────────────┐
│                        Agent Run                            │
│                    Span Kind: AGENT                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │  Step 1  │    │  Step 2  │    │  Step N  │
    │  CHAIN   │    │  CHAIN   │    │  CHAIN   │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
         ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ LLM Call │    │ LLM Call │    │ LLM Call │
    │   LLM    │    │   LLM    │    │   LLM    │
    └────┬─────┘    └────┬─────┘    └────┬─────┘
         │               │               │
    ┌────┴────┐     ┌────┴────┐     ┌────┴────┐
    ▼         ▼     ▼         ▼     ▼         ▼
┌──────┐  ┌──────┐ ┌──────┐  ┌──────┐ ┌──────┐  ┌──────┐
│ Tool │  │ Tool │ │ Tool │  │ Tool │ │ Tool │  │ Tool │
│ TOOL │  │ TOOL │ │ TOOL │  │ TOOL │ │ TOOL │  │ TOOL │
└──────┘  └──────┘ └──────┘  └──────┘ └──────┘  └──────┘
```

### 6.3 关键设计决策

| 设计点 | 决策 | 理由 |
|-------|------|------|
| Span 命名 | 使用类名 | 稳定、可读、一致 |
| Token 获取 | 双重策略 | 兼容不同模型实现 |
| Provider 识别 | 类名 + Endpoint | 提高识别成功率 |
| 防重复机制 | 检查父 Span 类型 | 只阻止 LLM 嵌套 |
| 输出格式 | 按 output_type 区分 | 优化展示效果 |

---

## 七、关联文档

- [[40-SmolagentsInstrumentor-整体架构与初始化流程]]
- [[41-SmolagentsInstrumentor-RunWrapper与StepWrapper实现分析]]
- [[42-SmolagentsInstrumentor-内部辅助函数详解]]
- [[44-SmolagentsInstrumentor-实战案例与性能优化]]

---

## 标签

主题：OpenTelemetry、smolagents、LLM 观测、代码分析
系列：SmolagentsInstrumentor 源码深度分析
