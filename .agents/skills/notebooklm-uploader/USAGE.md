# Z-Library to NotebookLM 使用指南

## 快速开始

### 1. 环境检查

确保依赖已安装：

```powershell
.venv\Scripts\python.exe .agents\skills\notebooklm-uploader\check_env.py
```

### 2. 登录 Z-Library

运行登录脚本，在浏览器中完成登录：

```powershell
.venv\Scripts\python.exe .agents\tools\zlibrary\login.py
```

**操作步骤**：
1. 浏览器会自动打开 Z-Library 网站
2. 手动完成登录
3. 登录成功后，**直接关闭浏览器窗口**
4. 脚本会自动检测浏览器关闭，保存 session 并退出
5. 保存位置：`.agents/tools/zlibrary/config/zl_tokens.json`

### 3. 搜索书籍

使用搜索功能查找书籍：

```powershell
# 使用新的 zlibrary 工具
.venv\Scripts\python.exe .agents\tools\zlibrary\zlib_search.py "开口之后"

# 或 AI 自动模式
.venv\Scripts\python.exe .agents\tools\zlibrary\zlib_api.py auto "开口之后"
```

搜索结果会显示：
- 书名
- 作者
- 年份
- 格式（PDF/EPUB）
- 大小
- 评分
- 书籍链接

### 4. 下载并上传到 NotebookLM

提供 Z-Library 书籍链接，自动下载并上传：

```powershell
.venv\Scripts\python.exe .agents\skills\notebooklm-uploader\scripts\upload.py "https://zh.zlib.li/book/xxxxx"
```

**注意**: upload.py 会自动使用 `.agents/tools/zlibrary/config/` 中的登录凭证

## 目录结构

```
.agents/tools/zlibrary/
├── login.py                  # 登录脚本
├── zlib_api.py               # AI API（搜索下载）
├── zlib_search.py            # 交互式搜索
├── zlib_reviews.py           # 评论获取
├── Zlibrary.py               # Z-Library API 封装
└── config/
    ├── storage_state.json    # 登录 session（自动保存）
    └── zl_tokens.json        # API token（自动提取）

.agents/skills/notebooklm-uploader/
├── scripts/
│   ├── upload.py             # 下载并上传到 NotebookLM
│   └── convert_epub.py       # EPUB 转 Markdown
├── docs/
│   ├── get_token_from_browser.py  # Token 获取指南
│   ├── TROUBLESHOOTING.md    # 故障排查
│   └── WORKFLOW.md           # 工作流说明
├── archive/                   # 归档的旧脚本
├── temp/                      # 临时文件
├── Zlibrary.py               # Z-Library API
├── search.py                 # 匿名搜索（无需登录）
├── search_with_login.py      # 登录后搜索（推荐）
├── check_env.py              # 环境检查
├── USAGE.md                  # 本文件
└── SKILL.md                  # AI Skill 规范

# 共享浏览器数据目录（所有 Skill 共用）
.agents/browser_user_data/                   # 浏览器持久化数据

# 下载目录
resources/downloads/books/                   # 下载的书籍
```

## 工作流程

```
登录 (login.py)
    ↓
浏览器打开 Z-Library → 用户登录 → 保存 session
    ↓
搜索 (search_with_login.py)
    ↓
使用 session 搜索书籍 → 显示结果列表
    ↓
下载并上传 (upload.py)
    ↓
使用 session 下载书籍 → 转换格式 → 上传到 NotebookLM
```

## 注意事项

1. **必须先登录** - 搜索和下载都需要有效的登录 session
2. **浏览器数据共享** - 使用 `.agents/browser_user_data/` 作为共享浏览器数据目录（所有需要浏览器的工具共用）
3. **合法使用** - 仅下载拥有合法访问权限的资源
4. **NotebookLM CLI** - 如需上传到 NotebookLM，需要先安装：`npm install -g notebooklm`

## 故障排查

### Q: 提示"未找到登录 session"
A: 运行 `.venv\Scripts\python.exe .agents\tools\zlibrary\login.py` 完成登录

### Q: 搜索失败
A: 检查网络连接，确认 Z-Library 网站可访问

### Q: 下载失败
A: 可能是 session 过期，重新运行登录脚本

### Q: 找不到浏览器数据目录
A: 确保 `.agents/browser_user_data/` 目录存在且有写入权限，且已完成登录
