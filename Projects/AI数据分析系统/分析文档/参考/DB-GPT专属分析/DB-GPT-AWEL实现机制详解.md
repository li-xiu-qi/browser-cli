---
source: https://github.com/eosphoros-ai/DB-GPT/tree/main/packages/dbgpt-core/src/dbgpt/core/awel
---

# DB-GPT AWEL 实现机制详解

**官方文档**: https://docs.dbgpt.site/docs/awel/awel/

AWEL（Agentic Workflow Expression Language）是 DB-GPT 的核心创新，它是一种面向大模型应用开发的智能代理工作流表达语言。本文档深入解析 AWEL 的内部实现机制。

---

## 核心概念

### 什么是 AWEL

AWEL 是一套专门为大模型应用开发设计的工作流编排语言。它通过三层架构提供强大的功能和灵活性：

- **Operator 层**：最基础的操作原子，如检索、向量化、模型交互、Prompt 处理等
- **AgentFream 层**：对 Operator 的进一步封装，支持链式计算和分布式操作
- **DSL 层**：标准化的结构化表示语言，用声明式语法编排工作流

### 设计哲学

DB-GPT 将 Agent 视为一等公民。RAG、数据源、SMMF、插件都是 Agent 依赖的资源。AWEL 的设计目标是：

1. **确定性编排**：对于 pipeline 类任务，不需要大模型的自动编排能力
2. **与 Agent 互补**：AWEL 满足生产级 pipeline 实现，Agent 处理开放式问题
3. **最小代码量**：通过编排能力，用最少代码开发大模型应用

---

## 架构实现

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      AWEL 架构层次                           │
├─────────────────────────────────────────────────────────────┤
│  DSL 层                                                      │
│  └── CREATE WORKFLOW ... END; 声明式语法                      │
├─────────────────────────────────────────────────────────────┤
│  AgentFream 层                                               │
│  └── af.text2vec().filter().llm().map().reduce()             │
├─────────────────────────────────────────────────────────────┤
│  Operator 层                                                 │
│  └── MapOperator, JoinOperator, BranchOperator, ...          │
├─────────────────────────────────────────────────────────────┤
│  DAG 执行引擎                                                │
│  ├── DAG 定义与管理                                          │
│  ├── Task 调度执行                                           │
│  └── Runner 执行器                                           │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件关系

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│  Trigger │────▶│ Operator │────▶│  Output  │
└──────────┘     └──────────┘     └──────────┘
      │                │
      │           ┌────┴────┐
      │           ▼         ▼
      │      ┌────────┐ ┌────────┐
      │      │  Map   │ │ Branch │
      │      └────────┘ └────────┘
      │
      ▼
┌──────────────┐
│  HttpTrigger │──▶ FastAPI 路由注册
│ IteratorTrigger│
└──────────────┘
```

---

## DAG 核心实现

### DAG 定义与管理

DAG（有向无环图）是 AWEL 的核心数据结构，定义在 `dag/base.py`：

```python
class DAG:
    """The DAG class. Manage the DAG nodes and the relationship between them."""
    
    def __init__(self, dag_id: str, ...):
        self._dag_id = dag_id
        self.node_map: Dict[str, DAGNode] = {}           # 节点映射
        self.node_name_to_node: Dict[str, DAGNode] = {}  # 名称到节点映射
        self._root_nodes: List[DAGNode] = []             # 根节点
        self._leaf_nodes: List[DAGNode] = []             # 叶子节点
        self._trigger_nodes: List[DAGNode] = []          # 触发节点
```

### DAGNode 基类

所有工作流节点都继承自 `DAGNode`：

```python
class DAGNode(DAGLifecycle, DependencyMixin, ViewMixin, ABC):
    """The base class of DAGNode."""
    
    def __init__(self, dag: Optional["DAG"] = None, ...):
        self._upstream: List["DAGNode"] = []      # 上游节点
        self._downstream: List["DAGNode"] = []    # 下游节点
        self._dag: Optional["DAG"] = dag          # 所属 DAG
        self._node_id: Optional[str] = node_id    # 节点 ID
        self._node_name: Optional[str] = node_name # 节点名称
```

### 依赖关系管理

DAGNode 通过 `DependencyMixin` 支持链式语法：

```python
class DependencyMixin(ABC):
    """Define the interface for setting upstream and downstream nodes."""
    
    def __lshift__(self, nodes):   # 实现 << 操作符
        self.set_upstream(nodes)
        
    def __rshift__(self, nodes):   # 实现 >> 操作符
        self.set_downstream(nodes)
