# smolagents流输出边界情况深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 适用版本: v1.12.0+
> 目标读者: 需要接入 smolagents 流输出的开发者

---

## 一、两种Agent流输出机制差异

### 1.1 ToolCallingAgent流输出特点

ToolCallingAgent使用JSON格式的tool_calls作为输出格式，其流输出机制具有以下特点：

| 特性 | 说明 |
|------|------|
| 输出格式 | JSON格式的tool_calls数组 |
| 流式粒度 | 整个tool_call一次性返回，无法在生成过程中拆分 |
| 可流式内容 | Thought文本通过模型generate_stream逐token输出 |
| 中间状态 | 工具执行期间完全无输出，直到执行完成 |

代码层面的流输出发生在两个位置：

1. **模型生成阶段**：调用`model.generate_stream`时，逐token输出thought内容
2. **工具调用阶段**：`process_tool_calls`方法执行工具，生成ToolCall和ToolOutput对象

```python
# 核心代码位置：ToolCallingAgent._step_stream 第1292-1307行
if self.stream_outputs and hasattr(self.model, "generate_stream"):
    output_stream = self.model.generate_stream(
        input_messages,
        stop_sequences=["Observation:", "Calling tools:"],
        tools_to_call_from=self.tools_and_managed_agents,
    )
    for event in output_stream:
        chat_message_stream_deltas.append(event)
        yield event  # 这里yield的是ChatMessageStreamDelta
    chat_message = agglomerate_stream_deltas(chat_message_stream_deltas)
```

### 1.2 CodeAgent流输出特点

CodeAgent使用Python代码块作为输出格式，其流输出机制具有以下特点：

| 特性 | 说明 |
|------|------|
| 输出格式 | Python代码块，使用特定分隔符包裹 |
| 流式粒度 | 代码生成可以逐token流式输出 |
| 可流式内容 | thought文本、代码生成过程 |
| 中间状态 | 代码执行期间无流输出 |

代码层面的流输出同样发生在模型生成阶段，但后续需要解析代码并执行：

```python
# 核心代码位置：CodeAgent._step_stream 第1660-1674行
if self.stream_outputs:
    output_stream = self.model.generate_stream(
        input_messages,
        stop_sequences=stop_sequences,
        **additional_args,
    )
    for event in output_stream:
        chat_message_stream_deltas.append(event)
        yield event  # 这里yield的是ChatMessageStreamDelta
    chat_message = agglomerate_stream_deltas(chat_message_stream_deltas)
```

### 1.3 流输出时序对比

![[smolagents-ToolCallingAgent流输出时序图.svg]]

![[smolagents-CodeAgent流输出时序图.svg]]

---

## 二、ToolCallingAgent边界情况

### 2.1 Tool执行时间过长

**问题描述**

Tool执行期间流输出完全中断，用户界面长时间无响应。

**根因分析**

ToolCallingAgent的流输出架构存在设计上的间隙：模型生成thought后调用工具，工具执行是同步阻塞的，执行期间没有任何yield语句。这意味着：

- 数据库查询、网络请求等I/O操作会完全阻塞流输出
- 用户看不到任何进度反馈
- 前端无法区分是执行中还是连接断开

**代码位置分析**

```python
# 问题代码段：process_tool_calls 第1416-1434行
if len(parallel_calls) == 1:
    tool_call = list(parallel_calls.values())[0]
    tool_output = process_single_tool_call(tool_call)  # 同步执行，无yield
    outputs[tool_output.id] = tool_output
    yield tool_output  # 执行完成后才yield
else:
    with ThreadPoolExecutor(self.max_tool_threads) as executor:
        futures = []
        for tool_call in parallel_calls.values():
            futures.append(executor.submit(process_single_tool_call, tool_call))
        for future in as_completed(futures):
            tool_output = future.result()  # 等待完成
            yield tool_output  # 完成后才yield
```

**解决方案**

方案1：在Tool内部实现进度回调机制

```python
class ProgressCallbackTool:
    def __init__(self, progress_callback):
        self.progress_callback = progress_callback
    
    def __call__(self, query):
        self.progress_callback("开始连接数据库...")
        connection = create_connection()
        self.progress_callback("执行查询...")
        result = connection.execute(query)
        self.progress_callback(f"获取到{len(result)}条记录")
        return result
```

方案2：使用异步Tool配合心跳机制

```python
async def tool_with_heartbeat(tool_func, callback, interval=1.0):
    task = asyncio.create_task(tool_func())
    while not task.done():
        callback({"type": "heartbeat", "status": "running"})
        await asyncio.wait_for(task, timeout=interval)
    return task.result()
```

方案3：前端超时保护

```javascript
// 前端实现超时检测
const HEARTBEAT_TIMEOUT = 30000; // 30秒
let lastChunkTime = Date.now();

websocket.onmessage = (event) => {
    lastChunkTime = Date.now();
    processChunk(event.data);
};

setInterval(() => {
    if (Date.now() - lastChunkTime > HEARTBEAT_TIMEOUT) {
        showLoadingAnimation();
    }
}, 5000);
```

### 2.2 多Tool连续调用

