# smolagents 性能优化指南

> 项目: AI数据分析系统  
> 分析对象: smolagents 1.12.0  
> 更新日期: 2026-02-06

---

## 一、Token优化

### 1.1 上下文压缩技术

smolagents 本身没有内置上下文截断机制，需要自行实现压缩策略。

**方案一：滑动窗口截断**

保留最近的 N 个步骤，丢弃早期历史：

```python
class ContextCompressor:
    def __init__(self, max_steps: int = 10):
        self.max_steps = max_steps
    
    def compress_memory(self, memory: AgentMemory) -> list[ChatMessage]:
        # 始终保留系统提示和初始任务
        messages = memory.system_prompt.to_messages()
        
        # 过滤步骤，只保留最近 max_steps 个 ActionStep
        recent_steps = [
            step for step in memory.steps 
            if isinstance(step, ActionStep)
        ][-self.max_steps:]
        
        # 添加规划步骤和任务步骤
        for step in memory.steps:
            if isinstance(step, TaskStep):
                messages.extend(step.to_messages())
            elif isinstance(step, PlanningStep):
                messages.extend(step.to_messages())
        
        # 添加最近的 ActionStep
        for step in recent_steps:
            messages.extend(step.to_messages())
        
        return messages
```

**方案二：摘要模式精简**

利用 smolagents 内置的 summary_mode：

```python
# 在规划时使用精简模式
planning_messages = agent.write_memory_to_messages(summary_mode=True)

# summary_mode 的行为：
# - SystemPromptStep: 返回空列表
# - PlanningStep: 返回空列表
# - TaskStep: 保留核心信息
# - ActionStep: 保留关键执行结果
```

**方案三：智能步选择**

根据步骤重要性决定保留策略：

```python
def should_keep_step(step: MemoryStep) -> bool:
    if isinstance(step, TaskStep):
        return True  # 始终保留任务
    
    if isinstance(step, ActionStep):
        # 保留出错的步骤
        if step.error is not None:
            return True
        # 保留包含最终答案的步骤
        if step.is_final_answer:
            return True
        # 保留工具调用步骤
        if step.tool_calls:
            return True
    
    return False
```

### 1.2 历史记录截断策略

**Token 预算控制**

```python
class TokenBudgetManager:
    def __init__(self, max_input_tokens: int = 8000):
        self.max_input_tokens = max_input_tokens
        self.token_counter = TokenCounter()
    
    def truncate_to_budget(self, messages: list[ChatMessage]) -> list[ChatMessage]:
        total_tokens = sum(
            self.token_counter.count(m) for m in messages
        )
        
        while total_tokens > self.max_input_tokens and len(messages) > 2:
            # 策略：从中间移除旧的 ActionStep
            # 保留系统提示和最新步骤
            for i, msg in enumerate(messages[1:-1], 1):
                if self._is_removable(msg):
                    removed_tokens = self.token_counter.count(messages[i])
                    messages.pop(i)
                    total_tokens -= removed_tokens
                    break
            else:
                # 无法继续移除
                break
        
        return messages
    
    def _is_removable(self, message: ChatMessage) -> bool:
        # 不移除系统消息和当前任务
        return message.role not in [MessageRole.SYSTEM, MessageRole.USER]
```

**关键指标**

| 场景 | 建议最大Token数 | 说明 |
|------|----------------|------|
| 轻量任务 | 4000 | 简单问答、单步工具调用 |
| 标准任务 | 8000 | 多步骤推理、常规分析 |
| 复杂任务 | 16000 | 深度分析、长文档处理 |
| 超长任务 | 32000 | 代码审查、复杂数据管道 |

### 1.3 Prompt精简技巧

**System Prompt 优化**

CodeAgent 的 System Prompt 比 ToolCallingAgent 长约 30%，可以通过以下方式精简：

```python
# 精简版 CodeAgent Prompt 模板
MINIMAL_CODE_AGENT_PROMPT = """\
You are a coding assistant. Solve tasks using Python code blocks.

Guidelines:
- Use <code> and </code> tags for code
- Use final_answer for results
- Print important intermediate values

Available imports: {authorized_imports}
"""

agent = CodeAgent(
    tools=tools,
    model=model,
    prompt_templates=PromptTemplates(
        system_prompt=MINIMAL_CODE_AGENT_PROMPT
    ),
    additional_authorized_imports=["pandas", "numpy"]
)
```

**工具描述精简**

```python
def create_compact_tool(tool_func, name: str, desc: str):
    """创建精简描述的工具"""
    return Tool(
        name=name,
        description=desc,  # 保持简短，不超过100字
        function=tool_func,
        inputs={
            "query": {
                "type": "string",
                "description": "Search query"
                # 避免冗长的参数描述
            }
        },
        output_type="string"
    )
```

**Prompt 模板变量替换优化**