```

使用示例：

```python
trigger >> request_handle_task >> llm_task >> model_parse_task
# 等同于：
request_handle_task.set_upstream(trigger)
llm_task.set_upstream(request_handle_task)
```

### DAG 上下文管理

```python
class DAGContext:
    """The context of current DAG, created when the DAG is running."""
    
    def __init__(self, ...):
        self._node_to_outputs: Dict[str, TaskContext]  # 节点输出
        self._share_data: Dict[str, Any]               # 共享数据
        self._streaming_call: bool                     # 是否流式调用
        self._dag_variables: DAGVariables              # DAG 变量
```

DAGVar 用于管理当前 DAG 的上下文状态：

```python
class DAGVar:
    """Store the current DAG context."""
    
    _thread_local = threading.local()
    _async_local: contextvars.ContextVar = contextvars.ContextVar(...)
    _system_app: Optional[SystemApp] = None
    _executor: Optional[Executor] = None
```

---

## Operator 实现机制

### BaseOperator 基类

所有操作符都继承自 `BaseOperator`，定义在 `operators/base.py`：

```python
class BaseOperator(DAGNode, ABC, Generic[OUT], metaclass=BaseOperatorMeta):
    """Abstract base class for operator nodes."""
    
    def __init__(self, task_id: Optional[str] = None, 
                 task_name: Optional[str] = None, ...):
        super().__init__(node_id=task_id, node_name=task_name, ...)
        self._runner: WorkflowRunner = runner  # 工作流执行器
        self._dag_ctx: Optional[DAGContext] = None
```

### 核心 Operator 类型

#### 1. MapOperator

用于数据转换，定义在 `operators/common_operator.py`：

```python
class MapOperator(BaseOperator, Generic[IN, OUT]):
    """Map operator that applies a mapping function to its inputs."""
    
    def __init__(self, map_function: Optional[MapFunc] = None, **kwargs):
        self.map_function = map_function
        
    async def _do_run(self, dag_ctx: DAGContext) -> TaskOutput[OUT]:
        curr_task_ctx = dag_ctx.current_task_context
        map_function = self.map_function or self.map
        
        input_ctx = await curr_task_ctx.task_input.map(map_function)
        output = input_ctx.parent_outputs[0].task_output
        curr_task_ctx.set_task_output(output)
        return output
        
    async def map(self, input_value: IN) -> OUT:
        """Subclasses override this method."""
        raise NotImplementedError
```

#### 2. JoinOperator

用于合并多个上游节点的输出：

```python
class JoinOperator(BaseOperator, Generic[OUT]):
    """Operator that joins inputs using a custom combine function."""
    
    def __init__(self, combine_function: JoinFunc, ...):
        self.combine_function = combine_function
        
    async def _do_run(self, dag_ctx: DAGContext) -> TaskOutput[OUT]:
        curr_task_ctx = dag_ctx.current_task_context
        input_ctx = await curr_task_ctx.task_input.map_all(
            self.combine_function
        )
        join_output = input_ctx.parent_outputs[0].task_output
        curr_task_ctx.set_task_output(join_output)
        return join_output
```

#### 3. BranchOperator

用于条件分支：

```python
class BranchOperator(BaseOperator, Generic[IN, OUT]):
    """Operator node that branches the workflow based on a provided function."""
    
    def __init__(self, branches: Optional[Dict[BranchFunc[IN], BranchTaskType]] = None):
        self._branches = branches
        
    async def _do_run(self, dag_ctx: DAGContext) -> TaskOutput[OUT]:
        # 并行执行所有分支条件判断
        branch_func_tasks = []
        for func, node_name in branches.items():
            branch_func_tasks.append(
                curr_task_ctx.task_input.predicate_map(func, failed_value=None)
            )
        branch_input_ctxs = await asyncio.gather(*branch_func_tasks)
        
        # 标记需要跳过的节点
        skip_node_names = []
        for ctx in branch_input_ctxs:
            if ctx.parent_outputs[0].task_output.is_none:
                skip_node_names.append(node_name)
        curr_task_ctx.update_metadata("skip_node_names", skip_node_names)
