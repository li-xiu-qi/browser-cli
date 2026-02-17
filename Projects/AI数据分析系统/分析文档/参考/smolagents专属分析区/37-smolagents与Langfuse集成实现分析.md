# smolagents 与 Langfuse 集成实现分析

> 项目: smolagents + Langfuse  
> 分析日期: 2026-02-06  
> 参考文档: https://langfuse.com/integrations/frameworks/smolagents

---

## 一、集成概述

### 1.1 什么是 Langfuse

Langfuse 是一个开源的 LLM 可观测性平台，提供：

- **Tracing**: 追踪 LLM 应用的完整执行链路
- **Monitoring**: 实时监控性能指标
- **Evaluation**: 评估 Agent 输出质量
- **Debugging**: 调试复杂的 Agent 行为

### 1.2 集成架构

```
┌─────────────────────────────────────────────────────────────┐
│                    smolagents Agent                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ CodeAgent   │  │ ToolCalling │  │ MultiStepAgent      │ │
│  │             │  │ Agent       │  │                     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                    │            │
│         └────────────────┴────────────────────┘            │
│                          │                                  │
│         ┌────────────────┴────────────────────┐            │
│         │     SmolagentsInstrumentor          │            │
│         │  (openinference-instrumentation-    │            │
│         │   smolagents)                       │            │
│         └────────────────┬────────────────────┘            │
└──────────────────────────┼──────────────────────────────────┘
                           │ OpenTelemetry Protocol
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Langfuse Platform                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Trace       │  │ Metrics     │  │ Evaluation          │ │
│  │ Dashboard   │  │ Dashboard   │  │ Dashboard           │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 核心技术栈

| 组件 | 作用 |
|------|------|
| **OpenTelemetry** | 分布式追踪标准协议 |
| **SmolagentsInstrumentor** | smolagents 的 OTel 插桩器 |
| **Langfuse** | OTel 后端，接收并展示追踪数据 |

---

## 二、集成实现步骤

### 2.1 安装依赖

```bash
# 核心依赖
pip install langfuse "smolagents[telemetry]" openinference-instrumentation-smolagents

# 或者完整安装（包含所有遥测和工具支持）
pip install langfuse "smolagents[telemetry,toolkit]"
```

依赖说明：

| 包 | 用途 |
|----|------|
| `langfuse` | Langfuse Python SDK |
| `smolagents[telemetry]` | smolagents 遥测支持 |
| `openinference-instrumentation-smolagents` | OTel 插桩实现 |

### 2.2 配置环境变量

```python
import os

# Langfuse 认证配置
os.environ["LANGFUSE_PUBLIC_KEY"] = "pk-lf-xxxxxxxx"      # 公钥
os.environ["LANGFUSE_SECRET_KEY"] = "sk-lf-xxxxxxxx"      # 私钥
os.environ["LANGFUSE_HOST"] = "https://cloud.langfuse.com"  # 服务端点

# Hugging Face Token（如使用 HF 模型）
os.environ["HF_TOKEN"] = "hf_xxxxxxxx"
```

获取 API Key：
1. 注册 Langfuse Cloud 账号或自建 Langfuse
2. 在项目设置中创建 API 凭证

### 2.3 初始化 Instrumentor

```python
from openinference.instrumentation.smolagents import SmolagentsInstrumentor
from langfuse import get_client

# 方式1：简单初始化（推荐）
SmolagentsInstrumentor().instrument()

# 方式2：验证连接后初始化
langfuse = get_client()
if langfuse.auth_check():
    print("Langfuse 连接成功")
    SmolagentsInstrumentor().instrument()
else:
    print("Langfuse 连接失败，请检查配置")
```

### 2.4 运行 Agent

```python
from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    WebSearchTool,
    VisitWebpageTool,
    InferenceClientModel,
)

# 创建模型
model = InferenceClientModel(
    model_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"
)

# 创建子 Agent
search_agent = ToolCallingAgent(
    tools=[WebSearchTool(), VisitWebpageTool()],
    model=model,
    name="search_agent",
    description="执行网络搜索的工具 Agent",
)

# 创建主 Agent
manager_agent = CodeAgent(
    tools=[],
    model=model,
    managed_agents=[search_agent],
)