```python
# 避免在每次调用时重复格式化
cached_prompt = None

def get_cached_system_prompt(agent):
    global cached_prompt
    if cached_prompt is None:
        cached_prompt = agent.system_prompt_template.format(
            authorized_imports=", ".join(agent.authorized_imports),
            tool_descriptions=agent.tool_descriptions,
            current_date=datetime.now().strftime("%Y-%m-%d")
        )
    return cached_prompt
```

### 1.4 缓存机制设计

**系统提示缓存**

```python
class CachedAgent:
    def __init__(self, agent: MultiStepAgent):
        self.agent = agent
        self._system_prompt_cache: str | None = None
    
    @property
    def system_prompt(self) -> str:
        if self._system_prompt_cache is None:
            self._system_prompt_cache = self.agent.system_prompt_template.format(
                tool_descriptions=self.agent.tool_descriptions,
                authorized_imports=self.agent.authorized_imports,
            )
        return self._system_prompt_cache
    
    def invalidate_cache(self):
        """工具变更时调用"""
        self._system_prompt_cache = None
```

**工具结果缓存**

```python
class ToolResultCache:
    def __init__(self, ttl_seconds: int = 300):
        self.cache: dict[str, tuple[Any, float]] = {}
        self.ttl = ttl_seconds
    
    def _make_key(self, tool_name: str, arguments: dict) -> str:
        key_data = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, tool_name: str, arguments: dict) -> Any | None:
        key = self._make_key(tool_name, arguments)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return result
            del self.cache[key]
        return None
    
    def set(self, tool_name: str, arguments: dict, result: Any):
        key = self._make_key(tool_name, arguments)
        self.cache[key] = (result, time.time())
```

### 1.5 重复内容消除

**Observation 去重**

```python
def deduplicate_observations(steps: list[ActionStep]) -> list[ActionStep]:
    """移除重复的观察结果"""
    seen_observations: set[str] = set()
    unique_steps = []
    
    for step in steps:
        if step.observations:
            obs_hash = hashlib.md5(
                step.observations.encode()
            ).hexdigest()
            if obs_hash not in seen_observations:
                seen_observations.add(obs_hash)
                unique_steps.append(step)
        else:
            unique_steps.append(step)
    
    return unique_steps
```

---

## 二、延迟优化

### 2.1 模型选择策略

**速度与质量平衡**

| 模型 | 平均延迟 | 质量评分 | 适用场景 |
|------|---------|---------|---------|
| gpt-4o-mini | 300ms | 75 | 简单任务、快速响应 |
| gpt-4o | 800ms | 90 | 标准任务 |
| claude-3-haiku | 400ms | 78 | 轻量分析 |
| claude-3-sonnet | 1000ms | 92 | 复杂推理 |
| llama-3.1-8b | 200ms | 70 | 本地部署、高并发 |
| llama-3.1-70b | 1500ms | 88 | 复杂任务、深度分析 |

**动态模型切换**

```python
class TieredModelRouter:
    def __init__(self):
        self.fast_model = OpenAIServerModel("gpt-4o-mini")
        self.accurate_model = OpenAIServerModel("gpt-4o")
    
    def select_model(self, task: str, complexity_hint: float = 0.5) -> Model:
        # 基于任务复杂度选择模型
        if complexity_hint < 0.3:
            return self.fast_model
        
        # 简单启发式判断
        simple_keywords = ["查询", "搜索", "获取"]
        if any(kw in task for kw in simple_keywords):
            return self.fast_model
        
        complex_keywords = ["分析", "计算", "推理", "优化"]
        if any(kw in task for kw in complex_keywords):
            return self.accurate_model
        
        # 默认使用快速模型
        return self.fast_model
```

### 2.2 流式输出优化

**流式消费最佳实践**

```python
async def optimized_stream_handler(agent, task: str):
    """优化的流式处理，减少渲染开销"""
    buffer = []
    last_update = time.time()
    update_interval = 0.05  # 50ms 刷新一次
    
    async for event in agent.run(task, stream=True):
        if isinstance(event, ChatMessageStreamDelta):
            buffer.append(event)
            
            # 控制刷新频率
            if time.time() - last_update > update_interval:
                text = agglomerate_stream_deltas(buffer).render_as_markdown()
                yield text
                last_update = time.time()
        
        elif isinstance(event, ActionStep):
            # 步骤完成，清空缓冲区
            buffer = []
            yield f"\n[Step {event.step_number} completed]\n"
```

**跳过非必要渲染**

```python
def create_efficient_agent():
    return CodeAgent(
        tools=tools,
        model=model,
        stream_outputs=True,
        # 关闭详细日志减少IO开销
        logger=AgentLogger(level=LogLevel.ERROR)
    )
```

### 2.3 预热机制

**模型连接预热**

