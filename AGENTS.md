# AGENTS.md - 笔记专用知识库

**版本**: 3.0.0  
**更新日期**: 2026-02-15  
**角色**: AI 协作总入口

---

## AI 协作规范（执行任何任务前的首要步骤）

**核心 Skill**: `.agents/skills/agent-collaboration/`

### 铁律：先读规范，再动手

**执行任务前，AI 必须完成以下步骤**：

1. **识别任务类型**（写作、分类、开发、管理等）
2. **检查项目级 README** - 如果工作目录有 README.md，优先阅读其中的"项目特定规范"部分
3. **阅读对应规范文档**（见下表）
4. **确认理解规范后**，才开始执行

### 规范优先级（重要！）

当规范冲突时，按以下优先级执行：

| 优先级 | 规范来源 | 说明 |
|--------|----------|------|
| 1 (最高) | **项目 README.md** | 项目根目录的 README 中定义的"项目特定规范" |
| 2 | **AGENTS.md** | 全局 AI 协作规范 |
| 3 | **SKILL.md** | 具体 Skill 的规范 |
| 4 | **通用最佳实践** | 行业通用的最佳实践 |

**示例**：如果 Projects/ERNIE-SQL/README.md 规定 "禁止重复下载数据"，而全局规范未提及，则以项目 README 为准。

| 如果你要... | 必须先阅读... |
|-------------|---------------|
| 不确定从哪开始 | [[agent-collaboration/00-基础规范/_入口导航]] |
| 创建或编辑笔记 | [[agent-collaboration/00-基础规范/写作规范]] |
| 确定文件放在哪里 | [[agent-collaboration/00-基础规范/PARA方法论]] |
| 查找目录位置 | [[agent-collaboration/00-基础规范/项目目录结构]] |
| 开发新的 Skill | [[agent-collaboration/01-开发指南/Skill开发规范]] |
| 管理知识库或 Cliper 数据 | [[agent-collaboration/02-知识运营/知识库管理手册]] |
| 管理图片素材库 | [[agent-collaboration/02-知识运营/图片资源管理]] |
| 配置 Python/Node.js 环境 | [[agent-collaboration/01-开发指南/开发环境配置]] |
| 修改 AI 规范本身 | [[agent-collaboration/01-开发指南/规范体系管理]] |

### 绝对禁止

- **禁止**不读规范直接凭经验执行
- **禁止**使用 Linux/Mac 命令（本环境是 **Windows + PowerShell**）
- **禁止**假设"大概就是这样"而忽视文档

---

## 快速任务导航