**问题描述**

多个工具顺序调用时，流输出呈现断断续续的特征，用户体验不佳。

**现象示例**

```
chunk1: "让我查询数据库..."
[等待5秒]
chunk2: "现在分析数据..."
[等待3秒]  
chunk3: "最终结果..."
```

**根因分析**

ToolCallingAgent的执行模型是顺序的：
1. 模型生成thought和tool_calls
2. 执行所有工具调用
3. 将结果返回给模型
4. 模型生成下一步

每个步骤之间存在明显的间隙，这些间隙期间没有流输出。

**解决方案**

在step_callback中发送进度信息：

```python
class StreamingCallback:
    def __init__(self, websocket):
        self.websocket = websocket
        self.step_count = 0
    
    def __call__(self, step_log, agent):
        self.step_count += 1
        if isinstance(step_log, ActionStep):
            asyncio.create_task(self.websocket.send({
                "type": "step_complete",
                "step_number": step_log.step_number,
                "has_error": step_log.error is not None
            }))
```

### 2.3 Tool返回大量数据

**问题描述**

Observation数据量过大时，可能导致流输出延迟或超时。

**根因分析**

ToolOutput包含完整的observation字符串，如果工具返回大量数据：
- 序列化耗时增加
- 网络传输延迟
- 可能触发WebSocket消息大小限制

**代码位置分析**

```python
# ToolOutput构造位置：process_single_tool_call 第1400-1414行
observation = str(tool_call_result).strip()  # 可能非常长
return ToolOutput(
    id=tool_call.id,
    output=tool_call_result,
    is_final_answer=is_final_answer,
    observation=observation,  # 完整数据
    tool_call=tool_call,
)
```

**解决方案**

```python
MAX_OBSERVATION_LENGTH = 10000

def truncate_observation(result, max_length=MAX_OBSERVATION_LENGTH):
    result_str = str(result)
    if len(result_str) > max_length:
        return result_str[:max_length] + f"\n... [截断，原始长度{len(result_str)}]"
    return result_str

# 在Tool中实现分页
class PaginatedDatabaseTool:
    def __call__(self, query, page=1, page_size=100):
        all_results = execute_query(query)
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "data": all_results[start:end],
            "total": len(all_results),
            "page": page,
            "total_pages": (len(all_results) + page_size - 1) // page_size
        }
```

### 2.4 Tool调用失败

**问题描述**

工具执行错误时的流输出行为不一致，可能抛出异常或将错误作为observation返回。

**代码位置分析**

```python
# 错误处理位置：execute_tool_call 第1482-1502行
try:
    validate_tool_arguments(tool, arguments)
except (ValueError, TypeError) as e:
    raise AgentToolCallError(str(e), self.logger) from e
except Exception as e:
    raise AgentToolExecutionError(error_msg, self.logger) from e
```

**边界情况**

| 错误类型 | 处理方式 | 流输出行为 |
|----------|----------|------------|
| 参数验证失败 | 抛出AgentToolCallError | 流中断，异常上抛 |
| 工具不存在 | 抛出AgentToolExecutionError | 流中断，异常上抛 |
| 执行异常 | 抛出AgentToolExecutionError | 流中断，异常上抛 |

**解决方案**

```python
class RobustToolExecutor:
    async def execute_with_fallback(self, tool_name, arguments, max_retries=2):
        for attempt in range(max_retries):
            try:
                return await self.execute_tool(tool_name, arguments)
            except AgentToolExecutionError as e:
                if attempt < max_retries - 1:
                    yield {
                        "type": "retry",
                        "attempt": attempt + 1,
                        "error": str(e)
                    }
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                else:
                    yield {
                        "type": "error",
                        "final_error": str(e)
                    }
                    raise
```

### 2.5 JSON解析失败

**问题描述**

模型生成的tool_call格式不正确，导致JSON解析失败。

**根因分析**

ToolCallingAgent依赖模型输出格式正确的JSON，但以下情况可能导致失败：
- 模型输出不稳定的JSON
- 模型输出包含markdown代码块包裹的JSON
- 模型输出不完整的JSON

**代码位置分析**

```python
# 解析位置：model.parse_tool_calls 第1327-1334行
if chat_message.tool_calls is None or len(chat_message.tool_calls) == 0:
    try:
        chat_message = self.model.parse_tool_calls(chat_message)
    except Exception as e:
        raise AgentParsingError(f"Error while parsing tool call from model output: {e}", self.logger)
```

**解决方案**

```python
import json
import re

class JSONRepairParser:
    @staticmethod
    def repair_json(text):
        # 尝试提取markdown代码块中的JSON
        code_block_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if code_block_match:
            text = code_block_match.group(1)
        
        # 尝试修复常见的JSON错误
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 修复尾部缺少的括号
            text = text.strip()
            open_braces = text.count('{') - text.count('}')
            open_brackets = text.count('[') - text.count(']')
            text += '}' * open_braces + ']' * open_brackets
            return json.loads(text)
    
    @staticmethod
    def parse_with_fallback(text, max_attempts=3):
        for attempt in range(max_attempts):
            try:
                return JSONRepairParser.repair_json(text)
            except json.JSONDecodeError:
                if attempt == max_attempts - 1:
                    raise
                # 尝试截断到最后的完整对象
                last_brace = text.rfind('}')
                if last_brace > 0:
                    text = text[:last_brace + 1]
```

