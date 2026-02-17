---
title: CAMEL 工具与技能系统分析
description: 深入分析 CAMEL 框架的工具集成机制和技能定义系统
tags: [camel, toolkit, function-tool, skill, mcp]
category: 参考/Agent专属分析区/camel专属分析区
date: 2026-02-06
author: AI Assistant
---

# CAMEL 工具与技能系统

## 1. Toolkit 架构概述

### 1.1 核心概念

CAMEL 的工具系统基于三个核心抽象层次：

| 层次 | 类 | 职责 |
|------|-----|------|
| 工具函数 | `FunctionTool` | 包装单个可调用函数，生成 OpenAI 兼容的 Schema |
| 工具集 | `BaseToolkit` | 组织相关工具，提供统一的工具发现接口 |
| 技能系统 | `SkillToolkit` | 加载外部 SKILL.md 文件，扩展 Agent 能力 |

### 1.2 BaseToolkit 基类

`BaseToolkit` 是所有工具集的基类，定义于 `camel/toolkits/base.py`：

```python
class BaseToolkit(metaclass=AgentOpsMeta):
    r"""工具集基类"""
    
    mcp: FastMCP
    timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD
    
    def __init__(self, timeout: Optional[float] = ...):
        # 初始化超时设置
        
    def get_tools(self) -> List[FunctionTool]:
        r"""返回工具列表，子类必须实现"""
        raise NotImplementedError
        
    def run_mcp_server(self, mode: Literal["stdio", "sse", ...]) -> None:
        r"""以 MCP 服务器模式运行"""
```

关键特性：

- **自动超时包装**：通过 `__init_subclass__` 自动为所有方法添加超时控制
- **MCP 兼容**：支持作为 MCP 服务器运行，实现跨进程工具调用
- **Agent 注册**：`RegisteredAgentToolkit` Mixin 允许工具集访问 Agent 实例

### 1.3 FunctionTool 工具包装器

`FunctionTool` 是 CAMEL 工具系统的核心类：

```python
class FunctionTool:
    r"""可被 OpenAI 模型调用的函数抽象"""
    
    def __init__(
        self,
        func: Callable,
        openai_tool_schema: Optional[Dict[str, Any]] = None,
        synthesize_schema: Optional[bool] = False,
        synthesize_output: Optional[bool] = False,
    ):
        self.func = func
        # 从函数签名自动生成 Schema，或接受自定义 Schema
        self.openai_tool_schema = openai_tool_schema or get_openai_tool_schema(func)
```

核心能力：

- **Schema 自动生成**：从 Python 类型注解和文档字符串生成 OpenAI 兼容的 JSON Schema
- **Schema 合成**：当自动生成失败时，使用 LLM 自动合成 Schema
- **输出合成**：支持在不实际执行的情况下模拟工具输出
- **异步支持**：同时支持同步和异步函数调用

## 2. 工具注册与发现机制

### 2.1 Schema 自动生成流程

```
Python 函数
    ↓
提取函数签名 → 参数类型注解
    ↓
提取文档字符串 → 参数描述
    ↓
创建 Pydantic 模型 → 生成 JSON Schema
    ↓
清理 title 字段 → 添加 additionalProperties: false
    ↓
OpenAI 兼容的 Tool Schema
```

代码实现：`get_openai_tool_schema` 函数

```python
def get_openai_tool_schema(func: Callable) -> Dict[str, Any]:
    # 1. 提取函数签名
    params = signature(func).parameters
    fields = {}
    for param_name, p in params.items():
        param_type = p.annotation if p.annotation is not Parameter.empty else Any
        # 2. 构建 Pydantic 字段定义
        if p.default is Parameter.empty:
            fields[param_name] = (param_type, FieldInfo())
        else:
            fields[param_name] = (param_type, FieldInfo(default=p.default))
    
    # 3. 创建 Pydantic 模型
    model = create_model(to_pascal(func.__name__), **fields)
    parameters_dict = get_pydantic_object_schema(model)
    
    # 4. 解析文档字符串
    docstring = parse(func.__doc__ or "")
    for param in docstring.params:
        if param.arg_name in parameters_dict["properties"]:
            parameters_dict["properties"][param.arg_name]["description"] = param.description
    
    # 5. 构建最终 Schema
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func_description,
            "strict": True,
            "parameters": parameters_dict,
        }
    }
```

### 2.2 工具集注册模式

每个 Toolkit 通过 `get_tools` 方法暴露其工具：

```python
class MathToolkit(BaseToolkit):
    def math_add(self, a: float, b: float) -> float:
        r"""Add two numbers."""
        return a + b
    
    def get_tools(self) -> List[FunctionTool]:
        return [
            FunctionTool(self.math_add),
            # ... 其他工具
        ]
```