# 运行（会自动追踪到 Langfuse）
result = manager_agent.run(
    "如果美国保持2024年的增长率，GDP翻倍需要多少年？"
)
```

---

## 三、追踪数据结构

### 3.1 Trace 结构

每个 Agent 运行会产生一个 Trace，包含多个 Span：

```
Trace: agent_run_xxx
├── Span: CodeAgent.run
│   ├── Span: llm_call (生成计划)
│   ├── Span: tool_call (调用 search_agent)
│   │   └── Span: ToolCallingAgent.run
│   │       ├── Span: llm_call (生成 tool_calls)
│   │       ├── Span: tool_execution (web_search)
│   │       ├── Span: tool_execution (visit_webpage)
│   │       └── Span: llm_call (生成结果)
│   ├── Span: llm_call (分析结果)
│   └── Span: code_execution (计算)
└── Span: final_answer
```

### 3.2 Span 属性

每个 Span 包含以下信息：

| 属性 | 说明 | 示例 |
|------|------|------|
| `name` | Span 名称 | `CodeAgent.run` |
| `input` | 输入内容 | 用户 query |
| `output` | 输出内容 | Agent 结果 |
| `token_usage` | Token 使用量 | `{"input": 523, "output": 298}` |
| `duration` | 执行耗时 | `12.5s` |
| `attributes` | 自定义属性 | `{"model": "gpt-4o"}` |

### 3.3 多 Agent 追踪示例

```
Trace: manager_run_001
├── Span: manager_planning
│   ├── input: "分析电动车市场"
│   ├── output: "需要搜索销量、价格、用户评价"
│   └── token_usage: {input: 245, output: 156}
├── Span: search_agent_call
│   ├── Span: search_agent_execution
│   │   ├── Span: web_search
│   │   │   ├── input: "2024年电动车销量"
│   │   │   └── output: "搜索结果..."
│   │   └── Span: visit_webpage
│   │       ├── input: "https://..."
│   │       └── output: "页面内容..."
│   └── output: "搜索报告..."
├── Span: analysis
│   ├── input: "搜索报告..."
│   └── output: "分析结论..."
└── Span: final_answer
    └── output: "最终答案..."
```

---

## 四、高级用法

### 4.1 添加自定义属性

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# 在自定义代码中添加追踪
with tracer.start_as_current_span("自定义业务逻辑") as span:
    span.set_attribute("user.id", "user_123")
    span.set_attribute("session.id", "session_456")
    span.set_attribute("custom.tag", "重要任务")
    
    result = agent.run("查询数据")
```

### 4.2 用户反馈收集

```python
from langfuse import get_client

langfuse = get_client()

# 假设从 UI 获取到用户反馈
def handle_user_feedback(trace_id: str, liked: bool):
    """处理用户反馈"""
    score = 1 if liked else 0
    langfuse.score(
        trace_id=trace_id,
        name="用户满意度",
        value=score,
        comment="用户通过点赞/点踩提交的反馈"
    )

# 使用示例
trace_id = "trace_xxx"  # 从追踪中获取
handle_user_feedback(trace_id, liked=True)
```

### 4.3 与 Gradio 集成收集反馈

```python
import gradio as gr
from opentelemetry import trace
from langfuse import get_client

langfuse = get_client()

def respond(prompt, history):
    """处理用户输入并返回响应"""
    with trace.get_tracer(__name__).start_as_current_span("聊天追踪") as span:
        # 运行 Agent
        output = agent.run(prompt)
        
        # 获取当前 trace_id
        trace_id = format_trace_id(
            trace.get_current_span().get_span_context().trace_id
        )
        
        # 添加到历史
        history.append({"role": "assistant", "content": output})
        
    return history, trace_id

def handle_feedback(data: gr.LikeData, trace_id):
    """处理用户点赞/点踩"""
    if data.liked:
        langfuse.score(
            trace_id=trace_id,
            name="用户反馈",
            value=1
        )
    else:
        langfuse.score(
            trace_id=trace_id,
            name="用户反馈",
            value=0
        )

# 构建 Gradio 界面
with gr.Blocks() as demo:
    chatbot = gr.Chatbot()
    prompt_box = gr.Textbox()
    trace_id_box = gr.Textbox(visible=False)
    
    # 提交问题
    prompt_box.submit(
        respond,
        [prompt_box, chatbot],
        [chatbot, trace_id_box]
    )
    
    # 点赞/点踩
    chatbot.like(
        handle_feedback,
        [trace_id_box],
        None
    )

demo.launch()
```

