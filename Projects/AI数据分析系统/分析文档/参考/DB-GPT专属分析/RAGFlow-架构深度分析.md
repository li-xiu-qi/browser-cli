# RAGFlow 架构深度分析

> 深入分析 RAGFlow 的 Chat 和文档处理架构，以及与 DB-GPT 的对比。

---

## 一、核心结论

### RAGFlow 的 Chat 用队列吗？

**不用！** RAGFlow 的 Chat 也是同步调用，和 DB-GPT 一样。

### RAGFlow 什么地方用队列？

**文档处理！** 这是 RAGFlow 的核心功能，使用 Redis + Celery。

### 核心定位

```
RAGFlow = 文档智能处理平台（核心）+ 对话 Chat（辅助）
DB-GPT  = 大模型服务平台（核心）+ 知识库（辅助）
```

---

## 二、RAGFlow Chat 架构

![RAGFlow Chat 架构](assets/ragflow-chat-architecture.svg)

### 2.1 架构特点

```
用户请求
    ↓
WebServer (FastAPI)
    ↓
路由分发
    ├── Chat API → 同步处理 → 直接调用 LLM
    └── Doc API  → 异步处理 → 投递队列
```

### 2.2 Chat 处理流程（同步，无队列）

```python
# 伪代码示意
@app.post("/v1/chat/completions")
def chat(request):
    # 1. 检索相关文档
    docs = es.search(request.question)
    
    # 2. 构建 Prompt
    prompt = build_rag_prompt(docs, request.question)
    
    # 3. 调用 LLM API（同步等待）
    response = call_llm_api(prompt)
    
    # 4. 返回结果
    return response
```

**为什么没有队列？**

- 对话需要**实时响应**
- LLM 调用是**同步阻塞**的
- 用户体验要求**立即看到回答**

---

## 三、RAGFlow vs DB-GPT Chat 对比

![Chat 架构对比](assets/ragflow-vs-dbgpt-chat-comparison.svg)

### 3.1 核心差异

| 维度 | DB-GPT | RAGFlow |
|------|--------|---------|
| **Chat 是否用队列** |  **无** |  **无** |
| **调用方式** | Controller-Worker | 直接调用 LLM API |
| **模型部署** | 自托管 Worker (GPU) | 调用外部 API |
| **RAG Pipeline** | AWEL 编排 | 内置 DeepDoc |
| **检索能力** | 基础 | 强（ES + 多种解析） |

### 3.2 关键发现

**共同点**：
-  Chat 都不用队列
-  都是同步调用
-  都支持流式输出

**差异点**：
- DB-GPT 自己托管模型（Worker）
- RAGFlow 调用外部 LLM API

---

## 四、RAGFlow 文档处理队列深度分析

![文档处理队列](assets/ragflow-document-queue-deep-dive.svg)

### 4.1 为什么文档处理必须用队列？

| 原因 | 说明 |
|------|------|
| **耗时长** | PDF 解析可能几分钟 |
| **资源消耗大** | OCR、Embedding 占用大量 CPU/GPU |
| **异步解耦** | 用户上传后即可离开 |
| **削峰填谷** | 控制并发，防止系统过载 |
| **可靠性** | 失败自动重试，任务不丢失 |

### 4.2 Celery 任务队列配置

```python
# Celery 配置
app = Celery('rag_flow')

app.conf.update(
    # 使用 Redis 作为 broker
    broker_url='redis://localhost:6379/0',
    
    # Worker 配置
    worker_prefetch_multiplier=1,  # 公平调度
    task_acks_late=True,           # 完成后再确认
    
    # 任务超时
    task_time_limit=1800,          # 30分钟超时
    
    # 重试配置
    task_max_retries=3,
    task_default_retry_delay=60,   # 1分钟后重试
)

# 任务定义
@app.task(bind=True, max_retries=3)
def process_document(self, doc_id):
    try:
        # 1. PDF 解析
        parse_pdf(doc_id)
        
        # 2. OCR 识别
        ocr_images(doc_id)
        
        # 3. 分块
        chunks = chunk_document(doc_id)
        
        # 4. Embedding
        embeddings = generate_embeddings(chunks)
        
        # 5. 索引
        index_to_es(doc_id, chunks, embeddings)
        
        # 更新状态
        update_status(doc_id, "success")
        
    except Exception as exc:
        # 失败重试
        raise self.retry(exc=exc, countdown=60)
```

