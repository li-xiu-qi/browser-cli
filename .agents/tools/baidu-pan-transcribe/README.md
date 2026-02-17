# 百度网盘媒体文件转录文稿

通过百度网盘 API 获取音视频文件的 AI 转录文稿（简单听记）。

## 功能

- 获取网盘内视频/音频文件的转录文稿
- 支持查询转写状态
- 输出为 Markdown 格式（可选时间戳）
- 支持批量获取多个文件

## 前提条件

- 百度网盘 SVIP（超级会员）
- 音视频文件已上传至百度网盘并已转写完成

## 安装

```bash
cd .agents/tools/baidu-pan-transcribe

# 使用 uv 安装依赖
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

## 使用方法

### 1. 获取单个文件的转录文稿

```bash
python transcribe.py --fsid 465930705301366
```

### 2. 通过文件路径获取转录

```bash
python transcribe.py --path "/转存区域/课程/一堂会员日.mp4"
```

### 3. 批量获取多个文件

```bash
python transcribe.py --fsids 465930705301366,465930705301367,465930705301368
```

### 4. 输出带时间戳的详细格式

```bash
python transcribe.py --fsid 465930705301366 --format detailed
```

### 5. 保存到指定文件

```bash
python transcribe.py --fsid 465930705301366 --output "./transcript.md"
```

### 6. 检查转写状态

```bash
python transcribe.py --fsid 465930705301366 --check-only
```

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--fsid` | 单个文件 ID | `--fsid 465930705301366` |
| `--fsids` | 多个文件 ID（逗号分隔） | `--fsids 111,222,333` |
| `--path` | 文件完整路径 | `--path "/视频/课程.mp4"` |
| `--format` | 输出格式：`simple` 或 `detailed` | `--format detailed` |
| `--output` | 输出文件路径 | `--output "./output.md"` |
| `--check-only` | 仅检查转写状态 | `--check-only` |
| `--token` | 指定 access token（可选） | `--token "xxx"` |

## 输出示例

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

## 文件结构

```
baidu-pan-transcribe/
├── README.md
├── requirements.txt
├── transcribe.py      # 主脚本
└── config.py          # 配置文件
```

## 注意事项

1. **转写需要时间**：SVIP 上传音视频后，系统会自动转写，一般需要几分钟到几十分钟
2. **文件要求**：视频需有人物发言，纯音乐/无声音视频无法转写
3. **API 限制**：每次最多查询 10 个文件的详细信息
4. **Token 有效期**：access_token 有效期 30 天

## 相关文档

- [音频转文稿 API 文档](../../Projects/2026-02-百度网盘自动化集成/docs/audio-transcription-api.md)
- [MCP Server 指南](../../Projects/2026-02-百度网盘自动化集成/docs/mcp-server-guide.md)
