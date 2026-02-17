---
name: content-converter
description: 内容转换专家。统一处理各种格式转换需求：EPUB→Markdown、Markdown→Word、图片/PDF→文字(OCR)、PDF翻译、音视频转文字、微信读书→PDF、视频→GIF。
---

# 内容转换器

**定位**: 一站式内容格式转换解决方案  
**适用场景**: 任何需要将内容从一种格式转换为另一种格式的需求

---

## 快速选择指南

| 你的需求 | 使用场景 | 工具路径 |
|----------|----------|----------|
| EPUB 电子书 → Markdown | [[#场景1 EPUB 转 Markdown\|场景1]] | `tools/epub/epub2md.js` |
| Markdown → Word (.docx) | [[#场景2 Markdown 转 Word\|场景2]] | `tools/md2docx/md2docx.py` |
| 图片/PDF → 文字 | [[#场景3 OCR 文字识别\|场景3]] | `tools/ocr/ocr.py` |
| 英文 PDF → 中文 PDF | [[#场景4 PDF 翻译\|场景4]] | `tools/pdf-translator/pdf-translator.py` |
| 音视频 → 文字 | [[#场景5 音视频转文字\|场景5]] | `tools/audio/audio-transcribe.js` |
| 微信读书 → PDF | [[#场景6 微信读书转 PDF\|场景6]] | `tools/weread/weread2pdf.js` |
| 视频 → GIF | [[#场景7 视频转 GIF\|场景7]] | `tools/video2gif/README.md` |

---

## 场景1: EPUB 转 Markdown

**用途**: 将 EPUB 电子书导入 Obsidian，生成带 Frontmatter 的 Markdown 笔记

**前置要求**: 共享 Node.js 环境（`adm-zip`, `fast-xml-parser`, `node-html-markdown`）

**使用方式**:

```bash
# 基础转换
node .agents/skills/content-converter/tools/epub/epub2md.js "<epub路径>"

# 带分类和标签
node .agents/skills/content-converter/tools/epub/epub2md.js "<epub路径>" --category "技术" --tags "编程,AI"

# 指定输出目录
node .agents/skills/content-converter/tools/epub/epub2md.js "<epub路径>" --output "resources/books/00_待分类"
```

**输出位置**: 默认 `resources/books/00_待分类/<书名>.md`

**特殊说明**:
- 自动提取书名、作者等元数据
- 图片保存到 `assets/<书名>/` 目录
- 合并为单个 Markdown 文件（符合 Obsidian 习惯）

---

## 场景2: Markdown 转 Word

**用途**: 将 Markdown 文档导出为带样式的 Word 文档

**前置要求**: 已安装 `pandoc`，Python 共享环境

**使用方式**:

```bash
# 基础转换
uv run python .agents/skills/content-converter/tools/md2docx/md2docx.py "<input.md>" "<output.docx>"

# 使用自定义模板
uv run python .agents/skills/content-converter/tools/md2docx/md2docx.py "<input.md>" "<output.docx>" --ref "template.docx"

# 指定图片资源路径
uv run python .agents/skills/content-converter/tools/md2docx/md2docx.py "<input.md>" "<output.docx>" --resource-path "./images"
```

**特性**:
- 自动优化表格宽度
- 支持自定义 Word 模板
- 自动处理图片路径

---

## 场景3: OCR 文字识别

**用途**: 将 PDF 书籍或图片转换为 Markdown，支持大文件自动拆分和后台处理

**前置要求**: Python 共享环境 + PyMuPDF (`uv pip install pymupdf`)

**工具路径**: `.agents/skills/content-converter/tools/ocr/ocr_async.py`

**使用方式**:

```bash
# 单文件识别（小文件 <10MB）
uv run python .agents/skills/content-converter/tools/ocr/ocr_async.py "<PDF路径>"

# 指定输出目录
uv run python .agents/skills/content-converter/tools/ocr/ocr_async.py "<PDF路径>" -o "resources/books/00_待分类"

# 不保存图片（使用远程链接）
uv run python .agents/skills/content-converter/tools/ocr/ocr_async.py "<PDF路径>" --no-images

# 调整 PDF 拆分页数（默认 5 页/份）
uv run python .agents/skills/content-converter/tools/ocr/ocr_async.py "<PDF路径>" --chunk-size 3
```

**后台批量处理**:

```bash
# 启动后台进程处理整个目录
python run_ocr_background.py

# 或在 PowerShell 中
Start-Process python -ArgumentList "run_ocr_background.py" -WindowStyle Hidden
```

**输出位置**: 
- 默认: `resources/books/00_待分类/<书名>.md`
- 图片: `resources/books/00_待分类/assets/<书名>/`

**特性**:
- **自动拆分**: 大 PDF (>10MB) 自动拆分为 5 页/份处理，避免 413 错误
- **异步处理**: 后台轮询 API 结果，适合长时间任务
- **断点续传**: 后台脚本会记录处理状态
- **自动清理**: 转换成功后自动删除源 PDF

**输出目录规范**:

```
resources/books/
├── 00_待分类/          # OCR 输出目录
│   ├── <书名>.md
│   └── assets/
│       └── <书名>/     # 书籍图片
└── ...
```

---

## 场景4: PDF 翻译

**用途**: 将英文学术论文翻译为中文，保留公式和排版

**前置要求**: `uv tool install pdf2zh`（PDFMathTranslate）

**使用方式**:

```bash
# 单文件翻译（默认 Google 翻译）
uv run python .agents/skills/content-converter/tools/pdf-translator/pdf-translator.py "<英文PDF>"

# 批量翻译
uv run python .agents/skills/content-converter/tools/pdf-translator/pdf-translator.py --batch "papers/"

# 使用 DeepL（需 API Key）
uv run python .agents/skills/content-converter/tools/pdf-translator/pdf-translator.py "<PDF>" -s deepl

# 翻译特定页码
uv run python .agents/skills/content-converter/tools/pdf-translator/pdf-translator.py "<PDF>" -p "1-10"
```

**输出文件**:
- `<原文件名>-zh.pdf` - 纯中文翻译版
- `<原文件名>-dual.pdf` - 中英对照版

**集成工作流**: `resources/论文阅读/`

---

## 场景5: 音视频转文字

**用途**: 将录音、视频转换为文字笔记（基于通义听悟 API）

**前置要求**: Node.js 共享环境（`playwright`）+ 通义听悟账号

**使用方式**:

```bash
# 完整流水线（自动上传+转写+导出）
node .agents/skills/content-converter/tools/audio/audio-transcribe.js "<文件或目录>"

# 单文件转录
node .agents/skills/content-converter/tools/audio/core-transcribe.js "<音频路径>"

# 批量导出
node .agents/skills/content-converter/tools/audio/batch-export.js

# 清理记录
node .agents/skills/content-converter/tools/audio/batch-delete.js
```

**支持格式**:
- 音频: mp3, wav, m4a, wma, aac, ogg, amr, flac, aiff（最大 500MB）
- 视频: mp4, wmv, m4v, flv, rmvb, dat, mov, mkv, webm, avi, mpeg, 3gp, ogg（最大 6GB）

**输出位置**: `datas/` 或脚本配置目录

**注意**: 首次使用需运行登录模式获取 Cookie

---

## 场景6: 微信读书转 PDF

**用途**: 将微信读书内容抓取并转换为 A4 PDF

**前置要求**: Node.js 共享环境（`playwright`, `pdf-lib`, `sharp`）

**使用方式**:

```bash
# 登录（首次使用必须）
node .agents/skills/content-converter/tools/weread/weread2pdf.js login

# 抓取短篇（前台运行）
node .agents/skills/content-converter/tools/weread/weread2pdf.js crawl "<微信读书URL>"

# 抓取长篇（后台运行，避免超时）
node .agents/skills/content-converter/tools/weread/weread2pdf.js crawl "<URL>" -bg

# 保留中间图片
node .agents/skills/content-converter/tools/weread/weread2pdf.js crawl "<URL>" --keep-images
```

**输出位置**: `tools/output/book_[ID]/book_result.pdf`

**注意**:
- 首次使用必须先 `login` 扫码
- 抓取过程会弹出浏览器窗口，请勿关闭
- 支持断点续传

---

## 场景7: 视频转 GIF

**用途**: 将演示视频转为 GIF 插入 Markdown 文章，适配微信公众号、知乎等平台

**前置要求**: 已安装 `ffmpeg` 和 `ffprobe`

### 根据视频时长选择压缩策略

| 视频时长 | 推荐参数 | 预期大小 | 适用场景 |
|---------|---------|---------|---------|
| < 20秒 | fps=4, scale=720px, 128色 | 2-5 MB | 短演示、动画 |
| 20-40秒 | fps=3, scale=480px, 64色 | 2-4 MB | 中等长度演示 |
| 40-70秒 | fps=2, scale=360px, 32色 | 2-3 MB | 长演示、代码流程 |

### 常用命令

```bash
# 轻度压缩（短视频 <20s，保持较好质量）
ffmpeg -i input.mp4 -vf "fps=4,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse" -loop 0 output.gif

# 中度压缩（中等视频 20-40s）
ffmpeg -vf "fps=3,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=64[p];[s1][p]paletteuse=dither=bayer" -loop 0 output.gif

# 重度压缩（长视频 >40s，文件必须 <5MB）
ffmpeg -i input.mp4 -vf "fps=2,scale=360:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=32[p];[s1][p]paletteuse=dither=bayer" -loop 0 output.gif
```

### 批量处理脚本

```powershell
# PowerShell 批量转换当前目录所有 mp4
Get-ChildItem *.mp4 | ForEach-Object {
    $duration = & ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 $_.Name
    $seconds = [int]$duration
    
    if ($seconds -lt 20) {
        $fps = 4; $scale = 720; $colors = 128
    } elseif ($seconds -lt 40) {
        $fps = 3; $scale = 480; $colors = 64
    } else {
        $fps = 2; $scale = 360; $colors = 32
    }
    
    $output = $_.BaseName + ".gif"
    ffmpeg -i $_.Name -vf "fps=$fps,scale=$scale:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=$colors[p];[s1][p]paletteuse=dither=bayer" -loop 0 $output -y
    
    $size = [math]::Round((Get-Item $output).Length / 1MB, 2)
    Write-Host "$output : $size MB"
}
```

### 质量检查清单

- [ ] 文件大小 < 5MB（微信公众号）
- [ ] 帧数 < 300
- [ ] 动效流畅，关键信息可见
- [ ] 无明显的颜色断层或模糊

### 故障排除

| 问题 | 原因 | 解决方案 |
|-----|------|---------|
| 文件仍 >5MB | 视频太长或分辨率太高 | 降低 fps 到 2，缩小 scale 到 360px |
| 颜色失真严重 | 颜色数太少 | 增加 max_colors 到 64 或 128 |
| 动作卡顿 | fps 太低 | 适当提高 fps（如 2→3），同时缩小尺寸 |
| 文字看不清 | 分辨率压缩过度 | 保持 scale=480px 以上，牺牲 fps |

---

## 依赖安装速查

| 场景 | 依赖 | 安装命令 |
|------|------|----------|
| 场景1 | Node.js 包 | 已包含在根目录 `package.json` |
| 场景2 | Pandoc | 官网下载安装 |
| 场景3 | PaddleOCR | `uv pip install paddlepaddle paddleocr` |
| 场景4 | pdf2zh | `uv tool install pdf2zh` |
| 场景5 | Playwright | 已包含在根目录 `package.json` |
| 场景6 | Playwright | 已包含在根目录 `package.json` |
| 场景7 | FFmpeg | 官网下载安装 |

---

## 通用原则

### 输出目录规范

所有转换工具默认输出到以下位置：

```
笔记专用/
├── 0_Inbox/              # 临时输出，待整理
├── Areas/书籍/           # EPUB 转换输出
├── Areas/笔记/           # OCR 输出
├── resources/论文阅读/translated/  # PDF 翻译输出
└── [工具目录]/output/    # 各工具默认输出
```

### 文件命名规范

转换后的文件建议使用以下命名格式：

```
[日期]_[来源]_[主题].[扩展名]

示例:
- 2024-01-15_三体_刘慈欣.md
- 2024-01-15_周报_项目进度.docx
- 2024-01-15_会议记录_产品评审.md
```

---

## 故障排除

### 常见问题

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| OCR 识别率低 | 手写体/复杂排版 | 人工校对 |
| PDF 翻译卡住 | 首次运行需下载模型 | 等待下载完成 |
| 微信读书抓取失败 | Cookie 过期 | 重新运行 `login` |
| Markdown 转 Word 乱码 | 编码问题 | 确保文件为 UTF-8 |
| 音视频转写失败 | API 限制 | 检查通义听悟配额 |

---

## 来源说明

本 Skill 合并自：
- `epub2obsidian`: EPUB 转 Markdown
- `md2docx`: Markdown 转 Word
- `ocr-to-obsidian`: OCR 文字识别
- `pdf-translator`: PDF 翻译
- `tongyi-tingwu`: 音视频转文字
- `wechat-book-to-pdf`: 微信读书转 PDF
- `video-to-gif`: 视频转 GIF
