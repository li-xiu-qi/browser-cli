# smolagents MCP与扩展机制分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/mcp_client.py, src/smolagents/tools.py, src/smolagents/agents.py, src/smolagents/models.py

---

## 一、MCP简介

### 1.1 什么是Model Context Protocol

Model Context Protocol，简称MCP，是Anthropic于2024年11月推出的开放协议标准。它定义了一套标准化的通信规范，用于连接大型语言模型应用与外部数据源、工具和服务。

MCP的核心设计目标：
- 让LLM应用能够无缝集成外部数据源
- 为AI系统暴露工具和能力提供统一接口
- 支持构建可组合的集成方案和工作流
- 实现主机、客户端、服务器之间的安全双向连接

### 1.2 为什么需要MCP

在MCP出现之前，每个AI框架都有自己的工具集成方式：
- OpenAI的Function Calling
- LangChain的Tool接口
- smolagents的Tool基类
- 各种自定义RPC方案

这种碎片化带来几个问题：
- 工具开发者需要为每个框架单独适配
- 用户被锁定在特定生态中
- 重复造轮子，资源浪费

MCP通过标准化协议解决这些问题：一次开发，到处运行。

### 1.3 MCP与Function Calling的关系

MCP和Function Calling不是竞争关系，而是互补关系：

| 层面 | Function Calling | MCP |
|------|------------------|-----|
| 层级 | 应用层API调用方式 | 传输层协议标准 |
| 范围 | 单次请求-响应 | 持久连接会话 |
| 能力 | 调用预定义函数 | 动态发现工具、资源、提示词 |
| 传输 | HTTP API | stdio、sse、streamable-http |

Function Calling是模型输出结构化调用的格式，MCP是承载这些调用的传输协议。

### 1.4 MCP协议核心组件

根据MCP规范，协议包含以下核心要素：

**基础协议**
- JSON-RPC消息格式
- 有状态连接
- 服务端与客户端能力协商

**核心功能**
- Resources: 上下文和数据资源
- Prompts: 模板化的消息和工作流
- Tools: AI模型可调用的函数
- Sampling: 服务端发起的LLM交互

**传输方式**
- stdio: 标准输入输出，适用于本地进程
- sse: 服务端推送事件，HTTP兼容
- streamable-http: 流式HTTP传输

---

## 二、MCPClient实现

### 2.1 整体架构

smolagents的MCPClient是对底层mcpadapt库的封装，核心依赖关系：

```
smolagents.MCPClient
    └── mcpadapt.core.MCPAdapt
            └── mcpadapt.smolagents_adapter.SmolAgentsAdapter
                    └── smolagents.Tool
```

### 2.2 MCPClient类结构

源码位置: src/smolagents/mcp_client.py

```python
class MCPClient:
    """Manages the connection to an MCP server and make its tools available to SmolAgents."""
    
    def __init__(
        self,
        server_parameters: "StdioServerParameters" | dict[str, Any] | list[...],
        adapter_kwargs: dict[str, Any] | None = None,
        structured_output: bool | None = None,
    ):
        # 初始化适配器
        self._adapter = MCPAdapt(
            server_parameters, 
            SmolAgentsAdapter(structured_output=structured_output), 
            **adapter_kwargs
        )
        self._tools: list[Tool] | None = None
        self.connect()
```

关键属性说明：
- `server_parameters`: 服务器连接参数，支持stdio配置或HTTP URL
- `adapter_kwargs`: 传递给MCPAdapt的额外参数
- `structured_output`: 是否启用结构化输出支持
- `_adapter`: 底层MCP适配器实例
- `_tools`: 从MCP服务器获取的工具列表

### 2.3 传输协议支持

MCPClient支持两种传输方式：

**stdio传输**
适用于本地命令行工具或脚本：

```python
from mcp import StdioServerParameters

server_parameters = StdioServerParameters(
    command="uvx",
    args=["--quiet", "pubmedmcp@0.1.3"],
    env={"UV_PYTHON": "3.12", **os.environ},
)

mcp_client = MCPClient(server_parameters)
```

**HTTP传输**
适用于远程MCP服务器：

```python
# Streamable HTTP，默认且推荐
server_parameters = {
    "url": "http://localhost:8000/mcp",
    "transport": "streamable-http"
}

# 或传统SSE传输
server_parameters = {
    "url": "http://localhost:8000/mcp",
    "transport": "sse"  # 已弃用
}

mcp_client = MCPClient(server_parameters)
```

### 2.4 连接生命周期管理

MCPClient提供两种连接管理模式：

**上下文管理器模式**
```python
with MCPClient(server_parameters) as tools:
    # 工具可用，退出时自动断开
    agent = CodeAgent(tools=tools, model=model)
```

