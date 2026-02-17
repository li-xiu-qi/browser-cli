# 百度网盘媒体文件转录文稿

通过百度网盘 API 上传音视频文件并获取 AI 转录文稿（简单听记）。

## 功能

- ✅ **本地上传文件**到百度网盘（支持秒传、分片上传）
- 获取网盘内视频/音频文件的转录文稿
- 支持查询转写状态
- 输出为 Markdown 格式（可选时间戳）
- 支持批量获取多个文件

## 前提条件

- 百度网盘 SVIP（超级会员）
- 音视频文件需有人物发言

## 安装

```bash
cd .agents/tools/media-transcriber/baidu-pan

# 使用 uv 安装依赖
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

## 使用方法

### 📤 上传文件（新增功能）

#### 1. 上传单个文件

```bash
python upload.py "./一堂课程.mp4"
```

#### 2. 上传到指定目录

```bash
python upload.py "./一堂课程.mp4" --remote-dir "/转存区域/课程"
```

#### 3. 上传并重命名

```bash
python upload.py "./一堂课程.mp4" --remote-name "会员日课程.mp4"
```

#### 4. 上传并等待转写完成

```bash
# 上传后自动等待转写完成，获取文稿
python upload.py "./一堂课程.mp4" --wait-transcript --timeout 60
```

**输出：**
```
准备上传: 一堂课程.mp4
  本地路径: ./一堂课程.mp4
  文件大小: 523.50 MB
  网盘路径: /一堂课程.mp4
计算文件 MD5...
预上传...
开始上传，共 131 个分片...
上传中... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 131/131
完成上传，创建文件...
✅ 上传成功！
文件ID: 465930705301366
等待转写完成（最多等待 60 分钟）...
⏳ 转写进行中... 已等待 5 分 30 秒
✅ 转写完成！
转录结果已保存: ./一堂课程.md
```

### 📥 获取转录文稿（文件已在网盘）

#### 获取单个文件的转录文稿

```bash
python transcribe.py --fsid 465930705301366
```

#### 通过文件路径获取转录

```bash
python transcribe.py --path "/转存区域/课程/一堂会员日.mp4"
```

#### 批量获取多个文件

```bash
python transcribe.py --fsids 465930705301366,465930705301367,465930705301368
```

#### 输出带时间戳的详细格式

```bash
python transcribe.py --fsid 465930705301366 --format detailed
```

#### 保存到指定文件

```bash
python transcribe.py --fsid 465930705301366 --output "./transcript.md"
```

#### 检查转写状态

```bash
python transcribe.py --fsid 465930705301366 --check-only
```

## 📋 命令行参数

### 上传脚本 (upload.py)

| 参数 | 说明 | 示例 |
|------|------|------|
| `file` | 要上传的本地文件路径 | `./video.mp4` |
| `--remote-dir` | 网盘目标目录 | `--remote-dir "/课程"` |
| `--remote-name` | 网盘文件名（可选） | `--remote-name "新名字.mp4"` |
| `--wait-transcript` | 上传后等待转写完成 | `--wait-transcript` |
| `--timeout` | 等待转写超时（分钟） | `--timeout 60` |
| `--token` | 指定 access token | `--token "xxx"` |

### 转录脚本 (transcribe.py)

| 参数 | 说明 | 示例 |
|------|------|------|
| `--fsid` | 单个文件 ID | `--fsid 465930705301366` |
| `--fsids` | 多个文件 ID（逗号分隔） | `--fsids 111,222,333` |
| `--path` | 文件完整路径 | `--path "/视频/课程.mp4"` |
| `--format` | 输出格式：`simple` 或 `detailed` | `--format detailed` |
| `--output` | 输出文件路径 | `--output "./output.md"` |
| `--check-only` | 仅检查转写状态 | `--check-only` |
| `--token` | 指定 access token | `--token "xxx"` |

## 📊 完整工作流程

### 场景 1：本地文件一键转录

```bash
# 上传 → 等待转写 → 获取文稿（一条龙）
python upload.py "./我的课程.mp4" --wait-transcript
```

### 场景 2：先上传，稍后获取文稿

```bash
# 1. 上传文件
python upload.py "./我的课程.mp4"
# 输出：文件ID: 465930705301366

# 2. 等待几分钟后，获取文稿
python transcribe.py --fsid 465930705301366 --output "./课程文稿.md"
```

### 场景 3：批量处理多个文件

```bash
# 使用 batch_transcribe.py
python batch_transcribe.py --scan-dir "/转存区域/课程" --output ./transcripts/
```

## 📁 文件结构

```
baidu-pan/
├── README.md                 # 本文档
├── requirements.txt          # Python 依赖
├── config.py                # 配置文件
├── upload.py                # ⭐ 上传文件脚本（新增）
├── transcribe.py            # 获取转录文稿
├── search_and_transcribe.py # 搜索并转录
├── batch_transcribe.py      # 批量转录
├── install.bat              # Windows 安装脚本
└── baidu-trans.bat          # 快速启动脚本
```

## 🚀 快速启动脚本

### Windows

```bash
# 上传到百度网盘
.venv\Scripts\python upload.py "./视频.mp4"

# 获取转录文稿
.venv\Scripts\python transcribe.py --fsid 123456
```

## 📄 输出示例

### Simple 格式
```markdown
# 一堂会员日0820

大家好，欢迎来到一堂会员日...

---
文件：一堂会员日0820.mp4
时长：120 分钟
转写状态：已完成
```

### Detailed 格式（带时间戳）
```markdown
# 一堂会员日0820

## 转录内容

[00:00:30] 大家好，欢迎来到一堂会员日
[00:01:20] 今天我们要讨论的主题是时间管理
[00:02:15] 首先，让我们看一下高效能人士的七个习惯
...

---
文件：一堂会员日0820.mp4
时长：120 分钟
转写状态：已完成
```

## ⚠️ 注意事项

1. **上传限制**
   - 单文件最大 4GB
   - 视频时长最长 4 小时
   - 支持分片上传，大文件也能上传

2. **转写需要时间**
   - SVIP 上传音视频后，系统会自动转写
   - 一般需要几分钟到几十分钟，取决于视频长度
   - 可以使用 `--wait-transcript` 自动等待

3. **文件要求**
   - 视频需有人物发言
   - 纯音乐/无声音视频无法转写
   - 支持格式：mp4, mov, avi, mkv, mp3, wav, m4a, aac 等

4. **秒传功能**
   - 如果文件已存在于百度网盘，会触发秒传
   - 秒传瞬间完成，无需等待上传

5. **API 限制**
   - 每次最多查询 10 个文件的详细信息
   - access_token 有效期 30 天

## 🔧 故障排除

| 问题 | 解决方案 |
|------|---------|
| 上传失败 | 检查网络连接和 Token 是否过期 |
| 转写结果为空 | 检查是否 SVIP、视频是否有人物发言 |
| 秒传失败 | 文件可能不存在于网盘，会转为正常上传 |
| 等待转写超时 | 视频较长，转写需要时间，可稍后手动获取 |

## 📚 相关文档

- [音频转文稿 API 文档](../../../Projects/2026-02-百度网盘自动化集成/docs/audio-transcription-api.md)
- [MCP Server 指南](../../../Projects/2026-02-百度网盘自动化集成/docs/mcp-server-guide.md)
- [百度网盘开放平台](https://pan.baidu.com/union)

---

**更新日期**: 2026-02-15  
**版本**: v0.2.0（新增上传功能）
