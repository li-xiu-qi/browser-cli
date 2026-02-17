# LAMBDA - 快速扫描报告

**分析日期**: 2026-02-05

## 1. 基础档案
| 维度 | 内容 |
|------|------|
| 项目定位 | 无代码多智能体数据分析系统，利用大模型能力实现自动化数据洞察（香港理工大学） |
| Star/Fork | 551 / 待查 |
| 维护状态 | 较慢（提供桌面 App 下载） |
| 许可证 | MIT |

## 2. 核心能力速览
- 主要功能:
  - 无代码数据分析（自然语言指令）
  - 双 Agent 系统（Programmer + Inspector）
  - 代码生成与自动调试
  - 自动报告生成
  - Jupyter Notebook 导出
  - 知识库集成（RAG）
- 技术亮点:
  - **双 Agent 协作**：Programmer 生成代码，Inspector 检查调试
  - **用户干预**：允许用户在操作循环中介入
  - **桌面应用**：提供 macOS/Windows 桌面 App

## 3. 架构概览
LAMBDA 采用**双 Agent 协作架构**：

```
User Input
    |
    v
Programmer Agent -> Generate Code -> Execute
    |                    |
    v                    v
Inspector Agent <- Check/Debug <- Result
    |
    v
Output / Report
```

- **Agent类型**: 双 Agent 协作（Programmer + Inspector）
- **工具注册**: 通过 Jupyter Kernel 执行 Python 代码
- **记忆管理**: 对话历史 + 项目缓存

## 4. 对我们项目的价值评估
| 评估项 | 评分 (1-5) | 说明 |
|--------|-----------|------|
| 架构参考 | 4 | Programmer-Inspector 双 Agent 模式有参考价值 |
| 代码复用 | 3 | 代码相对简单，核心逻辑可借鉴 |
| 集成潜力 | 3 | 可作为参考实现 |
| 学习价值 | 3 | 学术项目，设计简洁 |

### 4.1 值得借鉴的设计
- **Programmer-Inspector 分工**：代码生成与检查分离，提高可靠性
- **用户干预机制**：允许用户在执行循环中介入调整
- **Jupyter 导出**：工作流可导出为可复现的 Notebook

### 4.2 可复用的代码/模块
- `programmer.py` - Programmer Agent 实现
- `inspector.py` - Inspector Agent 实现
- `conversation.py` - 对话管理
- `kernel.py` - Jupyter Kernel 封装

## 5. 关键文件索引
| 文件路径 | 用途说明 |
|---------|---------|
| `LAMBDA.py` | 主入口类 |
| `programmer.py` | Programmer Agent |
| `inspector.py` | Inspector Agent |
| `conversation.py` | 对话状态管理 |
| `kernel.py` | Jupyter Kernel 执行环境 |
| `lambda_app.py` | Gradio UI 应用 |

## 6. 优先级判定
- [ ] 高优先级 - 重点研究
- [x] 中优先级 - 参考借鉴
- [ ] 低优先级 - 了解即可

**推荐理由**: 
1. **双 Agent 架构**：Programmer + Inspector 的分工模式值得借鉴
2. **简洁实现**：代码量适中，易于理解核心逻辑
3. **学术验证**：已发表 Journal of the American Statistical Association
4. **注意**：相比 TaskWeaver 和 AI Data Science Team，功能相对简单，适合作为入门参考
