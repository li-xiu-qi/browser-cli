# AIASys 整体架构分析

---

## 一、项目定位与核心目标

### 1.1 项目定义

AIASys 是面向工业制造场景的智能数据分析平台，定位为新一代柔性智能工业科研助手。项目名称 AIASys 代表 AI Agent System，强调其基于 Agent 架构的 AI 原生设计理念。

### 1.2 核心目标

| 目标维度 | 具体描述 |
|---------|---------|
| 工业数据分析 | 针对轧机、电机、减速器、轴承等工业设备进行深度数据分析 |
| 故障诊断 | 智能识别设备异常，提供故障分类、严重性评估和维护建议 |
| 参数预测 | 基于时间序列和参数辨识技术，实现设备参数预测与优化 |
| 智能交互 | 通过自然语言对话，降低工业数据分析的技术门槛 |

### 1.3 设计理念

AIASys 采用 Host-Worker 双 Agent 架构，这一设计理念借鉴了人类团队的协作模式：

- Host 类似于项目经理，负责理解需求、规划任务、协调资源
- Worker 类似于技术专家，负责具体的数据分析和代码实现

这种设计使得系统既能保持对用户友好，又能执行复杂的技术任务。

---

## 二、系统架构层次

### 2.1 架构概览

![系统架构图](../../assets/graphviz/aiasys-系统架构图.svg)

### 2.2 分层职责

```
用户 → 前端 React → 后端 FastAPI → Host Agent → Worker Agent → Jupyter Kernel
                ↓
            Supabase DB
```

#### 第一层：用户交互层

| 组件 | 职责 |
|------|------|
| 对话界面 | 自然语言输入、流式响应展示 |
| 文件管理器 | CSV、XLSX、PDF、DOCX 文件上传下载 |
| Notebook 回放器 | 分析过程的可视化回溯 |
| 可视化面板 | 图表、数据表格展示 |

#### 第二层：前端应用层

- 技术栈：React 19 + TypeScript 5.9 + Vite 7 + Tailwind CSS 4
- UI 组件库：shadcn/ui + Radix UI + Lucide React
- 核心能力：SSE 实时流处理、文件拖拽上传、响应式布局

#### 第三层：后端服务层

- 技术栈：FastAPI + Python 3.10+
- 核心模块：
  - API 路由层：RESTful API 设计
  - 会话管理层：SmolSessionManager 统一管理会话生命周期
  - 文件存储层：统一的文件存储服务
  - 任务队列层：Celery + Redis 异步任务处理

#### 第四层：Agent 调度层

- Host Agent：意图识别、任务分发、会话管理
- Worker Agent：代码执行、数据分析、可视化生成
- 工具集：工作区工具、文档工具、技能工具、Notebook 工具

#### 第五层：执行引擎层

- JupyterExecutorAdapter：适配 smolagents 的执行器接口
- MultiKernelInterpreterManager：多内核管理，会话隔离
- Python 执行环境：预装 pandas、numpy、matplotlib、seaborn 等

#### 第六层：数据持久层

- Supabase PostgreSQL：会话历史、元数据存储
- 本地文件系统：上传文件、输出结果、Notebook 文件

### 2.3 数据流向

![数据流图](../../assets/graphviz/aiasys-数据流图.svg)

数据流分为三个阶段：

1. 输入阶段：用户输入文本或上传文件，前端封装后通过 HTTP POST 提交到后端
2. 处理阶段：Host 解析意图，Worker 执行代码，Jupyter Kernel 运行 Python
3. 输出阶段：通过 SSE 流实时推送事件，最终返回分析报告和可视化结果

---

## 三、双 Agent 架构设计

### 3.1 架构原理

![双 Agent 架构图](../../assets/graphviz/aiasys-双Agent架构图.svg)

### 3.2 Host Agent

#### 类型与基础

Host Agent 基于 smolagents 的 ToolCallingAgent 实现，并扩展了 CompressedToolCallingAgent 以支持上下文压缩。

#### 核心职责

| 职责 | 说明 |
|------|------|
| 意图识别 | 解析用户自然语言请求，理解真实需求 |
| 任务规划 | 将复杂任务拆解为可执行的步骤 |
| 会话管理 | 维护多轮对话的上下文状态 |
| 工具分发 | 直接调用工作区工具处理简单任务 |
| 任务分发 | 通过 managed_agent 调用 Worker 处理复杂任务 |

