# Workflows 工作流目录

本目录包含 AI 协作的**标准化工作流**，每个工作流以**独立文件夹**形式组织，包含完整的执行规范、检查清单和示例。

---

## 目录结构

```
workflows/
├── README.md                              # 本文件：工作流总览
├── case-study-collection/                 # 案例收集
├── course-manuscript-refinement/          # 课程文稿精修
├── course-lecture-to-notes/               # 课程逐字稿转笔记
├── knowledge-processing/                  # 知识处理
└── knowledge-to-action/                   # 知识到行动
```

---

## 工作流列表

| 工作流 | 用途 | 触发语 | 复杂度 |
|-------|------|--------|--------|
| [[case-study-collection]] | 系统化收集决策案例 | "使用案例收集工作流" | ⭐⭐⭐ |
| [[course-manuscript-refinement]] | 课程转录文稿的排版与重命名 | "执行课程文稿精修工作流" | ⭐⭐ |
| [[course-lecture-to-notes]] | 课程逐字稿转结构化笔记 | "使用课程逐字稿转笔记工作流" | ⭐⭐⭐⭐ |
| [[knowledge-processing]] | 原始文稿到个人笔记的完整处理 | "使用知识处理工作流" | ⭐⭐⭐ |
| [[knowledge-to-action]] | 从笔记萃取 AI 可执行技能 | "使用 K2A 技能萃取工作流" | ⭐⭐⭐ |

---

## 工作流文件夹规范

每个工作流文件夹必须包含：

```
workflows/[workflow-name]/
├── README.md          # 工作流简介（1分钟了解）
├── WORKFLOW.md        # 完整工作流文档（详细步骤）
└── assets/            # （可选）示例文件、模板
```

### 文件说明

| 文件 | 用途 | 阅读时机 |
|-----|------|---------|
| `README.md` | 工作流简介、适用场景、快速启动 | 第一次了解该工作流 |
| `WORKFLOW.md` | 详细步骤、检查清单、最佳实践 | 执行工作流时参考 |

---

## 如何使用工作流

### 方式一：直接引用

告诉 AI 你要使用哪个工作流：

> "使用知识处理工作流，处理这个文件：resources/一堂课程/..."

### 方式二：浏览选择

1. 查看上文的"工作流列表"
2. 点击进入对应文件夹阅读 README
3. 按 README 指引执行

---

## 添加新工作流

如需添加新的工作流：

1. 在 `workflows/` 下新建文件夹（kebab-case 命名）
2. 创建 `README.md` 和 `WORKFLOW.md`
3. 更新本文件的"工作流列表"
4. （可选）在 AGENTS.md 中添加引用

### 命名规范

- 文件夹：kebab-case（短横线连接的小写字母）
- 示例：`course-to-notes-yitang`

---

## 维护者

- 创建：筱可
- 更新：2026-02-04
