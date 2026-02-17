# DB-GPT 部署运维架构分析

**分析日期**: 2026-02-06  
**版本**: 基于 DB-GPT 最新主分支代码分析  
**分析者**: AI Agent

---

## 1. 部署方式总览

### 1.1 支持的部署模式

| 部署模式 | 适用场景 | 复杂度 | 文档支持 |
|---------|---------|--------|---------|
| **单机 Docker** | 开发测试、快速体验 | ⭐ | 完整 |
| **Docker Compose** | 小型生产环境 | ⭐⭐ | 完整 |
| **分布式集群** | 中大型生产环境 | ⭐⭐⭐ | 完整 |
| **高可用集群 (HA)** | 企业级生产环境 | ⭐⭐⭐⭐ | 完整 |
| **Kubernetes** | 云原生大规模部署 | ⭐⭐⭐⭐⭐ |  暂不支持 |

### 1.2 官方镜像列表

| 镜像名称 | 用途 | 基础镜像 |
|---------|------|---------|
| `eosphorosai/dbgpt` | 本地模型部署（GPU） | nvidia/cuda:12.4.0-devel-ubuntu22.04 |
| `eosphorosai/dbgpt-openai` | 代理模型部署（CPU） | eosphorosai/dbgpt |
| `eosphorosai/dbgpt-allinone` | 一体化部署（内置MySQL） | eosphorosai/dbgpt + MySQL |

### 1.3 快速启动命令

```bash
# 1. 代理模型快速启动（无需GPU）
docker run -it --rm -e SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY} \
  -p 5670:5670 --name dbgpt eosphorosai/dbgpt-openai

# 2. 本地模型启动（需要GPU）
docker run --ipc host --gpus all -it --rm \
  -p 5670:5670 \
  -v ./models:/app/models \
  -v ./dbgpt-config.toml:/app/configs/dbgpt-config.toml \
  eosphorosai/dbgpt \
  dbgpt start webserver --config /app/configs/dbgpt-config.toml

# 3. Docker Compose 启动
docker compose up -d
```

---

## 2. 依赖服务分析

### 2.1 核心依赖矩阵

| 服务类型 | 可选方案 | 默认方案 | 用途 |
|---------|---------|---------|------|
| **元数据库** | SQLite / MySQL | SQLite | 存储应用元数据、会话、配置 |
| **向量数据库** | ChromaDB / Milvus / OceanBase / Weaviate | ChromaDB | 存储文档向量、知识库索引 |
| **图数据库** | TuGraph / Neo4j | TuGraph | GraphRAG 知识图谱存储 |
| **缓存** | Redis（可选） | 内存缓存 | 会话缓存、结果缓存 |
| **消息队列** | 内置 / RabbitMQ / Kafka | 内置 | 异步任务处理 |
| **对象存储** | S3 / OSS / COS / MinIO | 本地存储 | 文件存储、模型存储 |

### 2.2 Docker Compose 默认依赖栈

```yaml
# docker-compose.yml 服务依赖关系
services:
  db:                    # MySQL 元数据库
    image: mysql/mysql-server
    ports: [3306:3306]
    
  webserver:             # DB-GPT 主服务
    image: eosphorosai/dbgpt-openai:latest
    depends_on: [db]     # 依赖 MySQL
    ports: [5670:5670]
```

### 2.3 向量存储配置对比

| 向量数据库 | 配置示例 | 适用场景 |
|-----------|---------|---------|
| **ChromaDB** | 默认本地持久化 | 小规模、单节点 |
| **Milvus** | `type = "milvus"` | 大规模、分布式 |
| **OceanBase** | `type = "oceanbase"` | 企业级、已有 OB 环境 |

```toml
# ChromaDB 配置（默认）
[rag.storage.vector]
type = "chroma"
persist_path = "pilot/data"

# Milvus 配置
[rag.storage.vector]
type = "milvus"
host = "localhost"
port = 19530
```

---

## 3. 容器化支持

### 3.1 Dockerfile 分层架构

