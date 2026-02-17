# smolagents 生产环境部署指南

> **项目**: AI数据分析系统  
> **文档编号**: 29  
> **编写日期**: 2026-02-06  
> **适用范围**: smolagents 生产环境部署  

---

## 一、环境准备

### 1.1 Python版本要求

smolagents 要求 Python 3.9 或更高版本。生产环境推荐使用 Python 3.11，原因如下：

- 性能比 3.9 提升约 15-20%
- 更好的错误提示和调试体验
- 长期支持版本，稳定性好

验证 Python 版本：

```bash
python --version
```

### 1.2 虚拟环境管理

生产环境必须使用虚拟环境隔离依赖。三种主流方案对比如下：

| 方案 | 启动速度 | 依赖锁定 | 适用场景 |
|------|----------|----------|----------|
| venv | 快 | 需手动维护 | 简单项目、快速部署 |
| conda | 中 | 支持 | 需要管理非Python依赖 |
| poetry | 快 | 自动锁定 | 复杂项目、精确版本控制 |

#### 使用 venv

```bash
# 创建虚拟环境
python -m venv .venv

# 激活环境
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 使用 poetry

```bash
# 安装 poetry
pip install poetry

# 创建项目
poetry init

# 添加依赖
poetry add smolagents fastapi uvicorn gunicorn

# 安装所有依赖
poetry install

# 激活环境
poetry shell
```

### 1.3 依赖安装策略

#### requirements.txt 方式

适用于简单项目或 CI/CD 流水线：

```text
# requirements.txt
smolagents>=1.0.0,<2.0.0
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
gunicorn>=21.0.0
pydantic>=2.0.0
python-dotenv>=1.0.0
structlog>=23.0.0
prometheus-client>=0.17.0
```

生成锁定文件确保版本一致：

```bash
pip freeze > requirements-lock.txt
```

#### pyproject.toml 方式

推荐用于现代 Python 项目：

```toml
# pyproject.toml
[project]
name = "smolagents-service"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "smolagents>=1.0.0,<2.0.0",
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "gunicorn>=21.0.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "structlog>=23.0.0",
    "prometheus-client>=0.17.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

### 1.4 开发环境与生产环境差异

| 维度 | 开发环境 | 生产环境 |
|------|----------|----------|
| 执行器 | LocalPythonExecutor | E2BExecutor 或 DockerExecutor |
| 日志级别 | DEBUG | INFO 或 WARNING |
| 错误提示 | 详细堆栈 | 简化信息 |
| 自动重载 | 开启 | 关闭 |
| 并发数 | 1-2 | 根据负载配置 |
| 监控 | 可选 | 必须 |

环境变量区分配置：

```python
# config.py
import os
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"

ENV = Environment(os.getenv("ENV", "dev"))

# 根据环境调整配置
if ENV == Environment.PRODUCTION:
    EXECUTOR_TYPE = "e2b"
    LOG_LEVEL = "INFO"
    RELOAD = False
    WORKERS = int(os.getenv("WORKERS", "4"))
else:
    EXECUTOR_TYPE = "local"
    LOG_LEVEL = "DEBUG"
    RELOAD = True
    WORKERS = 1
```

---

## 二、Docker部署

### 2.1 多阶段构建 Dockerfile

多阶段构建可显著减少最终镜像大小。以下配置将镜像从约 500MB 压缩到约 200MB：

```dockerfile
# Dockerfile
# 阶段一：构建依赖
FROM python:3.11-slim as builder

WORKDIR /app

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 阶段二：运行环境
FROM python:3.11-slim

WORKDIR /app

# 安装运行时必要的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 创建非root用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 复制应用代码
COPY --chown=appuser:appuser . .

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]
```

### 2.2 依赖缓存优化

利用 Docker 层缓存机制，将不常变动的依赖安装放在前面：

```dockerfile
# 优化后的 Dockerfile 片段
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 代码变更频繁，放在后面
COPY . .
```

构建时启用 BuildKit 提升构建速度：