#### 工具集

- list_workspace_files：查看工作区文件列表
- read_document：读取 PDF、DOCX、TXT 等文档内容
- create_folder：创建工作目录

#### 指令特点

Host 的指令强调：
- 简单任务自行完成，不分配给下属专家
- 复杂任务合理拆解，高效调度
- 正式回复要像报告一样整洁
- 复杂调度逻辑留在思考过程

### 3.3 Worker Agent

#### 类型与基础

Worker Agent 基于 smolagents 的 CodeAgent 实现，并扩展了 CompressedCodeAgent。

#### 核心职责

| 职责 | 说明 |
|------|------|
| 代码生成 | 编写 Python 代码实现数据分析 |
| 数据清洗 | 使用 pandas 处理原始数据 |
| 数据分析 | 统计分析、频谱分析、趋势分析 |
| 可视化 | 生成 matplotlib、seaborn 图表 |
| 报告生成 | 输出结构化的分析结论 |

#### 执行环境

Worker 通过 JupyterExecutorAdapter 连接到 Jupyter Kernel，享有以下预配置环境：

```python
authorized_imports = [
    "pandas", "numpy", "matplotlib", "seaborn",
    "polars", "scipy", "sklearn", "statsmodels",
    "plotly", "openpyxl", "PIL", "requests",
    "bs4", "lxml", "sympy", "random",
    "json", "datetime", "time", "math",
    "re", "pathlib", "shutil",
]
```

#### 图片输出机制

系统通过以下方式处理图表输出：

1. 推荐做法：使用 plt.savefig 显式保存图片
2. 备选做法：plt.show 也会被自动捕获
3. 图片保存到会话目录的 outputs/images/ 下
4. Observation 返回 Markdown 格式的图片链接
5. Worker 在 final_answer 中引用图片链接

### 3.4 managed_agent 调用机制

managed_agent 是 smolagents 的原生特性，Host 通过这一机制调用 Worker：

```python
# Host 初始化时注册 Worker 为 managed_agent
managed_agents = [self.worker]

self.host = CompressedToolCallingAgent(
    model=self.model,
    tools=host_tools,
    managed_agents=managed_agents,  # 注册下属 Agent
    # ...
)
```

调用流程：

1. Host 判断任务复杂度
2. 如需 Worker 执行，Host 构建任务描述
3. Host 调用 Worker.run，等待返回
4. Worker 在独立环境中执行代码分析
5. Worker 返回结构化结果
6. Host 整合 Worker 结果，生成最终回复

### 3.5 上下文压缩机制

为解决长对话导致的上下文爆炸问题，AIASys 实现了三层压缩机制：

| 压缩层级 | 触发条件 | 处理方式 |
|---------|---------|---------|
| Microcompaction | 每次写入消息前 | 截断旧步骤中过长的 observations |
| Auto-compaction | token 超过阈值 | 生成结构化摘要，保留关键上下文 |
| Manual compact | 外部显式调用 | 深度压缩，可指定聚焦点 |

压缩参数由 CompactionConfig 控制：

```python
CompactionConfig(
    max_context_tokens=12000,        # 最大上下文 token 数
    output_reserve_tokens=2000,      # 为输出预留的 token
    safety_buffer_tokens=2000,       # 安全缓冲
    auto_compact_threshold=0.3,      # 自动压缩阈值比例
    tool_results_budget_tokens=100,  # 工具输出预算
)
```

---

## 四、技术栈选型分析

### 4.1 后端技术栈

| 技术 | 版本 | 选型理由 |
|------|------|---------|
| Python | 3.10+ | 数据分析生态最成熟的语言 |
| FastAPI | 最新 | 高性能异步框架，原生支持 OpenAPI |
| smolagents | 最新 | Hugging Face 开源 Agent 框架，轻量灵活 |
| Jupyter | 最新 | 代码执行环境，支持丰富的数据科学库 |
| Celery | 最新 | 分布式任务队列，处理异步分析任务 |
| Redis | 最新 | 缓存和消息代理，支持 Celery |
| uv | 最新 | 极速 Python 包管理器 |

