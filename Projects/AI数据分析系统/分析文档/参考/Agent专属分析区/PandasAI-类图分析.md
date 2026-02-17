# PandasAI 类图分析

> 深入分析 PandasAI 核心类的关系与职责

---

## 一、核心类关系图

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              PandasAI 核心类图                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐     │
│  │                              Agent                                    │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  + __init__(dfs, config, memory_size, vectorstore, description)      │     │
│  │  + chat(query: str) → BaseResponse                                   │     │
│  │  + follow_up(query: str) → BaseResponse                              │     │
│  │  + generate_code(query) → str                                        │     │
│  │  + execute_code(code) → dict                                         │     │
│  │  + train(queries, codes, docs) → None                                │     │
│  │  + generate_code_with_retries(query) → str                           │     │
│  │  + execute_with_retries(code) → Any                                  │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  - _process_query(query, output_type) → BaseResponse                 │     │
│  │  - _regenerate_code_after_error(code, error) → str                   │     │
│  │  - _handle_exception(code) → ErrorResponse                           │     │
│  │  - _execute_sql_query(query) → pd.DataFrame                          │     │
│  ├───────────────────────────────────────────────────────────────────────┤     │
│  │  属性:                                                                │     │
│  │  - _state: AgentState          (状态中心)                            │     │
│  │  - _code_generator: CodeGenerator  (代码生成)                        │     │
│  │  - _response_parser: ResponseParser (响应解析)                       │     │
│  │  - _sandbox: Sandbox           (可选沙箱)                            │     │
│  └──────────────────┬────────────────────────────────────────────────────┘     │
│                     │                                                           │
│                     │ uses                                                      │
│                     ▼                                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐     │
│  │                           AgentState                                  │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  (dataclass)                                                          │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  + dfs: List[DataFrame]              # 数据集                         │     │
│  │  + memory: Memory                    # 对话记忆                       │     │
│  │  + config: Config                    # 配置 (property)                │     │
│  │  + logger: Logger                    # 日志                           │     │
│  │  + vectorstore: VectorStore          # 向量存储                       │     │
│  │  + intermediate_values: Dict         # 中间值                         │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  + last_code_generated: str          # 最后生成的代码                 │     │
│  │  + last_code_executed: str           # 最后执行的代码                 │     │
│  │  + last_prompt_id: str               # Prompt 追踪 ID                 │     │
│  │  + last_prompt_used: str             # 最后使用的 Prompt              │     │
│  │  + output_type: str                  # 期望输出类型                   │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  + initialize(dfs, config, memory_size, vectorstore, description)    │     │
│  │  + assign_prompt_id()                                                │     │
│  │  + add(key, value) / get(key)                                        │     │
│  │  + reset_intermediate_values()                                       │     │
│  └──────────────────┬────────────────────────────────────────────────────┘     │
│                     │                                                           │
│       ┌─────────────┼─────────────┐                                             │
│       │             │             │                                             │
│       ▼             ▼             ▼                                             │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐                                        │
│  │ Memory  │  │ Config   │  │ Logger   │                                        │
│  └─────────┘  └──────────┘  └──────────┘                                        │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐     │
│  │                         CodeGenerator                                 │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  + __init__(context: AgentState)                                      │     │
│  │  + generate_code(prompt: BasePrompt) → str                           │     │
│  │  - validate_and_clean_code(code) → str                               │     │
│  ├───────────────────────────────────────────────────────────────────────┤     │
│  │  依赖:                                                                │     │
│  │  - _context: AgentState                                              │     │
│  │  - _code_cleaner: CodeCleaner                                        │     │
│  │  - _code_validator: CodeRequirementValidator                         │     │
│  └───────────────────────────────────────────────────────────────────────┘     │
│           │                                                                     │
│           ├──uses──► ┌─────────────┐                                            │
│           │          │ CodeCleaner │                                            │
│           │          │ ─────────── │                                            │
│           │          │ clean_code()│                                            │
│           │          │ _clean_sql_query()                                       │
│           │          │ _replace_output_filenames_with_temp_chart()              │
│           │          └─────────────┘                                            │
│           │                                                                     │
│           └──uses──► ┌──────────────────────┐                                   │
│                      │ CodeRequirementValidator                                  │
│                      │ ──────────────────── │                                   │
│                      │ validate(code) → bool│                                   │
│                      │ • 检查 execute_sql_query 调用                           │
│                      └──────────────────────┘                                   │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐     │
│  │                          CodeExecutor                                 │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  + __init__(config: Config)                                           │     │
│  │  + add_to_env(key, value)                                             │     │
│  │  + execute(code) → dict                                              │     │
│  │  + execute_and_return_result(code) → Any                             │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  属性:                                                                │     │
│  │  - _environment: dict   # 执行环境变量                                │     │
│  │  - environment: dict   # property 访问器                              │     │
│  ├───────────────────────────────────────────────────────────────────────┤     │
│  │  环境包含:                                                            │     │
│  │  - pd: pandas                                                         │     │
│  │  - plt: matplotlib.pyplot                                             │     │
│  │  - np: numpy                                                          │     │
│  │  - execute_sql_query: function (动态注入)                             │     │
│  │  - skills: functions (动态注入)                                       │     │
│  └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐     │
│  │                         ResponseParser                                │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  + parse(result, last_code_executed) → BaseResponse                  │     │
│  │  - _validate_response(result) → bool                                 │     │
│  │  - _generate_response(result, last_code_executed) → BaseResponse     │     │
│  └──────────────────┬────────────────────────────────────────────────────┘     │
│                     │                                                           │
│       ┌─────────────┼─────────────┬──────────────────┐                         │
│       │             │             │                  │                         │
│       ▼             ▼             ▼                  ▼                         │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌─────────────────┐                │
│  │NumberResp│ │StringResp│ │DataFrameResp│ │  ChartResponse  │                │
│  │  (value) │ │  (value) │ │   (value)   │ │    (value)      │                │
│  └──────────┘ └──────────┘ └─────────────┘ └─────────────────┘                │
│       │                                                        ▲               │
│       └──────────────────────┬─────────────────────────────────┘               │
│                              │                                                  │
│                              ▼                                                  │
│                   ┌───────────────────┐                                         │
│                   │   BaseResponse    │                                         │
│                   │  ───────────────  │                                         │
│                   │  value: Any       │                                         │
│                   │  type: str        │                                         │
│                   │  last_code_executed: str                                    │
│                   │  error: str       │                                         │
│                   └───────────────────┘                                         │
│                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────┐     │
│  │                            Sandbox                                    │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  (抽象基类)                                                             │     │
│  │  ─────────────────────────────────────────────────────────────────   │     │
│  │  + start()                                                            │     │
│  │  + stop()                                                             │     │
│  │  + execute(code, environment) → dict                                 │     │
│  │  - _exec_code(code, environment) → dict  (抽象)                      │     │
│  │  - _extract_sql_queries_from_code(code) → list[str]                  │     │
│  │  - _compile_code(code) → str                                         │     │
│  └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、类职责详解