```
┌─────────────────────────────────────────┐
│  eosphorosai/dbgpt-openai:latest       │  代理模型层 (+pip install dashscope)
├─────────────────────────────────────────┤
│  eosphorosai/dbgpt:latest               │  基础运行时层 (+项目代码)
├─────────────────────────────────────────┤
│  builder 阶段                            │  构建阶段 (+uv sync 安装依赖)
├─────────────────────────────────────────┤
│  nvidia/cuda:12.4.0-devel-ubuntu22.04  │  基础镜像层 (CUDA 支持)
└─────────────────────────────────────────┘
```

### 3.2 All-in-One 镜像

All-in-One 镜像将 MySQL 和 DB-GPT 打包在一起，适合快速体验：

```dockerfile
# docker/allinone/Dockerfile 关键步骤
FROM eosphorosai/dbgpt:latest

# 安装 MySQL
RUN apt-get install -y mysql-server

# 复制初始化脚本
COPY assets/schema/dbgpt.sql /docker-entrypoint-initdb.d/
COPY docker/examples/sqls/*_mysql.sql /docker-entrypoint-initdb.d/

# 自定义启动脚本
COPY docker/allinone/allinone-entrypoint.sh /usr/local/bin/
ENTRYPOINT ["/usr/local/bin/allinone-entrypoint.sh"]
```

### 3.3 数据持久化策略

| 数据类型 | 容器路径 | 建议挂载 | 说明 |
|---------|---------|---------|------|
| 应用数据 | `/app/pilot/data` |  必须 | RAG 知识库、向量索引 |
| 消息数据 | `/app/pilot/message` |  必须 | 会话历史、聊天记录 |
| 模型文件 | `/app/models` | ⚠️ 可选 | 本地模型存储 |
| 配置文件 | `/app/configs` | ⚠️ 可选 | 自定义配置 |
| SQLite | `/app/pilot/meta_data` |  可选 | 若使用 SQLite |

---

## 4. K8s 支持情况

### 4.1 当前状态

| 特性 | 支持状态 | 备注 |
|-----|---------|------|
| **Helm Chart** |  暂无 | 官方文档表示未来会提供 |
| **K8s YAML** |  暂无 | 需自行编写 |
| **Operator** |  暂无 | 无计划 |
| **HPA 支持** | ⚠️ 需配置 | Worker 层支持水平扩展 |
| **Service Mesh** | ⚠️ 需配置 | Istio/Linkerd 兼容 |

### 4.2 高可用部署方案

DB-GPT 支持通过 **StorageModelRegistry** 实现 Controller 的高可用：

```yaml
# 概念性 K8s 部署架构（需自行实现）

# Controller StatefulSet - 多副本
# 使用 MySQL 作为共享存储后端
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: dbgpt-controller
spec:
  replicas: 2  # 双活 Controller
  template:
    spec:
      containers:
      - name: controller
        command: ["dbgpt", "start", "controller", 
                   "--registry_type", "database",
                   "--registry_db_type", "mysql",
                   "--registry_db_host", "mysql-service"]

# Worker Deployment - 可水平扩展
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dbgpt-llm-worker
spec:
  replicas: 3  # 根据负载调整
```

### 4.3 Controller HA 原理

```
┌──────────────────────────────────────────────────────────┐
│                    MySQL (共享存储)                       │
│  ┌────────────────────────────────────────────────────┐  │
│  │  dbgpt_cluster_registry_instance 表                │  │
│  │  - model_name, host, port, weight                  │  │
│  │  - healthy, enabled, last_heartbeat                │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Controller-1 │  │ Controller-2 │  │ Controller-N │
│  :8000       │  │  :8000       │  │  :8000       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                  │                  │
       └──────────────────┴──────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐   ┌──────────────┐  ┌──────────────┐
│ LLM Worker   │   │ Embedding    │  │ Web Server   │
│              │   │ Worker       │  │              │
└──────────────┘   └──────────────┘  └──────────────┘
```

---

## 5. 配置管理

### 5.1 配置文件结构

