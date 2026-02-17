# PremSQL Agent 架构深度分析

> **分析目标**: 理解 PremSQL 的 Pipeline 架构设计，为 AI 数据分析系统提供参考  
> **分析日期**: 2026-02-05  
> **代码版本**: 基于 premsql/agents/ 目录源码

---

## 一、Pipeline 架构总览

### 1.1 核心设计理念

PremSQL 采用 **"流水线(Pipeline) + 路由器(Router)"** 的架构模式，与 TaskWeaver 的 Planner-Executor 模式形成鲜明对比：

| 特性 | PremSQL Pipeline | TaskWeaver Planner |
|------|------------------|-------------------|
| 控制方式 | Router 前缀匹配决策 | LLM 规划决策 |
| 执行路径 | 预定义分支 (query/analyse/plot) | 动态代码生成 |
| 扩展性 | 继承 Worker 基类 | 修改 Planner 提示词 |
| 中间状态 | SQLite 持久化存储 | 内存中的变量 |

### 1.2 架构层次图

![PremSQL-Pipeline流程图.svg](graphviz/PremSQL-Pipeline流程图.svg)
![PremSQL-Router工作流程图.svg](graphviz/PremSQL-Router工作流程图.svg)
![PremSQL-Worker链式执行图.svg](graphviz/PremSQL-Worker链式执行图.svg)

```
┌─────────────────────────────────────────────────────────────┐
│                    用户交互层 (User Query)                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Router Worker (路由决策)                   │
│  • /query   → Text2SQL Worker                              │
│  • /analyse → Analysis Worker                              │
│  • /plot    → Plot Worker                                  │
│  • 其他      → Followup Worker                             │
└───────────────────────────┬─────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Text2SQL      │  │ Analysis      │  │ Plot          │
│ Worker        │  │ Worker        │  │ Worker        │
│               │  │               │  │               │
│ • NL→SQL生成  │  │ • 数据分析    │  │ • 图表生成    │
│ • SQL执行     │  │ • 分块处理    │  │ • 可视化配置  │
│ • 错误修正    │  │ • 结果汇总    │  │ • Base64输出  │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │
        └──────────┬───────┴──────────────────┘
                   ▼
┌─────────────────────────────────────────────────────────────┐
│              Exit Worker Output (统一输出格式)               │
│  • 输出数据框 (DataFrame)                                    │
│  • 执行路径记录 (route_taken)                                │
│  • 错误信息 (error_from_xxx)                                 │
│  • 后续建议 (followup_suggestion)                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│         Agent Interaction Memory (SQLite 持久化)             │
│  • 会话历史存储                                              │
│  • 数据框传递 (历史记录查找)                                  │
│  • 支持多轮对话                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、Worker 基类设计分析

### 2.1 Worker 抽象体系

```python
# 核心基类定义 (agents/base.py)

class WorkerBase(ABC):
    """最基础 Worker 接口 - 仅定义 run 方法"""
    @abstractmethod
    def run(self):
        return NotImplementedError()

class Text2SQLWorkerBase(ABC):
    """Text2SQL 专用 Worker 基类 - 带数据库初始化"""
    def __init__(self, db_connection_uri, generator, executor, ...):
        self.generator = generator      # SQL 生成模型
        self.executor = executor        # SQL 执行器
        self.db = self.initialize_database(...)  # LangChain SQLDatabase
    
    @abstractmethod
    def run(self, question: str, **kwargs) -> Text2SQLWorkerOutput:
        raise NotImplementedError

class AnalysisWorkerBase(ABC):
    """分析 Worker 基类 - 接收 DataFrame 输入"""
    @abstractmethod
    def run(self, question: str, input_dataframe: pd.DataFrame) -> AnalyserWorkerOutput:
        raise NotImplementedError

class ChartPlotWorkerBase(ABC):
    """绘图 Worker 基类 - 可视化输出"""
    @abstractmethod  
    def run(self, question: str, input_dataframe: pd.DataFrame) -> ChartPlotWorkerOutput:
        raise NotImplementedError

class RouterWorkerBase(ABC):
    """路由 Worker 基类 - 决策执行路径"""
    @abstractmethod
    def run(self, question: str, input_dataframe: pd.DataFrame) -> RouterWorkerOutput:
        raise NotImplementedError
