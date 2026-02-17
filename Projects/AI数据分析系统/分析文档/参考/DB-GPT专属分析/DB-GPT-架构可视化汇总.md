# DB-GPT 架构可视化汇总

> 本文档使用 Graphviz 可视化 DB-GPT 的系统架构，帮助快速理解系统设计与组件关系。

---

##  图表清单

| 图表 | 文件 | 用途 |
|------|------|------|
| 整体架构图 | `dbgpt-architecture-overview.svg` | 展示完整技术栈与分层架构 |
| Monorepo 结构 | `dbgpt-monorepo-structure.svg` | 包依赖关系与分层设计 |
| 部署模式 | `dbgpt-service-deployment.svg` | 开发/生产部署对比 |
| 请求流程 | `dbgpt-request-flow.svg` | LLM 请求完整处理链路 |
| 组件系统 | `dbgpt-component-system.svg` | SystemApp 组件管理机制 |
| **vs RAGFlow** | `dbgpt-vs-ragflow-architecture.svg` | 分布式架构模式对比 |
| **横向扩展对比** | `scaling-comparison.svg` | 扩容方式差异 |
| **任务队列** | `dbgpt-task-queue-mechanism.svg` | DB-GPT 队列使用场景 |
| **异步架构** | `dbgpt-async-tasks-architecture.svg` | 异步任务架构全景 |
| **多用户架构** | `dbgpt-multi-user-architecture.svg` | 多用户与队列使用 |
| **用户隔离** | `dbgpt-user-isolation.svg` | 用户数据隔离机制 |
| **Chat 并发** | `chat-concurrency-architecture.svg` | Chat 多用户并发处理 |
| **队列对比** | `queue-vs-direct-comparison.svg` | 队列 vs 直接调用对比 |
| **企业级实践** | `enterprise-best-practices.svg` | 企业级最佳实践 |
| **RAGFlow Chat** | `ragflow-chat-architecture.svg` | RAGFlow Chat 架构 |
| **RAGFlow 对比** | `ragflow-vs-dbgpt-chat-comparison.svg` | Chat 架构对比 |
| **RAGFlow 队列** | `ragflow-document-queue-deep-dive.svg` | 文档处理队列分析 |
| **流式架构** | `dbgpt-streaming-architecture.svg` | 流式输出架构 |
| **流式对比** | `streaming-comparison.svg` | 流式 vs 普通响应 |
| **决策树** | `when-to-use-queue-decision-tree.svg` | 何时使用队列 |
| **队列矩阵** | `queue-usage-matrix.svg` | 队列使用矩阵 |
| **架构模式** | `architecture-patterns-comparison.svg` | 架构模式对比 |
| **架构启发** | `lessons-learned.svg` | 架构设计启发 |
| **DB-GPT 流式** | `dbgpt-streaming-implementation.svg` | DB-GPT 流式实现 |
| **RAGFlow 流式** | `ragflow-streaming-implementation.svg` | RAGFlow 流式实现 |
| **流式对比** | `streaming-implementation-comparison.svg` | 流式实现对比 |
| **SSE 协议** | `sse-protocol-detail.svg` | SSE 协议详解 |
| **高并发架构** | `chat-high-concurrency-architecture.svg` | Chat 高并发架构 |
| **队列局限** | `queue-cant-help.svg` | 队列不能解决瓶颈 |
| **资源分布** | `resource-distribution.svg` | 资源消耗分布 |
| **Worker流式** | `dbgpt-worker-streaming-mechanism.svg` | Worker 流式机制 |
| **Worker对比** | `worker-vs-task-queue.svg` | Worker vs 任务队列 |
| **Worker内部** | `worker-internal-queue.svg` | Worker 内部队列 |
| **会话架构** | `conversation-history-architecture.svg` | 历史会话架构 |
| **会话流程** | `conversation-history-flow.svg` | 历史会话流程 |
| **上下文管理** | `context-window-management.svg` | 上下文窗口管理 |

