# TaskWeaver Agent 架构深度分析

> **分析日期**: 2026-02-05  
> **源码版本**: TaskWeaver (Microsoft Open Source)  
> **分析范围**: Planner + Worker + Role 三层架构、依赖注入、经验学习、代码执行

---

## 一、架构总览

### 1.1 整体架构图

![TaskWeaver-核心流程图.svg](graphviz/TaskWeaver-核心流程图.svg)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TaskWeaver App Layer                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │  TaskWeaverApp  │───▶│ SessionManager  │───▶│      Session(s)         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Dependency Injection Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │
│  │PluginModule │ │LoggingModule│ │RoleModule   │ │ExecutionServiceModule│   │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘   │
│                              (injector 库实现)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent Core Layer                                   │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────┐      │
│   │                         Planner (Role)                          │      │
│   │  ┌──────────────────────────────────────────────────────────┐   │      │
│   │  │  - 接收用户请求，制定执行计划                              │   │      │
│   │  │  - 决策调用哪个 Worker                                    │   │      │
│   │  │  - 管理对话流程 (最多 max_self_ask_num=3 次自校正)         │   │      │
│   │  └──────────────────────────────────────────────────────────┘   │      │
│   └────────────────────────────┬────────────────────────────────────┘      │
│                                │                                            │
│           ┌────────────────────┼────────────────────┐                       │
│           ▼                    ▼                    ▼                       │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐                │
│   │CodeInterpreter│   │WebExplorer    │   │   ...其他      │                │
│   │   (Worker)    │   │   (Worker)    │   │   Worker      │                │
│   └───────┬───────┘   └───────────────┘   └───────────────┘                │
│           │                                                                 │
│   ┌───────▼───────┐                                                        │
│   │ CodeGenerator │  代码生成                                              │
│   │  CodeExecutor │  代码执行 (IPython Kernel)                             │
│   └───────────────┘                                                        │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Memory & Learning Layer                            │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────────────┐   │
│  │    Memory     │  │  Experience   │  │  Plugin Registry              │   │
│  │  Conversation │  │   Generator   │  │  (动态加载插件)                │   │
│  │    Round      │  │  (RAG 检索)   │  │                               │   │
│  │     Post      │  │               │  │                               │   │
│  └───────────────┘  └───────────────┘  └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计哲学

TaskWeaver 的设计体现了以下核心原则：

1. **分层解耦**: Planner 负责高层规划，Worker 负责具体执行，Role 定义通用接口
2. **依赖注入**: 使用 `injector` 库实现组件解耦，便于测试和扩展
3. **经验学习**: 内置 RAG 机制，支持从历史对话中检索相似经验
4. **状态保持**: 通过 IPython Kernel 保持代码执行状态
5. **插件化**: 支持动态加载插件扩展能力

---

## 二、核心组件分析

### 2.1 Role - 角色基类

**文件**: `taskweaver/role/role.py` (第 92-142 行)

```python
class Role:
    @inject
    def __init__(
        self,
        config: RoleConfig,
        logger: TelemetryLogger,
        tracing: Tracing,
        event_emitter: SessionEventEmitter,
        role_entry: Optional[RoleEntry] = None,
    ):
```

**设计要点**:

| 特性 | 说明 |
|------|------|
| `@inject` 装饰器 | 使用依赖注入自动注入配置、日志、追踪等组件 |
| `reply()` 抽象方法 | 子类必须实现，定义角色的核心行为 |
| `experience_generator` | 每个角色可独立加载经验，支持个性化学习 |
| `role_load_example()` | 支持 few-shot 示例加载 |

**RoleEntry 注册机制** (第 21-40 行):

```python
@dataclass
class RoleEntry:
    name: str      # 角色名称 (YAML 文件名)
    alias: str     # 显示别名
    module: type   # 实现类
    intro: str     # 介绍文本
```

角色通过 YAML 文件注册，实现声明式配置：
```yaml
# example.role.yaml
alias: "CodeInterpreter"
module: "taskweaver.code_interpreter.code_interpreter.CodeInterpreter"
intro: "A code interpreter that can execute Python code"
```

### 2.2 Planner - 规划者

**文件**: `taskweaver/planner/planner.py` (第 46-93 行)

```python
class Planner(Role):
    @inject
    def __init__(
        self,
        config: PlannerConfig,
        logger: TelemetryLogger,
        tracing: Tracing,
        event_emitter: SessionEventEmitter,
        llm_api: LLMApi,
        workers: Dict[str, Role],        # ← 关键：持有所有 Worker
        round_compressor: Optional[RoundCompressor],
        post_translator: PostTranslator,
        experience_generator: Optional[ExperienceGenerator] = None,
    ):
```

