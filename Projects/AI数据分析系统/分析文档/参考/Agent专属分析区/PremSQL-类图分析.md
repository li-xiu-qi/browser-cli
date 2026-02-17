# PremSQL 类图分析

> 基于源码的类结构分析与设计模式解读

---

## 一、Worker 继承体系

### 1.1 类继承层次图

```
                        ABC (Python 抽象基类)
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
   ┌─────────┐    ┌──────────┐    ┌───────────┐
   │WorkerBase│    │AgentBase │    │BaseModel  │
   │(最简接口)│    │(Pipeline │    │(Pydantic) │
   └────┬────┘    │ 主控类)  │    └─────┬─────┘
        │         └────┬─────┘          │
        │              │                │
   ┌────┴────┐         │         ┌──────┴──────┐
   │         │         │         │             │
   ▼         ▼         ▼         ▼             ▼
┌────────┐ ┌──────────┐    ┌──────────┐  ┌───────────┐
│Text2SQL│ │ Analysis │    │Router    │  │BaseWorker-│
│Worker  │ │WorkerBase│    │WorkerBase│  │Output     │
│Base    │ └────┬─────┘    └────┬─────┘  │(Pydantic) │
└────┬───┘      │               │        └─────┬─────┘
     │          ▼               ▼              │
     │    ┌──────────┐    ┌──────────┐         │
     │    │ChartPlot │    │Followup  │         │
     │    │WorkerBase│    │Worker    │         │
     │    └──────────┘    │(继承     │         │
     │                    │WorkerBase)│         │
     │                    └──────────┘         │
     │                                         │
     ▼                                         ▼
┌─────────────────┐                    ┌──────────────┐
│BaseLineText2SQL │                    │Text2SQLWorker│
│Worker           │                    │Output        │
│(具体实现)        │                    │              │
└─────────────────┘                    │AnalyserWorker│
                                       │Output        │
┌─────────────────┐                    │              │
│BaseLineAnalyser │                    │ChartPlotWorker│
│Worker           │                    │Output        │
│(具体实现)        │                    │              │
└─────────────────┘                    │RouterWorker  │
                                       │Output        │
┌─────────────────┐                    │              │
│BaseLinePlotWorker│                   │ExitWorkerOutput│
│(具体实现)        │                   │              │
└─────────────────┘                    │AgentOutput   │
                                       └──────────────┘
┌─────────────────┐
│BaseLineFollowup │
│Worker           │
│(具体实现)        │
└─────────────────┘
```

### 1.2 抽象基类详解

#### WorkerBase - 最简接口

```python
class WorkerBase(ABC):
    """所有 Worker 的最基础接口
    
    设计意图: 提供一个统一的调用契约，任何 Worker 都必须实现 run 方法
    """
    @abstractmethod
    def run(self):
        return NotImplementedError()
```

**设计特点**:
- 极简设计，只定义调用契约
- Followup Worker 直接继承此类（不需要特定输入类型）

#### Text2SQLWorkerBase - 数据库操作 Worker

```python
class Text2SQLWorkerBase(ABC):
    """Text2SQL 专用 Worker 基类
    
    职责:
    1. 管理数据库连接 (SQLDatabase)
    2. 协调 Generator 和 Executor
    3. 提供表过滤功能
    """
    def __init__(
        self,
        db_connection_uri: str,
        generator: Text2SQLGeneratorBase,
        executor: BaseExecutor,
        include_tables: Optional[str] = None,
        exclude_tables: Optional[str] = None,
    ):
        self.generator = generator      # SQL 生成模型
        self.executor = executor        # SQL 执行器
        self.db_connection_uri = db_connection_uri
        self.db = self.initialize_database(...)  # LangChain SQLDatabase
    
    def initialize_database(self, ...) -> SQLDatabase:
        """初始化数据库连接
        
        支持 include_tables/exclude_tables 过滤，减少 Schema 长度
        """
        return SQLDatabase.from_uri(
            database_uri=db_connection_uri,
            sample_rows_in_table_info=0,
            ignore_tables=exclude_tables,
            include_tables=include_tables
        )
    
    @abstractmethod
    def run(self, question: str, **kwargs) -> Text2SQLWorkerOutput:
        raise NotImplementedError
```

**设计特点**:
- 内置数据库生命周期管理
- 依赖注入：generator 和 executor 通过构造器传入
- 支持表级别过滤（优化 Token 使用）

#### AnalysisWorkerBase - 数据分析 Worker

