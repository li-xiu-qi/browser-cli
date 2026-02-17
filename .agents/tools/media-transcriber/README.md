# 音视频转录文稿工具集

集合了百度网盘和阿里通义听悟两个平台的音视频转录能力，根据文件大小和时长自动选择最优方案。

## 🎯 快速选择指南

| 你的情况 | 推荐方案 |
|---------|---------|
| 视频 > 4GB 或 > 4小时 | **通义听悟**（支持6GB/6小时） |
| 音频 > 500MB | **百度网盘**（支持4GB） |
| 文件已在百度网盘 | **百度网盘**（直接获取） |
| 本地文件快速转录 | **通义听悟**（一键上传） |
| 需要说话人分离 | **通义听悟** |
| 长期归档管理 | **百度网盘**（永久保存） |

## 📁 目录结构

```
media-transcriber/
├── README.md                 # 本文件
├── transcribe.py            # 统一入口脚本（自动选择平台）
├── transcribe.bat           # Windows 快速入口
├── transcribe-baidu.bat     # 百度网盘快速入口
├── transcribe-tongyi.bat    # 通义听悟快速入口
├── baidu-pan/               # 百度网盘转录工具
│   ├── README.md
│   ├── transcribe.py        # 获取转录文稿
│   ├── upload.py            # ⭐ 上传文件（新增）
│   ├── search_and_transcribe.py
│   ├── batch_transcribe.py
│   └── ...
└── tongyi-tingwu/           # 通义听悟转录工具
    ├── README.md
    ├── core_transcribe.js   # 通义听悟主脚本
    ├── pipeline.js
    └── ...
```

## 🚀 快速开始

### 方式一：统一入口（推荐）

```bash
# 自动根据文件大小选择平台
python transcribe.py "./我的视频.mp4"

# 强制使用指定平台
python transcribe.py "./我的视频.mp4" --provider baidu
python transcribe.py "./我的视频.mp4" --provider tongyi
```

### 方式二：直接使用各平台工具

#### 百度网盘 - 本地上传并转录（新增）
```bash
cd baidu-pan

# 上传本地文件
python upload.py "./本地视频.mp4"

# 上传并等待转写完成
python upload.py "./本地视频.mp4" --wait-transcript

# 上传到指定目录
python upload.py "./本地视频.mp4" --remote-dir "/转存区域/课程"
```

#### 百度网盘 - 获取已有文件转录
```bash
cd baidu-pan
python transcribe.py --fsid 465930705301366
python transcribe.py --path "/网盘路径/视频.mp4"
```

#### 通义听悟（本地文件）
```bash
cd tongyi-tingwu
node core_transcribe.js "./本地视频.mp4"
```

## 📊 平台能力对比

| 功能 | 百度网盘 | 通义听悟 |
|------|---------|---------|
| **视频大小** | 4GB | 6GB ✅ |
| **音频大小** | 4GB ✅ | 500MB |
| **视频时长** | 4小时 | 6小时 ✅ |
| **音频时长** | 4小时 | 6小时 ✅ |
| **本地上传** | ✅ | ✅ |
| **说话人分离** | ❌ | ✅ |
| **AI 摘要** | 简单 | 详细 ✅ |
| **章节速览** | ❌ | ✅ |
| **批量处理** | 10个/次 | 50个/次 ✅ |
| **永久保存** | ✅ | ❌（50个上限）|
| **官方 API** | ✅ | ❌（非官方）|

## ⚙️ 安装依赖

### 百度网盘工具
```bash
cd baidu-pan
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 通义听悟工具
```bash
cd tongyi-tingwu
npm install
# 首次使用需要登录
node login_handler.js
```

## 📝 使用示例

### 示例 1：自动选择平台
```bash
# 分析文件后自动选择最优平台
python transcribe.py "./一堂课程.mp4" --output ./notes/
```

### 示例 2：上传到百度网盘并转录
```bash
# 本地文件上传到百度网盘
python transcribe.py "./一堂课程.mp4" --provider baidu --upload

# 上传并等待转写完成
python transcribe.py "./一堂课程.mp4" --provider baidu --upload --wait
```

### 示例 3：批量处理文件夹
```bash
# 批量转录整个文件夹（自动分配平台）
python transcribe.py --batch "./课程/" --output ./transcripts/
```

### 示例 4：搜索网盘并转录
```bash
# 搜索网盘中的视频并获取转录
cd baidu-pan
python search_and_transcribe.py --search "一堂" --auto-transcribe 5
```

### 示例 5：通义听悟全自动流程
```bash
# 上传 → 转录 → 导出 → 清理（一键完成）
cd tongyi-tingwu
node core_transcribe.js "./会议录音.mp3" ./output/
```

## 🔧 配置说明

### 百度网盘 Token
Token 会自动从以下位置读取：
- `Projects/2026-02-百度网盘自动化集成/.token_info.json`

### 通义听悟 Cookie
首次使用需要运行：
```bash
cd tongyi-tingwu
node login_handler.js
```
扫码登录后会自动保存 cookie。

## ⚠️ 注意事项

1. **百度网盘**
   - 需要 SVIP（超级会员）
   - 支持本地上传到网盘（新增）
   - 转写需要时间（几分钟到几十分钟）
   - 支持秒传（文件已存在时瞬间完成）

2. **通义听悟**
   - 免费额度有限，超出需付费
   - 云端最多保存 50 个记录
   - 非官方 API，可能随时失效

3. **文件限制**
   - 百度网盘：视频/音频最大 4GB，时长 4 小时
   - 通义听悟：视频最大 6GB，音频最大 500MB，时长 6 小时

## 🤝 平台互补使用建议

**最佳实践流程：**

1. **新下载的大视频 (>4GB)** → 通义听悟
2. **已存在网盘的资料** → 百度网盘（直接获取）
3. **重要内容备份** → 通义听悟转写后，上传到网盘存档
4. **需要说话人分离** → 通义听悟
5. **长期归档管理** → 百度网盘（永久保存转录结果）

## 📚 详细文档

- [百度网盘工具详细文档](./baidu-pan/README.md)
- [通义听悟工具详细文档](./tongyi-tingwu/README.md)

## 🐛 故障排除

| 问题 | 解决方案 |
|------|---------|
| 百度网盘提示 Token 过期 | 重新获取 access_token |
| 通义听悟提示 Cookie 失效 | 重新运行 `login_handler.js` |
| 文件太大无法上传 | 根据大小选择合适平台 |
| 转写结果为空 | 检查是否 SVIP / 转写是否完成 |

---

**维护者**: 筱可  
**创建日期**: 2026-02-15
