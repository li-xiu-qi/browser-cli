# Skill 合并过程记录

> 记录 2026-02-11 至 2026-02-15 的 Skill 合并全过程，用于文章素材。

---

## 合并前状态（2026-02-11）

### 问题发现
- 用户说"帮我整理这篇笔记"，AI 不知道该调用 `obsidian-markdown-formatter` 还是 `text-polisher`
- 34 个 Skill，其中很多概念重叠
- 每个 Skill 有自己的 node_modules/venv，上下文爆炸

### 完整列表（合并前 34 个）

```
.agents/skills/
├── agent-collaboration/          # 保留（核心规范）
├── ai-writing-collaborator/      # → 降级为 workflow
├── baidu-pan-organizer/          # 保留（独立工具）
├── case-study-collector/         # → 合并到 learning-notes
├── course-note-taker/            # → 合并到 learning-notes
├── directory-indexer/            # 保留（独立工具）
├── epub2obsidian/                # → 合并到 content-converter
├── find-skills/                  # 保留（独立工具）
├── graphviz-best-practices/      # → 合并到 text-visualization
├── html-table-templates/         # → 合并到 text-visualization
├── json-canvas/                  # → 合并到 text-visualization
├── knowledge-base-manager/       # → 合并到 agent-collaboration (as doc)
├── knowledge-indexing/           # → 合并到 agent-collaboration (as doc)
├── md2docx/                      # → 合并到 content-converter
├── mcp-builder/                  # 保留（独立工具）
├── model-evaluator-writer/       # → 降级为 workflow
├── notebooklm-uploader/          # 保留（独立工具）
├── obsidian-markdown-formatter/  # → 合并到 content-formatter
├── obsidian-vault-manager/       # → 合并到 agent-collaboration (as doc)
├── ocr-to-obsidian/              # → 合并到 content-converter
├── pdf-translator/               # → 合并到 content-converter
├── remotion-renderer/            # 保留（独立工具）
├── skill-creator/                # 删除（用不上了）
├── text-polisher/                # → 合并到 content-formatter
├── tongyi-tingwu/                # → 合并到 content-converter
├── uv-package-manager/           # 保留（独立工具）
├── video-to-gif/                 # → 合并到 content-converter
├── web-clipper/                  # → 合并到 resource-crawler
├── wechat-book-to-pdf/           # → 合并到 content-converter
├── wechat-markdown-publisher/    # → 合并到 content-formatter
├── yt-dlp-downloader/            # → 合并到 resource-crawler
└── zlibrary-to-notebooklm/       # → 合并到 resource-crawler
```

---

## 合并决策记录

### 第一类：内容处理相关（10→2）

| 原 Skill | 合并目标 | 理由 | 敏感标记 |
|----------|----------|------|----------|
| obsidian-markdown-formatter | content-formatter | 都是排版 | 否 |
| wechat-markdown-publisher | content-formatter | 都是排版 | 否 |
| text-polisher | content-formatter | 都是排版 | 否 |
| epub2obsidian | content-converter | 都是转换 | 否 |
| md2docx | content-converter | 都是转换 | 否 |
| ocr-to-obsidian | content-converter | 都是转换 | 否 |
| pdf-translator | content-converter | 都是转换 | 否 |
| tongyi-tingwu | content-converter | 都是转换 | 否 |
| wechat-book-to-pdf | content-converter | 都是转换 | **🔴 是** |
| video-to-gif | content-converter | 都是转换 | 否 |

**关键洞察**：用户想的是"我要转换/排版内容"，不是"我要用 EPUB 工具"

### 第二类：学习场景（2→1）

| 原 Skill | 合并目标 | 理由 |
|----------|----------|------|
| course-note-taker | learning-notes | 都是学习 |
| case-study-collector | learning-notes | 都是学习 |

### 第三类：资源获取（3→1）

| 原 Skill | 合并目标 | 理由 | 敏感标记 |
|----------|----------|------|----------|
| web-clipper | resource-crawler | 都是获取资源 | 部分敏感 |
| yt-dlp-downloader | resource-crawler | 都是获取资源 | **🟡 需谨慎** |
| zlibrary-to-notebooklm | resource-crawler | 都是获取资源 | **🔴 是** |

### 第四类：文本可视化（3→1）

| 原 Skill | 合并目标 | 理由 |
|----------|----------|------|
| graphviz-best-practices | text-visualization | 文字→图形 |
| html-table-templates | text-visualization | 文字→表格 |
| json-canvas | text-visualization | 文字→画布 |

### 第五类：知识库管理（3→1，降级为 Doc）

| 原 Skill | 合并目标 | 理由 |
|----------|----------|------|
| knowledge-base-manager | agent-collaboration | 都是规范文档 |
| obsidian-vault-manager | agent-collaboration | 都是规范文档 |
| knowledge-indexing | agent-collaboration | 都是规范文档 |

**关键洞察**：这类不是"可调用工具"，而是"参考规范"，应该作为 agent-collaboration 的子文档

### 第六类：写作流程（2→2，降级为 Workflow）