---

## 1. 整体架构图

![整体架构图](assets/dbgpt-architecture-overview.svg)

### 核心洞察

- **六层架构**：用户层 → 接入层 → 应用层 → 服务层 → 核心层 → Worker层 → 存储层
- **Controller-Worker 模式**：模型推理任务分布式执行，Worker 独立注册
- **SystemApp 组件管理**：类似 Spring 的 DI 容器，统一管理组件生命周期

---

## 2. Monorepo 结构

![Monorepo 结构](assets/dbgpt-monorepo-structure.svg)

### 核心洞察

- **五包分层**：core → serve → app → ext → client
- **单向依赖**：上层依赖下层，core 是唯一切点
- **dbgpt-ext 可替换**：第三方实现不侵入核心

---

## 3. 部署模式对比

![部署模式](assets/dbgpt-service-deployment.svg)

### 核心洞察

| 模式 | 特点 | 适用场景 |
|------|------|----------|
| **All-in-One** | 单进程启动，组件嵌入式运行 | 开发/调试 |
| **服务分离** | Controller/Worker/WebServer 独立部署 | 生产环境 |

- **Controller** 负责 Worker 注册发现与负载均衡
- **Worker** 可按模型类型独立扩缩容
- **WebServer** 无状态，支持横向扩展

---

## 4. 请求处理流程

![请求流程](assets/dbgpt-request-flow.svg)

### 核心洞察

1. WebServer 接收请求
2. 查询 Controller 获取可用 Worker
3. Controller 返回健康 Worker 地址
4. WebServer 直接调用 Worker 执行推理
5. 结果逐层返回

**耗时分布**：
- 查询 Controller: ~1ms
- 选择 Worker: ~5ms
- 模型推理: 100ms - 10s+

---

## 5. 组件管理系统

![组件系统](assets/dbgpt-component-system.svg)

### 核心洞察

- **SystemApp 是中央注册中心**：所有组件在此注册
- **依赖获取方式**：`get_component("xxx_manager")`
- **层级关系**：
  - WorkerManager → ModelController
  - AgentManager → ResourceManager
  - DAGManager → TriggerManager

---

## 6. 横向扩展对比

![横向扩展对比](assets/scaling-comparison.svg)

### 核心差异

| 维度 | DB-GPT | RAGFlow |
|------|--------|---------|
| **扩展目标** | GPU Worker（模型推理） | Task Executor（文档处理） |
| **触发条件** | LLM 并发请求增加 | 文档处理队列积压 |
| **扩容方式** | 启动同名 Worker 自动注册 | 增加 Celery Worker 消费队列 |
| **任务类型** | 短时、同步、无状态 | 长时、异步、有状态 |

### 一句话理解

- **DB-GPT 扩容**：加 GPU 机器跑更多大模型实例
- **RAGFlow 扩容**：加 CPU 机器处理更多文档解析任务

---

## 7. 任务队列机制

![任务队列机制](assets/dbgpt-task-queue-mechanism.svg)

### 核心结论

**DB-GPT 有任务队列，但选择性使用**：

| 功能 | 使用队列？ | 原因 |
|------|-----------|------|
| 模型推理 |  | 需要实时响应 |
| 知识库构建 |  | 文档处理耗时 |

详见：[DB-GPT-任务队列机制详解](DB-GPT-任务队列机制详解.md)

---

## 8. 多用户支持

![多用户架构](assets/dbgpt-multi-user-architecture.svg)

### 核心结论

**DB-GPT 支持多用户**：

-  多用户注册/登录
-  数据按用户隔离
-  支持角色权限
-  WebServer 无状态可扩展

面向用户的功能队列使用：

| 功能 | 队列 | 说明 |
|------|------|------|
| 对话 |  | 同步实时 |
| 知识库 |  | 异步后台 |
| Agent |  | 同步实时 |