```python
class WarmedUpAgent:
    def __init__(self, agent_factory: Callable):
        self.agent_factory = agent_factory
        self.agent: MultiStepAgent | None = None
    
    async def warmup(self):
        """执行预热查询建立连接池"""
        self.agent = self.agent_factory()
        # 执行一个简单查询预热连接
        await self.agent.run("Hello", max_steps=1)
    
    async def run(self, task: str, **kwargs):
        if self.agent is None:
            await self.warmup()
        return await self.agent.run(task, **kwargs)
```

**执行器预热**

```python
def warmup_code_executor(agent: CodeAgent):
    """预热 Python 执行器环境"""
    warmup_code = """
import pandas as pd
import numpy as np
print("Executor warmed up")
"""
    # 执行一次初始化代码
    agent.python_executor(warmup_code)
```

### 2.4 连接复用

**HTTP 连接池配置**

```python
import httpx

# 为模型客户端配置连接池
class PooledModelClient:
    def __init__(self, api_key: str):
        self.client = httpx.Client(
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10
            ),
            timeout=httpx.Timeout(60.0),
            http2=True
        )
        self.api_key = api_key
    
    def generate(self, messages: list[dict], **kwargs):
        # 复用同一连接池
        response = self.client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"messages": messages, **kwargs}
        )
        return response.json()
```

### 2.5 批量处理

**任务批处理**

```python
async def batch_process(agent: MultiStepAgent, tasks: list[str], 
                        max_workers: int = 5) -> list[Any]:
    """批量处理多个任务"""
    semaphore = asyncio.Semaphore(max_workers)
    
    async def process_single(task: str):
        async with semaphore:
            return await agent.run(task)
    
    results = await asyncio.gather(
        *[process_single(t) for t in tasks],
        return_exceptions=True
    )
    return results
```

---

## 三、并发优化

### 3.1 多请求并发处理

**Agent 级别的并发**

```python
class ConcurrentAgentPool:
    def __init__(self, agent_factory: Callable, pool_size: int = 5):
        self.agents: list[MultiStepAgent] = [
            agent_factory() for _ in range(pool_size)
        ]
        self.queue: asyncio.Queue = asyncio.Queue()
        self.results: dict[str, Any] = {}
    
    async def submit(self, task_id: str, task: str):
        await self.queue.put((task_id, task))
    
    async def start_workers(self):
        async def worker(agent: MultiStepAgent):
            while True:
                task_id, task = await self.queue.get()
                try:
                    result = await agent.run(task)
                    self.results[task_id] = result
                except Exception as e:
                    self.results[task_id] = e
                finally:
                    self.queue.task_done()
        
        await asyncio.gather(*[
            worker(agent) for agent in self.agents
        ])
```

### 3.2 连接池配置

**ToolCallingAgent 线程池优化**

```python
from concurrent.futures import ThreadPoolExecutor

# 根据任务特性调整线程数
# CPU 密集型：线程数 <= CPU核心数
# IO 密集型：线程数可以更高

def calculate_optimal_threads() -> int:
    cpu_count = os.cpu_count() or 4
    # IO 密集型任务，可以设置 2-4 倍 CPU 核心数
    return min(cpu_count * 2, 16)

agent = ToolCallingAgent(
    tools=[web_search, api_call, database_query],
    model=model,
    max_tool_threads=calculate_optimal_threads()
)
```

### 3.3 异步执行模式

**异步工具封装**

```python
import asyncio
from functools import partial

class AsyncToolWrapper:
    def __init__(self, tool: Tool, executor: ThreadPoolExecutor):
        self.tool = tool
        self.executor = executor
    
    async def execute(self, **kwargs) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            partial(self.tool.function, **kwargs)
        )

# 使用示例
executor = ThreadPoolExecutor(max_workers=10)
async_tools = [AsyncToolWrapper(t, executor) for t in tools]
```

**完全异步 Agent**

```python
class AsyncCodeAgent(CodeAgent):
    async def arun(self, task: str, **kwargs):
        """异步运行接口"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            partial(self.run, task, **kwargs)
        )
```

### 3.4 资源竞争避免

**执行器隔离**

```python
from threading import Lock

class IsolatedExecutor:
    def __init__(self):
        self.lock = Lock()
        self.executor = LocalPythonExecutor()
    
    def execute(self, code: str):
        with self.lock:
            # 确保同一时间只有一个代码块执行
            return self.executor(code)

# 每个 Agent 使用独立的执行器
agents = [
    CodeAgent(
        tools=tools,
        model=model,
        executor=IsolatedExecutor()
    )
    for _ in range(5)
]
```

**状态隔离**

```python
class StatelessAgentFactory:
    """创建无状态 Agent 避免状态竞争"""
    
    def create_agent(self) -> MultiStepAgent:
        # 每次创建新的执行器实例
        return CodeAgent(
            tools=self.tools,
            model=self.model,
            executor=self.create_fresh_executor()
        )
```

---

## 四、内存优化

### 4.1 Memory管理策略

**步骤数据精简**

