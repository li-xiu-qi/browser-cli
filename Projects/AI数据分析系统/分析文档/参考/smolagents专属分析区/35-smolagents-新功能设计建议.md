# smolagents 新功能设计建议

> 项目: smolagents 功能扩展设计
> 文档版本: 1.0
> 创建日期: 2026-02-06
> 关联文档: [[14-smolagents-持久化与导入导出]]、[[27-smolagents-多Agent通信机制与返回结构深度分析]]

---

## 引言

本设计建议基于对 smolagents 现有架构的深度分析，针对生产环境部署和企业级应用需求，提出六个维度的功能增强方案。参考现有持久化机制 [[14-smolagents-持久化与导入导出]] 和通信机制 [[27-smolagents-多Agent通信机制与返回结构深度分析]]，识别出当前架构的关键短板并提出改进建议。

---

## 一、持久化功能增强

### 1.1 当前状态分析

现有 smolagents 的 save/load 机制主要保存静态配置：工具代码、Prompt模板、模型配置。参考 [[14-smolagents-持久化与导入导出]]，当前实现存在以下不足：

- 不保存运行时状态：Memory中的对话历史丢失
- 不支持执行中断恢复：长任务无法在中断后继续
- 无版本管理：无法回滚到之前的状态

### 1.2 Checkpoint机制设计

#### 自动保存点

实现基于步骤的自动保存机制：

```python
class CheckpointManager:
    """自动检查点管理器"""
    
    def __init__(
        self,
        agent: MultiStepAgent,
        save_interval: int = 5,
        storage_backend: str = "local",
        storage_config: dict = None
    ):
        self.agent = agent
        self.save_interval = save_interval
        self.step_count = 0
        self.storage = self._init_storage(storage_backend, storage_config)
    
    def on_step_end(self, step: MemoryStep):
        """每步结束时触发保存检查"""
        self.step_count += 1
        if self.step_count % self.save_interval == 0:
            self._create_checkpoint()
    
    def _create_checkpoint(self):
        """创建检查点"""
        checkpoint = {
            "version": "1.0",
            "timestamp": time.time(),
            "step_count": self.step_count,
            "memory": self._serialize_memory(),
            "agent_state": self._serialize_agent_state()
        }
        checkpoint_id = self.storage.save(checkpoint)
        logger.info(f"检查点已创建: {checkpoint_id}")
```

自动保存触发条件：

| 触发条件 | 说明 | 默认间隔 |
|----------|------|----------|
| 步骤计数 | 每执行N个步骤后保存 | 5步 |
| 时间间隔 | 每过N分钟后保存 | 10分钟 |
| 任务切换 | 子Agent调用前后 | 每次 |
| 错误发生 | 异常抛出时 | 立即 |

#### 手动保存

提供显式保存接口：

```python
# 用户主动触发保存
checkpoint_id = agent.checkpoint.save(
    name="关键决策点",
    tags=["重要", "待审查"]
)

# 在特定业务节点保存
if decision_confidence < 0.5:
    agent.checkpoint.save(
        name="低置信度决策",
        metadata={"confidence": decision_confidence}
    )
```

#### 状态恢复

实现从检查点恢复执行的能力：

```python
class CheckpointRecovery:
    """检查点恢复管理"""
    
    def restore(self, checkpoint_id: str) -> MultiStepAgent:
        """从检查点恢复Agent状态"""
        checkpoint = self.storage.load(checkpoint_id)
        
        # 重建Agent实例
        agent = MultiStepAgent.from_dict(checkpoint["agent_config"])
        
        # 恢复Memory状态
        agent.memory.steps = self._deserialize_memory(
            checkpoint["memory"]
        )
        
        # 恢复执行上下文
        agent.state = checkpoint["agent_state"]
        
        return agent
    
    def resume_from_checkpoint(
        self,
        checkpoint_id: str,
        continue_task: bool = True
    ):
        """从检查点继续执行"""
        agent = self.restore(checkpoint_id)
        
        if continue_task:
            # 获取未完成的任务
            pending_task = self._get_pending_task(checkpoint_id)
            return agent.run(pending_task, resume_from_checkpoint=True)
```

### 1.3 对话历史存储

#### 数据库存储方案

设计分层存储架构：

```python
from sqlalchemy import Column, String, DateTime, JSON, Integer, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ConversationSession(Base):
    """对话会话主表"""
    __tablename__ = "conversation_sessions"
    
    id = Column(String(36), primary_key=True)
    agent_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    status = Column(String(20), default="active")  # active, paused, completed
    metadata = Column(JSON)

class MemoryStepRecord(Base):
    """记忆步骤表"""
    __tablename__ = "memory_steps"
    
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), index=True)
    step_type = Column(String(50))  # TaskStep, ActionStep, PlanningStep
    step_index = Column(Integer)
    content = Column(JSON)  # 序列化的步骤数据
    token_usage = Column(JSON)
    timestamp = Column(Float)
```

#### 检索功能

实现对话历史的语义检索：

```python
class ConversationRetriever:
    """对话历史检索器"""
    
    def __init__(self, vector_store, db_session):
        self.vector_store = vector_store
        self.db = db_session
    
    def semantic_search(
        self,
        query: str,
        session_id: str = None,
        limit: int = 10
    ) -> list[dict]:
        """语义检索历史对话"""
        # 将查询向量化
        query_vector = self.embed(query)
        
        # 在向量库中搜索
        results = self.vector_store.search(
            query_vector,
            filter={"session_id": session_id} if session_id else None,
            top_k=limit
        )
        
        return results
    
    def search_by_tool_usage(
        self,
        tool_name: str,
        session_id: str = None
    ) -> list[dict]:
        """按工具使用检索"""
        query = self.db.query(MemoryStepRecord).filter(
            MemoryStepRecord.step_type == "ActionStep",
            MemoryStepRecord.content.op("->>")("tool_calls").contains(tool_name)
        )
        
        if session_id:
            query = query.filter(
                MemoryStepRecord.session_id == session_id
            )
        
        return query.all()
```

### 1.4 状态版本管理

#### 版本控制

实现类似Git的版本管理：

```python
class StateVersionManager:
    """Agent状态版本管理"""
    
    def commit(
        self,
        message: str,
        author: str = None
    ) -> str:
        """提交当前状态为新版本"""
        commit_id = self._generate_commit_id()
        
        commit_record = {
            "id": commit_id,
            "parent": self.current_commit,
            "message": message,
            "author": author,
            "timestamp": time.time(),
            "state_hash": self._compute_state_hash()
        }
        
        self._save_commit(commit_record)
        self._save_state_snapshot(commit_id)
        
        self.current_commit = commit_id
        return commit_id
    
    def checkout(self, commit_id: str) -> MultiStepAgent:
        """切换到指定版本"""
        # 加载版本状态
        state = self._load_state_snapshot(commit_id)
        
        # 重建Agent
        agent = MultiStepAgent.from_dict(state["agent_config"])
        agent.memory.steps = state["memory_steps"]
        
        self.current_commit = commit_id
        return agent
```

#### 回滚机制

提供快速回滚能力：

```python
def rollback_to_last_stable(agent: MultiStepAgent) -> MultiStepAgent:
    """回滚到最后稳定状态"""
    # 查找最后一个标记为稳定的提交
    stable_commit = version_manager.find_last_stable_commit()
    
    if not stable_commit:
        raise ValueError("未找到稳定版本")
    
    # 执行回滚
    return version_manager.checkout(stable_commit.id)

# 标记稳定版本
agent.version_manager.mark_stable(
    commit_id="abc123",
    reason="通过全部测试用例"
)
```

