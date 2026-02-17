---
title: CAMEL 项目概述与架构设计
description: CAMEL 多智能体角色扮演框架的整体架构和设计理念分析
tags: [camel, multi-agent, architecture, role-playing]
created: 2026-02-06
updated: 2026-02-06
version: 0.2.85
---

# CAMEL 项目概述与架构设计

## 1. 项目概述

### 1.1 全称与含义

**CAMEL** 的全称为 **Communicative Agents for "Mind" Exploration of Large Language Model Society**，即"用于大型语言模型群体心智探索的通信智能体"。

该项目由 CAMEL-AI.org 社区维护，是一个开源的多智能体研究框架，专注于探索智能体规模的扩展规律。

### 1.2 项目定位

CAMEL 是一个**多智能体角色扮演框架**，其核心定位包括：

- **研究平台**：支持大规模智能体系统的行为研究，可模拟多达 100 万个智能体的交互
- **数据生成引擎**：自动生成高质量的合成数据，用于模型训练和评估
- **任务自动化系统**：通过多智能体协作完成复杂任务
- **世界模拟器**：构建虚拟社会环境，研究智能体群体行为

### 1.3 核心设计理念

#### 角色扮演驱动协作

CAMEL 的核心创新在于**通过角色扮演实现复杂任务协作**。每个智能体被赋予明确的角色定义，包括：

- 角色名称与身份背景
- 个性特征与行为模式
- 专业技能与知识领域
- 目标导向与动机

这种设计使得智能体之间能够通过自然语言对话进行有效协作，而非仅依赖结构化的工具调用。

#### 四大设计原则

根据官方文档，CAMEL 框架遵循以下设计原则：

| 原则 | 含义 | 实现方式 |
|------|------|----------|
| **可演进性** | 系统能够持续学习和进化 | 强化学习、监督学习、数据生成 |
| **可扩展性** | 支持大规模智能体系统 | 高效协调、通信和资源管理 |
| **状态保持** | 智能体维护状态化记忆 | 多步交互、历史上下文保持 |
| **代码即提示** | 代码和注释作为智能体的提示 | 清晰可读的代码设计 |

---

## 2. 整体架构

### 2.1 目录结构

```
camel/
├── camel/                      # 核心代码库
│   ├── agents/                 # 智能体实现
│   │   ├── base.py            # 智能体基类
│   │   ├── chat_agent.py      # 对话智能体
│   │   ├── critic_agent.py    # 批评智能体
│   │   ├── task_agent.py      # 任务智能体
│   │   └── tool_agents/       # 工具智能体
│   ├── societies/             # 多智能体社会
│   │   ├── role_playing.py    # 角色扮演社会
│   │   └── workforce/         # 工作力管理系统
│   ├── memories/              # 记忆系统
│   │   ├── base.py            # 记忆基类
│   │   ├── blocks/            # 记忆块实现
│   │   └── context_creators/  # 上下文创建器
│   ├── models/                # 模型抽象层
│   │   ├── base_model.py      # 模型基类
│   │   ├── model_factory.py   # 模型工厂
│   │   └── *_model.py         # 各平台模型实现
│   ├── toolkits/              # 工具集
│   │   ├── base.py            # 工具基类
│   │   ├── function_tool.py   # 函数工具
│   │   └── *_toolkit.py       # 各类工具实现
│   ├── prompts/               # 提示词模板
│   ├── storages/              # 存储层
│   │   ├── vectordb_storages/ # 向量数据库
│   │   ├── graph_storages/    # 图数据库
│   │   └── key_value_storages/# 键值存储
│   ├── messages/              # 消息系统
│   ├── types/                 # 类型定义
│   └── utils/                 # 工具函数
├── apps/                      # 应用程序
├── examples/                  # 示例代码
├── docs/                      # 文档
└── tests/                     # 测试
```

### 2.2 架构图

![[camel-整体架构图.svg]]

---

## 3. 核心模块职责

### 3.1 agents 模块

**职责**：定义和实现各类智能体

**核心类**：

| 类名 | 职责 |
|------|------|
| `BaseAgent` | 所有智能体的抽象基类，定义 `reset` 和 `step` 接口 |
| `ChatAgent` | 主要对话智能体，支持工具调用和记忆管理 |
| `CriticAgent` | 批评智能体，评估其他智能体的输出质量 |
| `TaskSpecifyAgent` | 任务细化智能体，将模糊任务转化为具体指令 |
| `TaskPlannerAgent` | 任务规划智能体，分解复杂任务为子任务 |

**设计特点**：

- 所有智能体继承自 `BaseAgent`，保证接口一致性
- `ChatAgent` 是核心实现，支持工具集成和记忆系统
- 支持异步操作和流式响应

### 3.2 societies 模块

**职责**：管理多智能体协作社会

**核心组件**：