### 4.2 前端技术栈

| 技术 | 版本 | 选型理由 |
|------|------|---------|
| React | 19 | 最新版本，并发特性支持更好 |
| TypeScript | 5.9 | 类型安全，提升代码质量 |
| Vite | 7 | 极速构建工具，开发体验优秀 |
| Tailwind CSS | 4 | 实用优先的 CSS 框架 |
| shadcn/ui | 最新 | 基于 Radix UI 的高质量组件 |

### 4.3 数据库与存储

| 技术 | 用途 | 选型理由 |
|------|------|---------|
| Supabase | 会话历史、元数据 | PostgreSQL 托管服务，支持实时订阅 |
| 本地文件系统 | 上传文件、输出结果 | 大文件存储成本低，便于 Notebook 导出 |

### 4.4 容器化与部署

| 技术 | 用途 |
|------|------|
| Docker | 应用容器化 |
| Docker Compose | 本地开发环境编排 |
| Docker Sandbox | Worker 代码执行的隔离环境 |

---

## 五、支持的设备类型

AIASys 针对以下工业设备提供专门的分析能力：

| 设备类型 | 英文名称 | 典型分析场景 |
|---------|---------|-------------|
| 轧机 | Rolling Mill | 振动分析、辊缝偏差检测 |
| 电机 | Motor | 电流特征分析、轴承健康监测 |
| 减速器 | Reducer | 齿轮啮合频率分析、磨损检测 |
| 轴承 | Bearing | 故障特征频率识别、寿命预测 |

每种设备类型对应专门的 Skill 工具，封装了领域知识和分析方法。

---

## 六、核心功能模块

### 6.1 设备数据分析

| 分析类型 | 功能描述 |
|---------|---------|
| 振动分析 | 时域、频域、时频域振动信号处理 |
| 频谱分析 | FFT 变换、功率谱密度、倒频谱分析 |
| 趋势分析 | 时间序列趋势提取、变化点检测 |
| 异常检测 | 基于统计和机器学习的异常识别 |

### 6.2 智能故障诊断

| 诊断环节 | 功能描述 |
|---------|---------|
| 故障检测 | 识别设备是否处于异常状态 |
| 故障分类 | 判断故障类型，如轴承内圈故障、齿轮断齿 |
| 严重性评估 | 评估故障的严重程度和发展趋势 |
| 维护建议 | 生成针对性的维修和保养建议 |

### 6.3 参数预测优化

| 预测类型 | 功能描述 |
|---------|---------|
| 时间序列预测 | ARIMA、Prophet、LSTM 等模型 |
| 参数辨识预测 | 基于物理模型的参数估计 |
| 参数优化 | 多目标优化，寻找最佳运行参数 |

### 6.4 智能对话

- 基于大语言模型的自然语言交互
- 支持多轮对话和上下文理解
- 流式响应，实时反馈执行进度

### 6.5 文件管理

| 文件类型 | 支持操作 |
|---------|---------|
| CSV | 上传、解析、分析 |
| XLSX | Excel 文件读取和多 Sheet 处理 |
| PDF | 文档内容提取和解析 |
| DOCX | Word 文档读取 |
| PNG/JPG | 图片查看和引用 |

### 6.6 Notebook 回放

- 自动记录分析过程的代码和输出
- 支持历史 Notebook 的重运行
- 实现分析过程的可追溯和可复现

---

## 七、与 smolagents 的关系

### 7.1 smolagents 基础

smolagents 是 Hugging Face 开源的轻量级 Agent 框架，提供：

- CodeAgent：编写和执行 Python 代码
- ToolCallingAgent：调用外部工具
- 工具系统：易于扩展的工具定义
- 记忆系统：对话历史的维护

### 7.2 AIASys 的扩展

AIASys 在 smolagents 基础上进行了以下扩展：

#### 压缩 Agent

```python
class CompressedToolCallingAgent(ToolCallingAgent):
    """带上下文压缩的 Host Agent"""
    
    def write_memory_to_messages(self, summary_mode=False):
        # 先执行微压缩
        self.compaction_manager.microcompact(self.memory)
        # 再检查是否需要摘要压缩
        if self.compaction_manager.should_compact(self.memory):
            self.memory = self.compaction_manager.auto_compact(self.memory)
        # 标准消息生成
        return super().write_memory_to_messages(summary_mode)
```