**Planner 如何决策调用哪个 Worker**?

Planner 通过 LLM 的 JSON Schema 输出决定:

```python
# planner.py 第 76-81 行
self.response_json_schema["properties"]["response"]["properties"]["send_to"]["enum"] = list(
    self.recipient_alias_set,
) + ["User"]
```

LLM 输出格式:
```json
{
  "response": {
    "send_to": "CodeInterpreter",  // 决定发送给哪个 Worker
    "message": "请分析数据...",
    "init_plan": "1. 加载数据...",
    "plan": "...",
    "current_plan_step": "..."
  }
}
```

**自我校正机制** (第 339-361 行):

```python
except (JSONDecodeError, AssertionError) as e:
    if self.ask_self_cnt > self.max_self_ask_num:  # 最多 3 次
        raise Exception(f"Planner failed...")
    else:
        post_proxy.update_send_to(self.alias)  # 发给自己重试
        self.ask_self_cnt += 1
```

**对话压缩** (第 218-226 行):

```python
if self.config.prompt_compression and self.round_compressor is not None:
    summary, rounds = self.round_compressor.compress_rounds(
        rounds,
        rounds_formatter=lambda _rounds: str(self.compose_conversation_for_prompt(_rounds)),
        prompt_template=self.compression_prompt_template,
    )
```

### 2.3 CodeInterpreter - Worker 实现

**文件**: `taskweaver/code_interpreter/code_interpreter/code_interpreter.py` (第 94-141 行)

```python
class CodeInterpreter(Role, Interpreter):
    @inject
    def __init__(
        self,
        generator: CodeGenerator,      # 代码生成器
        executor: CodeExecutor,        # 代码执行器
        logger: TelemetryLogger,
        tracing: Tracing,
        event_emitter: SessionEventEmitter,
        config: CodeInterpreterConfig,
        role_entry: RoleEntry,
    ):
```

**执行流程** (第 149-330 行):

```
┌────────────────────────────────────────────────────────┐
│                    CodeInterpreter.reply()               │
├────────────────────────────────────────────────────────┤
│ 1. generator.reply() → 生成代码                         │
│    └─▶ 无代码生成? → 返回文本回复                        │
│                                                         │
│ 2. 代码验证 (code_snippet_verification)                  │
│    └─▶ 验证失败? → 返回修正指令 (max_retry_count=3)      │
│                                                         │
│ 3. executor.execute_code() → 执行代码                   │
│    └─▶ 执行失败? → 返回错误信息                          │
│                                                         │
│ 4. 格式化输出 → 返回给 Planner                          │
└────────────────────────────────────────────────────────┘
```

**代码安全验证** (配置项):

```python
# code_interpreter.py 第 31-68 行
self.code_verification_on = self._get_bool("code_verification_on", False)
self.allowed_modules = self._get_list("allowed_modules", [
    "pandas", "matplotlib", "numpy", "sklearn", ...
])
self.blocked_functions = self._get_list("blocked_functions", [
    "eval", "exec", "open", "input", ...
])
```

---

## 三、依赖注入实现分析

![TaskWeaver-依赖注入图.svg](graphviz/TaskWeaver-依赖注入图.svg)

### 3.1 Injector 库使用

TaskWeaver 使用 Python `injector` 库实现依赖注入。

**核心配置** (app.py 第 45-48 行):

```python
self.app_injector = Injector(
    [SessionManagerModule, PluginModule, LoggingModule, ExecutionServiceModule, RoleModule],
)
self.app_injector.binder.bind(AppConfigSource, to=config_src)
```

### 3.2 Module 定义示例

**RoleModule** (role.py 第 302-323 行):

```python
class RoleModule(Module):
    @provider
    def provide_role_registries(
        self,
        config: RoleModuleConfig,
    ) -> RoleRegistry:
        # 动态扫描 ext_role 和 code_interpreter 目录
        glob_strings = []
        for sub_dir in os.listdir(config.ext_role_base_path):
            ...
        return RoleRegistry(glob_strings, ttl=timedelta(minutes=5))
```

### 3.3 @inject 装饰器工作原理

