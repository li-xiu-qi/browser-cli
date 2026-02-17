---
title: AIASys Agent 系统深度分析
description: Host-Worker 双 Agent 架构设计与压缩机制详解
created: 2026-02-06
tags: [AIASys, Agent架构, smolagents, 上下文压缩]
---

# AIASys Agent 系统深度分析

## 1. 架构总览

AIASys 采用 Host-Worker 双 Agent 架构，在 [[smolagents]] 基础上进行了深度定制和扩展。

### 相关图表

| 图表 | 文件 |
|------|------|
| Host-Worker 架构图 | ![[aiasys-HostWorker架构图.svg]] |
| 压缩机制流程图 | ![[aiasys-压缩机制流程图.svg]] |
| Agent 工具链图 | ![[aiasys-Agent工具链图.svg]] |

### 1.1 核心架构图

```
用户请求 → Host Agent → Worker Agent → Jupyter Kernel
              ↓              ↓
         任务分配      代码执行
              ↓              ↓
         对话管理      数据分析
              ↓              ↓
         结果整合      可视化输出
```

### 1.2 架构特点

| 层级 | 组件 | 职责 | 基类 |
|------|------|------|------|
| 协调层 | Host Agent | 任务分配、对话管理、结果整合 | CompressedToolCallingAgent |
| 执行层 | Worker Agent | 代码生成、数据分析、可视化 | CompressedCodeAgent |
| 运行层 | Jupyter Kernel | Python 代码执行、环境管理 | MultiKernelInterpreterManager |
| 工具层 | Tool System | 文件操作、文档处理、Notebook 管理 | smolagents Tool |

### 1.3 数据流向

1. 用户输入通过 [[DataAnalysisTeam]] 进入 Host Agent
2. Host Agent 分析意图，决定自行处理或分发给 Worker Agent
3. Worker Agent 调用 Jupyter Executor 执行 Python 代码
4. 执行结果返回 Host Agent 进行整合和润色
5. 最终结果返回给用户

---

## 2. Host Agent 分析

### 2.1 职责定位

Host Agent 是数据分析团队的主持人，承担以下核心职责：

- 理解用户需求和意图
- 简单任务自行调用工具完成
- 复杂任务拆解并分发给 Worker Agent
- 对 Worker 的输出结果进行整合和润色
- 管理对话上下文和记忆

### 2.2 实现方式

Host Agent 基于 [[CompressedToolCallingAgent]] 实现，继承自 smolagents 的 [[ToolCallingAgent]]。

```python
class CompressedToolCallingAgent(ToolCallingAgent):
    """在 write_memory_to_messages 中对历史步骤进行 LLM 压缩"""
    
    def __init__(
        self,
        keep_recent_steps: int = 10,
        compression_threshold: int = 15,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.keep_recent_steps = keep_recent_steps
        self.compression_threshold = compression_threshold
```

### 2.3 Host 专业指令

Host Agent 拥有专门的行为指导指令，定义在 [[team.py]] 中的 `HOST_INSTRUCTIONS`：

```python
HOST_INSTRUCTIONS = """你是一个精干的数据分析团队主持人。

你的优势：
1. 理解用户的需求和意图
2. 简单任务你可以自己调用工具完成，不分配给下属专家
3. 拆解复杂任务，分配给下属专家 managed_agents 完成
4. 高效调度下属专家，确保任务按时高质量完成
5. 对专家的输出结果进行整合和润色

指导：
1. 第一个工具优先使用 list_workspace_files 确认可用文件
2. 使用 thought 进行深度逻辑分析和任务拆解
3. 使用 final_answer 提供正式回复
"""
```

### 2.4 Worker 管理

Host Agent 通过 smolagents 的 `managed_agents` 机制管理 Worker：

```python
# DataAnalysisTeam 初始化时构建 managed_agents
managed_agents = [self.worker]

# Host 创建时传入 managed_agents
self.host = CompressedToolCallingAgent(
    model=self.model,
    tools=host_tools,
    managed_agents=managed_agents,  # Worker 作为被管理 Agent
    name="data_analysis_host",
    description="数据分析主持人，负责与用户交流，拆解需求，调度下属 agent",
)
```

### 2.5 调用机制

当 Host Agent 需要将任务分配给 Worker 时，实际上是通过 smolagents 的 Agent 调用协议：

