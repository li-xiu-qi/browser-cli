# 03-AgentFream 层实现机制

**分析对象**: AWEL AgentFream 层  
**分析日期**: 2026-02-08

---

## TL;DR

AgentFream 是 AWEL 的**链式 API 层**，借鉴 Pandas/Spark 设计，提供**函数式编程风格**的工作流编排。核心机制：**惰性求值**、**类型推导**、**链式调用**。

---

## 1. 设计哲学

### 1.1 为什么设计 AgentFream?

```
问题：Operator 层太底层，DSL 层太声明式
      ↓
需求：Pythonic、链式、直观、可调试
      ↓
方案：AgentFream - 链式 API 层
```

### 1.2 对比其他链式 API

| 框架 | 链式风格 | 特点 | AgentFream 借鉴 |
|------|---------|------|-----------------|
| **Pandas** | `df.filter().groupby().agg()` | 数据处理 |  方法命名 |
| **Spark** | `rdd.map().filter().reduce()` | 分布式 |  惰性求值 |
| **LangChain** | `RunnableSequence` | LLM 链 | ⚠️ 过于复杂 |
| **TensorFlow** | `tf.data.Dataset` | 数据流 |  类型安全 |

---

## 2. 核心实现

### 2.1 AgentFream 类设计

```python
from typing import TypeVar, Generic, Callable, List, Optional, Union
import inspect

T = TypeVar('T')  # 输入类型
R = TypeVar('R')  # 输出类型

class AgentFream(Generic[T, R]):
    """
    AgentFream: 链式工作流构建器
    
    类型参数:
        T: 源数据类型 (Source 的输出类型)
        R: 当前转换后的类型
    
    示例:
        >>> af = AgentFream(HttpSource("/api/data"))
        >>> result = (af
        ...     .map(parse_json)
        ...     .filter(lambda x: x['score'] > 0.8)
        ...     .llm(model="gpt-4")
        ...     .execute())
    """
    
    def __init__(
        self,
        source: SourceOperator[T],
        name: Optional[str] = None
    ):
        """
        初始化 AgentFream
        
        Args:
            source: 数据源算子，作为工作流的起点
            name: 工作流名称
        """
        self._name = name or f"fream_{id(self)}"
        self._source = source
        self._tail: BaseOperator = source
        self._dag: DAG = DAG(self._name)
        self._dag.add_node(source)
        
        # 类型追踪 (用于类型推导)
        self._input_type: Type[T] = self._infer_type(source)
        self._output_type: Type[R] = self._input_type
        
        # 执行配置
        self._execution_config: ExecutionConfig = ExecutionConfig()
        
    # ========== 核心链式方法 ==========
    
    def map(
        self, 
        func: Callable[[R], U],
        name: Optional[str] = None
    ) -> AgentFream[T, U]:
        """
        映射操作：对每个元素应用转换函数
        
        Args:
            func: 转换函数，R -> U
            name: 算子名称
            
        Returns:
            新的 AgentFream，类型为 AgentFream[T, U]
            
        示例:
            >>> af.map(lambda x: x.upper())
            >>> af.map(parse_json, name="parse")
        """
        op = MapOperator(func, config=OperatorConfig(name=name))
        self._add_node(op)
        
        # 创建新的 AgentFream 并更新类型
        new_fream = self._clone()
        new_fream._output_type = self._infer_function_output(func)
        return new_fream
    
    def filter(
        self,
        predicate: Callable[[R], bool],
        name: Optional[str] = None
    ) -> AgentFream[T, R]:
        """
        过滤操作：保留满足条件的元素
        
        Args:
            predicate: 条件函数，R -> bool
            name: 算子名称
            
        Returns:
            AgentFream[T, R] (类型不变，数量可能减少)
        """
        op = FilterOperator(predicate, config=OperatorConfig(name=name))
        self._add_node(op)
        return self._clone()
    
    def reduce(
        self,
        reducer: Callable[[R, R], R],
        initial: Optional[R] = None,
        name: Optional[str] = None
    ) -> AgentFream[T, R]:
        """
        归约操作：将多个元素合并为单个结果
        
        Args:
            reducer: 归约函数，(R, R) -> R
            initial: 初始值
            name: 算子名称
            
        Returns:
            AgentFream[T, R] (从 List[R] 归约为 R)
        """
        op = ReduceOperator(reducer, initial, config=OperatorConfig(name=name))
        self._add_node(op)
        return self._clone()
    
    def llm(
        self,
        model: str,
        prompt_template: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        streaming: bool = False,
        name: Optional[str] = None
    ) -> AgentFream[T, str]:
        """
        LLM 调用操作
        
        Args:
            model: 模型名称，如 "gpt-4", "vicuna-13b"
            prompt_template: 提示词模板，支持 {input} 占位符
            temperature: 温度参数
            max_tokens: 最大 token 数
            streaming: 是否流式输出
            name: 算子名称
            
        Returns:
            AgentFream[T, str] (LLM 输出为字符串)
            
        示例:
            >>> af.llm("gpt-4", prompt_template="总结: {input}")
        """
        op = LLMOperator(
            model=model,
            prompt_template=prompt_template,
            temperature=temperature,
            max_tokens=max_tokens,
            streaming=streaming,
            config=OperatorConfig(name=name)
        )
        self._add_node(op)
        
        new_fream = self._clone()
        new_fream._output_type = str
        return new_fream
    
    def embed(
        self,
        model: str = "text2vec",
        name: Optional[str] = None
    ) -> AgentFream[T, List[float]]:
        """
        向量化操作
        
        Args:
            model: 嵌入模型名称
            name: 算子名称
            
        Returns:
            AgentFream[T, List[float]]
        """
        op = EmbeddingOperator(model, config=OperatorConfig(name=name))
        self._add_node(op)
        
        new_fream = self._clone()
        new_fream._output_type = List[float]
        return new_fream
    
    def retrieve(
        self,
        vector_store: str,
        collection: str,
        top_k: int = 5,
        name: Optional[str] = None
    ) -> AgentFream[T, List[Document]]:
        """
        向量检索操作
        
        Args:
            vector_store: 向量存储名称
            collection: 集合名称
            top_k: 返回文档数
            name: 算子名称
            
        Returns:
            AgentFream[T, List[Document]]
        """
        op = RetrievalOperator(
            vector_store=vector_store,
            collection=collection,
            top_k=top_k,
            config=OperatorConfig(name=name)
        )
        self._add_node(op)
        
        new_fream = self._clone()
        new_fream._output_type = List[Document]
        return new_fream
    
    def branch(
        self,
        condition: Callable[[R], bool],
        true_branch: Callable[[AgentFream], AgentFream],
        false_branch: Optional[Callable[[AgentFream], AgentFream]] = None,
        name: Optional[str] = None
    ) -> AgentFream[T, R]:
        """
        分支操作：条件执行不同分支
        
        Args:
            condition: 条件函数
            true_branch: 条件为 True 时执行的分支
            false_branch: 条件为 False 时执行的分支 (可选)
            name: 算子名称
            
        Returns:
            AgentFream[T, R]
        """
        # 构建分支子图
        true_fream = true_branch(self._clone())
        false_fream = false_branch(self._clone()) if false_branch else None
        
        op = BranchOperator(
            condition=condition,
            true_branch=true_fream._tail,
            false_branch=false_fream._tail if false_fream else None,
            config=OperatorConfig(name=name)
        )
        self._add_node(op)
        return self._clone()
    
    def join(
        self,
        other: AgentFream,
        left_key: Callable[[R], Any],
        right_key: Callable[[Any], Any],
        join_type: str = "inner",
        name: Optional[str] = None
    ) -> AgentFream[T, Dict]:
        """
        连接操作：合并两个 AgentFream
        
        Args:
            other: 另一个 AgentFream
            left_key: 左表连接键
            right_key: 右表连接键
            join_type: 连接类型 (inner/left/right/outer)
            name: 算子名称
            
        Returns:
            AgentFream[T, Dict]
        """
        # 合并 DAG
        self._dag.merge(other._dag)
        
        op = JoinOperator(
            left_key=left_key,
            right_key=right_key,
            join_type=join_type,
            config=OperatorConfig(name=name)
        )
        
        # 连接两个输入
        self._tail.connect(op)
        other._tail.connect(op)
        self._dag.add_node(op)
        self._dag.add_edge(self._tail, op)
        self._dag.add_edge(other._tail, op)
        
        self._tail = op
        return self._clone()
    
    # ========== 执行方法 ==========
    
    async def execute(self, input_data: Optional[T] = None) -> R:
        """
        执行工作流
        
        Args:
            input_data: 输入数据 (如果 Source 需要)
            
        Returns:
            执行结果，类型为 R
        """
        executor = DAGExecutor(self._dag, self._execution_config)
        return await executor.run(input_data)
    
    async def execute_stream(
        self, 
        input_data: Optional[T] = None
    ) -> AsyncIterator[R]:
        """
        流式执行工作流
        
        Args:
            input_data: 输入数据
            
        Yields:
            中间结果或最终结果
        """
        executor = StreamingDAGExecutor(self._dag, self._execution_config)
        async for chunk in executor.run_stream(input_data):
            yield chunk
    
    def collect(self) -> List[R]:
        """
        收集结果为列表 (仅用于批处理)
        
        Returns:
            结果列表
        """
        # 触发执行并收集结果
        import asyncio
        return asyncio.run(self.execute())
    
    # ========== 输出方法 ==========
    
    def write_to_sink(
        self, 
        sink: SinkOperator[R],
        name: Optional[str] = None
    ) -> None:
        """
        设置输出目标
        
        Args:
            sink: 输出算子
            name: 算子名称
        """
        if name:
            sink.config.name = name
        self._add_node(sink)
    
    def to_dag(self) -> DAG:
        """
        转换为 DAG 对象
        
        Returns:
            构建好的 DAG
        """
        return self._dag
    
    # ========== 内部方法 ==========
    
    def _add_node(self, op: BaseOperator) -> None:
        """内部：添加节点到 DAG"""
        self._tail.connect(op)
        self._dag.add_node(op)
        self._dag.add_edge(self._tail, op)
        self._tail = op
    
    def _clone(self) -> AgentFream:
        """内部：创建当前状态的浅拷贝"""
        new_fream = AgentFream.__new__(AgentFream)
        new_fream._name = self._name
        new_fream._source = self._source
        new_fream._tail = self._tail
        new_fream._dag = self._dag
        new_fream._input_type = self._input_type
        new_fream._output_type = self._output_type
        new_fream._execution_config = self._execution_config
        return new_fream
    
    def _infer_type(self, obj) -> Type:
        """推断类型"""
        # 实际实现使用 typing 模块
        return Any
    
    def _infer_function_output(self, func: Callable) -> Type:
        """从函数签名推断输出类型"""
        sig = inspect.signature(func)
        return_annotation = sig.return_annotation
        if return_annotation != inspect.Signature.empty:
            return return_annotation
        return Any
    
    # ========== 魔术方法 ==========
    
    def __or__(self, other: Callable[[AgentFream], AgentFream]) -> AgentFream:
        """
        支持管道操作符 |
        
        示例:
            >>> af | (lambda f: f.map(func).filter(pred))
        """
        return other(self)
    
    def __repr__(self) -> str:
        return f"AgentFream({self._name}): {self._input_type} -> {self._output_type}"
```