---

## 三、CodeAgent边界情况

### 3.1 代码生成过程中的流输出

**问题描述**

代码生成期间用户看到的是逐token的输出，但存在多种中断风险。

**代码位置分析**

```python
# 流输出位置：CodeAgent._step_stream 第1660-1674行
output_stream = self.model.generate_stream(
    input_messages,
    stop_sequences=stop_sequences,
    **additional_args,
)
for event in output_stream:
    chat_message_stream_deltas.append(event)
    yield event  # 逐token yield
```

**边界情况**

| 情况 | 现象 | 处理方式 |
|------|------|----------|
| 用户取消 | 生成中断，代码不完整 | 检查cancel标志 |
| max_tokens限制 | 代码被截断 | 检测不完整代码 |
| markdown格式错误 | 代码块解析失败 | 增强parse_code_blobs容错 |

**解决方案**

```python
class CodeGenerationHandler:
    def __init__(self):
        self.cancelled = False
        self.buffer = ""
    
    def cancel(self):
        self.cancelled = True
    
    async def stream_with_cancellation(self, generator):
        try:
            async for chunk in generator:
                if self.cancelled:
                    yield {"type": "cancelled", "partial_code": self.buffer}
                    break
                self.buffer += chunk.content or ""
                yield chunk
        except Exception as e:
            yield {"type": "error", "error": str(e), "partial_code": self.buffer}
    
    def is_code_complete(self, code, code_block_tags):
        # 检查代码是否完整
        return code.strip().endswith(code_block_tags[1])
```

### 3.2 代码执行期间的流输出中断

**问题描述**

代码执行是同步的，执行期间没有任何流输出，形成黑盒阶段。

**代码位置分析**

```python
# 执行位置：CodeAgent._step_stream 第1726-1752行
code_output = self.python_executor(code_action)  # 同步执行
# 执行期间无yield
observation = "Execution logs:\n" + code_output.logs
```

**根因分析**

- LocalPythonExecutor使用exec执行代码
- 代码执行期间无法yield中间状态
- 长时间运行的代码会让用户界面卡住

**解决方案**

方案1：在代码中使用print输出进度

```python
# 在系统提示中强调使用print
SYSTEM_PROMPT += """
如果代码执行时间较长，请使用print语句输出进度信息，例如：
```python
print("开始处理数据...")
for i, item in enumerate(large_dataset):
    process(item)
    if i % 100 == 0:
        print(f"已处理 {i}/{len(large_dataset)} 条记录")
print("处理完成")
```
"""
```

方案2：修改executor支持流式输出

```python
class StreamingPythonExecutor:
    def __call__(self, code):
        # 重写execute以支持流式捕获
        import sys
        from io import StringIO
        
        output_buffer = StringIO()
        
        class StreamingOutput:
            def write(self, text):
                output_buffer.write(text)
                # 触发回调
                self.on_output(text)
            
            def on_output(self, text):
                # 通过回调发送流输出
                pass
        
        old_stdout = sys.stdout
        sys.stdout = StreamingOutput()
        try:
            exec(code, self.state)
        finally:
            sys.stdout = old_stdout
        
        return output_buffer.getvalue()
```

### 3.3 代码执行错误

**问题描述**

代码执行失败时的流输出行为需要正确处理。

**边界情况分类**

| 错误类型 | 发生阶段 | 处理方式 |
|----------|----------|----------|
| SyntaxError | 解析阶段 | 立即返回错误 |
| ImportError | 执行初期 | 提示缺少授权 |
| RuntimeError | 执行中 | 捕获并返回 |
| TimeoutError | 执行超时 | 强制终止 |
| MemoryError | 资源耗尽 | 强制终止 |

**代码位置分析**

```python
# 错误处理位置：第1735-1751行
except Exception as e:
    if hasattr(self.python_executor, "state") and "_print_outputs" in self.python_executor.state:
        execution_logs = str(self.python_executor.state["_print_outputs"])
        # 记录已执行的输出
    error_msg = str(e)
    if "Import of " in error_msg and " is not allowed" in error_msg:
        # 特殊处理导入错误
        self.logger.log("[bold red]Warning to user: ...")
    raise AgentExecutionError(error_msg, self.logger)
```

**解决方案**

```python
class CodeErrorHandler:
    ERROR_PATTERNS = {
        r"Import of (\w+) is not allowed": "缺少导入授权",
        r"NameError: name '(\w+)' is not defined": "变量未定义",
        r"SyntaxError:": "代码语法错误",
        r"TimeoutError:": "执行超时",
    }
    
    @classmethod
    def classify_error(cls, error_msg):
        for pattern, category in cls.ERROR_PATTERNS.items():
            if re.search(pattern, error_msg):
                return category
        return "执行错误"
    
    @classmethod
    def get_recovery_suggestion(cls, error_msg, code):
        category = cls.classify_error(error_msg)
        suggestions = {
            "缺少导入授权": "请将该模块添加到additional_authorized_imports",
            "变量未定义": "请检查变量名拼写或初始化",
            "代码语法错误": "请修正代码语法",
            "执行超时": "请优化代码性能或分批处理",
        }
        return suggestions.get(category, "请检查代码逻辑")
```

