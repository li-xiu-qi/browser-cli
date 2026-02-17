# 05-DAG 执行引擎

**分析对象**: AWEL DAG 执行引擎  
**分析日期**: 2026-02-08

---

## TL;DR

AWEL 执行引擎采用 **DAG (有向无环图)** 调度模型，支持 **拓扑排序**、**并行执行**、**流式处理** 和 **分布式扩展 (Ray)**。核心组件：**DAG Builder** → **Scheduler** → **Executor**。

---

## 1. DAG 基础结构

### 1.1 DAG 类设计

```python
from typing import Set, Dict, List, Optional, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field

@dataclass
class DAG:
    """
    有向无环图 (Directed Acyclic Graph)
    
    用于表示 AWEL 工作流的执行依赖关系
    """
    name: str
    nodes: Set[BaseOperator] = field(default_factory=set)
    edges: Dict[BaseOperator, Set[BaseOperator]] = field(
        default_factory=lambda: defaultdict(set)
    )
    in_degree: Dict[BaseOperator, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    
    def add_node(self, op: BaseOperator) -> None:
        """添加节点"""
        self.nodes.add(op)
        if op not in self.edges:
            self.edges[op] = set()
    
    def add_edge(self, from_op: BaseOperator, to_op: BaseOperator) -> None:
        """
        添加边 (依赖关系)
        
        from_op -> to_op 表示 to_op 依赖 from_op 的输出
        """
        self.add_node(from_op)
        self.add_node(to_op)
        
        if to_op not in self.edges[from_op]:
            self.edges[from_op].add(to_op)
            self.in_degree[to_op] += 1
    
    def remove_edge(self, from_op: BaseOperator, to_op: BaseOperator) -> None:
        """移除边"""
        if to_op in self.edges[from_op]:
            self.edges[from_op].remove(to_op)
            self.in_degree[to_op] -= 1
    
    def get_upstream(self, op: BaseOperator) -> Set[BaseOperator]:
        """获取所有上游节点"""
        upstream = set()
        for node, neighbors in self.edges.items():
            if op in neighbors:
                upstream.add(node)
        return upstream
    
    def get_downstream(self, op: BaseOperator) -> Set[BaseOperator]:
        """获取所有下游节点"""
        return self.edges.get(op, set())
    
    def topological_sort(self) -> List[BaseOperator]:
        """
        拓扑排序
        
        返回节点的线性执行顺序，保证依赖关系
        使用 Kahn 算法
        """
        # 复制入度表
        in_degree = dict(self.in_degree)
        
        # 找到所有入度为 0 的节点 (没有依赖)
        queue = deque([
            node for node in self.nodes 
            if in_degree.get(node, 0) == 0
        ])
        
        result = []
        
        while queue:
            # 取出一个可以执行的节点
            node = queue.popleft()
            result.append(node)
            
            # 更新下游节点的入度
            for neighbor in self.edges.get(node, set()):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否有环
        if len(result) != len(self.nodes):
            raise ValueError("DAG contains cycles!")
        
        return result
    
    def get_parallel_groups(self) -> List[List[BaseOperator]]:
        """
        获取并行执行组
        
        每层包含可以同时执行的节点
        """
        in_degree = dict(self.in_degree)
        groups = []
        
        while True:
            # 找到当前所有入度为 0 的节点
            ready = [
                node for node in self.nodes
                if in_degree.get(node, 0) == 0 and 
                node not in [n for group in groups for n in group]
            ]
            
            if not ready:
                break
            
            groups.append(ready)
            
            # 更新入度
            for node in ready:
                for neighbor in self.edges.get(node, set()):
                    in_degree[neighbor] -= 1
        
        return groups
    
    def visualize(self) -> str:
        """生成可视化文本 (Mermaid 格式)"""
        lines = ["graph TD"]
        for node in self.nodes:
            node_id = id(node)
            node_name = node.config.name or node.__class__.__name__
            lines.append(f"    N{node_id}[{node_name}]")
        
        for from_node, to_nodes in self.edges.items():
            from_id = id(from_node)
            for to_node in to_nodes:
                to_id = id(to_node)
                lines.append(f"    N{from_id} --> N{to_id}")
        
        return '\n'.join(lines)
```

