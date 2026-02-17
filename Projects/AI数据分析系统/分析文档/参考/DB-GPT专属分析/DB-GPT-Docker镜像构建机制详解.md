---
source: https://github.com/eosphoros-ai/DB-GPT/tree/main/docker
---

# DB-GPT Docker 镜像构建机制详解

DB-GPT 提供了多个官方镜像，针对不同的部署场景进行了优化。本文档深入解析这些镜像的构建原理和实现机制。

---

## 官方镜像概览

| 镜像名称 | 适用场景 | 基础镜像 | 特点 |
|---------|---------|---------|------|
| `eosphorosai/dbgpt` | 本地模型部署（GPU） | nvidia/cuda:12.4.0-devel-ubuntu22.04 | 包含 CUDA 支持、本地模型推理 |
| `eosphorosai/dbgpt-openai` | 代理模型部署（CPU） | ubuntu:22.04 | 纯 CPU、代理模式、轻量级 |
| `eosphorosai/dbgpt-allinone` | 一体化部署 | eosphorosai/dbgpt + MySQL | 内置 MySQL、开箱即用 |

---

## 核心构建机制

### 1. 单 Dockerfile 多模式构建

DB-GPT 使用**单一 Dockerfile** 配合**构建参数**实现多镜像构建，核心技巧是 `EXTRAS` 参数控制依赖安装。

```dockerfile
# docker/base/Dockerfile
ARG BASE_IMAGE="nvidia/cuda:12.4.0-devel-ubuntu22.04"
ARG EXTRAS="base,proxy_openai,rag,storage_chromadb,cuda121,hf,quant_bnb,dbgpts"

FROM ${BASE_IMAGE} as builder

# 根据 EXTRAS 安装不同依赖
RUN extras=$(echo $EXTRAS | tr ',' '\n' | while read extra; do 
    echo "--extra $extra"; 
done | tr '\n' ' ') && \
    uv sync --frozen --all-packages --no-dev $extras
```

### 2. 构建脚本的模式切换

`docker/base/build_image.sh` 是构建的核心脚本，通过 `--install-mode` 参数切换不同模式：

```bash
# 模式定义
DEFAULT_PROXY_EXTRAS="base,proxy_openai,rag,graph_rag,storage_chromadb,dbgpts,..."
DEFAULT_CUDA_EXTRAS="${DEFAULT_PROXY_EXTRAS},cuda121,hf,quant_bnb,flash_attn,quant_awq"

# 不同模式的配置
 case "$DB_GPT_INSTALL_MODE" in
    default)
        BASE_IMAGE="$CUDA_BASE_IMAGE"
        EXTRAS="$DEFAULT_CUDA_EXTRAS"
        ;;
    openai)
        BASE_IMAGE="$CPU_BASE_IMAGE"          # 使用 CPU 镜像
        EXTRAS="$DEFAULT_PROXY_EXTRAS"        # 去掉 CUDA 依赖
        ;;
    vllm)
        BASE_IMAGE="$CUDA_BASE_IMAGE"
        EXTRAS="$DEFAULT_CUDA_EXTRAS,vllm"    # 添加 vLLM
        ;;
esac
```

---

## 各镜像详细解析

### 镜像 1：eosphorosai/dbgpt（GPU 本地模型）

**构建命令**：

```bash
./docker/base/build_image.sh --install-mode default
```

**配置参数**：

| 参数 | 值 | 说明 |
|------|-----|------|
| BASE_IMAGE | nvidia/cuda:12.4.0-devel-ubuntu22.04 | CUDA 开发镜像 |
| EXTRAS | base,proxy_openai,...,cuda121,hf,quant_bnb,flash_attn,quant_awq | 完整依赖 |

**关键依赖解释**：

```
base                 # 核心功能
proxy_openai         # OpenAI API 代理
rag                  # RAG 功能
graph_rag            # 图 RAG
storage_chromadb     # ChromaDB 向量存储
cuda121              # CUDA 12.1 支持
hf                   # HuggingFace 库
quant_bnb            # BitsAndBytes 量化
flash_attn           # Flash Attention
quant_awq            # AWQ 量化
dbgpts               # DB-GPT 插件系统
```

**适用场景**：
- 本地 GPU 部署 LLM（如 Llama、Qwen 等）
- 需要 CUDA 加速的推理
- 支持多种量化方案（BNB、AWQ、GGUF 等）

---

### 镜像 2：eosphorosai/dbgpt-openai（CPU 代理模式）

**构建命令**：