### 3.4 无限循环或长时间运行

**问题描述**

代码可能陷入无限循环或长时间运行，需要有效的超时控制。

**根因分析**

CodeAgent依赖executor的超时控制，但不同executor的实现不同：
- LocalPythonExecutor：使用signal或threading.Timeout
- RemoteExecutor：依赖远程服务的超时设置

**解决方案**

```python
import signal
from contextlib import contextmanager

class TimeoutExecutor:
    @contextmanager
    def time_limit(self, seconds):
        def signal_handler(signum, frame):
            raise TimeoutError(f"代码执行超过{seconds}秒限制")
        
        signal.signal(signal.SIGALRM, signal_handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
    
    def execute_with_timeout(self, code, timeout=30):
        with self.time_limit(timeout):
            return self.python_executor(code)
```

### 3.5 输出格式问题

**问题描述**

final_answer的格式可能不符合预期，包含多余的markdown或stdout输出。

**根因分析**

CodeAgent通过final_answer变量获取结果，但代码可能输出其他内容到stdout，导致：
- stdout包含调试信息
- final_answer包含markdown标记
- 两者内容不一致

**代码位置分析**

```python
# 输出处理位置：第1753-1765行
truncated_output = truncate_content(str(code_output.output))
observation += "Last output from code snippet:\n" + truncated_output
memory_step.observations = observation

if not code_output.is_final_answer:
    execution_outputs_console += [
        Text(f"Out: {truncated_output}"),
    ]
yield ActionOutput(output=code_output.output, is_final_answer=code_output.is_final_answer)
```

**解决方案**

```python
def clean_final_answer(output, code_block_tags):
    """清理final_answer输出"""
    output_str = str(output)
    
    # 移除代码块标记
    if output_str.startswith(code_block_tags[0]):
        output_str = output_str[len(code_block_tags[0]):]
    if output_str.endswith(code_block_tags[1]):
        output_str = output_str[:-len(code_block_tags[1])]
    
    # 移除markdown标记
    output_str = re.sub(r'```\w*\n?', '', output_str)
    
    return output_str.strip()

# 在系统提示中强调格式
CODE_AGENT_PROMPT += """
使用final_answer工具时，请直接返回结果内容，不要添加markdown代码块。
正确：final_answer("结果内容")
错误：final_answer("```\n结果内容\n```")
"""
```

---

## 四、通用流输出边界情况

### 4.1 上下文长度超限

**问题描述**

流输出过程中上下文历史累积超过模型最大token限制。

**根因分析**

每次调用模型都携带完整历史，随着步骤增加：
- token使用量线性增长
- 可能触发模型的max_tokens限制
- 模型开始遗忘早期内容

**解决方案**

```python
class ContextManager:
    def __init__(self, max_tokens=8000, summary_threshold=6000):
        self.max_tokens = max_tokens
        self.summary_threshold = summary_threshold
        self.token_counter = 0
    
    def should_summarize(self, messages):
        total_tokens = sum(self.estimate_tokens(m) for m in messages)
        return total_tokens > self.summary_threshold
    
    def summarize_history(self, messages):
        # 保留系统提示和最近几步
        system_msg = messages[0]
        recent_messages = messages[-6:]  # 保留最近3轮对话
        
        # 中间部分进行摘要
        middle_messages = messages[1:-6]
        summary = self.generate_summary(middle_messages)
        
        return [system_msg, summary] + recent_messages
    
    def estimate_tokens(self, message):
        # 简单估算：1个token约等于4个字符
        content = str(message.get("content", ""))
        return len(content) // 4
```

### 4.2 网络中断

**问题描述**

流输出过程中网络连接断开。

**边界情况**

| 场景 | 表现 | 应对策略 |
|------|------|----------|
| 连接重置 | Generator抛出异常 | 捕获异常，通知用户 |
| 读取超时 | 长时间无数据 | 心跳检测 |
| SSL错误 | 证书问题 | 降级为非加密连接 |

**解决方案**

```python
import asyncio
from aiohttp import ClientConnectorError

class ResilientStream:
    def __init__(self, agent, max_retries=3):
        self.agent = agent
        self.max_retries = max_retries
        self.retry_count = 0
    
    async def run_with_recovery(self, task):
        while self.retry_count < self.max_retries:
            try:
                async for chunk in self.agent.run_stream(task):
                    yield chunk
                return
            except ClientConnectorError:
                self.retry_count += 1
                if self.retry_count >= self.max_retries:
                    yield {"type": "error", "message": "连接失败，请检查网络"}
                    raise
                yield {"type": "retry", "attempt": self.retry_count}
                await asyncio.sleep(2 ** self.retry_count)
