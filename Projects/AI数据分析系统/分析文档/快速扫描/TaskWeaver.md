# TaskWeaver - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | 微软开发的 code-first Agent 框架，专为数据分析任务设计，支持代码片段解释用户请求并通过插件协调执行 |
| Star/Fork | 6.1k / 待查 |
| 维护状态 | 活跃（最近更新 2025-03） |
| 许可证 | MIT |

## 2. 核心能力速览
- 主要功能:
  - 复杂任务规划与分解（Planner + CodeInterpreter 双角色架构）
  - 代码优先的任务执行（支持 Python 代码生成与执行）
  - 插件系统（自定义算法封装为插件）
  - 状态保持执行（保留内存中数据结构如 DataFrame）
  - 代码验证与安全执行（支持容器模式）
  - 多角色协作（Planner、CodeInterpreter、Recepta 等扩展角色）
- 技术亮点:
  - **双角色架构**：Planner 负责任务规划，CodeInterpreter 负责代码执行
  - **状态保持**：不同于纯文本对话，保留代码执行历史和内存数据
  - **共享内存**：角色间信息共享机制

## 3. 架构概览
TaskWeaver 采用**多角色协作架构**，核心是 Planner + CodeInterpreter 双角色设计：

```
User <-> Planner <-> CodeInterpreter <-> CodeExecutor
            |              |
            v              v
      Shared Memory   Plugin Pool
```

- **Agent类型**: Plan-and-Execute + ReAct 混合
- **工具注册**: 插件系统通过 YAML + Python 文件定义，`taskweaver/plugin/` 目录下注册
- **记忆管理**: 
  - Conversation 历史记录（Round/Post 结构）
  - Shared Memory 角色间信息共享
  - Experience 从历史对话学习经验

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 5 | 成熟的双角色架构，Planner-Worker 模式值得借鉴 |
| 代码复用 | 4 | 插件系统、代码执行器、记忆模块可复用 |
| 集成潜力 | 4 | 可作为库导入，支持容器化部署 |
| 学习价值 | 5 | 微软出品，代码质量高，文档完善 |

### 4.1 值得借鉴的设计
- **Planner-Worker 角色分离**：明确规划与执行的职责边界
- **代码验证机制**：执行前静态检查代码安全性
- **共享内存设计**：多 Agent 间状态共享机制
- **Experience 学习**：从历史对话提取经验用于后续任务

### 4.2 可复用的代码/模块
- `taskweaver/code_interpreter/code_executor.py` - 代码执行引擎
- `taskweaver/plugin/` - 插件注册与管理
- `taskweaver/memory/` - 记忆管理模块
- `taskweaver/planner/planner.py` - 规划器实现

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| `taskweaver/planner/planner.py` | 任务规划器，负责任务分解与角色协调 |
| `taskweaver/code_interpreter/code_interpreter.py` | 代码解释器角色实现 |
| `taskweaver/code_interpreter/code_executor.py` | 代码执行引擎 |
| `taskweaver/plugin/base.py` | 插件基类定义 |
| `taskweaver/memory/memory.py` | 记忆管理核心 |
| `taskweaver/ces/` | 代码执行服务（Code Execution Service） |

## 6. 优先级判定
- [x] 高优先级 - 重点研究
- [ ] 中优先级 - 参考借鉴
- [ ] 低优先级 - 了解即可

**推荐理由**: 
1. **架构成熟**：Planner + CodeInterpreter 双角色架构清晰，适合复杂数据分析任务
2. **微软背书**：代码质量高，维护活跃，文档完善
3. **技术匹配**：code-first 理念与我们的数据分析场景高度契合
4. **可扩展性**：支持自定义插件和角色扩展
