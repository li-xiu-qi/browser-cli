# DB-GPT vs RAGFlow 分布式架构深度分析

> 本文档通过架构图对比分析 DB-GPT 和 RAGFlow 的分布式设计差异，帮助你理解两种模式的适用场景。

---

## 一、核心架构模式对比

### 1.1 DB-GPT: Controller-Worker 模式

![Controller-Worker 模式](assets/arch-pattern-controller-worker.svg)

**核心思想**: 服务注册与发现

```
用户请求 → WebServer → 查询 Controller → 获取 Worker 地址 → 直接调用 Worker
```

**关键组件**:

| 组件 | 职责 | 特点 |
|------|------|------|
| **Controller** | 注册中心 | 维护 Worker 地址表，健康检查（20s心跳） |
| **WebServer** | API 网关 | 无状态，每次请求重新查询 Worker |
| **Worker** | 模型推理 | GPU 服务，主动注册，直接暴露接口 |

**工作流程**:

1. **Worker 启动**: 向 Controller 注册自身信息（模型名、地址、心跳）
2. **请求处理**: WebServer 收到请求后查询 Controller 获取可用 Worker
3. **直接调用**: WebServer 直接与 Worker 通信，Controller 不参与数据传输
4. **故障检测**: Controller 定期检测 Worker 心跳，剔除失效节点

---

### 1.2 RAGFlow: Task Queue 模式

![Task Queue 模式](assets/arch-pattern-task-queue.svg)

**核心思想**: 异步任务队列

```
上传文档 → WebServer → 投递任务到 Redis → Executor 消费 → 异步处理 → 更新状态
```

**关键组件**:

| 组件 | 职责 | 特点 |
|------|------|------|
| **Redis** | 任务队列 | 消息缓冲，削峰填谷 |
| **WebServer** | 任务提交 | 只负责投递，不等待结果 |
| **Executor** | 任务执行 | CPU 进程，消费队列，更新进度 |

**工作流程**:

1. **任务投递**: WebServer 将文档处理任务序列化后推入 Redis 队列
2. **任务消费**: Executor 从队列拉取任务，执行 PDF 解析/分块/Embedding
3. **状态追踪**: 通过 MySQL 记录任务进度（pending → processing → success/fail）
4. **结果查询**: 用户轮询或 WebSocket 获取处理结果

---

### 1.3 模式对比总结

| 维度 | Controller-Worker (DB-GPT) | Task Queue (RAGFlow) |
|------|---------------------------|----------------------|
| **通信方式** | 同步 HTTP/gRPC 调用 | 异步消息队列 |
| **调用链路** | 点对点直连 | 队列中转 |
| **状态管理** | 无状态（每次重新发现） | 有状态（任务进度追踪） |
| **失败处理** | 调用方重试 | 队列自动重试 |
| **适用任务** | 模型推理（同步） | 文档处理（异步） |
| **扩展触发** | 并发请求增加 | 队列积压 |

> **注意**: DB-GPT 也有任务队列（用于知识库构建），但模型推理采用直接调用。详见 [DB-GPT-任务队列机制详解](DB-GPT-任务队列机制详解.md)。

---

## 二、Docker 部署架构对比

### 2.1 DB-GPT Docker 部署

![DB-GPT Docker 部署](assets/docker-deployment-dbgpt.svg)

**核心服务**:

```yaml
# docker-compose.yml 核心结构
services:
  controller:     # 注册中心（1个）
    command: dbgpt start controller
    ports: ["8000:8000"]
    
  webserver:      # API 层（可扩展）
    command: dbgpt start webserver --controller-addr http://controller:8000
    ports: ["5670:5670"]
    scale: 2      # 水平扩展
    
  worker:         # GPU 推理服务（重点扩展）
    command: dbgpt start worker --controller-addr http://controller:8000 --model-name qwen-72b
    deploy:
      resources:
        reservations:
          devices: [{driver: nvidia, count: 1}]
    # 启动多个同名 Worker 实现负载均衡
```

**部署特点**:

1. **Controller 单点**: 轻量级，只存储元数据，可快速重启
2. **Worker GPU 绑定**: 每个 Worker 独占 GPU，模型常驻显存
3. **网络发现**: 通过 Docker Network 或 K8s Service 发现彼此
4. **存储共享**: 模型文件通过 Volume 共享，避免重复下载

---

### 2.2 RAGFlow Docker 部署

![RAGFlow Docker 部署](assets/docker-deployment-ragflow.svg)

**核心服务**:

