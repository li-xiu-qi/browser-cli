# smolagents vs PandasAI 架构对比

> 分析日期: 2026-02-06
> 对比项目: smolagents vs PandasAI

## 一、总体架构对比

### 1.1 核心架构模式

smolagents 和 PandasAI 采用了完全不同的架构设计哲学。

smolagents 采用 **ReAct + Tool/Code 双模式** 架构。其核心是一个抽象基类 `MultiStepAgent`，通过继承派生出 `ToolCallingAgent` 和 `CodeAgent` 两种具体实现。这种设计的核心思想是：用一套统一的 ReAct 循环框架，支撑两种不同的交互模式。

PandasAI 采用 **Facade + State-Driven** 架构。其核心是一个 `Agent` 类作为外观接口，内部通过 `AgentState` 状态机驱动整个流程。这种设计的核心思想是：把所有状态集中管理，简化组件间的数据传递。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         架构模式对比                                     │
├──────────────────────────┬──────────────────────────────────────────────┤
│       smolagents         │               PandasAI                       │
├──────────────────────────┼──────────────────────────────────────────────┤
│                          │                                              │
│   ReAct 循环框架          │   State-Driven 流程                          │
│   ┌─────────────────┐    │   ┌─────────────────┐                          │
│   │ MultiStepAgent  │    │   │  Agent Facade   │                          │
│   │   抽象基类       │    │   │  统一入口       │                          │
│   └────────┬────────┘    │   └────────┬────────┘                          │
│            │             │            │                                  │
│     ┌──────┴──────┐      │            ▼                                  │
│     │             │      │   ┌─────────────────┐                          │
│  ┌──▼──┐     ┌───▼───┐   │   │   AgentState    │                          │
│  │Tool │     │ Code  │   │   │  单一数据源      │                          │
│  │Call │     │ Agent │   │   └────────┬────────┘                          │
│  └─────┘     └───────┘   │            │                                  │
│                          │   ┌────────┴────────┐                          │
│   继承派生模式            │   │  CodeGenerator  │                          │
│                          │   │  CodeCleaner    │                          │
│                          │   │  CodeValidator  │                          │
│                          │   │  CodeExecutor   │                          │
│                          │   └─────────────────┘                          │
│                          │                                              │
└──────────────────────────┴──────────────────────────────────────────────┘
```

### 1.2 代码规模与复杂度

| 维度 | smolagents | PandasAI |
|------|-----------|----------|
| 核心代码量 | ~1800 行 | ~500 行 Agent 核心 |
| 总代码量 | ~6000 行 | ~10000 行 |
| 架构复杂度 | 极简 | 简单 |
| 依赖数量 | 少 | 中等 |

smolagents 的极简主义体现在：核心 Agent 逻辑仅 1800 行左右，但功能完整。PandasAI 的极简主义体现在：Agent 核心类仅 330 行，但整个项目包含更多外围功能如向量存储、Skills 管理等。

### 1.3 模块组织对比

smolagents 的模块划分遵循 **功能边界清晰** 原则：

```
smolagents/
├── agents.py          # Agent 基类和两种实现
├── memory.py          # 记忆系统
├── tools.py           # 工具定义
├── models.py          # 模型接口
├── local_python_executor.py  # 本地执行器
├── remote_executors.py       # 远程执行器
└── monitoring.py      # 监控日志
```

PandasAI 的模块划分遵循 **流程驱动** 原则：

```
pandasai/
├── agent/
│   ├── base.py        # Agent Facade
│   └── state.py       # 状态机
├── core/
│   ├── code_generation/
│   ├── code_execution/
│   └── response/
├── skills/            # 技能扩展
└── sandbox/           # 沙箱抽象
```

## 二、Agent设计对比

### 2.1 Agent 类型设计

smolagents 提供了 **两种 Agent 实现**：

**ToolCallingAgent**
- 利用 LLM 原生的 tool calling 能力
- 输出 JSON 格式的工具调用
- 支持并行执行多个工具
- 适用于结构化任务

**CodeAgent**
- LLM 生成 Python 代码
- 代码在沙箱环境中执行
- 支持任意 Python 代码
- 适用于复杂数据处理

PandasAI 提供了 **单一 Agent 实现**：

**Agent Facade**
- 统一的外观接口
- 内部自动生成和执行代码
- 专注于 Pandas 数据分析
- 通过 `AgentState` 驱动流程

### 2.2 ReAct 循环 vs 状态机驱动

smolagents 的 ReAct 循环实现了完整的 **思考-行动-观察** 模式：

```python
# smolagents 的 ReAct 循环
def _run_stream(self, task: str, max_steps: int):
    while not returned_final_answer and self.step_number <= max_steps:
        # 1. 规划步骤 可选
        if self.planning_interval and should_plan:
            planning_step = self._generate_planning_step(task)
            yield planning_step
        
        # 2. 执行动作步骤
        action_step = ActionStep(step_number=self.step_number)
        for output in self._step_stream(action_step):
            yield output
            if isinstance(output, ActionOutput) and output.is_final_answer:
                returned_final_answer = True
        
        self.memory.steps.append(action_step)
        self.step_number += 1
