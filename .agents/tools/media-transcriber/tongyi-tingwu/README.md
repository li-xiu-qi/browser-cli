# 通义听悟 API 自动化工具

这套脚本利用通义听悟（通义千问音视频速读）的 API，实现视频/音频的自动转文字、导出 Markdown 笔记以及云端记录清理。

## 目录结构

```
tongyi-tingwu/
├── config.js               # 配置文件（Cookie、Token）
├── common.js               # 公共模块（API 封装、工具函数）
├── pipeline_core_wrapper.js # 上传核心逻辑（被其他脚本引用）
├── pipeline.js             # 批量上传工具
├── core_transcribe.js      # 全自动转录工具（上传+等待+导出+清理）
├── batch_export.js         # 批量导出云端记录
├── batch_delete.js         # 批量删除云端记录
├── login_handler.js        # 自动登录获取 Cookie
├── datas/                  # 数据目录（Cookie 存储）
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

### 2. 获取 Cookie（推荐方式）

运行自动登录工具：

```bash
node login_handler.js
```

- 会自动打开浏览器
- 扫码或账号密码登录
- 登录成功后自动保存 Cookie 到 `datas/cookies.json`

### 3. 开始使用

#### 场景一：全自动转录（推荐）

上传 → 等待转写 → 导出 Markdown → 删除云端记录，一键完成：

```bash
# 转录单个文件
node core_transcribe.js ./会议录音.mp3

# 指定输出目录
node core_transcribe.js ./课程视频.mp4 ./笔记
```

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
| `login_handler.js` | 自动登录获取 Cookie | 首次使用或 Cookie 过期 |
| `core_transcribe.js` | 全自动流程 | 单个文件，追求一键完成 |
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
// 方式1: 自动获取（推荐）
// 运行 login_handler.js 后自动保存到 datas/cookies.json

// 方式2: 手动配置（备用）
const DEFAULT_COOKIE = "你的_COOKIE_字符串";
const XSRF_TOKEN = "你的_XSRF_TOKEN";
```

## 注意事项

1. **Cookie 有效期**：Cookie 会过期，如果脚本报错提示认证失败，请重新运行 `login_handler.js` 获取最新 Cookie

2. **配额限制**：通义听悟云端最多保存 50 个记录，`pipeline.js` 默认开启 `AUTO_DELETE_MODE`，会在配额满时自动导出并清理旧记录

3. **自动转码**：视频文件会自动转换为 OGG 音频以加速上传（需要 FFmpeg 已安装）

4. **API 变动**：这些是非官方 API，如果通义千问更新了接口，脚本可能会失效

## 依赖

- Node.js 18+
- Playwright（用于自动登录）
- FFmpeg（可选，用于视频转音频）
