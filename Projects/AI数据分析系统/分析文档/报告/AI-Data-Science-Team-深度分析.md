# AI Data Science Team 深度分析

**项目名称**: AI Data Science Team  
**项目定位**: 专业数据科学Agent库 + AI Pipeline Studio可视化平台  
**Star/Fork**: 4.7k / 活跃社区  
**分析日期**: 2026-02-05  
**分析维度**: 前端架构、后端架构、Agent算法、ML能力

---

## 一、项目概述

### 1.1 核心价值主张

AI Data Science Team是**面向数据科学工作流的专业化Agent库**，其核心创新在于：

1. **专业Agent分工**: 针对数据科学各环节（清洗→特征工程→建模→评估）设计专用Agent
2. **H2O AutoML集成**: 开箱即用的机器学习AutoML能力
3. **AI Pipeline Studio**: 可视化Pipeline编排，支持人机协作
4. **MLflow集成**: 完整的实验跟踪和模型管理

### 1.2 与其他项目的差异

| 维度 | AI Data Science Team | Vanna | TaskWeaver | PandasAI |
|------|---------------------|-------|-----------|----------|
| **核心能力** | 完整ML工作流 | Text-to-SQL | Agent编排 | DataFrame操作 |
| **ML支持** |  H2O AutoML |  |  |  |
| **可视化** |  Pipeline Studio |  |  |  图表 |
| **AutoML** |  完整 |  |  |  |
| **目标用户** | 数据科学家 | 分析师 | 开发者 | 分析师 |

---

## 二、前端架构分析

### 2.1 技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **框架** | Streamlit | 1.28+ | Python-first Web框架 |
| **组件** | Streamlit Components | v1 | 自定义组件支持 |
| **可视化** | Plotly | 5.x | 图表渲染 |
| **状态管理** | Streamlit Session State | - | 内置状态管理 |
| **样式** | Streamlit Theming + Custom CSS | - | 主题+自定义样式 |

