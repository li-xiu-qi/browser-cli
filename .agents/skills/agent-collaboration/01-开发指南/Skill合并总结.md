# Skill 合并总结

**日期**: 2026-02-15  
**原始 Skill 数**: 34  
**当前 Skill 数**: 15  
**工作流**: 2  
**总计减少**: 17 个 skill

---

## 合并结果一览

### 1. content-formatter（合并 3 个 skill）

**来源**:
- `obsidian-markdown-formatter`: Obsidian 排版规范
- `wechat-markdown-publisher`: 公众号发布适配
- `text-polisher`: 转写文稿润色

**结构**:
```
content-formatter/
└── SKILL.md          # 3 个场景：Obsidian排版/公众号适配/文稿润色
```

### 2. content-converter（合并 7 个 skill）

**来源**:
- `epub2obsidian`: EPUB 转 Markdown
- `md2docx`: Markdown 转 Word
- `ocr-to-obsidian`: OCR 文字识别
- `pdf-translator`: PDF 翻译
- `tongyi-tingwu`: 音视频转文字
- `wechat-book-to-pdf`: 微信读书转 PDF
- `video-to-gif`: 视频转 GIF

**结构**:
```
content-converter/
├── SKILL.md
└── tools/
    ├── epub/              # 原 epub2obsidian
    ├── md2docx/           # 原 md2docx
    ├── ocr/               # 原 ocr-to-obsidian
    ├── pdf-translator/    # 原 pdf-translator
    ├── audio/             # 原 tongyi-tingwu
    ├── weread/            # 原 wechat-book-to-pdf
    └── video2gif/         # 原 video-to-gif
```

### 3. learning-notes（合并 2 个 skill）

**来源**:
- `course-note-taker`: 沉浸式课程笔记
- `case-study-collector`: 结构化案例收集

**结构**:
```
learning-notes/
├── SKILL.md              # 3 个场景：课程笔记/商业案例/教学案例
└── templates/            # 可选模板目录
```

### 4. resource-crawler（合并 3 个 skill）

**来源**:
- `web-clipper`: 网页内容抓取
- `yt-dlp-downloader`: 音视频下载
- `zlibrary`: Z-Library 书籍下载

**结构**:
```
resource-crawler/
├── SKILL.md
└── tools/
    ├── web-clipper/       # 场景1: 网页抓取
    ├── video-dl/          # 场景2: 音视频下载
    └── zlibrary/          # 场景3: 书籍下载
```

### 5. agent-collaboration/知识库管理（合并 3 个 skill）

**来源**:
- `knowledge-base-manager`: 知识库管理基础规范
- `obsidian-vault-manager`: Vault 结构管理与附件规范
- `knowledge-indexing`: 索引命名规范

**位置**: `agent-collaboration/02-知识运营/知识库管理.md`

**章节**:
- 知识库架构（PARA + 技能库软连接）
- 附件管理规范
- 写作规范
- 索引命名规范
- 工作流
- 规范演进机制

### 6. text-visualization（合并 3 个 skill）

**来源**:
- `graphviz-best-practices`: Graphviz 图表最佳实践
- `html-table-templates`: HTML 表格模板库（50+模板）
- `json-canvas`: JSON Canvas 规范

**结构**:
```
text-visualization/
├── SKILL.md
└── templates/
    ├── graphviz/         # 场景1: Graphviz图表
    │   └── README.md
    ├── html-tables/      # 场景2: HTML表格
    │   ├── README.md
    │   ├── previews/     # 50+预览图
    │   └── sources/      # 50+HTML模板
    └── json-canvas/      # 场景3: JSON Canvas
        └── README.md
```

---

## 迁移到工作流（2 个）

| 工作流 | 来源 | 用途 |
|--------|------|------|
| `AI协作写作工作流.md` | ai-writing-collaborator | AI协作五步写作流程 |
| `模型评测文章写作工作流.md` | model-evaluator-writer | AI模型评测文章写作指南 |

---

## 保持独立的 Skill（15 个）

| Skill | 说明 |
|-------|------|
| agent-collaboration | 核心基础设施（含知识库管理规范） |
| baidu-pan-organizer | 百度网盘工具 |
| content-converter | 内容转换（已合并7个） |
| content-formatter | 内容排版（已合并3个） |
| find-skills | 发现技能 |
| text-visualization | 文本可视化（合并3个：Graphviz/HTML表格/Canvas） |
| learning-notes | 学习笔记（已合并2个） |
| mcp-builder | MCP构建 |
| notebooklm-uploader | NotebookLM上传 |
| remotion-renderer | Remotion视频渲染 |
| resource-crawler | 资源抓取（已合并3个） |
| uv-package-manager | UV包管理 |
| vscode-manager | VS Code管理规范 |

---

## 合并原则总结

### 应该合并的信号
1. **总是同时使用** - 调用 A 时 90% 会调用 B
2. **概念重叠** - 同一类知识的不同侧面
3. **维护负担** - 更新 A 必须同步更新 B
4. **用户困惑** - 不知道该选 A 还是 B

### 应该独立的信号
1. **独立价值** - 可能单独使用 A 而不需要 B
2. **不同触发条件** - 激活场景完全不同
3. **不同受众** - A 给开发者，B 给写作者
4. **组合灵活性** - A+B、A+C、B+D 都是有效组合

### 目录结构原则
**合并时必须保持子目录结构**：
```
skill-name/
├── SKILL.md
└── tools/
    ├── 场景1/            # 原 skill-a
    ├── 场景2/            # 原 skill-b
    └── 场景3/            # 原 skill-c
```

**禁止平铺**：
```
 不要这样：
tools/
├── tool1.js
├── tool2.py
└── ...
```

---

## 后续建议

当前 15 个 skill 结构清晰，不建议继续合并：

- **content-converter**: 7 个转换工具，结构良好
- **content-formatter**: 3 个排版规范，纯文档
- **learning-notes**: 2 个笔记类型，场景清晰
- **resource-crawler**: 3 个抓取工具，分类明确
- **agent-collaboration**: 知识库管理规范完整

其余 10 个 skill 都是独立功能领域，保持独立更有利于 AI 准确识别和使用。