---

## 二、多Agent增强

### 2.1 当前状态分析

参考 [[27-smolagents-多Agent通信机制与返回结构深度分析]]，当前多Agent系统采用同步函数调用模型，存在以下局限：

- 上下文传递有限：Manager无法看到子Agent执行细节
- 无并行支持：一次只能调用一个子Agent
- 无法中断：子Agent一旦开始执行就无法中途停止
- 状态隔离：子Agent之间无法共享状态

### 2.2 消息总线设计

#### 发布订阅架构

实现异步消息通信机制：

```python
from dataclasses import dataclass
from typing import Callable
import asyncio

@dataclass
class AgentMessage:
    """Agent间消息格式"""
    message_id: str
    sender_id: str
    recipient_id: str  # 空字符串表示广播
    message_type: str  # task, result, event, heartbeat
    payload: dict
    timestamp: float
    correlation_id: str = None  # 用于关联请求和响应

class MessageBus:
    """Agent消息总线"""
    
    def __init__(self):
        self.subscribers: dict[str, list[Callable]] = {}
        self.message_queue = asyncio.Queue()
        self.running = False
    
    def subscribe(
        self,
        agent_id: str,
        message_types: list[str],
        handler: Callable
    ):
        """订阅消息"""
        key = f"{agent_id}:{','.join(message_types)}"
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(handler)
    
    def publish(self, message: AgentMessage):
        """发布消息"""
        asyncio.create_task(self._dispatch(message))
    
    async def _dispatch(self, message: AgentMessage):
        """消息分发"""
        # 直接发送
        if message.recipient_id:
            key = f"{message.recipient_id}:{message.message_type}"
            for handler in self.subscribers.get(key, []):
                await handler(message)
        else:
            # 广播
            for key, handlers in self.subscribers.items():
                if message.message_type in key:
                    for handler in handlers:
                        await handler(message)
```

#### 消息格式规范

定义标准消息类型：

```python
class MessageTypes:
    """标准消息类型"""
    
    # 任务相关
    TASK_ASSIGN = "task.assign"        # 分配任务
    TASK_PROGRESS = "task.progress"    # 任务进度更新
    TASK_COMPLETE = "task.complete"    # 任务完成
    TASK_FAILED = "task.failed"        # 任务失败
    
    # 状态相关
    STATE_UPDATE = "state.update"      # 状态更新
    STATE_REQUEST = "state.request"    # 请求状态
    STATE_SHARE = "state.share"        # 共享状态
    
    # 协调相关
    COORD_HEARTBEAT = "coord.heartbeat"
    COORD_ELECTION = "coord.election"
    COORD_LOCK = "coord.lock"
```

### 2.3 并行子Agent调用

#### 并行执行