```python
class MemoryOptimizedAgent:
    def __init__(self, agent: MultiStepAgent, 
                 max_steps_in_memory: int = 20):
        self.agent = agent
        self.max_steps = max_steps_in_memory
    
    def run_with_memory_limit(self, task: str):
        result = self.agent.run(task)
        
        # 执行后清理旧步骤
        if len(self.agent.memory.steps) > self.max_steps:
            # 保留系统提示和最近步骤
            self.agent.memory.steps = (
                [s for s in self.agent.memory.steps 
                 if isinstance(s, TaskStep)] +
                [s for s in self.agent.memory.steps 
                 if isinstance(s, ActionStep)][-self.max_steps:]
            )
        
        return result
```

**定期清理机制**

```python
class PeriodicMemoryCleaner:
    def __init__(self, agent: MultiStepAgent, 
                 cleanup_interval: int = 10):
        self.agent = agent
        self.step_count = 0
        self.interval = cleanup_interval
    
    def maybe_cleanup(self):
        self.step_count += 1
        if self.step_count % self.interval == 0:
            self._cleanup_large_fields()
    
    def _cleanup_large_fields(self):
        """清理占用内存较大的字段"""
        for step in self.agent.memory.steps:
            if isinstance(step, ActionStep):
                # 清理图片数据
                if step.observations_images:
                    step.observations_images = None
                # 清理详细的输入消息
                if step.model_input_messages:
                    step.model_input_messages = [
                        m for m in step.model_input_messages
                        if m.role == MessageRole.USER
                    ][:5]  # 只保留最近5条
```

### 4.2 大对象处理

**图片数据处理优化**

```python
class OptimizedImageHandling:
    def __init__(self, max_image_size: tuple[int, int] = (1024, 1024)):
        self.max_size = max_image_size
    
    def process_image(self, image: PIL.Image.Image) -> PIL.Image.Image:
        """压缩图片减少内存占用"""
        if image.size[0] > self.max_size[0] or \
           image.size[1] > self.max_size[1]:
            image.thumbnail(self.max_size)
        
        # 转换为更节省内存的格式
        if image.mode not in ['RGB', 'L']:
            image = image.convert('RGB')
        
        return image
    
    def clear_image_cache(self, memory: AgentMemory):
        """清除图片缓存"""
        for step in memory.steps:
            if isinstance(step, ActionStep):
                step.observations_images = None
```

**大型结果分页**

```python
class PagedResultHandler:
    def __init__(self, page_size: int = 1000):
        self.page_size = page_size
    
    def paginate_large_result(self, result: Any) -> Iterator[Any]:
        if isinstance(result, list) and len(result) > self.page_size:
            for i in range(0, len(result), self.page_size):
                yield result[i:i + self.page_size]
        else:
            yield result
```

### 4.3 内存泄漏排查

**内存监控装饰器**

```python
import tracemalloc
import functools

def memory_tracker(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        start_mem = tracemalloc.get_traced_memory()
        
        try:
            result = func(*args, **kwargs)
        finally:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            print(f"Function: {func.__name__}")
            print(f"Current memory: {current / 1024 / 1024:.2f} MB")
            print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
            print(f"Memory delta: {(current - start_mem[0]) / 1024 / 1024:.2f} MB")
        
        return result
    return wrapper

# 使用示例
@memory_tracker
def run_agent_task(agent, task):
    return agent.run(task)
```

**常见泄漏点检查清单**

| 检查项 | 泄漏风险 | 检查方法 |
|--------|---------|---------|
| 步骤列表无限增长 | 高 | 检查 memory.steps 长度 |
| 图片数据未清理 | 高 | 检查 observations_images |
| 回调函数闭包引用 | 中 | 检查 step_callbacks |
| 模型连接未关闭 | 中 | 检查 httpx 客户端 |
| 执行器状态累积 | 低 | 检查 executor 状态 |

### 4.4 垃圾回收优化

**显式垃圾回收**

```python
import gc

class GCOptimizedAgent:
    def __init__(self, gc_threshold: int = 100):
        self.gc_threshold = gc_threshold
        self.step_count = 0
    
    def after_step(self):
        self.step_count += 1
        if self.step_count >= self.gc_threshold:
            gc.collect()
            self.step_count = 0
```

---

## 五、成本优化

### 5.1 模型切换策略

**分层模型策略**

```python
class TieredModelStrategy:
    def __init__(self):
        self.tiers = {
            "fast": {
                "model": OpenAIServerModel("gpt-4o-mini"),
                "cost_per_1k": 0.00015,
                "max_tokens": 4000
            },
            "standard": {
                "model": OpenAIServerModel("gpt-4o"),
                "cost_per_1k": 0.005,
                "max_tokens": 8000
            },
            "premium": {
                "model": OpenAIServerModel("gpt-4o-2024-08-06"),
                "cost_per_1k": 0.015,
                "max_tokens": 16000
            }
        }
    
    def select_tier(self, task_complexity: float, 
                    accuracy_required: float) -> str:
        if task_complexity < 0.3 and accuracy_required < 0.8:
            return "fast"
        elif task_complexity < 0.7 and accuracy_required < 0.95:
            return "standard"
        else:
            return "premium"
```

