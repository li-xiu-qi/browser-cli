# smolagents 常见问题与解决方案

> 项目: AI数据分析系统  
> 文档类型: FAQ  
> 更新日期: 2026-02-06  
> 关联文档: [[10-smolagents-Retry与错误处理机制.md|Retry与错误处理机制]]

---

## 一、安装问题

### Q1: pip install smolagents 时提示依赖冲突

**问题描述**  
安装过程中出现类似 `ERROR: Cannot install smolagents because these package versions have conflicting dependencies` 的错误。

**解决方案**

1. 使用虚拟环境隔离安装
   ```bash
   python -m venv smolagents_env
   source smolagents_env/bin/activate  # Linux/Mac
   smolagents_env\Scripts\activate     # Windows
   pip install smolagents
   ```

2. 使用 uv 进行快速安装，uv 的依赖解析更高效
   ```bash
   uv pip install smolagents
   ```

3. 如果冲突涉及 torch，先单独安装 torch 再安装 smolagents
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
   pip install smolagents --no-deps
   pip install transformers accelerate gradio  # 手动安装必要依赖
   ```

**预防措施**  
安装前使用 `pip check` 检查当前环境依赖状态。建议始终在新虚拟环境中安装 smolagents。

---

### Q2: 安装后导入 smolagents 报错 `ModuleNotFoundError`

**问题描述**  
安装完成后运行 `import smolagents` 提示找不到模块。

**解决方案**

1. 确认安装位置
   ```bash
   pip show smolagents
   python -c "import sys; print(sys.path)"
   ```

2. 检查 Python 版本，smolagents 需要 Python 3.10+
   ```bash
   python --version
   ```

3. 如果是多 Python 版本环境，使用正确的 pip
   ```bash
   python3.10 -m pip install smolagents
   python3.10 -c "import smolagents"
   ```

4. 清理 pip 缓存后重新安装
   ```bash
   pip cache purge
   pip install --no-cache-dir smolagents
   ```

---

### Q3: Windows 系统下安装失败

**问题描述**  
Windows 平台安装时出现编译错误或权限拒绝。

**解决方案**

1. 安装 Visual C++ Build Tools
   - 下载地址: https://visualstudio.microsoft.com/visual-cpp-build-tools/
   - 安装 "Desktop development with C++" 工作负载

2. 使用管理员权限运行终端

3. 如果涉及 rust 依赖，先安装 Rust
   ```bash
   # 使用 rustup 安装
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
   ```

4. 使用预编译 wheel 避免本地编译
   ```bash
   pip install --only-binary :all: smolagents
   ```

---

### Q4: 企业内网环境无法安装

**问题描述**  
由于网络限制，无法从 PyPI 直接下载包。

**解决方案**

1. 使用内部 PyPI 镜像
   ```bash
   pip install smolagents -i https://your-internal-pypi.com/simple
   ```

2. 离线安装，先在有网络环境下载 whl 文件
   ```bash
   # 有网络环境
   pip download smolagents -d ./smolagents_packages
   
   # 拷贝到内网环境后安装
   pip install --no-index --find-links ./smolagents_packages smolagents
   ```

3. 使用 conda 安装，如果企业有 conda 镜像
   ```bash
   conda install -c conda-forge smolagents
   ```

---

## 二、运行问题

### 2.1 模型调用失败

#### Q5: API Key 错误 `AuthenticationError`

**问题描述**  
运行时报错提示 API key 无效或认证失败。

**错误信息示例**
```
AuthenticationError: Invalid API key provided
```

**解决方案**

1. 检查环境变量设置
   ```python
   import os
   print(os.environ.get("OPENAI_API_KEY"))  # 确认变量已设置
   ```

2. 在代码中显式传递 API key
   ```python
   from smolagents import OpenAIServerModel
   
   model = OpenAIServerModel(
       model_id="gpt-4",
       api_key="your-api-key-here",  # 直接传递
       api_base="https://api.openai.com/v1"
   )
   ```

3. 检查 .env 文件加载
   ```python
   from dotenv import load_dotenv
   load_dotenv()  # 确保在导入 smolagents 前加载
   ```

4. 验证 API key 权限，确认 key 有调用目标模型的权限

---

#### Q6: 模型不可用或模型名称错误

**问题描述**  
报错提示模型不存在或无法访问指定模型。

**错误信息示例**
```
NotFoundError: The model 'gpt-4-turbo' does not exist
```

**解决方案**

1. 确认模型名称拼写正确
   - OpenAI: `gpt-4`, `gpt-4o`, `gpt-3.5-turbo`
   - Anthropic: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`
   - 本地模型: 使用 HuggingFace 完整模型 ID

