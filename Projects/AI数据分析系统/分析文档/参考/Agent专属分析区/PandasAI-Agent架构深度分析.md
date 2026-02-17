# PandasAI Agent 架构深度分析

> **分析日期**: 2026-02-05  
> **版本**: 3.0  
> **分析范围**: `pandasai/agent/`, `pandasai/core/`

---

## 一、架构总览：极简设计的哲学

### 1.1 核心设计理念

PandasAI 的设计哲学可以用一句话概括：**"一行代码，无限可能"**。

```python
# 极简 API - 用户只需要两行代码
agent = Agent(dfs)
result = agent.chat("分析数据")
```

其内部架构却暗含精妙设计：

```
┌─────────────────────────────────────────────────────────────────┐
│                     PandasAI 极简架构图                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   User Query ──► Agent ──► AgentState ──► CodeGenerator         │
│                               │               │                 │
│                               ▼               ▼                 │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  状态驱动 (State-Driven)                                │    │
│   │  • 单一数据源 (AgentState 保存所有上下文)                 │    │
│   │  • 配置集中管理 (Config 通过 property 动态获取)          │    │
│   └───────────────────────────────────────────────────────┘    │
│                               │                                 │
│                               ▼                                 │
│   CodeCleaner ──► CodeValidator ──► CodeExecutor ──► Response   │
│        │                                                        │
│        ▼                                                        │
│   Sandbox (可选) ──► 安全执行环境                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 与 TaskWeaver、DB-GPT 的对比

| 维度 | PandasAI | TaskWeaver | DB-GPT |
|------|----------|------------|--------|
| **架构复杂度** | ⭐ 极简 (4个核心类) | ⭐⭐⭐ 复杂 (多组件协作) | ⭐⭐⭐⭐ 企业级 (微服务架构) |
| **状态管理** | 单一 AgentState | PlannerSession + Post | 多状态机 |
| **API 简洁度** | `agent.chat()` | 需配置 Planner/Worker | 需配置多模块 |
| **扩展性** | Skill + Sandbox | Plugin 系统 | 丰富的生态系统 |
| **适用场景** | 个人/小团队 | 企业应用开发 | 大规模企业部署 |
| **错误处理** | 简单重试机制 | 复杂重试+验证 | 完整监控体系 |

---

## 二、AgentState 状态机分析

![PandasAI-状态流转图.svg](graphviz/PandasAI-状态流转图.svg)

### 2.1 状态机设计：一个 dataclass 管所有

```python
@dataclass
class AgentState:
    """Context class for managing pipeline attributes"""
    
    # 核心数据
    dfs: List[DataFrame] = field(default_factory=list)
    _config: Union[Config, dict] = field(default_factory=dict)
    
    # 会话状态
    memory: Memory = field(default_factory=Memory)
    intermediate_values: Dict[str, Any] = field(default_factory=dict)
    
    # 执行状态
    last_code_generated: Optional[str] = None
    last_code_executed: Optional[str] = None
    last_prompt_id: str = None
    last_prompt_used: str = None
    output_type: Optional[str] = None
    
    # 扩展能力
    vectorstore: Optional[VectorStore] = None
    logger: Optional[Logger] = None
```

**设计亮点**:

1. **单一数据源**: 所有组件共享同一个 `AgentState` 实例
2. **延迟配置**: `config` 通过 `@property` 动态获取，支持全局/局部配置
3. **不可变设计**: 使用 `@dataclass` 确保状态清晰可追踪

### 2.2 状态流转

```
                    ┌─────────────────┐
                    │   INITIALIZED   │
                    └────────┬────────┘
                             │ initialize()
                             ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  CODE_EXECUTED  │◄───│  CODE_GENERATED │◄───│   QUERY_RECEIVED│
└────────┬────────┘    └─────────────────┘    └─────────────────┘
         │                                          │
         │                                          │ generate_code()
         │ execute_code()                           ▼
         │                                   ┌─────────────────┐
         └──────────────────────────────────►│      ERROR      │
                                             └─────────────────┘
                                                    │
                                                    │ _regenerate_code_after_error()
                                                    ▼
                                             ┌─────────────────┐
                                             │   RETRYING      │──┐
                                             └─────────────────┘  │
                                                    ▲──────────────┘
                                                    │ (max_retries)
                                                    └──────────────┘