```

### 4.3 用户取消

**问题描述**

用户需要能够中途取消正在执行的请求。

**解决方案**

```python
class CancellableAgent:
    def __init__(self):
        self._cancelled = False
        self._current_generator = None
    
    def cancel(self):
        self._cancelled = True
        if self._current_generator:
            self._current_generator.close()
    
    async def run_stream(self, task):
        self._cancelled = False
        generator = self.agent.run_stream(task)
        self._current_generator = generator
        
        try:
            async for chunk in generator:
                if self._cancelled:
                    yield {"type": "cancelled"}
                    break
                yield chunk
        finally:
            self._current_generator = None
```

### 4.4 并发请求

**问题描述**

多个并发的流输出请求可能导致资源问题。

**边界情况**

| 问题 | 风险 | 解决方案 |
|------|------|----------|
| 内存占用剧增 | 每个请求持有完整上下文 | 限制并发数 |
| rate limit触发 | API调用频率过高 | 请求队列化 |
| 上下文混淆 | 请求间数据互相影响 | 严格上下文隔离 |

**解决方案**

```python
import asyncio
from asyncio import Semaphore

class RateLimitedAgentPool:
    def __init__(self, max_concurrent=5, rate_limit_per_minute=60):
        self.semaphore = Semaphore(max_concurrent)
        self.rate_limiter = asyncio.Queue(maxsize=rate_limit_per_minute)
        self.request_queue = asyncio.Queue()
    
    async def acquire_slot(self):
        await self.semaphore.acquire()
        try:
            # 等待rate limiter有空位
            await self.rate_limiter.put(1)
            await asyncio.sleep(60 / 60)  # 每分钟60个请求
        except asyncio.QueueFull:
            await asyncio.sleep(1)
    
    async def release_slot(self):
        self.semaphore.release()
    
    async def process_request(self, agent, task):
        await self.acquire_slot()
        try:
            async for chunk in agent.run_stream(task):
                yield chunk
        finally:
            await self.release_slot()
```

---

## 五、接入系统时的关键注意点

### 5.1 回调函数设计

正确的回调设计是流输出集成的关键。

```python
from smolagents import CodeAgent, ToolCallingAgent
from smolagents.memory import ActionStep, PlanningStep, FinalAnswerStep

class StreamingCallback:
    def __init__(self, websocket):
        self.websocket = websocket
        self.step_counter = 0
    
    async def __call__(self, step_log, agent):
        """
        注意：此回调在每个step结束时调用
        ToolCallingAgent和CodeAgent都会触发
        """
        self.step_counter += 1
        
        if isinstance(step_log, ActionStep):
            await self._handle_action_step(step_log)
        elif isinstance(step_log, PlanningStep):
            await self._handle_planning_step(step_log)
        elif isinstance(step_log, FinalAnswerStep):
            await self._handle_final_answer(step_log)
    
    async def _handle_action_step(self, step_log):
        """处理ActionStep - 包含tool调用或代码执行结果"""
        data = {
            "type": "action_step",
            "step_number": step_log.step_number,
            "token_usage": {
                "input": step_log.token_usage.input_tokens if step_log.token_usage else 0,
                "output": step_log.token_usage.output_tokens if step_log.token_usage else 0,
            } if step_log.token_usage else None,
            "timing": {
                "start": step_log.timing.start_time,
                "end": step_log.timing.end_time,
            } if step_log.timing else None,
            "error": str(step_log.error) if step_log.error else None,
        }
        
        # 提取tool_calls或代码
        if hasattr(step_log, 'tool_calls') and step_log.tool_calls:
            data["tool_calls"] = [
                {
                    "name": tc.name,
                    "arguments": tc.arguments,
                    "id": tc.id,
                }
                for tc in step_log.tool_calls
            ]
        
        if hasattr(step_log, 'code_action') and step_log.code_action:
            data["code"] = step_log.code_action
        
        await self.websocket.send_json(data)
    
    async def _handle_planning_step(self, step_log):
        """处理PlanningStep - 规划阶段"""
        await self.websocket.send_json({
            "type": "planning",
            "plan": step_log.plan,
        })
    
    async def _handle_final_answer(self, step_log):
        """处理FinalAnswerStep - 最终答案"""
        await self.websocket.send_json({
            "type": "final_answer",
            "output": str(step_log.output),
        })
