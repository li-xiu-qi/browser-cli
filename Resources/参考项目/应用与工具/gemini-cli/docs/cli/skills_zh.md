# Agent Skills (智能体技能)

*注：这是一个实验性功能，需通过 `experimental.skills` 开启。你也可以在 `/settings` 交互界面中搜索 "Skills" 来切换此开关并管理其他相关设置。*

Agent Skills 允许你为 Gemini CLI 扩展专业领域知识、程序化工作流和特定任务资源。该功能基于 [Agent Skills](https://agentskills.io) 开放标准，一个“技能（Skill）”是一个自包含的目录，它将指令和资产打包成一种可被发现的能力。

## 概述

与通用的上下文文件（如 [`GEMINI.md`](./gemini-md.md)，提供持久的项目全局背景）不同，Skills 代表的是 **按需调用的专业知识（On-demand expertise）**。这使得 Gemini 能够维护一个庞大的专业能力库——例如安全审计、云部署或代码库迁移——而不会使模型的即时上下文窗口变得拥挤。

Gemini 会根据你的请求和技能描述，自主决定何时使用某项技能。当识别到相关技能时，模型会使用 `activate_skill` 工具“拉取”完成任务所需的完整指令和资源。

## 核心优势

- **知识共享**：将复杂的工作流（如特定团队的 PR 审查流程）打包成一个文件夹，供任何人使用。
- **可复用的工作流**：通过提供程序化框架，确保复杂的多步任务能够一致地执行。
- **资源捆绑**：将脚本、模板或示例数据与指令一起包含，使智能体拥有所需的一切。
- **渐进式披露（Progressive Disclosure）**：初始仅加载技能元数据（名称和描述）。详细指令和资源仅在模型明确激活技能时才披露，从而节省上下文 Token。

## 技能发现层级

Gemini CLI 从三个主要位置发现技能：

1.  **项目技能（Project Skills）** (`.gemini/skills/`)：项目特定的技能，通常提交至版本控制系统并与团队共享。
2.  **用户技能（User Skills）** (`~/.gemini/skills/`)：在所有项目中都可用的个人技能。
3.  **扩展技能（Extension Skills）**：捆绑在已安装的 [扩展](../extensions/index.md) 中的技能。

**优先级**：如果多个技能重名，高优先级位置将覆盖低优先级：**项目 > 用户 > 扩展**。

## 管理技能

### 在交互会话中

使用 `/skills` 命令查看和管理可用技能：

- `/skills list`（默认）：显示所有发现的技能及其状态。
- `/skills disable <name>`：防止使用特定技能。
- `/skills enable <name>`：重新启用已禁用的技能。
- `/skills reload`：从所有层级刷新已发现的技能列表。

*注：`/skills disable` 和 `/skills enable` 默认作用于 `user` 作用域。使用 `--scope project` 来管理项目特定的设置。*

### 在终端中

`gemini skills` 命令提供了管理工具：

```bash
# 列出所有发现的技能
gemini skills list

# 从 Git 仓库、本地目录或压缩的技能文件 (.skill) 安装技能
# 默认使用用户作用域 (~/.gemini/skills)
gemini skills install https://github.com/user/repo.git
gemini skills install /path/to/local/skill
gemini skills install /path/to/local/my-expertise.skill

# 使用 --path 从单体仓库或子目录安装特定技能
gemini skills install https://github.com/my-org/my-skills.git --path skills/frontend-design

# 安装到工作区作用域 (.gemini/skills)
gemini skills install /path/to/skill --scope workspace

# 按名称卸载技能
gemini skills uninstall my-expertise --scope workspace

# 启用技能（全局）
gemini skills enable my-expertise

# 禁用技能。可以使用 --scope 指定 project 或 user（默认为 project）
gemini skills disable my-expertise --scope project
```

## 创建技能

技能是一个在根目录下包含 `SKILL.md` 文件的目录。该文件使用 YAML frontmatter 定义元数据，并使用 Markdown 编写指令。

### 目录结构

技能是自包含的目录。技能至少需要一个 `SKILL.md` 文件，但也可以包含其他资源：

```text
my-skill/
├── SKILL.md       (必填) 指令与元数据
├── scripts/       (可选) 可执行脚本/工具
├── references/    (可选) 静态文档与示例
└── assets/        (可选) 模板与二进制资源
```

### 基础结构 (SKILL.md)

```markdown
---
name: <唯一名称>
description: <技能的功能以及 Gemini 何时该使用它>
---

<关于智能体应如何行为/使用该技能的指令>
```

- **`name`**：唯一标识符（小写字母、数字和连字符）。
- **`description`**：最重要的字段。Gemini 根据此字段决定技能何时相关。请务必详细描述其提供的专业知识。
- **正文**：第二个 `---` 下方的所有内容都将作为专家的程序化指南注入到模型中。

### 示例：团队代码评审员 (Team Code Reviewer)

创建 `~/.gemini/skills/code-reviewer/SKILL.md`：

```markdown
---
name: code-reviewer
description:
  擅长审查代码的风格、安全性和性能。当用户要求“反馈”、“评审”或“检查”其更改时使用。
---

# 代码评审员

你是一名资深代码评审员。在评审代码时，请遵循以下流程：

1.  **分析**：审查暂存的更改或提供的特定文件。确保更改范围合理，且是解决问题所需的最精简改动。
2.  **风格**：确保代码遵循 `GEMINI.md` 文件中描述的项目规范和惯用模式。
3.  **安全性**：标记任何潜在的安全漏洞。
4.  **测试**：验证新逻辑是否有对应的测试覆盖，且测试覆盖能够充分验证这些更改。

请以简练的列表形式提供反馈，分为“优势”和“改进点”。
```

### 资源约定

虽然你可以根据喜好组织技能目录，但 Agent Skills 标准建议遵循以下约定：

- **`scripts/`**：智能体可以运行的可执行脚本（bash, python, node）。
- **`references/`**：供智能体参考的静态文档、Schema 或示例数据。
- **`assets/`**：代码模板、样板代码或二进制资源。

当技能被激活时，Gemini CLI 会向模型提供整个技能目录的 tree 视图，使其能够发现并利用这些资产。

## 运行机制（安全与隐私）

1.  **发现（Discovery）**：在会话开始时，Gemini CLI 扫描发现层级，并将所有已启用技能的名称和描述注入到系统提示词中。
2.  **激活（Activation）**：当 Gemini 识别到与技能描述匹配的任务时，它会调用 `activate_skill` 工具。
3.  **授权（Consent）**：你会在界面中看到一个确认提示，详细说明技能的名称、用途以及它将获得的目录访问权限。
4.  **注入（Injection）**：经你批准后：
    - `SKILL.md` 的正文和目录结构会被添加到对话历史中。
    - 技能目录会被添加到智能体的允许文件路径中，授予其读取任何捆绑资产的权限。
5.  **执行（Execution）**：模型在专业知识激活的状态下继续运行。它被要求在合理范围内优先遵循技能的程序化指南。