### 1.2 DAG 构建示例

```python
# 构建 RAG DAG
rag_dag = DAG("rag_workflow")

# 创建算子
trigger = HttpTrigger("/api/chat")
parse = MapOperator(lambda x: x.json()['query'])
embed = EmbeddingOperator("text2vec")
retrieve = RetrievalOperator("chromadb", "docs", top_k=5)
llm = LLMOperator("gpt-4", prompt_template="Answer: {input}")
format_output = MapOperator(lambda x: {"response": x})

# 添加边 (构建依赖关系)
rag_dag.add_edge(trigger, parse)
rag_dag.add_edge(parse, embed)
rag_dag.add_edge(embed, retrieve)
rag_dag.add_edge(retrieve, llm)
rag_dag.add_edge(llm, format_output)

# 拓扑排序
execution_order = rag_dag.topological_sort()
print("Execution order:", [n.config.name for n in execution_order])
# ['HttpTrigger', 'MapOperator', 'EmbeddingOperator', 
#  'RetrievalOperator', 'LLMOperator', 'MapOperator']

# 并行分组
parallel_groups = rag_dag.get_parallel_groups()
for i, group in enumerate(parallel_groups):
    print(f"Level {i}: {[n.config.name for n in group]}")
# Level 0: ['HttpTrigger']
# Level 1: ['MapOperator']
# Level 2: ['EmbeddingOperator']
# Level 3: ['RetrievalOperator']
# Level 4: ['LLMOperator']
# Level 5: ['MapOperator']
```

---

## 2. 调度器 (Scheduler)

### 2.1 调度策略

```python
from enum import Enum, auto
from typing import Protocol
import asyncio
import heapq

class SchedulingStrategy(Enum):
    """调度策略"""
    SEQUENTIAL = auto()       # 顺序执行
    PARALLEL = auto()         # 最大并行
    STREAMING = auto()        # 流式执行
    PRIORITY = auto()         # 优先级调度
    PIPELINE = auto()         # 流水线

class Scheduler(Protocol):
    """调度器接口"""
    
    async def schedule(
        self, 
        dag: DAG, 
        input_data: Any
    ) -> Any:
        """调度执行 DAG"""
        ...

class SequentialScheduler:
    """顺序调度器"""
    
    async def schedule(self, dag: DAG, input_data: Any) -> Any:
        """按拓扑顺序逐个执行"""
        execution_order = dag.topological_sort()
        
        # 存储每个节点的输出
        outputs: Dict[BaseOperator, Any] = {}
        
        for op in execution_order:
            # 获取上游输出作为输入
            upstream = dag.get_upstream(op)
            if upstream:
                # 合并多个上游输出
                if len(upstream) == 1:
                    input_val = outputs[list(upstream)[0]]
                else:
                    input_val = [outputs[u] for u in upstream]
            else:
                input_val = input_data
            
            # 执行算子
            output = await op.execute(input_val)
            outputs[op] = output
        
        # 返回最后一个节点的输出
        return outputs[execution_order[-1]]

class ParallelScheduler:
    """并行调度器"""
    
    def __init__(self, max_concurrency: int = 10):
        self.max_concurrency = max_concurrency
        self.semaphore = asyncio.Semaphore(max_concurrency)
    
    async def schedule(self, dag: DAG, input_data: Any) -> Any:
        """按层级并行执行"""
        parallel_groups = dag.get_parallel_groups()
        outputs: Dict[BaseOperator, Any] = {}
        
        for level, group in enumerate(parallel_groups):
            # 同层节点并行执行
            tasks = []
            for op in group:
                task = self._execute_operator(op, dag, outputs, input_data)
                tasks.append(task)
            
            # 等待当前层全部完成
            level_outputs = await asyncio.gather(*tasks)
            for op, output in zip(group, level_outputs):
                outputs[op] = output
        
        # 返回最后完成的输出
        last_group = parallel_groups[-1]
        if len(last_group) == 1:
            return outputs[last_group[0]]
        else:
            return [outputs[op] for op in last_group]
    
    async def _execute_operator(
        self,
        op: BaseOperator,
        dag: DAG,
        outputs: Dict[BaseOperator, Any],
        input_data: Any
    ) -> Any:
        """执行单个算子 (带并发控制)"""
        async with self.semaphore:
            # 准备输入
            upstream = dag.get_upstream(op)
            if upstream:
                if len(upstream) == 1:
                    input_val = outputs[list(upstream)[0]]
                else:
                    input_val = [outputs[u] for u in upstream]
            else:
                input_val = input_data
            
            return await op.execute(input_val)

class StreamingScheduler:
    """流式调度器"""
    
    async def schedule_stream(
        self, 
        dag: DAG, 
        input_data: Any
    ) -> AsyncIterator[Any]:
        """流式执行，产出中间结果"""
        execution_order = dag.topological_sort()
        
        # 对于流式执行，我们逐个处理输入元素
        if isinstance(input_data, (list, AsyncIterator)):
            async for item in self._as_async_iter(input_data):
                async for intermediate in self._process_item(
                    dag, execution_order, item
                ):
                    yield intermediate
        else:
            async for intermediate in self._process_item(
                dag, execution_order, input_data
            ):
                yield intermediate
    
    async def _process_item(
        self,
        dag: DAG,
        execution_order: List[BaseOperator],
        item: Any
    ) -> AsyncIterator[Any]:
        """处理单个输入项"""
        outputs: Dict[BaseOperator, Any] = {}
        
        for op in execution_order:
            upstream = dag.get_upstream(op)
            if upstream:
                if len(upstream) == 1:
                    input_val = outputs[list(upstream)[0]]
                else:
                    input_val = [outputs[u] for u in upstream]
            else:
                input_val = item
            
            # 流式执行
            if hasattr(op, 'execute_stream'):
                async for chunk in op.execute_stream(input_val):
                    yield {
                        'operator': op.config.name,
                        'chunk': chunk
                    }
                output = chunk  # 最后一个 chunk
            else:
                output = await op.execute(input_val)
            
            outputs[op] = output
        
        yield outputs[execution_order[-1]]
    
    async def _as_async_iter(
        self, 
        data: Union[List, AsyncIterator]
    ) -> AsyncIterator[Any]:
        """统一转换为异步迭代器"""
        if hasattr(data, '__aiter__'):
            async for item in data:
                yield item
        else:
            for item in data:
                yield item
```