```bash
./docker/base/build_image.sh --install-mode openai
```

**配置参数**：

| 参数 | 值 | 说明 |
|------|-----|------|
| BASE_IMAGE | ubuntu:22.04 | 纯 CPU 基础镜像 |
| EXTRAS | base,proxy_openai,rag,graph_rag,storage_chromadb,dbgpts,... | 去掉 CUDA 依赖 |

**与 dbgpt 镜像的区别**：

```diff
# 基础镜像
- BASE_IMAGE=nvidia/cuda:12.4.0-devel-ubuntu22.04
+ BASE_IMAGE=ubuntu:22.04

# 依赖
- EXTRAS=... ,cuda121,hf,quant_bnb,flash_attn,quant_awq
+ EXTRAS=...  (无 CUDA 相关依赖)
```

**适用场景**：
- 纯 CPU 环境
- 使用 OpenAI、Claude 等云端 API
- 轻量级部署，镜像更小

---

### 镜像 3：eosphorosai/dbgpt-allinone（一体化部署）

**构建命令**：

```bash
./docker/allinone/build_image.sh
```

**Dockerfile 结构**：

```dockerfile
# docker/allinone/Dockerfile
ARG BASE_IMAGE="eosphorosai/dbgpt:latest"

FROM ${BASE_IMAGE}

# 安装 MySQL
RUN apt-get install -y mysql-server

# 配置 MySQL
RUN sed -i 's/bind-address = 127.0.0.1/bind-address = 0.0.0.0/g' \
    /etc/mysql/mysql.conf.d/mysqld.cnf

# 初始化脚本
COPY docker/allinone/allinone-entrypoint.sh /usr/local/bin/

ENTRYPOINT ["/usr/local/bin/allinone-entrypoint.sh"]
```

**启动脚本** (`allinone-entrypoint.sh`)：

```bash
#!/bin/bash

# 1. 启动 MySQL
service mysql start

# 2. 执行初始化 SQL
for file in /docker-entrypoint-initdb.d/*.sql
do
    mysql -u root -p${MYSQL_ROOT_PASSWORD} < "$file"
done

# 3. 启动 DB-GPT
python3 dbgpt/app/dbgpt_server.py
```

**构建逻辑**：

```
eosphorosai/dbgpt (基础镜像)
    ↓ 继承并添加 MySQL
    ↓ 安装 mysql-server
    ↓ 配置远程访问
    ↓ 初始化 dbgpt.sql
eosphorosai/dbgpt-allinone
```

---

## EXTRAS 依赖管理系统

DB-GPT 使用 Python 的 `extras` 机制管理可选依赖，定义在 `pyproject.toml`：

```toml
[project.optional-dependencies]
base = ["fastapi", "uvicorn", ...]
proxy_openai = ["openai", "tiktoken"]
rag = ["langchain", "chromadb", ...]
cuda121 = ["torch", "torchvision", "torchaudio"]
hf = ["transformers", "accelerate", ...]
quant_bnb = ["bitsandbytes"]
flash_attn = ["flash-attn"]
quant_awq = ["autoawq"]
vllm = ["vllm"]
llama_cpp = ["llama-cpp-python"]
```

构建时通过 `EXTRAS` 参数选择安装：

```bash
# 安装基础 + RAG
uv sync --extra base --extra rag

# 安装 GPU 完整版
uv sync --extra base --extra cuda121 --extra hf --extra quant_bnb
```

---

## 构建流程详解

### 完整的镜像构建流程

```
┌─────────────────────────────────────────────────────────────┐
│                     构建流程                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 选择模式                                                  │
│     ├── default  → eosphorosai/dbgpt                        │
│     ├── openai   → eosphorosai/dbgpt-openai                 │
│     ├── vllm     → eosphorosai/dbgpt-vllm                   │
│     ├── llama-cpp→ eosphorosai/dbgpt-llama-cpp              │
│     └── full     → eosphorosai/dbgpt-full                   │
│                                                             │
│  2. 确定基础镜像                                              │
│     ├── GPU 模式: nvidia/cuda:12.4.0-devel-ubuntu22.04     │
│     └── CPU 模式: ubuntu:22.04                              │
│                                                             │
│  3. 计算 EXTRAS                                              │
│     ├── 基础依赖: base, rag, storage_chromadb              │
│     ├── 代理依赖: proxy_openai, proxy_anthropic, ...       │
│     └── GPU 依赖: cuda121, hf, quant_bnb, ... (可选)        │
│                                                             │
│  4. Docker Build                                             │
│     ├── Stage 1: builder (安装依赖)                          │
│     └── Stage 2: runtime (复制 venv)                         │
│                                                             │
│  5. 生成镜像                                                  │
│     └── eosphorosai/dbgpt[-{mode}]                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Dockerfile 多阶段构建

```dockerfile
# Stage 1: Builder
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04 as builder
WORKDIR /app