```python
class AnalysisWorkerBase(ABC):
    """数据分析 Worker 基类
    
    职责: 对 DataFrame 进行自然语言分析
    """
    @abstractmethod
    def run(
        self, 
        question: str, 
        input_dataframe: Optional[pd.DataFrame] = None
    ) -> AnalyserWorkerOutput:
        raise NotImplementedError
```

**设计特点**:
- 输入是 DataFrame（来自上游 Worker 或历史记录）
- 输出是分析结论（自然语言）

#### ChartPlotWorkerBase - 图表生成 Worker

```python
class ChartPlotWorkerBase(ABC):
    """图表生成 Worker 基类
    
    职责: 将 DataFrame 转换为可视化图表
    """
    @abstractmethod
    def run(
        self, 
        question: str, 
        input_dataframe: Optional[pd.DataFrame] = None
    ) -> ChartPlotWorkerOutput:
        raise NotImplementedError
```

**设计特点**:
- 与 AnalysisWorkerBase 相同输入类型
- 输出包含图表配置和 Base64 图片

#### RouterWorkerBase - 路由决策 Worker

```python
class RouterWorkerBase(ABC):
    """路由 Worker 基类
    
    职责: 决定 Pipeline 执行路径
    """
    @abstractmethod
    def run(
        self, 
        question: str, 
        input_dataframe: Optional[pd.DataFrame] = None
    ) -> RouterWorkerOutput:
        raise NotImplementedError
```

---

## 二、具体 Worker 实现

### 2.1 实现类列表

| 抽象基类 | 具体实现 | 文件路径 |
|---------|---------|---------|
| Text2SQLWorkerBase | BaseLineText2SQLWorker | `agents/baseline/workers/text2sql.py` |
| AnalysisWorkerBase | BaseLineAnalyserWorker | `agents/baseline/workers/analyser.py` |
| ChartPlotWorkerBase | BaseLinePlotWorker | `agents/baseline/workers/plotter.py` |
| RouterWorkerBase | SimpleRouterWorker | `agents/router.py` |
| WorkerBase | BaseLineFollowupWorker | `agents/baseline/workers/followup.py` |

### 2.2 BaseLineText2SQLWorker 详解

```python
class BaseLineText2SQLWorker(Text2SQLWorkerBase):
    def __init__(
        self,
        db_connection_uri: str,
        generator: Text2SQLGeneratorBase,
        helper_model: Optional[Text2SQLGeneratorBase] = None,  # 额外：修正模型
        executor: Optional[BaseExecutor] = None,
        include_tables: Optional[list] = None,
        exclude_tables: Optional[list] = None,
        auto_filter_tables: Optional[bool] = False,  # 额外：自动表过滤
    ):
        super().__init__(...)
        self.corrector = helper_model        # 用于错误修正
        self.table_filer_worker = helper_model  # 用于表过滤
        self.auto_filter_tables = auto_filter_tables
    
    def filer_tables_from_schema(self, question: str, ...) -> dict:
        """使用 LLM 选择与问题相关的表"""
        
    def _create_prompt(self, question: str, ...) -> str:
        """构建包含 Schema、Few-shot 的 Prompt"""
        
    def run(self, question: str, ...) -> Text2SQLWorkerOutput:
        """主执行流程"""
        # 1. 直接执行 SQL（如果 question 是 `sql` 格式）
        # 2. 创建 Prompt
        # 3. 生成 SQL（带 execution_guided_decoding）
        # 4. 执行 SQL
        # 5. 错误修正（如果需要）
        
    def do_correction(self, question: str, result: dict, ...) -> str:
        """SQL 错误修正流程"""
```

**扩展功能**:
- `helper_model`: 用于表过滤和错误修正的辅助模型
- `auto_filter_tables`: 自动选择相关表，减少 Prompt 长度
- `execution_guided_decoding`: 基于执行反馈的解码策略

### 2.3 BaseLineAnalyserWorker 详解

```python
class BaseLineAnalyserWorker(AnalysisWorkerBase):
    def __init__(self, generator: Text2SQLGeneratorBase):
        self.generator = generator
    
    def run_chunkwise_analysis(
        self,
        question: str,
        input_dataframe: pd.DataFrame,
        chunk_size: Optional[int] = 20,
        max_chunks: Optional[int] = 20,
        ...
    ) -> tuple[str, str]:
        """分块分析：处理大数据集"""
        # 1. 将 DataFrame 分块
        # 2. 逐块分析
        # 3. 使用 Merger Prompt 汇总结果
        
    def analyse(self, question: str, input_dataframe: pd.DataFrame, ...) -> dict:
        """单块分析"""
        # 解析 Analysis 和 Reasoning 部分
        
    def run(self, question: str, input_dataframe: pd.DataFrame, ...) -> AnalyserWorkerOutput:
        """主入口：自动选择分块或直接分析"""
```