1. Host Agent 生成工具调用请求，目标为 Worker Agent
2. smolagents 内部处理 Agent 间调用
3. Worker Agent 在独立上下文中执行任务
4. Worker 返回结果后，Host 继续后续处理

---

## 3. Worker Agent 分析

### 3.1 职责定位

Worker Agent 是专业的数据分析执行者，职责包括：

- 编写 Python 代码进行数据清洗
- 执行数据分析和统计计算
- 生成可视化图表
- 在 Jupyter 环境中运行代码

### 3.2 实现方式

Worker Agent 基于 [[CompressedCodeAgent]] 实现，继承自 smolagents 的 [[CodeAgent]]。

```python
class CompressedCodeAgent(CodeAgent):
    """使用 CompactionManager 进行上下文压缩的 CodeAgent
    
    适用于 Worker 角色，防止代码执行日志撑爆上下文
    """
    
    def __init__(
        self,
        compaction_config: Optional[CompactionConfig] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        config = compaction_config or CompactionConfig()
        self.compaction_manager = CompactionManager(
            model=self.model,
            config=config,
        )
```

### 3.3 Worker 专业指令

```python
WORKER_INSTRUCTIONS = """你是一个专业的数据分析专家，负责在 Jupyter Notebook 环境中编写执行代码。

禁止：
1. 绝对禁止在代码中包含任何与自我意识、决策过程相关的内容
2. 绝对禁止在代码中包含任何与用户对话相关的内容
3. 禁止修改现有文件
4. 禁止安装任何新的库

你的职责只有在 Jupyter Notebook 环境编写和执行 Python 代码来完成数据分析任务。

你的优势：
1. 熟练使用 pandas、numpy、matplotlib、seaborn 等数据分析和可视化库
2. 能够高效地处理数据清洗、转换、分析和可视化任务
3. 能够根据需求生成高质量的图表和报告
"""
```

### 3.4 Jupyter 执行器绑定

Worker Agent 的核心特性是与 Jupyter 执行器深度绑定：

```python
# DataAnalysisTeam 初始化 Worker 时
self.worker = CompressedCodeAgent(
    model=self.model,
    tools=worker_tools,
    name="data_analysis_worker",
    description="能够编写 Python 代码进行数据清洗、分析和可视化的专家",
    executor=self.executor,  # JupyterExecutorAdapter
    additional_authorized_imports=self.executor.authorized_imports,
    instructions=worker_instructions,
    step_callbacks=[persistent_worker_callback],
    stream_outputs=True,
    code_block_tags="markdown",
    compaction_config=config,
)
```

---

## 4. 压缩 Agent 机制

### 4.1 三层压缩架构

AIASys 实现了业界领先的三层上下文压缩机制：

| 层级 | 名称 | 触发条件 | 执行方式 | 功能 |
|------|------|----------|----------|------|
| L1 | Microcompaction | 每次 write_memory_to_messages | 原地修改 | 截断旧 observations |
| L2 | Auto-compaction | Token 超过阈值 | 重建 memory | 生成结构化摘要 |
| L3 | Manual compact | 用户/API 手动触发 | 重建 memory | 深度压缩，支持聚焦 |

### 4.2 压缩流程图

```
write_memory_to_messages 调用
           ↓
    执行 Microcompaction
           ↓
    检查 Token 阈值
           ↓
    ┌─────────────┴─────────────┐
    ↓                           ↓
 未超过阈值                   超过阈值
    ↓                           ↓
 直接返回消息              执行 Auto-compaction
    ↓                           ↓
                         生成结构化摘要
                                 ↓
                         重建 AgentMemory
                                 ↓
                         返回压缩后的消息
```

### 4.3 Microcompaction 实现

Microcompaction 是轻量级的原地压缩，直接修改 memory.steps：

```python
def microcompact(self, memory: "AgentMemory") -> None:
    """微压缩：截断旧步骤的 observations"""
    steps = memory.steps
    tool_steps = [
        (i, step) for i, step in enumerate(steps)
        if isinstance(step, ActionStep) and self._has_tool_results(step)
    ]
    
    # 保留最近 N 个工具结果完整
    keep_recent = {i for i, _ in tool_steps[-self.config.tool_results_keep_recent:]}
    
    # 对旧步骤执行截断
    for i, step in enumerate(steps):
        age = len(steps) - 1 - i
        if age >= self.config.microcompact_full_steps:
            if step.observations and len(step.observations) > limit:
                step.observations = self._truncate_content(
                    step.observations, max_length=limit
                )
```