```

PandasAI 采用 **状态流转** 模式：

```
INITIALIZED → QUERY_RECEIVED → CODE_GENERATED → CODE_EXECUTED
                   │                 │                  │
                   ▼                 ▼                  ▼
              generate_code()  validate_clean()   execute_code()
                   │                 │                  │
                   └─────────────────┴──────────────────┘
                                      │
                                      ▼
                                   ERROR → RETRYING → 循环
```

### 2.3 多 Agent 支持

smolagents 支持 **ManagedAgent** 模式：
- 可以注册子 Agent 作为工具
- 实现简单的多 Agent 协作
- 通过 Tool 机制集成

PandasAI **不支持多 Agent**：
- 设计为单一 Agent 工作
- 没有子 Agent 或协作机制
- 扩展性受限

## 三、代码生成对比

### 3.1 代码生成范围

smolagents 的 CodeAgent 生成 **通用 Python 代码**：
- 支持任意 Python 库
- 不限定于数据分析
- 代码块通过正则表达式解析
- 白名单控制 import

PandasAI 生成 **专用的数据分析代码**：
- 强制使用 Pandas 操作
- 可选使用 `execute_sql_query` 函数
- 代码模板化程度高
- SQL 注入防护

### 3.2 代码验证机制

smolagents 的验证：
- 语法检查：通过 AST 解析
- 白名单检查：控制可 import 的模块
- 危险模块拦截：os、sys、subprocess 等

PandasAI 的验证链：

```
┌──────────────────────────────────────────────────────────────┐
│                    PandasAI 代码验证链                        │
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

### 3.3 代码执行环境

smolagents 提供 **6 种执行器选择**：

| 执行器 | 类型 | 适用场景 | 安全性 |
|--------|------|---------|--------|
| LocalPythonExecutor | 本地 | 开发/测试 | 低 |
| E2BExecutor | 云端沙箱 | 生产 | 高 |
| DockerExecutor | 容器 | 生产 | 高 |
| WasmExecutor | WebAssembly | 浏览器 | 高 |
| ModalExecutor | Serverless | 生产 | 高 |
| JupyterExecutor | Jupyter Kernel | 研究 | 中 |

PandasAI 提供 **可选 Sandbox**：
- 仅提供抽象基类
- 无默认安全实现
- 依赖子类实现隔离
- 默认直接本地执行

## 四、对话管理对比

### 4.1 记忆系统设计

smolagents 采用 **Step-based 记忆系统**：

```python
class AgentMemory:
    def __init__(self, system_prompt: SystemPromptStep):
        self.system_prompt = system_prompt
        self.steps: list[MemoryStep] = []  # 核心：步骤列表

MemoryStep (ABC)
├── SystemPromptStep    # 系统提示
├── TaskStep            # 任务定义
├── PlanningStep        # 规划步骤
├── ActionStep          # 动作步骤
└── FinalAnswerStep     # 最终答案
```

每个 `ActionStep` 记录完整的执行信息：
- 步骤序号
- 模型输入消息
- 模型输出
- Token 使用量
- Tool 调用列表
- 执行输出
- 观察结果
- 错误信息
- 执行时间

PandasAI 采用 **简单对话历史**：

```python
@dataclass
class AgentState:
    memory: Memory = field(default_factory=Memory)
    # Memory 内部维护对话列表
```