```bash
# Linux/Mac
DOCKER_BUILDKIT=1 docker build -t smolagents-service .

# Windows PowerShell
$env:DOCKER_BUILDKIT=1; docker build -t smolagents-service .
```

### 2.3 docker-compose配置

#### 基础配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV=prod
      - WORKERS=4
      - LOG_LEVEL=INFO
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

#### 生产环境完整配置

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    image: smolagents-service:${VERSION:-latest}
    container_name: smolagents-app
    ports:
      - "127.0.0.1:8000:8000"  # 仅绑定本地，通过 nginx 反向代理
    environment:
      - ENV=prod
      - WORKERS=4
      - TIMEOUT=120
      - MAX_REQUESTS=10000
    env_file:
      - .env.production
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    networks:
      - smolagents-network

  nginx:
    image: nginx:alpine
    container_name: smolagents-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - smolagents-network

  prometheus:
    image: prom/prometheus:latest
    container_name: smolagents-prometheus
    ports:
      - "127.0.0.1:9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'
    networks:
      - smolagents-network

volumes:
  prometheus-data:

networks:
  smolagents-network:
    driver: bridge
```

---

## 三、安全配置

### 3.1 环境变量管理

使用 python-dotenv 加载环境变量，区分不同环境的配置文件：

```python
# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# 根据环境加载对应配置
env = os.getenv("ENV", "dev")
env_file = Path(f".env.{env}")
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

class Settings:
    # 应用配置
    APP_NAME = os.getenv("APP_NAME", "smolagents-service")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # 服务器配置
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    WORKERS = int(os.getenv("WORKERS", "4"))
    
    # 安全配置
    SECRET_KEY = os.getenv("SECRET_KEY")
    API_KEY = os.getenv("API_KEY")
    
    # LLM API配置
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    HF_API_TOKEN = os.getenv("HF_API_TOKEN")
    
    # E2B配置
    E2B_API_KEY = os.getenv("E2B_API_KEY")
    
    # 执行器配置
    EXECUTOR_TYPE = os.getenv("EXECUTOR_TYPE", "local")
    EXECUTOR_TIMEOUT = int(os.getenv("EXECUTOR_TIMEOUT", "30"))
    
    # 日志配置
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "json")

settings = Settings()
```

环境变量文件示例：

```bash
# .env.production
ENV=prod
DEBUG=false

# 安全密钥 - 生产环境必须使用强随机字符串
SECRET_KEY=your-super-secret-key-here-min-32-chars
API_KEY=your-api-key-for-client-auth

# LLM API密钥
OPENAI_API_KEY=sk-...
HF_API_TOKEN=hf_...

# E2B沙箱密钥
E2B_API_KEY=e2b_...

# 执行器配置
EXECUTOR_TYPE=e2b
EXECUTOR_TIMEOUT=60

# 日志
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 3.2 API密钥管理

生产环境推荐使用专门的密钥管理服务：

```python
# 方案一：使用 AWS Secrets Manager
import boto3
from botocore.exceptions import ClientError

def get_secret(secret_name, region="us-east-1"):
    client = boto3.client('secretsmanager', region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
    except ClientError as e:
        raise e

# 方案二：使用 HashiCorp Vault
import hvac

def get_vault_secret(path):
    client = hvac.Client(url=os.getenv('VAULT_ADDR'))
    client.token = os.getenv('VAULT_TOKEN')
    secret = client.secrets.kv.v2.read_secret_version(path=path)
    return secret['data']['data']

# 方案三：使用 Azure Key Vault
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def get_azure_secret(vault_url, secret_name):
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)
    secret = client.get_secret(secret_name)
    return secret.value
```

### 3.3 密钥轮换机制

实现自动密钥轮换：