### 4.4 Auto-compaction 实现

Auto-compaction 在 Token 超过阈值时触发，生成结构化摘要：

```python
def auto_compact(self, memory: "AgentMemory") -> "AgentMemory":
    """自动压缩：达到阈值时生成结构化摘要"""
    steps = memory.steps
    
    # 分离最近步骤和待摘要步骤
    keep_count = self.config.microcompact_full_steps
    recent_steps = steps[-keep_count:]
    steps_to_summarize = steps[:-keep_count]
    
    # 增量压缩：只压缩新增步骤
    new_steps_to_compress = steps_to_summarize[self._summary_covers_up_to:]
    
    # 生成摘要
    summary_content = self._generate_incremental_summary(
        self._cached_summary,
        new_steps_to_compress,
        original_task,
    )
    
    # 重建 memory
    new_memory = AgentMemory(system_prompt=memory.system_prompt.system_prompt)
    new_memory.steps.append(summary_step)
    new_memory.steps.append(continuation_step)
    new_memory.steps.extend(recent_steps)
    
    return new_memory
```

### 4.5 结构化摘要格式

压缩后的摘要采用 9 段式结构化格式：

```markdown
## 用户需求记录
- [按时间顺序列出用户提出的所有需求/问题]

## 已完成操作及结果
- [操作1]: [具体结果]
- [操作2]: [具体结果]

## 重要文件/数据
- [如有生成的文件路径或关键数据，列在此处]

## 当前状态
- [当前任务的进展状态]

## 待办事项
- [尚未完成的任务]

## 关键发现
- [数据分析中的重要发现]

## 图表/可视化
- [生成的图表列表]

## 错误/异常
- [执行过程中遇到的问题]

## 下一步建议
- [建议的后续操作]
```

### 4.6 压缩配置参数

```python
@dataclass
class CompactionConfig:
    max_context_tokens: int = 128000        # 模型最大上下文窗口
    output_reserve_tokens: int = 32000      # 预留给输出的 token 数
    safety_buffer_tokens: int = 13000       # 安全缓冲区
    auto_compact_threshold: float = 0.78    # 触发阈值：可用上下文的 78%
    microcompact_full_steps: int = 3        # 保留完整的最近 N 步
    microcompact_observation_limit: int = 2000  # 旧 observations 截断长度
    enable_disk_offload: bool = True        # 启用磁盘卸载
    tool_results_budget_tokens: int = 40000 # 工具输出总预算
    summary_max_tokens: int = 4000          # 摘要最大 token 数
```

### 4.7 Token 估算器

使用 LiteLLM 的 token_counter 进行真实计数：

```python
from litellm import token_counter

class TokenEstimator:
    def _count_with_fallback(self, text: str) -> int:
        try:
            return int(token_counter(model=self._model_id, text=text))
        except Exception:
            return int(len(text) / self.chars_per_token)  # 回退到字符估算
```

---

## 5. Agent 间通信

### 5.1 调用协议

Host Agent 调用 Worker Agent 遵循 smolagents 的 Managed Agent 协议：

```python
# Host 中声明 managed_agents
self.host = CompressedToolCallingAgent(
    managed_agents=[self.worker],  # Worker 作为被管理 Agent
)

# Host 通过工具调用的方式使用 Worker
# 实际上是在内部转换为对 Worker.run 的调用
```

### 5.2 流式通信机制

为了实现 Worker 执行过程的实时透传，AIASys 设计了队列+线程的流式机制：

```python
def stream(self, task: str) -> Generator[Any, None, None]:
    # 创建局部队列
    event_queue = queue.Queue()
    self._current_event_queue = event_queue
    
    def run_host_thread():
        # Host 执行时，Worker 的回调会将步骤放入队列
        for step in self.host.run(task, reset=False, stream=True):
            event_queue.put((self.host.name, step))
        event_queue.put(None)  # 结束信号
    
    # 启动 Host 线程
    thread = threading.Thread(target=run_host_thread)
    thread.start()
    
    # 消费队列，透传事件
    while True:
        event = event_queue.get(timeout=300)
        if event is None:
            break
        yield event
```