**手动管理模式**
```python
try:
    mcp_client = MCPClient(server_parameters)
    tools = mcp_client.get_tools()
    # 使用工具
finally:
    mcp_client.disconnect()  # 必须手动关闭
```

### 2.5 获取工具

```python
def get_tools(self) -> list[Tool]:
    """获取MCP服务器提供的工具列表"""
    if self._tools is None:
        raise ValueError("MCP服务器未连接，先调用connect()")
    return self._tools
```

工具列表在连接时初始化，当前版本只获取会话创建时的工具，未来版本将支持动态更新。

---

## 三、Tool集成

### 3.1 MCP工具到smolagents Tool的转换

转换过程由`mcpadapt.smolagents_adapter.SmolAgentsAdapter`处理，核心逻辑：

1. MCP服务器暴露工具元数据：名称、描述、输入schema
2. Adapter将MCP schema转换为smolagents Tool的inputs格式
3. 生成包装类，将MCP调用转发到服务器

### 3.2 Schema转换映射

MCP工具定义使用JSON Schema，smolagents使用简化格式：

**MCP输入Schema示例**
```json
{
    "name": "search_papers",
    "description": "Search academic papers",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query"
            },
            "limit": {
                "type": "integer",
                "description": "Max results"
            }
        },
        "required": ["query"]
    }
}
```

**转换为smolagents格式**
```python
{
    "query": {
        "type": "string",
        "description": "Search query"
    },
    "limit": {
        "type": "integer",
        "description": "Max results",
        "nullable": True  # 非required字段标记为nullable
    }
}
```

### 3.3 名称处理

MCP工具名称可能包含连字符等非法字符，转换时会进行清理：
- 替换非法字符为下划线
- 确保符合Python标识符规范
- 避免与Python关键字冲突

### 3.4 ToolCollection.from_mcp

除了直接使用MCPClient，smolagents还提供更简洁的ToolCollection接口：

```python
from smolagents import ToolCollection

with ToolCollection.from_mcp(
    server_parameters, 
    trust_remote_code=True,
    structured_output=True
) as tool_collection:
    agent = CodeAgent(
        tools=[*tool_collection.tools], 
        add_base_tools=True, 
        model=model
    )
    agent.run("Find remedy for hangover")
```

ToolCollection.from_mcp是上下文管理器，自动处理连接生命周期。

### 3.5 结构化输出支持

MCPClient支持结构化输出，启用后可以：
- 处理outputSchema定义的输出格式
- 解析structuredContent字段
- 使用JSON解析作为fallback

启用方式：
```python
mcp_client = MCPClient(
    server_parameters,
    structured_output=True  # 1.25版本后将默认为True
)
```

---

## 四、使用示例

### 4.1 基础使用流程

```python
import os
from smolagents import MCPClient, CodeAgent, InferenceClientModel
from mcp import StdioServerParameters

# 1. 配置模型
model = InferenceClientModel()

# 2. 配置MCP服务器参数
server_parameters = StdioServerParameters(
    command="uvx",
    args=["--quiet", "pubmedmcp@0.1.3"],
    env={"UV_PYTHON": "3.12", **os.environ},
)

# 3. 使用上下文管理器连接MCP服务器
with MCPClient(server_parameters) as mcp_tools:
    # 4. 创建Agent，传入MCP工具
    agent = CodeAgent(
        tools=mcp_tools, 
        add_base_tools=True, 
        model=model
    )
    
    # 5. 运行任务
    result = agent.run("搜索关于偏头痛治疗的最新研究")
    print(result)
```

### 4.2 连接远程HTTP服务器

```python
from smolagents import MCPClient, CodeAgent

# HTTP传输配置
http_config = {
    "url": "http://127.0.0.1:8000/mcp",
    "transport": "streamable-http"
}

with MCPClient(http_config) as tools:
    agent = CodeAgent(tools=tools, model=model)
    agent.run("执行任务")
```

### 4.3 多MCP服务器连接

```python
# 同时连接多个MCP服务器
server_params_list = [
    StdioServerParameters(command="server1.py", args=[], env=os.environ),
    StdioServerParameters(command="server2.py", args=[], env=os.environ),
]

with MCPClient(server_params_list) as all_tools:
    # all_tools包含所有服务器的工具
    agent = CodeAgent(tools=all_tools, model=model)
```

### 4.4 使用ToolCollection简化代码

```python
from smolagents import ToolCollection, CodeAgent

with ToolCollection.from_mcp(
    {"url": "http://localhost:8000/mcp", "transport": "streamable-http"},
    trust_remote_code=True
) as collection:
    agent = CodeAgent(tools=[*collection.tools], model=model)
    agent.run("任务描述")
```

---

## 五、扩展机制

### 5.1 自定义Tool