**扩展功能**:
- `run_chunkwise_analysis`: 处理大数据集，避免 Token 溢出
- 两阶段分析：分块分析 + 结果汇总

### 2.4 BaseLinePlotWorker 详解

```python
class BaseLinePlotWorker(ChartPlotWorkerBase):
    def __init__(
        self, 
        generator: Text2SQLGeneratorBase, 
        plot_tool: BasePlotTool  # 注入绘图工具
    ):
        self.generator = generator
        self.plot_tool = plot_tool
    
    def run(self, question: str, input_dataframe: pd.DataFrame, ...) -> ChartPlotWorkerOutput:
        # 1. 生成图表配置（JSON）
        # 2. 使用 plot_tool 渲染
        # 3. Base64 编码（如果 plot_image=True）
```

**扩展功能**:
- `plot_tool`: 可替换的绘图工具（matplotlib/plotly/altair）
- 配置化图表：LLM 生成配置，工具负责渲染

### 2.5 SimpleRouterWorker 详解

```python
class SimpleRouterWorker(RouterWorkerBase):
    def run(self, question: str, input_dataframe: Optional[pd.DataFrame]) -> RouterWorkerOutput:
        # 前缀匹配路由规则
        if question.startswith("/query"):
            route_to = "query"
        elif question.startswith("/analyse"):
            route_to = "analyse"
        elif question.startswith("/plot"):
            route_to = "plot"
        else:
            route_to = "followup"
        
        return RouterWorkerOutput(
            route_to=route_to,
            question=question,
            decision_reasoning="Simple routing based on question prefix"
        )
```

**设计特点**:
- 简单高效：O(1) 时间复杂度
- 可预测：相同输入总是相同输出

### 2.6 BaseLineFollowupWorker 详解

```python
class BaseLineFollowupWorker(WorkerBase):
    def __init__(self, generator: Text2SQLGeneratorBase):
        self.generator = generator
    
    def run(
        self,
        prev_output: ExitWorkerOutput,  # 依赖上一个输出
        db_schema: str,
        user_feedback: Optional[str] = None,
        ...
    ) -> FollowupWorkerOutput:
        # 根据 prev_output.route_taken 提取不同字段
        # 生成后续建议 (suggestion)
        # 建议替代路径 (alternative_route)
```

**设计特点**:
- 依赖完整的上一个输出（ExitWorkerOutput）
- 用于错误恢复和多轮对话

---

## 三、Pipeline 主控类

### 3.1 AgentBase - Pipeline 抽象基类

```python
class AgentBase(ABC):
    """Pipeline 主控基类
    
    职责:
    1. 管理会话历史 (AgentInteractionMemory)
    2. 定义统一调用接口 (__call__)
    3. 输出格式转换
    """
    def __init__(
        self,
        session_name: str,
        db_connection_uri: str,
        session_db_path: Optional[str] = None,
        route_worker_kwargs: Optional[dict] = None,
    ):
        self.session_name = session_name
        self.db_connection_uri = db_connection_uri
        # 每个 Agent 实例拥有独立的内存会话
        self.history = AgentInteractionMemory(
            session_name=session_name, 
            db_path=session_db_path
        )
        self.route_worker_kwargs = route_worker_kwargs
    
    @abstractmethod
    def run(
        self,
        question: str,
        input_dataframe: Optional[dict] = None,
        server_mode: Optional[bool] = False,
    ) -> Union[ExitWorkerOutput, AgentOutput]:
        """子类必须实现的执行逻辑"""
        raise NotImplementedError()
    
    def __call__(self, question, input_dataframe=None, server_mode=False):
        """统一调用入口
        
        自动处理:
        1. server_mode 配置
        2. 执行 run 方法
        3. 保存到历史记录
        4. 输出格式转换
        """
        output = self.run(question=question, input_dataframe=input_dataframe)
        self.history.push(output=output)  # 自动持久化
        if server_mode:
            output = self.convert_exit_output_to_agent_output(output)
        return output
```