### 5.3 Worker 回调注册

Worker 的步骤通过 callback 机制上报：

```python
def persistent_worker_callback(step: MemoryStep, **kwargs):
    if self._current_event_queue:
        # 显式包装为：来源名称, 步骤对象
        self._current_event_queue.put((self.worker.name, step))

# Worker 初始化时注册 callback
self.worker = CompressedCodeAgent(
    step_callbacks=[persistent_worker_callback],
)
```

### 5.4 错误处理

| 错误类型 | 处理方式 | 说明 |
|----------|----------|------|
| Worker 执行错误 | 返回错误信息给 Host | Host 决定是否重试或终止 |
| 超时错误 | 队列获取超时 5 分钟 | 返回超时提示 |
| Kernel 崩溃 | 自动重启或报错 | 由 KernelManager 处理 |
| 代码验证失败 | 抛出 InterpreterError | 阻止危险代码执行 |

### 5.5 超时控制

```python
try:
    event = event_queue.get(timeout=300)  # 5分钟超时
except queue.Empty:
    yield "执行超时，无响应"
    break
```

---

## 6. 与 smolagents 多 Agent 对比

### 6.1 smolagents 的 Manager-Managed 架构

smolagents 原生支持多 Agent 架构：

```python
from smolagents import CodeAgent, ToolCallingAgent, HfApiModel

# 创建被管理的 CodeAgent
code_agent = CodeAgent(
    tools=[],
    model=HfApiModel(),
    name="code_executor",
    description="执行 Python 代码"
)

# 创建管理 Agent，传入 managed_agents
manager_agent = ToolCallingAgent(
    tools=[],
    model=HfApiModel(),
    managed_agents=[code_agent],  # 管理其他 Agent
)
```

### 6.2 AIASys 的 Host-Worker 架构

AIASys 对 smolagents 架构进行了专业化改造：

```python
# AIASys 专业化封装
class DataAnalysisTeam:
    def __init__(self, session_id: str):
        # 创建 Worker（压缩版 CodeAgent）
        self.worker = CompressedCodeAgent(
            executor=JupyterExecutorAdapter(session_id),
            name="data_analysis_worker",
        )
        
        # 创建 Host（压缩版 ToolCallingAgent）
        self.host = CompressedToolCallingAgent(
            managed_agents=[self.worker],
            name="data_analysis_host",
        )
```

### 6.3 设计差异对比

| 特性 | smolagents 原生 | AIASys 实现 |
|------|-----------------|-------------|
| Agent 类型 | 通用 | 专业化 Host-Worker |
| 上下文压缩 | 无 | 三层压缩机制 |
| 代码执行 | 本地 Python | Jupyter Kernel |
| 流式输出 | 基础支持 | 完整队列+线程机制 |
| 记忆管理 | 基础 Memory | 持久化 + 压缩 + 恢复 |
| 工具系统 | 通用 Tool | 专业化数据分析工具 |
| 会话管理 | 无 | SessionManager 完整支持 |

### 6.4 选型理由

AIASys 选择定制化 Host-Worker 架构而非使用 smolagents 原生多 Agent 的原因：

1. **上下文压缩需求**：数据分析任务产生大量代码执行日志，需要专门的压缩机制
2. **Jupyter 集成**：需要与 Jupyter Kernel 深度集成，而非本地 Python 执行
3. **流式输出要求**：工业场景需要实时看到执行过程，不能等待全部完成
4. **会话持久化**：用户会话需要长期保持和恢复
5. **专业化分工**：Host 专注对话协调，Worker 专注代码执行，职责更清晰

---

## 7. Agent 工具系统

### 7.1 工具注册机制

AIASys 采用工厂模式创建会话绑定的工具：

```python
# workspace 工具工厂
def create_workspace_tools(session_id: str, user_id: Optional[str] = None):
    @tool
    def list_workspace_files() -> str:
        """获取当前会话工作区中的所有文件列表"""
        files = _list_workspace_files(session_id, user_id=user_id)
        return json.dumps({"files": files})
    
    @tool
    def create_folder(folder_name: str) -> str:
        """在当前会话工作区中创建新文件夹"""
        # 实现...
    
    return [list_workspace_files, create_folder]
```

### 7.2 工具分类