#### 5.1.1 继承Tool基类

```python
from smolagents import Tool

class MyCustomTool(Tool):
    name = "my_tool"
    description = "This is my custom tool"
    inputs = {
        "param1": {
            "type": "string",
            "description": "First parameter"
        },
        "param2": {
            "type": "integer",
            "description": "Second parameter",
            "nullable": True
        }
    }
    output_type = "string"
    
    def forward(self, param1: str, param2: int = None) -> str:
        # 实现工具逻辑
        return f"Result: {param1}, {param2}"
```

#### 5.1.2 使用@tool装饰器

```python
from smolagents import tool

@tool
def my_simple_tool(query: str, limit: int = 10) -> str:
    """
    Search for information.
    
    Args:
        query: Search query string
        limit: Maximum number of results
    
    Returns:
        Search results as string
    """
    return f"Results for {query}"
```

#### 5.1.3 Tool验证机制

Tool类初始化时自动验证：
- name必须是有效Python标识符
- 必须定义description、inputs、output_type
- forward方法签名必须与inputs匹配
- 输入类型必须是AUTHORIZED_TYPES之一

AUTHORIZED_TYPES定义：
```python
AUTHORIZED_TYPES = [
    "string", "boolean", "integer", "number",
    "image", "audio", "array", "object", "any", "null"
]
```

### 5.2 自定义Agent

#### 5.2.1 Agent类层次

```
MultiStepAgent (抽象基类)
    ├── CodeAgent      # 代码执行型Agent
    └── ToolCallingAgent  # 工具调用型Agent
```

#### 5.2.2 继承MultiStepAgent

```python
from smolagents import MultiStepAgent

class CustomAgent(MultiStepAgent):
    def initialize_system_prompt(self) -> str:
        # 自定义系统提示词
        return "You are a specialized agent..."
    
    def _step_stream(self, memory_step):
        # 自定义执行步骤
        pass
```

#### 5.2.3 Agent配置选项

```python
agent = CodeAgent(
    tools=[my_tool],
    model=model,
    max_steps=20,           # 最大步数
    add_base_tools=True,    # 添加基础工具
    planning_interval=5,    # 规划间隔
    prompt_templates={...}, # 自定义提示词模板
    final_answer_checks=[...], # 最终答案验证函数
)
```

### 5.3 集成新模型

#### 5.3.1 Model基类

```python
from smolagents import Model, ChatMessage

class MyCustomModel(Model):
    def __init__(self, model_id: str, **kwargs):
        super().__init__(model_id=model_id, **kwargs)
        # 初始化模型
        self.model = load_model(model_id)
    
    def generate(
        self,
        messages: list[ChatMessage],
        stop_sequences: list[str] | None = None,
        response_format: dict | None = None,
        tools_to_call_from: list | None = None,
        **kwargs
    ) -> ChatMessage:
        # 实现生成逻辑
        response = self.model.generate(messages)
        return ChatMessage(role="assistant", content=response)
```

#### 5.3.2 模型注册

smolagents使用MODEL_REGISTRY管理内置模型：

```python
MODEL_REGISTRY = {
    "openai": OpenAIServerModel,
    "azure": AzureOpenAIServerModel,
    "anthropic": AnthropicModel,
    # ...
}
```

#### 5.3.3 流式输出支持

```python
def generate_stream(self, messages, **kwargs):
    """实现流式生成"""
    for chunk in self.model.stream_generate(messages):
        yield ChatMessageStreamDelta(
            content=chunk.text,
            token_usage=TokenUsage(...)
        )
```

### 5.4 自定义Executor

#### 5.4.1 PythonExecutor接口

```python
class PythonExecutor(ABC):
    @abstractmethod
    def send_variables(self, variables: dict):
        pass
    
    @abstractmethod
    def send_tools(self, tools: dict):
        pass
    
    @abstractmethod
    def __call__(self, code: str) -> str:
        pass
```

#### 5.4.2 内置Executor实现

- LocalPythonExecutor: 本地执行，默认
- E2BExecutor: E2B沙箱执行
- DockerExecutor: Docker容器执行
- BlaxelExecutor: Blaxel平台执行
- ModalExecutor: Modal平台执行
- WasmExecutor: WebAssembly执行

#### 5.4.3 使用远程Executor

```python
from smolagents import CodeAgent
from smolagents.remote_executors import E2BExecutor

executor = E2BExecutor(api_key="...")
agent = CodeAgent(
    tools=[],
    model=model,
    executor=executor
)
```

---

## 六、工具生态集成

### 6.1 Hugging Face Hub集成

#### 6.1.1 从Hub加载工具

```python
from smolagents import Tool

# 加载远程工具
tool = Tool.from_hub(
    "smolagents/test-tool",
    trust_remote_code=True
)
```

