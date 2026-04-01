# 论文阅读管理

**定位**: 学术论⽂的统⼀存储与中⼼  
**组织方式**: 每篇论⽂⼀个⽂件夹（参考 Zotero）  
**详细规范**: [[.agents/skills/.ai-rules/02-知识运营/论文管理/论文管理规范|论文管理规范]]

---

## 目录结构

```
论文阅读/
├── README.md                          # 本文件：管理规范说明
├── _INDEX-论文阅读.md                  # 论文索引：快速查阅所有论文
└── papers/                            # 论文文件夹集合
    └── {论文标题}/                     # 每篇论文一个文件夹
        ├── meta.json                  # 论文元数据（标题、作者、年份等）
        ├── original.pdf               # 原始英文PDF
        ├── translated-zh.pdf          # 中文翻译版（可选）
        ├── translated-dual.pdf        # 中英对照版（可选）
        ├── ocr.md                     # OCR提取的Markdown（可选）
        ├── images/                    # OCR提取的图片（可选）
        └── notes.md                   # 阅读笔记（可选）
```

---

## 快速开始

### 新增论文（7步流程）

```powershell
# 1. 创建论文文件夹
$paperName = "关键词_论文标题英文"
New-Item -ItemType Directory -Path "papers/$paperName"

# 2. 放入原始 PDF → original.pdf

# 3. 创建 meta.json（填写基本信息）

# 4. [可选] OCR 提取文本
uv run python .agents/skills/content-converter/tools/ocr/ocr.py "papers/$paperName/original.pdf" -o "papers/$paperName/"

# 5. [可选] PDF 翻译
uv run python .agents/skills/content-converter/tools/pdf-translator/pdf-translator.py "papers/$paperName/original.pdf"

# 6. [可选] 创建 notes.md（阅读笔记）

# 7. 在 _INDEX-论文阅读.md 中登记
```

---

## 文件夹命名规范

```
{缩写或关键词}_{标题英文}
```

**示例**：
- `LoRA_Low-Rank_Adaptation_of_Large_Language_Models`
- `Attention_Is_All_You_Need`
- `LinearAttention_Transformers_are_RNNs_Fast_Autoregressive_Transformers_with_Linear_Attention`

---

## 元数据 (meta.json)

```json
{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "year": 2020,
  "venue": "ICML 2020",
  "keywords": ["关键词1", "关键词2"],
  "tags": ["#LLM", "#Architecture"],
  "url": "https://arxiv.org/abs/...",
  "doi": null,
  "added_date": "2026-02-16",
  "translation_status": "未翻译",
  "ocr_status": "已完成",
  "reading_status": "未读",
  "rating": null,
  "notes": ""
}
```

---

## 文件说明

| 文件 | 必需 | 说明 |
|------|:----:|------|
| `meta.json` | ✅ | 论文元数据 |
| `original.pdf` | ✅ | 原始英文论文 |
| `ocr.md` | ❌ | OCR提取的文本 |
| `translated-zh.pdf` | ❌ | 中文翻译版 |
| `translated-dual.pdf` | ❌ | 中英对照版 |
| `images/` | ❌ | 提取的图片 |
| `notes.md` | ❌ | **阅读笔记** |

---

## 阅读笔记在哪写？

有两种方式：

### 方式一：论文文件夹内（推荐）
- 位置：`papers/{论文标题}/notes.md`
- 优点：笔记和论文在一起，方便对照
- 适合：单篇论文的深度阅读笔记

### 方式二：Areas 领域下（知识整合）
- 位置：`Areas/阅读方法/` 或新建 `Areas/论文研究/`
- 优点：同主题论文聚合，方便知识串联
- 适合：跨论文的主题研究、综述笔记

---

## 阅读笔记写作规范

### 公式书写规范（重要）

**所有数学公式必须使用 LaTeX 格式**，确保在 Obsidian 中正确渲染。

**正确示例**:
```markdown
- 行内公式：$O(n^2)$、$\phi(x) = \text{elu}(x) + 1$
- 块级公式：
$$
\text{Attention} = \text{softmax}\left(\frac{QK^T}{\sqrt{d}}\right) V
$$
```

**错误示例**:
```markdown
- 不要使用纯文本：O(n^2)、φ(x) = elu(x) + 1
- 不要使用代码块包裹公式
```

**常用 LaTeX 符号速查**:
| 符号 | LaTeX | 显示 |
|------|-------|------|
| 上标 | `$n^2$` | $n^2$ |
| 下标 | `$x_i$` | $x_i$ |
| 分数 | `$\frac{a}{b}$` | $\frac{a}{b}$ |
| 开方 | `$\sqrt{d}$` | $\sqrt{d}$ |
| 求和 | `$\sum_{i=1}^n$` | $\sum_{i=1}^n$ |
| 点乘 | `$Q \cdot K$` | $Q \cdot K$ |

详细规范参见 [[.agents/skills/.ai-rules/02-知识运营/论文管理/论文管理规范\|论文管理规范#阅读笔记写作规范]]

---

## 论文分类标签

| 标签 | 含义 |
|------|------|
| `#LLM` | 大语言模型 |
| `#PEFT` | 参数高效微调 |
| `#RAG` | 检索增强生成 |
| `#Agent` | AI 智能体 |
| `#Architecture` | 模型架构 |
| `#Attention` | 注意力机制 |
| `#Training` | 训练技术 |
| `#Inference` | 推理优化 |
| `#Multimodal` | 多模态 |

---

## 工具集成

| 工具 | 用途 | 命令 |
|------|------|------|
| OCR | 提取 PDF 文本 | `uv run python .agents/skills/content-converter/tools/ocr/ocr.py "<PDF>"` |
| PDF 翻译 | 英译中 | `uv run python .agents/skills/content-converter/tools/pdf-translator/pdf-translator.py "<PDF>"` |

---

## 关联文档

| 文档 | 说明 |
|------|------|
| [[_INDEX-论文阅读]] | 论文索引，查看所有已收录论文 |
| [[.agents/skills/.ai-rules/02-知识运营/论文管理/论文管理规范\|论文管理规范]] | 详细管理规范 |
| [[Areas/阅读方法/论文阅读工作流\|论文阅读工作流]] | 论文阅读方法论（SOP） |

---

**维护者**: 筱可  
**更新日期**: 2026-02-16
