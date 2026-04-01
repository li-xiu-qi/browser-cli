# 通义听悟 API 自动化工具

这套脚本利用通义听悟（通义千问音视频速读）的 API，实现视频/音频的自动转文字、导出 Markdown 笔记以及云端记录清理。

当前这套工具的登录态主线已经更新：

- 优先使用 `browser-cli` 自己的会话或其他浏览器会话导出的 cookie JSON
- 目标页面优先看 `https://www.qianwen.com/discover/audioread`
- 共享浏览器会话快照默认落到 `.runtime/browser-session/qianwen.json`
- 把 `qianwen.com` cookies 写到 `datas/cookies.json`
- 默认优先复用 `datas/cookies.json`，只有登录校验失败时才重新从 `browser-cli` 刷新
- `config.js` 会自动从 cookie 里提取 `XSRF-TOKEN`
- `login_handler.js` 仍保留，但现在是备用，不再是默认主线
- 登录是否真的可用，以 `/assistant/api/record/oss/token/get?c=tongyi-web` 的鉴权结果为准，不只看上传 UI
- `core_transcribe.js` 现在会先校验持久化会话，再决定是否刷新

稳定工作流已经单独整理成：

- [通义听悟-稳定转录SOP.md](./通义听悟-稳定转录SOP.md)

## 目录结构

```
tongyi-tingwu/
├── config.js               # 配置文件（Cookie、Token）
├── common.js               # 公共模块（API 封装、工具函数）
├── pipeline_core_wrapper.js # 上传核心逻辑（被其他脚本引用）
├── pipeline.js             # 批量上传工具
├── ensure_session.js       # 优先复用持久化 cookie，失效时再刷新
├── ensure-session.cmd      # 会话校验与刷新入口
├── core_transcribe.js      # 全自动转录工具（上传+等待+导出+清理）
├── batch_export.js         # 批量导出云端记录
├── batch_delete.js         # 批量删除云端记录
├── login_handler.js        # 备用：独立浏览器登录获取 Cookie
├── seed-cookies-from-browser-session.cmd
├── seed-cookies-from-browser-session.ps1 # 把浏览器会话导出的 cookies 导入 datas/cookies.json
├── seed-cookies-from-browser-cli.cmd     # 直接从 browser-cli 承接会话
├── datas/                  # 数据目录（本地 Cookie 存储，不提交真实内容）
├── node_modules/           # 依赖
└── README.md               # 本文档
```

## 🚀 快速开始

### 1. 准备环境

需要安装 Node.js 和 Playwright：

```bash
# 安装依赖
npm install
```

### 2. 获取 Cookie

#### 方式 A：浏览器会话导入，推荐

这是当前更推荐的路径。

适合场景：

- `browser-cli` 的 profile 已经登录了千问
- 或你已经拿到了可用的浏览器会话 cookie JSON
- 不想再开一个独立浏览器重复登录

建议顺序：

1. 在 `browser-cli` 或其他浏览器会话里打开 `https://www.qianwen.com/discover/audioread`
2. 确认页面已经进入真实上传界面，而不是登录页
3. 导出 storage-state 到 `.runtime/browser-session/qianwen.json`
4. 从该快照筛出 `qianwen.com` 相关 cookies，写入 `datas/cookies.json`
5. 后续默认直接复用 `datas/cookies.json`

重要补充：

- “能看到上传 UI” 只是第一层信号
- 最终判断以 `/assistant/api/record/oss/token/get?c=tongyi-web` 是否返回 `success=true` 为准
- 如果 `datas/cookies.json` 已经能通过这个校验，不要重复刷新 cookie
- 只有 `datas/cookies.json` 失效时，才重新执行 `seed-cookies-from-browser-cli.cmd`

如果你已经有浏览器会话导出的 cookie JSON，可以直接导入：

```powershell
.\seed-cookies-from-browser-session.cmd ".runtime\browser-session\qianwen.json"
```

默认只保留 `qianwen.com` 相关 cookies。  
如果你确实需要把 `aliyun.com` 相关 cookie 一起写入：

```powershell
.\seed-cookies-from-browser-session.cmd ".runtime\browser-session\qianwen.json" -KeepAliyun
```

如果你已经在 `browser-cli` 里登录了千问，更低摩擦的直达入口是：

```powershell
.\seed-cookies-from-browser-cli.cmd
```

如果确实需要把 `aliyun.com` 一并带进来：

```powershell
.\seed-cookies-from-browser-cli.cmd -KeepAliyun
```

补充约定：

- `datas/cookies.json` 是本地运行时文件
- `.runtime/browser-session/qianwen.json` 是共享浏览器会话快照
- 仓库里只保留格式参考文件 `datas/cookies.example.json`
- 不要提交真实登录态

### 2.1 标准会话链路

当前默认做法是：

1. `browser-cli` 维护浏览器会话
2. `seed-cookies-from-browser-cli.cmd` 导出 storage-state
3. 共享快照写到 `.runtime/browser-session/qianwen.json`
4. 下游工具把 `qianwen.com` cookies 写到 `datas/cookies.json`
5. `ensure_session.js` 先校验 `datas/cookies.json`
6. 只有校验失败时，才重新从 `browser-cli` 刷新

这条链路的重点是“会话文件复用”，不是“每次都重新抓 cookie”。

#### 方式 B：独立浏览器登录，备用

运行自动登录工具：

```bash
node login_handler.js
```

- 会自动打开浏览器
- 扫码或账号密码登录
- 登录成功后自动保存 Cookie 到 `datas/cookies.json`

这条路在以下情况更合适：