```python
# 典型的依赖注入构造函数
@inject
def __init__(
    self,
    config: PlannerConfig,           # 从 injector 获取 PlannerConfig 实例
    llm_api: LLMApi,                 # 从 injector 获取 LLMApi 实例
    workers: Dict[str, Role],        # 从 injector 获取所有 Role 实例
    ...
):
```

**好处**:

| 好处 | 说明 |
|------|------|
| 解耦 | 组件不需要知道依赖如何创建 |
| 可测试 | 便于 mock 依赖进行单元测试 |
| 可配置 | 通过 Module 配置不同的实现 |
| 生命周期管理 | 可控制依赖的单例/多例 |

### 3.4 Session 级别的子注入器

**文件**: `session/session.py` (第 69-82 行)

```python
# 每个 Session 有自己的子注入器
self.session_injector = app_injector.create_child_injector()

# 绑定 Session 特有的元数据
self.session_injector.binder.bind(SessionMetadata, self.metadata)

# 创建 Worker 实例时注入 role_entry
role_instance = self.session_injector.create_object(
    role_entry.module,
    {"role_entry": role_entry},
)
```

---

## 四、记忆机制分析

### 4.1 记忆层次结构

```
Memory (会话级别)
  └─ Conversation (对话)
       └─ Round[] (轮次数组)
            └─ Post[] (消息数组)
                 └─ Attachment[] (附件数组)
```

**核心类定义**:

| 类 | 文件 | 职责 |
|----|------|------|
| `Memory` | `memory/memory.py` | 管理会话的所有对话 |
| `Conversation` | `memory/conversation.py` | 多轮对话容器 |
| `Round` | `memory/round.py` | 单轮对话（一次用户请求）|
| `Post` | `memory/post.py` | 单条消息 |
| `Attachment` | `memory/attachment.py` | 消息附件 |

### 4.2 Post 消息结构

**文件**: `memory/post.py` (第 12-49 行)

```python
@dataclass
class Post:
    id: str
    send_from: RoleName      # 发送者
    send_to: RoleName        # 接收者
    message: str             # 文本消息
    attachment_list: List[Attachment]  # 附件列表
```

### 4.3 Attachment 类型系统

**文件**: `memory/attachment.py` (第 10-51 行)

```python
class AttachmentType(Enum):
    # Planner 类型
    init_plan = "init_plan"
    plan = "plan"
    current_plan_step = "current_plan_step"
    
    # CodeInterpreter
    thought = "thought"
    reply_type = "reply_type"
    reply_content = "reply_content"
    verification = "verification"
    execution_status = "execution_status"
    execution_result = "execution_result"
    
    # 共享内存
    shared_memory_entry = "shared_memory_entry"
```

### 4.4 角色视角的记忆过滤

**文件**: `memory/memory.py` (第 32-64 行)

```python
def get_role_rounds(self, role: RoleName, include_failure_rounds: bool = False) -> List[Round]:
    """获取特定角色的视角的记忆"""
    for round in self.conversation.rounds:
        new_round = Round.create(...)
        for post in round.post_list:
            if post.send_from == role or post.send_to == role:
                new_round.add_post(copy.deepcopy(post))
```

**关键设计**: 每个 Role 只看到与自己相关的对话历史，实现信息隔离。

### 4.5 共享内存机制

**文件**: `memory/memory.py` (第 79-106 行)

```python
def get_shared_memory_entries(self, entry_type: SharedMemoryEntryType) -> List[SharedMemoryEntry]:
    """获取特定类型的共享内存条目"""
    for round in self.conversation.rounds:
        for post in round.post_list:
            for attachment in post.attachment_list:
                if attachment.type == AttachmentType.shared_memory_entry:
                    entry: SharedMemoryEntry = attachment.extra
                    if entry.type == entry_type:
                        ...
```

Planner 通过 `SharedMemoryEntry` 向 Workers 传递计划信息。

---

## 五、代码执行与状态保持

### 5.1 执行架构

```
┌─────────────────────────────────────────────────────────────┐
│                     CodeExecutor                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐      ┌─────────────────────────────┐   │
│  │   exec_mgr      │─────▶│     Session Client          │   │
│  │ (Manager 接口)   │      │  - 管理 IPython Kernel      │   │
│  └─────────────────┘      │  - 保持执行状态              │   │
│                           └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   IPython Kernel (ces)                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           TaskWeaverContextMagic (Magic)            │    │
│  │  - _taskweaver_update_session_var (更新变量)        │    │
│  │  - _taskweaver_session_init (初始化上下文)          │    │
│  │  - _taskweaver_plugin_register (注册插件)           │    │
│  │  - _taskweaver_plugin_load (加载插件)               │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 IPython Magic 状态保持

**文件**: `ces/kernel/ctx_magic.py` (第 31-36 行)

```python
@cell_magic
def _taskweaver_update_session_var(self, line: str, cell: str):
    """更新会话变量到 IPython 命名空间"""
    json_dict_str = cell
    session_var_dict = json.loads(json_dict_str)
    self.executor.update_session_var(session_var_dict)
    return fmt_response(True, "Session var updated.", self.executor.session_var)