---

## 3. 惰性求值机制

### 3.1 为什么需要惰性求值?

```python
# 立即求值的问题
result = (af
    .map(expensive_transform)  # 立即执行
    .filter(rare_condition)     # 大部分数据被过滤，前面计算浪费
    .map(another_transform)     # 再次立即执行
)

# 惰性求值的优势
result = (af
    .map(expensive_transform)   # 只记录，不执行
    .filter(rare_condition)     # 只记录，不执行
    .map(another_transform)     # 只记录，不执行
    .execute()                  # 触发执行，优化后执行
)
```

### 3.2 执行计划优化

```python
class ExecutionOptimizer:
    """执行计划优化器"""
    
    @staticmethod
    def optimize(dag: DAG) -> DAG:
        """优化 DAG 执行计划"""
        optimizations = [
            OperatorFusion.fuse_operators,
            PredicatePushdown.push_down,
            ParallelismAnalyzer.add_parallel_hints,
        ]
        
        optimized = dag
        for opt in optimizations:
            optimized = opt(optimized)
        
        return optimized

# 优化示例：算子融合
class OperatorFusion:
    @staticmethod
    def fuse_operators(dag: DAG) -> DAG:
        """
        融合相邻的可合并算子
        
        map(f).map(g) → map(g∘f)
        filter(p1).filter(p2) → filter(p1 ∧ p2)
        """
        # 实现...
        pass
```