```yaml
# docker-compose.yml 核心结构
services:
  server:         # Web + API + 任务投递
    image: infiniflow/ragflow:latest
    ports: ["80:80", "9380:9380"]
    
  redis:          # 任务队列
    image: redis:alpine
    
  task-executor:  # 文档处理（重点扩展）
    command: celery -A tasks worker -Q rag_flow -l info
    scale: 3      # 水平扩展
    
  es:             # 文档索引
    image: elasticsearch:8.11.3
    
  mysql:          # 业务数据
    image: mysql:8.0
```

**部署特点**:

1. **Redis 中心枢纽**: 所有 Executor 连接同一 Redis 消费任务
2. **Executor 无差别**: 所有 Executor 相同，自动竞争消费
3. **存储分离**: ES 存索引，MySQL 存状态，Redis 存队列
4. **CPU 密集型**: Executor 不需要 GPU，主要消耗 CPU

---

## 三、横向扩展机制对比

### 3.1 扩展机制全景图

![横向扩展对比](assets/scaling-mechanism-comparison.svg)

### 3.2 DB-GPT 扩展详解

**扩展对象**: GPU Worker（模型推理服务）

**触发条件**:
- LLM 并发请求超过当前 Worker 处理能力
- GPU 利用率持续 100%
- 请求响应时间显著增加

**扩容方式**:

```bash
# 方式1: Docker Compose 扩容
docker-compose up --scale worker=3 -d

# 方式2: 手动启动新 Worker
docker run -d \
  --name dbgpt-worker-3 \
  --gpus all \
  -e CONTROLLER_ADDR=http://controller:8000 \
  -e MODEL_NAME=qwen-72b \
  -v model-cache:/app/models \
  eosphorosai/dbgpt:latest \
  dbgpt start worker
```

**负载均衡机制**:

```python
# Controller 内部逻辑
class ModelRegistry:
    def get_workers(self, model_name):
        workers = self.store.get(model_name, [])
        healthy = [w for w in workers if w.is_healthy()]
        return random.choice(healthy)  # 简单随机选择
```

**特点**:
- Worker 启动后**自动注册**到 Controller
- 同名 Worker 自动形成**负载均衡组**
- Controller 只返回地址，**不转发流量**
- Worker 故障后 120s（心跳超时）被剔除

---

### 3.3 RAGFlow 扩展详解

**扩展对象**: Task Executor（文档处理进程）

**触发条件**:
- Redis 队列任务积压（queue length > threshold）
- 文档处理延迟增加
- 业务高峰期保障

**扩容方式**:

```bash
# 方式1: Docker Compose 扩容
docker-compose up --scale task-executor=5 -d

# 方式2: K8s 扩容
kubectl scale deployment task-executor --replicas=5

# 方式3: Celery 动态扩容
celery -A tasks multi start worker2 worker3 -Q rag_flow
```

**负载均衡机制**:

```python
# Celery 内部逻辑
class CeleryWorker:
    def run(self):
        while True:
            task = redis.brpop('rag_flow_queue')  # 阻塞消费
            self.process(task)  # 处理任务
```

**特点**:
- Executor 启动后**自动连接** Redis
- 多个 Executor **竞争消费**队列
- Celery 内置公平调度，避免任务倾斜
- 失败任务自动重试（可配置重试次数）

---

## 四、请求处理流程对比

### 4.1 DB-GPT 请求流程（同步）

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client │────▶│ WebServer│────▶│ Controller│────▶│  Worker  │
└─────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                 │               │
     │                │ 1.查询模型地址   │               │
     │                │────────────────▶│               │
     │                │                 │               │
     │                │ 2.返回 Worker 列表              │
     │                │◀────────────────│               │
     │                │                 │               │
     │                │ 3.直接调用 Worker              │
     │                │───────────────────────────────▶│
     │                │                 │               │
     │                │ 4.返回推理结果   │               │
     │                │◀───────────────────────────────│
     │                │                 │               │
     │ 5.返回给用户   │                 │               │
     │◀───────────────│                 │               │