实现并行调用多个子Agent：

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelAgentExecutor:
    """并行Agent执行器"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    async def execute_parallel(
        self,
        tasks: list[dict]
    ) -> list[dict]:
        """
        并行执行多个子Agent任务
        
        tasks格式:
        [
            {
                "agent": sub_agent_instance,
                "task": "任务描述",
                "timeout": 60
            }
        ]
        """
        loop = asyncio.get_event_loop()
        
        # 创建异步任务
        futures = []
        for task_def in tasks:
            future = loop.run_in_executor(
                self.executor,
                self._execute_with_timeout,
                task_def
            )
            futures.append(future)
        
        # 等待全部完成
        results = await asyncio.gather(*futures, return_exceptions=True)
        
        return [
            {
                "task_index": i,
                "result": result if not isinstance(result, Exception) else None,
                "error": str(result) if isinstance(result, Exception) else None,
                "success": not isinstance(result, Exception)
            }
            for i, result in enumerate(results)
        ]
    
    def _execute_with_timeout(self, task_def: dict):
        """带超时的执行"""
        agent = task_def["agent"]
        task = task_def["task"]
        timeout = task_def.get("timeout", 60)
        
        # 使用信号量实现超时
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"任务执行超时: {timeout}秒")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            result = agent.run(task)
            return result
        finally:
            signal.alarm(0)
```

#### 结果聚合

实现多种结果聚合策略：

```python
class ResultAggregator:
    """结果聚合器"""
    
    def __init__(self, strategy: str = "concat"):
        self.strategy = strategy
    
    def aggregate(self, results: list[dict]) -> str:
        """根据策略聚合结果"""
        if self.strategy == "concat":
            return self._concat_aggregate(results)
        elif self.strategy == "vote":
            return self._vote_aggregate(results)
        elif self.strategy == "merge":
            return self._merge_aggregate(results)
        elif self.strategy == "best":
            return self._best_aggregate(results)
        else:
            raise ValueError(f"未知聚合策略: {self.strategy}")
    
    def _concat_aggregate(self, results: list[dict]) -> str:
        """简单拼接聚合"""
        parts = []
        for i, r in enumerate(results):
            if r["success"]:
                parts.append(f"=== 结果 {i+1} ===\n{r['result']}")
        return "\n\n".join(parts)
    
    def _vote_aggregate(self, results: list[dict]) -> str:
        """投票聚合，适用于分类任务"""
        from collections import Counter
        
        successful_results = [
            r["result"] for r in results if r["success"]
        ]
        
        if not successful_results:
            return "无成功结果"
        
        # 统计最频繁的答案
        counter = Counter(successful_results)
        most_common = counter.most_common(1)[0]
        
        return f"投票结果: {most_common[0]} (支持率: {most_common[1]}/{len(successful_results)})"
    
    def _best_aggregate(self, results: list[dict]) -> str:
        """选择最佳结果"""
        # 根据置信度或质量评分选择最佳结果
        scored_results = []
        for r in results:
            if r["success"]:
                score = self._compute_quality_score(r["result"])
                scored_results.append((score, r["result"]))
        
        if not scored_results:
            return "无成功结果"
        
        best = max(scored_results, key=lambda x: x[0])
        return best[1]
    
    def _compute_quality_score(self, result: str) -> float:
        """计算结果质量分数"""
        # 基于结果长度、结构化程度等评估
        score = 0.0
        
        # 偏好结构化结果
        if "```" in result:
            score += 10
        
        # 偏好有数据支持的结果
        if any(c.isdigit() for c in result):
            score += 5
        
        # 惩罚过短的结果
        if len(result) < 50:
            score -= 10
        
        return score
```

### 2.4 Agent间状态共享

#### 共享内存

实现Agent间共享数据空间：

```python
from typing import Any
import threading

class SharedMemory:
    """Agent间共享内存"""
    
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self._storage: dict[str, Any] = {}
        self._locks: dict[str, threading.Lock] = {}
        self._metadata: dict[str, dict] = {}
        self._global_lock = threading.Lock()
    
    def get(self, key: str, default=None) -> Any:
        """获取共享值"""
        with self._global_lock:
            return self._storage.get(key, default)
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = None,
        owner: str = None
    ):
        """
        设置共享值
        
        ttl: 生存时间，秒
        owner: 设置者Agent ID
        """
        with self._global_lock:
            self._storage[key] = value
            self._metadata[key] = {
                "created_at": time.time(),
                "ttl": ttl,
                "owner": owner,
                "version": self._metadata.get(key, {}).get("version", 0) + 1
            }
            
            if key not in self._locks:
                self._locks[key] = threading.Lock()
    
    def acquire_lock(self, key: str, timeout: float = 10.0) -> bool:
        """获取键级锁"""
        lock = self._locks.get(key)
        if not lock:
            return False
        return lock.acquire(timeout=timeout)
    
    def release_lock(self, key: str):
        """释放键级锁"""
        lock = self._locks.get(key)
        if lock:
            lock.release()
    
    def subscribe_changes(self, key: str, callback: Callable):
        """订阅数据变更"""
        # 实现变更通知机制
        pass
```

#### 状态同步

实现跨Agent状态同步：

```python
class StateSynchronizer:
    """Agent状态同步器"""
    
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.local_states: dict[str, dict] = {}
        self.sync_interval = 5  # 秒
        self._start_sync_loop()
    
    def share_state(
        self,
        agent_id: str,
        state_key: str,
        state_value: Any,
        scope: str = "all"
    ):
        """
        共享状态给其他Agent
        
        scope: all, parent, children, specific_agent_id
        """
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=agent_id,
            recipient_id=scope if scope != "all" else "",
            message_type=MessageTypes.STATE_SHARE,
            payload={
                "state_key": state_key,
                "state_value": state_value,
                "timestamp": time.time()
            },
            timestamp=time.time()
        )
        
        self.message_bus.publish(message)
    
    def request_state(
        self,
        agent_id: str,
        target_agent: str,
        state_keys: list[str]
    ) -> dict:
        """请求其他Agent的状态"""
        correlation_id = str(uuid.uuid4())
        
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=agent_id,
            recipient_id=target_agent,
            message_type=MessageTypes.STATE_REQUEST,
            payload={"state_keys": state_keys},
            timestamp=time.time(),
            correlation_id=correlation_id
        )
        
        # 发送请求
        self.message_bus.publish(message)
        
        # 等待响应
        return self._wait_for_response(correlation_id, timeout=10.0)
```

---

## 三、可观测性增强

### 3.1 OpenTelemetry完整集成

#### Trace集成

实现分布式追踪：

```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from functools import wraps

class SmolagentsTracer:
    """smolagents追踪器"""
    
    def __init__(self, tracer_provider=None):
        self.tracer = trace.get_tracer(
            "smolagents",
            tracer_provider=tracer_provider
        )
    
    def instrument_agent(self, agent: MultiStepAgent):
        """为Agent添加追踪"""
        original_run = agent.run
        
        @wraps(original_run)
        def traced_run(task: str, **kwargs):
            with self.tracer.start_as_current_span(
                f"agent.{agent.name}.run",
                attributes={
                    "agent.name": agent.name,
                    "agent.class": agent.__class__.__name__,
                    "task.length": len(task)
                }
            ) as span:
                try:
                    result = original_run(task, **kwargs)
                    span.set_attribute("result.length", len(str(result)))
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        
        agent.run = traced_run
        return agent
    
    def trace_tool_call(self, tool: Tool):
        """为工具调用添加追踪"""
        original_forward = tool.forward
        
        @wraps(original_forward)
        def traced_forward(*args, **kwargs):
            with self.tracer.start_as_current_span(
                f"tool.{tool.name}",
                attributes={
                    "tool.name": tool.name,
                    "tool.description": tool.description[:100]
                }
            ) as span:
                start = time.time()
                try:
                    result = original_forward(*args, **kwargs)
                    duration = time.time() - start
                    span.set_attribute("duration_ms", duration * 1000)
                    span.set_attribute("result.type", type(result).__name__)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    raise
        
        tool.forward = traced_forward
        return tool
```

#### Metrics集成

暴露关键性能指标：

```python
from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, ObservableGauge

class SmolagentsMetrics:
    """smolagents指标收集"""
    
    def __init__(self):
        self.meter = metrics.get_meter("smolagents")
        self._init_metrics()
    
    def _init_metrics(self):
        """初始化指标"""
        # Token使用计数器
        self.token_counter = self.meter.create_counter(
            "smolagents.tokens.used",
            description="Total tokens used",
            unit="token"
        )
        
        # 执行时间直方图
        self.execution_histogram = self.meter.create_histogram(
            "smolagents.execution.duration",
            description="Agent execution duration",
            unit="ms"
        )
        
        # 步骤数直方图
        self.steps_histogram = self.meter.create_histogram(
            "smolagents.steps.count",
            description="Number of steps per run"
        )
        
        # 活跃Agent数量
        self.active_agents = self.meter.create_observable_gauge(
            "smolagents.agents.active",
            description="Number of active agents",
            callbacks=[self._get_active_agents]
        )
        
        # 工具调用计数器
        self.tool_calls = self.meter.create_counter(
            "smolagents.tool.calls",
            description="Tool call count by tool name"
        )
        
        # 错误计数器
        self.errors = self.meter.create_counter(
            "smolagents.errors",
            description="Error count by type"
        )
    
    def record_run(self, agent: MultiStepAgent, result: RunResult):
        """记录一次运行指标"""
        attributes = {
            "agent.name": agent.name,
            "agent.class": agent.__class__.__name__
        }
        
        # Token使用
        self.token_counter.add(
            result.token_usage.total_tokens,
            attributes=attributes
        )
        
        # 执行时间
        self.execution_histogram.record(
            result.timing.total_seconds * 1000,
            attributes=attributes
        )
        
        # 步骤数
        self.steps_histogram.record(
            len(result.steps),
            attributes=attributes
        )
```

#### Logs集成

统一日志收集：

```python
import logging
from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler

class SmolagentsLogger:
    """smolagents日志集成"""
    
    def __init__(self):
        self.logger_provider = LoggerProvider()
        self.handler = LoggingHandler(
            logger_provider=self.logger_provider,
            set_logger_provider=True
        )
        
        # 配置smolagents日志
        smolagents_logger = logging.getLogger("smolagents")
        smolagents_logger.addHandler(self.handler)
        smolagents_logger.setLevel(logging.INFO)
    
    def log_agent_step(
        self,
        agent: MultiStepAgent,
        step: MemoryStep,
        level: str = "info"
    ):
        """记录Agent步骤日志"""
        body = {
            "agent_name": agent.name,
            "step_type": step.__class__.__name__,
            "step_index": getattr(step, "step_number", 0),
            "observations": getattr(step, "observations", None),
            "tool_calls": getattr(step, "tool_calls", None)
        }
        
        severity = self._map_level_to_severity(level)
        
        self.logger_provider.get_logger("smolagents.agent").emit(
            body=body,
            severity_number=severity,
            attributes={
                "agent.id": id(agent),
                "session.id": getattr(agent, "session_id", "unknown")
            }
        )
```

### 3.2 调用链追踪

#### 跨Agent追踪

实现完整的调用链路追踪：

```python
from opentelemetry.propagate import extract, inject
from opentelemetry.context import attach, detach

class DistributedTracer:
    """分布式调用链追踪"""
    
    def __init__(self, tracer):
        self.tracer = tracer
    
    def start_managed_agent_span(
        self,
        parent_context,
        agent_name: str,
        task: str
    ):
        """开始子Agent调用追踪"""
        # 从父上下文提取trace信息
        context = extract(parent_context)
        token = attach(context)
        
        try:
            with self.tracer.start_as_current_span(
                f"managed_agent.{agent_name}",
                kind=trace.SpanKind.CLIENT,
                attributes={
                    "managed_agent.name": agent_name,
                    "task": task[:200]
                }
            ) as span:
                # 注入trace信息到子Agent上下文
                carrier = {}
                inject(carrier)
                
                return span, carrier
        finally:
            detach(token)
    
    def link_parent_span(self, parent_carrier: dict):
        """在子Agent中链接父span"""
        parent_context = extract(parent_carrier)
        token = attach(parent_context)
        
        return token
```

#### 可视化

提供调用链可视化：

```python
class TraceVisualizer:
    """调用链可视化"""
    
    def generate_trace_diagram(
        self,
        trace_id: str,
        format: str = "mermaid"
    ) -> str:
        """生成追踪图"""
        # 获取trace数据
        spans = self._get_trace_spans(trace_id)
        
        if format == "mermaid":
            return self._to_mermaid(spans)
        elif format == "json":
            return self._to_json(spans)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def _to_mermaid(self, spans: list) -> str:
        """转换为Mermaid序列图"""
        lines = ["sequenceDiagram"]
        
        for span in spans:
            parent = span.get("parent_id", "Root")
            name = span["name"]
            duration = span["duration_ms"]
            
            lines.append(f"    {parent}->>{name}: {span.get('attributes', {}).get('task', 'call')}")
            lines.append(f"    Note over {name}: {duration}ms")
        
        return "\n".join(lines)
```

### 3.3 性能指标暴露

#### Prometheus格式

实现Prometheus指标导出：

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest

class PrometheusExporter:
    """Prometheus指标导出器"""
    
    def __init__(self):
        # Token使用
        self.tokens_total = Counter(
            "smolagents_tokens_total",
            "Total tokens used",
            ["agent_name", "model_class"]
        )
        
        # 执行时间
        self.execution_duration = Histogram(
            "smolagents_execution_duration_seconds",
            "Agent execution duration",
            ["agent_name", "status"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        # 活跃Agent
        self.active_agents = Gauge(
            "smolagents_active_agents",
            "Number of active agents"
        )
        
        # LLM调用次数
        self.llm_calls = Counter(
            "smolagents_llm_calls_total",
            "Total LLM calls",
            ["agent_name", "model_class"]
        )
        
        # 工具调用
        self.tool_calls = Counter(
            "smolagents_tool_calls_total",
            "Total tool calls",
            ["tool_name", "status"]
        )
    
    def export(self) -> bytes:
        """导出Prometheus格式数据"""
        return generate_latest()
```

#### 自定义指标

支持用户自定义指标：

```python
class CustomMetricsRegistry:
    """自定义指标注册表"""
    
    def __init__(self):
        self.metrics: dict[str, Any] = {}
    
    def register_counter(
        self,
        name: str,
        description: str,
        labels: list[str] = None
    ):
        """注册计数器"""
        self.metrics[name] = {
            "type": "counter",
            "description": description,
            "labels": labels or [],
            "value": 0
        }
    
    def increment(self, name: str, labels: dict = None, value: int = 1):
        """增加计数器"""
        metric = self.metrics.get(name)
        if not metric or metric["type"] != "counter":
            raise ValueError(f"未知计数器: {name}")
        
        label_key = tuple(sorted(labels.items())) if labels else ()
        
        if "values" not in metric:
            metric["values"] = {}
        
        metric["values"][label_key] = metric["values"].get(label_key, 0) + value
```

---

## 四、企业级功能

### 4.1 多租户支持

#### 数据隔离

实现租户级别的数据隔离：

```python
from contextvars import ContextVar
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# 当前租户上下文
current_tenant: ContextVar[str] = ContextVar("current_tenant", default=None)

class TenantAwareSession:
    """租户感知的数据库会话"""
    
    def __init__(self, engine):
        self.Session = sessionmaker(bind=engine)
    
    def get_session(self):
        """获取带租户过滤的会话"""
        session = self.Session()
        tenant_id = current_tenant.get()
        
        if tenant_id:
            # 添加租户过滤
            @event.listens_for(session, "do_orm_execute")
            def _add_tenant_filter(execute_state):
                if execute_state.is_select:
                    execute_state.statement = execute_state.statement.options(
                        with_loader_criteria(
                            TenantMixin,
                            lambda cls: cls.tenant_id == tenant_id
                        )
                    )
        
        return session

class TenantMixin:
    """租户混合类，添加到所有模型"""
    tenant_id = Column(String(100), nullable=False, index=True)
```

#### 资源配额

实现租户资源限制：

```python
class ResourceQuotaManager:
    """资源配额管理器"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.quotas: dict[str, dict] = {}
    
    def set_quota(self, tenant_id: str, quotas: dict):
        """设置租户配额"""
        self.quotas[tenant_id] = {
            "max_requests_per_minute": quotas.get("rpm", 60),
            "max_tokens_per_day": quotas.get("tpd", 1000000),
            "max_concurrent_agents": quotas.get("agents", 10),
            "max_storage_mb": quotas.get("storage", 1000)
        }
    
    def check_and_consume(
        self,
        tenant_id: str,
        resource_type: str,
        amount: int = 1
    ) -> bool:
        """检查并消耗配额"""
        quota = self.quotas.get(tenant_id, {})
        limit = quota.get(resource_type)
        
        if not limit:
            return True
        
        key = f"quota:{tenant_id}:{resource_type}"
        current = self.redis.get(key) or 0
        
        if int(current) + amount > limit:
            return False
        
        self.redis.incr(key, amount)
        return True
    
    def get_usage(self, tenant_id: str) -> dict:
        """获取租户资源使用情况"""
        quota = self.quotas.get(tenant_id, {})
        usage = {}
        
        for resource_type in quota.keys():
            key = f"quota:{tenant_id}:{resource_type}"
            usage[resource_type] = {
                "limit": quota[resource_type],
                "used": int(self.redis.get(key) or 0),
                "remaining": quota[resource_type] - int(self.redis.get(key) or 0)
            }
        
        return usage