```

### 5.2 流输出与WebSocket集成

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
import json

app = FastAPI()

@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 初始化Agent
    agent = CodeAgent(
        model=model,
        tools=tools,
        step_callbacks=[StreamingCallback(websocket)],
        stream_outputs=True,  # 启用流输出
    )
    
    try:
        while True:
            # 接收用户消息
            data = await websocket.receive_json()
            task = data.get("task", "")
            
            # 边界情况检查：空任务
            if not task.strip():
                await websocket.send_json({
                    "type": "error",
                    "message": "任务不能为空"
                })
                continue
            
            # 流式执行
            try:
                async for chunk in agent.run_stream(task):
                    # 边界情况：chunk可能是None
                    if chunk is None:
                        continue
                    
                    # 边界情况：处理不同类型的chunk
                    if hasattr(chunk, 'content'):
                        # ChatMessageStreamDelta
                        await websocket.send_json({
                            "type": "stream_delta",
                            "content": chunk.content,
                        })
                    elif hasattr(chunk, 'output'):
                        # ActionOutput
                        await websocket.send_json({
                            "type": "action_output",
                            "output": str(chunk.output),
                            "is_final": chunk.is_final_answer,
                        })
                    else:
                        # 其他类型，尝试通用序列化
                        await websocket.send_json({
                            "type": "unknown",
                            "data": str(chunk),
                        })
                        
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"执行错误: {str(e)}"
                })
                
    except WebSocketDisconnect:
        # 边界情况：用户断开连接
        # 需要取消正在执行的任务
        if hasattr(agent, 'interrupt'):
            agent.interrupt()
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"系统错误: {str(e)}"
        })
```

### 5.3 错误处理策略

```python
class RobustStreamingAgent:
    """增强错误处理能力的流输出Agent包装器"""
    
    ERROR_RECOVERY_STRATEGIES = {
        "JSONDecodeError": {
            "retry": True,
            "max_retries": 3,
            "prompt_suffix": "\n请确保输出格式正确。",
        },
        "TimeoutError": {
            "retry": True,
            "max_retries": 2,
            "backoff": 2.0,
        },
        "AgentParsingError": {
            "retry": True,
            "max_retries": 2,
        },
        "AgentExecutionError": {
            "retry": False,  # 执行错误不重试，让Agent自己处理
        },
    }
    
    def __init__(self, agent):
        self.agent = agent
        self.error_history = []
    
    async def run_with_error_handling(self, task, max_retries=3):
        current_task = task
        attempt = 0
        
        while attempt < max_retries:
            try:
                async for chunk in self.agent.run_stream(current_task):
                    # 包装chunk添加元数据
                    yield {
                        "attempt": attempt + 1,
                        "chunk": chunk,
                    }
                return
                    
            except json.JSONDecodeError as e:
                strategy = self.ERROR_RECOVERY_STRATEGIES["JSONDecodeError"]
                if attempt < strategy["max_retries"]:
                    attempt += 1
                    current_task = task + strategy["prompt_suffix"]
                    yield {
                        "type": "recovery",
                        "attempt": attempt,
                        "error": "JSON解析失败，正在重试",
                    }
                    await asyncio.sleep(1)
                else:
                    yield {
                        "type": "error",
                        "error": f"JSON解析失败，已达到最大重试次数: {str(e)}"
                    }
                    raise
                    
            except TimeoutError as e:
                strategy = self.ERROR_RECOVERY_STRATEGIES["TimeoutError"]
                if attempt < strategy["max_retries"]:
                    attempt += 1
                    yield {
                        "type": "recovery",
                        "attempt": attempt,
                        "error": "执行超时，正在重试",
                    }
                    await asyncio.sleep(strategy["backoff"] ** attempt)
                else:
                    yield {
                        "type": "error",
                        "error": f"执行超时，已达到最大重试次数"
                    }
                    raise
                    
            except Exception as e:
                error_type = type(e).__name__
                self.error_history.append({
                    "type": error_type,
                    "message": str(e),
                    "attempt": attempt,
                })
                
                yield {
                    "type": "error",
                    "error_type": error_type,
                    "error": str(e),
                }
                raise
```

---

## 六、测试用例建议

### 6.1 ToolCallingAgent测试场景

