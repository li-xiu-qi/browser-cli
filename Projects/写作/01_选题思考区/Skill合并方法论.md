# Skill 合并方法论：从 34 个混乱到 12 个清晰的实战复盘

---

## 核心观点

**AI 协作工具的 Skill 不是越多越好，而是越"整"越好。**

当我的 Skill 从 5 个膨胀到 34 个时，我发现一个反直觉的现象：AI 反而变得更"笨"了。问题不在于 AI 的能力，而在于 Skill 的管理方式。

---

## 问题的症状（真实经历）

### 症状 1：选择困难
> 用户说"帮我整理一下这篇笔记"
> 
> AI 面对 3 个选择：`obsidian-markdown-formatter`、`wechat-markdown-publisher`、`text-polisher`
> 
> 不知道该调用哪一个，因为它们功能重叠但又不完全相同

### 症状 2：维护噩梦
- 同样的排版规则散落在 3 个 Skill 里
- 修改一个规范要改 3 处
- 版本不一致导致 AI 输出风格混乱

### 症状 3：上下文污染
```
.agents/skills/
├── skill-a/node_modules/  ← 重复的依赖
├── skill-b/node_modules/  ← 重复的依赖
├── skill-c/node_modules/  ← 重复的依赖
...
```

AI 加载时会把所有 Skill 文件都喂给上下文，34 个 Skill × 各自的 node_modules = 上下文爆炸。

---

## 合并的驱动力

我总结了一个简单的判断标准：

| 信号 | 含义 | 行动 |
|------|------|------|
| **总是同时使用** | 用户调用 A 时 90% 也会调用 B | 合并 |
| **概念重叠** | 两个 Skill 的 DESCRIPTION 有 50%+ 重复 | 合并 |
| **维护负担** | 改一个规则要改 N 处 | 合并 |
| **用户困惑** | 用户不知道该选哪个 | 合并 |

---

## 这次合并的成果

```
合并前：34 个 Skill
合并后：12 个 Skill + 2 个 Workflows

核心合并：
├── content-formatter ← obsidian-markdown-formatter + wechat-markdown-publisher + text-polisher (3→1)
├── content-converter ← epub2obsidian + md2docx + ocr-to-obsidian + pdf-translator + tongyi-tingwu + wechat-book-to-pdf + video-to-gif (7→1)
├── learning-notes ← course-note-taker + case-study-collector (2→1)
├── resource-crawler ← web-clipper + yt-dlp-downloader + zlibrary (3→1)
├── text-visualization ← graphviz-best-practices + html-table-templates + json-canvas (3→1)
└── agent-collaboration ← knowledge-base-manager + obsidian-vault-manager + knowledge-indexing (3→1, as docs)
```

---

## 关键洞察

### 1. 场景化组织优于功能化组织

**错误做法**：
```
skills/
├── epub2obsidian/     # EPUB 相关
├── md2docx/           # Word 相关
├── pdf-translator/    # PDF 相关
```

**正确做法**：
```
skills/
└── content-converter/     # 统一入口：内容转换
    ├── tools/
    │   ├── epub/          # EPUB 场景
    │   ├── md2docx/       # Word 场景
    │   └── pdf-translator/# PDF 场景
```

用户想的是"我要转换内容"，不是"我要用 EPUB 工具"。

### 2. Skill vs Workflow 的边界

| 类型 | 定位 | 例子 |
|------|------|------|
| **Skill** | 可调用能力，有入口函数 | content-converter |
| **Workflow** | 流程指南，告诉用户怎么做 | AI协作写作工作流 |
| **Doc** | 参考规范，供人阅读 | agent-collaboration |

**经验**：写作流程类的从 Skill 降级为 Workflow，因为它不是"工具"而是"方法论"。

### 3. 目录结构必须保持原貌

合并时最大的陷阱：想把文件扁平化。

**错误**：
```
tools/
├── epub2md.js          # 丢失了原项目的结构
├── md2docx.py          # 混合在一起
├── ocr.py
```

**正确**：
```
tools/
├── epub/               # 保留原项目结构
│   ├── epub2md.js
│   └── package.json
├── md2docx/
│   ├── md2docx.py
│   └── requirements.txt
└── ocr/
    └── ocr.py
```

保持原结构是为了：
- 未来拆分容易
- 原项目的 README/文档 还能对上
- 依赖关系清晰

### 4. 环境统一是必须的

**Before**：每个 Skill 有自己的 node_modules/ 或 venv/
**After**：全部使用根目录的共享环境

```
笔记专用/
├── .venv/              # 共享 Python 环境
├── node_modules/       # 共享 Node 环境
└── .agents/skills/
    └── content-converter/
        └── tools/
            ├── epub/       # 无 node_modules
            ├── md2docx/    # 无 venv
            └── ocr/        # 无私有依赖
```

---

## 给你的建议

### 判断是否应该合并的信号

- [ ] **总是同时使用**：调用 A 时 90% 也会调用 B
- [ ] **概念重叠**：两个 Skill 解决的是同一类问题
- [ ] **维护负担**：改一个规则要改多处
- [ ] **用户困惑**：用户不知道该选哪个
- [ ] **目录混乱**：skills/ 目录超过 20 个条目

### 判断应该保持独立的信号

- [ ] **独立价值**：单独使用也有意义
- [ ] **不同受众**：面向完全不同的用户群
- [ ] **组合灵活性**：用户可能需要 A 但不要 B
- [ ] **技术隔离**：依赖冲突严重无法共存

---

## 下一步：成文思路

这篇文章适合写成**经验复盘类技术文章**，目标读者是使用 AI 工具（Claude Code、Kimi CLI 等）的开发者。

**文章结构**：
1. 钩子：AI 变"笨"的陷阱
2. 为什么要合并？（问题症状）
3. 合并的三大原则（场景化、结构保持、环境统一）
4. 实战成果（合并前后对比）
5. 给你的建议（判断信号）
6. 附录：完整合并清单

**风格**：实操性强、有具体数字（34→12）、有代码/目录示例
