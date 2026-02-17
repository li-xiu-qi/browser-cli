# Skill 合并与拆分原则

**定位**: 指导何时合并 Skill、何时保持独立，避免 Skill 泛滥或过度臃肿  
**适用范围**: `.agents/skills/` 目录下的所有 Skill

---

## 核心原则

### 合并的驱动力

| 信号 | 说明 | 行动 |
|------|------|------|
| **总是同时使用** | 用户调用 A 时 90% 会调用 B | 考虑合并 |
| **概念重叠** | 两个 Skill 教授的是同一类知识的不同侧面 | 考虑合并 |
| **维护负担** | 更新 A 时必须同步更新 B | 考虑合并 |
| **用户困惑** | 用户不知道该选 A 还是 B | 考虑合并 |

### 保持独立的驱动力

| 信号 | 说明 | 行动 |
|------|------|------|
| **独立价值** | 用户可能单独使用 A 而不需要 B | 保持独立 |
| **不同触发条件** | A 和 B 的激活场景完全不同 | 保持独立 |
| **不同受众** | A 给开发者用，B 给写作者用 | 保持独立 |
| **组合灵活性** | A+B、A+C、B+D 都是有效组合 | 保持独立 |

---

## 当前 Skill 分析

### 现有 20 个 Skill 分类

| 类别 | Skill 数量 | 列表 |
|------|-----------|------|
| **核心基础设施** | 1 | agent-collaboration |
| **知识库管理** | 1 | learning-notes |
| **写作与排版** | 1 | content-formatter |
| **内容转换** | 2 | content-converter, resource-crawler |
| **数据获取** | 0 | （已合并到 resource-crawler） |
| **可视化** | 1 | text-visualization |
| **开发工具** | 4 | uv-package-manager, mcp-builder, find-skills, remotion-renderer |
| **其他** | 3 | baidu-pan-organizer, notebooklm-uploader, remotion-best-practices |

### 已完成的合并

| 合并后 Skill | 原 Skill 列表 | 目录结构 |
|-------------|--------------|----------|
| `content-formatter` | obsidian-markdown-formatter, wechat-markdown-publisher, text-polisher | 无 tools，纯规范 |
| `content-converter` | epub2obsidian, md2docx, ocr-to-obsidian, pdf-translator, tongyi-tingwu, wechat-book-to-pdf, video-to-gif | `tools/{原skill名}/` |
| `learning-notes` | course-note-taker, case-study-collector | 无 tools，纯规范 |

### 迁移到工作流

| 工作流 | 原 Skill |
|--------|----------|
| `workflows/AI协作写作工作流.md` | ai-writing-collaborator |

### 迁移到规范

| 规范文档 | 原 Skill |
|----------|----------|
| `agent-collaboration/02-知识运营/知识库管理.md` | knowledge-base-manager |

---

## 建议合并的 Skill

### 1. 排版类合并（高优先级）

**候选**: `obsidian-markdown-formatter` + `wechat-markdown-publisher` + `text-polisher`

**理由**:
- 三者都是"内容格式化/排版"，概念高度重叠
- 模型评测文章写作时这三个工具/规范总是配合使用
- 用户困惑："我该用哪个排版 skill？"

**合并后**: `content-formatter`
- 场景1: Obsidian 笔记排版
- 场景2: 公众号发布排版  
- 场景3: 转写文稿润色

**保留独立**: `ai-writing-collaborator`（写作流程）和 `course-note-taker`（课程笔记模板）保持独立，因为它们是"写作方法"而非"排版规范"。

### 2. 知识库管理类合并（中优先级）

**已完成**: `knowledge-base-manager` + `obsidian-vault-manager` → `agent-collaboration/02-知识运营/知识库管理.md`

**理由**:
- `knowledge-base-manager` 描述中已包含"笔记模板管理、附件规范检查"
- `obsidian-vault-manager` 的附件管理规范已合并到知识库管理文档
- `knowledge-indexing` 只是命名规范，完全可以作为知识库管理的一个章节

**合并后**: `knowledge-base-manager`
- 子章节1: PARA 方法论实践
- 子章节2: 笔记模板管理
- 子章节3: 索引命名规范（原 knowledge-indexing）
- 子章节4: 附件规范检查
- 子章节: Vault 结构管理与附件规范（已合并 obsidian-vault-manager）

**已合并**: `case-study-collector` 已合并到 `learning-notes` 的"场景2: 案例收集"

### 3. 百度网盘工具合并（低优先级）

**候选**: `baidu-pan-organizer` + `baidu-pan-transcribe`（tools 中的工具）

**理由**:
- 都是百度网盘相关功能
- 但功能差异大：一个是文件整理，一个是音频转写

**建议**: 暂不合并，保持独立。如果后续增加更多百度网盘功能，再考虑创建 `baidu-pan-toolkit`。