2. 检查模型访问权限
   - 对于 GPT-4 等高级模型，需要先在 OpenAI 后台开通权限
   - 确认账户有足够额度

3. 使用正确的模型类
   ```python
   # OpenAI API
   from smolagents import OpenAIServerModel
   model = OpenAIServerModel(model_id="gpt-4")
   
   # Azure OpenAI
   from smolagents import AzureOpenAIServerModel
   model = AzureOpenAIServerModel(
       model_id="gpt-4",
       azure_endpoint="https://your-resource.openai.azure.com/"
   )
   
   # HuggingFace
   from smolagents import HfApiModel
   model = HfApiModel(model_id="meta-llama/Llama-2-70b-chat-hf")
   ```

---

#### Q7: 网络超时和连接错误

**问题描述**  
调用模型时出现超时或连接中断。

**错误信息示例**
```
TimeoutError: Request timed out after 30 seconds
ConnectionError: Connection reset by peer
```

**解决方案**

1. 增加超时时间
   ```python
   from smolagents import OpenAIServerModel
   
   model = OpenAIServerModel(
       model_id="gpt-4",
       timeout=120  # 增加到120秒
   )
   ```

2. 启用自动重试，smolagents 内置 Retrying 机制
   ```python
   model = OpenAIServerModel(
       model_id="gpt-4",
       retry=True  # 启用重试
   )
   ```
   重试配置默认参数:
   - 最大尝试次数: 3次
   - 初始等待: 60秒
   - 指数退避: 2倍
   - 随机抖动: 启用

3. 使用代理
   ```python
   import os
   os.environ["HTTP_PROXY"] = "http://proxy.company.com:8080"
   os.environ["HTTPS_PROXY"] = "http://proxy.company.com:8080"
   ```

4. 检查 DNS 解析
   ```bash
   nslookup api.openai.com
   ```

---

#### Q8: 速率限制错误 429

**问题描述**  
频繁调用时触发 API 速率限制。

**错误信息示例**
```
RateLimitError: Rate limit exceeded: 429 Too Many Requests
```

**解决方案**

1. 启用 smolagents 自动重试，自动处理 429 错误
   ```python
   model = OpenAIServerModel(model_id="gpt-4", retry=True)
   ```

2. 自定义重试参数
   ```python
   from smolagents.utils import Retrying
   
   custom_retryer = Retrying(
       max_attempts=5,
       wait_seconds=30,
       exponential_base=2,
       jitter=True
   )
   ```

3. 实施调用限流
   ```python
   import time
   from functools import wraps
   
   def rate_limit(max_per_minute):
       min_interval = 60.0 / max_per_minute
       last_call = [0.0]
       
       def decorator(func):
           @wraps(func)
           def wrapper(*args, **kwargs):
               elapsed = time.time() - last_call[0]
               if elapsed < min_interval:
                   time.sleep(min_interval - elapsed)
               last_call[0] = time.time()
               return func(*args, **kwargs)
           return wrapper
       return decorator
   ```

4. 升级 API 账户等级获取更高配额

---

### 2.2 代码执行错误

#### Q9: Python 导入错误 `ImportError`

**问题描述**  
Agent 生成的代码中包含无法导入的模块。

**错误信息示例**
```
AgentExecutionError: Import of pandas is not allowed
```

**解决方案**

1. 配置允许导入的模块列表
   ```python
   from smolagents import CodeAgent
   
   agent = CodeAgent(
       tools=[],
       model=model,
       additional_authorized_imports=["pandas", "numpy", "matplotlib"]
   )
   ```