```
configs/
├── dbgpt-app-config.example.toml      # 基础配置示例
├── dbgpt-proxy-openai.toml            # OpenAI 代理配置
├── dbgpt-proxy-siliconflow.toml       # 硅基流动配置
├── dbgpt-proxy-deepseek.toml          # DeepSeek 配置
├── dbgpt-proxy-ollama.toml            # Ollama 本地配置
├── dbgpt-local-glm.toml               # 本地 GLM 模型配置
├── dbgpt-local-qwen.toml              # 本地 Qwen 模型配置
├── dbgpt-graphrag.toml                # GraphRAG 配置
├── dbgpt-cloud-storage.example.toml   # 云存储配置
└── dbgpt-bm25-rag.toml                # BM25 检索配置
```

### 5.2 TOML 配置分层

```toml
# 核心配置分层结构
[system]                          # 系统级配置
language = "${env:DBGPT_LANG:-zh}"
log_level = "INFO"
encrypt_key = "your_secret_key"

[service.web]                     # Web 服务配置
host = "0.0.0.0"
port = 5670

[service.web.database]            # 元数据库配置
type = "sqlite"                   # 或 mysql
path = "pilot/meta_data/dbgpt.db"

[service.model.controller]        # 模型控制器配置
host = "0.0.0.0"
port = 8000

[service.model.controller.registry.database]  # Controller HA 配置
type = "mysql"                    # StorageModelRegistry

[service.model.worker]            # 模型 Worker 配置
host = "0.0.0.0"
port = 8001
worker_type = "llm"
controller_addr = "${env:CONTROLLER_ADDR}"

[service.model.api]               # API 服务配置
host = "0.0.0.0"
port = 8100

[models]                          # 模型配置
[[models.llms]]                   # LLM 模型列表
name = "gpt-4o"
provider = "proxy/openai"
api_key = "${env:OPENAI_API_KEY}"

[[models.embeddings]]             # Embedding 模型列表
name = "text-embedding-3-small"
provider = "proxy/openai"

[[models.rerankers]]              # Reranker 模型列表
name = "bge-reranker-v2-m3"
provider = "proxy/siliconflow"

[rag.storage.vector]              # 向量存储配置
type = "chroma"
persist_path = "pilot/data"

[rag.storage.graph]               # 图存储配置（GraphRAG）
type = "tugraph"
host = "127.0.0.1"
port = 7687
```

### 5.3 环境变量映射

| 环境变量 | 配置项 | 说明 |
|---------|--------|------|
| `DBGPT_LANG` | `system.language` | 界面语言 |
| `SILICONFLOW_API_KEY` | `models.llms[].api_key` | API 密钥 |
| `OPENAI_API_BASE` | `models.llms[].api_base` | API 端点 |
| `LLM_MODEL_NAME` | `models.llms[].name` | 默认模型 |
| `MYSQL_HOST` | `service.web.database.host` | 数据库主机 |
| `CONTROLLER_ADDR` | `service.web.controller_addr` | 控制器地址 |
| `TRACER_TO_OPEN_TELEMETRY` | 观测配置 | 启用链路追踪 |

### 5.4 配置优先级

```
高优先级 ──────────────────────────────> 低优先级

命令行参数 > 环境变量 > 配置文件 > 默认配置

示例：
  --port 8080        (最高)
  DBGPT_PORT=8080    (次之)
  config.toml 中 port = 8080
  默认 5670          (最低)
```

---

## 6. 监控与日志

### 6.1 可观测性支持

| 功能 | 支持状态 | 配置方式 |
|-----|---------|---------|
| **OpenTelemetry 链路追踪** |  | `TRACER_TO_OPEN_TELEMETRY=True` |
| **Jaeger 集成** |  | `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` |
| **Prometheus 指标** | ⚠️ 需配置 | 通过 OpenTelemetry Collector |
| **结构化日志** |  | JSON / 文本格式 |
| **日志级别控制** |  | `DBGPT_LOG_LEVEL` |

### 6.2 Jaeger 集成示例