---

## 建议保持独立的 Skill（但建立关联）

这些 Skill 看似相关，但应该保持独立，通过 SKILL.md 中的"关联 Skill"部分建立链接：

| Skill A | Skill B | 保持独立理由 | 关联方式 |
|---------|---------|-------------|----------|
| `ai-writing-collaborator` | `course-note-taker` | 不同写作场景（通用写作 vs 课程笔记） | A 的文档中链接 B |
| `模型评测文章写作工作流` | `AI协作写作工作流` | 不同写作类型（评测报告 vs 通用文章） | 工作流之间的关联 |
| `content-converter` (场景7) | `模型评测文章写作工作流` | 视频转 GIF 工具被写作指南引用 | 工作流中组合使用 |
| `content-converter` | `resource-crawler` (场景3) | 格式转换 vs 书籍下载 | 工作流中组合使用 |
| `resource-crawler` (场景1) | `resource-crawler` (场景2) | 同一 Skill 不同场景 | 网页抓取 vs 音视频下载 |

---

## 合并操作步骤

### Step 1: 选择主 Skill
选择内容最全面、引用最多、URL 最稳定的作为主 Skill。

### Step 2: 保持目录结构（重要！）

**原则：合并时不打散原 Skill 的目录结构，保持清晰的子目录组织**

```
主-skill/
├── SKILL.md              # 统一入口，包含各场景说明
└── tools/                # 工具目录
    ├── 场景1/            # 原 skill-a 的工具
    │   ├── tool.js
    │   └── lib/
    ├── 场景2/            # 原 skill-b 的工具
    │   ├── tool.py
    │   └── config/
    └── 场景3/            # 原 skill-c 的工具（只有命令则放 README.md）
        └── README.md
```

**禁止的做法**：
```
 不要这样：
tools/
├── tool1.js          # 所有文件平铺，来源不明
├── tool2.py
├── tool3.js
└── ...

 应该这样：
tools/
├── skill-a/          # 子目录明确标识来源
│   └── tool1.js
├── skill-b/
│   └── tool2.py
└── skill-c/
    └── README.md
```

### Step 3: 内容迁移
将被合并 Skill 的核心内容迁移到主 Skill 的对应章节：

```markdown
## 场景 X: [原 Skill 名称]

### 适用条件
[原 Skill 的触发条件]

### 操作步骤
[原 Skill 的核心指令]

### 工具路径
`tools/场景X/原工具名.js`

### 注意事项
[原 Skill 的注意事项]
```

### Step 4: 更新关联文档
- 修改主 SKILL.md，添加"多场景支持"说明
- 在被合并的 Skill 目录放置重定向说明（可选，保留一段时间）
- 更新所有引用该 skill 的文档路径

### Step 5: 更新入口导航
更新 `00-入口导航.md` 中的 Skill 列表。

### 示例：content-converter 的合并结构

```
content-converter/
├── SKILL.md
└── tools/
    ├── epub/               # 原 epub2obsidian
    │   └── epub2md.js
    ├── md2docx/            # 原 md2docx
    │   └── md2docx.py
    ├── ocr/                # 原 ocr-to-obsidian
    │   └── ocr.py
    ├── pdf-translator/     # 原 pdf-translator
    │   └── pdf-translator.py
    ├── audio/              # 原 tongyi-tingwu
    │   ├── audio-transcribe.js
    │   ├── core_transcribe.js
    │   ├── batch_export.js
    │   └── batch_delete.js
    ├── weread/             # 原 wechat-book-to-pdf
    │   └── weread2pdf.js
    └── video2gif/          # 原 video-to-gif
        └── README.md       # 纯命令行工具，记录命令
```

---

## 命名空间管理

### 反模式：过度拆分

```
 不推荐：
- markdown-bold-formatter      (太细)
- markdown-list-formatter      (太细)
- markdown-table-formatter     (太细)
```

### 正模式：适度聚合

```
 推荐：
- content-formatter            (合并后)
  - 场景1: 基础 Markdown 排版
  - 场景2: 公众号排版
  - 场景3: 转写文稿润色
```

---

## 决策流程图

```
发现潜在合并候选
       │
       ▼
   用户是否会单独使用 A？ ──是──▶ 保持独立
       │否
       ▼
   更新 A 时是否必须更新 B？ ──是──▶ 合并
       │否
       ▼
   概念上是否是同一类知识？ ──是──▶ 合并
       │否
       ▼
   用户是否困惑该选哪个？ ──是──▶ 合并或重命名
       │否
       ▼
   保持独立，建立关联链接
```

---

## 关联文档

- [[Skill开发规范]]: Skill 开发标准
- [[../00-基础规范/_入口导航]]: Skill 库导航
- [[../01-开发指南/规范体系管理|规范体系管理]]: 规范文档维护

