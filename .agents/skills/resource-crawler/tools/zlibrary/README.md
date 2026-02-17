# Z-Library 工具集

Z-Library 搜索下载工具，支持 AI 自动调用和人工交互。

## 快速开始

### 1. 登录

```powershell
.venv\Scripts\python.exe .agents\tools\zlibrary\login.py
```

按提示在浏览器中登录，然后回到终端按 Enter 保存。

### 2. 使用

**AI 自动模式**（推荐）：
```powershell
# 搜索并自动下载最佳 PDF
.venv\Scripts\python.exe .agents\tools\zlibrary\zlib_api.py auto "认知觉醒" --format pdf

# 包含评论信息
.venv\Scripts\python.exe .agents\tools\zlibrary\zlib_api.py auto "认知觉醒" --with-reviews
```

**交互式搜索**：
```powershell
.venv\Scripts\python.exe .agents\tools\zlibrary\zlib_search.py "认知觉醒"
```

**获取评论**：
```powershell
.venv\Scripts\python.exe .agents\tools\zlibrary\zlib_api.py reviews 11005990 5
```

## 文件说明

| 文件 | 用途 |
|------|------|
| `login.py` | 浏览器登录，保存 session |
| `zlib_api.py` | AI 调用入口（搜索/下载/评论） |
| `zlib_search.py` | 人工交互式搜索 |
| `zlib_reviews.py` | 获取书籍评论 |
| `Zlibrary.py` | Z-Library API 封装 |

## 配置

- **Token**: `config/zl_tokens.json`
- **Session**: `config/storage_state.json`
- **下载目录**: `resources/downloads/books/`
- **浏览器数据**: `.agents/browser_user_data/`

## 相关 Skill

- **Z-Library Skill**: `.agents/skills/zlibrary/SKILL.md`
- **NotebookLM Uploader**: `.agents/skills/notebooklm-uploader/SKILL.md`