| 组件 | 职责 |
|------|------|
| `RolePlaying` | 双智能体角色扮演场景，一个 assistant 一个 user |
| `Workforce` | 多智能体工作力管理系统，支持动态任务分配 |
| `Worker` | 工作力中的工作单元，可以是单个智能体或子工作力 |
| `TaskChannel` | 任务通道，用于智能体间任务传递 |

**角色扮演模式**：

```python
# RolePlaying 的核心交互模式
role_playing = RolePlaying(
    assistant_role_name="python程序员",
    user_role_name="股票交易员",
    task_prompt="开发一个股票交易机器人"
)
# Assistant 和 User 通过对话协作完成任务
```

### 3.3 memories 模块

**职责**：智能体的记忆存储和检索

**核心类**：

| 类名 | 职责 |
|------|------|
| `MemoryBlock` | 记忆块的抽象基类 |
| `ChatHistoryBlock` | 对话历史记忆块 |
| `VectorDBBlock` | 向量数据库记忆块 |
| `BaseContextCreator` | 上下文创建器基类 |
| `ScoreBasedContextCreator` | 基于评分的上下文创建器 |
| `MemoryRecord` | 记忆记录数据结构 |

**记忆类型**：

- **短期记忆**：对话历史，保存在 `ChatHistoryBlock`
- **长期记忆**：向量化知识，保存在 `VectorDBBlock`
- **上下文管理**：通过 `ContextCreator` 控制记忆注入提示词的方式

### 3.4 toolkits 模块

**职责**：为智能体提供外部工具能力

**核心类**：

| 类名 | 职责 |
|------|------|
| `BaseToolkit` | 工具集基类，所有工具集的父类 |
| `FunctionTool` | 函数工具包装器，将 Python 函数转为智能体可用工具 |
| `SearchToolkit` | 搜索工具集 |
| `CodeExecutionToolkit` | 代码执行工具集 |

**工具集成方式**：

```python
# 工具通过 FunctionTool 包装后注入智能体
search_tool = SearchToolkit().search_duckduckgo
agent = ChatAgent(
    model=model,
    tools=[search_tool]
)
```

**工具类别**：

- 搜索类：DuckDuckGo、Google、维基百科等
- 代码类：Python 执行、Docker 执行等
- 存储类：文件操作、数据库访问等
- 通信类：Slack、Discord、邮件等
- 专业类：GitHub、Notion、Google Drive 等

### 3.5 models 模块

**职责**：LLM 模型的抽象和统一管理

**核心类**：

| 类名 | 职责 |
|------|------|
| `BaseModelBackend` | 模型后端基类 |
| `ModelFactory` | 模型工厂，根据配置创建对应模型实例 |
| `ModelManager` | 模型管理器，支持多模型负载均衡 |

**支持的模型平台**：

- OpenAI
- Anthropic
- Google Gemini
- 本地模型：Ollama、vLLM、LM Studio
- 国内模型：DeepSeek、通义千问、Moonshot 等
- 其他：Azure OpenAI、Bedrock、Groq 等

**统一接口**：

所有模型通过统一的 `run` 方法调用，返回标准化的响应格式，上层模块无需关心底层模型差异。

### 3.6 prompts 模块

**职责**：提示词模板管理

**核心类**：

| 类名 | 职责 |
|------|------|
| `TextPrompt` | 文本提示词基类，继承自 `str` |
| `SystemMessageGenerator` | 系统消息生成器 |
| `TaskPrompt` | 任务提示词模板 |

**提示词设计**：

- 提示词即代码，支持类型安全
- 通过模板参数动态生成
- 支持角色特定的提示词定制

### 3.7 storages 模块

**职责**：数据持久化存储

**存储类型**：

| 类型 | 实现 | 用途 |
|------|------|------|
| 向量存储 | Qdrant、Milvus、FAISS、Chroma 等 | 语义检索、RAG |
| 图存储 | Neo4j、NebulaGraph | 知识图谱 |
| 键值存储 | Redis、JSON 文件、内存 | 配置、状态 |
| 对象存储 | S3、Azure Blob、GCS | 文件、大对象 |

---

## 4. 与 smolagents 的对比

| 维度 | CAMEL | smolagents |
|------|-------|-----------|
| **架构风格** | 角色扮演社会 | ReAct 循环 |
| **Agent 关系** | 平等协作，角色互补 | Manager-Managed 层级 |
| **通信方式** | 自然语言对话 | 结构化的工具调用 |
| **设计理念** | 模拟人类社会协作 | 代码优先的工具编排 |
| **复杂度** | 高，功能全面 | 低，轻量简洁 |
| **记忆系统** | 多层级记忆，支持向量检索 | 简单的对话历史 |
| **扩展性** | 支持百万级 Agent 模拟 | 适合单任务场景 |
| **适用场景** | 研究、复杂协作任务 | 快速原型、简单任务 |

**选择建议**：

- 需要研究多智能体行为、生成合成数据、构建复杂协作系统时选择 **CAMEL**
- 需要快速实现工具调用、轻量级 Agent 时选择 **smolagents**