| 原 Skill | 处理方式 | 理由 | 敏感标记 |
|----------|----------|------|----------|
| ai-writing-collaborator | → workflows/ | 不是工具，是方法论 | 否 |
| model-evaluator-writer | → workflows/ | 不是工具，是方法论 | 否 |

---

## 敏感内容说明

**🔴 高度敏感**（公开文章必须脱敏）：
- `wechat-book-to-pdf`：涉及微信读书平台内容获取
- `zlibrary-to-notebooklm`：涉及 Z-Library 资源下载

**🟡 需谨慎**（建议模糊处理）：
- `yt-dlp-downloader`：视频下载工具
- `web-clipper`：网页抓取的技术细节

**脱敏处理方式**：
- 不提具体工具名 → 用"内容转换工具"、"资源获取工具"代替
- 不提具体平台 → 用"某阅读平台"、"公开资源站"代替
- 删除实现代码和技术细节 → 保留功能描述和使用场景

**关键洞察**：告诉用户"怎么写作"应该放在 workflows/，不是 skills/

---

## 合并过程中的关键决策

### 决策 1：目录结构必须保持

**曾考虑过**：把工具文件扁平化放在一起
```
# ❌ 错误
content-converter/tools/
├── epub2md.js
├── md2docx.py
├── ocr.py
```

**最终决定**：使用子目录保持原结构
```
# ✅ 正确
content-converter/tools/
├── epub/
│   ├── epub2md.js
│   └── package.json
├── md2docx/
│   ├── md2docx.py
│   └── requirements.txt
└── ocr/
    └── ocr.py
```

**理由**：
1. 原项目的 README/文档 还能对上
2. 依赖关系清晰
3. 未来拆分容易

### 决策 2：环境必须统一

**Before**：
```
skills/
├── epub2obsidian/node_modules/
├── md2docx/venv/
├── ocr-to-obsidian/venv/
...
```

**After**：
```
笔记专用/
├── .venv/              # 共享 Python
├── node_modules/       # 共享 Node
└── .agents/skills/
    └── content-converter/
        └── tools/
            ├── epub/       # 无私有 node_modules
            ├── md2docx/    # 无私有 venv
            └── ocr/        # 无私有依赖
```

**规则**：tools/ 子目录里**禁止**出现 node_modules/ 或 venv/

### 决策 3：SKILL.md 的写法

**采用场景化表格**：
```markdown
| 需求 | 场景 | 工具 |
|------|------|------|
| EPUB → Markdown | 场景1 | `tools/epub/epub2md.js` |
| Markdown → Word | 场景2 | `tools/md2docx/md2docx.py` |
| 图片/PDF → 文字 | 场景3 | `tools/ocr/ocr.py` |
```

**不采用**：
```markdown
# 场景1: EPUB 转 Markdown
...
# 场景2: Markdown 转 Word
...
```

**理由**：表格一目了然，用户快速找到对应场景

---

## 合并后验证

### 最终结构（2026-02-15）

```
.agents/
├── skills/ (12 个)
│   ├── agent-collaboration/      # 核心规范（Doc）
│   ├── baidu-pan-organizer/      # 独立工具
│   ├── content-converter/        # 内容转换（7 场景）
│   │   └── tools/
│   │       ├── epub/
│   │       ├── md2docx/
│   │       ├── ocr/
│   │       ├── pdf-translator/
│   │       ├── audio/
│   │       ├── weread/
│   │       └── video2gif/
│   ├── content-formatter/        # 内容排版（3 场景）
│   ├── directory-indexer/        # 独立工具
│   ├── find-skills/              # 独立工具
│   ├── learning-notes/           # 学习笔记（2 场景）
│   ├── mcp-builder/              # 独立工具
│   ├── notebooklm-uploader/      # 独立工具
│   ├── remotion-renderer/        # 独立工具
│   ├── resource-crawler/         # 资源抓取（3 场景）
│   ├── text-visualization/       # 文本可视化（3 场景）
│   └── uv-package-manager/       # 独立工具
└── workflows/ (2 个)
    ├── AI协作写作工作流.md
    └── 模型评测文章写作.md
```

### 验证清单
- [x] 34 个 Skill → 12 个 Skill + 2 个 Workflow
- [x] 所有 tools/ 子目录无私有 node_modules
- [x] 所有 tools/ 子目录无私有 venv
- [x] AGENTS.md 更新到 v3.0.0
- [x] agent-collaboration 导航文档更新
- [x] 11-Skill合并与拆分原则.md 创建

---

## 可用于文章的素材

### 金句
- "Skill 不是越多越好，而是越'整'越好"
- "用户想的是'我要转换内容'，不是'我要用 EPUB 工具'"
- "AI 变'笨'往往不是能力问题，而是管理问题"

### 数据
- 34 → 12（Skill 数量减少 65%）
- 7 → 1（内容转换类合并）
- 3 → 1（内容排版类合并）

### 对比图建议
1. 合并前的混乱目录（长列表）
2. 合并后的清晰结构（分类展示）
3. content-converter/tools/ 子目录结构
4. SKILL.md 场景表格设计

### 案例
- content-formatter：3 个排版 Skill 的合并
- content-converter：7 个转换工具的合并
- agent-collaboration：从工具到文档的降级