```

### 2.2 设计亮点分析

| 设计特点 | 说明 | 优势 |
|---------|------|------|
| **按职责分层** | 每个基类对应特定任务类型 | 职责单一，易于测试 |
| **显式依赖注入** | generator/executor/plot_tool 通过构造函数传入 | 便于 Mock 测试和替换实现 |
| **标准化输出** | 每个 Worker 返回 Pydantic Model | 类型安全，序列化友好 |
| **数据库封装** | Text2SQLWorkerBase 内置数据库初始化 | 统一管理连接和 Schema |

### 2.3 AgentBase - Pipeline 主控基类

```python
class AgentBase(ABC):
    def __init__(self, session_name, db_connection_uri, ...):
        # 每个 Agent 实例拥有独立的内存会话
        self.history = AgentInteractionMemory(session_name=session_name, ...)
    
    def __call__(self, question, input_dataframe=None, server_mode=False):
        # 统一入口，自动处理历史记录存储
        output = self.run(question=question, input_dataframe=input_dataframe)
        self.history.push(output=output)  # 自动持久化
        return output
```

**关键特性**:
- 使用 `__call__` 作为统一调用入口
- 自动将会话历史推送到 SQLite
- 支持 `server_mode` 模式（不生成图片，返回 base64）

---

## 三、Router 路由决策机制

![PremSQL-Router工作流程图.svg](graphviz/PremSQL-Router工作流程图.svg)
![PremSQL-Worker链式执行图.svg](graphviz/PremSQL-Worker链式执行图.svg)

### 3.1 SimpleRouterWorker 实现

```python
class SimpleRouterWorker(RouterWorkerBase):
    def run(self, question: str, input_dataframe: Optional[pd.DataFrame]) -> RouterWorkerOutput:
        # 基于前缀的简单路由规则
        if question.startswith("/query"):
            route_to = "query"      # → Text2SQL Worker
        elif question.startswith("/analyse"):
            route_to = "analyse"    # → Analysis Worker
        elif question.startswith("/plot"):
            route_to = "plot"       # → Plot Worker
        else:
            route_to = "followup"   # → Followup Worker
        
        # 移除前缀，提取真实问题
        question = question.split(f"/{route_to}")[1] if route_to != "followup" else question
        
        return RouterWorkerOutput(
            route_to=route_to,
            question=question,
            decision_reasoning="Simple routing based on question prefix"
        )
```

### 3.2 路由决策对比分析

| 方案 | PremSQL (SimpleRouter) | TaskWeaver (Planner) |
|------|------------------------|---------------------|
| **决策机制** | 字符串前缀匹配 | LLM 生成执行计划 |
| **响应速度** | 极快 (O(1)) | 较慢 (需要 LLM 推理) |
| **灵活性** | 固定分支 | 可处理任意复杂任务 |
| **可预测性** | 高 | 中（受提示词影响） |
| **适用场景** | 标准化数据分析流程 | 开放式编程任务 |

### 3.3 Router 设计哲学

PremSQL 的 Router 体现 **"显式优于隐式"** 的设计原则：

1. **用户意图显式化**: 通过 `/query`、 `/analyse`、 `/plot` 前缀明确表达意图
2. **执行路径可预测**: 无 LLM 随机性，相同输入总是走相同路径
3. **错误定位容易**: 路由规则简单，问题易于排查

---

## 四、Pipeline 执行流程详解

### 4.1 主流程代码分析 (baseline/main.py)

```python
class BaseLineAgent(AgentBase):
    def run(self, question: str, input_dataframe: Optional[pd.DataFrame] = None) -> ExitWorkerOutput:
        # Step 1: Router 决策
        decision = self.router.run(question=question, input_dataframe=input_dataframe)
        
        # Step 2: 从历史记录查找可用的 DataFrame（用于 analyse/plot）
        dataframe_from_history = self._find_dataframe_from_history()
        
        # Step 3: 根据路由决策执行对应 Worker
        if decision.route_to in ["query", "analyse", "plot"]:
            worker_output = self._execute_worker(
                question=question,
                route_to=decision.route_to,
                input_dataframe=input_dataframe,
                dataframe_from_history=dataframe_from_history,
            )
            exit_output = self._create_exit_worker_output(...)
            
            # Step 4: 错误处理 → Followup Worker
            if exit_output 有错误:
                followup_output = self._handle_followup(exit_output)
                exit_output.followup_suggestion = followup_output.suggestion
        else:
            # Step 5: Followup 路由处理（多轮对话）
            exit_output = self._handle_followup_route(question=question)
        
        return exit_output