---

## 4. 类型推导系统

### 4.1 类型追踪

```python
from typing import get_type_hints, get_origin, get_args

class TypeTracker:
    """类型追踪器"""
    
    @staticmethod
    def infer_map_output(
        input_type: Type[T],
        func: Callable[[T], R]
    ) -> Type[R]:
        """推断 map 操作的输出类型"""
        # 1. 检查函数注解
        hints = get_type_hints(func)
        if 'return' in hints:
            return hints['return']
        
        # 2. 检查函数签名
        sig = inspect.signature(func)
        if sig.return_annotation != inspect.Signature.empty:
            return sig.return_annotation
        
        # 3. 无法推断，返回 Any
        return Any
    
    @staticmethod
    def infer_filter_output(input_type: Type[T]) -> Type[T]:
        """filter 不改变类型"""
        return input_type
    
    @staticmethod
    def infer_reduce_output(
        element_type: Type[T],
        reducer: Callable[[T, T], T]
    ) -> Type[T]:
        """reduce 输出元素类型"""
        return element_type

# 使用示例
class TypedAgentFream(AgentFream[T, R]):
    def map(self, func: Callable[[R], U]) -> TypedAgentFream[T, U]:
        output_type = TypeTracker.infer_map_output(self._output_type, func)
        # ...
        return TypedAgentFream(output_type=output_type)
```