---

## 5. 技术栈

### 5.1 核心依赖

```toml
# pyproject.toml 核心依赖
python = ">=3.10,<3.15"
openai = ">=1.86.0"
pydantic = ">=2.10.6"
httpx = ">=0.28.0"
websockets = ">=13.0"
tiktoken = ">=0.7.0"
```

### 5.2 支持的模型

| 提供商 | 模型类型 |
|--------|----------|
| OpenAI | GPT-4o、GPT-4、GPT-3.5 |
| Anthropic | Claude 系列 |
| Google | Gemini 系列 |
| 本地部署 | Ollama、vLLM、LM Studio |
| 国内平台 | DeepSeek、Moonshot、Qwen |
| 云服务 | Azure、AWS Bedrock、Groq |

### 5.3 存储支持

| 类型 | 支持的实现 |
|------|-----------|
| 向量数据库 | Qdrant、Milvus、FAISS、Chroma、Weaviate |
| 图数据库 | Neo4j、NebulaGraph |
| 关系数据库 | PostgreSQL + pgvector、TiDB |
| 缓存 | Redis、内存 |
| 对象存储 | S3、Azure Blob、GCS |

### 5.4 部署选项

- **本地运行**：直接 Python 脚本执行
- **Docker**：容器化部署
- **Kubernetes**：集群化部署
- **API 服务**：FastAPI 接口封装

---

## 6. 核心设计理念详解

### 6.1 角色扮演

CAMEL 的核心创新是**角色扮演机制**。每个智能体在创建时被赋予：

- **角色名称**：如"Python 程序员"、"产品经理"
- **角色描述**：详细的能力、性格、目标定义
- **系统消息**：通过 `SystemMessageGenerator` 生成

这种设计的优势：

1. **自然协作**：智能体像人类一样通过对话协作
2. **多样性**：不同角色带来不同视角和解决方案
3. **可解释性**：角色行为可预测、可理解

### 6.2 自然语言通信

与强调工具调用的框架不同，CAMEL 智能体之间主要通过**自然语言对话**协作：

```
User: 我们需要设计一个股票交易系统的架构
Assistant: 好的，我建议采用微服务架构，包含以下模块：数据获取、策略引擎、执行模块...
```

这种通信方式更接近人类协作模式，适合开放式、创造性的任务。

### 6.3 模块化设计

CAMEL 采用高度模块化设计：

- **可插拔的模型层**：任意切换底层 LLM
- **可扩展的工具集**：自定义工具易于集成
- **灵活的存储层**：根据需求选择存储方案
- **可定制的记忆策略**：不同任务使用不同的记忆管理方式

### 6.4 生产级特性

- **异步支持**：所有核心操作支持异步执行
- **流式响应**：支持流式输出，提升用户体验
- **错误处理**：完善的异常处理和重试机制
- **可观测性**：内置日志和监控支持
- **配置管理**：环境变量和配置文件支持

---

## 7. 模块依赖关系

![[camel-模块依赖图.svg]]

**依赖关系说明**：

1. **models** 是最底层，被所有上层模块依赖
2. **messages** 定义数据协议，贯穿整个系统
3. **agents** 依赖 models、memories、toolkits
4. **societies** 依赖 agents，实现多智能体协作
5. **storages** 为 memories 提供持久化支持
6. **prompts** 被 agents 和 societies 使用

---

## 8. 典型使用场景

### 8.1 数据生成

```python
from camel.datagen import SelfInstructGenerator

# 使用 Self-Instruct 生成指令数据
generator = SelfInstructGenerator(
    model=model,
    seed_instructions=seed_data
)
data = generator.generate(num_instructions=1000)
```

### 8.2 角色扮演对话

```python
from camel.societies import RolePlaying

society = RolePlaying(
    assistant_role_name="AI 研究员",
    user_role_name="数据工程师",
    task_prompt="设计一个推荐系统"
)
# 自动进行多轮对话协作
```

### 8.3 工作力管理

```python
from camel.societies.workforce import Workforce
from camel.agents import ChatAgent

workforce = Workforce(description="软件开发团队")
workforce.add_single_agent_worker("前端开发", agent=frontend_agent)
workforce.add_single_agent_worker("后端开发", agent=backend_agent)

result = workforce.process_task("开发一个电商平台")
```

---

## 9. 参考资源

- **官方文档**: https://docs.camel-ai.org
- **GitHub**: https://github.com/camel-ai/camel
- **论文**: CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society
- **PyPI**: https://pypi.org/project/camel-ai

---

## 10. 相关文档

- [[02-camel-核心模块详解]]
- [[03-camel-角色扮演机制]]
- [[04-camel-工具集成系统]]
- [[05-camel-记忆系统设计]]
- [[smolagents专属分析区/01-smolagents-项目概述与架构设计|smolagents 项目概述]]

---

*本文档基于 CAMEL v0.2.85 版本分析*