```yaml
# docker/compose_examples/observability/docker-compose.yml
services:
  jaeger:
    image: jaegertracing/all-in-one:1.58
    ports:
      - "16686:16686"   # Jaeger UI
      - "4317:4317"     # OTLP gRPC
      - "4318:4318"     # OTLP HTTP
    environment:
      - SPAN_STORAGE_TYPE=badger

  webserver:
    image: eosphorosai/dbgpt-openai:latest
    environment:
      - TRACER_TO_OPEN_TELEMETRY=True
      - OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://jaeger:4317
      - DBGPT_LOG_LEVEL=DEBUG
```

### 6.3 日志配置

```toml
[system]
log_level = "INFO"      # DEBUG / INFO / WARNING / ERROR

[log]
level = "INFO"
format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
```

---

## 7. 多租户支持分析

### 7.1 当前状态

| 特性 | 支持状态 | 说明 |
|-----|---------|------|
| **用户隔离** |  基础支持 | 基于用户ID的数据隔离 |
| **系统编码 (sys_code)** |  | 多系统/租户标识 |
| **资源配额** |  | 暂无细粒度配额控制 |
| **租户级配置** | ⚠️ 部分支持 | 通过 sys_code 区分 |
| **权限控制** | ⚠️ 基础支持 | 角色基础权限 |

### 7.2 数据隔离机制

```python
# 关键数据表字段
- user_name:    用户名
- sys_code:     系统/租户编码
- team_mode:    团队模式
```

### 7.3 集群注册表的多租户支持

```sql
-- dbgpt_cluster_registry_instance 表
CREATE TABLE `dbgpt_cluster_registry_instance` (
  `model_name` varchar(128) NOT NULL,
  `user_name` varchar(128) DEFAULT NULL,    -- 用户隔离
  `sys_code` varchar(128) DEFAULT NULL,     -- 租户隔离
  ...
  UNIQUE KEY `uk_model_instance` (`model_name`, `host`, `port`, `sys_code`)
);
```

---

## 8. 与 RAGFlow 部署对比

### 8.1 部署方式对比

| 特性 | DB-GPT | RAGFlow |
|-----|--------|---------|
| **Docker 单机** |  |  |
| **Docker Compose** |  |  |
| **Kubernetes Helm** |  |  |
| **K8s Operator** |  |  |
| **All-in-One 镜像** |  |  |
| **GPU 支持** |  CUDA 12.4 |  CUDA 12.4 |
| **CPU 模式** |  |  |

### 8.2 依赖服务对比

| 服务 | DB-GPT | RAGFlow |
|-----|--------|---------|
| **元数据库** | SQLite / MySQL | MySQL 8.0+ |
| **向量数据库** | ChromaDB / Milvus / OceanBase | Elasticsearch |
| **图数据库** | TuGraph / Neo4j |  |
| **缓存** | 内存 / Redis | Redis |
| **文档解析** | 内置 | 内置 (DeepDoc) |
| **任务队列** | 内置 | Redis + Celery |

### 8.3 配置管理对比

| 特性 | DB-GPT | RAGFlow |
|-----|--------|---------|
| **配置格式** | TOML | YAML (template) |
| **环境变量** | 完整支持 | 完整支持 (.env) |
| **配置分层** | 5层结构 | 扁平结构 |
| **热更新** |  |  |
| **配置验证** | 启动时 | 启动时 |

### 8.4 可观测性对比

| 特性 | DB-GPT | RAGFlow |
|-----|--------|---------|
| **OpenTelemetry** |  内置 |  |
| **Jaeger 链路追踪** |  示例完整 |  |
| **Prometheus 指标** | ⚠️ 间接支持 |  直接支持 |
| **日志级别控制** |  |  |
| **健康检查端点** | ⚠️ |  |

### 8.5 高可用方案对比

| 特性 | DB-GPT | RAGFlow |
|-----|--------|---------|
| **Controller HA** |  StorageModelRegistry | N/A |
| **Worker 水平扩展** |  | ⚠️ |
| **数据库 HA** | 依赖外部 MySQL | 依赖外部 MySQL |
| **向量库 HA** | 依赖外部 Milvus | 依赖 ES 集群 |
| **K8s 原生 HA** |  |  Helm 支持 |

