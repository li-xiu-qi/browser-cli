# Agent 专属分析计划

> 深度分析三个优秀项目的 Agent 架构设计：TaskWeaver、PandasAI、PremSQL

---

## 分析目标

理解不同项目如何解决以下 Agent 核心问题：
1. **Agent 生命周期管理** - 创建、执行、销毁
2. **规划与决策** - 如何决定执行什么
3. **记忆与会话** - 状态如何保持
4. **工具/动作扩展** - 如何添加新能力
5. **多 Agent 协作** - 如何协调多个 Agent

---

## 项目清单

| 项目 | 核心特点 | 分析重点 |
|------|---------|---------|
| **TaskWeaver** | 微软开源，Planner+Worker+Role 架构 | 依赖注入、角色系统、经验学习 |
| **PandasAI** | 极简 API，专注数据分析 | 状态机、自动重试、Sandbox |
| **PremSQL** | Pipeline 流水线设计 | Worker 链式执行、路由决策 |

---

## 分析维度

### 1. 架构设计
- [ ] 整体架构图
- [ ] 核心类与接口
- [ ] 模块依赖关系

### 2. Agent 生命周期
- [ ] 创建流程
- [ ] 执行流程
- [ ] 销毁/清理流程

### 3. 规划与决策
- [ ] 如何理解用户意图
- [ ] 如何选择工具/动作
- [ ] 多步任务如何规划

### 4. 记忆机制
- [ ] 短期记忆（会话）
- [ ] 长期记忆（持久化）
- [ ] 经验学习（如果有）

### 5. 扩展性
- [ ] 如何添加新 Agent
- [ ] 如何添加新工具
- [ ] 配置化程度

### 6. 代码质量
- [ ] 设计模式使用
- [ ] 错误处理
- [ ] 可测试性

---

## 输出要求

每个项目产出：
1. `XX-Agent架构深度分析.md` - 详细分析文档
2. `graphviz/XX-核心流程图.dot` - Graphviz 流程图 (统一放在 graphviz 目录)
3. `XX-类图分析.md` - 核心类关系

---

## 参考代码路径

```
Projects/AI数据分析系统/参考项目/
├── TaskWeaver/taskweaver/
│   ├── planner/planner.py          # Planner 核心
│   ├── role/role.py                # Role 基础类
│   ├── code_interpreter/           # CodeInterpreter Worker
│   ├── memory/                     # 记忆系统
│   └── plugin/                     # 插件系统
│
├── pandas-ai/pandasai/
│   ├── agent/base.py               # Agent 基础类
│   ├── agent/state.py              # 状态管理
│   ├── core/code_generation/       # 代码生成
│   └── core/code_execution/        # 代码执行
│
└── premsql/premsql/agents/
    ├── base.py                     # Worker 基类
    ├── router.py                   # 路由决策
    ├── baseline/workers/           # 各种 Worker
    └── memory.py                   # 记忆管理
```

---

## 分析顺序

三个项目**并行分析**，最后汇总对比。

---

*计划创建时间: 2026-02-06*  
*分析负责人: AI Code Assistant (并行子Agent)*