`Memory` 类仅维护简单的消息列表，没有复杂的步骤追踪。

### 4.2 上下文构建

smolagents 的上下文构建：

```python
def write_memory_to_messages(self) -> list[ChatMessage]:
    """将记忆转换为模型输入消息"""
    messages = [self.system_prompt.to_chat_message()]
    
    for step in self.steps:
        if isinstance(step, TaskStep):
            messages.append(step.to_chat_message())
        elif isinstance(step, ActionStep):
            # 添加模型输出 Assistant
            messages.append(step.model_output_message)
            # 添加观察结果 User
            messages.append(ChatMessage(role=MessageRole.USER, content=step.observations))
    
    return messages
```

PandasAI 的上下文构建：
- 直接从 `Memory` 获取对话历史
- 拼接为 prompt 模板
- 没有复杂的角色区分

### 4.3 对话持久化

两者都 **不提供内置持久化**：
- smolagents：每次运行从空 memory 开始
- PandasAI：Memory 仅在内存中
- 都需要外部实现持久化

## 五、安全性对比

### 5.1 代码执行安全

smolagents 的 **多层安全防护**：

1. **白名单机制**
   ```python
   BASE_BUILTIN_MODULES = [
       "math", "random", "datetime", "collections",
       "itertools", "json", "re", "statistics",
   ]
   DANGEROUS_MODULES = ["os", "sys", "subprocess", "importlib"]
   ```

2. **执行器隔离**
   - 本地执行器：依赖白名单
   - 远程执行器：进程/容器级隔离

3. **语法检查**
   - AST 解析验证代码结构
   - 禁止危险语句

PandasAI 的 **有限安全防护**：

1. **环境隔离**
   ```python
   def get_environment() -> dict:
       return {
           "pd": pandas,
           "plt": matplotlib,
           "np": numpy,
       }
   ```

2. **SQL 注入防护**
   - 清洗 SQL 查询
   - 验证表名白名单

3. **可选 Sandbox**
   - 仅抽象接口
   - 无默认实现

### 5.2 安全能力对比表

| 安全特性 | smolagents | PandasAI |
|---------|-----------|----------|
| 白名单控制 | 完整 | 有限 |
| 沙箱执行 | 6 种选择 | 需自实现 |
| 语法检查 | AST 解析 | 无 |
| SQL 防护 | 无 | 有 |
| 危险模块拦截 | 完整 | 依赖环境 |

## 六、适用场景对比

### 6.1 场景推荐表

| 场景 | 推荐选择 | 理由 |
|------|---------|------|
| 通用任务 | smolagents | 更通用，不局限于数据分析 |
| 数据分析专用 | PandasAI | 更专业，强制 Pandas/SQL 操作 |
| 快速原型 | 两者皆可 | 都简单，几行代码即可运行 |
| 复杂工作流 | smolagents | ReAct 循环更适合多步推理 |
| 教育场景 | smolagents | 代码更清晰，架构易于理解 |
| 企业级部署 | smolagents | 更多执行器选择，安全可控 |
| Jupyter 环境 | PandasAI | 与 Pandas 工作流无缝集成 |
| 多 Agent 协作 | smolagents | 支持 ManagedAgent |

### 6.2 场景深度分析

**数据分析场景**

PandasAI 更适合：
- 用户只需要分析 DataFrame
- 希望代码强制使用 SQL 操作
- 需要与现有 Pandas 工作流集成

smolagents 也可以：
- 通过 CodeAgent 执行任意数据分析
- 但需要更多配置
- 没有强制 SQL 的约束

**通用 Agent 场景**

smolagents 明显更适合：
- ToolCallingAgent 可调用任意工具
- CodeAgent 可执行任意代码
- 不仅限于数据分析

PandasAI 几乎不适用：
- 设计为数据分析专用
- 没有通用工具调用机制

**复杂任务场景**

smolagents 更适合：
- ReAct 循环支持多步推理
- 可规划、执行、观察、反思
- 支持子 Agent 协作

PandasAI 受限：
- 单一状态机驱动
- 没有规划能力
- 不支持子 Agent

## 七、设计哲学对比

### 7.1 smolagents：研究型设计