```

**耗时分布**:

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 网络传输 | 1-5ms | WebServer → Controller → Worker |
| 模型推理 | 100ms-10s | 取决于模型大小和输入长度 |
| 总计 | 100ms-10s+ | 主要是模型推理时间 |

---

### 4.2 RAGFlow 请求流程（异步）

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Client │────▶│ WebServer│────▶│  Redis   │────▶│ Executor │
└─────────┘     └──────────┘     └──────────┘     └──────────┘
     │                │                 │               │
     │ 1.上传文档      │                 │               │
     │────────────────▶│                 │               │
     │                │                 │               │
     │                │ 2.投递任务       │               │
     │                │────────────────▶│               │
     │                │                 │               │
     │ 3.立即返回任务ID                │               │
     │◀────────────────│                 │               │
     │                │                 │               │
     │ 4.轮询查询进度  │                 │               │
     │──────────────────────────────────────────────────▶│
     │                │                 │ 5.拉取任务     │
     │                │                 │◀──────────────│
     │                │                 │               │
     │                │                 │ 6.更新进度    │
     │◀──────────────────────────────────────────────────│
     │                │                 │               │
     │ 7.处理完成      │                 │               │
     │◀──────────────────────────────────────────────────│
```

**耗时分布**:

| 阶段 | 耗时 | 说明 |
|------|------|------|
| 任务投递 | <10ms | 立即返回任务ID |
| 队列等待 | 0-? | 取决于 Executor 数量 |
| 文档处理 | 10s-5min | PDF 解析、OCR、分块、Embedding |
| 总计 | 10s-5min+ | 异步处理，用户可离开 |

---

## 五、适用场景分析

### 5.1 选择 DB-GPT 的场景

 **适合使用 DB-GPT 的场景**:

| 场景 | 原因 |
|------|------|
| 大模型对话系统 | 需要低延迟（<3s）响应 |
| 实时问答 | 用户需要立即得到答案 |
| GPU 资源充足 | 需要水平扩展 GPU 推理能力 |
| 多模型调度 | 需要动态调度不同模型 |

 **不适合的场景**:

- 大量文档批处理（浪费 GPU 资源）
- 容忍高延迟的任务

---

### 5.2 选择 RAGFlow 的场景

 **适合使用 RAGFlow 的场景**:

| 场景 | 原因 |
|------|------|
| 企业文档库建设 | 大量文档需要异步处理 |
| 知识库检索 | 复杂检索流程需要多阶段处理 |
| 批量导入 | 用户可接受等待，后台慢慢处理 |
| CPU 资源充足 | 需要水平扩展文档处理能力 |

 **不适合的场景**:

- 实时对话（队列延迟不可控）
- GPU 推理为主的任务

---

## 六、混合架构建议

### 6.1 为什么需要混合？

在实际项目中，往往需要**两者结合**:

| 需求 | 解决方案 |
|------|----------|
| 文档入库 | RAGFlow 处理（异步队列） |
| 实时问答 | DB-GPT 处理（同步推理） |

### 6.2 架构示意

```
                    ┌──────────────────┐
                    │     用户请求      │
                    └────────┬─────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  上传文档     │ │  实时对话     │ │  知识检索     │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           ▼                ▼                ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   RAGFlow    │ │    DB-GPT    │ │    RAGFlow   │
    │  任务队列     │ │  Controller  │ │    ES检索    │
    │  异步处理     │ │  同步推理     │ │              │
    └──────────────┘ └──────────────┘ └──────────────┘
```

---

## 七、总结

### 核心差异一览

| 特性 | DB-GPT | RAGFlow |
|------|--------|---------|
| **设计目标** | 大模型推理服务化 | 文档处理管道化 |
| **分布式模式** | Controller-Worker 注册发现 | Task Queue + Executor 消费 |
| **扩容对象** | GPU Worker | CPU Executor |
| **任务类型** | 同步、短时、无状态 | 异步、长时、有状态 |
| **通信方式** | 直接 HTTP/gRPC 调用 | 队列中转 |
| **失败重试** | 客户端重试 | 队列自动重试 |

### 选择决策树

```
你的主要需求是什么？
    │
    ├── 实时对话/低延迟 LLM 推理 ──▶ DB-GPT
    │
    ├── 文档入库/批量处理 ────────▶ RAGFlow
    │
    └── 两者都需要 ───────────────▶ 混合架构
```

---

## 附录：图表清单

| 图表 | 文件名 | 说明 |
|------|--------|------|
| Controller-Worker 模式 | `arch-pattern-controller-worker.svg` | DB-GPT 服务注册发现架构 |
| Task Queue 模式 | `arch-pattern-task-queue.svg` | RAGFlow 异步任务队列架构 |
| DB-GPT Docker 部署 | `docker-deployment-dbgpt.svg` | DB-GPT 容器化部署结构 |
| RAGFlow Docker 部署 | `docker-deployment-ragflow.svg` | RAGFlow 容器化部署结构 |
| 横向扩展对比 | `scaling-mechanism-comparison.svg` | 扩容机制对比 |

---

*文档生成时间: 2026-02-06*  
*工具: Graphviz 14.1.2*