| 任务 | 查阅文档 |
|------|----------|
| 了解系统环境 | [[agent-collaboration/00-基础规范/_入口导航#系统环境]] |
| 创建/编辑笔记 | [[agent-collaboration/00-基础规范/写作规范]] |
| 确定文件位置 | [[agent-collaboration/00-基础规范/PARA方法论]] |
| 查找目录结构 | [[agent-collaboration/00-基础规范/项目目录结构]] |
| 处理课程案例 | [[agent-collaboration/02-知识运营/知识库管理手册]] |
| 管理附件 | [[agent-collaboration/02-知识运营/知识库管理手册#附件管理]] |
| 管理抓取文章 | [[agent-collaboration/02-知识运营/知识库管理手册#Cliper Datas 管理]] |
| 评估图片质量 | [[.agents/tools/image-analyzer/README]] |
| 开发新 Skill | [[agent-collaboration/01-开发指南/Skill开发规范]] |
| 配置开发环境 | [[agent-collaboration/01-开发指南/开发环境配置]] |
| 修改 AI 规范 | [[agent-collaboration/01-开发指南/规范体系管理]] |
| 归档内容 | [[Archives/README\|归档中心]] |
| 查找一堂课程 | [[Areas/导航/一堂课程-个人篇\|一堂课程导航]] |
| 创建索引文件 | [[agent-collaboration/02-知识运营/知识库管理#索引命名规范\|索引命名规范]] |

---

## 架构说明

### 目录结构

```
.agents/
├── tools/                    # 🔧 共用工具（多 Skill 共享）
│   ├── browser-login/        # 通用浏览器登录
│   ├── directory-indexer/    # 目录索引
│   └── ...
│
├── workflows/                # 🔄 工作流（已合并 skill 迁移至此）
│   ├── AI协作写作工作流.md
│   └── 模型评测文章写作工作流.md
│
└── skills/                   # 📚 Skill（规范 + 私有工具）
    ├── agent-collaboration/  # 核心规范体系
    ├── content-converter/    # 内容转换（7场景）
    ├── content-formatter/    # 内容排版（3场景）
    ├── learning-notes/       # 学习笔记（3场景）
    ├── resource-crawler/     # 资源抓取（3场景）
    ├── text-visualization/   # 文本可视化（3场景）
    └── ...
```

### 使用原则

| 类型 | 位置 | 说明 |
|------|------|------|
| **共用工具** | `tools/` | 多个 Skill 共享的工具，如 browser-login, image-analyzer |
| **Skill 工具** | `skills/{name}/tools/` | 仅该 Skill 使用的工具 |
| **公共工作流** | `workflows/` | 跨多个 Skill 的复合流程 |
| **Skill 工作流** | `skills/{name}/workflows/` | 仅该 Skill 内部的 SOP |

---

## 可用技能库

**核心位置**: `.agents/skills/`

| Skill | 用途 | 场景数 |
|-------|------|--------|
| agent-collaboration | AI 协作规范体系（含知识库管理） | 规范文档 |
| content-converter | 内容格式转换 | 7 场景 |
| content-formatter | 内容排版规范 | 3 场景 |
| learning-notes | 学习笔记与案例收集 | 3 场景 |
| resource-crawler | 网络资源抓取 | 3 场景 |
| text-visualization | 文本可视化 | 3 场景 |
| notebooklm-uploader | 上传书籍到 NotebookLM | 独立工具 |
| mcp-builder | MCP 服务器构建 | 独立工具 |
| remotion-renderer | Remotion 视频渲染 | 独立工具 |
| uv-package-manager | UV 包管理 | 独立工具 |

**规范中心**: [[agent-collaboration/SKILL|agent-collaboration]] - 所有规范的入口

---

## 工作流使用指南

### 公共工作流（跨 Skill）

**位置**: `.agents/workflows/`

| 工作流 | 用途 | 触发语 |
|-------|------|--------|
| [[workflows/knowledge-processing\|知识处理]] | 原始文稿 → 个人笔记 | "使用知识处理工作流" |
| [[workflows/knowledge-to-action\|知识到行动]] | 从笔记萃取 AI 技能 | "使用 K2A 技能萃取工作流" |

### 工作流（已合并 Skill 迁移至此）

**位置**: `workflows/`

| 工作流 | 来源 | 用途 |
|--------|------|------|
| AI协作写作工作流.md | ai-writing-collaborator | AI协作五步写作流程 |
| 模型评测文章写作工作流.md | model-evaluator-writer | AI模型评测文章写作指南 |

**说明**: 
- **工作流** 在 `workflows/` 目录，提供特定场景的完整 SOP
- **Skill 私有工具** 在 `skills/{name}/tools/` 目录，按子目录组织

---

## AI 身份设定

**唯一事实来源**: [[Areas/My_Persona/00_基本设定与交流]]

- AI 自称"小可"
- 用户署名"筱可"
- 核心驱动力：赢与构建秩序

---

## 版本更新说明

| 版本 | 日期 | 变更 |
|------|------|------|
| 3.0.2 | 2026-02-15 | 规范二级目录去序号化：一级保留序号，二级及以下使用纯文件名 |
| 3.0.1 | 2026-02-15 | 规范序号体系重构：统一 agent-collaboration 各目录编号为连续序号 |
| 3.0.0 | 2026-02-15 | 大规模 Skill 合并：从 34 个合并为 12 个 Skill + 2 个工作流，详见合并总结文档 |
| 2.8.1 | 2026-02-11 | AI 身份设定整合进 agent-collaboration SKILL |
| 2.8.0 | 2026-02-06 | 新增项目级规范优先级规则，项目 README 优先于全局规范 |
| 2.7.0 | 2026-02-05 | 新增规范体系管理，去除重复内容 |
| 2.6.0 | 2026-02-05 | 增加系统环境说明 |

**详细变更记录**: [[agent-collaboration/changelogs/README|变更日志中心]]

---

## 维护者

筱可 (li-xiu-qi)