smolagents 的设计哲学是 **"展示 Agent 原理"**：

1. **极简主义**
   - 1800 行代码实现完整框架
   - 没有过度设计
   - 每个类职责清晰

2. **教育价值**
   - 代码清晰易懂
   - 架构直观
   - 是学习 Agent 框架的好材料

3. **双模式探索**
   - ToolCalling 和 Code 两种模式
   - 展示不同交互范式的优劣
   - 给使用者选择权

4. **可扩展性**
   - 抽象基类设计
   - 多种执行器可选
   - 工具系统简单灵活

### 7.2 PandasAI：实用型设计

PandasAI 的设计哲学是 **"解决具体问题"**：

1. **开箱即用**
   - `agent.chat()` 一行代码完成
   - 不需要理解内部机制
   - 隐藏复杂性

2. **专注领域**
   - 只解决数据分析问题
   - 深度优化 Pandas 场景
   - SQL 优先的安全策略

3. **简化配置**
   - 全局/局部配置层级
   - 合理的默认值
   - 通过 property 优雅处理

4. **错误恢复**
   - 双层重试机制
   - 自动修复常见错误
   - 用户无感知

### 7.3 设计哲学对比图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        设计哲学对比                                      │
├──────────────────────────┬──────────────────────────────────────────────┤
│       smolagents         │               PandasAI                       │
├──────────────────────────┼──────────────────────────────────────────────┤
│                          │                                              │
│   "展示原理"              │   "解决问题"                                  │
│                          │                                              │
│   • 极简代码              │   • 开箱即用                                  │
│   • 清晰架构              │   • 隐藏复杂                                  │
│   • 教育价值              │   • 专注领域                                  │
│   • 双模式探索            │   • 简化配置                                  │
│                          │                                              │
│   适合：学习、研究、扩展    │   适合：快速使用、数据分析                    │
│                          │                                              │
└──────────────────────────┴──────────────────────────────────────────────┘
```

## 八、选型建议

### 8.1 选型决策树

```
开始选型
    │
    ├─ 是否需要通用 Agent 能力？
    │      ├─ 是 → 选择 smolagents
    │      └─ 否 → 继续
    │
    ├─ 是否只需要数据分析？
    │      ├─ 是 → 继续
    │      └─ 否 → 选择 smolagents
    │
    ├─ 是否希望代码强制使用 SQL？
    │      ├─ 是 → 选择 PandasAI
    │      └─ 否 → 继续
    │
    ├─ 是否需要多 Agent 协作？
    │      ├─ 是 → 选择 smolagents
    │      └─ 否 → 两者皆可
    │
    └─ 是否需要深度 Pandas 集成？
           ├─ 是 → 选择 PandasAI
           └─ 否 → 选择 smolagents
```

### 8.2 具体建议

**选择 smolagents 如果**：
- 你需要一个通用的 Agent 框架
- 你希望理解 Agent 的工作原理
- 你需要执行任意 Python 代码
- 你需要多 Agent 协作
- 你需要多种执行环境选择
- 你在做研究或教育

**选择 PandasAI 如果**：
- 你只需要分析 Pandas DataFrame
- 你希望最简单的一行代码 API
- 你希望代码强制使用安全 SQL
- 你在 Jupyter 环境工作
- 你不需要扩展其他功能
- 你只想快速得到分析结果

### 8.3 混合使用建议

在某些场景下，可以 **结合使用** 两者：

1. 使用 smolagents 作为主框架
2. 在数据分析任务中调用 PandasAI 的组件
3. 使用 PandasAI 的 CodeCleaner 进行代码验证
4. 使用 smolagents 的多种执行器增强安全性

## 九、总结

smolagents 和 PandasAI 代表了两种截然不同的 Agent 设计哲学。smolagents 是研究型的，追求极简和通用，适合学习 Agent 原理和构建通用 Agent 系统。PandasAI 是实用型的，追求开箱即用和专注，适合快速进行数据分析任务。

两者没有绝对的优劣，关键在于匹配具体需求。理解它们的架构差异，有助于做出正确的技术选型。

---

**参考文档**：
- [[01-smolagents-Agent架构深度分析]]
- [[Agent专属分析区/PandasAI-Agent架构深度分析]]
