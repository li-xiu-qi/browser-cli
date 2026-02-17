# OCR 工具 - 执行计划与文档

**工具**: PaddleOCR Layout Parsing  
**用途**: PDF/图片 → Markdown  
**状态**: 已部署，后台运行中

---

## 目录结构

```
.agents/skills/content-converter/tools/ocr/
├── ocr_async.py           # 主程序：异步 OCR，支持大文件拆分
├── pdf_splitter.py        # PDF 拆分器（PyMuPDF）
├── batch_convert.py       # 批量处理脚本（带状态记录）
├── convert_all.ps1        # PowerShell 批量脚本
├── run_ocr_background.py  # 后台运行入口
└── README.md              # 本文档
```

**输出目录**:
```
resources/books/
├── 00_待分类/             # OCR 输出位置
│   ├── <书名>.md
│   └── assets/<书名>/     # 图片资源
├── 01_哲学/               # 手动分类（待创建）
├── 02_经济学/
└── ...
```

---

## 当前执行状态

### 进行中
- **后台进程**: 运行中 (PID 需检查)
- **已完成**: 6 个文件
- **待处理**: 11 个 PDF
- **预计完成**: 30-50 分钟

### 已完成的文件
1. 高手必备的经济学思维系列套装 (EPUB) - 7.04 MB
2. 三桅帆科普系列丛书 - 0.07 MB
3. 中国哲学简史 - 0.15 MB
4. 伦理学与哲学的限度 - 0.17 MB
5. 纳瓦尔宝典 - 0.28 MB
6. 刻意练习 - 0.09 MB

---

## 使用指南

### 1. 单文件处理

```bash
# 小文件（<10MB）
uv run python .agents/skills/content-converter/tools/ocr/ocr_async.py "<pdf路径>"

# 大文件（自动拆分）
uv run python .agents/skills/content-converter/tools/ocr/ocr_async.py "<pdf路径>" --chunk-size 5
```

### 2. 后台批量处理

```bash
# 在项目根目录执行
python run_ocr_background.py

# 或在 PowerShell 中后台运行
Start-Process python -ArgumentList "run_ocr_background.py" -WindowStyle Hidden
```

### 3. 监控进度

```powershell
# 查看进程
Get-Process python | Where-Object { $_.CommandLine -like "*ocr*" }

# 查看日志
Get-Content .agents/skills/resources/downloads/books/ocr_progress.log -Tail 20

# 统计已完成
(Get-ChildItem resources/books/00_待分类 -Filter "*.md").Count
```

---

## 后续整理计划

### Phase 1: 等待转换完成
- 监控后台进程直到全部 17 个 PDF 处理完成
- 检查失败日志，重新处理失败的文件

### Phase 2: 移动到 Areas/书籍
- 将 `resources/books/00_待分类/` 中的文件移动到 `Areas/书籍/`
- 按分类整理到子目录（哲学/经济学/认知科学等）
- 更新个人书架索引

### Phase 3: 清理
- 删除源 PDF 文件（已上传到百度网盘）
- 清理临时文件和日志
- 归档处理记录

---

## 配置说明

### 默认配置
```python
# ocr_async.py
MAX_FILE_SIZE_MB = 10        # 超过此大小自动拆分
PAGES_PER_CHUNK = 5          # 每份 PDF 页数
OUTPUT_DIR = "resources/books/00_待分类"
```

### API 配置
```python
JOB_URL = "https://paddleocr.aistudio-app.com/api/v2/ocr/jobs"
TOKEN = "01ad53b81383d257dd9610407bf94d330315a502"
MODEL = "PaddleOCR-VL-1.5"
```

---

## 故障排除

| 问题 | 原因 | 解决 |
|------|------|------|
| 413 Request Too Large | 文件太大 | 自动拆分，减小 chunk-size |
| 处理超时 | API 响应慢 | 使用后台模式 |
| 图片未保存 | 网络问题 | 检查网络，重新下载 |
| 识别质量差 | PDF 扫描质量 | 手动校对或使用其他工具 |

---

## 依赖安装

```bash
# 必需
uv pip install pymupdf requests

# OCR 工具所在目录已添加到 Python 路径
# 无需额外安装 paddlepaddle
```

---

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-02-17 | 创建异步 OCR 工具，支持 PDF 拆分 |
| 2026-02-17 | 更改默认输出位置到 resources/books/ |
| 2026-02-17 | 添加后台批量处理功能 |

---

## 负责人

- **创建**: 小可 (AI)
- **使用**: 筱可
- **维护**: 参考 content-converter SKILL.md