### 5.2 Token预算控制

**实时预算监控**

```python
class TokenBudgetController:
    def __init__(self, daily_budget: float = 10.0):
        self.daily_budget = daily_budget
        self.daily_tokens = 0
        self.cost_per_1k = 0.005  # gpt-4o 价格
    
    def check_budget(self, estimated_tokens: int) -> bool:
        estimated_cost = (estimated_tokens / 1000) * self.cost_per_1k
        current_cost = (self.daily_tokens / 1000) * self.cost_per_1k
        return (current_cost + estimated_cost) <= self.daily_budget
    
    def record_usage(self, tokens: int):
        self.daily_tokens += tokens
        
        # 预算告警
        current_cost = (self.daily_tokens / 1000) * self.cost_per_1k
        if current_cost > self.daily_budget * 0.8:
            print(f"Warning: Daily budget 80% consumed")
```

**步骤级别限制**

```python
class StepBudgetAgent:
    def __init__(self, max_tokens_per_step: int = 2000,
                 max_steps: int = 5):
        self.max_tokens_per_step = max_tokens_per_step
        self.max_steps = max_steps
        self.token_usage_log: list[int] = []
    
    def should_stop(self, current_step: int, 
                    step_tokens: int) -> bool:
        self.token_usage_log.append(step_tokens)
        
        # 检查单步token限制
        if step_tokens > self.max_tokens_per_step:
            return True
        
        # 检查总步数限制
        if current_step >= self.max_steps:
            return True
        
        return False
```

### 5.3 智能降级机制

**故障转移策略**

```python
class FallbackModelChain:
    def __init__(self, models: list[Model]):
        self.models = models
        self.failure_counts: dict[int, int] = {i: 0 for i in range(len(models))}
        self.max_failures = 3
    
    async def generate_with_fallback(self, messages: list[ChatMessage]):
        for idx, model in enumerate(self.models):
            if self.failure_counts[idx] >= self.max_failures:
                continue
            
            try:
                result = await model.generate(messages)
                return result
            except Exception as e:
                self.failure_counts[idx] += 1
                print(f"Model {idx} failed: {e}")
                continue
        
        raise Exception("All models failed")
```

**结果缓存降级**

```python
class CachedFallbackAgent:
    def __init__(self, agent: MultiStepAgent, cache_ttl: int = 3600):
        self.agent = agent
        self.cache: dict[str, tuple[Any, float]] = {}
        self.ttl = cache_ttl
    
    async def run(self, task: str) -> Any:
        # 检查缓存
        cached = self.cache.get(task)
        if cached and time.time() - cached[1] < self.ttl:
            return cached[0]
        
        try:
            result = await self.agent.run(task)
            self.cache[task] = (result, time.time())
            return result
        except Exception as e:
            # 如果执行失败且有缓存，返回缓存结果
            if cached:
                print(f"Using stale cache due to error: {e}")
                return cached[0]
            raise
```

### 5.4 用量监控

**详细用量报告**

```python
class UsageMonitor:
    def __init__(self):
        self.usage_log: list[dict] = []
    
    def record_step(self, step: ActionStep):
        self.usage_log.append({
            "step_number": step.step_number,
            "input_tokens": step.token_usage.input_tokens if step.token_usage else 0,
            "output_tokens": step.token_usage.output_tokens if step.token_usage else 0,
            "timestamp": time.time(),
            "duration": step.timing.duration if step.timing else 0
        })
    
    def generate_report(self) -> dict:
        total_input = sum(u["input_tokens"] for u in self.usage_log)
        total_output = sum(u["output_tokens"] for u in self.usage_log)
        total_duration = sum(u["duration"] for u in self.usage_log)
        
        return {
            "total_steps": len(self.usage_log),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "estimated_cost_usd": self._calculate_cost(total_input, total_output),
            "avg_duration_ms": (total_duration / len(self.usage_log) * 1000) 
                               if self.usage_log else 0
        }
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        # gpt-4o 定价
        input_cost = (input_tokens / 1000) * 0.0025
        output_cost = (output_tokens / 1000) * 0.010
        return input_cost + output_cost
```

---

## 六、压测方法

### 6.1 压测设计

**负载测试场景**