### 2.2 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Pipeline Studio                        │
│                     (Streamlit App)                          │
├─────────────────────────────────────────────────────────────┤
│  UI Layer                                                    │
│  ├── 侧边栏: 数据集管理 / Agent选择 / 参数配置               │
│  ├── 主工作区: Pipeline可视化编辑器                          │
│  ├── 底部面板: 代码预览 / 输出展示 / 日志                    │
│  └── 对话框: Agent交互 / 人工审核                            │
├─────────────────────────────────────────────────────────────┤
│  State Management                                            │
│  ├── st.session_state[\"datasets\"]         # 数据集状态     │
│  ├── st.session_state[\"pipeline_graph\"]   # Pipeline图     │
│  ├── st.session_state[\"agent_outputs\"]    # Agent输出      │
│  └── st.session_state[\"undo/redo_stack\"]  # 操作历史       │
├─────────────────────────────────────────────────────────────┤
│  Agent Integration                                           │
│  └── LangGraph Agents → Streamlit UI Bridge                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 核心组件详解

#### 2.3.1 Pipeline可视化编辑器

**功能**:
- 节点-边图可视化（使用Plotly或Streamlit-agraph）
- 拖拽式节点添加/连接
- 节点状态显示（等待→运行→完成→错误）
- 点击节点查看详情/编辑参数

**实现亮点**:
```python
# Pipeline状态持久化
PIPELINE_STUDIO_ARTIFACT_STORE_PATH = "pipeline_store/pipeline_studio_artifact_store.json"
PIPELINE_STUDIO_FLOW_LAYOUT_PATH = "pipeline_store/pipeline_studio_flow_layout.json"

# 撤销/重做功能
_pipeline_studio_undo_stack = []
_pipeline_studio_redo_stack = []
```

#### 2.3.2 Agent交互界面

**多Agent协调UI**:
```python
# Supervisor Agent状态显示
st.sidebar.markdown("###  Agent团队")
for agent_name, status in agent_statuses.items():
    st.sidebar.status(f"{agent_name}: {status}")

# Agent输出实时流式显示
st.chat_message("assistant").write_stream(agent_response_stream)
```

#### 2.3.3 人工审核(Human-in-the-loop)

**审核点设计**:
```python
# 代码审核弹窗
with st.dialog("Review Agent Code", width="large"):
    st.code(generated_code, language="python")
    col1, col2 = st.columns(2)
    if col1.button(" Approve"):
        approve_and_execute()
    if col2.button(" Edit"):
        show_code_editor()
```

### 2.4 前端优势与不足

| 优势 | 说明 |
|------|------|
| **快速开发** | Streamlit纯Python开发，无需前端技能 |
| **实时交互** | 组件级自动刷新，无需手动刷新页面 |
| **Session管理** | 内置session_state，状态管理简单 |
| **组件丰富** | 内置表格、图表、表单等常用组件 |

| 不足 | 说明 |
|------|------|
| **性能瓶颈** | 大数据量渲染会卡顿（>10万行） |
| **自定义受限** | 复杂自定义UI需要写React组件 |
| **布局僵硬** | 单列布局，复杂布局困难 |
| **无离线能力** | 强依赖Streamlit服务器 |

### 2.5 借鉴价值

**适合我们的场景**:
-  快速原型验证（MVP阶段）
-  数据科学工具（与Jupyter Notebook互补）
-  内部工具（不需要复杂UI定制）

**不适合的场景**:
-  面向C端消费者的产品（需要精致UI）
-  高频交互的实时应用（性能不够）

---

## 三、后端架构分析

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    AI Data Science Team                      │
│                    (Python Library)                          │
├─────────────────────────────────────────────────────────────┤
│  Multi-Agent Layer                                           │
│  └── Supervisor DS Team                                      │
│      ├── Data Loading Agent                                  │
│      ├── Data Cleaning Agent                                 │
│      ├── Data Wrangling Agent                                │
│      ├── Feature Engineering Agent                           │
│      ├── EDA Agent                                           │
│      ├── Visualization Agent                                 │
│      ├── H2O ML Agent                                        │
│      └── MLflow Tools Agent                                  │
├─────────────────────────────────────────────────────────────┤
│  Agent Template Layer                                        │
│  ├── BaseAgent (抽象基类)                                    │
│  ├── Coding Agent Graph (代码生成工作流)                     │
│  └── Human Review Nodes (人工审核节点)                       │
├─────────────────────────────────────────────────────────────┤
│  Tools Layer                                                 │
│  ├── H2O AutoML Integration                                  │
│  ├── MLflow Integration                                      │
│  ├── DataFrame Tools                                         │
│  └── SQL Database Tools                                      │
├─────────────────────────────────────────────────────────────┤
│  Infrastructure Layer                                        │
│  ├── LangGraph (Agent编排)                                   │
│  ├── LangChain (LLM抽象)                                     │
│  ├── Code Sandbox (代码沙箱)                                 │
│  └── Logging & Checkpointing                                 │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 核心模块详解

#### 3.2.1 Agent基类设计 (BaseAgent)

```python
class BaseAgent:
    """
    所有Agent的抽象基类，定义通用接口
    """
    def __init__(self, model, log=False, log_path=None, 
                 human_in_the_loop=False, checkpointer=None):
        self.model = model
        self.log = log
        self.log_path = log_path
        self.human_in_the_loop = human_in_the_loop
        self.checkpointer = checkpointer
        self.response = None
        
    def invoke_agent(self, **kwargs):
        """同步执行Agent"""
        self.response = self.compiled_graph.invoke(kwargs)
        return self.response
    
    def ainvoke_agent(self, **kwargs):
        """异步执行Agent"""
        return self.compiled_graph.ainvoke(kwargs)
    
    def update_params(self, **kwargs):
        """动态更新参数并重建图"""
        self._params.update(kwargs)
        self._build_graph()
```

**设计亮点**:
-  统一的Agent接口（所有Agent遵循相同契约）
-  参数热更新（无需重启即可调整配置）
-  检查点支持（状态持久化，支持恢复）

#### 3.2.2 Agent工作流模板 (LangGraph)

```python
def create_coding_agent_graph(agent_name, llm, system_prompt, 
                               human_in_the_loop=False):
    """
    创建标准的数据科学Agent工作流图
    """
    # 定义状态
    class AgentState(TypedDict):
        messages: Annotated[Sequence[BaseMessage], operator.add]
        code: str
        code_error: str
        data_raw: pd.DataFrame
        data_processed: pd.DataFrame
        response: dict
    
    # 定义节点
    def node_generate_code(state):
        """生成代码节点"""
        response = llm.invoke(system_prompt + state["messages"])
        code = extract_code(response.content)
        return {"code": code, "messages": [response]}
    
    def node_execute_code(state):
        """执行代码节点"""
        try:
            result = execute_sandboxed(state["code"], state["data_raw"])
            return {"data_processed": result, "code_error": ""}
        except Exception as e:
            return {"code_error": str(e)}
    
    def node_human_review(state):
        """人工审核节点"""
        if human_in_the_loop:
            return Command("human_review", resume={"action": "await"})
        return {"response": {"status": "approved"}}
    
    def node_fix_code(state):
        """修复代码节点"""
        error_prompt = f"Error: {state['code_error']}\nPlease fix the code."
        fixed = llm.invoke(error_prompt)
        return {"code": extract_code(fixed.content)}
    
    # 构建图
    builder = StateGraph(AgentState)
    builder.add_node("generate", node_generate_code)
    builder.add_node("execute", node_execute_code)
    builder.add_node("review", node_human_review)
    builder.add_node("fix", node_fix_code)
    
    # 定义边和条件路由
    builder.add_edge(START, "generate")
    builder.add_edge("generate", "execute")
    builder.add_conditional_edges(
        "execute",
        lambda s: "fix" if s["code_error"] else "review",
        {"fix": "fix", "review": "review"}
    )
    builder.add_edge("fix", "execute")  # 循环修复
    builder.add_edge("review", END)
    
    return builder.compile(checkpointer=checkpointer)
```

**设计亮点**:
-  标准化的代码生成→执行→审核→修复循环
-  LangGraph提供可视化调试能力（Mermaid图）
-  支持条件分支和循环（复杂工作流）

#### 3.2.3 H2O AutoML集成

```python
class H2OMLAgent(BaseAgent):
    """
    H2O AutoML Agent - 自动化机器学习
    """
    def invoke_agent(self, data_raw, target_variable, 
                     user_instructions="", max_runtime=60):
        # 1. 生成H2O代码
        code = self._generate_h2o_code(
            data_summary=data_raw.describe(),
            target=target_variable,
            instructions=user_instructions,
            max_runtime=max_runtime
        )
        
        # 2. 执行H2O AutoML
        result = execute_sandboxed(code, data_raw)
        
        # 3. 保存最佳模型
        if self.model_directory:
            save_h2o_model(result["best_model"], self.model_directory)
        
        # 4. MLflow记录（可选）
        if self.enable_mlflow:
            log_to_mlflow(result)
        
        return result
```

**AutoML流程**:
```
数据上传 → 自动特征工程 → 多算法训练 
    → Leaderboard排名 → 最佳模型保存 → MLflow记录
```

**支持的算法**:
- 随机森林 (DRF)
- 梯度提升机 (GBM)
- XGBoost
- 深度学习 (Deep Learning)
- 广义线性模型 (GLM)
- 朴素贝叶斯
- 自动特征工程

#### 3.2.4 MLflow集成

```python
class MLflowToolsAgent(BaseAgent):
    """
    MLflow工具Agent - 实验跟踪和模型管理
    """
    def __init__(self, mlflow_tracking_uri, experiment_name):
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.experiment_name = experiment_name
        mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
    
    def log_model(self, model, metrics, artifacts):
        with mlflow.start_run():
            # 记录参数
            mlflow.log_params(model.params)
            # 记录指标
            mlflow.log_metrics(metrics)
            # 记录模型
            mlflow.sklearn.log_model(model, "model")
            # 记录Artifact
            mlflow.log_artifacts(artifacts)
```

**MLflow能力**:
-  实验跟踪（参数、指标、模型）
-  模型版本管理（注册中心）
-  模型部署（REST API）
-  模型对比（可视化）

### 3.3 代码沙箱与安全

```python
# 代码执行沙箱
def run_code_sandboxed_subprocess(code, data, timeout=60):
    """
    在子进程中隔离执行代码
    """
    import subprocess
    import tempfile
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # 在子进程中执行，限制资源
        result = subprocess.run(
            ['python', temp_file],
            capture_output=True,
            text=True,
            timeout=timeout,
            # 可添加更多安全限制：
            # - 内存限制
            # - CPU限制
            # - 网络隔离
        )
        return result.stdout
    finally:
        os.unlink(temp_file)
```

**安全措施**:
-  子进程隔离
-  超时控制
-  临时文件自动清理
-  内存/CPU限制（可扩展）

### 3.4 后端优势与不足

| 优势 | 说明 |
|------|------|
| **专业分工** | 每个Agent专注特定数据科学任务 |
| **H2O集成** | 开箱即用的AutoML能力 |
| **LangGraph** | 可视化工作流，易于调试 |
| **检查点** | 支持状态持久化和恢复 |
| **人机协作** | 支持人工审核节点 |

| 不足 | 说明 |
|------|------|
| **Beta阶段** | API可能变动，生产使用需谨慎 |
| **资源消耗** | H2O AutoML需要较多内存 |
| **并发限制** | Streamlit + LangGraph并发处理能力有限 |

---

## 四、Agent算法分析

### 4.1 Multi-Agent架构

```
                    ┌─────────────────┐
                    │  Supervisor DS  │
                    │    协调Agent    │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼───────┐   ┌───────▼───────┐   ┌───────▼───────┐
│ Data Cleaning │   │  H2O ML       │   │ Visualization │
│    Agent      │   │   Agent       │   │    Agent      │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼───────┐
                    │  Shared State │
                    │  (DataFrame)  │
                    └───────────────┘
```

### 4.2 Agent协作模式

#### 模式1: Sequential Pipeline（顺序管道）

```python
# 数据清洗 → 特征工程 → 建模
def sequential_pipeline(data, target):
    # Step 1: 清洗
    cleaning_agent = DataCleaningAgent(llm)
    cleaning_agent.invoke_agent(data_raw=data)
    data_cleaned = cleaning_agent.get_data_cleaned()
    
    # Step 2: 特征工程
    feature_agent = FeatureEngineeringAgent(llm)
    feature_agent.invoke_agent(data_raw=data_cleaned)
    data_featured = feature_agent.get_data_engineered()
    
    # Step 3: 建模
    ml_agent = H2OMLAgent(llm)
    ml_agent.invoke_agent(data_raw=data_featured, target_variable=target)
    
    return ml_agent.get_best_model()
```

#### 模式2: Supervisor协调（动态规划）

```python
class SupervisorDSTeam:
    """
    Supervisor Agent根据任务动态选择和协调子Agent
    """
    def invoke(self, task_description, data):
        # 1. Supervisor分析任务
        plan = self.supervisor.plan(task_description)
        
        # 2. 按规划执行
        for step in plan.steps:
            agent = self.get_agent(step.agent_type)
            result = agent.execute(step.instruction, data)
            data = result.data  # 更新共享状态
            
        return data
```

### 4.3 核心Agent算法详解

#### 4.3.1 Data Cleaning Agent

**Prompt策略**:
```python
SYSTEM_PROMPT = """
You are a data cleaning expert. Given a dataset summary and user instructions,
generate a Python function to clean the data.

Default cleaning steps (unless user overrides):
1. Remove columns with >40% missing values
2. Impute numeric missing values with mean
3. Impute categorical missing values with mode
4. Convert to appropriate data types
5. Remove duplicate rows
6. Remove rows with missing values
7. Remove extreme outliers (>3x IQR)

Output format:
```python
def data_cleaner(df):
    # Your cleaning code here
    return df_cleaned
```

Dataset summary:
{data_summary}

User instructions:
{user_instructions}
"""
```

**算法流程**:
```
接收数据摘要 → 生成清洗代码 → 执行代码 → 返回清洗后数据
    ↑______________________________________|
         (如果出错，修复代码并重试)
```

#### 4.3.2 H2O ML Agent

**Prompt策略**:
```python
SYSTEM_PROMPT = """
You are an H2O AutoML expert. Generate code to train ML models.

Key requirements:
1. Import h2o and start H2O cluster
2. Convert pandas DataFrame to H2OFrame
3. Set up H2OAutoML with:
   - max_runtime_secs (user specified)
   - max_models (optional)
   - exclude_algos (optional)
   - nfolds for cross-validation
4. Train with target variable
5. Save leaderboard and best model
6. Shutdown H2O cluster

Output format:
```python
def h2o_automl(df, target):
    import h2o
    from h2o.automl import H2OAutoML
    
    h2o.init()
    hf = h2o.H2OFrame(df)
    
    aml = H2OAutoML(
        max_runtime_secs=60,
        nfolds=5,
        seed=42
    )
    aml.train(y=target, training_frame=hf)
    
    # Save results
    best_model = aml.leader
    leaderboard = aml.leaderboard
    
    h2o.shutdown()
    return best_model, leaderboard
```
"""
```

**支持的AutoML配置**:
| 参数 | 说明 | 默认值 |
|------|------|--------|
| max_runtime_secs | 最大运行时间 | 60 |
| max_models | 最大模型数 | None |
| exclude_algos | 排除算法 | [] |
| nfolds | 交叉验证折数 | 5 |
| balance_classes | 类别平衡 | False |

### 4.4 Human-in-the-loop设计

```python
def node_func_human_review(state: AgentState) -> Command:
    """
    人工审核节点 - 暂停执行等待用户输入
    """
    return Command(
        goto="human_review",
        update={
            "pending_review": True,
            "code_to_review": state["code"]
        },
        resume={
            "action": "await",  # 等待用户操作
            "timeout": 3600     # 1小时超时
        }
    )

# 用户审核后恢复执行
def resume_after_review(state: AgentState, human_response: dict):
    if human_response["action"] == "approve":
        return {"response": {"approved": True}}
    elif human_response["action"] == "edit":
        return {"code": human_response["edited_code"]}
    elif human_response["action"] == "reject":
        return {"response": {"approved": False, "reason": human_response["reason"]}}
```

**审核点设计**:
-  代码生成后审核
-  数据清洗结果审核
-  特征工程结果审核
-  模型训练参数审核

---

## 五、ML能力深度分析

### 5.1 H2O AutoML能力矩阵

| 能力 | 支持情况 | 说明 |
|------|---------|------|
| **分类** |  | 自动检测目标类型，二分类/多分类 |
| **回归** |  | 连续值预测 |
| **时间序列** | ⚠️ | 通过H2O-3的TimeSeries支持 |
| **特征工程** |  | 自动编码、标准化、特征选择 |
| **超参优化** |  | 网格搜索+随机搜索 |
| **集成学习** |  | Stacking Ensemble自动构建 |
| **模型解释** |  | SHAP值、PDP图、ICE图 |

### 5.2 算法覆盖

```
H2O AutoML算法栈:
├── 树模型
│   ├── Distributed Random Forest (DRF)
│   ├── Gradient Boosting Machine (GBM)
│   ├── XGBoost
│   └── LightGBM (通过扩展)
├── 深度学习
│   └── Deep Learning (多层感知机)
├── 线性模型
│   ├── Generalized Linear Model (GLM)
│   └── Elastic Net
└── 其他
    ├── Naive Bayes
    └── Stacked Ensemble (自动集成)
```

### 5.3 MLflow实验管理

```python
# 完整的ML工作流跟踪
with mlflow.start_run(run_name="H2O_AutoML_Churn"):
    # 记录数据集信息
    mlflow.log_param("dataset", "churn_data.csv")
    mlflow.log_param("n_rows", len(df))
    mlflow.log_param("n_features", len(df.columns))
    
    # 记录AutoML配置
    mlflow.log_params({
        "max_runtime_secs": 60,
        "nfolds": 5,
        "exclude_algos": ["DeepLearning"]
    })
    
    # 训练并记录指标
    aml.train(y=target, training_frame=hf)
    mlflow.log_metric("auc", aml.leader.auc())
    mlflow.log_metric("logloss", aml.leader.logloss())
    
    # 记录模型
    mlflow.h2o.log_model(aml.leader, "h2o_model")
    
    # 记录Artifact
    mlflow.log_artifact("leaderboard.html")
```

---

## 六、总结与借鉴建议

### 6.1 核心优势总结

| 维度 | 优势 | 评分 |
|------|------|------|
| **ML能力** | H2O AutoML开箱即用，算法覆盖全面 | ⭐⭐⭐⭐⭐ |
| **Agent设计** | 专业分工清晰，Supervisor协调模式 | ⭐⭐⭐⭐⭐ |
| **工作流** | LangGraph可视化Pipeline | ⭐⭐⭐⭐ |
| **实验管理** | MLflow完整集成 | ⭐⭐⭐⭐⭐ |
| **人机协作** | 审核点设计完善 | ⭐⭐⭐⭐ |

### 6.2 适用场景

** 适合**:
- 数据科学团队内部工具
- 自动化ML实验平台
- 教学/培训场景
- 快速原型验证

** 不适合**:
- 面向C端消费者的产品（UI不够精致）
- 高并发在线服务（性能限制）
- 生产级稳定性要求（Beta阶段）

### 6.3 借鉴建议

#### 可复用的组件

| 组件 | 文件路径 | 复用价值 |
|------|---------|---------|
| **BaseAgent** | `templates/agent_templates.py` | Agent基类设计模式 |
| **Coding Agent Graph** | `templates/agent_templates.py` | 代码生成执行工作流 |
| **H2O Integration** | `ml_agents/h2o_ml_agent.py` | AutoML集成方案 |
| **MLflow Tools** | `ml_agents/mlflow_tools_agent.py` | 实验跟踪集成 |
| **Code Sandbox** | `utils/sandbox.py` | 代码安全执行 |

#### 应用到我们的项目

**短期（MVP）**:
1. 参考BaseAgent设计我们的Agent基类
2. 使用LangGraph构建可视化工作流
3. 集成H2O AutoML提供预测能力

**中期**:
1. 添加MLflow实验跟踪
2. 实现Human-in-the-loop审核点
3. 构建Pipeline可视化编辑器

**长期**:
1. 将Streamlit前端替换为React（性能考虑）
2. 自建模型训练能力（不仅依赖H2O）
3. 多租户权限管理

### 6.4 风险提示

| 风险 | 说明 | 缓解措施 |
|------|------|---------|
| **Beta稳定性** | API可能变动 | 锁定版本，封装适配层 |
| **H2O资源** | AutoML内存消耗大 | 限制max_runtime，资源监控 |
| **LLM成本** | 多Agent调用Token多 | 缓存Prompt，使用小模型 |
| **Streamlit性能** | 大数据量卡顿 | 分页加载，后端预处理 |

---

## 七、关键代码片段

### 7.1 创建一个自定义Agent

```python
from ai_data_science_team.templates import BaseAgent, create_coding_agent_graph

class MyCustomAgent(BaseAgent):
    def __init__(self, model, **kwargs):
        super().__init__(model, **kwargs)
        self.system_prompt = """Your system prompt here..."""
        self._build_graph()
    
    def _build_graph(self):
        self.compiled_graph = create_coding_agent_graph(
            agent_name="my_agent",
            llm=self.model,
            system_prompt=self.system_prompt,
            human_in_the_loop=self.human_in_the_loop
        )
    
    def invoke_agent(self, data_raw, user_instructions=""):
        return self.compiled_graph.invoke({
            "data_raw": data_raw,
            "messages": [HumanMessage(content=user_instructions)]
        })
```

### 7.2 使用Supervisor协调多Agent

```python
from ai_data_science_team.multiagents import make_supervisor_ds_team

team = make_supervisor_ds_team(
    model=llm,
    agents=["data_cleaning", "feature_engineering", "h2o_ml"],
    human_in_the_loop=True
)

result = team.invoke({
    "task": "Clean the data and train a model to predict churn",
    "data": df,
    "target": "churn"
})
```

---

**报告完成** | 本报告基于项目源码和文档分析生成