### 2.1 Agent - 协调器 (Coordinator)

**设计模式**: Facade 模式

```python
class Agent:
    """
    Agent 是 PandasAI 的 Facade 类，隐藏内部复杂性，提供极简 API。
    
    职责:
    1. 协调各组件工作 (State, Generator, Executor, Parser)
    2. 实现双层重试机制
    3. 管理 SQL 查询执行
    4. 处理异常和错误
    """
    
    def __init__(self, dfs, config=None, ...):
        # 1. 初始化状态
        self._state = AgentState()
        self._state.initialize(dfs, config, ...)
        
        # 2. 初始化组件
        self._code_generator = CodeGenerator(self._state)
        self._response_parser = ResponseParser()
        self._sandbox = sandbox
```

**关键方法**:

| 方法 | 职责 | 重试机制 |
|------|------|----------|
| `chat()` | 主入口，开始新对话 | 调用带重试的方法 |
| `follow_up()` | 继续对话 | 调用带重试的方法 |
| `generate_code()` | 单次代码生成 | 无 |
| `generate_code_with_retries()` | 带重试的代码生成 | 有 (LLM 层) |
| `execute_code()` | 单次代码执行 | 无 |
| `execute_with_retries()` | 带重试的代码执行 | 有 (执行层) |

### 2.2 AgentState - 状态中心 (State Center)

