---
name: resource-crawler
description: 资源抓取专家。统一处理网络资源获取：网页内容抓取、音视频下载、Z-Library书籍下载。
---

# 资源抓取器

**定位**: 一站式网络资源获取解决方案  
**适用场景**: 
- 场景1: 网页内容抓取（文字、图片）
- 场景2: 音视频下载（YouTube、B站、播客等）

---

## 快速选择指南

| 你的需求 | 选择场景 | 工具路径 |
|----------|----------|----------|
| 抓取公众号文章/网页内容 | [[#场景1 网页内容抓取\|场景1]] | `tools/web-clipper/web_clipper.js` |
| 下载 YouTube/B站视频 | [[#场景2 音视频下载\|场景2]] | `tools/video-dl/download.py` |
| 下载播客音频 | [[#场景2 音视频下载\|场景2]] | `tools/video-dl/download.py -a` |
| Z-Library 搜索下载书籍 | [[#场景3 Z-Library书籍下载\|场景3]] | `tools/zlibrary/zlib_api.py` |

---

## 场景1: 网页内容抓取

**用途**: 抓取网页内容（尤其是微信公众号文章）并转换为 Markdown

**前置要求**: 共享 Node.js 环境（`playwright`, `jsdom`, `turndown`, `defuddle`）

**浏览器数据目录**（重要）:
- 使用项目统一的 `.agents/browser_user_data/` 目录
- 该目录保存浏览器登录状态，首次抓取微信文章前建议先登录微信网页版
- 多个 Skill 共享同一浏览器数据，避免重复登录

**使用方式**:

```bash
# 基础抓取（使用 v2 增强版，更好的图片处理）
node .agents/skills/resource-crawler/tools/web-clipper/web_clipper_v2.js "<URL>"

# 指定输出目录
node .agents/skills/resource-crawler/tools/web-clipper/web_clipper_v2.js "<URL>" "Areas/0_Inbox"

# 旧版本（可能遇到图片占位问题）
# node .agents/skills/resource-crawler/tools/web-clipper/web_clipper.js "<URL>"
```

**推荐**: 使用 `web_clipper_v2.js`，它修复了微信图片占位问题

**输出位置**: 默认 `cliper_datas/` 目录下

**特性**:
- 自动切换有头/无头模式应对反爬
- 针对微信公众号深度优化
- 自动处理样式和多模态内容
- **使用 `.agents/browser_user_data/` 共享浏览器数据**

---

## 场景2: 音视频下载

**用途**: 下载 YouTube、B站及其他支持站点的视频或音频

**前置要求**: Python 共享环境 + `yt-dlp` (`uv pip install yt-dlp`)

**使用方式**:

```bash
# 下载视频（默认最佳质量）
uv run python .agents/skills/resource-crawler/tools/video-dl/download.py "https://www.youtube.com/watch?v=VIDEO_ID"

# 指定质量
uv run python .agents/skills/resource-crawler/tools/video-dl/download.py "<URL>" -q 720p

# 仅下载音频（MP3，适合播客）
uv run python .agents/skills/resource-crawler/tools/video-dl/download.py "<URL>" -a

# 指定输出目录
uv run python .agents/skills/resource-crawler/tools/video-dl/download.py "<URL>" -o "./my_videos/"
```

**质量选项**:
| 选项 | 说明 |
|------|------|
| `best` | 最高可用质量（默认） |
| `1080p` | 全高清 |
| `720p` | 高清 |
| `480p` | 标清 |
| `worst` | 最低质量（文件最小） |

**支持站点**:
- **视频**: YouTube, Bilibili, Vimeo, TikTok, Twitter/X, Instagram
- **音频**: SoundCloud, Bandcamp, 播客
- **直播**: Twitch, YouTube Live（支持录制）

**输出位置**: 默认 `resources/downloads/media/`

---

## 场景3: Z-Library 书籍下载

**用途**: 搜索和下载 Z-Library 上的电子书籍

> ⚠️ **【重要提醒】使用本工具前，请务必先开启 VPN/代理！**
> 
> Z-Library 域名在国内无法直接访问，不开启代理会导致连接超时。
> 请确认代理已开启后再执行以下命令。

### 架构设计

采用**分离式登录架构**：

```
┌─────────────────────────────────────────────────────────────────┐
│  通用浏览器登录 (browser-login)                                    │
│  - 打开浏览器 → 用户手动登录 → 保存到 browser_user_data           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Z-Library API (zlib_api.py)                                     │
│  - 自动从 browser_user_data 提取 token                           │
│  - 保存到 zl_tokens.json 供后续使用                              │
│  - 执行搜索/下载操作                                              │
└─────────────────────────────────────────────────────────────────┘
```

**优点**:
- 登录与使用分离，各工具独立
- 浏览器数据共享，一处登录多处使用
- API 自动提取 token，无需手动操作

### 前置要求

- Python 共享环境 + `requests`, `playwright`
- **VPN/代理已开启**
- 首次使用需完成浏览器登录

### 使用方式

**Step 1: 首次登录（只需一次）**

```bash
# 方式1: 使用通用浏览器登录工具
uv run python .agents/tools/browser-login/login.py https://zh.zlib.li --name zlibrary

# 方式2: 使用 Z-Library 专用登录脚本（包装器，效果相同）
uv run python .agents/skills/resource-crawler/tools/zlibrary/login.py
```

**登录步骤**:
1. 浏览器自动打开 Z-Library 网站
2. **手动完成登录**（输入账号密码）
3. 看到已登录页面后，回到终端按 **Enter**
4. Cookie 自动保存到 `.agents/browser_user_data/`

**Step 2: 搜索下载书籍**

```bash
# AI 自动搜索并下载最佳匹配（自动提取 token）
uv run python .agents/skills/resource-crawler/tools/zlibrary/zlib_api.py auto "认知觉醒" --format pdf

# 搜索并包含评论信息
uv run python .agents/skills/resource-crawler/tools/zlibrary/zlib_api.py auto "认知觉醒" --with-reviews

# 仅搜索（返回 JSON 结果）
uv run python .agents/skills/resource-crawler/tools/zlibrary/zlib_api.py search "书名" 10

# 获取书籍评论
uv run python .agents/skills/resource-crawler/tools/zlibrary/zlib_api.py reviews <book_id> 5

# 交互式搜索（适合手动选择）
uv run python .agents/skills/resource-crawler/tools/zlibrary/zlib_search.py "书名"
```

### 文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 浏览器数据 | `.agents/browser_user_data/` | 持久化浏览器数据（各工具共享） |
| Token 文件 | `tools/zlibrary/config/zl_tokens.json` | 提取的 Z-Library 凭证 |
| 下载目录 | `resources/downloads/books/` | 下载的书籍 |

### 注意事项

1. **登录一次，长期使用**: Token 长期有效，除非账号退出或限额用尽
2. **每日限额**: 免费账户每日 10 本下载限额
3. **自动提取**: API 会自动从 browser_user_data 提取 token，无需手动配置
4. **多账号切换**: 如需切换账号，删除 `zl_tokens.json` 后重新登录

---

## 依赖安装速查

| 场景 | 依赖 | 安装命令 |
|------|------|----------|
| 场景1 | Node.js 包 | 已包含在根目录 `package.json` |
| 场景2 | yt-dlp | `uv pip install yt-dlp` |
| 场景2（可选） | FFmpeg | `winget install Gyan.FFmpeg` |
| 场景3 | requests, playwright | `uv pip install requests playwright` |

---

## 故障排除

### 场景1: 网页抓取失败

- 检查网络连接
- 确认目标网页是否需要登录
- 脚本会自动尝试有头模式

### 场景2: 音视频下载失败

```bash
# 更新 yt-dlp
uv pip install -U yt-dlp

# 验证安装
yt-dlp --version

# 查看可用格式
yt-dlp -F "<URL>"
```

### 场景3: Z-Library 登录失败或连接超时

- **检查代理是否已开启**（最常见原因）
- 检查网络连接
- 确认 Z-Library 域名是否可用
- 重新运行 `login.py` 获取新 Token
- 如遇 SSL 错误，尝试更换域名或更新域名配置

---

## 来源说明

本 Skill 合并自：
- `web-clipper`: 网页内容抓取
- `yt-dlp-downloader`: 音视频下载
- `zlibrary`: Z-Library 书籍下载