2. 使用更宽松的导入策略，开发测试时使用
   ```python
   agent = CodeAgent(
       tools=[],
       model=model,
       additional_authorized_imports=["*"]  # 允许所有导入，生产环境慎用
   )
   ```

3. 预安装需要的包
   ```bash
   pip install pandas numpy matplotlib seaborn
   ```

4. 查看默认允许的导入列表
   ```python
   from smolagents.local_python_executor import BASE_BUILTIN_MODULES
   print(BASE_BUILTIN_MODULES)
   ```

---

#### Q10: 代码语法错误

**问题描述**  
Agent 生成的代码存在语法问题导致执行失败。

**错误信息示例**
```
AgentExecutionError: unexpected EOF while parsing
```

**解决方案**

1. 检查模型输出格式，确保使用支持代码生成的模型
   - 推荐: GPT-4, Claude-3, CodeLlama
   - 避免使用过度简化的模型

2. 优化系统提示词
   ```python
   agent = CodeAgent(
       tools=[],
       model=model,
       system_prompt="""你是一个专业的Python程序员。
生成代码时请注意:
1. 代码必须完整，不要截断
2. 使用正确的缩进
3. 确保所有引号和括号配对
4. 导入语句放在最前面"""
   )
   ```

3. 查看完整的错误堆栈
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

4. 手动修正后重新运行，或让 Agent 继续修复
   ```python
   # 在错误提示中告诉 Agent 具体问题
   result = agent.run("修复之前代码中的缩进错误，任务: 计算平均值")
   ```

---

#### Q11: 代码执行超时

**问题描述**  
Agent 生成的代码运行时间过长。

**解决方案**

1. 设置执行超时时间
   ```python
   from smolagents import CodeAgent
   
   agent = CodeAgent(
       tools=[],
       model=model,
       executor_timeout=30  # 30秒超时
   )
   ```

2. 优化提示词，要求高效代码
   ```python
   agent.run("""
   分析这个CSV文件，要求:
   1. 使用向量化操作，不要用循环
   2. 如果数据量大，先采样再分析
   3. 设置超时保护
   
   文件: data.csv
   """)
   ```

3. 对于长时间任务，使用 Tool 替代 CodeAgent
   ```python
   from smolagents import Tool
   
   class LongRunningAnalysis(Tool):
       name = "long_analysis"
       description = "执行耗时分析"
       
       def forward(self, file_path: str):
           # 在这里实现超时控制
           import signal
           
           def timeout_handler(signum, frame):
               raise TimeoutError("分析超时")
           
           signal.signal(signal.SIGALRM, timeout_handler)
           signal.alarm(60)  # 60秒
           
           try:
               # 执行分析
               result = self.analyze(file_path)
               return result
           finally:
               signal.alarm(0)
   ```

---

### 2.3 工具调用异常

#### Q12: 工具参数错误

**问题描述**  
调用工具时参数类型或格式不匹配。

**错误信息示例**
```
AgentToolCallError: Missing required parameter 'file_path'
ValidationError: Expected str, got int for parameter 'query'
```

**解决方案**

1. 检查工具定义，确保参数类型标注正确
   ```python
   from smolagents import Tool
   from typing import Optional
   
   class FileReader(Tool):
       name = "file_reader"
       description = "读取文件内容"
       inputs = {
           "file_path": {
               "type": "string",
               "description": "文件的完整路径"
           },
           "encoding": {
               "type": "string", 
               "description": "文件编码",
               "nullable": True
           }
       }
       output_type = "string"
       
       def forward(self, file_path: str, encoding: Optional[str] = "utf-8"):
           with open(file_path, "r", encoding=encoding) as f:
               return f.read()
   ```

2. 在工具内部添加参数校验
   ```python
   def forward(self, file_path: str):
       if not isinstance(file_path, str):
           raise ValueError(f"file_path 必须是字符串，当前类型: {type(file_path)}")
       if not os.path.exists(file_path):
           raise FileNotFoundError(f"文件不存在: {file_path}")
       # ...
   ```

3. 使用示例引导 Agent 正确使用
   ```python
   class FileReader(Tool):
       name = "file_reader"
       description = """读取文件内容。
       
       使用示例:
       file_reader(file_path="/path/to/file.txt")
       file_reader(file_path="data.csv", encoding="gbk")
       """
       # ...
   ```