### 4.4 数据集评估

```python
from datasets import load_dataset
from langfuse import get_client

langfuse = get_client()

# 加载评估数据集
dataset = load_dataset("openai/gsm8k", "main", split="train")

# 创建 Langfuse 数据集
langfuse.create_dataset(
    name="math_benchmark",
    description="数学问题评估数据集"
)

# 添加测试用例
for item in dataset.select(range(100)):
    langfuse.create_dataset_item(
        dataset_name="math_benchmark",
        input={"question": item["question"]},
        expected_output={"answer": item["answer"]}
    )

# 在数据集上运行评估
def evaluate_agent(agent, dataset_name):
    """在数据集上评估 Agent"""
    dataset = langfuse.get_dataset(dataset_name)
    
    for item in dataset.items:
        # 运行 Agent
        output = agent.run(item.input["question"])
        
        # 记录到 Langfuse
        langfuse.score(
            trace_id=output.trace_id,
            name="正确答案",
            value=check_answer(output, item.expected_output)
        )
```

---

## 五、监控指标

### 5.1 成本监控

```python
# Token 使用量自动追踪
# 在 Langfuse Dashboard 中查看：
# - 每次调用的 input/output tokens
# - 按模型统计的累计消耗
# - 成本估算（需配置模型价格）
```

### 5.2 延迟分析

```python
# 自动记录的延迟指标：
# - 总调用延迟
# - 每个 Span 的耗时
# - LLM 调用延迟
# - 工具执行延迟

# 在 Dashboard 中可识别瓶颈
```

### 5.3 质量评估

```python
# LLM-as-a-Judge 自动评估

eval_template = """
请评估以下回答的质量：
1. 准确性（1-5分）
2. 完整性（1-5分）
3. 毒性（是/否）

回答内容：{answer}
"""

def auto_evaluate(output: str):
    """自动评估"""
    eval_result = judge_llm.run(
        eval_template.format(answer=output)
    )
    return eval_result
```

---

## 六、最佳实践

### 6.1 生产环境配置

```python
# 1. 使用环境变量配置
import os

os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY")
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY")
os.environ["LANGFUSE_HOST"] = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# 2. 采样策略（高流量场景）
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

sampler = TraceIdRatioBased(0.1)  # 10% 采样

# 3. 错误处理
try:
    SmolagentsInstrumentor().instrument()
except Exception as e:
    logger.warning(f"Langfuse 初始化失败: {e}")
    # 继续运行，不阻塞主流程
```

### 6.2 性能优化

```python
# 1. 异步导出
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

exporter = OTLPSpanExporter(
    endpoint="https://cloud.langfuse.com/api/public/otel/v1/traces",
    timeout=30,  # 超时时间
)

# 2. 批量处理
from opentelemetry.sdk.trace.export import BatchSpanProcessor

span_processor = BatchSpanProcessor(
    exporter,
    max_queue_size=2048,
    max_export_batch_size=512,
)
```

### 6.3 隐私保护

```python
# 1. 敏感数据脱敏
def sanitize_input(input_data: dict) -> dict:
    """脱敏处理"""
    sensitive_keys = ["password", "token", "api_key"]
    for key in sensitive_keys:
        if key in input_data:
            input_data[key] = "***"
    return input_data

# 2. 选择性追踪
import os

if os.getenv("ENABLE_TRACING", "true").lower() == "true":
    SmolagentsInstrumentor().instrument()
```

---

## 七、与官方示例对比

### 7.1 官方文档示例

```python
# 来自 https://langfuse.com/integrations/frameworks/smolagents

from openinference.instrumentation.smolagents import SmolagentsInstrumentor

# 简单初始化
SmolagentsInstrumentor().instrument()

# 然后正常使用 smolagents
```

### 7.2 对比 Phoenix Arize