### 2.2 优先级调度

```python
@dataclass
class PrioritizedOperator:
    """带优先级的算子包装"""
    priority: float
    operator: BaseOperator
    
    def __lt__(self, other):
        return self.priority < other.priority

class PriorityScheduler:
    """优先级调度器"""
    
    def __init__(self):
        self.priority_fn: Callable[[BaseOperator], float] = self._default_priority
    
    def _default_priority(self, op: BaseOperator) -> float:
        """默认优先级计算"""
        # LLM 操作优先级更高 (成本更高，尽早执行)
        if isinstance(op, LLMOperator):
            return 0.0
        # IO 操作次之
        elif isinstance(op, (RetrievalOperator, HttpTrigger)):
            return 1.0
        # 计算操作优先级最低
        else:
            return 2.0
    
    async def schedule(self, dag: DAG, input_data: Any) -> Any:
        """按优先级调度执行"""
        in_degree = dict(dag.in_degree)
        outputs: Dict[BaseOperator, Any] = {}
        ready_queue: List[PrioritizedOperator] = []
        
        # 初始化：入度为 0 的节点加入优先队列
        for node in dag.nodes:
            if in_degree.get(node, 0) == 0:
                priority = self.priority_fn(node)
                heapq.heappush(ready_queue, PrioritizedOperator(priority, node))
        
        while ready_queue:
            # 取出优先级最高的节点
            prio_op = heapq.heappop(ready_queue)
            op = prio_op.operator
            
            # 准备输入
            upstream = dag.get_upstream(op)
            if upstream:
                if len(upstream) == 1:
                    input_val = outputs[list(upstream)[0]]
                else:
                    input_val = [outputs[u] for u in upstream]
            else:
                input_val = input_data
            
            # 执行
            output = await op.execute(input_val)
            outputs[op] = output
            
            # 更新下游节点
            for neighbor in dag.get_downstream(op):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    priority = self.priority_fn(neighbor)
                    heapq.heappush(
                        ready_queue, 
                        PrioritizedOperator(priority, neighbor)
                    )
        
        # 找到输出节点 (没有下游的节点)
        sink_nodes = [
            n for n in dag.nodes 
            if not dag.get_downstream(n)
        ]
        
        if len(sink_nodes) == 1:
            return outputs[sink_nodes[0]]
        return [outputs[n] for n in sink_nodes]
```

