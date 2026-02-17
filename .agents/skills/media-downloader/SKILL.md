---
name: media-downloader
description: |
  智能媒体下载器。聚合搜索 Pexels、Unsplash、Pixabay 等免费图库，下载高清图片和视频素材。
  支持 YouTube 视频下载、智能剪辑、自动元数据管理。
  
  触发词: "下载图片", "找视频", "download images", "find video", "/media", "搜索配图"
version: 2.0.0
---

# 🎬 Media Downloader - 智能媒体下载器

一站式媒体资源搜索与下载工具。支持多个免费图库聚合搜索、YouTube 下载、视频剪辑，自动管理版权元数据。

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🖼️ **聚合搜索** | 同时搜索 Pexels、Unsplash、Pixabay 三大图库 |
| 📹 **视频素材** | 免费商用视频片段搜索下载 |
| 📺 **YouTube 下载** | 支持时间段裁剪、音频提取 |
| ✂️ **智能剪辑** | 自动裁剪视频到指定时长 |
| 📝 **元数据管理** | 自动创建版权信息文件 (`.meta.json`) |
| 🌍 **中英双语** | 支持中英文搜索关键词 |

---

## 🚀 快速开始

### 1. 配置 API Key

编辑 `.env` 文件：

```bash
# Pexels (推荐) - https://www.pexels.com/api/
PEXELS_API_KEY=your_key_here

# Unsplash (可选) - https://unsplash.com/developers
UNSPLASH_ACCESS_KEY=your_key_here

# Pixabay (可选) - https://pixabay.com/api/docs/
PIXABAY_API_KEY=your_key_here
```

### 2. 检查配置

```bash
python media_cli.py status
```

### 3. 开始使用

```bash
# 下载 5 张猫咪图片
python media_cli.py image "cute cats" -n 5

# 搜索视频
python media_cli.py search "ocean waves" -t video

# 下载 YouTube 视频
python media_cli.py youtube "https://youtube.com/watch?v=xxx" -s 60 -e 120
```

---

## 💬 自然语言使用

直接告诉我你想要什么：

| 你说... | 我会... |
|---------|---------|
| "下载 5 张星空的图片" | 搜索并下载高清星空图片 |
| "找一些适合做 PPT 的商务图片" | 推荐并下载商务场景图片 |
| "下载这个 YouTube 视频的前 30 秒" | 下载并自动剪辑 |
| "找一段海浪的视频素材" | 搜索免费海浪视频 |

---

## 📋 CLI 命令参考

### 搜索媒体

```bash
python media_cli.py search <关键词> [选项]

选项:
  -t, --type      类型: image|video|all (默认: all)
  -n, --count     结果数量 (默认: 5)
  -p, --providers 指定提供商: pexels,unsplash,pixabay

示例:
  python media_cli.py search "nature" -t image -n 10
  python media_cli.py search "city" -p pexels,unsplash
```

### 下载图片

```bash
python media_cli.py image <关键词> [选项]

选项:
  -n, --count     下载数量 (默认: 5)
  -o, --output    输出目录 (默认: downloads)

示例:
  python media_cli.py image "coffee workspace" -n 5 -o ./images
```

### 下载视频素材

```bash
python media_cli.py video <关键词> [选项]

选项:
  -n, --count     下载数量 (默认: 3)
  -d, --duration  目标时长(秒)，超过则自动剪辑
  -o, --output    输出目录

示例:
  python media_cli.py video "sunset" -n 3 -d 30
```

### YouTube 下载

```bash
python media_cli.py youtube <URL> [选项]

选项:
  -s, --start     开始时间(秒)
  -e, --end       结束时间(秒)
  -a, --audio-only 仅下载音频
  -o, --output    输出目录

示例:
  # 下载完整视频
  python media_cli.py youtube "https://youtube.com/watch?v=xxx"
  
  # 下载 1:30-2:00 片段
  python media_cli.py youtube "https://youtube.com/watch?v=xxx" -s 90 -e 120
  
  # 仅下载音频
  python media_cli.py youtube "https://youtube.com/watch?v=xxx" -a
```

### 视频剪辑

```bash
python media_cli.py trim <输入文件> [选项]

选项:
  -s, --start     开始时间(秒)
  -e, --end       结束时间(秒)
  -d, --duration  目标时长(秒，从中间截取)
  -o, --output    输出文件

示例:
  # 截取 10-30 秒
  python media_cli.py trim video.mp4 -s 10 -e 30
  
  # 截取中间 30 秒
  python media_cli.py trim video.mp4 -d 30
```

---

## 📁 输出结构

下载的文件会自动保存到 `downloads/` 目录，并附带元数据文件：

```
downloads/
├── coffee_workspace_1_pexels.jpg
├── coffee_workspace_1_pexels.jpg.meta.json  # 元数据
├── coffee_workspace_2_unsplash.jpg
├── coffee_workspace_2_unsplash.jpg.meta.json
└── ...
```

### 元数据文件格式

```json
{
  "source": "pexels",
  "type": "image",
  "id": "12345",
  "url": "https://www.pexels.com/photo/12345/",
  "author": "John Doe",
  "author_url": "https://www.pexels.com/@johndoe",
  "width": 1920,
  "height": 1080,
  "license": "Free for commercial use",
  "attribution": "Photo by John Doe on Pexels",
  "downloaded_at": "2026-02-16T15:30:00"
}
```

---

## ⚙️ 高级配置

### 支持的图库

| 图库 | 图片 | 视频 | 需要署名 | 免费额度 |
|------|------|------|---------|---------|
| Pexels | ✅ | ✅ | 否 | 200/hour |
| Unsplash | ✅ | ❌ | ✅ | 50/hour |
| Pixabay | ✅ | ✅ | 否 | 100/min |

### 环境变量

除了 `.env` 文件，也支持系统环境变量：

```bash
export PEXELS_API_KEY=your_key
export UNSPLASH_ACCESS_KEY=your_key
export PIXABAY_API_KEY=your_key
```

---

## 🛠️ 依赖安装

### 必需依赖

```bash
# Python 依赖
pip install requests

# 或使用 uv
uv pip install requests
```

### 可选依赖

```bash
# YouTube 下载
pip install yt-dlp

# 视频剪辑 (系统包)
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
# Windows: https://ffmpeg.org/download.html
```

---

## 📄 版权说明

所有下载的素材均来自免费商用图库：

- **Pexels**: 免费商用，无需署名（推荐署名）
- **Unsplash**: 免费商用，需要署名
- **Pixabay**: 免费商用，无需署名

元数据文件中的 `attribution` 字段提供了标准的署名格式，请在使用图片时遵守各平台的使用条款。

---

## 🔄 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.0.0 | 2026-02-16 | 重构：模块化架构、新增元数据管理、改进 CLI |
| 1.0.0 | 2026-02-15 | 初始版本 |

---

**开始使用吧！直接告诉我你想要什么图片或视频！** 🎬