### 4.2 类型安全示例

```python
# 正确：类型推导保证类型安全
af: AgentFream[Request, str] = (
    AgentFream(HttpSource("/api/data"))
    .map(lambda req: req.json())           # Request -> Dict
    .map(lambda data: json.dumps(data))    # Dict -> str
    .llm("gpt-4")                           # str -> str
)

# 错误：类型不匹配 (会被类型检查器捕获)
af_bad: AgentFream[Request, int] = (
    AgentFream(HttpSource("/api/data"))
    .map(lambda req: req.json())
    .llm("gpt-4")                           #  llm 输出 str，不是 int
)
```

---

## 5. 实战示例

### 5.1 RAG 工作流

```python
# RAG (Retrieval-Augmented Generation) 完整工作流
rag_pipeline = (
    AgentFream(HttpSource("/api/chat", methods=["POST"]))
    # 1. 解析请求
    .map(lambda req: req.json()['query'], name="parse_query")
    
    # 2. 向量化查询
    .embed(model="text2vec", name="embed_query")
    
    # 3. 检索相关文档
    .retrieve(
        vector_store="chromadb",
        collection="docs",
        top_k=5,
        name="retrieve_docs"
    )
    
    # 4. 构建提示词
    .map(
        lambda docs: construct_prompt(query, docs),
        name="build_prompt"
    )
    
    # 5. LLM 生成
    .llm(
        model="gpt-4",
        temperature=0.7,
        streaming=True,
        name="generate"
    )
    
    # 6. 格式化输出
    .map(lambda text: {"response": text}, name="format_output")
)

# 执行
result = await rag_pipeline.execute()
```

### 5.2 多分支工作流

```python
# 智能客服路由
customer_service = (
    AgentFream(HttpSource("/api/support"))
    .map(lambda req: req.json(), name="parse_request")
    
    # 意图识别分支
    .branch(
        condition=lambda x: x['intent'] == 'technical',
        true_branch=lambda f: (
            f.llm(model="tech-support-gpt", name="tech_support")
             .map(format_technical_response)
        ),
        false_branch=lambda f: (
            f.branch(
                condition=lambda x: x['intent'] == 'billing',
                true_branch=lambda f2: f2.llm(model="billing-gpt"),
                false_branch=lambda f2: f2.llm(model="general-gpt")
            )
        ),
        name="intent_routing"
    )
    
    .map(lambda x: {"answer": x}, name="format_response")
)
```

### 5.3 数据 ETL + LLM 分析

```python
# 销售数据分析
sales_analysis = (
    AgentFream(DBSource("sales_db", query="SELECT * FROM orders"))
    
    # 数据清洗
    .filter(lambda row: row['amount'] > 0, name="filter_valid")
    .map(clean_data, name="clean")
    
    # 聚合统计
    .reduce(
        reducer=lambda acc, row: {
            'total': acc['total'] + row['amount'],
            'count': acc['count'] + 1,
            'avg': (acc['total'] + row['amount']) / (acc['count'] + 1)
        },
        initial={'total': 0, 'count': 0, 'avg': 0},
        name="aggregate"
    )
    
    # LLM 生成分析报告
    .map(
        lambda stats: f"销售总额: {stats['total']}, 订单数: {stats['count']}",
        name="format_stats"
    )
    .llm(
        model="gpt-4",
        prompt_template="基于以下数据生成分析报告:\n{input}",
        name="generate_report"
    )
    
    # 写入数据库
    .write_to_sink(
        DBSink(table="analysis_reports"),
        name="save_report"
    )
)
```

---

## 6. 与 AIASys 的对比分析

| 维度 | AWEL AgentFream | AIASys Host-Worker |
|------|-----------------|-------------------|
| **编程风格** | 链式函数式 | 类继承命令式 |
| **灵活性** | 高 (任意组合) | 中 (固定结构) |
| **学习曲线** | 平缓 (类似 Pandas) | 中 (需要理解 Agent 概念) |
| **可视化** | 易于 DAG 可视化 | 需要额外设计 |
| **调试** | 可以单步执行算子 | 可以观察对话 |
| **适用场景** | 批量数据处理 | 交互式对话 |

---

## 7. 总结

AgentFream 层的核心设计亮点：

1. **链式 API** - 直观、流畅的编程体验
2. **类型安全** - 泛型 + 类型推导
3. **惰性求值** - 执行计划优化
4. **函数式风格** - 纯函数组合
5. **可观测性** - 每个步骤可追踪

---

*分析完成于 2026-02-08*