详见：[DB-GPT-多用户与队列机制分析](DB-GPT-多用户与队列机制分析.md)

---

## 9. Chat 与企业级实践

![Chat 并发架构](assets/chat-concurrency-architecture.svg)

### 核心结论

**Chat 不用队列是正确设计**：

-  行业通用做法（ChatGPT、Claude 等）
-  多用户支持靠 WebServer 水平扩展
-  是企业级架构（限流、熔断、负载均衡）

![队列对比](assets/queue-vs-direct-comparison.svg)

**队列 vs 直接调用**：

| 维度 | 直接调用 | 任务队列 |
|------|---------|---------|
| 延迟 | 低 | 高 |
| 体验 | 实时 | 异步 |
| 适用 | 实时对话 | 后台任务 |

详见：[DB-GPT-Chat多用户与企业级实践分析](DB-GPT-Chat多用户与企业级实践分析.md)

---

## 10. RAGFlow 架构分析

![RAGFlow Chat](assets/ragflow-chat-architecture.svg)

### 核心结论

**RAGFlow Chat 也不用队列！**

-  Chat 同步调用，无队列
-  文档处理用队列（Celery）
-  调用外部 LLM API（非自托管）

![RAGFlow 对比](assets/ragflow-vs-dbgpt-chat-comparison.svg)

**与 DB-GPT 对比**：

| 维度 | DB-GPT | RAGFlow |
|------|--------|---------|
| Chat 队列 | 无 | 无 |
| 模型部署 | 自托管 Worker | 调用外部 API |
| 核心定位 | 大模型服务 | 文档处理 |

详见：[RAGFlow-架构深度分析](RAGFlow-架构深度分析.md)

---

## 11. 流式输出支持

![流式架构](assets/dbgpt-streaming-architecture.svg)

### 核心结论

**DB-GPT 前端完全支持流式输出**：

-  使用 SSE (Server-Sent Events)
-  `useChat` Hook 实现
-  逐字显示，体验好

![流式对比](assets/streaming-comparison.svg)

**流式 vs 普通响应**：

| 维度 | 普通响应 | 流式输出 |
|------|---------|---------|
| 感知延迟 | 高 | 低 |
| 用户体验 | 等待焦虑 | 实时反馈 |
| 行业标配 |  |  |

详见：[DB-GPT-流式输出支持](DB-GPT-流式输出支持.md)

---

## 12. 架构设计总结

![决策树](assets/when-to-use-queue-decision-tree.svg)

### 核心结论

**何时使用队列？**

-  **不用队列**：实时交互、短时任务、同步调用
-  **使用队列**：后台处理、长时任务、异步处理

**从项目中学习的架构原则**：

1. 队列不是万能的
2. 瓶颈决定扩展方向
3. 用户体验优先
4. 混合架构是趋势

![架构模式](assets/architecture-patterns-comparison.svg)

**三种架构模式**：

| 模式 | 适用场景 | 示例 |
|------|---------|------|
| 同步直接调用 | 实时交互 | Chat |
| 异步任务队列 | 后台处理 | 文档解析 |
| 混合架构 | 完整平台 | DB-GPT / RAGFlow |

详见：[何时使用队列-架构设计总结](何时使用队列-架构设计总结.md)

---

## 13. 流式输出实现分析

![DB-GPT 流式](assets/dbgpt-streaming-implementation.svg)

### 核心结论

**两者都使用 SSE (Server-Sent Events)**：

| 项目 | 前端 | 后端 | 模型 |
|------|------|------|------|
| DB-GPT | `@microsoft/fetch-event-source` | FastAPI StreamingResponse | 自托管 Worker |
| RAGFlow | 原生 EventSource | Flask Response | 外部 LLM API |

![流式对比](assets/streaming-implementation-comparison.svg)

**核心差异**：
- DB-GPT: Worker(自托管) → StreamingResponse → 前端
- RAGFlow: 外部 LLM API → Response → 前端