#### 6.1.2 推送工具到Hub

```python
tool.push_to_hub(
    repo_id="username/my-tool",
    commit_message="Upload tool"
)
```

#### 6.1.3 加载工具集合

```python
from smolagents import ToolCollection

# 从Hub集合加载多个工具
collection = ToolCollection.from_hub(
    "huggingface-tools/diffusion-tools",
    trust_remote_code=True
)

agent = CodeAgent(tools=[*collection.tools], model=model)
```

### 6.2 第三方工具集成

#### 6.2.1 从LangChain工具转换

```python
from smolagents import Tool
from langchain.tools import WikipediaQueryRun

langchain_tool = WikipediaQueryRun(...)
smol_tool = Tool.from_langchain(langchain_tool)
```

转换逻辑：
```python
class LangChainToolWrapper(Tool):
    def __init__(self, _langchain_tool):
        self.name = _langchain_tool.name.lower()
        self.description = _langchain_tool.description
        self.inputs = _langchain_tool.args.copy()
        self.output_type = "string"
        self.langchain_tool = _langchain_tool
    
    def forward(self, *args, **kwargs):
        return self.langchain_tool.run(kwargs)
```

#### 6.2.2 从Gradio Space转换

```python
from smolagents import Tool

# 将Hugging Face Space作为工具
image_generator = Tool.from_space(
    space_id="black-forest-labs/FLUX.1-schnell",
    name="image-generator",
    description="Generate an image from a prompt"
)
```

#### 6.2.3 从Gradio工具转换

```python
from smolagents import Tool
import gradio as gr

gradio_tool = gr.Tool(...)
smol_tool = Tool.from_gradio(gradio_tool)
```

### 6.3 工具链组合

#### 6.3.1 多来源工具组合

```python
from smolagents import CodeAgent, Tool, MCPClient

# 收集来自不同来源的工具
my_custom_tool = MyCustomTool()
langchain_tool = Tool.from_langchain(lc_tool)

with MCPClient(mcp_params) as mcp_tools:
    # 合并所有工具
    all_tools = [
        my_custom_tool,
        langchain_tool,
        *mcp_tools
    ]
    
    agent = CodeAgent(tools=all_tools, model=model)
```

#### 6.3.2 工具依赖管理

Tool类自动分析代码依赖：
```python
def to_dict(self) -> dict:
    tool_dict = {
        "name": self.name,
        "code": tool_code,
        "requirements": sorted(requirements)  # 自动检测的非stdlib依赖
    }
    return tool_dict
```

---

## 七、对我们项目的启示

### 7.1 MCP集成策略

对于AI数据分析系统项目，MCP集成带来以下价值：

1. **标准化工具接入**: 统一的数据源连接器接口，降低集成成本
2. **动态工具发现**: 运行时从MCP服务器获取可用工具列表
3. **安全隔离**: MCP服务器在独立进程中运行，与主应用隔离

建议实现方案：
```python
# 数据分析专用MCP服务器配置
DATA_ANALYSIS_MCP_SERVERS = {
    "sql_connector": {
        "command": "python",
        "args": ["mcp_servers/sql_server.py"],
        "env": {"DB_URL": "..."}
    },
    "pandas_processor": {
        "command": "python", 
        "args": ["mcp_servers/pandas_server.py"]
    }
}
```

### 7.2 扩展机制借鉴

#### 7.2.1 Tool设计模式

smolagents的Tool基类设计值得借鉴：
- 声明式inputs定义，自动生成schema
- 延迟初始化机制，setup方法按需加载
- 自动签名验证，确保一致性

#### 7.2.2 Agent架构

MultiStepAgent的抽象层次清晰：
- 记忆管理分离到AgentMemory
- 回调机制支持扩展
- 流式输出统一接口

### 7.3 生态集成思路

1. **模块化工具市场**: 类似Hugging Face Hub的工具发布机制
2. **多框架兼容**: 支持导入LangChain、LlamaIndex等生态工具
3. **标准化协议**: 内部工具也采用MCP协议，保持统一

### 7.4 安全考量

smolagents的安全设计值得学习：
- `trust_remote_code`显式确认机制
- 远程Executor隔离执行环境
- 工具代码静态分析验证

建议在我们的项目中：
- 所有外部工具必须通过显式授权
- 敏感操作在沙箱环境中执行
- 记录所有工具调用日志用于审计

---

## 参考文档

- [[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/mcp_client.py|mcp_client.py 源码]]
- [[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/tools.py|tools.py 源码]]
- [[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py 源码]]
- [[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/models.py|models.py 源码]]
- MCP官方规范: https://modelcontextprotocol.io/specification
- smolagents文档: https://huggingface.co/docs/smolagents
