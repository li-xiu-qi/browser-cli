# DB-GPT vs RAGFlow 分布式架构深度对比

## 一句话总结

- **DB-GPT**: 像微服务调用，直接调用 GPU Worker 做模型推理
- **RAGFlow**: 像任务队列，把文档处理任务异步分发给多个执行器

---

## 架构对比图

![架构对比](assets/dbgpt-vs-ragflow-architecture.svg)

---

## 核心差异

| 维度 | DB-GPT | RAGFlow |
|------|--------|---------|
| **分布式模式** | Controller-Worker 注册发现 | Task Queue + Executor 消费 |
| **横向扩展目标** | GPU 模型推理服务 | CPU 文档处理任务 |
| **任务类型** | 模型推理（LLM/Embedding） | 文档解析/分块/索引 |
| **调用方式** | 同步直接调用（HTTP/gRPC） | 异步队列投递（Celery） |
| **任务时长** | 短（100ms - 10s） | 长（秒级 - 分钟级） |
| **状态管理** | 无状态（每次重新查询） | 有状态（任务进度追踪） |
| **失败重试** | 由调用方重试（简单随机） | 由队列自动重试 |
| **负载均衡** | 随机选择健康 Worker | 轮询/公平分发 |

---

## DB-GPT 分布式详解

### 1. Docker 部署方式

```yaml
# docker-compose.yml 核心服务
services:
  # 1. Controller - 注册中心（单点）
  controller:
    image: eosphorosai/dbgpt:latest
    command: dbgpt start controller
    ports:
      - "8000:8000"
    
  # 2. WebServer - API/UI（可扩展）
  webserver:
    image: eosphorosai/dbgpt:latest
    command: dbgpt start webserver --controller-addr http://controller:8000
    ports:
      - "5670:5670"
    depends_on:
      - controller
    # 可横向扩展：docker-compose up --scale webserver=3
    
  # 3. Worker - 模型推理（GPU 节点，可扩展）
  worker-1:
    image: eosphorosai/dbgpt:latest
    command: dbgpt start worker --controller-addr http://controller:8000 --model-name qwen-72b
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    depends_on:
      - controller
      
  worker-2:
    image: eosphorosai/dbgpt:latest
    command: dbgpt start worker --controller-addr http://controller:8000 --model-name qwen-72b
    # 同类模型多个 Worker 实现负载均衡
    
  worker-embedding:
    image: eosphorosai/dbgpt:latest
    command: dbgpt start worker --controller-addr http://controller:8000 --model-name bge-large
    # 专门处理 Embedding
```

### 2. 分布式流程

```
用户请求 → WebServer → 查询 Controller → 获取 Worker 地址 → 直接调用 Worker
```

**关键特点**：
- **WebServer 无状态**：不保存任何连接信息，可以随时扩容/缩容
- **Worker 主动注册**：启动时向 Controller 注册，定时发送心跳（20s）
- **Controller 单点**：存储 Worker 地址表（内存+可选DB），轻量级
- **直接调用**：WebServer 拿到 Worker 地址后**直接调用**，不经过 Controller 转发

### 3. 横向扩展方式

| 扩展目标 | 场景 | 命令 |
|---------|------|------|
| WebServer | API 并发增加 | `docker-compose up --scale webserver=3` |
| LLM Worker | 大模型推理压力大 | 启动更多 GPU 节点，同名自动负载均衡 |
| Embedding Worker | RAG 检索变慢 | 独立扩展 Embedding 服务 |

**负载均衡策略**：
```python
# Controller 返回可用 Worker 列表
workers = controller.get_workers(model_name="qwen-72b")
# 随机选择一个（简单策略）
selected = random.choice(workers)
# WebServer 直接调用
response = requests.post(f"http://{selected.host}:{selected.port}/generate", ...)
```

---

## RAGFlow 分布式详解

### 1. Docker 部署方式