### 2.3 Agent 工具集成

Agent 初始化时接收工具列表：

```python
chat_agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=[
        *MathToolkit().get_tools(),
        *SearchToolkit().get_tools(),
    ]
)
```

Agent 内部维护工具注册表：

```python
self._internal_tools: Dict[str, FunctionTool] = {}
for tool in tools:
    if callable(tool) and not isinstance(tool, FunctionTool):
        tool = FunctionTool(tool)
    self._internal_tools[tool.get_function_name()] = tool
```

## 3. 内置工具集详解

### 3.1 搜索工具集 SearchToolkit

位置：`camel/toolkits/search_toolkit.py`

支持的搜索引擎：

| 方法 | 搜索引擎 | 认证方式 |
|------|----------|----------|
| `search_serper` | Google via Serper.dev | SERPER_API_KEY |
| `search_duckduckgo` | DuckDuckGo | 无需认证 |
| `search_google` | Google Custom Search | GOOGLE_API_KEY + SEARCH_ENGINE_ID |
| `search_brave` | Brave Search | BRAVE_API_KEY |
| `search_wiki` | Wikipedia | 无需认证 |
| `search_tavily` | Tavily AI Search | TAVILY_API_KEY |
| `search_baidu` | 百度搜索 | 无需认证 |
| `search_bing` | 必应搜索 | 无需认证 |

使用示例：

```python
search_toolkit = SearchToolkit()
tools = search_toolkit.get_tools()

# 使用 DuckDuckGo 搜索
results = search_toolkit.search_duckduckgo(
    query="Python programming",
    source="text",
    number_of_result_pages=5
)
```

### 3.2 代码执行工具集 CodeExecutionToolkit

位置：`camel/toolkits/code_execution.py`

支持的沙箱环境：

| 沙箱类型 | 描述 | 适用场景 |
|----------|------|----------|
| `internal_python` | 内部 Python 解释器 | 简单计算，无需隔离 |
| `jupyter` | Jupyter Kernel | 数据分析，可视化 |
| `docker` | Docker 容器 | 完全隔离，安全执行 |
| `subprocess` | 子进程 | 系统命令执行 |
| `e2b` | E2B 云沙箱 | 云端安全执行 |
| `microsandbox` | Microsandbox | 轻量级隔离 |

```python
code_toolkit = CodeExecutionToolkit(
    sandbox="docker",
    verbose=True,
    require_confirm=True  # 执行前确认
)

# 执行 Python 代码
result = code_toolkit.execute_code(
    code="print('Hello, World!')",
    code_type="python"
)
```

### 3.3 文件操作工具集 FileToolkit

位置：`camel/toolkits/file_toolkit.py`

支持的文件格式：

- **读取**：txt, json, yaml, pdf, docx
- **写入**：md, txt, csv, json, yaml, html, pdf, docx

安全特性：

- 工作目录限制：所有操作限制在指定目录内
- 文件名清理：自动替换危险字符
- 自动备份：修改前创建 .bak 备份文件

```python
file_toolkit = FileToolkit(
    working_directory="./output",
    backup_enabled=True
)
```

### 3.4 数学工具集 MathToolkit

位置：`camel/toolkits/math_toolkit.py`

基础数学运算：

```python
class MathToolkit(BaseToolkit):
    def math_add(self, a: float, b: float) -> float
    def math_subtract(self, a: float, b: float) -> float
    def math_multiply(self, a: float, b: float, decimal_places: int = 2) -> float
    def math_divide(self, a: float, b: float, decimal_places: int = 2) -> float
    def math_round(self, a: float, decimal_places: int = 0) -> float
```

### 3.5 其他常用工具集

| 工具集 | 功能 | 关键依赖 |
|--------|------|----------|
| `GithubToolkit` | GitHub API 操作 | PyGithub |
| `SlackToolkit` | Slack 消息发送 | slack-sdk |
| `NotionToolkit` | Notion 页面操作 | notion-client |
| `BrowserToolkit` | 浏览器自动化 | playwright |
| `SQLToolkit` | 数据库查询 | sqlalchemy |
| `MemoryToolkit` | 向量记忆检索 | 无 |
| `HumanToolkit` | 人工介入 | 无 |

## 4. 工具调用流程

### 4.1 完整调用流程

![camel-工具调用流程图](camel-工具调用流程图.svg)

流程说明：