```python
import asyncio
from dataclasses import dataclass

@dataclass
class LoadTestConfig:
    concurrent_users: int = 10
    requests_per_user: int = 100
    think_time_ms: int = 100
    ramp_up_seconds: int = 30

async def run_load_test(agent_factory: Callable, 
                        tasks: list[str],
                        config: LoadTestConfig):
    results = []
    semaphore = asyncio.Semaphore(config.concurrent_users)
    
    async def user_session(user_id: int):
        agent = agent_factory()
        for i in range(config.requests_per_user):
            async with semaphore:
                task = random.choice(tasks)
                start = time.time()
                try:
                    result = await agent.run(task)
                    latency = time.time() - start
                    results.append({
                        "user_id": user_id,
                        "request_id": i,
                        "latency_ms": latency * 1000,
                        "success": True
                    })
                except Exception as e:
                    results.append({
                        "user_id": user_id,
                        "request_id": i,
                        "latency_ms": 0,
                        "success": False,
                        "error": str(e)
                    })
                
                await asyncio.sleep(config.think_time_ms / 1000)
    
    # 启动所有用户会话
    await asyncio.gather(*[
        user_session(i) for i in range(config.concurrent_users)
    ])
    
    return results
```

**压力递增测试**

```python
async def ramp_up_test(agent_factory: Callable,
                       task: str,
                       max_concurrent: int = 50,
                       step: int = 5):
    """逐步增加并发量，找到系统极限"""
    results_by_concurrency = {}
    
    for concurrent in range(1, max_concurrent + 1, step):
        config = LoadTestConfig(
            concurrent_users=concurrent,
            requests_per_user=10,
            think_time_ms=0
        )
        
        results = await run_load_test(agent_factory, [task], config)
        
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        avg_latency = sum(r["latency_ms"] for r in results if r["success"]) / \
                      max(sum(1 for r in results if r["success"]), 1)
        
        results_by_concurrency[concurrent] = {
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency
        }
        
        print(f"Concurrent: {concurrent}, Success: {success_rate:.2%}, "
              f"Latency: {avg_latency:.0f}ms")
        
        # 成功率低于90%时停止
        if success_rate < 0.9:
            break
    
    return results_by_concurrency
```

### 6.2 关键指标监控

**性能指标收集**

```python
class PerformanceCollector:
    def __init__(self):
        self.metrics = {
            "latency": [],
            "throughput": [],
            "error_rate": [],
            "token_usage": [],
            "memory_usage": []
        }
    
    def record_request(self, latency_ms: float, 
                       tokens: int,
                       success: bool):
        self.metrics["latency"].append(latency_ms)
        if success:
            self.metrics["token_usage"].append(tokens)
        else:
            self.metrics["error_rate"].append(1)
    
    def get_summary(self) -> dict:
        latencies = self.metrics["latency"]
        return {
            "p50_latency_ms": np.percentile(latencies, 50) if latencies else 0,
            "p95_latency_ms": np.percentile(latencies, 95) if latencies else 0,
            "p99_latency_ms": np.percentile(latencies, 99) if latencies else 0,
            "avg_throughput": len(latencies) / sum(latencies) * 1000 if latencies else 0,
            "error_rate": len(self.metrics["error_rate"]) / 
                          max(len(latencies), 1)
        }
```

**关键指标定义**

| 指标名称 | 目标值 | 说明 |
|---------|-------|------|
| P50 延迟 | < 2s | 50% 请求的响应时间 |
| P95 延迟 | < 5s | 95% 请求的响应时间 |
| P99 延迟 | < 10s | 99% 请求的响应时间 |
| 吞吐量 | > 10 RPS | 每秒处理请求数 |
| 错误率 | < 1% | 失败请求占比 |
| Token/秒 | > 500 | 生成效率 |

### 6.3 瓶颈定位方法

**性能分析工具**

```python
import cProfile
import pstats
import io

def profile_agent_execution(agent: MultiStepAgent, task: str):
    """使用cProfile分析性能瓶颈"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    result = agent.run(task)
    
    profiler.disable()
    
    # 输出分析结果
    s = io.StringIO()
    stats = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    stats.print_stats(20)  # 输出前20个最耗时的函数
    print(s.getvalue())
    
    return result
```

**瓶颈检查清单**

```python
def diagnose_performance(agent: MultiStepAgent, task: str) -> dict:
    issues = []
    
    # 1. 检查步骤数
    agent.run(task)
    step_count = len(agent.memory.steps)
    if step_count > 10:
        issues.append(f"步骤数过多: {step_count}，建议优化任务分解")
    
    # 2. 检查单步Token消耗
    for step in agent.memory.steps:
        if isinstance(step, ActionStep) and step.token_usage:
            total = step.token_usage.input_tokens + step.token_usage.output_tokens
            if total > 4000:
                issues.append(f"步骤 {step.step_number} Token消耗过高: {total}")
    
    # 3. 检查工具执行时间
    for step in agent.memory.steps:
        if isinstance(step, ActionStep) and step.timing:
            duration = step.timing.duration
            if duration > 5:  # 超过5秒
                issues.append(f"步骤 {step.step_number} 执行时间过长: {duration:.1f}s")
    
    return {
        "step_count": step_count,
        "total_tokens": sum(
            (s.token_usage.input_tokens + s.token_usage.output_tokens) 
            for s in agent.memory.steps 
            if isinstance(s, ActionStep) and s.token_usage
        ),
        "issues": issues
    }
```