```python
# utils/key_rotation.py
import os
import time
from datetime import datetime, timedelta

class KeyRotationManager:
    def __init__(self, rotation_days=90):
        self.rotation_days = rotation_days
        self.key_cache = {}
        self.last_rotation = datetime.now()
    
    def get_key(self, key_name):
        # 检查是否需要轮换
        if self._should_rotate():
            self._perform_rotation()
        
        # 从缓存或环境变量获取
        if key_name not in self.key_cache:
            self.key_cache[key_name] = os.getenv(key_name)
        
        return self.key_cache[key_name]
    
    def _should_rotate(self):
        return datetime.now() - self.last_rotation > timedelta(days=self.rotation_days)
    
    def _perform_rotation(self):
        # 实现密钥轮换逻辑
        # 这里可以调用 AWS Secrets Manager 或 Vault 的轮换 API
        self.last_rotation = datetime.now()
        # 清空缓存，强制重新获取
        self.key_cache.clear()

key_manager = KeyRotationManager()
```

### 3.4 敏感信息日志脱敏

使用 structlog 实现自动脱敏：

```python
# utils/logging.py
import re
import structlog

def mask_sensitive_data(logger, method_name, event_dict):
    """自动脱敏敏感信息"""
    sensitive_patterns = [
        (r'"api_key":\s*"[^"]*"', '"api_key": "***"'),
        (r'"token":\s*"[^"]*"', '"token": "***"'),
        (r'"password":\s*"[^"]*"', '"password": "***"'),
        (r'sk-[a-zA-Z0-9]{48}', 'sk-***'),
        (r'hf_[a-zA-Z0-9]{34}', 'hf_***'),
        (r'e2b_[a-zA-Z0-9]{32}', 'e2b_***'),
    ]
    
    for key, value in event_dict.items():
        if isinstance(value, str):
            for pattern, replacement in sensitive_patterns:
                value = re.sub(pattern, replacement, value)
            event_dict[key] = value
    
    return event_dict

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        mask_sensitive_data,  # 脱敏处理器
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if os.getenv("LOG_FORMAT") == "json" 
        else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

---

## 四、监控配置

### 4.1 结构化日志

```python
# utils/logger.py
import sys
import structlog
import logging
from pythonjsonlogger import jsonlogger

def setup_logging(log_level="INFO", json_format=True):
    """配置结构化日志"""
    
    # 配置标准库 logging
    log_handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    log_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.handlers = [log_handler]
    
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if json_format 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# 使用示例
logger = structlog.get_logger()
logger.info("agent_execution_started", task_id="123", executor_type="e2b")
logger.error("execution_failed", task_id="123", error="timeout", duration=30.5)
```

### 4.2 Prometheus 指标监控

```python
# utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time

# 定义指标
AGENT_EXECUTIONS_TOTAL = Counter(
    'smolagents_executions_total',
    'Total number of agent executions',
    ['status', 'executor_type']
)