```

**工作原理**:

1. Session 级别的变量存储在 `session_variables` 字典中
2. 每次执行代码前，通过 Magic 命令注入到 IPython 命名空间
3. 执行后，通过 `_taskweaver_exec_post_check` 获取输出变量

**文件**: `code_executor.py` (第 68-84 行)

```python
def execute_code(self, exec_id: str, code: str) -> ExecutionResult:
    self.start()
    if not self.plugin_loaded:
        self.load_plugin()
        self.plugin_loaded = True
    
    # 更新会话变量到执行环境
    self.exec_client.update_session_var(self.session_variables)
    
    # 执行代码
    result = self.exec_client.execute_code(exec_id, code)
    ...
```

### 5.3 插件加载机制

**文件**: `ces/kernel/ctx_magic.py` (第 80-122 行)

```python
@line_cell_magic
def _taskweaver_plugin_register(self, line: str, cell: str):
    """注册插件代码"""
    plugin_name = line
    plugin_code = cell
    self.executor.register_plugin(plugin_name, plugin_code)

@line_cell_magic
def _taskweaver_plugin_load(self, line: str, cell: str, local_ns: Dict[str, Any]):
    """加载插件实例到命名空间"""
    plugin_name = line
    plugin_config = json.loads(cell)
    self.executor.config_plugin(plugin_name, plugin_config)
    local_ns[plugin_name] = self.executor.get_plugin_instance(plugin_name)
```

---

## 六、经验学习机制

### 6.1 ExperienceGenerator 架构

**文件**: `memory/experience.py` (第 59-67 行)

```python
class ExperienceGenerator:
    @inject
    def __init__(
        self,
        llm_api: LLMApi,
        config: ExperienceConfig,
        logger: TelemetryLogger,
        tracing: Tracing,
    ):
        self.experience_list: List[Experience] = []
```

### 6.2 经验生成流程

```
┌─────────────────────────────────────────────────────────────┐
│                    经验生成流程                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 保存原始对话 (raw_exp_{session_id}.yaml)                  │
│     └─▶ Memory.save_experience()                             │
│                                                             │
│  2. 刷新经验索引 (refresh)                                    │
│     └─▶ 检查是否有新 raw_exp 文件                            │
│     └─▶ 调用 LLM 生成经验摘要                                │
│     └─▶ 计算 embedding 并保存 (exp_{id}.yaml)               │
│                                                             │
│  3. 检索经验 (retrieve_experience)                           │
│     └─▶ 计算 query embedding                                 │
│     └─▶ 余弦相似度匹配                                       │
│     └─▶ 返回相似度 > threshold 的经验                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**经验摘要生成** (第 106-143 行):

```python
@tracing_decorator
def summarize_experience(self, exp_id: str, prompt: Optional[str] = None):
    # 读取原始对话
    conversation = read_yaml(raw_exp_file_path)
    conversation = self._preprocess_conversation_data(conversation)
    
    # 调用 LLM 生成摘要
    prompt = [
        format_chat_message("system", system_instruction),
        format_chat_message("user", json.dumps(conversation)),
    ]
    summarized_experience = self.llm_api.chat_completion(prompt)["content"]
    return summarized_experience
```

**经验检索** (第 267-295 行):

```python
@tracing_decorator
def retrieve_experience(self, user_query: str) -> List[Tuple[Experience, float]]:
    user_query_embedding = np.array(self.llm_api.get_embedding(user_query))
    
    similarities = []
    for experience in self.experience_list:
        similarity = cosine_similarity(
            user_query_embedding.reshape(1, -1),
            np.array(experience.embedding).reshape(1, -1),
        )
        similarities.append((experience, similarity))
    
    # 过滤阈值
    selected_experiences = [
        (exp, sim) for exp, sim in experience_rank 
        if sim >= self.config.retrieve_threshold
    ]
    return selected_experiences
```

### 6.3 经验在 Prompt 中的应用