---

#### Q13: 工具不可用

**问题描述**  
Agent 尝试调用未注册或不存在的工具。

**错误信息示例**
```
AgentToolExecutionError: Tool 'web_search' not found
```

**解决方案**

1. 确认工具已正确注册
   ```python
   from smolagents import CodeAgent, DuckDuckGoSearchTool
   
   search_tool = DuckDuckGoSearchTool()
   agent = CodeAgent(
       tools=[search_tool],  # 确保工具在列表中
       model=model
   )
   ```

2. 查看 Agent 可用的工具列表
   ```python
   print(agent.tools)
   print(agent.tools.keys())
   ```

3. 检查工具名称拼写
   ```python
   # 工具名称区分大小写
   agent.run("使用 web_search 搜索...")  # 如果工具名是 WebSearch 会失败
   ```

4. 使用默认工具集
   ```python
   from smolagents import TOOLING_DEFAULT_TOOLS
   
   agent = CodeAgent(
       tools=TOOLING_DEFAULT_TOOLS,
       model=model
   )
   ```

---

#### Q14: 工具返回值处理错误

**问题描述**  
工具返回的数据类型 Agent 无法正确处理。

**解决方案**

1. 明确指定输出类型
   ```python
   class DataAnalysisTool(Tool):
       name = "data_analysis"
       description = "数据分析工具"
       inputs = {...}
       output_type = "string"  # 明确指定为字符串
       
       def forward(self, data: str):
           result = self.analyze(data)
           return str(result)  # 确保返回字符串
   ```

2. 对于复杂返回类型，使用 JSON 字符串
   ```python
   import json
   
   def forward(self, query: str):
       result = {
           "status": "success",
           "data": self.query_db(query),
           "count": len(results)
       }
       return json.dumps(result, ensure_ascii=False)
   ```

3. 处理异常情况，返回错误信息而非抛出异常
   ```python
   def forward(self, file_path: str):
       try:
           with open(file_path) as f:
               return f.read()
       except Exception as e:
           return f"错误: 无法读取文件 - {str(e)}"
   ```

---

### 2.4 内存溢出

#### Q15: 处理大数据时出现 MemoryError

**问题描述**  
Agent 处理大文件或大量数据时内存耗尽。

**错误信息示例**
```
MemoryError: Unable to allocate array
```

**解决方案**

1. 使用分块处理
   ```python
   # 在工具中实现分块读取
   def process_large_file(file_path: str):
       chunk_size = 10000
       results = []
       
       for chunk in pd.read_csv(file_path, chunksize=chunk_size):
           # 处理每一块
           processed = chunk.groupby("category").sum()
           results.append(processed)
       
       return pd.concat(results)
   ```

2. 限制返回数据量
   ```python
   class DatabaseTool(Tool):
       def forward(self, query: str, limit: int = 1000):
           # 强制添加 LIMIT
           if "LIMIT" not in query.upper():
               query += f" LIMIT {limit}"
           return self.execute(query)
   ```

3. 使用生成器而非列表
   ```python
   def search_items(query: str):
       # 使用生成器逐条返回
       for item in database.search(query):
           yield item
           if item.count > 100:  # 限制返回数量
               break
   ```

4. 监控系统内存
   ```python
   import psutil
   
   def check_memory():
       memory = psutil.virtual_memory()
       if memory.percent > 80:
           raise MemoryError("系统内存不足，请减少数据量")
   ```

---

#### Q16: 循环引用导致内存泄漏

**问题描述**  
Agent 多次运行后内存持续增长不释放。

**解决方案**

1. 定期清理 Agent 的 memory
   ```python
   agent = CodeAgent(tools=[], model=model)
   
   for task in tasks:
       result = agent.run(task)
       # 任务完成后清理 memory
       agent.memory.steps = []
   ```

2. 重新创建 Agent 实例
   ```python
   def process_batch(items):
       results = []
       for item in items:
           # 每个任务创建新 Agent
           agent = CodeAgent(tools=[], model=model)
           result = agent.run(f"处理: {item}")
           results.append(result)
           # Agent 会被垃圾回收
       return results
   ```