```

### 2.3 Config 的优雅设计

```python
@property
def config(self):
    """
    Returns the local config if set, otherwise fetches the global config.
    优雅地处理配置优先级：局部 > 全局
    """
    if self._config is not None:
        return self._config
    import pandasai as pai
    return pai.config.get()

@config.setter
def config(self, value):
    """Allows setting a new config value."""
    self._config = Config(**value) if isinstance(value, dict) else value
```

**学习点**:
- 通过 property 实现配置层级（局部 > 全局）
- 支持 dict/Config 对象的灵活赋值

---

## 三、代码生成流程

### 3.1 CodeGenerator：职责单一的生成器

```python
class CodeGenerator:
    def __init__(self, context: AgentState):
        self._context = context
        self._code_cleaner = CodeCleaner(self._context)      # 代码清洗
        self._code_validator = CodeRequirementValidator(self._context)  # 代码验证

    def generate_code(self, prompt: BasePrompt) -> str:
        # 1. 调用 LLM 生成代码
        code = self._context.config.llm.generate_code(prompt, self._context)
        self._context.last_code_generated = code
        
        # 2. 验证和清洗
        cleaned_code = self.validate_and_clean_code(code)
        self._context.last_code_generated = cleaned_code
        
        return cleaned_code
```

### 3.2 三步验证链

```
┌──────────────────────────────────────────────────────────────┐
│                    代码生成验证链                              │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│   LLM Output                                                 │
│      │                                                       │
│      ▼                                                       │
│   ┌──────────────────┐                                       │
│   │ CodeValidator    │ 验证: 必须调用 execute_sql_query      │
│   │                  │ 异常: ExecuteSQLQueryNotUsed          │
│   └────────┬─────────┘                                       │
│            │ 通过?                                           │
│            ▼                                                 │
│   ┌──────────────────┐                                       │
│   │ CodeCleaner      │ 清洗:                                  │
│   │                  │   - 替换图表输出路径                    │
│   │                  │   - 移除 plt.show()                    │
│   │                  │   - 验证 SQL 表名                       │
│   │                  │   - 跳过函数定义                        │
│   └────────┬─────────┘                                       │
│            │                                                 │
│            ▼                                                 │
│   Clean Code                                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 3.3 SQL 注入防护

```python
class CodeCleaner:
    def _clean_sql_query(self, sql_query: str) -> str:
        """清洗 SQL 查询，防止注入"""
        # 1. 去除分号
        sql_query = sql_query.rstrip(";")
        
        # 2. 提取表名
        table_names = SQLParser.extract_table_names(sql_query, dialect)
        
        # 3. 只允许访问已注册的 DataFrame
        allowed_table_names = {
            df.schema.name: df.schema.name for df in self.context.dfs
        }
        
        # 4. 替换为安全的表名
        return self._replace_table_names(sql_query, table_names, allowed_table_names)
```

---

## 四、代码执行与 Sandbox

### 4.1 CodeExecutor：轻量级执行器

```python
class CodeExecutor:
    def __init__(self, config: Config):
        # 预加载安全环境
        self._environment = get_environment()  # pd, plt, np

    def execute_and_return_result(self, code: str) -> Any:
        # 执行代码
        self.execute(code)
        
        # 强制要求返回 result 变量
        if "result" not in self._environment:
            raise NoResultFoundError(
                "No result was returned. Please return: "
                "result = {'type': ..., 'value': ...}"
            )
        
        return self._environment.get("result")
```

### 4.2 环境隔离设计

```python
def get_environment() -> dict:
    """
    Returns the environment for the code to be executed.
    仅暴露安全的数据分析库。
    """
    return {
        "pd": import_dependency("pandas"),
        "plt": import_dependency("matplotlib.pyplot"),
        "np": import_dependency("numpy"),
    }
```

### 4.3 Sandbox：可选的安全层