**设计模式**: 单一数据源 (Single Source of Truth)

```python
@dataclass
class AgentState:
    """
    AgentState 是 PandasAI 的核心设计，所有组件共享同一状态实例。
    
    设计亮点:
    1. 使用 @dataclass 简化定义
    2. 使用 @property 实现配置层级
    3. 中间值字典支持动态扩展
    """
    
    @property
    def config(self):
        # 优雅处理配置优先级: 局部 > 全局
        if self._config is not None:
            return self._config
        return pai.config.get()  # 全局配置
```

**状态分类**:

```
AgentState
├── 静态状态 (初始化后不变)
│   ├── dfs: DataFrame 列表
│   ├── memory: 对话记忆
│   ├── config: 配置
│   └── logger: 日志器
│
├── 动态状态 (每次查询变化)
│   ├── last_code_generated: 最后生成的代码
│   ├── last_code_executed: 最后执行的代码
│   ├── last_prompt_id: Prompt 追踪 ID
│   ├── last_prompt_used: 最后使用的 Prompt
│   └── output_type: 期望输出类型
│
└── 中间值 (临时存储)
    └── intermediate_values: Dict[str, Any]
```

### 2.3 CodeGenerator - 代码生成器

**设计模式**: Strategy 模式 (通过 Prompt 策略)

```python
class CodeGenerator:
    """
    职责单一的代码生成器，将复杂逻辑拆分为验证和清洗两个阶段。
    """
    
    def generate_code(self, prompt: BasePrompt) -> str:
        # 1. 调用 LLM
        code = self._context.config.llm.generate_code(prompt, self._context)
        
        # 2. 验证和清洗
        cleaned_code = self.validate_and_clean_code(code)
        
        return cleaned_code
```

**工作流程**:

```
Prompt ──► LLM.generate_code() ──► Raw Code
                                         │
                                         ▼
                              ┌──────────────────┐
                              │ CodeValidator    │
                              │ • 检查必须调用   │
                              │   execute_sql_query
                              └────────┬─────────┘
                                       │ 通过?
                                       ▼
                              ┌──────────────────┐
                              │ CodeCleaner      │
                              │ • 替换图表路径   │
                              │ • 验证 SQL 表名  │
                              │ • 移除 plt.show  │
                              └────────┬─────────┘
                                       │
                                       ▼
                              Clean Code
```

### 2.4 CodeExecutor - 代码执行器

**设计模式**: Environment 模式

```python
class CodeExecutor:
    """
    轻量级代码执行器，通过控制环境变量保证安全。
    """
    
    def __init__(self, config: Config):
        # 预加载安全的数据分析库
        self._environment = get_environment()  # pd, plt, np
    
    def add_to_env(self, key: str, value: Any):
        """动态注入自定义函数"""
        self._environment[key] = value
    
    def execute_and_return_result(self, code: str) -> Any:
        exec(code, self._environment)
        
        # 强制要求返回 result 变量
        if "result" not in self._environment:
            raise NoResultFoundError(...)
        
        return self._environment["result"]
```

**安全设计**:

| 安全措施 | 实现方式 |
|----------|----------|
| 环境隔离 | 仅暴露 pd, plt, np |
| 动态注入 | 通过 add_to_env 添加 execute_sql_query |
| 结果约束 | 强制要求返回 result 变量 |
| 可选沙箱 | 通过 Sandbox 接口支持自定义隔离 |

### 2.5 ResponseParser - 响应解析器

**设计模式**: Factory 模式

```python
class ResponseParser:
    """
    根据 result 类型创建对应的 Response 对象。
    """
    
    def _generate_response(self, result: dict, last_code_executed: str):
        type_mapping = {
            "number": NumberResponse,
            "string": StringResponse,
            "dataframe": DataFrameResponse,
            "plot": ChartResponse,
        }
        
        response_class = type_mapping.get(result["type"])
        return response_class(result["value"], last_code_executed)
```

**Response 类层次**:

```
BaseResponse (抽象基类)
├── NumberResponse    → value: int/float
├── StringResponse    → value: str
├── DataFrameResponse → value: pd.DataFrame
└── ChartResponse     → value: str (路径) / dict (base64)
```