```python
import pytest
import asyncio
from unittest.mock import Mock, patch

class TestToolCallingAgentStreaming:
    """ToolCallingAgent流输出测试套件"""
    
    @pytest.mark.asyncio
    async def test_normal_tool_call_streaming(self):
        """测试正常工具调用的流输出"""
        agent = ToolCallingAgent(
            model=mock_model,
            tools=[mock_tool],
            stream_outputs=True,
        )
        
        chunks = []
        async for chunk in agent.run_stream("test task"):
            chunks.append(chunk)
        
        # 验证流输出包含预期内容
        assert any(hasattr(c, 'content') for c in chunks)  # thought内容
        assert any(hasattr(c, 'tool_calls') for c in chunks)  # tool调用
    
    @pytest.mark.asyncio
    async def test_tool_execution_timeout(self):
        """测试工具执行超时的流输出行为"""
        slow_tool = MockTool(execution_time=60)  # 模拟慢工具
        agent = ToolCallingAgent(
            model=mock_model,
            tools=[slow_tool],
            stream_outputs=True,
        )
        
        # 应该能够检测到超时
        with pytest.raises(TimeoutError):
            async for chunk in agent.run_stream("test"):
                pass
    
    @pytest.mark.asyncio
    async def test_large_observation_handling(self):
        """测试大observation的处理"""
        large_tool = MockTool(return_value="x" * 100000)  # 100KB数据
        agent = ToolCallingAgent(
            model=mock_model,
            tools=[large_tool],
            stream_outputs=True,
        )
        
        chunks = []
        async for chunk in agent.run_stream("test"):
            chunks.append(chunk)
        
        # 验证数据被正确截断或分页
        observation_sizes = [len(str(c)) for c in chunks if hasattr(c, 'observation')]
        assert all(size < 50000 for size in observation_sizes)
    
    @pytest.mark.asyncio
    async def test_tool_error_recovery(self):
        """测试工具错误时的恢复"""
        error_tool = MockTool(side_effect=Exception("Tool failed"))
        agent = ToolCallingAgent(
            model=mock_model,
            tools=[error_tool],
            stream_outputs=True,
        )
        
        # 应该抛出AgentToolExecutionError
        with pytest.raises(AgentToolExecutionError):
            async for chunk in agent.run_stream("test"):
                pass
    
    @pytest.mark.asyncio
    async def test_malformed_json_handling(self):
        """测试畸形JSON的处理"""
        # 模拟返回畸形JSON的模型
        bad_model = MockModel(json_response='{"invalid json')
        agent = ToolCallingAgent(
            model=bad_model,
            tools=[mock_tool],
            stream_outputs=True,
        )
        
        with pytest.raises(AgentParsingError):
            async for chunk in agent.run_stream("test"):
                pass
    
    @pytest.mark.asyncio
    async def test_multiple_parallel_tools(self):
        """测试并行工具调用的流输出"""
        agent = ToolCallingAgent(
            model=mock_model,
            tools=[tool1, tool2, tool3],
            stream_outputs=True,
            max_tool_threads=3,
        )
        
        # 模拟模型返回多个tool_calls
        mock_model.tool_calls = [call1, call2, call3]
        
        chunks = []
        async for chunk in agent.run_stream("test"):
            chunks.append(chunk)
        
        # 验证所有工具调用都被处理
        tool_outputs = [c for c in chunks if hasattr(c, 'tool_call')]
        assert len(tool_outputs) == 3
```

### 6.2 CodeAgent测试场景

```python
class TestCodeAgentStreaming:
    """CodeAgent流输出测试套件"""
    
    @pytest.mark.asyncio
    async def test_simple_code_generation_streaming(self):
        """测试简单代码生成的流输出"""
        agent = CodeAgent(
            model=mock_model,
            tools=[],
            stream_outputs=True,
        )
        
        chunks = []
        async for chunk in agent.run_stream("calculate 2+2"):
            chunks.append(chunk)
        
        # 验证流输出包含代码生成过程
        assert any(hasattr(c, 'content') for c in chunks)
    
    @pytest.mark.asyncio
    async def test_long_code_generation(self):
        """测试长代码生成的流输出"""
        long_code = "\n".join([f"print({i})" for i in range(100)])
        mock_model.set_response(long_code)
        
        agent = CodeAgent(
            model=mock_model,
            tools=[],
            stream_outputs=True,
        )
        
        chunks = []
        async for chunk in agent.run_stream("test"):
            chunks.append(chunk)
        
        # 验证所有chunk都被接收
        assert len(chunks) > 10
    
    @pytest.mark.asyncio
    async def test_code_execution_error(self):
        """测试代码执行错误的处理"""
        agent = CodeAgent(
            model=mock_model,
            tools=[],
            stream_outputs=True,
        )
        
        # 模拟模型生成有语法错误的代码
        mock_model.set_response("```python\nprint(undefined_var)\n```")
        
        with pytest.raises(AgentExecutionError):
            async for chunk in agent.run_stream("test"):
                pass
    
    @pytest.mark.asyncio
    async def test_infinite_loop_detection(self):
        """测试无限循环检测"""
        agent = CodeAgent(
            model=mock_model,
            tools=[],
            stream_outputs=True,
        )
        
        # 模拟生成无限循环代码
        mock_model.set_response("```python\nwhile True: pass\n```")
        
        # 应该触发超时
        with pytest.raises(TimeoutError):
            async for chunk in agent.run_stream("test"):
                pass
    
    @pytest.mark.asyncio
    async def test_memory_limit(self):
        """测试内存限制"""
        agent = CodeAgent(
            model=mock_model,
            tools=[],
            stream_outputs=True,
        )
        
        # 模拟生成消耗大量内存的代码
        mock_model.set_response("```python\nlist(range(100000000))\n```")
        
        with pytest.raises(MemoryError):
            async for chunk in agent.run_stream("test"):
                pass
    
    @pytest.mark.asyncio
    async def test_generation_interruption(self):
        """测试生成中断"""
        agent = CodeAgent(
            model=mock_model,
            tools=[],
            stream_outputs=True,
        )
        
        async def generate_with_timeout():
            chunks = []
            async for chunk in agent.run_stream("test"):
                chunks.append(chunk)
                if len(chunks) > 5:
                    agent.interrupt()
            return chunks
        
        with pytest.raises(AgentError):
            await generate_with_timeout()
```

---

## 七、监控指标

![[smolagents-流输出监控架构图.svg]]

### 7.1 延迟指标