```python
class Sandbox:
    """
    Sandbox 抽象基类 - 允许自定义隔离执行环境
    """
    def execute(self, code: str, environment: dict) -> dict:
        if not self._started:
            self.start()  # 启动沙箱环境
            return self._exec_code(code, environment)
        return self._exec_code(code, environment)

    def _exec_code(self, code: str, environment: dict) -> dict:
        raise NotImplementedError("Subclasses must implement")
```

**与 DB-GPT Sandbox 对比**:

| 特性 | PandasAI Sandbox | DB-GPT Sandbox |
|------|------------------|----------------|
| 设计目标 | 可插拔的抽象层 | 完整的安全执行环境 |
| 默认实现 | 无 (可选) | 有 (Docker/本地) |
| 隔离级别 | 依赖子类实现 | 进程/容器级隔离 |
| 适用场景 | 简单增强 | 企业级安全要求 |

### 4.4 Agent 层的 Sandbox 集成

```python
def execute_code(self, code: str) -> dict:
    code_executor = CodeExecutor(self._state.config)
    
    # 向环境注入自定义函数
    code_executor.add_to_env("execute_sql_query", self._execute_sql_query)
    for skill in self._state.skills:
        code_executor.add_to_env(skill.name, skill.func)
    
    # 如果有 Sandbox，使用 Sandbox 执行
    if self._sandbox:
        return self._sandbox.execute(code, code_executor.environment)
    
    # 否则直接执行
    return code_executor.execute_and_return_result(code)
```

---

## 五、自动错误重试机制

### 5.1 双层重试策略

PandasAI 实现了**双层重试机制**：

```
┌──────────────────────────────────────────────────────────────────┐
│                      双层重试架构                                 │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   第一层: 代码生成重试 (generate_code_with_retries)               │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  if LLM 生成失败:                                       │    │
│   │      while attempts <= max_retries:                     │    │
│   │          使用错误提示重新生成                           │    │
│   │          attempts++                                     │    │
│   └────────────────────────────────────────────────────────┘    │
│                              │                                   │
│                              ▼                                   │
│   第二层: 代码执行重试 (execute_with_retries)                    │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  while attempts <= max_retries:                         │    │
│   │      try:                                               │    │
│   │          执行代码                                       │    │
│   │          return 结果                                    │    │
│   │      except Exception:                                  │    │
│   │          使用错误追踪重新生成代码                        │    │
│   │          attempts++                                     │    │
│   └────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 5.2 代码实现

```python
def generate_code_with_retries(self, query: str) -> Any:
    """Execute the code with retry logic."""
    max_retries = self._state.config.max_retries
    attempts = 0
    
    try:
        return self.generate_code(query)
    except Exception as e:
        exception = e
        while attempts <= max_retries:
            try:
                return self._regenerate_code_after_error(
                    self._state.last_code_generated, exception
                )
            except Exception as e:
                exception = e
                attempts += 1
                if attempts > max_retries:
                    raise

def execute_with_retries(self, code: str) -> Any:
    """Execute the code with retry logic."""
    max_retries = self._state.config.max_retries
    attempts = 0

    while attempts <= max_retries:
        try:
            result = self.execute_code(code)
            return self._response_parser.parse(result, code)
        except Exception as e:
            attempts += 1
            if attempts > max_retries:
                raise
            code = self._regenerate_code_after_error(code, e)
```

### 5.3 错误修复 Prompt 设计

```python
def _regenerate_code_after_error(self, code: str, error: Exception) -> str:
    """根据错误类型选择不同的修复策略"""
    error_trace = traceback.format_exc()
    
    if isinstance(error, InvalidLLMOutputType):
        # 输出类型错误
        prompt = get_correct_output_type_error_prompt(self._state, code, error_trace)
    else:
        # 执行错误
        prompt = get_correct_error_prompt_for_sql(self._state, code, error_trace)
    
    return self._code_generator.generate_code(prompt)
```

**错误修复模板** (`correct_execute_sql_query_usage_error_prompt.tmpl`):

```
The user asked the following question:
{{context.memory.get_conversation()}}

You generated the following Python code:
{{code}}