### 3.2 BaseLineAgent - 具体实现

```python
class BaseLineAgent(AgentBase):
    """Baseline Pipeline 实现
    
    组合了四个 Worker:
    1. text2sql_worker: SQL 生成
    2. analysis_worker: 数据分析
    3. plotter_worker: 图表生成
    4. followup_worker: 后续处理
    
    加上 Router 决策
    """
    def __init__(
        self,
        session_name: str,
        db_connection_uri: str,
        specialized_model1: Text2SQLGeneratorBase,  # SQL 专用模型
        specialized_model2: Text2SQLGeneratorBase,  # 分析专用模型
        executor: BaseExecutor,
        plot_tool: BasePlotTool,
        ...
    ):
        super().__init__(...)
        # Worker 实例化
        self.text2sql_worker = BaseLineText2SQLWorker(...)
        self.analysis_worker = BaseLineAnalyserWorker(generator=specialized_model2)
        self.plotter_worker = BaseLinePlotWorker(generator=specialized_model2, plot_tool=plot_tool)
        self.followup_worker = BaseLineFollowupWorker(generator=specialized_model2)
        self.router = SimpleRouterWorker()
    
    def run(self, question: str, input_dataframe: Optional[pd.DataFrame] = None) -> ExitWorkerOutput:
        # 1. Router 决策
        # 2. 查找历史 DataFrame
        # 3. 执行对应 Worker
        # 4. 错误处理
        # 5. 返回 ExitWorkerOutput
```

---

## 四、数据模型 (Pydantic)

### 4.1 输出模型继承体系

```
BaseModel (Pydantic)
    │
    └── BaseWorkerOutput
            │
            ├── Text2SQLWorkerOutput
            │       ├── db_connection_uri: str
            │       ├── sql_string: str
            │       ├── sql_reasoning: Optional[str]
            │       ├── input_dataframe: Optional[Dict]
            │       └── output_dataframe: Optional[Dict]
            │
            ├── AnalyserWorkerOutput
            │       ├── analysis: str
            │       ├── input_dataframe: Optional[Dict]
            │       └── analysis_reasoning: Optional[str]
            │
            ├── ChartPlotWorkerOutput
            │       ├── input_dataframe: Optional[Dict]
            │       ├── plot_config: Optional[Dict]
            │       ├── image_plot: Optional[str]  # Base64
            │       └── plot_reasoning: Optional[str]
            │
            ├── RouterWorkerOutput
            │       ├── route_to: Literal["followup", "plot", "analyse", "query"]
            │       ├── input_dataframe: Optional[Dict]
            │       └── decision_reasoning: Optional[str]
            │
            └── FollowupWorkerOutput
                    ├── route_taken: Literal[...]
                    ├── suggestion: str
                    └── alternative_route: Optional[Literal[...]]

    └── ExitWorkerOutput (聚合所有 Worker 输出)
            ├── session_name: str
            ├── question: str
            ├── route_taken: Literal[...]
            ├── sql_string, sql_output_dataframe, error_from_sql_worker
            ├── analysis, error_from_analysis_worker
            ├── plot_config, image_to_plot, error_from_plot_worker
            └── followup_suggestion, followup_route_to_take

    └── AgentOutput (最终输出)
            ├── session_name, question, db_connection_uri, route_taken
            ├── input_dataframe, output_dataframe
            ├── sql_string, analysis, reasoning, plot_config, image_to_plot
            ├── followup_route, followup_suggestion
            └── error_from_pipeline
```

### 4.2 模型设计特点

| 特点 | 说明 |
|------|------|
| **统一基类** | BaseWorkerOutput 定义通用字段 (question, error_from_model, additional_input) |
| **类型安全** | 使用 Optional 和 Literal 精确约束字段类型 |
| **序列化友好** | DataFrame 存储为 Dict (含 data 和 columns)，便于 JSON 序列化 |
| **错误传播** | 每个 Worker 有独立的 error_from_xxx 字段 |
| **聚合输出** | ExitWorkerOutput 聚合所有 Worker 输出，是 Pipeline 的统一返回值 |

---

## 五、记忆管理类

### 5.1 AgentInteractionMemory