```python
# Phoenix 集成方式（官方文档也提供）
from phoenix.otel import register
from openinference.instrumentation.smolagents import SmolagentsInstrumentor

register()
SmolagentsInstrumentor().instrument()

# 访问 http://0.0.0.0:6006 查看
```

| 平台 | 部署方式 | 特点 |
|------|----------|------|
| **Langfuse** | Cloud / 自建 | 功能完整，开源，企业级 |
| **Phoenix** | 本地 | 轻量，快速开始 |

---

## 八、常见问题

### Q1: 为什么没有追踪数据？

**排查步骤**：
1. 检查环境变量是否正确设置
2. 确认 `SmolagentsInstrumentor().instrument()` 在 Agent 运行前调用
3. 验证网络连接：`langfuse.auth_check()`
4. 检查采样率设置

### Q2: 如何减少追踪开销？

**解决方案**：
1. 使用采样：`TraceIdRatioBased(0.1)`
2. 异步导出
3. 批量处理
4. 生产环境可选择性关闭

### Q3: 多 Agent 如何追踪？

**答案**：自动支持。每个子 Agent 的调用会生成独立的 Span，嵌套在主 Trace 下。

### Q4: 如何与现有监控系统整合？

**方案**：
- Langfuse 支持 Prometheus 指标导出
- 可以通过 Webhook 接收告警
- 支持与其他 OTel 后端并行使用

---

## 九、对我们项目的启示

### 9.1 推荐架构

```python
# AI数据分析系统 + Langfuse 集成

class DataAnalysisSystem:
    def __init__(self, enable_tracing=True):
        # 初始化追踪
        if enable_tracing:
            self._setup_tracing()
        
        # 初始化 Agent
        self.analyzer = self._create_analyzer()
    
    def _setup_tracing(self):
        """配置 Langfuse 追踪"""
        from openinference.instrumentation.smolagents import SmolagentsInstrumentor
        
        SmolagentsInstrumentor().instrument()
        
        # 可选：添加自定义处理器
        self._setup_custom_processors()
    
    def _setup_custom_processors(self):
        """设置自定义 Span 处理器"""
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        
        exporter = OTLPSpanExporter(
            endpoint=f"{os.getenv('LANGFUSE_HOST')}/api/public/otel/v1/traces",
            headers={"Authorization": f"Basic {self._get_auth_token()}"}
        )
        
        processor = BatchSpanProcessor(exporter)
        # 添加到 tracer provider
    
    def analyze(self, query: str, user_id: str = None):
        """执行分析并追踪"""
        from opentelemetry import trace
        
        tracer = trace.get_tracer(__name__)
        
        with tracer.start_as_current_span("数据分析任务") as span:
            # 添加业务属性
            if user_id:
                span.set_attribute("user.id", user_id)
            span.set_attribute("query.type", self._classify_query(query))
            
            # 执行分析
            result = self.analyzer.run(query)
            
            return result
```

### 9.2 监控指标体系

| 指标类型 | 具体指标 | 用途 |
|----------|----------|------|
| **成本** | Token 消耗、API 调用费用 | 成本控制 |
| **性能** | 延迟分布、吞吐量 | 性能优化 |
| **质量** | 用户反馈、LLM 评估分数 | 质量改进 |
| **业务** | 查询类型分布、成功率 | 业务分析 |

### 9.3 实施建议

1. **渐进式接入**
   - 开发环境：全量追踪
   - 测试环境：采样追踪
   - 生产环境：采样追踪 + 关键业务全量

2. **告警配置**
   - 错误率 > 5%
   - P99 延迟 > 10s
   - Token 消耗异常增长

3. **持续优化**
   - 定期回顾追踪数据
   - 识别高频问题模式
   - 优化 Agent Prompt 和工具

---

## 十、参考资源

- **官方文档**: https://langfuse.com/integrations/frameworks/smolagents
- **GitHub Discussion**: https://github.com/orgs/langfuse/discussions/5536
- **Hugging Face 文档**: https://huggingface.co/docs/smolagents/tutorials/inspect_runs
- **Langfuse Cookbook**: https://langfuse.com/guides/cookbook

---

*本文档基于 Langfuse 官方集成文档和社区实践编写*