3. 手动调用垃圾回收
   ```python
   import gc
   
   agent.run(task)
   gc.collect()  # 强制垃圾回收
   ```

---

## 三、性能问题

### Q17: Agent 响应速度慢

**问题描述**  
Agent 执行任务耗时过长。

**可能原因与解决方案**

| 原因 | 诊断方法 | 解决方案 |
|------|----------|----------|
| 模型延迟 | 查看模型 API 响应时间 | 切换到低延迟模型如 gpt-3.5-turbo |
| 代码执行慢 | 检查是否有复杂计算 | 优化代码或使用预编译工具 |
| 网络延迟 | ping API 端点 | 使用就近的服务端点或 CDN |
| 过多步骤 | 查看 step_number | 增加 max_steps 或优化任务拆分 |

**综合优化方案**

1. 使用流式响应提升感知速度
   ```python
   for step in agent.run_stream("复杂任务"):
       print(f"步骤 {step.step_number} 完成")
   ```

2. 设置合理的 max_steps
   ```python
   agent = CodeAgent(
       tools=[],
       model=model,
       max_steps=5  # 限制步数避免无限循环
   )
   ```

3. 缓存常用工具结果
   ```python
   from functools import lru_cache
   
   class CachedSearchTool(Tool):
       @lru_cache(maxsize=100)
       def forward(self, query: str):
           return self.perform_search(query)
   ```

---

### Q18: Token 消耗过高

**问题描述**  
API 调用费用超出预期。

**原因分析**

1. 上下文过长导致每次请求 Token 数增加
2. 重复调用模型进行相同或相似查询
3. 模型生成过长的代码或解释

**解决方案**

1. 启用上下文摘要
   ```python
   agent = CodeAgent(
       tools=[],
       model=model,
       memory_summary=True  # 启用自动摘要
   )
   ```

2. 定期重置对话
   ```python
   # 每完成一个独立任务后重置
   agent.memory.steps = []
   ```

3. 使用更小的模型处理简单任务
   ```python
   from smolagents import OpenAIServerModel
   
   # 简单任务使用轻量级模型
   simple_model = OpenAIServerModel(model_id="gpt-3.5-turbo")
   complex_model = OpenAIServerModel(model_id="gpt-4")
   
   simple_agent = CodeAgent(tools=[], model=simple_model)
   complex_agent = CodeAgent(tools=[], model=complex_model)
   ```

4. 优化提示词减少模型输出长度
   ```python
   agent.run("分析数据，用一句话总结关键发现")
   ```

---

### Q19: 并发处理瓶颈

**问题描述**  
同时运行多个 Agent 实例时性能下降。

**解决方案**