### 8.6 部署复杂度对比

```
┌─────────────────────────────────────────────────────────────────┐
│                     部署复杂度曲线                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  复杂度                                                          │
│    ▲                                                            │
│    │                               ┌────────── RAGFlow (K8s)    │
│ 高 │                         ┌────┘                              │
│    │    ┌──── DB-GPT (HA)    │                                  │
│    │────┘                    │                                  │
│    │                         └────┐                              │
│ 中 │                               └────────── RAGFlow (Compose) │
│    │    ┌──── DB-GPT (Compose)                                   │
│    │────┘                                                       │
│    │                                                             │
│ 低 │    ┌──── DB-GPT (Docker) ──── RAGFlow (Docker)             │
│    │────┘                                                       │
│    └────────────────────────────────────────────────────────────▶│
│         单机        小集群       大集群      K8s                  │
│                         部署规模                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. 生产部署建议

### 9.1 小型部署（< 100 用户）

```yaml
# 推荐架构：Docker Compose + SQLite
docker-compose.yml:
  - webserver (1 实例)
  - 使用 SQLite 元数据库
  - ChromaDB 本地持久化
```

### 9.2 中型部署（100-1000 用户）

```yaml
# 推荐架构：Docker Compose + MySQL
docker-compose.yml:
  - webserver (1-2 实例)
  - MySQL 元数据库
  - Milvus 向量库
  - Redis 缓存
```

### 9.3 大型部署（> 1000 用户）

```yaml
# 推荐架构：分布式集群
# 需自行编写 K8s YAML 或等待官方 Helm Chart

components:
  - Controller: 2+ 实例 (HA)
  - LLM Worker: 根据 GPU 资源扩展
  - Embedding Worker: 2+ 实例
  - Web Server: 2+ 实例 (负载均衡后)
  - MySQL: 主从集群
  - Milvus: 分布式集群
  - Redis: 哨兵/集群模式
```

### 9.4 关键配置 checklist

- [ ] 修改默认 `encrypt_key`
- [ ] 配置外部 MySQL（生产环境）
- [ ] 配置外部向量库（Milvus 推荐）
- [ ] 启用链路追踪（可选）
- [ ] 配置日志轮转
- [ ] 配置数据备份策略
- [ ] 配置健康检查端点
- [ ] 配置资源限制（CPU/内存）

---

## 10. 总结

### 10.1 DB-GPT 部署优势

1. **灵活的部署模式**：支持从单机到高可用集群的平滑演进
2. **完善的 Docker 支持**：官方镜像丰富，文档详尽
3. **Controller HA 机制**：基于数据库的共享注册表实现高可用
4. **配置分层清晰**：TOML 配置结构合理，环境变量支持完善
5. **OpenTelemetry 原生支持**：可观测性方案现代化

### 10.2 部署限制

1. **无原生 K8s 支持**：缺少 Helm Chart 和 Operator
2. **多租户能力有限**：仅基础隔离，无细粒度配额控制
3. **监控体系待完善**：Prometheus 指标需额外配置
4. **自动扩缩容**：需依赖外部 K8s HPA 或自定义脚本

### 10.3 与 RAGFlow 选择建议

| 场景 | 推荐方案 |
|-----|---------|
| 需要快速 K8s 部署 | RAGFlow (Helm Chart 完整) |
| 需要 GraphRAG 能力 | DB-GPT (原生支持 TuGraph) |
| 需要 OpenTelemetry 追踪 | DB-GPT (内置支持) |
| 需要文档解析深度优化 | RAGFlow (DeepDoc) |
| 多模型管理场景 | DB-GPT (SMMF 架构更成熟) |

---

**参考文档**：
- [DB-GPT Docker 部署文档](https://docs.dbgpt.cn/docs/installation/docker)
- [DB-GPT HA 集群部署](https://docs.dbgpt.cn/docs/installation/model_service/cluster_ha)
- [RAGFlow Helm 部署](https://github.com/infiniflow/ragflow/tree/main/helm)