| 类别 | 工具 | 用途 | 可用 Agent |
|------|------|------|------------|
| 工作区 | list_workspace_files | 列出工作区文件 | Host + Worker |
| 工作区 | create_folder | 创建文件夹 | Host + Worker |
| 文档 | list_documents | 列出文档 | Host |
| 文档 | read_document | 读取文档内容 | Host |
| 文档 | read_document_pages | 分页读取 | Host |
| 文档 | search_document | BM25 检索 | Host |
| Notebook | replay_notebook | 重跑 Notebook | Worker |
| Notebook | list_notebook_cells | 列出代码单元 | Worker |
| Notebook | get_notebook_variables | 查看变量 | Worker |
| Skill | list_available_skills | 列出技能 | Worker |
| Skill | activate_skill | 激活技能 | Worker |

### 7.3 工具调用流程

```
Agent 决策 → 生成工具调用 → Tool Collection 分发 → 工具执行 → 结果返回 → 进入 Observation
```

### 7.4 Jupyter 作为执行工具

Jupyter Kernel 被设计为 Worker Agent 的核心执行后端：

```python
class JupyterExecutorAdapter(PythonExecutor):
    """将 JupyterKernelInterpreter 适配为 smolagents 的 PythonExecutor"""
    
    def __call__(self, code_action: str) -> CodeOutput:
        # 1. 环境准备与验证
        # 2. 发送执行请求
        msg_id = client.execute(code_action)
        # 3. 轮询消息并收集结果
        # 4. 返回 CodeOutput
```

### 7.5 自定义工具实现示例

```python
from smolagents import tool

@tool
def analyze_dataframe_columns(df_json: str) -> str:
    """
    分析 DataFrame 的列统计信息
    
    Args:
        df_json: DataFrame 的 JSON 字符串
        
    Returns:
        每列的数据类型、缺失值比例、统计摘要
    """
    import pandas as pd
    df = pd.read_json(df_json)
    
    result = {
        "columns": df.dtypes.to_dict(),
        "missing_ratio": (df.isnull().sum() / len(df)).to_dict(),
        "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
    }
    return json.dumps(result, ensure_ascii=False)
```

---

## 8. Agent 记忆管理

### 8.1 记忆结构

Agent 记忆采用 smolagents 的 `AgentMemory` 结构：

```python
class AgentMemory:
    system_prompt: SystemPromptStep  # 系统提示词
    steps: List[MemoryStep]          # 执行步骤历史
```

### 8.2 记忆步骤类型

| 步骤类型 | 用途 | 来源 |
|----------|------|------|
| TaskStep | 用户任务输入 | smolagents |
| ActionStep | 工具/代码执行 | smolagents |
| PlanningStep | 计划生成 | smolagents |
| FinalAnswerStep | 最终答案 | smolagents |
| SummaryStep | 压缩摘要 | AIASys 扩展 |
| ContinuationStep | 继续指令 | AIASys 扩展 |

### 8.3 记忆持久化

通过 SessionManager 实现记忆的保存和加载：

```python
def save_memory(self, task_prompt: str = None, final_answer: str = None):
    """保存当前会话的记忆状态"""
    new_host_steps = self.host.memory.steps[self.host_step_offset:]
    new_worker_steps = self.worker.memory.steps[self.worker_step_offset:]
    
    agent_steps_map = {
        "host": new_host_steps,
        "worker": new_worker_steps,
    }
    
    self.session_manager.save_smol_steps(
        self.session_id,
        agent_steps_map,
        user_id=self.user_id,
    )

def _load_memory(self):
    """从 SessionManager 加载历史记录"""
    history_steps = self.session_manager.load_smol_steps(
        self.session_id, user_id=self.user_id, agent_role="host"
    )
    if history_steps:
        self.host.memory.steps.extend(history_steps)
```

### 8.4 上下文压缩

详细压缩机制见第 4 章，核心思想：

1. **微压缩**：每次写入消息前截断旧 observations
2. **自动压缩**：Token 超过阈值时生成结构化摘要
3. **手动压缩**：用户可主动触发深度压缩

### 8.5 多轮对话管理

```python
# 初始化时加载历史
self._load_memory()

# 运行任务（不重置记忆）
result = self.host.run(task, reset=False)

# 任务完成后保存新增步骤
self.save_memory()
```

---

## 9. 工业场景适配

### 9.1 设备数据分析专用工具

针对工业数据分析场景，AIASys 提供专业化工具集：