```python
class AgentInteractionMemory:
    """SQLite 持久化存储
    
    职责:
    1. 按 session_name 分表存储
    2. ExitWorkerOutput 序列化/反序列化
    3. 历史记录查询
    """
    def __init__(self, session_name: str, db_path: Optional[str] = None):
        self.session_name = session_name
        self.db_path = db_path or "premsql_pipeline_memory.db"
        self.conn = sqlite3.connect(self.db_path)
        self.create_table_if_not_exists()
    
    def create_table_if_not_exists(self):
        """按 session_name 创建表"""
        CREATE TABLE {session_name} (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            route_taken TEXT,
            sql_string TEXT,
            sql_output_dataframe TEXT,  -- JSON
            analysis TEXT,
            plot_config TEXT,           -- JSON
            image_to_plot TEXT,         -- Base64
            followup_suggestion TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    
    def push(self, output: ExitWorkerOutput):
        """存储记录"""
        
    def get(self, limit: Optional[int] = None) -> List[ExitWorkerOutput]:
        """查询历史"""
        
    def get_latest_dataframe(self, decision: str) -> dict:
        """获取最近可用的 DataFrame"""
```

---

## 六、设计模式应用

### 6.1 模板方法模式 (Template Method)

```python
# AgentBase 定义模板流程
class AgentBase(ABC):
    def __call__(self, question, ...):
        # 1. 前置处理 (server_mode 配置)
        # 2. 执行子类实现
        output = self.run(question=question, ...)
        # 3. 后置处理 (保存历史)
        self.history.push(output=output)
        # 4. 格式转换
        return output
    
    @abstractmethod
    def run(self, ...):
        """子类实现具体逻辑"""
```

### 6.2 策略模式 (Strategy)

```python
# Router 选择执行策略
class BaseLineAgent:
    def _execute_worker(self, route_to, ...):
        decision_mapping = {
            "query": lambda: self.text2sql_worker.run(...),
            "analyse": lambda: self.analysis_worker.run(...),
            "plot": lambda: self.plotter_worker.run(...),
        }
        return decision_mapping[route_to]()
```

### 6.3 依赖注入 (Dependency Injection)

```python
class BaseLineText2SQLWorker(Text2SQLWorkerBase):
    def __init__(self, generator: Text2SQLGeneratorBase, executor: BaseExecutor, ...):
        # 通过构造函数注入依赖
        self.generator = generator
        self.executor = executor

class BaseLinePlotWorker(ChartPlotWorkerBase):
    def __init__(self, generator: Text2SQLGeneratorBase, plot_tool: BasePlotTool):
        # plot_tool 可替换为不同实现
        self.plot_tool = plot_tool
```

### 6.4 工厂模式 (简单工厂)

```python
# initialize_database 是工厂方法
class Text2SQLWorkerBase:
    def initialize_database(self, db_connection_uri, ...) -> SQLDatabase:
        """创建 SQLDatabase 实例"""
        return SQLDatabase.from_uri(...)
```

---

## 七、类关系总结

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           BaseLineAgent                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │text2sql_worker│  │analysis_worker│  │plotter_worker│  │followup_worker││
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                 │                 │         │
│         ▼                 ▼                 ▼                 ▼         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │Text2SQLWorker│  │AnalysisWorker│  │ChartPlotWorker│  │   Worker     │ │
│  │    Base      │  │    Base      │  │    Base       │  │   Base       │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                                          │
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐ │
│  │    router    │──┤           SimpleRouterWorker                      │ │
│  └──────────────┘  └──────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌──────────────┐  ┌──────────────────────────────────────────────────┐ │
│  │   history    │──┤        AgentInteractionMemory                     │ │
│  └──────────────┘  └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ExitWorkerOutput (统一输出)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐    │
│  │SQL 相关字段  │ │Analysis 字段│ │ Plot 字段   │ │ Followup 字段   │    │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 八、扩展建议

### 8.1 添加新 Worker 的步骤

1. **定义输出模型** (继承 BaseWorkerOutput)
2. **定义抽象基类** (继承 WorkerBase)
3. **实现具体 Worker** (继承新基类)
4. **修改 Router** (添加新的路由规则)
5. **集成到 Agent** (在 BaseLineAgent 中添加 Worker 实例)

### 8.2 可优化的设计

| 优化点 | 当前实现 | 建议 |
|--------|---------|------|
| Worker 注册 | 硬编码在 Agent | 使用注册表模式 |
| 数据传递 | 通过历史记录隐式传递 | 显式传递 DataFrame 引用 |
| Router | 简单前缀匹配 | 支持 LLM-based Router |
| 并行执行 | 串行执行 | 支持 Worker 并行 |

---

*类图分析完成*