```

### 4.2 执行流程时序图

```
用户            Router          BaseLineAgent      Worker      Memory
 |                |                  |               |           |
 |---"/query..."->|                  |               |           |
 |                |---route_to------>|               |           |
 |                |                  |               |           |
 |                |                  |---检查历史---->|           |
 |                |                  |<--DataFrame----|           |
 |                |                  |               |           |
 |                |                  |---执行 Worker->|           |
 |                |                  |<--输出结果-----|           |
 |                |                  |               |           |
 |                |                  |---存储结果---------------->|
 |                |                  |<--确认-------|           |
 |<---------------输出结果-----------|               |           |
```

### 4.3 各 Worker 执行细节

#### Text2SQL Worker 流程

```python
class BaseLineText2SQLWorker(Text2SQLWorkerBase):
    def run(self, question, ...):
        # 1. 表过滤（可选）- 减少 Schema 长度
        if self.auto_filter_tables:
            to_include = self.filer_tables_from_schema(question)
        
        # 2. 构建 Prompt - 包含 Schema、Few-shot、问题
        prompt = self._create_prompt(question, ...)
        
        # 3. 生成 SQL - 使用 execution_guided_decoding
        generated_sql = self.generator.execution_guided_decoding(...)
        
        # 4. 执行 SQL
        result = execute_and_render_result(db=self.db, sql=generated_sql)
        
        # 5. 错误修正（如果失败）
        if result["error_from_model"]:
            generated_sql = self.do_correction(question, result, ...)
            result = execute_and_render_result(...)
        
        return Text2SQLWorkerOutput(
            sql_string=generated_sql,
            output_dataframe=result["dataframe"],
            ...
        )
```

**设计亮点**:
- `execution_guided_decoding`: 基于执行反馈的解码策略，SQL 执行失败时自动重试
- `do_correction`: 专门的错误修正流程，使用错误提示模板重新生成

#### Analysis Worker 流程

```python
class BaseLineAnalyserWorker(AnalysisWorkerBase):
    def run(self, question, input_dataframe, ...):
        # 支持分块分析（大数据集）
        if len(input_dataframe) > chunk_size and do_chunkwise_analysis:
            # 分块处理 + 结果汇总
            analysis, error = self.run_chunkwise_analysis(...)
        else:
            # 直接分析（截断到 chunk_size）
            analysis, error = self.analyse(...)
        
        return AnalyserWorkerOutput(analysis=analysis, ...)
```

**设计亮点**:
- **分块分析**: 处理大数据集时避免 Token 溢出
- **两阶段汇总**: 先分块分析，再使用 Merger Prompt 汇总结果

#### Plot Worker 流程

```python
class BaseLinePlotWorker(ChartPlotWorkerBase):
    def run(self, question, input_dataframe, ...):
        # 1. 生成图表配置（JSON 格式）
        prompt = prompt_template.format(columns=list(input_dataframe.columns), question=question)
        plot_config = self.generator.generate(...)
        plot_config = eval(plot_config.replace("null", "None"))
        
        # 2. 使用 PlotTool 生成图表
        fig = self.plot_tool.run(data=input_dataframe, plot_config=plot_config)
        
        # 3. 转换为 Base64（便于传输）
        if plot_image:
            output = self.plot_tool.convert_image_to_base64(...)
        
        return ChartPlotWorkerOutput(plot_config=plot_config, image_plot=output, ...)
```

---

## 五、中间结果传递机制

### 5.1 数据流转方式

PremSQL 采用 **"DataFrame 作为一等公民"** 的设计理念：

```
Text2SQL Worker              Analysis Worker              Plot Worker
     |                             |                            |
     |  output_dataframe           |                            |
     |  {"data": [...],            |  input_dataframe           |
     |   "columns": [...]}         |  (从历史加载)               |
     |---------------------------->|                            |
     |                             |                            |
     |                             |  (analysis 结果)           |
     |                             |---------------------------->
     |                             |                            |
     |                             |                   input_dataframe
     |                             |                   (从历史加载)