```

### 4.2 访问控制

#### RBAC

实现基于角色的访问控制：

```python
from enum import Enum
from functools import wraps

class Permission(Enum):
    """权限定义"""
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_RUN = "agent:run"
    TOOL_USE = "tool:use"
    ADMIN = "admin:*"

class Role:
    """角色定义"""
    ADMIN = [Permission.ADMIN]
    DEVELOPER = [
        Permission.AGENT_CREATE,
        Permission.AGENT_READ,
        Permission.AGENT_UPDATE,
        Permission.AGENT_RUN,
        Permission.TOOL_USE
    ]
    VIEWER = [Permission.AGENT_READ]

class RBACManager:
    """RBAC管理器"""
    
    def __init__(self):
        self.user_roles: dict[str, list[str]] = {}
        self.role_permissions: dict[str, list[Permission]] = {
            "admin": Role.ADMIN,
            "developer": Role.DEVELOPER,
            "viewer": Role.VIEWER
        }
    
    def assign_role(self, user_id: str, role: str):
        """分配角色给用户"""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
        self.user_roles[user_id].append(role)
    
    def check_permission(
        self,
        user_id: str,
        permission: Permission
    ) -> bool:
        """检查用户是否有权限"""
        roles = self.user_roles.get(user_id, [])
        
        for role in roles:
            permissions = self.role_permissions.get(role, [])
            if permission in permissions or Permission.ADMIN in permissions:
                return True
        
        return False
    
    def require_permission(self, permission: Permission):
        """权限检查装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                user_id = kwargs.get("user_id") or self._get_current_user()
                if not self.check_permission(user_id, permission):
                    raise PermissionError(f"缺少权限: {permission.value}")
                return func(*args, **kwargs)
            return wrapper
        return decorator
```

#### API密钥管理

实现安全的API密钥管理：

```python
import hashlib
import secrets
from datetime import datetime, timedelta

class APIKeyManager:
    """API密钥管理器"""
    
    def __init__(self, db_session):
        self.db = db_session
    
    def generate_key(
        self,
        user_id: str,
        name: str,
        permissions: list[str],
        expires_days: int = 90
    ) -> dict:
        """生成新API密钥"""
        # 生成随机密钥
        raw_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # 保存到数据库
        api_key = APIKeyModel(
            id=secrets.token_hex(16),
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            permissions=permissions,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
            last_used_at=None,
            is_active=True
        )
        
        self.db.add(api_key)
        self.db.commit()
        
        # 只返回一次原始密钥
        return {
            "id": api_key.id,
            "key": raw_key,  # 只返回一次
            "name": name,
            "expires_at": api_key.expires_at
        }
    
    def validate_key(self, raw_key: str) -> dict:
        """验证API密钥"""
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        api_key = self.db.query(APIKeyModel).filter(
            APIKeyModel.key_hash == key_hash,
            APIKeyModel.is_active == True,
            APIKeyModel.expires_at > datetime.utcnow()
        ).first()
        
        if not api_key:
            raise ValueError("无效的API密钥")
        
        # 更新最后使用时间
        api_key.last_used_at = datetime.utcnow()
        self.db.commit()
        
        return {
            "user_id": api_key.user_id,
            "permissions": api_key.permissions,
            "name": api_key.name
        }
    
    def revoke_key(self, key_id: str, user_id: str):
        """撤销API密钥"""
        api_key = self.db.query(APIKeyModel).filter(
            APIKeyModel.id == key_id,
            APIKeyModel.user_id == user_id
        ).first()
        
        if api_key:
            api_key.is_active = False
            self.db.commit()
```

### 4.3 审计日志

#### 操作记录

实现详细的操作审计：

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class AuditLogEntry:
    """审计日志条目"""
    id: str
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    tenant_id: str
    ip_address: str
    user_agent: str
    request_id: str
    before_state: dict
    after_state: dict
    metadata: dict

class AuditLogger:
    """审计日志记录器"""
    
    ACTIONS = {
        "AGENT_CREATE": "agent.create",
        "AGENT_RUN": "agent.run",
        "AGENT_UPDATE": "agent.update",
        "AGENT_DELETE": "agent.delete",
        "TOOL_EXECUTE": "tool.execute",
        "CONFIG_CHANGE": "config.change",
        "LOGIN": "auth.login",
        "LOGOUT": "auth.logout"
    }
    
    def __init__(self, storage_backend):
        self.storage = storage_backend
    
    def log(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: str = None,
        tenant_id: str = None,
        before_state: dict = None,
        after_state: dict = None,
        metadata: dict = None
    ):
        """记录审计日志"""
        entry = AuditLogEntry(
            id=secrets.token_hex(16),
            timestamp=datetime.utcnow(),
            user_id=user_id or self._get_current_user(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            tenant_id=tenant_id or current_tenant.get(),
            ip_address=self._get_client_ip(),
            user_agent=self._get_user_agent(),
            request_id=self._get_request_id(),
            before_state=before_state or {},
            after_state=after_state or {},
            metadata=metadata or {}
        )
        
        self.storage.save(entry)
    
    def query(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        user_id: str = None,
        action: str = None,
        resource_type: str = None,
        limit: int = 100
    ) -> list[AuditLogEntry]:
        """查询审计日志"""
        return self.storage.query(
            start_time=start_time,
            end_time=end_time,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            limit=limit
        )
```

#### 合规支持

支持合规性要求：

```python
class ComplianceManager:
    """合规管理器"""
    
    RETENTION_POLICIES = {
        "gdpr": 2555,  # 7年
        "hipaa": 2555,  # 7年
        "soc2": 1095,   # 3年
        "iso27001": 1095  # 3年
    }
    
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
        self.compliance_standard = "gdpr"
    
    def set_retention_policy(self, standard: str):
        """设置数据保留策略"""
        if standard not in self.RETENTION_POLICIES:
            raise ValueError(f"未知的合规标准: {standard}")
        self.compliance_standard = standard
    
    def export_user_data(self, user_id: str) -> dict:
        """导出用户数据，支持GDPR数据可携带权"""
        # 收集该用户的所有数据
        data = {
            "user_id": user_id,
            "agents": self._get_user_agents(user_id),
            "conversations": self._get_user_conversations(user_id),
            "audit_logs": self._get_user_audit_logs(user_id),
            "export_time": datetime.utcnow().isoformat()
        }
        return data
    
    def delete_user_data(self, user_id: str):
        """删除用户数据，支持GDPR被遗忘权"""
        # 记录删除操作
        self.audit_logger.log(
            action="DATA_DELETE",
            resource_type="user",
            resource_id=user_id,
            metadata={"reason": "user_request", "compliance": "gdpr"}
        )
        
        # 执行删除
        self._delete_user_agents(user_id)
        self._delete_user_conversations(user_id)
        self._anonymize_audit_logs(user_id)
    
    def generate_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """生成合规报告"""
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "standard": self.compliance_standard,
            "summary": {
                "total_agents": self._count_agents(start_date, end_date),
                "total_conversations": self._count_conversations(start_date, end_date),
                "total_api_calls": self._count_api_calls(start_date, end_date),
                "data_retention_days": self.RETENTION_POLICIES[self.compliance_standard]
            },
            "security_events": self._get_security_events(start_date, end_date),
            "access_violations": self._get_access_violations(start_date, end_date)
        }
```

---

## 五、开发者体验

### 5.1 IDE插件

#### 代码提示

设计IDE插件的智能提示功能：

```python
# LSP服务器实现
class SmolagentsLanguageServer:
    """smolagents语言服务器协议实现"""
    
    def __init__(self):
        self.tool_registry = {}
        self.agent_schemas = {}
    
    def on_completion(self, params: dict) -> list[dict]:
        """代码补全"""
        uri = params["textDocument"]["uri"]
        position = params["position"]
        
        # 获取当前上下文
        context = self._get_completion_context(uri, position)
        
        completions = []
        
        # 工具补全
        if context.is_tool_argument:
            for tool in self.tool_registry.values():
                completions.append({
                    "label": tool.name,
                    "kind": 3,  # Function
                    "detail": tool.description,
                    "documentation": self._generate_tool_doc(tool),
                    "insertText": self._generate_snippet(tool)
                })
        
        # Agent配置补全
        if context.is_agent_config:
            completions.extend(self._get_agent_config_completions())
        
        return completions
    
    def on_hover(self, params: dict) -> dict:
        """悬停提示"""
        uri = params["textDocument"]["uri"]
        position = params["position"]
        
        # 获取光标下的符号
        symbol = self._get_symbol_at_position(uri, position)
        
        if symbol.type == "tool":
            tool = self.tool_registry.get(symbol.name)
            if tool:
                return {
                    "contents": {
                        "kind": "markdown",
                        "value": self._format_tool_documentation(tool)
                    }
                }
        
        return None
```

#### 调试支持

实现Agent调试功能：

```python
class AgentDebugger:
    """Agent调试器"""
    
    def __init__(self):
        self.breakpoints: set[int] = set()
        self.step_mode = False
        self.paused = False
        self.current_step = None
    
    def set_breakpoint(self, step_number: int):
        """设置断点"""
        self.breakpoints.add(step_number)
    
    def remove_breakpoint(self, step_number: int):
        """移除断点"""
        self.breakpoints.discard(step_number)
    
    def on_step_start(self, step: MemoryStep):
        """步骤开始时检查断点"""
        step_num = getattr(step, "step_number", 0)
        
        if step_num in self.breakpoints or self.step_mode:
            self.paused = True
            self.current_step = step
            
            # 触发调试事件
            self._emit_debug_event({
                "type": "breakpoint_hit",
                "step": step_num,
                "memory": self._serialize_step(step)
            })
            
            # 等待继续信号
            self._wait_for_continue()
    
    def step_over(self):
        """单步跳过"""
        self.step_mode = True
        self.paused = False
    
    def step_into(self):
        """单步进入"""
        self.step_mode = True
        self.paused = False
    
    def continue_execution(self):
        """继续执行"""
        self.step_mode = False
        self.paused = False
    
    def inspect_memory(self) -> dict:
        """检查当前内存状态"""
        if not self.current_step:
            return {}
        
        return {
            "current_step": self._serialize_step(self.current_step),
            "observations": getattr(self.current_step, "observations", None),
            "tool_calls": getattr(self.current_step, "tool_calls", None),
            "token_usage": getattr(self.current_step, "token_usage", None)
        }
```

### 5.2 调试工具

#### 执行追踪

实现详细的执行追踪：

```python
class ExecutionTracer:
    """执行追踪器"""
    
    def __init__(self):
        self.traces: list[dict] = []
        self.enabled = True
    
    def trace_llm_call(
        self,
        messages: list[dict],
        response: str,
        duration_ms: float,
        token_usage: dict
    ):
        """追踪LLM调用"""
        if not self.enabled:
            return
        
        self.traces.append({
            "type": "llm_call",
            "timestamp": time.time(),
            "input_messages": messages,
            "response": response,
            "duration_ms": duration_ms,
            "token_usage": token_usage
        })
    
    def trace_tool_execution(
        self,
        tool_name: str,
        arguments: dict,
        result: Any,
        duration_ms: float,
        error: Exception = None
    ):
        """追踪工具执行"""
        if not self.enabled:
            return
        
        self.traces.append({
            "type": "tool_execution",
            "timestamp": time.time(),
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
            "duration_ms": duration_ms,
            "error": str(error) if error else None
        })
    
    def trace_reasoning(
        self,
        step_number: int,
        thought: str,
        action: str
    ):
        """追踪推理过程"""
        if not self.enabled:
            return
        
        self.traces.append({
            "type": "reasoning",
            "timestamp": time.time(),
            "step_number": step_number,
            "thought": thought,
            "action": action
        })
    
    def export_trace(self, format: str = "json") -> str:
        """导出追踪数据"""
        if format == "json":
            return json.dumps(self.traces, indent=2, default=str)
        elif format == "html":
            return self._generate_html_report()
        else:
            raise ValueError(f"不支持的格式: {format}")
```

#### 状态查看

实现Agent状态可视化：

```python
class StateInspector:
    """状态检查器"""
    
    def __init__(self, agent: MultiStepAgent):
        self.agent = agent
    
    def get_full_state(self) -> dict:
        """获取完整状态"""
        return {
            "agent_info": {
                "name": self.agent.name,
                "class": self.agent.__class__.__name__,
                "max_steps": self.agent.max_steps,
                "current_step": len(self.agent.memory.steps)
            },
            "memory": self._serialize_memory(),
            "tools": self._list_tools(),
            "managed_agents": self._list_managed_agents(),
            "model": self._get_model_info()
        }
    
    def _serialize_memory(self) -> dict:
        """序列化内存"""
        return {
            "system_prompt": self.agent.memory.system_prompt,
            "steps": [
                {
                    "type": step.__class__.__name__,
                    "index": i,
                    "content": self._serialize_step(step)
                }
                for i, step in enumerate(self.agent.memory.steps)
            ]
        }
    
    def get_step_detail(self, step_index: int) -> dict:
        """获取特定步骤详情"""
        if step_index >= len(self.agent.memory.steps):
            raise ValueError(f"无效步骤索引: {step_index}")
        
        step = self.agent.memory.steps[step_index]
        
        return {
            "index": step_index,
            "type": step.__class__.__name__,
            "raw": self._serialize_step(step),
            "token_usage": getattr(step, "token_usage", None),
            "duration_ms": getattr(step, "duration", None)
        }
```

### 5.3 可视化界面

#### Web UI

设计Web管理界面：

```python
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

class SmolagentsWebUI:
    """smolagents Web界面"""
    
    def __init__(self):
        self.app = FastAPI(title="smolagents Dashboard")
        self._setup_routes()
        self._setup_websocket()
    
    def _setup_routes(self):
        """设置API路由"""
        
        @self.app.get("/api/agents")
        async def list_agents():
            """列出所有Agent"""
            return {
                "agents": [
                    {
                        "id": agent.id,
                        "name": agent.name,
                        "status": agent.status,
                        "last_run": agent.last_run_time
                    }
                    for agent in self.agent_registry.values()
                ]
            }
        
        @self.app.get("/api/agents/{agent_id}/runs")
        async def get_agent_runs(agent_id: str, limit: int = 10):
            """获取Agent运行历史"""
            runs = self.run_history.get(agent_id, [])
            return {"runs": runs[-limit:]}
        
        @self.app.post("/api/agents/{agent_id}/run")
        async def run_agent(agent_id: str, task: str):
            """执行Agent"""
            agent = self.agent_registry.get(agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent不存在")
            
            result = await asyncio.to_thread(agent.run, task)
            return {"result": result}
        
        @self.app.get("/api/traces/{trace_id}")
        async def get_trace(trace_id: str):
            """获取追踪数据"""
            trace = self.trace_storage.get(trace_id)
            if not trace:
                raise HTTPException(status_code=404, detail="追踪不存在")
            return trace
    
    def _setup_websocket(self):
        """设置WebSocket实时更新"""
        
        @self.app.websocket("/ws/agent/{agent_id}")
        async def agent_websocket(websocket: WebSocket, agent_id: str):
            await websocket.accept()
            
            # 订阅Agent事件
            self.event_bus.subscribe(
                f"agent.{agent_id}",
                lambda event: websocket.send_json(event)
            )
            
            try:
                while True:
                    # 保持连接
                    await websocket.receive_text()
            except:
                pass
```

#### 实时监控

实现实时监控仪表板：

```python
class RealtimeMonitor:
    """实时监控"""
    
    def __init__(self):
        self.metrics_buffer = deque(maxlen=1000)
        self.active_connections: list[WebSocket] = []
    
    def record_metric(self, metric_type: str, value: float, labels: dict):
        """记录指标"""
        metric = {
            "timestamp": time.time(),
            "type": metric_type,
            "value": value,
            "labels": labels
        }
        
        self.metrics_buffer.append(metric)
        
        # 广播给所有连接
        asyncio.create_task(self._broadcast(metric))
    
    async def _broadcast(self, metric: dict):
        """广播指标更新"""
        disconnected = []
        
        for conn in self.active_connections:
            try:
                await conn.send_json(metric)
            except:
                disconnected.append(conn)
        
        # 清理断开连接
        for conn in disconnected:
            self.active_connections.remove(conn)
    
    def get_dashboard_data(self) -> dict:
        """获取仪表板数据"""
        return {
            "active_agents": self._count_active_agents(),
            "requests_per_second": self._calculate_rps(),
            "average_latency": self._calculate_avg_latency(),
            "error_rate": self._calculate_error_rate(),
            "top_tools": self._get_top_tools(),
            "recent_traces": list(self.metrics_buffer)[-50:]
        }
    
    def _calculate_rps(self) -> float:
        """计算每秒请求数"""
        now = time.time()
        recent = [m for m in self.metrics_buffer 
                  if m["timestamp"] > now - 60]
        return len(recent) / 60 if recent else 0
```

---

## 六、功能优先级

### 6.1 优先级矩阵

根据价值和实现复杂度对功能进行排序：

| 优先级 | 功能模块 | 具体功能 | 价值 | 复杂度 | 推荐版本 |
|--------|----------|----------|------|--------|----------|
| P0 | 可观测性 | OpenTelemetry基础集成 | 高 | 中 | v1.1 |
| P0 | 持久化 | Checkpoint自动保存 | 高 | 中 | v1.1 |
| P0 | 多Agent | 并行子Agent调用 | 高 | 中 | v1.1 |
| P1 | 可观测性 | Prometheus指标导出 | 高 | 低 | v1.2 |
| P1 | 持久化 | 对话历史数据库存储 | 高 | 中 | v1.2 |
| P1 | 开发者体验 | 执行追踪工具 | 中 | 低 | v1.2 |
| P2 | 多Agent | 消息总线 | 中 | 高 | v1.3 |
| P2 | 多Agent | 共享内存 | 中 | 中 | v1.3 |
| P2 | 持久化 | 状态版本管理 | 中 | 高 | v1.3 |
| P3 | 企业级 | 多租户 | 高 | 高 | v2.0 |
| P3 | 企业级 | RBAC | 中 | 中 | v2.0 |
| P3 | 企业级 | 审计日志 | 中 | 中 | v2.0 |
| P4 | 开发者体验 | Web UI | 中 | 高 | v2.1 |
| P4 | 开发者体验 | IDE插件 | 低 | 高 | v2.2 |

### 6.2 版本路线图

#### v1.1 - 生产就绪基础

目标：让smolagents具备生产环境部署的基本能力

核心功能：
- OpenTelemetry基础集成：Trace、Metrics、Logs
- Checkpoint自动保存与恢复
- 并行子Agent调用
- 基础API密钥管理

#### v1.2 - 运维增强

目标：提升可运维性和问题排查能力

核心功能：
- Prometheus指标导出
- 对话历史持久化存储
- 执行追踪工具
- 错误告警机制

#### v1.3 - 多Agent增强

目标：提升多Agent系统的协作能力

核心功能：
- 异步消息总线
- Agent间共享内存
- 状态版本管理
- 高级结果聚合策略

#### v2.0 - 企业级特性

目标：满足大型企业部署需求

核心功能：
- 多租户数据隔离
- RBAC访问控制
- 审计日志与合规
- API密钥生命周期管理

#### v2.1+ - 开发者体验

目标：降低开发和调试门槛

核心功能：
- Web管理界面
- 实时监控仪表板
- IDE插件
- 调试工具链

### 6.3 实施建议

#### 快速收益项目

这些功能可以在短时间内实现并产生明显价值：

1. **Prometheus指标导出**：监控基础完善，实施简单
2. **执行追踪工具**：对开发者价值高，实施难度低
3. **API密钥管理**：安全基础，实施中等

#### 需要架构调整的项目

这些功能需要较大的架构改动：

1. **多租户支持**：需要修改数据访问层
2. **消息总线**：需要引入异步架构
3. **Web UI**：需要独立的frontend开发

#### 依赖关系

```
OpenTelemetry基础集成
    ├── Prometheus指标导出
    └── 执行追踪工具

Checkpoint机制
    ├── 对话历史存储
    └── 状态版本管理

多Agent增强
    ├── 并行调用
    ├── 消息总线
    └── 共享内存

企业级功能
    ├── 多租户
    ├── RBAC
    └── 审计日志
```

---

## 七、原型代码

### 7.1 完整使用示例

以下代码展示如何在一个项目中使用上述增强功能：

```python
# ========== 初始化配置 ==========

from smolagents import CodeAgent, ToolCallingAgent
from smolagents.enterprise import (
    CheckpointManager,
    MessageBus,
    ParallelAgentExecutor,
    SmolagentsTracer,
    PrometheusExporter,
    MultiTenantManager,
    RBACManager
)

# 初始化追踪
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

# 初始化Checkpoint管理器
checkpoint_manager = CheckpointManager(
    storage_backend="s3",  # 或 "local", "redis"
    storage_config={
        "bucket": "agent-checkpoints",
        "region": "us-east-1"
    },
    save_interval=5
)

# 初始化消息总线
message_bus = MessageBus()
message_bus.start()

# 初始化Prometheus导出
prometheus = PrometheusExporter()

# ========== 创建Agent ==========

# 创建子Agent
research_agent = ToolCallingAgent(
    name="researcher",
    description="执行信息检索",
    tools=[WebSearchTool(), DocumentReaderTool()],
    model=fast_model,
    max_steps=5
)

code_agent = ToolCallingAgent(
    name="coder",
    description="生成和执行代码",
    tools=[PythonInterpreterTool(), CodeValidatorTool()],
    model=fast_model,
    max_steps=10
)

analyst_agent = ToolCallingAgent(
    name="analyst",
    description="分析数据并生成报告",
    tools=[DataAnalyzerTool(), ReportGeneratorTool()],
    model=fast_model,
    max_steps=8
)

# 创建主Agent
manager = CodeAgent(
    name="analysis_manager",
    description="协调数据分析工作流",
    model=strong_model,
    managed_agents=[research_agent, code_agent, analyst_agent],
    checkpoint_manager=checkpoint_manager,
    message_bus=message_bus
)

# ========== 并行执行示例 ==========

async def parallel_analysis(query: str):
    """并行执行多个分析任务"""
    
    executor = ParallelAgentExecutor(max_workers=3)
    
    tasks = [
        {
            "agent": research_agent,
            "task": f"搜索相关信息: {query}",
            "timeout": 60
        },
        {
            "agent": code_agent,
            "task": f"生成数据处理代码: {query}",
            "timeout": 120
        },
        {
            "agent": analyst_agent,
            "task": f"分析需求: {query}",
            "timeout": 90
        }
    ]
    
    # 并行执行
    results = await executor.execute_parallel(tasks)
    
    # 聚合结果
    aggregator = ResultAggregator(strategy="merge")
    final_result = aggregator.aggregate(results)
    
    return final_result

# ========== 多租户示例 ==========

# 初始化多租户管理
tenant_manager = MultiTenantManager(
    db_engine=create_engine("postgresql://..."),
    redis_client=redis.Redis()
)

# 创建租户
tenant = tenant_manager.create_tenant(
    name="acme-corp",
    quotas={
        "rpm": 100,
        "tpd": 1000000,
        "agents": 20,
        "storage": 5000
    }
)

# 在租户上下文中运行Agent
with tenant_manager.with_tenant(tenant.id):
    result = manager.run("分析Q4销售数据")

# ========== 访问控制示例 ==========

rbac = RBACManager()

# 定义角色权限
rbac.define_role(
    "data_analyst",
    permissions=[
        Permission.AGENT_READ,
        Permission.AGENT_RUN,
        Permission.TOOL_USE
    ]
)

rbac.define_role(
    "admin",
    permissions=[Permission.ADMIN]
)

# 分配角色
rbac.assign_role("user-123", "data_analyst")

# 受保护的Agent操作
@rbac.require_permission(Permission.AGENT_CREATE)
def create_new_agent(config: dict, user_id: str):
    return CodeAgent(**config)

# ========== 完整工作流示例 ==========

async def full_workflow_example():
    """完整工作流示例"""
    
    # 1. 设置租户和权限
    tenant_id = "tenant-123"
    user_id = "user-456"
    
    with tenant_manager.with_tenant(tenant_id):
        # 检查配额
        if not tenant_manager.check_quota(tenant_id, "agents", 1):
            raise QuotaExceededError("Agent数量超出配额")
        
        # 2. 启用追踪
        tracer = SmolagentsTracer()
        instrumented_agent = tracer.instrument_agent(manager)
        
        # 3. 设置Checkpoint
        checkpoint_manager.attach_to_agent(instrumented_agent)
        
        # 4. 执行任务
        try:
            # 检查是否有未完成的检查点
            last_checkpoint = checkpoint_manager.get_latest(tenant_id)
            
            if last_checkpoint and last_checkpoint.status == "interrupted":
                # 从检查点恢复
                agent = checkpoint_manager.restore(last_checkpoint.id)
                result = agent.resume()
            else:
                # 新任务
                result = instrumented_agent.run(
                    "分析竞争对手的财务数据并生成报告",
                    additional_args={
                        "user_id": user_id,
                        "tenant_id": tenant_id
                    }
                )
            
            # 5. 记录审计日志
            audit_logger.log(
                action="AGENT_RUN",
                resource_type="agent",
                resource_id=instrumented_agent.name,
                user_id=user_id,
                tenant_id=tenant_id,
                metadata={
                    "result_length": len(str(result)),
                    "steps": len(instrumented_agent.memory.steps)
                }
            )
            
            return result
            
        except Exception as e:
            # 错误时自动保存检查点
            checkpoint_manager.create_emergency_checkpoint(
                agent=instrumented_agent,
                error=e
            )
            raise

# ========== 监控集成示例 ==========

from fastapi import FastAPI
from prometheus_client import make_asgi_app

app = FastAPI()

# 添加Prometheus端点
prometheus_app = make_asgi_app()
app.mount("/metrics", prometheus_app)

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "active_agents": len(active_agents),
        "queue_depth": message_bus.queue.qsize()
    }

@app.get("/api/v1/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """获取Agent状态"""
    agent = agent_registry.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404)
    
    inspector = StateInspector(agent)
    return inspector.get_full_state()

# 启动监控
@app.on_event("startup")
async def start_monitoring():
    # 启动指标收集
    metrics_collector = SmolagentsMetrics()
    metrics_collector.start_collection(interval=10)
    
    # 启动实时监视器
    monitor = RealtimeMonitor()
    await monitor.start()
```

### 7.2 配置示例

```yaml
# smolagents.yaml - 完整配置示例

# 持久化配置
persistence:
  checkpoint:
    enabled: true
    backend: s3  # local, s3, redis, postgres
    interval_steps: 5
    interval_seconds: 300
    s3:
      bucket: agent-checkpoints
      region: us-east-1
      prefix: checkpoints/
  
  history:
    backend: postgres
    connection_string: postgresql://user:pass@localhost/smolagents
    retention_days: 90
  
  versioning:
    enabled: true
    max_versions: 100

# 多Agent配置
multi_agent:
  message_bus:
    type: redis  # in_memory, redis, rabbitmq
    redis:
      host: localhost
      port: 6379
      db: 0
  
  parallel:
    max_workers: 10
    default_timeout: 60
  
  shared_memory:
    backend: redis
    namespace: smolagents_shared

# 可观测性配置
observability:
  opentelemetry:
    enabled: true
    exporter: otlp  # otlp, console, jaeger
    otlp:
      endpoint: http://localhost:4317
      insecure: true
  
  prometheus:
    enabled: true
    port: 9090
    path: /metrics
  
  tracing:
    sample_rate: 1.0  # 1.0 = 100%
    include_prompts: false  # 是否记录提示词内容
  
  logging:
    level: INFO
    format: json
    output: stdout

# 企业级配置
enterprise:
  multi_tenant:
    enabled: true
    isolation_level: strict  # strict, logical
    default_quotas:
      rpm: 60
      tpd: 100000
      agents: 10
      storage_mb: 1000
  
  rbac:
    enabled: true
    default_roles:
      - admin
      - developer
      - viewer
  
  audit:
    enabled: true
    storage: postgres
    retention_years: 7
    include_full_state: false
  
  api_keys:
    enabled: true
    rotation_days: 90
    hash_algorithm: sha256

# 开发者体验配置
devex:
  web_ui:
    enabled: true
    port: 8080
    auth: true
  
  debug:
    enabled: false  # 生产环境应关闭
    trace_llm_calls: true
    trace_tool_calls: true
    max_trace_size_mb: 100
```

### 7.3 部署示例

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装smolagents及企业级扩展
RUN pip install smolagents[enterprise,observability]

# 复制代码
COPY src/ ./src/
COPY config.yaml .

# 暴露端口
EXPOSE 8080 9090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# 启动命令
CMD ["python", "-m", "smolagents.server", "--config", "config.yaml"]
```

```yaml
# docker-compose.yaml
version: '3.8'

services:
  smolagents:
    build: .
    ports:
      - "8080:8080"  # Web UI
      - "9090:9090"  # Prometheus metrics
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/smolagents
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./config.yaml:/app/config.yaml
    depends_on:
      - db
      - redis
      - otel-collector

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
      POSTGRES_DB: smolagents
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  otel-collector:
    image: otel/opentelemetry-collector:latest
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ./otel-config.yaml:/etc/otel-collector-config.yaml
    ports:
      - "4317:4317"  # OTLP gRPC

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yaml:/etc/prometheus/prometheus.yaml
      - prometheus_data:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana-dashboards:/etc/grafana/provisioning/dashboards

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

---

## 八、总结

本设计建议针对 smolagents 在生产环境部署中的关键需求，提出了六个维度的功能增强方案。参考现有架构分析 [[14-smolagents-持久化与导入导出]] 和 [[27-smolagents-多Agent通信机制与返回结构深度分析]]，识别出以下关键改进点：

**高优先级改进**：

1. **可观测性**：OpenTelemetry集成让系统运行状态透明可查
2. **持久化**：Checkpoint机制支持任务中断恢复和状态回滚
3. **并行执行**：多Agent并行调用大幅提升复杂任务处理效率

**中长期改进**：

1. **多Agent增强**：消息总线和共享内存让Agent协作更灵活
2. **企业级功能**：多租户和RBAC满足大型组织部署需求
3. **开发者体验**：调试工具和Web界面降低开发门槛

实施建议遵循渐进式策略，先完成基础可观测性和持久化功能，再逐步引入企业级特性。这样可以让smolagents从实验性框架进化为生产就绪的企业级平台。

---

*关联文档：*
- [[14-smolagents-持久化与导入导出]]
- [[27-smolagents-多Agent通信机制与返回结构深度分析]]
- [[06-smolagents-多Agent系统深度分析]]