However, it resulted in the following error:
{{error}}

Fix the python code above and return the new python code 
but the code generated should use execute_sql_query function
```

---

## 六、扩展性分析

### 6.1 Skill 系统

```python
# 通过 SkillsManager 注册自定义函数
self._state.skills = SkillsManager.get_skills()

# 执行时注入环境
def execute_code(self, code: str) -> dict:
    code_executor = CodeExecutor(self._state.config)
    for skill in self._state.skills:
        code_executor.add_to_env(skill.name, skill.func)
```

### 6.2 VectorStore 集成

```python
def train(self, queries=None, codes=None, docs=None):
    """训练 Agent，支持 Q&A 和文档"""
    if docs is not None:
        self._state.vectorstore.add_docs(docs)
    
    if queries and codes:
        self._state.vectorstore.add_question_answer(queries, codes)
```

### 6.3 Response 类型扩展

```python
class ResponseParser:
    def _generate_response(self, result: dict, last_code_executed: str = None):
        if result["type"] == "number":
            return NumberResponse(result["value"], last_code_executed)
        elif result["type"] == "string":
            return StringResponse(result["value"], last_code_executed)
        elif result["type"] == "dataframe":
            return DataFrameResponse(result["value"], last_code_executed)
        elif result["type"] == "plot":
            return ChartResponse(result["value"], last_code_executed)
```

---

## 七、优缺点总结

### 7.1 优点

| 优点 | 说明 |
|------|------|
| **极简 API** | `agent.chat()` 一行代码完成所有操作 |
| **状态集中** | AgentState 单一数据源，易于追踪 |
| **轻量设计** | 核心代码 < 500 行，易于理解 |
| **灵活配置** | 全局/局部配置 + 可选 Sandbox |
| **分层错误处理** | 双层重试机制，自动修复 |
| **SQL 优先** | 强制使用 SQL 进行数据操作，更安全 |

### 7.2 缺点

| 缺点 | 说明 |
|------|------|
| **功能有限** | 相比 TaskWeaver/DB-GPT，缺少复杂规划能力 |
| **Sandbox 薄弱** | 仅提供抽象层，无默认安全实现 |
| **错误信息** | 重试机制简单，无详细日志追踪 |
| **扩展性受限** | Skill 系统简单，无复杂 Plugin 机制 |
| **企业级特性** | 缺少权限管理、审计日志等 |

### 7.3 适用场景

```
推荐使用 PandasAI 的场景:
 快速原型开发
 个人数据分析
 小团队协作
 Jupyter Notebook 环境
 已有 pandas 工作流增强

不推荐的场景:
 企业级生产环境
 高安全要求场景
 复杂多步推理任务
 需要精细控制的场景
```

---

## 八、架构启示

### 8.1 可借鉴的设计

1. **状态机模式**: AgentState 作为单一数据源，简化组件间通信
2. **配置层级**: property 实现全局/局部配置，优雅处理优先级
3. **双层重试**: 生成层 + 执行层分离，提高成功率
4. **强制约束**: 通过 CodeValidator 强制使用安全函数

### 8.2 改进建议

1. **增强 Sandbox**: 提供默认的 Docker/进程隔离实现
2. **完善日志**: 增加结构化日志和追踪 ID
3. **Plugin 系统**: 参考 TaskWeaver 设计更灵活的扩展机制
4. **响应流式**: 支持生成过程的实时反馈

---

## 九、核心文件速查

| 文件 | 职责 | 行数 |
|------|------|------|
| `agent/base.py` | Agent 主类，协调所有组件 | ~330 |
| `agent/state.py` | 状态管理，单一数据源 | ~130 |
| `core/code_generation/base.py` | 代码生成器 | ~65 |
| `core/code_execution/code_executor.py` | 代码执行器 | ~50 |
| `core/response/parser.py` | 响应解析 | ~75 |
| `dataframe/base.py` | DataFrame 封装 | ~195 |
| `sandbox/sandbox.py` | 沙箱抽象基类 | ~90 |

---

*分析完成。![PandasAI-核心流程图.svg](graphviz/PandasAI-核心流程图.svg)*