```python
STREAMING_LATENCY_METRICS = {
    # 首字节延迟 - 用户感知的关键指标
    "time_to_first_chunk": {
        "description": "从请求到首个chunk返回的时间",
        "threshold_warning": 2.0,  # 秒
        "threshold_critical": 5.0,
        "labels": ["agent_type", "model_id"],
    },
    
    # 块间延迟 - 反映流输出的平滑度
    "time_between_chunks": {
        "description": "连续chunk之间的平均间隔",
        "threshold_warning": 1.0,  # 秒
        "threshold_critical": 3.0,
        "labels": ["agent_type", "step_number"],
    },
    
    # 总流式时间
    "total_streaming_time": {
        "description": "整个流输出的持续时间",
        "threshold_warning": 60.0,  # 秒
        "threshold_critical": 120.0,
        "labels": ["agent_type", "task_complexity"],
    },
}
```

### 7.2 内容指标

```python
STREAMING_CONTENT_METRICS = {
    # 输出量指标
    "total_chunks": {
        "description": "返回的总chunk数",
        "aggregation": "sum",
        "labels": ["agent_type"],
    },
    
    "total_tokens": {
        "description": "生成的总token数",
        "aggregation": "sum",
        "labels": ["agent_type", "model_id"],
    },
    
    "chunks_per_second": {
        "description": "每秒输出的chunk数",
        "aggregation": "avg",
        "threshold_warning": 0.5,
        "labels": ["agent_type"],
    },
    
    # 代码特定指标
    "code_lines_generated": {
        "description": "生成的代码行数",
        "aggregation": "histogram",
        "buckets": [10, 50, 100, 200, 500],
        "labels": ["agent_type"],
    },
    
    # 工具特定指标
    "tool_calls_per_step": {
        "description": "每步的工具调用数",
        "aggregation": "histogram",
        "buckets": [1, 2, 3, 5, 10],
        "labels": ["agent_type"],
    },
}
```

### 7.3 错误指标

```python
STREAMING_ERROR_METRICS = {
    # 错误计数
    "streaming_errors_total": {
        "description": "流输出错误总数",
        "aggregation": "counter",
        "labels": ["error_type", "agent_type"],
    },
    
    # 错误类型细分
    "error_by_category": {
        "categories": [
            "JSON_DECODE_ERROR",
            "TIMEOUT_ERROR", 
            "PARSING_ERROR",
            "EXECUTION_ERROR",
            "NETWORK_ERROR",
            "CANCELLED",
        ],
        "aggregation": "counter",
    },
    
    # 中断统计
    "interrupted_streams": {
        "description": "被中断的流数",
        "aggregation": "counter",
        "labels": ["interruption_reason"],
    },
    
    # 超时统计
    "timeout_count": {
        "description": "超时次数",
        "aggregation": "counter",
        "labels": ["timeout_phase"],  # generation, execution
    },
}
```

### 7.4 资源指标

```python
STREAMING_RESOURCE_METRICS = {
    # 内存使用
    "memory_usage_mb": {
        "description": "流输出期间的内存使用峰值",
        "aggregation": "gauge",
        "labels": ["agent_type"],
    },
    
    # 活跃连接
    "active_generators": {
        "description": "当前活跃的Generator数量",
        "aggregation": "gauge",
        "labels": ["agent_type"],
    },
    
    # Token使用效率
    "tokens_per_step": {
        "description": "每步消耗的token数",
        "aggregation": "histogram",
        "buckets": [500, 1000, 2000, 4000, 8000],
    },
}
```

---

## 八、总结与最佳实践

### 8.1 ToolCallingAgent最佳实践

1. **超时设计**
   - 为每个Tool设置独立的超时时间
   - 使用异步执行避免阻塞流输出
   - 在前端实现心跳检测机制

2. **Observation管理**
   - 在Tool层面实现数据截断或分页
   - 使用summary工具压缩大结果
   - 避免在observation中返回原始二进制数据

3. **错误恢复**
   - 实现Tool级别的重试机制
   - 使用友好的错误信息替换技术堆栈
   - 将错误反馈给模型尝试自动修复

### 8.2 CodeAgent最佳实践

1. **代码执行监控**
   - 在系统提示中鼓励使用print输出进度
   - 设置合理的执行超时时间
   - 监控内存使用情况

2. **代码质量**
   - 使用结构化输出提高代码解析可靠性
   - 在系统提示中明确代码格式要求
   - 实现代码格式验证

3. **安全控制**
   - 严格控制authorized_imports
   - 使用沙箱执行环境
   - 监控敏感操作

### 8.3 通用最佳实践

1. **流输出设计**
   - 实现统一的chunk类型处理
   - 使用异步编程模型
   - 设计清晰的状态机

2. **错误处理**
   - 使用错误处理决策树
   - 实现优雅降级
   - 记录详细的错误上下文

3. **监控告警**
   - 监控关键延迟指标
   - 设置合理的告警阈值
   - 实现可观测性埋点

4. **前端集成**
   - 实现加载状态指示器
   - 支持取消操作
   - 优雅处理断线重连

---

## 附录：错误处理决策树

![[smolagents-流输出错误处理决策树.svg]]

---

## 参考文档

- [[agents.py|smolagents agents.py源码]]
- [[models.py|smolagents models.py源码]]
- [[memory.py|smolagents memory.py源码]]
- smolagents官方文档