```

### 5.2 历史记录查找机制

```python
def _find_dataframe_from_history(self):
    # 从最近 10 条记录中查找有效 DataFrame
    history_entries = self.history.get(limit=10)
    for entry in history_entries:
        content = entry["message"]
        df = content.show_output_dataframe()  # 尝试获取输出数据框
        if df is not None and len(df) > 0:
            return df
    return None
```

### 5.3 ExitWorkerOutput - 统一输出格式

```python
class ExitWorkerOutput(BaseModel):
    # 基本信息
    session_name: str
    question: str
    route_taken: Literal["plot", "analyse", "query", "followup"]
    
    # Text2SQL 结果
    sql_string: Optional[str]
    sql_output_dataframe: Optional[Dict]
    error_from_sql_worker: Optional[str]
    
    # Analysis 结果
    analysis: Optional[str]
    analysis_input_dataframe: Optional[Dict]
    error_from_analysis_worker: Optional[str]
    
    # Plot 结果
    plot_config: Optional[Dict]
    image_to_plot: Optional[str]  # Base64
    error_from_plot_worker: Optional[str]
    
    # Followup 结果
    followup_suggestion: Optional[str]
    followup_route_to_take: Optional[str]
```

---

## 六、记忆管理机制

### 6.1 AgentInteractionMemory 架构

```python
class AgentInteractionMemory:
    def __init__(self, session_name: str, db_path: Optional[str] = None):
        self.session_name = session_name
        self.db_path = db_path or "premsql_pipeline_memory.db"
        self.conn = sqlite3.connect(self.db_path)
        self.create_table_if_not_exists()  # 按 session_name 建表
    
    def push(self, output: ExitWorkerOutput):
        # 将 ExitWorkerOutput 序列化存储
        cursor.execute("INSERT INTO {session_name} (...) VALUES (...)")
    
    def get(self, limit: Optional[int] = None) -> List[ExitWorkerOutput]:
        # 获取历史记录