---

## 3. 执行器 (Executor)

### 3.1 基础执行器

```python
class DAGExecutor:
    """DAG 执行器"""
    
    def __init__(
        self,
        dag: DAG,
        config: ExecutionConfig = None
    ):
        self.dag = dag
        self.config = config or ExecutionConfig()
        self.scheduler = self._create_scheduler()
        self.metrics = ExecutionMetrics()
    
    def _create_scheduler(self) -> Scheduler:
        """根据配置创建调度器"""
        if self.config.strategy == SchedulingStrategy.SEQUENTIAL:
            return SequentialScheduler()
        elif self.config.strategy == SchedulingStrategy.PARALLEL:
            return ParallelScheduler(self.config.max_concurrency)
        elif self.config.strategy == SchedulingStrategy.PRIORITY:
            return PriorityScheduler()
        else:
            return SequentialScheduler()
    
    async def run(self, input_data: Any = None) -> Any:
        """执行 DAG"""
        self.metrics.start()
        
        try:
            # 初始化所有算子
            await self._setup_operators()
            
            # 调度执行
            result = await self.scheduler.schedule(self.dag, input_data)
            
            self.metrics.success()
            return result
            
        except Exception as e:
            self.metrics.failure(e)
            raise ExecutionError(f"DAG execution failed: {e}") from e
        finally:
            # 清理资源
            await self._teardown_operators()
            self.metrics.end()
    
    async def _setup_operators(self):
        """初始化所有算子"""
        for op in self.dag.nodes:
            await op.setup()
    
    async def _teardown_operators(self):
        """清理所有算子"""
        for op in self.dag.nodes:
            await op.teardown()

class StreamingDAGExecutor(DAGExecutor):
    """流式 DAG 执行器"""
    
    async def run_stream(
        self, 
        input_data: Any = None
    ) -> AsyncIterator[Any]:
        """流式执行"""
        scheduler = StreamingScheduler()
        
        await self._setup_operators()
        
        try:
            async for chunk in scheduler.schedule_stream(
                self.dag, input_data
            ):
                yield chunk
        finally:
            await self._teardown_operators()
```

### 3.2 执行监控

```python
@dataclass
class ExecutionMetrics:
    """执行指标"""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    operator_metrics: Dict[str, OperatorMetrics] = field(
        default_factory=dict
    )
    status: str = "pending"  # pending, running, success, failure
    error: Optional[str] = None
    
    def start(self):
        self.start_time = time.time()
        self.status = "running"
    
    def end(self):
        self.end_time = time.time()
    
    def success(self):
        self.status = "success"
        self.end()
    
    def failure(self, error: Exception):
        self.status = "failure"
        self.error = str(error)
        self.end()
    
    @property
    def duration(self) -> float:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0

@dataclass
class OperatorMetrics:
    """算子执行指标"""
    operator_name: str
    start_time: float
    end_time: Optional[float] = None
    input_size: int = 0
    output_size: int = 0
    retry_count: int = 0
    error: Optional[str] = None
    
    @property
    def duration(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

class MonitoredExecutor(DAGExecutor):
    """带监控的执行器"""
    
    async def run(self, input_data: Any = None) -> Any:
        """执行并记录指标"""
        execution_order = self.dag.topological_sort()
        outputs: Dict[BaseOperator, Any] = {}
        
        for op in execution_order:
            metric = OperatorMetrics(
                operator_name=op.config.name or str(id(op)),
                start_time=time.time()
            )
            
            try:
                # 准备输入
                upstream = self.dag.get_upstream(op)
                if upstream:
                    if len(upstream) == 1:
                        input_val = outputs[list(upstream)[0]]
                    else:
                        input_val = [outputs[u] for u in upstream]
                else:
                    input_val = input_data
                
                metric.input_size = self._estimate_size(input_val)
                
                # 执行
                output = await op.execute(input_val)
                outputs[op] = output
                
                metric.output_size = self._estimate_size(output)
                metric.end_time = time.time()
                
            except Exception as e:
                metric.error = str(e)
                metric.end_time = time.time()
                raise
            finally:
                self.metrics.operator_metrics[op.config.name] = metric
        
        return outputs[execution_order[-1]]
    
    def _estimate_size(self, data: Any) -> int:
        """估算数据大小"""
        import sys
        return sys.getsizeof(data)
    
    def get_report(self) -> dict:
        """生成执行报告"""
        return {
            'dag_name': self.dag.name,
            'status': self.metrics.status,
            'total_duration': self.metrics.duration,
            'operator_count': len(self.dag.nodes),
            'operators': [
                {
                    'name': name,
                    'duration': m.duration,
                    'input_size': m.input_size,
                    'output_size': m.output_size,
                    'error': m.error
                }
                for name, m in self.metrics.operator_metrics.items()
            ]
        }
```