1. **用户输入**：Agent 接收用户消息
2. **上下文构建**：将历史消息和可用工具 Schema 发送给模型
3. **模型决策**：模型决定调用哪个工具，生成工具调用请求
4. **请求解析**：Agent 解析模型响应中的 tool_calls
5. **工具执行**：根据 tool_name 查找并执行对应工具
6. **结果记录**：将工具执行结果存入记忆
7. **循环或结束**：模型根据工具结果决定继续调用或返回最终答案

### 4.2 工具执行核心代码

```python
def _execute_tool(self, tool_call_request: ToolCallRequest) -> ToolCallingRecord:
    func_name = tool_call_request.tool_name
    args = tool_call_request.args
    tool_call_id = tool_call_request.tool_call_id
    
    # 1. 查找工具
    tool = self._internal_tools.get(func_name)
    if tool is None:
        raise ValueError(f"Tool '{func_name}' not found")
    
    # 2. 执行工具
    try:
        raw_result = tool(**args)
    except Exception as e:
        result = f"Tool execution failed: {e}"
    
    # 3. 记录调用
    return self._record_tool_calling(func_name, args, result, tool_call_id)
```

### 4.3 异步执行支持

CAMEL 完整支持异步工具执行：

```python
async def _aexecute_tool(self, tool_call_request: ToolCallRequest) -> ToolCallingRecord:
    tool = self._internal_tools.get(func_name)
    
    # 检查是否为异步函数
    if inspect.iscoroutinefunction(tool.func):
        raw_result = await tool.async_call(**args)
    else:
        # 同步工具在 executor 中运行
        loop = asyncio.get_running_loop()
        raw_result = await loop.run_in_executor(_SYNC_TOOL_EXECUTOR, tool, **args)
```

## 5. 自定义工具开发

### 5.1 基础工具集开发

```python
from camel.toolkits import BaseToolkit, FunctionTool
from typing import List

class MyToolkit(BaseToolkit):
    r"""自定义工具集示例"""
    
    def __init__(self, api_key: str, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.api_key = api_key
    
    def my_function(self, arg1: str, arg2: int = 10) -> str:
        r"""工具函数描述。
        
        Args:
            arg1: 第一个参数描述
            arg2: 第二个参数描述，默认为 10
            
        Returns:
            返回值描述
        """
        # 工具实现
        return f"Result: {arg1}, {arg2}"
    
    def get_tools(self) -> List[FunctionTool]:
        return [FunctionTool(self.my_function)]
```

### 5.2 使用装饰器快速创建工具

```python
from camel.toolkits import tool

@tool
def calculate_area(length: float, width: float) -> float:
    r"""Calculate the area of a rectangle.
    
    Args:
        length: The length of the rectangle
        width: The width of the rectangle
        
    Returns:
        The calculated area
    """
    return length * width

# 直接使用装饰器创建的工具
agent = ChatAgent(tools=[calculate_area])
```

### 5.3 需要 Agent 访问的工具集

当工具需要与 Agent 交互时使用 `RegisteredAgentToolkit`：

```python
from camel.toolkits import BaseToolkit, RegisteredAgentToolkit

class AgentAwareToolkit(BaseToolkit, RegisteredAgentToolkit):
    r"""需要访问 Agent 实例的工具集"""
    
    def check_agent_memory(self, query: str) -> str:
        r"""查询 Agent 记忆中的信息"""
        if self.agent is None:
            return "Agent not registered"
        
        # 访问 Agent 的记忆
        memory_content = self.agent.memory.get_context()
        # 处理查询...
        return result
```

注册方式：

```python
agent = ChatAgent(
    tools=[*AgentAwareToolkit().get_tools()],
    toolkits_to_register_agent=[AgentAwareToolkit()]  # 注册 Agent 到工具集
)
```

## 6. 技能系统 SkillToolkit

### 6.1 技能文件格式

技能是存储在 `SKILL.md` 文件中的结构化指令：

```yaml
---
name: data-analysis
description: 数据分析和可视化技能
---

# 数据分析流程

## 步骤 1：数据加载
使用 pandas 加载数据文件...

## 步骤 2：数据清洗
处理缺失值和异常值...

## 步骤 3：可视化
使用 matplotlib 创建图表...
```

### 6.2 技能发现机制

`SkillToolkit` 按优先级扫描以下目录：

| 优先级 | 作用域 | 路径 |
|--------|--------|------|
| 1 | repo | `./.camel/skills` 或 `./.agents/skills` |
| 2 | user | `~/.camel/skills` 或 `~/.config/camel/skills` |
| 3 | system | `/etc/camel/skills` |

### 6.3 技能使用流程

```python
skill_toolkit = SkillToolkit(working_directory="./project")

# 列出可用技能
skills = skill_toolkit.list_skills()

# 加载特定技能
skill_content = skill_toolkit.load_skill("data-analysis")
```