```

### 6.2 数据库存储结构

```sql
CREATE TABLE {session_name} (
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT,
    route_taken TEXT,           -- 执行路径
    sql_string TEXT,            -- SQL
    sql_output_dataframe TEXT,  -- JSON 序列化的 DataFrame
    analysis TEXT,              -- 分析结果
    plot_config TEXT,           -- 图表配置
    image_to_plot TEXT,         -- Base64 图片
    followup_suggestion TEXT,   -- 后续建议
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

### 6.3 记忆设计特点

| 特性 | 实现方式 | 优势 |
|------|---------|------|
| **会话隔离** | 按 session_name 分表 | 数据隔离，易于清理 |
| **完整状态** | 存储完整的 ExitWorkerOutput | 可随时恢复对话上下文 |
| **自动持久化** | `__call__` 中自动 push | 不丢失任何交互 |
| **多轮对话** | Followup Worker 使用历史 | 支持追问和修正 |

---

## 七、扩展性分析

### 7.1 如何添加新 Worker

**步骤 1: 定义输出模型 (agents/models.py)**

```python
class NewWorkerOutput(BaseWorkerOutput):
    result: str
    metadata: Optional[Dict] = None
```

**步骤 2: 定义 Worker 基类 (agents/base.py)**

```python
class NewWorkerBase(ABC):
    @abstractmethod
    def run(self, question: str, input_dataframe: pd.DataFrame) -> NewWorkerOutput:
        raise NotImplementedError
```

**步骤 3: 实现具体 Worker (agents/baseline/workers/)**

```python
class BaseLineNewWorker(NewWorkerBase):
    def __init__(self, generator: Text2SQLGeneratorBase):
        self.generator = generator
    
    def run(self, question: str, input_dataframe: pd.DataFrame) -> NewWorkerOutput:
        # 实现业务逻辑
        return NewWorkerOutput(result=..., question=question)
```

**步骤 4: 修改 Router (agents/router.py)**

```python
class SimpleRouterWorker(RouterWorkerBase):
    def run(self, question: str, ...):
        if question.startswith("/newfeature"):
            route_to = "newfeature"
        # ...
```

**步骤 5: 集成到 Pipeline (agents/baseline/main.py)**

```python
class BaseLineAgent(AgentBase):
    def __init__(self, ...):
        self.new_worker = BaseLineNewWorker(generator=specialized_model2)
    
    def _execute_worker(self, ...):
        decision_mapping = {
            "newfeature": lambda: self.new_worker.run(...),
            # ...
        }
```

### 7.2 扩展示意图

```
                    ┌─────────────────┐
                    │  SimpleRouter   │
                    └────────┬────────┘
                             │
         ┌──────────┬────────┼────────┬──────────┐
         ▼          ▼        ▼        ▼          ▼
    ┌────────┐ ┌────────┐ ┌─────┐ ┌────────┐ ┌────────┐
    │ query  │ │analyse │ │plot │ │followup│ │  NEW   │  ← 新增 Worker
    │ Worker │ │ Worker │ │Worker│ │ Worker │ │ Worker │
    └────┬───┘ └────┬───┘ └──┬──┘ └───┬────┘ └───┬────┘
         │          │        │        │          │
         └──────────┴────────┴────────┴──────────┘
                             │
                    ┌────────▼────────┐
                    │ ExitWorkerOutput│
                    └─────────────────┘
```

---

## 八、优缺点总结

### 8.1 优点

| 优点 | 说明 |
|------|------|
| **架构清晰** | Worker + Router + Pipeline 三层结构，职责分明 |
| **类型安全** | 全链路使用 Pydantic Model，编译期类型检查 |
| **可测试性强** | 依赖注入设计，易于 Mock 和单元测试 |
| **持久化完善** | SQLite 存储完整对话历史，支持会话恢复 |
| **错误处理健壮** | 每个 Worker 有独立的错误处理和修正机制 |
| **大数据支持** | Analysis Worker 支持分块分析，避免 Token 溢出 |

### 8.2 缺点

| 缺点 | 说明 | 改进建议 |
|------|------|---------|
| **路由过于简单** | 前缀匹配无法处理复杂意图 | 引入 LLM-based Router 作为可选项 |
| **Worker 间耦合** | 通过历史记录隐式传递 DataFrame | 显式传递 DataFrame 引用 |
| **缺乏并行执行** | 各 Worker 串行执行 | 支持独立 Worker 并行 |
| **扩展门槛** | 添加 Worker 需要修改多处 | 提供 Worker 注册机制 |
| **错误恢复有限** | Followup 仅提供建议，不自动重试 | 自动重试机制 |

### 8.3 与 TaskWeaver 对比总结

| 维度 | PremSQL | TaskWeaver |
|------|---------|------------|
| **架构模式** | Pipeline (预定义流程) | Planner-Executor (动态规划) |
| **适用场景** | 标准化数据分析 | 开放式数据任务 |
| **用户交互** | 命令式 (/query) | 自然语言 |
| **可控性** | 高 | 中 |
| **灵活性** | 中 | 高 |
| **开发成本** | 低（固定流程） | 高（需要代码生成） |
| **执行安全** | 高（预定义代码） | 中（动态生成代码） |

---

## 九、对 AI 数据分析系统的启示

### 9.1 值得借鉴的设计

1. **Worker 基类体系**: 按职责抽象，依赖注入
2. **标准化输出模型**: Pydantic 定义，类型安全
3. **持久化记忆**: SQLite 存储，支持多轮对话
4. **错误修正机制**: Text2SQL 的自动重试和修正
5. **分块处理**: Analysis Worker 的大数据处理策略

### 9.2 需要改进的方面

1. **Router 智能化**: 结合 LLM 进行意图识别
2. **动态流水线**: 支持条件分支和循环
3. **Worker 热插拔**: 注册机制而非硬编码
4. **可视化监控**: Pipeline 执行过程可视化

---

## 附录：核心代码索引

| 文件 | 职责 | 关键类 |
|------|------|--------|
| `agents/base.py` | Worker 基类定义 | WorkerBase, Text2SQLWorkerBase, AgentBase |
| `agents/router.py` | 路由决策 | SimpleRouterWorker |
| `agents/baseline/main.py` | Pipeline 主流程 | BaseLineAgent |
| `agents/baseline/workers/text2sql.py` | SQL 生成 | BaseLineText2SQLWorker |
| `agents/baseline/workers/analyser.py` | 数据分析 | BaseLineAnalyserWorker |
| `agents/baseline/workers/plotter.py` | 图表生成 | BaseLinePlotWorker |
| `agents/baseline/workers/followup.py` | 后续处理 | BaseLineFollowupWorker |
| `agents/memory.py` | 记忆管理 | AgentInteractionMemory |
| `agents/models.py` | 数据模型 | ExitWorkerOutput, AgentOutput |

---

*分析完成，供架构设计参考*