```python
# 设备数据读取工具
@tool
def read_device_data(file_path: str, device_id: str) -> str:
    """
    读取工业设备传感器数据
    
    支持格式：CSV、Parquet、HDF5
    自动识别时间戳列和传感器通道
    """
    # 实现...

# 振动分析工具
@tool
def analyze_vibration_signal(signal_data: list, sampling_rate: float) -> str:
    """
    对振动信号进行时频域分析
    
    返回：FFT 频谱、包络谱、峭度指标
    """
    # 实现...
```

### 9.2 故障诊断流程

```
上传设备数据
    ↓
数据质量检查（Worker）
    ↓
特征提取 - 时域/频域/时频域
    ↓
异常检测算法
    ↓
故障模式匹配
    ↓
生成诊断报告（Host 整合）
```

### 9.3 参数预测实现

```python
# Worker Agent 中的预测代码示例
def predict_parameters(historical_data, target_param, horizon=24):
    """
    基于历史数据预测设备参数
    
    Args:
        historical_data: 历史传感器数据 DataFrame
        target_param: 目标预测参数名称
        horizon: 预测步长（小时）
    """
    import pandas as pd
    from sklearn.ensemble import GradientBoostingRegressor
    
    # 特征工程
    df = historical_data.copy()
    df['hour'] = df.index.hour
    df['dayofweek'] = df.index.dayofweek
    
    # 创建滞后特征
    for lag in [1, 2, 3, 6, 12, 24]:
        df[f'{target_param}_lag_{lag}'] = df[target_param].shift(lag)
    
    # 训练模型
    features = [c for c in df.columns if 'lag' in c or c in ['hour', 'dayofweek']]
    X = df[features].dropna()
    y = df[target_param].loc[X.index]
    
    model = GradientBoostingRegressor(n_estimators=100)
    model.fit(X, y)
    
    # 预测未来值
    last_known = X.iloc[-1:].values
    predictions = []
    
    for i in range(horizon):
        pred = model.predict(last_known)[0]
        predictions.append(pred)
        # 更新滞后特征...
    
    return predictions
```

### 9.4 可视化输出规范

```python
# Worker 生成图表的标准流程
import matplotlib.pyplot as plt

# 1. 创建图表
plt.figure(figsize=(12, 6))
plt.plot(timestamps, values)
plt.title('设备温度趋势')
plt.xlabel('时间')
plt.ylabel('温度 (°C)')

# 2. 显式保存（推荐）
plt.savefig('temperature_trend.png', dpi=150, bbox_inches='tight')

# 3. 在 final_answer 中引用
final_answer = {
    "task_outcome_short": "温度趋势分析",
    "task_outcome_detailed": "设备温度呈现上升趋势... ![温度趋势](/api/files/.../temperature_trend.png)",
}
```

---

## 10. 总结

### 10.1 架构优势

AIASys 的 Host-Worker 双 Agent 架构具有以下核心优势：

1. **职责分离清晰**：Host 专注协调，Worker 专注执行
2. **上下文压缩领先**：三层压缩机制有效管理长对话
3. **流式体验完整**：实时透传执行过程
4. **工业场景适配**：专业工具链支持设备数据分析

### 10.2 关键技术点

- 基于 smolagents 的灵活扩展
- CompactionManager 的三层压缩
- 队列+线程的流式通信
- SessionManager 的持久化管理

### 10.3 文件位置

| 文件 | 路径 |
|------|------|
| Host Agent | apps/backend/app/agents/core/host.py |
| 压缩 Agents | apps/backend/app/agents/core/compressed_agents.py |
| DataAnalysisTeam | apps/backend/app/agents/core/team.py |
| 压缩管理器 | apps/backend/app/agents/compaction/manager.py |
| Jupyter 执行器 | apps/backend/app/agents/executor/jupyter.py |
| 工作区工具 | apps/backend/app/agents/tools/workspace.py |
| 文档工具 | apps/backend/app/agents/tools/document.py |
| Notebook 工具 | apps/backend/app/agents/tools/notebook.py |

---

## 相关文档

- [[01-AIASys系统架构总览]]
- [[02-AIASys数据流分析]]
- [[03-AIASys-Jupyter集成分析]]
- [[smolagents-多Agent架构分析]]
- [[AIASys-压缩机制设计文档]]