Agent 集成：

```python
agent = ChatAgent(
    tools=[*SkillToolkit().get_tools()],
)
# Agent 可以调用 load_skill 加载技能指导任务执行
```

## 7. MCP 工具集成

### 7.1 MCP 协议支持

CAMEL 支持 MCP 协议实现跨进程工具调用：

```python
from camel.toolkits import MCPToolkit

# 连接到 MCP 服务器
mcp_toolkit = MCPToolkit(
    server_url="http://localhost:8000",
    timeout=30
)

tools = mcp_toolkit.get_tools()
```

### 7.2 将 Toolkit 作为 MCP 服务器

使用 `@MCPServer` 装饰器：

```python
from camel.toolkits import BaseToolkit, MCPServer
from camel.utils import MCPServer as mcp_decorator

@mcp_decorator()
class MyToolkit(BaseToolkit):
    def get_tools(self):
        return [...]
    
# 运行 MCP 服务器
toolkit = MyToolkit()
toolkit.run_mcp_server(mode="stdio")
```

## 8. 与 smolagents 工具对比

| 特性 | CAMEL Toolkit | smolagents Tool |
|------|---------------|-----------------|
| **组织方式** | Toolkit 集合，多个工具一组 | 独立 Tool，单个函数 |
| **工具定义** | 类方法，通过 `get_tools` 暴露 | 函数或类，直接实例化 |
| **参数定义** | Python 类型注解 | `inputs` 字典描述 |
| **返回值** | 灵活，任意类型 | 需指定 `output_type` |
| **Schema 生成** | 自动从类型注解生成 | 手动定义或自动推断 |
| **异步支持** | 原生支持 | 有限支持 |
| **MCP 兼容** | 内置支持 | 需额外适配 |
| **技能系统** | SKILL.md 文件支持 | 无 |
| **工具发现** | 运行时通过 Toolkit 发现 | 静态定义 |

### 8.1 代码对比示例

**CAMEL 方式**：

```python
class WeatherToolkit(BaseToolkit):
    def get_weather(self, city: str, date: Optional[str] = None) -> Dict[str, Any]:
        r"""获取城市天气信息。
        
        Args:
            city: 城市名称
            date: 日期，格式 YYYY-MM-DD，默认为今天
        """
        # 实现...
        return {"temperature": 25, "condition": "sunny"}
    
    def get_tools(self) -> List[FunctionTool]:
        return [FunctionTool(self.get_weather)]
```

**smolagents 方式**：

```python
from smolagents import Tool

class WeatherTool(Tool):
    name = "get_weather"
    description = "获取城市天气信息"
    inputs = {
        "city": {"type": "string", "description": "城市名称"},
        "date": {"type": "string", "description": "日期", "nullable": True}
    }
    output_type = "object"
    
    def forward(self, city: str, date: Optional[str] = None) -> Dict[str, Any]:
        # 实现...
        return {"temperature": 25, "condition": "sunny"}
```

## 9. 工具系统架构图

![camel-Toolkit架构图](camel-Toolkit架构图.svg)

架构层次说明：

1. **工具实现层**：具体的工具函数实现，如搜索、文件操作等
2. **工具集层**：`BaseToolkit` 子类，组织和暴露相关工具
3. **工具包装层**：`FunctionTool` 将函数包装为模型可调用的格式
4. **Agent 集成层**：`ChatAgent` 管理工具注册、调用和结果处理
5. **模型交互层**：与 LLM 的交互，传递工具 Schema 和处理工具调用请求

## 10. 最佳实践

### 10.1 工具设计原则

1. **单一职责**：每个工具函数只做一件事
2. **清晰文档**：完整的 docstring，包含 Args 和 Returns
3. **类型注解**：所有参数和返回值都应有类型注解
4. **错误处理**：工具内部捕获异常，返回友好的错误信息

### 10.2 性能优化

1. **超时控制**：为可能耗时的工具设置合理超时
2. **异步执行**：对于 IO 密集型工具使用异步实现
3. **结果缓存**：对重复查询使用 `@functools.lru_cache`

### 10.3 安全考虑

1. **沙箱执行**：代码执行使用隔离环境
2. **路径限制**：文件操作限制在指定工作目录
3. **敏感信息**：API 密钥通过环境变量传递

## 参考链接

- [[01-camel-架构概述]]
- [[02-camel-消息系统]]
- [[03-camel-记忆系统]]
- [[04-camel-Agent系统]]
- CAMEL 源码：`Projects/AI数据分析系统/参考项目/camel/camel/toolkits/`