### 4.3 任务状态流转

```
pending (创建)
    ↓
processing (开始处理)
    ↓
├── success (完成)
└── fail (失败，可重试)
    ↓
retrying (重试中)
    ↓
├── success
└── fail (最终失败)
```

---

## 五、RAGFlow 企业级特性

### 5.1 支持的特性

| 特性 | 支持情况 | 实现方式 |
|------|---------|---------|
| **多用户** |  支持 | JWT + 用户隔离 |
| **权限控制** |  支持 | 角色权限 |
| **文档队列** |  支持 | Redis + Celery |
| **任务追踪** |  支持 | MySQL 状态表 |
| **并发控制** |  支持 | Worker 进程池 |
| **失败重试** |  支持 | Celery 自动重试 |
| **Chat 限流** | ⚠️ 需配置 | 依赖外部 API 限制 |

### 5.2 与 DB-GPT 的企业级对比

| 维度 | DB-GPT | RAGFlow |
|------|--------|---------|
| **多用户支持** |  完整 |  完整 |
| **Chat 限流** |  内置 | ⚠️ 依赖外部 |
| **模型管理** |  自托管 |  外部 API |
| **文档处理** |  支持 |  更强 |
| **任务队列** |  可选 |  必需 |
| **可观测性** | ⚠️ 需集成 | ⚠️ 需集成 |

---

## 六、选择建议

### 6.1 选择 RAGFlow 的场景

 **适合使用 RAGFlow**：

| 场景 | 原因 |
|------|------|
| 企业文档库建设 | DeepDoc 解析能力强 |
| 复杂文档格式 | 支持 PDF/Word/Excel/PPT |
| 已有 LLM API | 不想自建模型服务 |
| 文档处理为主 | 对话只是辅助功能 |

### 6.2 选择 DB-GPT 的场景

 **适合使用 DB-GPT**：

| 场景 | 原因 |
|------|------|
| 自建模型服务 | 需要托管私有模型 |
| 多模型调度 | 需要动态切换模型 |
| 对话为主 | Chat 是核心功能 |
| 复杂 Agent | AWEL 编排能力强 |

### 6.3 混合架构建议

**最佳实践：RAGFlow + DB-GPT 结合**

```
文档入库：RAGFlow（异步处理，DeepDoc 解析）
    ↓
知识库存储：Elasticsearch
    ↓
实时对话：DB-GPT（同步推理，多模型调度）
    ↓
检索增强：调用 RAGFlow 的 ES 索引
```

---

## 七、总结

### 7.1 核心观点

1. **RAGFlow Chat 不用队列**
   - 和 DB-GPT 一样，同步调用
   - 实时对话不适合队列

2. **RAGFlow 文档处理用队列**
   - 这是核心功能
   - Redis + Celery 实现
   - 支持重试、进度追踪

3. **两者都是企业级架构**
   - 都支持多用户
   - 都支持水平扩展
   - 都符合行业最佳实践

### 7.2 关键差异

```
┌─────────────────────────────────────────────────────────────┐
│                      架构差异总结                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   DB-GPT                    RAGFlow                          │
│   ────────                  ───────                          │
│   模型服务为核心            文档处理为核心                    │
│   自托管 GPU Worker         调用外部 LLM API                  │
│   Chat + 知识库             文档 + Chat                      │
│   适合：对话系统            适合：文档平台                    │
│                                                              │
│   共同点：Chat 都不用队列，都是同步调用                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 附录

### 相关图表

| 图表 | 说明 |
|------|------|
| `ragflow-chat-architecture.svg` | RAGFlow Chat 架构 |
| `ragflow-vs-dbgpt-chat-comparison.svg` | Chat 架构对比 |
| `ragflow-document-queue-deep-dive.svg` | 文档处理队列深度分析 |

### 参考文档

- [DB-GPT-Chat多用户与企业级实践分析](DB-GPT-Chat多用户与企业级实践分析.md)
- [DB-GPT-vs-RAGFlow-分布式架构深度分析](DB-GPT-vs-RAGFlow-分布式架构深度分析.md)

---

*文档更新时间: 2026-02-06*
