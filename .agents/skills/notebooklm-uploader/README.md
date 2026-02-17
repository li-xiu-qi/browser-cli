# Z-Library to NotebookLM

自动从 Z-Library 下载书籍并上传到 Google NotebookLM。

## 快速开始

### 1. 环境检查
```powershell
.venv\Scripts\python.exe .agents\skills\notebooklm-uploader\check_env.py
```

### 2. 登录 Z-Library
```powershell
# 1. 登录 Z-Library（只需一次）
.venv\Scripts\python.exe .agents\tools\zlibrary\login.py
```

1. 浏览器自动打开 Z-Library
2. 手动完成登录
3. **关闭浏览器窗口**，脚本自动保存 session

### 3. 搜索书籍
```powershell
.venv\Scripts\python.exe .agents\tools\zlibrary\zlib_api.py auto "书名" --format pdf
```

### 4. 下载并上传到 NotebookLM
```powershell
.venv\Scripts\python.exe .agents\skills\notebooklm-uploader\scripts\upload.py "https://zh.zlib.li/book/xxxxx"
```

## 文件说明

### Z-Library 工具 (.agents/tools/zlibrary/)

| 文件 | 说明 |
|------|------|
| `login.py` | 登录脚本 |
| `zlib_api.py` | AI API（搜索、下载、评论） |
| `zlib_search.py` | 交互式搜索 |
| `zlib_reviews.py` | 评论获取 |
| `Zlibrary.py` | Z-Library API 封装 |

### NotebookLM 集成 (.agents/skills/notebooklm-uploader/)

| 文件 | 说明 |
|------|------|
| `scripts/upload.py` | 下载并上传到 NotebookLM |
| `scripts/convert_epub.py` | EPUB 转 Markdown |

## 配置目录

- **Session**: `.agents/tools/zlibrary/config/storage_state.json`
- **Token**: `.agents/tools/zlibrary/config/zl_tokens.json`
- **浏览器数据**: `.agents/browser_user_data/`
- **下载目录**: `resources/downloads/books/`

## 详细文档

- [使用指南](USAGE.md)
- [AI Skill 规范](SKILL.md)
- [故障排查](docs/TROUBLESHOOTING.md)

## 更新日志

### 2026-02-15
- 修复 `login.py` 浏览器关闭检测问题（使用普通浏览器模式 + 持久化上下文）
- 整理文件结构，将冗余脚本移至 `archive/` 目录
- 更新文档，修正路径引用