---

## 七、优化配置示例

### 7.1 高性能配置

**CodeAgent 高性能配置**

```python
from smolagents import CodeAgent, HfApiModel, Tool
from concurrent.futures import ThreadPoolExecutor

# 高性能配置
high_performance_config = {
    # 执行器配置
    "executor_type": "local",  # 本地执行延迟最低
    "additional_authorized_imports": [
        "pandas", "numpy", "json", "re", "math"
    ],
    "max_print_outputs_length": 1000,  # 限制输出长度
    
    # 流式输出
    "stream_outputs": True,
    
    # 规划间隔，减少规划开销
    "planning_interval": None,  # 关闭自动规划
}

# 创建高性能 Agent
high_perf_agent = CodeAgent(
    tools=[web_search, calculator],
    model=HfApiModel(
        model_id="meta-llama/Llama-3.1-8B-Instruct",
        # 配置连接池
        custom_http_client=httpx.Client(
            limits=httpx.Limits(max_connections=20)
        )
    ),
    **high_performance_config
)
```

**ToolCallingAgent 高并发配置**

```python
from smolagents import ToolCallingAgent

# 高并发配置
concurrent_config = {
    # 并行工具执行
    "max_tool_threads": 8,  # 根据 CPU 核心数调整
    
    # 流式输出
    "stream_outputs": True,
    
    # 规划间隔
    "planning_interval": 5,  # 每5步规划一次
}

concurrent_agent = ToolCallingAgent(
    tools=[web_search, visit_webpage, calculator],
    model=OpenAIServerModel("gpt-4o-mini"),  # 使用快速模型
    **concurrent_config
)
```

### 7.2 低成本配置

```python
# 低成本优化配置
cost_effective_config = {
    # 使用成本最低的模型
    "model": OpenAIServerModel("gpt-4o-mini"),
    
    # 限制最大步数
    "max_steps": 3,
    
    # 禁用规划节省 Token
    "planning_interval": None,
    
    # 使用 ToolCallingAgent 减少代码解析开销
    "agent_class": ToolCallingAgent,
}

# Token 预算控制
budget_agent = ToolCallingAgent(
    tools=[essential_tools],  # 只保留必要工具
    model=cost_effective_config["model"],
    max_steps=cost_effective_config["max_steps"],
    planning_interval=cost_effective_config["planning_interval"]
)
```

### 7.3 生产环境配置

```python
# 生产环境完整配置
production_config = {
    "agent": {
        "type": "CodeAgent",
        "max_steps": 10,
        "planning_interval": 5,
        "stream_outputs": True,
        "executor_type": "docker",  # 生产环境使用 Docker 隔离
        "additional_authorized_imports": [
            "pandas", "numpy", "matplotlib", "json"
        ],
    },
    "model": {
        "provider": "openai",
        "model": "gpt-4o",
        "timeout": 60,
        "max_retries": 3,
    },
    "monitoring": {
        "enable_metrics": True,
        "log_level": "INFO",
        "token_budget_daily": 1000000,
    },
    "performance": {
        "connection_pool_size": 20,
        "max_concurrent_requests": 10,
        "cache_ttl": 300,
    }
}

class ProductionAgent:
    def __init__(self, config: dict):
        self.config = config
        self.monitor = UsageMonitor()
        self.budget = TokenBudgetController(
            config["monitoring"]["token_budget_daily"]
        )
        self.agent = self._create_agent()
    
    def _create_agent(self) -> MultiStepAgent:
        cfg = self.config["agent"]
        return CodeAgent(
            tools=self._load_tools(),
            model=self._create_model(),
            max_steps=cfg["max_steps"],
            planning_interval=cfg["planning_interval"],
            stream_outputs=cfg["stream_outputs"],
            executor_type=cfg["executor_type"],
            additional_authorized_imports=cfg["additional_authorized_imports"],
            step_callbacks=[self.monitor.record_step]
        )
    
    async def run(self, task: str):
        # 预算检查
        if not self.budget.check_budget(2000):  # 预估2000 token
            raise Exception("Daily token budget exceeded")
        
        result = await self.agent.run(task)
        
        # 记录使用量
        for step in self.agent.memory.steps:
            if isinstance(step, ActionStep) and step.token_usage:
                self.budget.record_usage(
                    step.token_usage.input_tokens + 
                    step.token_usage.output_tokens
                )
        
        return result
```

### 7.4 完整优化示例代码

