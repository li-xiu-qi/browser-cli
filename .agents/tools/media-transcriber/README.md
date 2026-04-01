# 音视频转录文稿工具集

集合了百度网盘和阿里通义听悟两个平台的音视频转录能力，根据文件大小和时长自动选择最优方案。

## 入口校准

- `tongyi-tingwu/` 是通义听悟的正式主线
- `../content-converter/audio/` 里有一份历史镜像脚本，但它和 `tongyi-tingwu/` 重复，不应再被当成独立入口
- 真正涉及通义听悟上传、导出、Cookie、当前浏览器会话排障时，默认落到 [tongyi-tingwu/README.md](./tongyi-tingwu/README.md)
- 通义听悟当前默认是“持久化会话复用”主线：共享快照落 `.runtime/browser-session/qianwen.json`，工具实际使用的 cookie 落 `tongyi-tingwu/datas/cookies.json`
- 已验证的稳定做法已经单独沉淀成 [通义听悟-稳定转录SOP](./tongyi-tingwu/通义听悟-稳定转录SOP.md)

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
├── transcribe-youtube-tongyi.bat # YouTube 下载加通义听悟转录
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
# 当前更推荐：直接从 browser-cli 承接千问会话
.\seed-cookies-from-browser-cli.cmd

# 或者使用统一会话目录里的 JSON
.\seed-cookies-from-browser-session.cmd ".runtime\browser-session\qianwen.json"

# 当前会话不可用时，再走独立浏览器登录
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

### 示例 6：YouTube 下载后直接转录
```powershell
.\transcribe-youtube-tongyi.bat "https://www.youtube.com/watch?v=kwSVtQ7dziU" "resources\downloads\media\podcasts\no-priors-karpathy" "no-priors-code-agents-autoresearch-loopy-era-andrej-karpathy"
```

## 🔧 配置说明

### 百度网盘 Token
Token 会自动从以下位置读取：
- `Projects/2026-02-百度网盘自动化集成/.token_info.json`

### 通义听悟 Cookie
当前更推荐先复用 `browser-cli` 或其他浏览器会话的登录态：

```bash
cd tongyi-tingwu
.\ensure-session.cmd
```

如果需要刷新，再运行：

```bash
cd tongyi-tingwu
.\seed-cookies-from-browser-cli.cmd
```

如果当前会话和 `browser-cli` 都不可用，再运行：

```bash
cd tongyi-tingwu
node login_handler.js
```

补充说明：

- 目标页面更建议看 `https://www.qianwen.com/discover/audioread`
- 共享浏览器会话快照约定为 `.runtime/browser-session/qianwen.json`
- `datas/cookies.json` 支持浏览器导出的 cookies 数组
- `config.js` 会自动从 cookies 中提取 `XSRF-TOKEN`
- `datas/cookies.json` 属于本地敏感登录态，仓库只保留 `cookies.example.json`
- 浏览器会话 JSON 的统一暂存目录约定为 `.runtime/browser-session/<tool>.json`
- 当前默认不是每次都重新抓 cookie，而是先复用 `datas/cookies.json`
- 如果当前激活浏览器页面已经出现上传 UI，但工具侧仍返回 `NOT_LOGIN`，先用 `ensure_session.js` 看登录校验结果，再决定是否刷新 cookie；不要先重写上传器，也不要先切到本地模型
- 如果想少记细节，直接看 [tongyi-tingwu/通义听悟-稳定转录SOP.md](./tongyi-tingwu/通义听悟-稳定转录SOP.md)

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
- [通义听悟稳定转录 SOP](./tongyi-tingwu/通义听悟-稳定转录SOP.md)

## 🐛 故障排除

| 问题 | 解决方案 |
|------|---------|
| 百度网盘提示 Token 过期 | 重新获取 access_token |
| 通义听悟提示 Cookie 失效或返回 `NOT_LOGIN` | 先运行 `ensure-session.cmd` 看持久化 `datas/cookies.json` 是否仍有效。只有校验失败时，才重新执行 `seed-cookies-from-browser-cli.cmd`，或导入统一会话文件，再不行才运行 `login_handler.js`。若页面已登录但工具仍报 `NOT_LOGIN`，以鉴权接口结果为准，不要只看上传 UI。 |
| 文件太大无法上传 | 根据大小选择合适平台 |
| 转写结果为空 | 检查是否 SVIP / 转写是否完成 |

---

**维护者**: 筱可  
**创建日期**: 2026-02-15