#### Jupyter 执行适配器

```python
class JupyterExecutorAdapter(PythonExecutor):
    """将 Jupyter Kernel 适配为 smolagents 执行器"""
    
    def __call__(self, code_action: str) -> CodeOutput:
        # 执行代码并捕获结果
        # 处理文本输出和图片输出
        # 返回 CodeOutput 供 Agent 观察
```

#### 双 Agent 团队封装

```python
class DataAnalysisTeam:
    """数据分析团队：Host + Worker 协作"""
    
    def __init__(self, session_id, ...):
        # 创建 Worker
        self.worker = CompressedCodeAgent(...)
        # 创建 Host，注册 Worker 为 managed_agent
        self.host = CompressedToolCallingAgent(
            managed_agents=[self.worker],
            ...
        )
```

### 7.3 定制化特性

| 特性 | 说明 |
|------|------|
| 三层压缩 | Micro + Auto + Manual，解决上下文爆炸 |
| 磁盘卸载 | 工具输出过大时卸载到磁盘 |
| 增量压缩 | 只压缩新增步骤，提高效率 |
| 中文字体 | 自动配置 matplotlib 中文字体 |
| 图片捕获 | 自动捕获并保存图表 |

---

## 八、架构优缺点评估

### 8.1 架构优势

#### 模块化设计

- 各层职责清晰，便于独立开发和测试
- Agent 层与执行层解耦，可替换执行后端
- 工具系统易于扩展，新功能通过添加工具实现

#### 可扩展性

- Host-Worker 模式支持增加更多 Specialist Agent
- 技能系统允许动态加载领域知识
- 异步任务队列支持水平扩展

#### AI 原生

- 从设计之初就以 LLM 为核心
- 自然语言交互降低使用门槛
- 代码执行 + LLM 推理的混合架构

#### 工程化程度高

- 完整的开发文档和规范
- 自动化测试和部署流程
- 完善的监控和日志系统

### 8.2 潜在挑战

#### 架构复杂度

- 双 Agent 协作增加了理解难度
- 流式传输和多线程增加了调试复杂度
- 状态管理涉及多个组件

#### 调试难度

- Agent 的推理过程难以追踪
- 长对话的问题定位困难
- 上下文压缩可能影响调试信息

#### 性能考量

- LLM 调用是主要性能瓶颈
- 上下文压缩有计算开销
- 文件 I/O 和内核启动需要时间

#### 稳定性风险

- Jupyter Kernel 可能崩溃
- LLM 输出不稳定，需要重试机制
- 长时间运行的任务需要超时处理

### 8.3 优化方向

| 方向 | 措施 |
|------|------|
| 性能优化 | 实现 Agent 结果缓存、并行工具调用 |
| 稳定性 | 增强 Kernel 监控和自动重启 |
| 可观测性 | 完善 Tracing 和 Metrics 采集 |
| 成本控制 | 实现模型降级策略、压缩阈值调优 |

---

## 九、总结

AIASys 是一个面向工业制造的智能数据分析平台，其核心价值在于：

1. **降低技术门槛**：通过自然语言交互，让非专业数据分析人员也能进行设备分析
2. **提升分析效率**：AI Agent 自动编写代码，大幅减少人工编码工作量
3. **保证分析质量**：基于 Jupyter 的可复现分析，确保结果可追溯
4. **支持专业深度**：通过 Skill 系统，封装工业领域的专业知识

Host-Worker 双 Agent 架构是 AIASys 的灵魂设计，它模拟了人类团队的协作模式，使得系统既能保持对用户友好，又能执行复杂的技术任务。配合 smolagents 的灵活性和上下文压缩机制，AIASys 在工程实现上达到了较好的平衡。

---

## 参考文档

- [[AGENTS.md|AIASys AGENTS.md]]
- [[README.md|AIASys README]]
- [[docs/ai/03-be/architecture|后端架构文档]]
- [[docs/ai/03-be/agent-specs|Agent 规范]]
- [[apps/backend/docs/02-arch|后端架构详细文档]]

---

*文档版本: 1.0.0*  
*创建日期: 2026-02-08*  
*分析对象: AIASys v2.x*