```

### 自定义 Operator 示例

```python
class RequestHandleOperator(MapOperator[TriggerReqBody, str]):
    """Custom operator to handle request."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def map(self, input_value: TriggerReqBody) -> str:
        print(f"Receive input value: {input_value}")
        return f"Hello, {input_value.name}, your age is {input_value.age}"
```

---

## Trigger 实现机制

### Trigger 基类

Trigger 是 DAG 的入口，定义在 `trigger/base.py`。

### HttpTrigger 实现

`HttpTrigger` 是常用的触发器，定义在 `trigger/http_trigger.py`：

```python
class HttpTrigger(Trigger):
    """Http trigger for AWEL."""
    
    def __init__(
        self,
        endpoint: str,                              # API 端点
        methods: Optional[Union[str, List[str]]] = "GET",  # HTTP 方法
        request_body: Optional["RequestBody"] = None,      # 请求体类型
        streaming_response: bool = False,           # 是否流式响应
        ...
    ):
        self._endpoint = endpoint
        self._methods = [methods] if isinstance(methods, str) else methods
        self._req_body = request_body
        self._streaming_response = streaming_response
```

### 路由注册机制

HttpTrigger 会自动注册到 FastAPI：

```python
def mount_to_router(self, router: "APIRouter", global_prefix: Optional[str] = None):
    """Mount the trigger to a router."""
    endpoint = self._resolved_endpoint()
    path = join_paths(global_prefix, endpoint) if global_prefix else endpoint
    dynamic_route_function = self._create_route_func()
    
    router.api_route(
        endpoint,
        methods=self._methods,
        response_model=self._response_model,
        status_code=self._status_code,
        tags=self._router_tags,
    )(dynamic_route_function)
```

### DAG 触发执行

```python
async def _trigger_dag(
    body: Any,
    dag: DAG,
    streaming_response: Optional[bool] = False,
    ...
) -> Any:
    leaf_nodes = dag.leaf_nodes
    if len(leaf_nodes) != 1:
        raise ValueError("HttpTrigger just support one leaf node in dag")
    end_node = cast(BaseOperator, leaf_nodes[0])
    
    if not streaming_response:
        return await end_node.call(call_data=body)
    else:
        _generator = await end_node.call_stream(call_data=body)
        return StreamingResponse(_generator, ...)
```

---

## 工作流执行引擎

### DefaultWorkflowRunner

执行引擎定义在 `runner/local_runner.py`：

```python
class DefaultWorkflowRunner(WorkflowRunner):
    """The default workflow runner."""
    
    async def execute_workflow(
        self,
        node: BaseOperator,
        call_data: Optional[CALL_DATA] = None,
        streaming_call: bool = False,
        exist_dag_ctx: Optional[DAGContext] = None,
        dag_variables: Optional[DAGVariables] = None,
    ) -> DAGContext:
        """Execute the workflow starting from a given operator."""
        
        # 构建 JobManager
        job_manager = JobManager.build_from_end_node(node, call_data)
        
        # 创建或复用 DAGContext
        if not exist_dag_ctx:
            node_outputs: Dict[str, TaskContext] = {}
            share_data: Dict[str, Any] = {}
            event_loop_task_id = id(asyncio.current_task())
        
        dag_ctx = DAGContext(...)
        
        # 递归执行节点
        await self._execute_node(
            job_manager, node, dag_ctx, node_outputs, skip_node_ids, system_app
        )
        
        return dag_ctx
```

### 节点递归执行

```python
async def _execute_node(
    self,
    job_manager: JobManager,
    node: BaseOperator,
    dag_ctx: DAGContext,
    node_outputs: Dict[str, TaskContext],
    skip_node_ids: Set[str],
    system_app: Optional[SystemApp],
):
    # 跳过已执行节点
    if node.node_id in node_outputs:
        return

    # 递归执行所有上游节点（目前串行，待优化为并行）
    for upstream_node in node.upstream:
        if isinstance(upstream_node, BaseOperator):
            await self._execute_node(...)

    # 准备输入
    inputs = [node_outputs[n.node_id] for n in node.upstream]
    input_ctx = DefaultInputContext(inputs)
    
    # 创建任务上下文
    task_ctx = DefaultTaskContext(node.node_id, TaskState.INIT, ...)
    dag_ctx.set_current_task_context(task_ctx)
    task_ctx.set_current_state(TaskState.RUNNING)

    # 执行节点
    try:
        await node._run(dag_ctx, task_ctx.log_id)
        node_outputs[node.node_id] = dag_ctx.current_task_context
        task_ctx.set_current_state(TaskState.SUCCESS)
        
        # 处理分支逻辑
        if isinstance(node, BranchOperator):
            skip_nodes = task_ctx.metadata.get("skip_node_names", [])
            _skip_current_downstream_by_node_name(node, skip_nodes, skip_node_ids)
    except Exception as e:
        task_ctx.set_current_state(TaskState.FAILED)
        raise e
```

---

## 前端可视化编排

DB-GPT 提供完整的前端可视化工作流编排能力，基于 ReactFlow 实现。

### 前端架构

**技术栈**：
- **ReactFlow**：可视化画布和节点连接
- **Next.js**：前端框架
- **Ant Design**：UI 组件库

**核心组件**（位于 `web/pages/construct/flow/canvas/index.tsx`）：

```typescript
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
} from 'reactflow';

const Canvas: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      nodeTypes={{ customNode: CanvasNode }}
      edgeTypes={{ buttonedge: ButtonEdge }}
    >
      <Background />
      <Controls />
    </ReactFlow>
  );
};
```

### 功能特性

| 功能 | 实现组件 |
|------|---------|
| 拖拽添加节点 | `AddNodesSider` |
| 节点连接 | `ButtonEdge` + ReactFlow `addEdge` |
| 节点配置 | `CanvasNode` + 属性面板 |
| 工作流保存 | `SaveFlowModal` |
| 导入/导出 | `ImportFlowModal` / `ExportFlowModal` |
| 模板选择 | `FlowTemplateModal` |

### 前后端协作

前端画布编排的 JSON 数据通过 API 保存到后端，后端 AWEL 引擎执行：

```
前端画布（ReactFlow）
    ↓ 保存/加载
后端 Flow API（/api/v1/awel/flow/*）
    ↓ 解析执行
AWEL 引擎（DAG Runner）
```

---

## MCP 接入机制

DB-GPT 通过 `MCPToolPack` 实现 MCP（Model Context Protocol）接入。

### 核心实现

位于 `packages/dbgpt-serve/src/dbgpt_serve/agent/resource/mcp.py`：

```python
class MCPSSEToolPack(MCPToolPack):
    """MCP SSE 模式工具包"""
    
    def __init__(self, mcp_servers: Union[str, List[str]], **kwargs):
        # 支持多个 MCP 服务器（分号分隔）
        servers = mcp_servers.split(";") if isinstance(mcp_servers, str) else mcp_servers
        
        # 支持 Token 认证
        headers = {}
        if "token" in kwargs:
            headers[server] = {"Authorization": f"Bearer {token}"}
        
        # SSL 配置支持
        ssl_verify = ...
        
        super().__init__(mcp_servers=mcp_servers, headers=headers, ssl_verify=verify)
```

### 使用方式

```python
from dbgpt.agent.resource import MCPToolPack

# 1. 连接 MCP SSE 服务器
tools = MCPToolPack("http://127.0.0.1:8000/sse")

# 2. 绑定到 Agent
tool_engineer = (
    await ToolAssistantAgent()
    .bind(tools)           # 绑定 MCP 工具
    .bind(LLMConfig(...))
    .build()
)

# 3. 启动对话
await user_proxy.initiate_chat(
    recipient=tool_engineer,
    message="看下这个页面: https://example.com"
)
```

### 配置参数

| 参数 | 说明 |
|------|------|
| `mcp_servers` | MCP 服务器 URL，多个用分号分隔 |
| `token` | 认证 Token，支持 Bearer 格式 |
| `no_ssl_verify` | 禁用 SSL 验证（开发环境） |
| `ssl_ca_cert` | 自定义 CA 证书路径 |

### 启动 MCP 服务器示例

使用 supergateway 代理 stdio MCP 服务为 SSE：

```bash
# fetch 服务
npx -y supergateway --stdio "uvx mcp-server-fetch"

# 文件系统服务
npx -y supergateway --stdio "npx -y @modelcontextprotocol/server-filesystem ./"
```

---

## Flow 可视化与元数据

### ViewMetadata 元数据

每个 Operator 都带有元数据，用于前端可视化：

```python
class HttpTrigger(Trigger):
    metadata = ViewMetadata(
        label="Http Trigger",
        name="http_trigger",
        category=OperatorCategory.TRIGGER,
        operator_type=OperatorType.INPUT,
        description="Trigger your workflow by http request",
        inputs=[],
        outputs=[],
        parameters=[
            Parameter.build_from("API Endpoint", "endpoint", str, ...),
            Parameter.build_from("Http Methods", "methods", str, ...),
        ],
    )
```

### 资源注册

通过装饰器注册可复用资源：

```python
@register_resource(
    label="Dict Http Body",
    name="dict_http_body",
    category=ResourceCategory.HTTP_BODY,
    resource_type=ResourceType.CLASS,
)
class DictHttpBody(BaseHttpBody):
    pass
```

### Operator 分类

```python
class OperatorCategory(str, Enum):
    TRIGGER = "trigger"           # 触发器
    SENDER = "sender"             # 发送器
    LLM = "llm"                   # LLM 操作
    CONVERSION = "conversion"     # 转换
    OUTPUT_PARSER = "output_parser"  # 输出解析
    COMMON = "common"             # 通用
    AGENT = "agent"               # Agent
    RAG = "rag"                   # RAG
    DATABASE = "database"         # 数据库
```

---

## 完整使用示例

### 示例 1：简单聊天 DAG

```python
from dbgpt._private.pydantic import BaseModel, Field
from dbgpt.core import ModelMessage, ModelRequest
from dbgpt.core.awel import DAG, HttpTrigger, MapOperator
from dbgpt.model.operators import LLMOperator


class TriggerReqBody(BaseModel):
    model: str = Field(..., description="Model name")
    user_input: str = Field(..., description="User input")


class RequestHandleOperator(MapOperator[TriggerReqBody, ModelRequest]):
    async def map(self, input_value: TriggerReqBody) -> ModelRequest:
        messages = [ModelMessage.build_human_message(input_value.user_input)]
        return ModelRequest.build_request(input_value.model, messages)


with DAG("dbgpt_awel_simple_dag_example") as dag:
    trigger = HttpTrigger(
        "/examples/simple_chat", methods="POST", request_body=TriggerReqBody
    )
    request_handle_task = RequestHandleOperator()
    llm_task = LLMOperator(task_name="llm_task")
    model_parse_task = MapOperator(lambda out: out.to_dict())
    
    trigger >> request_handle_task >> llm_task >> model_parse_task
```

### 示例 2：带分支的 DAG

```python
from dbgpt.core.awel import BranchOperator

class ConditionBranch(BranchOperator[str, str]):
    async def branches(self) -> Dict[BranchFunc[str], BranchTaskType]:
        return {
            lambda x: "sql" in x.lower(): "sql_task",      # 走 SQL 分支
            lambda x: "chart" in x.lower(): "chart_task",  # 走图表分支
            lambda x: True: "default_task",                 # 默认分支
        }

with DAG("branch_example") as dag:
    trigger = HttpTrigger("/branch", request_body=dict)
    branch = ConditionBranch()
    sql_task = SQLGenerateOperator(node_name="sql_task")
    chart_task = ChartGenerateOperator(node_name="chart_task")
    default_task = DefaultOperator(node_name="default_task")
    
    trigger >> branch
    branch >> sql_task
    branch >> chart_task
    branch >> default_task
```

### 示例 3：开发模式测试

```python
if __name__ == "__main__":
    if dag.leaf_nodes[0].dev_mode:
        # 开发模式，本地调试
        from dbgpt.core.awel import setup_dev_environment
        setup_dev_environment([dag], port=5555)
    else:
        # 生产模式，由 DB-GPT 自动加载
        pass
```

---

## 关键设计特点

### 1. 类型安全

大量使用泛型和类型提示：

```python
class MapOperator(BaseOperator, Generic[IN, OUT]):
    async def map(self, input_value: IN) -> OUT: ...
```

### 2. 异步优先

所有执行方法都是异步的：

```python
async def _do_run(self, dag_ctx: DAGContext) -> TaskOutput[OUT]: ...
async def call(self, ...) -> OUT: ...
async def call_stream(self, ...) -> AsyncIterator[OUT]: ...
```

### 3. 上下文管理

通过 ContextVar 和线程局部变量管理上下文：

```python
CURRENT_DAG_CONTEXT: ContextVar[Optional[DAGContext]] = ContextVar(...)
```

### 4. 可扩展性

通过继承和元类实现灵活扩展：

```python
class BaseOperatorMeta(ABCMeta):
    """Metaclass of BaseOperator."""
    
    @classmethod
    def _apply_defaults(cls, func: F) -> F:
        # 自动应用默认参数
        ...
```

---

## 关联文档

- [[DB-GPT架构分析]]: DB-GPT 整体架构
- [[开源项目目录结构分析]]: 项目代码组织
- [[RAGFlow架构分析]]: 对比 RAGFlow 的实现