### 2.6 Sandbox - 沙箱抽象

**设计模式**: Template Method 模式

```python
class Sandbox(ABC):
    """
    沙箱抽象基类，允许用户自定义安全执行环境。
    
    默认无实现，需要子类化:
    - DockerSandbox: Docker 容器隔离
    - ProcessSandbox: 进程隔离
    - RestrictedPythonSandbox: 受限 Python 执行
    """
    
    def execute(self, code: str, environment: dict) -> dict:
        # 模板方法
        if not self._started:
            self.start()
        return self._exec_code(code, environment)
    
    @abstractmethod
    def _exec_code(self, code: str, environment: dict) -> dict:
        pass
```

---

## 三、关键交互时序

### 3.1 正常查询流程

```
User          Agent          AgentState    CodeGenerator    CodeExecutor    ResponseParser
 │              │                │                │                │                │
 │──chat()────►│                │                │                │                │
 │              │──initialize()─►│                │                │                │
 │              │◄───────────────│                │                │                │
 │              │                │                │                │                │
 │              │──generate_code_with_retries()────────────────────►│                │
 │              │                │                │                │                │
 │              │◄───────────────generate_code(prompt)─────────────│                │
 │              │                │                │                │                │
 │              │                │                │──validate_and_clean()──────────►│
 │              │                │                │◄───────────────────────────────│
 │              │◄───────────────clean_code────────────────────────│                │
 │              │                │                │                │                │
 │              │──execute_with_retries(code)──────────────────────────────────────►│
 │              │                │                │                │                │
 │              │                │                │                │──execute()────►│
 │              │                │                │                │◄───────────────│
 │              │                │                │                │                │
 │              │◄─────────────────────────────────────────────────result───────────│
 │              │                │                │                │                │
 │              │──parse(result)────────────────────────────────────────────────────►│
 │              │◄─────────────────────────────────────────────────BaseResponse─────│
 │              │                │                │                │                │
 │◄─────────────│                │                │                │                │
 │                                                                                   │
```

### 3.2 错误重试流程

```
Agent           CodeExecutor        Error Handler      CodeGenerator
  │                  │                    │                  │
  │──execute_with_retries()────────────────────────────────────────►
  │                  │                    │                  │
  │                  │──execute()─────────────────────────────►
  │                  │                    │                  │
  │                  │◄────Exception──────────────────────────│
  │                  │                    │                  │
  │◄─────────────────error────────────────│                  │
  │                  │                    │                  │
  │──_regenerate_code_after_error()───────►│                  │
  │                  │                    │                  │
  │                  │                    │──generate_code()─►│
  │                  │                    │                  │
  │◄──────────────────────────────────────new_code─────────────│
  │                  │                    │                  │
  │──execute_with_retries(new_code)──────────────────────────────►
  │                  │                    │                  │
  │                  │──execute()─────────────────────────────►
  │                  │                    │                  │
  │◄─────────────────success───────────────────────────────────│
  │                  │                    │                  │
```

---

## 四、设计模式总结

| 设计模式 | 应用位置 | 作用 |
|----------|----------|------|
| **Facade** | Agent 类 | 隐藏内部复杂性，提供简洁 API |
| **Strategy** | BasePrompt 子类 | 支持不同的 Prompt 生成策略 |
| **Factory** | ResponseParser | 根据类型创建对应的 Response 对象 |
| **Template Method** | Sandbox | 定义沙箱执行流程，子类实现具体逻辑 |
| **Singleton (隐含)** | Config | 通过 property 实现全局配置共享 |

---

## 五、架构亮点总结

1. **极简 API**: `agent.chat()` 一行代码完成所有操作
2. **单一数据源**: AgentState 集中管理所有状态
3. **分层验证**: Validator → Cleaner → Executor 三层保障
4. **灵活配置**: 局部/全局配置通过 property 优雅处理
5. **双层重试**: 生成层和执行层分离，提高成功率
6. **可选安全**: Sandbox 作为可选项，不强加复杂度
7. **强制约束**: 通过 CodeValidator 强制使用安全函数

---

*类图由 Kimi Code CLI 生成*