AGENT_EXECUTION_DURATION = Histogram(
    'smolagents_execution_duration_seconds',
    'Agent execution duration in seconds',
    ['executor_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

AGENT_ACTIVE_REQUESTS = Gauge(
    'smolagents_active_requests',
    'Number of active agent requests'
)

CODE_EXECUTIONS_TOTAL = Counter(
    'smolagents_code_executions_total',
    'Total number of code executions',
    ['status', 'language']
)

def track_execution(executor_type="local"):
    """执行追踪装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            AGENT_ACTIVE_REQUESTS.inc()
            
            try:
                result = await func(*args, **kwargs)
                AGENT_EXECUTIONS_TOTAL.labels(
                    status="success", 
                    executor_type=executor_type
                ).inc()
                return result
            except Exception as e:
                AGENT_EXECUTIONS_TOTAL.labels(
                    status="error",
                    executor_type=executor_type
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                AGENT_EXECUTION_DURATION.labels(
                    executor_type=executor_type
                ).observe(duration)
                AGENT_ACTIVE_REQUESTS.dec()
        return wrapper
    return decorator

# FastAPI 集成
from fastapi import FastAPI, Response

app = FastAPI()

@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

Prometheus 配置文件：

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'smolagents-service'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s
```

### 4.3 健康检查端点

```python
# routes/health.py
from fastapi import APIRouter, status
from pydantic import BaseModel
from typing import Dict, Any
import time

router = APIRouter()

# 启动时间
START_TIME = time.time()

class HealthResponse(BaseModel):
    status: str
    version: str
    uptime: float
    checks: Dict[str, Any]

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """基础健康检查"""
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime=time.time() - START_TIME,
        checks={}
    )

@router.get("/ready")
async def readiness_check():
    """就绪检查 - 检查依赖服务"""
    checks = {
        "executor": await check_executor(),
        "llm_api": await check_llm_api(),
    }
    
    all_healthy = all(c["status"] == "ok" for c in checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }

@router.get("/live")
async def liveness_check():
    """存活检查 - 简单返回200"""
    return {"status": "alive"}

async def check_executor():
    """检查执行器状态"""
    try:
        # 执行一个简单的测试代码
        from smolagents import LocalPythonExecutor
        executor = LocalPythonExecutor(additional_authorized_imports=[])
        executor("1 + 1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def check_llm_api():
    """检查 LLM API 可用性"""
    import httpx
    try:
        # 这里根据实际使用的 API 进行检查
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                timeout=5.0
            )
        return {"status": "ok" if response.status_code == 200 else "error"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

### 4.4 告警规则配置

```yaml
# monitoring/alert_rules.yml
groups:
  - name: smolagents_alerts
    rules:
      # 高错误率告警
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(smolagents_executions_total{status="error"}[5m])) 
            / 
            sum(rate(smolagents_executions_total[5m]))
          ) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高错误率 detected"
          description: "错误率超过 10%"

      # 执行超时告警
      - alert: ExecutionTimeout
        expr: |
          histogram_quantile(0.95, 
            sum(rate(smolagents_execution_duration_seconds_bucket[5m])) by (le)
          ) > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "执行超时"
          description: "95% 的执行时间超过 30 秒"

      # 服务不可用告警
      - alert: ServiceDown
        expr: up{job="smolagents-service"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "服务不可用"
          description: "smolagents-service 已停止"

      # 内存使用告警
      - alert: HighMemoryUsage
        expr: |
          container_memory_usage_bytes{name="smolagents-app"} 
          / container_spec_memory_limit_bytes{name="smolagents-app"} > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率高"
          description: "内存使用率超过 85%"
```

---

## 五、性能调优

### 5.1 Gunicorn 配置

```python
# gunicorn.conf.py
import os
import multiprocessing

# 服务器配置
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Worker 配置
# 公式: workers = 2 * CPU核心数 + 1
workers = int(os.getenv('WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# 连接配置
worker_connections = 1000
backlog = 2048

# 超时配置
timeout = int(os.getenv('TIMEOUT', '120'))
keepalive = 5
graceful_timeout = 30

# 工作模式
preload_app = True  # 预加载应用，减少内存占用

# 请求限制
max_requests = int(os.getenv('MAX_REQUESTS', '10000'))
max_requests_jitter = 1000  # 随机抖动，避免同时重启

# 日志配置
accesslog = "-"  # 输出到 stdout
errorlog = "-"
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程名称
proc_name = "smolagents-service"

# 安全配置
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# 服务器钩子
def on_starting(server):
    """服务器启动时"""
    pass

def on_reload(server):
    """配置重载时"""
    pass

def when_ready(server):
    """Worker 准备好后"""
    pass

def worker_int(worker):
    """Worker 收到 SIGINT 时"""
    pass

def on_exit(server):
    """服务器退出时"""
    pass
```

### 5.2 超时配置

```python
# config/timeouts.py
from dataclasses import dataclass

@dataclass
class TimeoutConfig:
    # HTTP 请求超时
    request_timeout: int = 120
    
    # Agent 执行超时
    agent_execution_timeout: int = 60
    
    # 代码执行超时
    code_execution_timeout: int = 30
    
    # LLM API 调用超时
    llm_api_timeout: int = 60
    
    # 数据库连接超时
    db_connection_timeout: int = 10
    
    # 缓存操作超时
    cache_timeout: int = 5

# 生产环境配置
PROD_TIMEOUTS = TimeoutConfig(
    request_timeout=120,
    agent_execution_timeout=60,
    code_execution_timeout=30,
    llm_api_timeout=60,
)

# 开发环境配置
DEV_TIMEOUTS = TimeoutConfig(
    request_timeout=300,
    agent_execution_timeout=120,
    code_execution_timeout=60,
    llm_api_timeout=120,
)
```

在 FastAPI 中应用超时：

```python
# main.py
from fastapi import FastAPI, HTTPException
import asyncio
from config.timeouts import PROD_TIMEOUTS

app = FastAPI()

@app.post("/execute")
async def execute_agent(request: ExecuteRequest):
    try:
        # 使用 asyncio.wait_for 实现超时
        result = await asyncio.wait_for(
            run_agent(request),
            timeout=PROD_TIMEOUTS.agent_execution_timeout
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Execution timeout"
        )

async def run_agent(request):
    # Agent 执行逻辑
    pass
```

### 5.3 资源限制

Docker 资源限制配置：

```yaml
# docker-compose.resources.yml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
      nproc:
        soft: 65536
        hard: 65536
```

Kubernetes 资源限制：

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smolagents-service
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: app
        image: smolagents-service:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

### 5.4 连接池配置

```python
# utils/connection_pool.py
import httpx
from contextlib import asynccontextmanager

class ConnectionPool:
    def __init__(self):
        # HTTP 连接池
        self.http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0
            ),
            timeout=httpx.Timeout(
                connect=5.0,
                read=60.0,
                write=10.0,
                pool=5.0
            )
        )
    
    async def close(self):
        await self.http_client.aclose()

# 全局连接池实例
pool = ConnectionPool()

# 在 FastAPI 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    yield
    # 关闭时
    await pool.close()

app = FastAPI(lifespan=lifespan)
```

---

## 六、高可用设计

### 6.1 Nginx 负载均衡

```nginx
# nginx/nginx.conf
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    '$request_time $upstream_response_time';

    access_log /var/log/nginx/access.log main;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript;

    # 上游服务器组
    upstream smolagents_backend {
        least_conn;  # 最少连接负载均衡
        
        server app:8000 weight=5 max_fails=3 fail_timeout=30s;
        # 如果有多实例，添加更多 server
        # server app2:8000 weight=5 max_fails=3 fail_timeout=30s;
        
        keepalive 32;
    }

    # 限流配置
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    server {
        listen 80;
        server_name _;

        # 健康检查
        location /nginx-health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        location / {
            # 限流
            limit_req zone=api_limit burst=20 nodelay;
            limit_conn conn_limit 10;

            proxy_pass http://smolagents_backend;
            proxy_http_version 1.1;
            
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header Connection "";
            
            proxy_connect_timeout 30s;
            proxy_send_timeout 120s;
            proxy_read_timeout 120s;
            
            proxy_buffering on;
            proxy_buffer_size 4k;
            proxy_buffers 8 4k;
        }

        # Prometheus 指标直接透传
        location /metrics {
            proxy_pass http://smolagents_backend/metrics;
            proxy_http_version 1.1;
        }
    }
}
```

### 6.2 故障转移策略

```python
# utils/failover.py
import asyncio
import random
from typing import List, Callable, Any
from dataclasses import dataclass

@dataclass
class Endpoint:
    url: str
    weight: int = 1
    healthy: bool = True
    fail_count: int = 0
    last_check: float = 0

class FailoverManager:
    def __init__(self, endpoints: List[Endpoint], max_failures: int = 3):
        self.endpoints = endpoints
        self.max_failures = max_failures
        self.circuit_breaker = {}
    
    async def execute_with_failover(
        self, 
        operation: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """带故障转移的执行"""
        healthy_endpoints = [
            e for e in self.endpoints 
            if e.healthy and self.circuit_breaker.get(e.url, False) is not True
        ]
        
        if not healthy_endpoints:
            raise Exception("No healthy endpoints available")
        
        # 按权重随机选择
        endpoint = random.choices(
            healthy_endpoints,
            weights=[e.weight for e in healthy_endpoints]
        )[0]
        
        try:
            result = await operation(endpoint, *args, **kwargs)
            # 重置失败计数
            endpoint.fail_count = 0
            return result
        except Exception as e:
            endpoint.fail_count += 1
            
            # 触发熔断
            if endpoint.fail_count >= self.max_failures:
                endpoint.healthy = False
                self.circuit_breaker[endpoint.url] = True
                
                # 异步恢复检查
                asyncio.create_task(self._recovery_check(endpoint))
            
            # 尝试下一个端点
            return await self.execute_with_failover(operation, *args, **kwargs)
    
    async def _recovery_check(self, endpoint: Endpoint):
        """检查服务是否恢复"""
        await asyncio.sleep(30)  # 30秒后检查
        
        try:
            # 健康检查请求
            # 如果恢复，重置状态
            endpoint.healthy = True
            endpoint.fail_count = 0
            self.circuit_breaker[endpoint.url] = False
        except:
            # 仍然不可用，继续熔断
            pass
```

### 6.3 会话保持

对于需要状态保持的场景：

```python
# utils/session.py
import redis
import json
import uuid
from typing import Optional, Dict, Any

class SessionManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.ttl = 3600  # 1小时过期
    
    def create_session(self, data: Dict[str, Any]) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())
        self.redis.setex(
            f"session:{session_id}",
            self.ttl,
            json.dumps(data)
        )
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话数据"""
        data = self.redis.get(f"session:{session_id}")
        if data:
            return json.loads(data)
        return None
    
    def update_session(self, session_id: str, data: Dict[str, Any]):
        """更新会话"""
        self.redis.setex(
            f"session:{session_id}",
            self.ttl,
            json.dumps(data)
        )
    
    def delete_session(self, session_id: str):
        """删除会话"""
        self.redis.delete(f"session:{session_id}")

# FastAPI 依赖注入
from fastapi import Request, HTTPException

async def get_session(request: Request):
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID required")
    
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    return session
```

### 6.4 滚动更新

Docker Compose 滚动更新：

```bash
#!/bin/bash
# scripts/rolling_update.sh

# 配置
SERVICE_NAME="smolagents-service"
NEW_IMAGE="smolagents-service:v2.0.0"

echo "Starting rolling update..."

# 获取当前实例数
SCALE=$(docker-compose ps -q app | wc -l)
echo "Current scale: $SCALE"

# 逐步更新每个实例
for i in $(seq 1 $SCALE); do
    echo "Updating instance $i..."
    
    # 创建新实例
    docker-compose up -d --no-deps --scale app=$((SCALE + 1)) --no-recreate app
    
    # 等待新实例健康
    sleep 10
    
    # 移除一个旧实例
    docker-compose up -d --no-deps --scale app=$SCALE --no-recreate app
    
    echo "Instance $i updated"
done

echo "Rolling update completed"
```

Kubernetes 滚动更新配置：

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smolagents-service
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # 最多多启动 1 个 Pod
      maxUnavailable: 0  # 不允许不可用
  template:
    spec:
      containers:
      - name: app
        image: smolagents-service:latest
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## 七、部署Checklist

### 7.1 环境检查

- [ ] Python 版本 >= 3.11
- [ ] 虚拟环境已创建并激活
- [ ] 所有依赖已安装并锁定版本
- [ ] 环境变量文件已配置
- [ ] 敏感信息未提交到版本控制

### 7.2 安全配置

- [ ] API 密钥已更换为生产环境密钥
- [ ] 密钥长度符合安全要求
- [ ] 密钥轮换机制已配置
- [ ] 日志脱敏规则已启用
- [ ] 生产环境禁用 DEBUG 模式

### 7.3 执行器配置

- [ ] 生产环境使用远程执行器：E2BExecutor 或 DockerExecutor
- [ ] LocalPythonExecutor 仅用于开发
- [ ] 执行超时时间已配置
- [ ] 代码导入白名单已审查
- [ ] 执行器资源限制已设置

### 7.4 监控配置

- [ ] 结构化日志已启用
- [ ] Prometheus 指标端点可访问
- [ ] 健康检查端点已实现
- [ ] 告警规则已配置
- [ ] 日志收集系统已集成

### 7.5 性能配置

- [ ] Gunicorn worker 数量已优化
- [ ] 超时配置已调整
- [ ] 连接池已配置
- [ ] 资源限制已设置
- [ ] 限流规则已启用

### 7.6 高可用配置

- [ ] Nginx 负载均衡已配置
- [ ] 故障转移策略已测试
- [ ] 健康检查机制已验证
- [ ] 滚动更新流程已准备
- [ ] 备份和恢复方案已确认

### 7.7 Docker 部署检查

- [ ] Dockerfile 使用多阶段构建
- [ ] 基础镜像使用 python:3.11-slim
- [ ] 镜像大小已优化到 200MB 以下
- [ ] 非 root 用户运行容器
- [ ] 健康检查已配置
- [ ] 资源限制已设置

### 7.8 部署前最终检查

```bash
# 运行部署前检查脚本
#!/bin/bash
# scripts/pre_deploy_check.sh

echo "=== Pre-deployment Check ==="

# 1. 检查环境变量
echo "Checking environment variables..."
required_vars=("SECRET_KEY" "API_KEY" "E2B_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: $var is not set"
        exit 1
    fi
done
echo "Environment variables OK"

# 2. 检查 Python 版本
echo "Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# 3. 检查依赖
echo "Checking dependencies..."
pip check

# 4. 运行测试
echo "Running tests..."
python -m pytest tests/ -q

# 5. 检查 Docker
echo "Checking Docker..."
docker --version
docker-compose --version

# 6. 构建测试镜像
echo "Building test image..."
docker build -t smolagents-service:test .

# 7. 检查镜像大小
echo "Checking image size..."
image_size=$(docker images smolagents-service:test --format "{{.Size}}")
echo "Image size: $image_size"

echo "=== All checks passed ==="
```

### 7.9 部署后验证

```bash
#!/bin/bash
# scripts/post_deploy_verify.sh

BASE_URL=${1:-"http://localhost:8000"}

echo "=== Post-deployment Verification ==="

# 1. 健康检查
echo "1. Testing health endpoint..."
curl -sf "${BASE_URL}/health" || exit 1
echo "Health check passed"

# 2. 就绪检查
echo "2. Testing ready endpoint..."
curl -sf "${BASE_URL}/ready" || exit 1
echo "Ready check passed"

# 3. 指标端点
echo "3. Testing metrics endpoint..."
curl -sf "${BASE_URL}/metrics" | grep "smolagents_executions_total" > /dev/null || exit 1
echo "Metrics endpoint OK"

# 4. 简单执行测试
echo "4. Testing agent execution..."
curl -sf -X POST "${BASE_URL}/execute" \
    -H "Content-Type: application/json" \
    -d '{"task": "Calculate 1 + 1"}' || exit 1
echo "Execution test passed"

# 5. 检查日志
echo "5. Checking logs for errors..."
docker-compose logs --tail=100 app | grep -i "error" && echo "WARNING: Errors found in logs"

echo "=== Deployment verified successfully ==="
```

---

## 八、参考文档

- smolagents 执行机制分析：[[02-smolagents-代码执行机制深度分析]]
- smolagents 执行器选型指南：[[18-smolagents-代码执行器选型指南]]
- FastAPI 官方文档：https://fastapi.tiangolo.com
- Gunicorn 配置指南：https://docs.gunicorn.org
- Prometheus 监控：https://prometheus.io/docs
- Docker 最佳实践：https://docs.docker.com/develop/dev-best-practices

---

*本文档基于 smolagents 源码分析生成，适用于 AI数据分析系统 项目生产环境部署*