```python
"""
smolagents 生产级优化配置示例
"""
import asyncio
import time
import hashlib
import json
from typing import Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from smolagents import (
    CodeAgent, ToolCallingAgent, MultiStepAgent,
    AgentMemory, ActionStep, TaskStep, PlanningStep,
    MessageRole, ChatMessage
)


@dataclass
class OptimizedAgentConfig:
    """优化配置参数"""
    # 模型配置
    model_name: str = "gpt-4o-mini"
    model_timeout: float = 60.0
    
    # Agent 配置
    max_steps: int = 5
    planning_interval: int | None = None
    stream_outputs: bool = True
    
    # 性能配置
    max_tool_threads: int = 4
    executor_type: str = "local"
    
    # Token 配置
    max_context_tokens: int = 8000
    max_tokens_per_step: int = 2000
    
    # 缓存配置
    cache_ttl: int = 300
    enable_caching: bool = True
    
    # 监控配置
    enable_monitoring: bool = True


class OptimizedAgent:
    """
    生产级优化的 smolagents 封装
    """
    
    def __init__(self, config: OptimizedAgentConfig):
        self.config = config
        self.cache: dict[str, tuple[Any, float]] = {}
        self.executor = ThreadPoolExecutor(max_workers=config.max_tool_threads)
        self.token_usage = {"input": 0, "output": 0}
        self.request_count = 0
        
        # 创建底层 Agent
        self.agent = self._create_agent()
    
    def _create_agent(self) -> MultiStepAgent:
        from smolagents import OpenAIServerModel, DuckDuckGoSearchTool
        
        model = OpenAIServerModel(
            model_id=self.config.model_name,
            timeout=self.config.model_timeout
        )
        
        if self.config.executor_type == "tool_calling":
            return ToolCallingAgent(
                tools=[DuckDuckGoSearchTool()],
                model=model,
                max_steps=self.config.max_steps,
                planning_interval=self.config.planning_interval,
                stream_outputs=self.config.stream_outputs,
                max_tool_threads=self.config.max_tool_threads
            )
        else:
            return CodeAgent(
                tools=[DuckDuckGoSearchTool()],
                model=model,
                max_steps=self.config.max_steps,
                planning_interval=self.config.planning_interval,
                stream_outputs=self.config.stream_outputs,
                executor_type=self.config.executor_type,
                additional_authorized_imports=["pandas", "numpy"]
            )
    
    def _get_cache_key(self, task: str) -> str:
        return hashlib.md5(task.encode()).hexdigest()
    
    async def run(self, task: str, use_cache: bool = True) -> Any:
        start_time = time.time()
        self.request_count += 1
        
        # 缓存检查
        if use_cache and self.config.enable_caching:
            cache_key = self._get_cache_key(task)
            cached = self.cache.get(cache_key)
            if cached and time.time() - cached[1] < self.config.cache_ttl:
                print(f"Cache hit for task: {task[:50]}...")
                return cached[0]
        
        # 上下文压缩
        self._compress_context_if_needed()
        
        # 执行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            lambda: self.agent.run(task)
        )
        
        # 记录指标
        duration = time.time() - start_time
        self._record_metrics(duration)
        
        # 缓存结果
        if use_cache and self.config.enable_caching:
            self.cache[cache_key] = (result, time.time())
        
        return result
    
    def _compress_context_if_needed(self):
        """压缩上下文控制 Token 使用"""
        if len(self.agent.memory.steps) > 10:
            # 只保留最近的步骤
            self.agent.memory.steps = [
                s for s in self.agent.memory.steps
                if isinstance(s, TaskStep)
            ][-1:] + [
                s for s in self.agent.memory.steps
                if isinstance(s, ActionStep)
            ][-5:]
    
    def _record_metrics(self, duration: float):
        """记录性能指标"""
        if not self.config.enable_monitoring:
            return
        
        # 收集 Token 使用量
        for step in self.agent.memory.steps:
            if isinstance(step, ActionStep) and step.token_usage:
                self.token_usage["input"] += step.token_usage.input_tokens
                self.token_usage["output"] += step.token_usage.output_tokens
        
        print(f"Request {self.request_count}: {duration:.2f}s, "
              f"Total tokens: {self.token_usage}")
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "request_count": self.request_count,
            "total_input_tokens": self.token_usage["input"],
            "total_output_tokens": self.token_usage["output"],
            "cache_size": len(self.cache),
        }
    
    def cleanup(self):
        """清理资源"""
        self.executor.shutdown(wait=True)
        self.cache.clear()


# 使用示例
async def main():
    config = OptimizedAgentConfig(
        model_name="gpt-4o-mini",
        max_steps=3,
        enable_caching=True,
        enable_monitoring=True
    )
    
    agent = OptimizedAgent(config)
    
    try:
        # 执行任务
        result = await agent.run("What is the capital of France?")
        print(f"Result: {result}")
        
        # 打印统计
        print(f"Stats: {agent.get_stats()}")
    finally:
        agent.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 相关文档

- [[03-smolagents-流式输出机制深度分析]]
- [[04-smolagents-记忆与历史对话管理]]
- [[25-smolagents-CodeAgent与ToolCallingAgent深度对比]]
- [[AI数据分析系统-性能优化方案]]

---

*文档版本: 1.0*  
*更新日期: 2026-02-06*