```yaml
# docker-compose.yml 核心服务
services:
  # 1. WebServer + Task Scheduler（一体）
  server:
    image: infiniflow/ragflow:latest
    command: bash -c "./entrypoint.sh"
    ports:
      - "80:80"
      - "9380:9380"
    
  # 2. Redis - 任务队列
  redis:
    image: redis:alpine
    
  # 3. Task Executor - 任务执行器（可扩展）
  task-executor-1:
    image: infiniflow/ragflow:latest
    command: bash -c "celery -A tasks worker -Q rag_flow -l info"
    depends_on:
      - redis
    # CPU 密集型
    
  task-executor-2:
    image: infiniflow/ragflow:latest
    command: bash -c "celery -A tasks worker -Q rag_flow -l info"
    # 可横向扩展多个执行器
    
  # 4. Elasticsearch - 文档存储
  es:
    image: elasticsearch:8.11.3
```

### 2. 分布式流程

```
上传文档 → WebServer → 提交任务到 Redis Queue → Executor 消费 → 异步处理 → 更新状态
```

**关键特点**：
- **任务队列解耦**：WebServer 只负责提交任务，不等待完成
- **Executor 消费**：多个 Executor 竞争消费队列中的任务
- **状态追踪**：通过数据库追踪文档处理进度（pending → processing → success）
- **异步执行**：文档处理可能需要分钟级时间，用户通过轮询获取进度

### 3. 横向扩展方式

| 扩展目标 | 场景 | 命令 |
|---------|------|------|
| Task Executor | 文档处理积压 | `docker-compose up --scale task-executor=5` |
| WebServer | API 并发增加 | 较少需要，因为文档处理是异步的 |

**负载均衡策略**：
```python
# Celery 自动分发
@app.task(bind=True)
def process_document(self, doc_id):
    # 任意空闲 Executor 执行
    pdf_parser.parse(file_path)
    chunker.split()
    embedder.embed()
    es.index()
    update_status(doc_id, "success")
```

---

## 关键问题解答

### Q1: 为什么 DB-GPT 不用任务队列？

**因为不需要**：
1. **任务时长不同**：LLM 推理是 100ms-10s，文档处理是秒级-分钟级
2. **同步需求**：用户对话需要立即得到响应，不能异步
3. **状态简单**：模型推理是无状态的，不需要追踪进度

### Q2: 为什么 RAGFlow 需要任务队列？

**因为必须**：
1. **任务耗时长**：PDF 解析、OCR、分块、Embedding 可能耗时几分钟
2. **异步解耦**：用户上传后就可以离开，后台慢慢处理
3. **可靠性**：队列保证任务不丢失，失败自动重试
4. **削峰填谷**：文档上传高峰时排队，平峰时处理

### Q3: 横向扩展的本质区别？

| 系统 | 扩展的是 | 解决的问题 |
|------|---------|-----------|
| **DB-GPT** | GPU 模型服务 | 大模型推理并发能力不足 |
| **RAGFlow** | CPU 任务执行器 | 文档处理吞吐量不足 |

### Q4: DB-GPT 的瓶颈在哪里？

1. **Controller 单点**：虽然轻量，但是单点故障风险
2. **Worker 状态**：Worker 故障时 Controller 需要 120s 才能感知（心跳超时）
3. **负载均衡简单**：随机选择，没有考虑 GPU 利用率

### Q5: RAGFlow 的瓶颈在哪里？

1. **ES 存储压力**：文档块数量庞大时查询变慢
2. **任务队列长度**：大量文档上传时队列积压
3. **重文档处理**：超大 PDF 可能长时间占用 Executor

---

## 总结

| 场景 | 推荐架构 |
|------|---------|
| 主要做**对话/问答**，需要 GPU 推理扩展 | DB-GPT 模式 |
| 主要做**文档管理**，需要批量处理 | RAGFlow 模式 |
| 两者都需要 | 结合使用（RAGFlow 处理文档，DB-GPT 做对话）|

两种架构没有优劣之分，**取决于主要 workload 的类型**：
- 计算密集型短时任务 → Controller-Worker 直接调用
- I/O 密集型长时任务 → 任务队列异步处理