# 安装 Python、uv 等
RUN apt-get install python3.11 python3-pip ...
RUN pipx install uv

# 创建虚拟环境
RUN python3.11 -m venv /app/.venv

# 根据 EXTRAS 安装依赖
COPY pyproject.toml uv.lock ./
COPY packages /app/packages
RUN uv sync --frozen --all-packages --no-dev $extras

# Stage 2: Runtime
FROM nvidia/cuda:12.4.0-devel-ubuntu22.04

# 仅复制虚拟环境（不复制源码）
COPY --from=builder /app/.venv /opt/.uv.venv
COPY . .

# 修复 shebang
RUN sed -i "s|/app/.venv|/opt/.uv.venv|g" ...

ENV PATH="/opt/.uv.venv/bin:$PATH"
CMD ["dbgpt", "start", "webserver", "--config", ...]
```

---

## 多模式支持的实现技巧

### 技巧 1：构建参数控制

```dockerfile
ARG BASE_IMAGE="nvidia/cuda:12.4.0-devel-ubuntu22.04"
ARG EXTRAS="base,proxy_openai,rag,..."

FROM ${BASE_IMAGE}
```

### 技巧 2：Shell 脚本模式切换

```bash
case "$INSTALL_MODE" in
    openai)
        BASE_IMAGE="ubuntu:22.04"
        EXTRAS="base,proxy_openai,..."
        ;;
    default)
        BASE_IMAGE="nvidia/cuda:12.4.0-devel-ubuntu22.04"
        EXTRAS="base,...,cuda121,..."
        ;;
esac
```

### 技巧 3：动态依赖生成

```bash
# 将逗号分隔的 EXTRAS 转换为 uv 参数
extras=$(echo $EXTRAS | tr ',' '\n' | while read extra; do 
    echo "--extra $extra"; 
done | tr '\n' ' ')

# 执行: uv sync --extra base --extra proxy_openai ...
uv sync --frozen --all-packages --no-dev $extras
```

### 技巧 4：镜像名称自动后缀

```bash
# openai 模式自动添加后缀
if [ "$DB_GPT_INSTALL_MODE" != "default" ]; then
    IMAGE_NAME="$IMAGE_NAME-$DB_GPT_INSTALL_MODE"
fi

# 结果: eosphorosai/dbgpt-openai
```

---

## 实际构建示例

### 构建 GPU 版本（默认）

```bash
./docker/base/build_image.sh \
    --image-name eosphorosai/dbgpt \
    --install-mode default
```

### 构建 CPU 版本（OpenAI 代理）

```bash
./docker/base/build_image.sh \
    --image-name eosphorosai/dbgpt-openai \
    --install-mode openai
```

### 构建 vLLM 版本

```bash
./docker/base/build_image.sh \
    --image-name eosphorosai/dbgpt-vllm \
    --install-mode vllm
```

### 构建一体化版本

```bash
# 先确保基础镜像存在
docker pull eosphorosai/dbgpt:latest

# 构建 allinone
./docker/allinone/build_image.sh
```

---

## 最佳实践与借鉴

### 值得借鉴的设计

1. **单一 Dockerfile 多模式**
   - 维护成本低
   - 通过参数控制差异

2. **EXTRAS 依赖管理**
   - 精细化的依赖分组
   - 按需安装，减少镜像体积

3. **多阶段构建**
   - 构建环境和运行环境分离
   - 仅复制虚拟环境，不复制构建工具

4. **自动化命名**
   - 根据模式自动添加镜像后缀
   - 避免手动命名错误

### 自定义构建建议

如果需要添加自定义依赖：

```bash
./docker/base/build_image.sh \
    --install-mode openai \
    --add-extras "custom_package,another_package"
```

如果需要自定义基础镜像：

```bash
./docker/base/build_image.sh \
    --base-image nvidia/cuda:11.8.0-devel-ubuntu20.04 \
    --install-mode default
```

---

## 关联文档

- [[开源项目目录结构分析]]: 项目整体结构
- [[DB-GPT架构分析]]: 系统架构设计
- [[DB-GPT-AWEL实现机制详解]]: 工作流编排