![SSE 协议](assets/sse-protocol-detail.svg)

详见：[RAGFlow-vs-DB-GPT-流式输出实现分析](RAGFlow-vs-DB-GPT-流式输出实现分析.md)

---

## 14. Chat 高并发与队列问题

![高并发架构](assets/chat-high-concurrency-architecture.svg)

### 核心结论

**为什么 Chat 不用队列也能扛高并发？**

-  资源消耗在 Worker (GPU)，不在 WebServer
-  队列不能增加 GPU 算力，只能增加延迟
-  高并发通过**限流 + 扩容 Worker**解决

![队列局限](assets/queue-cant-help.svg)

**队列 vs 不用队列对比**：

| 维度 | 不用队列 | 用队列 |
|------|---------|--------|
| 吞吐量 | 100 QPS | 100 QPS（一样） |
| 延迟 | 几秒 | 几分钟 |
| 用户体验 | 立即知道结果 | 不知道等多久 |

详见：[Chat高并发与队列问题详解](Chat高并发与队列问题详解.md)

---

## 15. Worker 流式输出机制

![Worker 流式](assets/dbgpt-worker-streaming-mechanism.svg)

### 核心澄清

**Worker 是 HTTP 推理服务，不是任务队列！**

```
前端 SSE → WebServer → Worker HTTP → 模型逐字生成 → 流式返回
```

**Worker 特点**：
- HTTP Server，提供 `/generate` API
- 同步调用，流式返回
- 模型使用 `yield` 逐字生成 token

**Worker 不是什么**：
-  不是 Celery 任务队列
-  不是 Redis 队列
-  是模型推理服务

![Worker 对比](assets/worker-vs-task-queue.svg)

详见：[DB-GPT-Worker流式输出机制详解](DB-GPT-Worker流式输出机制详解.md)

---

## 16. 历史会话回顾功能

![会话架构](assets/conversation-history-architecture.svg)

### 核心结论

**两者都支持历史会话回顾**：

| 功能 | DB-GPT | RAGFlow |
|------|--------|---------|
| 历史会话列表 |  |  |
| 会话详情查看 |  |  |
| 继续历史对话 |  |  |
| 引用溯源 | ⚠️ 基础 |  强 |

**数据模型**：
- DB-GPT: `conversation` + `chat_message`
- RAGFlow: `dialog` + `message`（带 reference 字段）

![上下文管理](assets/context-window-management.svg)

**上下文管理策略**：
1. **直接截断**：保留最近 N 条
2. **滑动窗口**：保留最近 N 轮（常用）
3. **摘要+最近**：早期摘要 + 最近完整对话

详见：[历史会话回顾功能分析](历史会话回顾功能分析.md)

---

## 17. 流式输出与历史会话生命周期

![生命周期](assets/streaming-and-history-lifecycle.svg)

### 核心机制

**生命周期**：
1. 创建对话 → 2. 保存用户消息 → 3. 流式输出 → 4. 保存 AI 回复 → 5. 更新对话

**关键设计**：
- 用户消息：立即保存
- AI 消息：流式完成后一次性保存
- 中断处理：保存已生成部分

![状态管理](assets/streaming-state-management.svg)

**技术框架**：
- 前端：React + SSE
- 后端：FastAPI/Flask + StreamingResponse
- 数据库：MySQL/PostgreSQL

详见：[流式输出与历史会话生命周期分析](流式输出与历史会话生命周期分析.md)

---

## 附录：源码文件

所有 `.dot` 源文件位于 `assets/` 目录，可修改后重新渲染：

```powershell
# 渲染所有图表
cd assets
foreach ($file in Get-ChildItem -Filter "*.dot") {
    $svg = $file.BaseName + ".svg"
    dot -Tsvg $file.Name -o $svg
}
```

---

*生成时间：2026-02-06*  
*工具：Graphviz 14.1.2*