- 当前会话拿不到可用 cookie
- `browser-cli` 这边还没有登录千问
- 你就是想把这套工具和浏览器会话完全隔离

### 3. 开始使用

#### 场景一：全自动转录（推荐）

上传 → 等待转写 → 导出 Markdown → 删除云端记录，一键完成：

```bash
# 先校验持久化会话，只有失效时才刷新
node ensure_session.js

# 转录单个文件
node core_transcribe.js ./会议录音.mp3

# 指定输出目录
node core_transcribe.js ./课程视频.mp4 ./笔记
```

低摩擦 Windows 入口：

```powershell
cd ..\
.\transcribe-tongyi.bat "C:\path\to\audio-or-video.mp3" "resources\downloads\media\podcasts\sample"
```

#### 场景一补充：YouTube 直达转录

如果目标内容还在 YouTube，可以直接走下载加转录的一键链路：

```powershell
cd ..\
.\transcribe-youtube-tongyi.bat "https://www.youtube.com/watch?v=kwSVtQ7dziU" "resources\downloads\media\podcasts\no-priors-karpathy" "no-priors-code-agents-autoresearch-loopy-era-andrej-karpathy"
```

这条脚本会自动保留：

- 音频 `mp3`
- 元信息 `info.json`
- 字幕 `srt`
- 通义听悟导出的 Markdown

#### 场景二：批量上传（异步处理）

如果你有大量文件需要上传，批量上传更高效：

```bash
# 上传单个文件或整个文件夹
node pipeline.js ./录音文件夹 ./outputs

# 转写完成后，批量导出结果
node batch_export.js 50 ./outputs
```

#### 场景三：管理云端记录

```bash
# 导出云端已完成的记录
node batch_export.js 20 ./exports

# 清理云端记录释放空间
node batch_delete.js 10
```

## 脚本说明

| 脚本 | 功能 | 适用场景 |
|------|------|----------|
| `ensure_session.js` | 先复用持久化 cookie，失效时再刷新 | 希望把会话校验动作前置并显式执行 |
| `ensure-session.cmd` | `ensure_session.js` 的低摩擦入口 | Windows 下快速校验登录态 |
| `seed-cookies-from-browser-session.cmd` | 导入浏览器会话导出的 cookies | 已经有千问登录态时的主线 |
| `seed-cookies-from-browser-cli.cmd` | 直接从 browser-cli 导入 cookies | 已经在 browser-cli 里登录千问时的低摩擦主线 |
| `login_handler.js` | 自动登录获取 Cookie | 当前会话不可用时的备用路径 |
| `core_transcribe.js` | 全自动流程，内部会先确保会话可用 | 单个文件，追求一键完成 |
| `youtube_to_transcript.js` | 先下载 YouTube 音频和字幕，再导出通义听悟 Markdown | 视频链接还没落成本地文件时的直达入口 |
| `pipeline.js` | 批量上传 | 大量文件，异步处理 |
| `batch_export.js` | 批量导出 | 转写完成后下载结果 |
| `batch_delete.js` | 批量删除 | 释放云端空间 |

## 文件限制

- 单次最多上传 **50 个文件**
- 视频：mp4/wmv/m4v/flv/rmvb/dat/mov/mkv/webm/avi/mpeg/3gp/ogg，最大 **6GB**
- 音频：mp3/wav/m4a/wma/aac/ogg/amr/flac/aiff，最大 **500MB**
- 单个文件最长 **6 小时**

## 配置说明

编辑 `config.js`：

```javascript
// 方式1: 浏览器会话导入或 login_handler.js 自动保存
// datas/cookies.json 支持浏览器导出的 cookies 数组
// XSRF-TOKEN 会自动从 cookies.json 里提取
// 仓库只保留 datas/cookies.example.json 作为结构参考

// 方式2: 手动配置（备用）
const DEFAULT_COOKIE = "你的_COOKIE_字符串";
const XSRF_TOKEN = "你的_XSRF_TOKEN";
```

## 注意事项

1. **Cookie 有效期**：`datas/cookies.json` 现在是默认持久化登录态。只要它还能通过 `ensure_session.js` 校验，就继续复用；只有失效时，才重新执行 `seed-cookies-from-browser-cli.cmd` 或 `login_handler.js`

2. **配额限制**：通义听悟云端最多保存 50 个记录，`pipeline.js` 默认开启 `AUTO_DELETE_MODE`，会在配额满时自动导出并清理旧记录

3. **自动转码**：视频文件会自动转换为 OGG 音频以加速上传（需要 FFmpeg 已安装）

4. **API 变动**：这些是非官方 API，如果通义千问更新了接口，脚本可能会失效

5. **目标页面**：当前更建议以 `https://www.qianwen.com/discover/audioread` 作为登录态验证页，但真正决定是否可上传的仍是鉴权接口返回
6. **排障顺序**：先跑 `ensure_session.js` 看持久化 cookie 是否仍有效，再决定要不要刷新；不要把“重新抓 cookie”当第一反应
7. **状态字段**：等待转写完成时要以返回记录里的 `recordStatus` 为准，不要只看 `status`

## 推荐入口

如果只是想快速执行，不想记内部脚本名，默认记这三个入口就够了：

1. `..\transcribe-tongyi.bat`：本地文件直达转录
2. `..\transcribe-youtube-tongyi.bat`：YouTube 下载加转录
3. `.\ensure-session.cmd`：只检查当前持久化会话是否还能继续复用

## 依赖

- Node.js 18+
- Playwright（用于自动登录）
- FFmpeg（可选，用于视频转音频）