1. 使用线程池管理并发
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   def run_agent_task(task):
       agent = CodeAgent(tools=[], model=model)
       return agent.run(task)
   
   with ThreadPoolExecutor(max_workers=3) as executor:
       results = list(executor.map(run_agent_task, tasks))
   ```

2. 共享模型实例，每个 Agent 独立但共享模型连接
   ```python
   shared_model = OpenAIServerModel(model_id="gpt-4")
   
   agents = [
       CodeAgent(tools=[], model=shared_model)
       for _ in range(5)
   ]
   ```

3. 使用异步 API 如果支持
   ```python
   import asyncio
   
   async def async_agent_run(agent, task):
       # 如果模型支持异步调用
       return await agent.run_async(task)
   ```

---

## 四、多 Agent 问题

### Q20: 子 Agent 调用失败

**问题描述**  
管理 Agent 调用子 Agent 时出错。

**错误信息示例**
```
AgentToolExecutionError: Error executing request to team member 'data_analyst'
```

**解决方案**

1. 确认子 Agent 已正确注册为工具
   ```python
   from smolagents import CodeAgent, ManagedAgent
   
   sub_agent = CodeAgent(tools=[], model=sub_model)
   managed = ManagedAgent(
       agent=sub_agent,
       name="data_analyst",
       description="专门处理数据分析任务"
   )
   
   main_agent = CodeAgent(
       tools=[managed],  # 将子 Agent 作为工具传入
       model=main_model
   )
   ```

2. 检查子 Agent 的描述是否清晰
   ```python
   managed = ManagedAgent(
       agent=sub_agent,
       name="data_analyst",
       description="""数据分析专家 Agent。
       
       适用场景:
       - 处理 CSV、Excel 文件
       - 生成统计报表
       - 数据可视化
       
       调用示例: data_analyst(task="分析 sales.csv 中的月度趋势")
       """
   )
   ```

3. 限制子 Agent 的 max_steps
   ```python
   sub_agent = CodeAgent(
       tools=[],
       model=sub_model,
       max_steps=3  # 子 Agent 限制步数
   )
   ```

---

### Q21: 多 Agent 调用链追踪困难

**问题描述**  
难以追踪 Agent 之间的调用关系和执行流程。

**解决方案**

1. 启用详细日志
   ```python
   import logging
   logging.basicConfig(
       level=logging.DEBUG,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

2. 为每个 Agent 设置唯一标识
   ```python
   sub_agent1 = CodeAgent(
       tools=[],
       model=model,
       name="web_searcher"
   )
   sub_agent2 = CodeAgent(
       tools=[],
       model=model,
       name="data_analyst"
   )
   ```

3. 自定义日志记录器
   ```python
   from smolagents.utils import AgentLogger, LogLevel
   
   logger = AgentLogger()
   logger.LEVEL = LogLevel.DEBUG
   
   agent = CodeAgent(
       tools=[],
       model=model,
       logger=logger
   )
   ```

4. 使用回调函数追踪执行
   ```python
   def on_step_complete(step):
       print(f"[追踪] Agent 完成步骤 {step.step_number}")
       if step.error:
           print(f"[追踪] 步骤出错: {step.error}")
   
   agent.run("任务", callbacks=[on_step_complete])
   ```

---

### Q22: 多 Agent 结果不一致

**问题描述**  
相同任务多次执行结果不同。

**解决方案**

1. 设置随机种子
   ```python
   import random
   import numpy as np
   
   random.seed(42)
   np.random.seed(42)
   ```

2. 对于 LLM 调用，设置 temperature=0
   ```python
   model = OpenAIServerModel(
       model_id="gpt-4",
       temperature=0  # 确定性输出
   )
   ```

3. 使用确定性工具
   ```python
   class DeterministicSearch(Tool):
       @lru_cache(maxsize=None)
       def forward(self, query: str):
           # 缓存确保相同查询返回相同结果
           return self.search(query)
   ```

4. 记录完整执行轨迹以便对比
   ```python
   result = agent.run("任务")
   
   # 保存执行历史
   import json
   history = [step.dict() for step in agent.memory.steps]
   with open("execution_trace.json", "w") as f:
       json.dump(history, f, indent=2)
   ```

---

### Q23: Token 统计不准确

**问题描述**  
多 Agent 场景下难以统计总 Token 消耗。

**解决方案**

1. 在每个 Agent 中记录 Token 使用
   ```python
   class TokenTracker:
       def __init__(self):
           self.total_tokens = 0
           self.call_count = 0
       
       def record(self, tokens: int):
           self.total_tokens += tokens
           self.call_count += 1
   
   tracker = TokenTracker()
   
   # 自定义模型包装器记录 Token
   class TrackedModel:
       def __init__(self, base_model, tracker):
           self.base_model = base_model
           self.tracker = tracker
       
       def generate(self, messages, **kwargs):
           response = self.base_model.generate(messages, **kwargs)
           if hasattr(response, 'usage'):
               self.tracker.record(response.usage.total_tokens)
           return response
   ```

2. 汇总所有 Agent 的 Token 消耗
   ```python
   def run_multi_agent_system(task, agents_config):
       total_tokens = 0
       
       for agent_name, agent in agents_config.items():
           result = agent.run(task)
           tokens = agent.get_token_usage()  # 假设有此方法
           total_tokens += tokens
           print(f"{agent_name}: {tokens} tokens")
       
       print(f"总消耗: {total_tokens} tokens")
   ```

---

## 五、调试技巧

### Q24: 如何设置日志级别

**解决方案**

1. 设置 smolagents 内部日志级别
   ```python
   import logging
   
   # 设置 smolagents 日志
   smolagents_logger = logging.getLogger("smolagents")
   smolagents_logger.setLevel(logging.DEBUG)
   
   # 添加控制台处理器
   handler = logging.StreamHandler()
   handler.setLevel(logging.DEBUG)
   formatter = logging.Formatter(
       '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   handler.setFormatter(formatter)
   smolagents_logger.addHandler(handler)
   ```

2. 不同日志级别说明
   - DEBUG: 详细的执行步骤、工具调用参数、模型输入输出
   - INFO: 主要执行阶段、错误提示
   - WARNING: 非致命问题
   - ERROR: 执行错误

3. 日志级别推荐
   - 开发阶段: DEBUG
   - 测试阶段: INFO
   - 生产阶段: WARNING

---

### Q25: 如何追踪调用链

**解决方案**

1. 使用 AgentLogger
   ```python
   from smolagents.utils import AgentLogger, LogLevel
   
   logger = AgentLogger()
   logger.LEVEL = LogLevel.DEBUG
   
   agent = CodeAgent(
       tools=[],
       model=model,
       logger=logger
   )
   ```

2. 分析 memory.steps
   ```python
   result = agent.run("任务")
   
   for step in agent.memory.steps:
       print(f"步骤 {step.step_number}:")
       print(f"  动作: {step.action}")
       print(f"  观察: {step.observations}")
       print(f"  错误: {step.error}")
       print(f"  时间: {step.timing}")
   ```

3. 导出完整执行记录
   ```python
   import json
   
   execution_log = {
       "task": "任务描述",
       "steps": [],
       "final_result": result
   }
   
   for step in agent.memory.steps:
       execution_log["steps"].append({
           "step_number": step.step_number,
           "action": str(step.action) if step.action else None,
           "observations": step.observations,
           "error": str(step.error) if step.error else None,
           "duration": step.timing.duration if step.timing else None
       })
   
   with open("execution_log.json", "w", encoding="utf-8") as f:
       json.dump(execution_log, f, ensure_ascii=False, indent=2)
   ```

---

### Q26: 问题定位方法

**系统化排查流程**

1. 确认问题层级
   ```
   模型层 -> 检查 API 调用和响应
     ↓
   解析层 -> 检查输出格式解析
     ↓
   执行层 -> 检查代码/工具执行
     ↓
   工具层 -> 检查具体工具实现
   ```

2. 逐层隔离测试
   ```python
   # 1. 单独测试模型
   response = model.generate([{"role": "user", "content": "测试"}])
   print(response)
   
   # 2. 单独测试工具
   tool_result = my_tool.forward(param="test")
   print(tool_result)
   
   # 3. 使用最小 Agent 测试
   minimal_agent = CodeAgent(tools=[], model=model)
   result = minimal_agent.run("1+1等于几")
   ```

3. 使用断点调试
   ```python
   import pdb
   
   # 在可疑位置设置断点
   def suspicious_function():
       pdb.set_trace()  # 执行到这里会进入交互式调试
       # ...
   ```

---

### Q27: 如何创建最小复现案例

**步骤**

1. 剥离业务逻辑，保留核心问题
   ```python
   # 原始复杂代码
   # ... 50行业务代码 ...
   
   # 最小复现
   from smolagents import CodeAgent, OpenAIServerModel
   
   model = OpenAIServerModel(model_id="gpt-4")
   agent = CodeAgent(tools=[], model=model)
   
   # 最简单的能触发问题的任务
   result = agent.run("读取不存在的文件")
   ```

2. 使用 mock 数据
   ```python
   # 不要依赖外部资源
   from unittest.mock import Mock, patch
   
   mock_model = Mock()
   mock_model.generate.return_value = "print('hello')"
   
   agent = CodeAgent(tools=[], model=mock_model)
   ```

3. 记录环境信息
   ```python
   import smolagents
   import sys
   
   print(f"Python: {sys.version}")
   print(f"smolagents: {smolagents.__version__}")
   print(f"OS: {sys.platform}")
   ```

---

## 六、错误码参考

### smolagents 异常类型速查表

| 错误类型 | 触发条件 | 解决方案 |
|----------|----------|----------|
| AgentError | 所有异常的基类 | 查看具体子类型 |
| AgentParsingError | 解析模型输出失败 | 检查模型输出格式；换用更强的模型 |
| AgentExecutionError | Python 代码执行失败 | 检查导入权限；检查代码语法；查看执行日志 |
| AgentToolCallError | 工具参数验证失败 | 检查参数类型和必填项 |
| AgentToolExecutionError | 工具执行出错 | 检查工具实现；查看工具内部异常 |
| AgentMaxStepsError | 达到最大步数限制 | 增加 max_steps；简化任务；优化提示词 |
| AgentGenerationError | 模型 API 调用失败 | 检查 API key；检查网络；查看模型可用性 |

### 常见 HTTP 状态码

| 状态码 | 含义 | 解决方案 |
|--------|------|----------|
| 400 | 请求参数错误 | 检查请求格式；查看 API 文档 |
| 401 | 认证失败 | 检查 API key；检查密钥权限 |
| 403 | 权限不足 | 确认账户已开通该模型访问权限 |
| 404 | 模型不存在 | 检查模型名称拼写 |
| 429 | 速率限制 | 启用 retry；降低调用频率；升级账户 |
| 500 | 服务端错误 | 稍后重试；联系服务提供商 |
| 503 | 服务不可用 | 检查服务状态页面；稍后重试 |

### 常见 Python 异常映射

| Python 异常 | smolagents 包装 | 处理建议 |
|-------------|-----------------|----------|
| ImportError | AgentExecutionError | 添加 additional_authorized_imports |
| SyntaxError | AgentExecutionError | 让模型修正代码 |
| TimeoutError | AgentExecutionError | 增加 executor_timeout |
| MemoryError | AgentExecutionError | 减少数据量；优化算法 |
| ValueError | AgentToolCallError | 检查工具参数定义 |
| TypeError | AgentToolCallError | 检查参数类型匹配 |

---

## 七、调试工具

### 推荐工具列表

| 工具 | 用途 | 安装命令 |
|------|------|----------|
| logging | 内置日志记录 | 内置 |
| pdb | 交互式调试 | 内置 |
| ipdb | 增强版 pdb | `pip install ipdb` |
| rich | 美化输出和日志 | `pip install rich` |
| loguru | 现代日志库 | `pip install loguru` |
| py-spy | 性能分析 | `pip install py-spy` |
| memory_profiler | 内存分析 | `pip install memory_profiler` |

### 使用 rich 美化 smolagents 输出

```python
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

# 美化显示 Agent 执行结果
def pretty_print_agent_result(agent, result):
    console.print(Panel(f"最终结果: {result}", title="Agent Result"))
    
    for step in agent.memory.steps:
        if step.action:
            code = Syntax(str(step.action), "python", theme="monokai")
            console.print(Panel(code, title=f"Step {step.step_number}"))
        
        if step.error:
            console.print(Panel(
                str(step.error), 
                title="Error", 
                style="red"
            ))
```

### 使用 loguru 记录详细日志

```python
from loguru import logger
import sys

# 配置 loguru
logger.remove()
logger.add(sys.stderr, level="DEBUG")
logger.add("smolagents.log", rotation="10 MB", level="DEBUG")

# 包装 Agent 调用
@logger.catch  # 自动记录异常
def run_agent_with_logging(agent, task):
    logger.info(f"开始执行任务: {task}")
    result = agent.run(task)
    logger.info(f"任务完成，结果: {result}")
    return result
```

### 性能分析示例

```python
import cProfile
import pstats

# 分析 Agent 性能
profiler = cProfile.Profile()
profiler.enable()

result = agent.run("复杂数据分析任务")

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 打印前20个最耗时的函数
```

---

## 相关文档

- [[10-smolagents-Retry与错误处理机制.md|Retry与错误处理机制]]
- [[30-smolagents-概念清单.md|概念清单]]
- [[31-smolagents-数据与变量清单.md|数据与变量清单]]
- [[33-smolagents-API参考.md|API参考]]

---

*文档版本: 1.0  
更新日期: 2026-02-06*