**文件**: `planner/planner.py` (第 200-209 行)

```python
def compose_prompt(self, rounds: List[Round]) -> List[ChatMessageType]:
    experiences = self.format_experience(
        template=self.prompt_data["experience_instruction"],
    )
    
    chat_history = [
        format_chat_message(
            role="system",
            message=f"{self.compose_sys_prompt(context=self.get_env_context())}\n{experiences}",
        ),
    ]
```

---

## 七、扩展性设计

### 7.1 自定义 Worker 扩展

创建新 Worker 的步骤:

1. **继承 Role 基类**:
```python
class MyWorker(Role):
    @inject
    def __init__(self, config: MyConfig, ...):
        super().__init__(config, ...)
    
    def reply(self, memory: Memory, **kwargs) -> Post:
        # 实现核心逻辑
        pass
```

2. **创建 role.yaml 配置文件**:
```yaml
# my_worker.role.yaml
alias: "MyWorker"
module: "my_module.MyWorker"
intro: "A custom worker that..."
```

3. **添加到配置**:
```json
{
  "roles": ["planner", "code_interpreter", "my_worker"]
}
```

### 7.2 插件扩展

**文件**: `plugin/base.py` (第 9-43 行)

```python
class Plugin(ABC):
    def __init__(self, name: str, ctx: PluginContext, config: Dict[str, Any]):
        self.name = name
        self.ctx = ctx
        self.config = config
    
    @abstractmethod
    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """插件入口点"""
```

### 7.3 PostTranslator 扩展

支持自定义 LLM 输出解析:

```python
class PostTranslator:
    def raw_text_to_post(
        self,
        llm_output: Iterable[ChatMessageType],
        post_proxy: PostEventProxy,
        validation_func: Optional[Callable[[Post], None]] = None,
    ) -> None:
        # 支持自定义验证函数
```

---

## 八、与 DB-GPT 对比

| 维度 | TaskWeaver | DB-GPT |
|------|------------|--------|
| **架构模式** | Planner + Worker + Role | Agent + Tool + Memory |
| **依赖注入** | 使用 `injector` 库 | 自定义 `AWEL` 流程编排 |
| **代码执行** | IPython Kernel (状态保持) | Python 沙箱 (无状态) |
| **经验学习** | 内置 RAG 经验检索 | 依赖外部 VectorStore |
| **插件系统** | IPython Magic 动态加载 | 标准 Tool 注册 |
| **配置方式** | YAML + JSON 声明式 | Python 代码式 |
| **适用场景** | 数据分析、代码生成 | 通用 LLM 应用 |

---

## 九、优缺点总结

### 优点

1. **架构清晰**: Planner-Worker-Role 三层架构职责明确
2. **依赖注入**: 组件解耦，便于测试和扩展
3. **状态保持**: IPython Kernel 保证代码执行连续性
4. **经验学习**: 内置 RAG，支持从历史对话学习
5. **安全机制**: 代码验证 + 模块白名单
6. **流式处理**: LLM 输出流式解析，响应及时

### 缺点

1. **复杂性**: 依赖注入增加了理解门槛
2. **单进程限制**: IPython Kernel 单进程执行，无法并行
3. **经验冷启动**: 需要先积累对话才能生成经验
4. **配置分散**: 配置分散在多个 YAML/JSON 文件
5. **调试困难**: 异步消息流调试较复杂

---

## 十、关键代码索引

| 功能 | 文件 | 行号 |
|------|------|------|
| Role 基类 | `role/role.py` | 92-142 |
| Planner 决策 | `planner/planner.py` | 237-371 |
| CodeInterpreter | `code_interpreter/code_interpreter.py` | 94-335 |
| 代码生成 | `code_interpreter/code_generator.py` | 52-416 |
| 代码执行 | `code_interpreter/code_executor.py` | 42-152 |
| 经验学习 | `memory/experience.py` | 59-335 |
| 对话记忆 | `memory/conversation.py` | 14-84 |
| IPython Magic | `ces/kernel/ctx_magic.py` | 20-155 |
| Post 消息 | `memory/post.py` | 12-96 |
| Round 轮次 | `memory/round.py` | 13-86 |
| Memory 管理 | `memory/memory.py` | 16-113 |
| Session 管理 | `session/session.py` | 44-363 |
| 依赖注入配置 | `app/app.py` | 15-85 |
| 模块配置 | `config/module_config.py` | 9-47 |
| Post 转换器 | `role/translator.py` | 17-300 |