---

## 4. 分布式执行 (Ray)

```python
import ray

@ray.remote
class RayOperator:
    """Ray 远程算子包装"""
    
    def __init__(self, operator_class, *args, **kwargs):
        self.operator = operator_class(*args, **kwargs)
    
    async def execute(self, input_data):
        return await self.operator.execute(input_data)
    
    async def setup(self):
        await self.operator.setup()
    
    async def teardown(self):
        await self.operator.teardown()

class RayDistributedExecutor(DAGExecutor):
    """Ray 分布式执行器"""
    
    def __init__(self, dag: DAG, config: ExecutionConfig = None):
        super().__init__(dag, config)
        ray.init()
        self.ray_operators: Dict[BaseOperator, ray.ObjectRef] = {}
    
    async def run(self, input_data: Any = None) -> Any:
        """分布式执行"""
        parallel_groups = self.dag.get_parallel_groups()
        
        for group in parallel_groups:
            # 同层并行提交到 Ray
            futures = []
            for op in group:
                # 创建 Ray 远程算子
                ray_op = RayOperator.remote(
                    op.__class__,
                    *op._init_args,
                    **op._init_kwargs
                )
                self.ray_operators[op] = ray_op
                
                # 准备输入
                upstream = self.dag.get_upstream(op)
                if upstream:
                    if len(upstream) == 1:
                        input_val = self.ray_operators[list(upstream)[0]]
                    else:
                        input_val = [
                            self.ray_operators[u] for u in upstream
                        ]
                else:
                    input_val = input_data
                
                # 提交任务
                future = ray_op.execute.remote(input_val)
                futures.append((op, future))
            
            # 等待当前层完成
            for op, future in futures:
                result = ray.get(future)
                self.ray_operators[op] = result
        
        # 获取最终输出
        sink_nodes = [
            n for n in self.dag.nodes 
            if not self.dag.get_downstream(n)
        ]
        
        if len(sink_nodes) == 1:
            return self.ray_operators[sink_nodes[0]]
        return [self.ray_operators[n] for n in sink_nodes]
    
    def __del__(self):
        ray.shutdown()
```

---

## 5. 与 AIASys 的对比

| 特性 | AWEL DAG Executor | AIASys Host-Worker |
|------|-------------------|-------------------|
| **执行模型** | DAG 图调度 | 线性对话 |
| **并行能力** | 原生支持 | 有限 |
| **流式支持** | StreamingScheduler | SSE 包装 |
| **分布式** | Ray 支持 | 无 |
| **可视化** | DAG 可视化 | 需额外实现 |
| **适用场景** | 批量数据处理 | 交互式对话 |

---

## 6. 总结

AWEL 执行引擎的核心设计亮点：

1. **DAG 调度** - 拓扑排序确保依赖正确
2. **多级并行** - 同层节点并行执行
3. **流式支持** - StreamingScheduler 实时产出
4. **可扩展** - Ray 分布式执行
5. **可观测** - 完整的执行指标

---

*分析完成于 2026-02-08*
