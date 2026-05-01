---
name: wenyan-cli-ops
description: |
  Wenyan-CLI 项目运维总入口。涵盖项目介绍、Fork 分支策略、私有 patch 说明、
  服务器部署流程、公众号文章发布流程、故障排查。触发于任何涉及 wenyan-cli
  升级、patch、部署、发布、服务器维护的场景。
---

# Wenyan-CLI 项目运维

## 项目介绍

**Wenyan-CLI** 是一个将 Markdown 渲染为微信公众号风格 HTML 并一键发布到公众号草稿箱的 CLI 工具。

- **上游项目**：`https://github.com/caol64/wenyan-cli`（@caol64）
- **本组织 Fork**：`https://github.com/li-xiu-qi/wenyan-cli`
- **核心依赖**：`@wenyan-md/cli`（CLI 入口）、`@wenyan-md/core`（渲染核心）
- **Node.js**：v20.20.0（服务器），上游要求 >=22，但功能正常

### Wenyan-CLI 能做什么

1. **渲染**：将 Markdown 转为微信公众号风格的 HTML（支持多种主题）
2. **脚注**：自动将正文中的 `[文字](URL)` 链接转为上标编号脚注
3. **图片处理**：本地图片自动上传到微信素材库
4. **发布**：一键发布到微信公众号草稿箱

---

## 分支策略（重要）

```
upstream (caol64/wenyan-cli)
    └── main (上游原始分支，只读)
            │
            ▼  fork
    li-xiu-qi/wenyan-cli
            ├── main (同步上游，只读，不部署)
            └── xiaoke-customizations (私有功能分支，部署到服务器)
```

| 分支 | 用途 | 是否部署 |
|---|---|---|
| `upstream/main` | 上游原始代码 | — |
| `fork/main` | 仅同步上游更新，保持与 upstream 一致 | ❌ 不部署 |
| `fork/xiaoke-customizations` | 私有开发分支，包含所有自定义 patch 和主题 | ✅ 部署到服务器 |

**关键规则**：`main` 分支只用于同步上游，所有实际开发和部署都来自 `xiaoke-customizations`。

### 合并上游更新流程

```bash
# 1. 本地 main 同步上游
git checkout main
git fetch upstream
git merge --ff-only upstream/main

# 2. 合并到私有分支
git checkout xiaoke-customizations
git rebase main

# 3. 重新应用私有 patch（如有冲突）
# - import.meta.main → Node.js 兼容修复
# - digest 字段修复
# - URL 去重与 references 支持

# 4. 构建并部署
npm install && npm run build
# 部署到服务器...
```

---

## 我们的私有 Patch（xiaoke-customizations 分支）

### Patch 列表

| Patch | 文件 | 说明 | 状态 |
|---|---|---|---|
| **import.meta.main 兼容** | `dist/cli.js` | Node.js 不支持 `import.meta.main`（Bun/Deno 特性），改为 `fileURLToPath` 回退检测 | ✅ 已应用 |
| **digest 字段传递** | `core.js` + `wrapper.js` | frontmatter 的 `digest` 字段解析并传递给微信草稿 API | ✅ 已应用 |
| **URL 去重** | `core.js` | `addFootnotes` 使用 `Map` 记录已出现的 href，重复 URL 复用同一编号 | ✅ 已应用 |
| **references 支持** | `core.js` + `wrapper.js` | 解析 `references` frontmatter 数组，渲染到文末「参考来源」区块 | ✅ 已应用 |

### Patch 详情

#### 1. import.meta.main 兼容修复

上游使用 `import.meta.main` 判断是否是 CLI 直接执行，Node.js 不支持。修复为：

```javascript
// 修复前
if (import.meta.main) { ... }

// 修复后
import { fileURLToPath } from "url";
const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) { ... }
```

#### 2. digest 字段传递

```javascript
// core.js - handleFrontMatter
const { title, description, cover, author, source_url, digest, references } = attributes;
// ...
if (digest) result.digest = digest;

// wrapper.js - publishToWechatDraft
const { title, content, cover, author, source_url, digest, need_open_comment, only_fans_can_comment } = articleOptions;
// ...
const data = await wechatPublisher.publishToDraft(accessToken, {
  title, content, thumb_media_id: thumbMediaId, author,
  content_source_url: source_url,
  digest,  // ← 新增
  need_open_comment: need_open_comment ? 1 : 0,
  only_fans_can_comment: only_fans_can_comment ? 1 : 0
});
```

#### 3. URL 去重

```javascript
function addFootnotes(element, listStyle = false) {
  const footnotes = [];
  const hrefMap = new Map();  // ← 新增
  let footnoteIndex = 0;
  const links = element.querySelectorAll("a[href]");
  links.forEach((linkElement) => {
    const title = linkElement.textContent || linkElement.innerText;
    const href = linkElement.getAttribute("href") || "";
    let idx;
    if (hrefMap.has(href)) {  // ← 重复 URL 复用编号
      idx = hrefMap.get(href);
    } else {
      idx = ++footnoteIndex;
      hrefMap.set(href, idx);
      footnotes.push([idx, title, href]);
    }
    const footnoteMarker = element.ownerDocument.createElement("sup");
    footnoteMarker.setAttribute("class", "footnote");
    footnoteMarker.innerHTML = `[${idx}]`;
    linkElement.after(footnoteMarker);
  });
  // ...
}
```

#### 4. references 支持

在 frontmatter 中添加 `references` 数组，文末自动渲染「参考来源」区块：

```yaml
---
title: 文章标题
digest: "摘要"
references:
  - title: 来源名称
    url: https://example.com/article
  - title: 另一个来源
    url: https://example.com/another
---
```

渲染为 HTML：
```html
<hr>
<h3>参考来源</h3>
<section id="references">
  <p><span class="footnote-num">[1]</span>来源名称: <i>https://example.com/article</i></p>
  <p><span class="footnote-num">[2]</span>另一个来源: <i>https://example.com/another</i></p>
</section>
```

---

## 自定义主题

| 主题 | 文件 | 适用文章类型 |
|---|---|---|
| `xiaoke-default` | `themes/xiaoke-default.css` | 思辨/思考类/方法论长文 |
| `xiaoke-comparison` | `themes/xiaoke-comparison.css` | 对比/汇总/集合整理类文章 |

主题文件在 `xiaoke-customizations` 分支的 `themes/` 目录下维护。

---

## 服务器信息

| 配置 | 值 |
|---|---|
| **服务器** | 阿里云 ECS 北京 |
| **IP:端口** | `47.93.150.15:18317` |
| **systemd 服务** | `wenyan-cli.service` |
| **Node.js** | v20.20.0 |
| **API Key** | `kT6MOrUnPxB5z3FniyqnLRcaHq979C3x` |
| **公众号白名单** | 服务器公网 IP 已加入 |
| **环境变量文件** | `/etc/wenyan-cli.env` |

### 启动脚本

```bash
#!/usr/bin/env bash
set -euo pipefail
source /etc/wenyan-cli.env
mkdir -p /root/.config/wenyan-md
# 直接用 node 执行真实路径，避免 ESM 符号链接模块解析错误
CLI_PATH=$(readlink -f /usr/local/bin/wenyan)
exec /usr/bin/env node "$CLI_PATH" serve --port "${WENYAN_PORT:-3000}" --api-key "$WENYAN_API_KEY"
```

**关键**：`wenyan` 是符号链接，ESM 环境下直接执行会模块解析失败。必须用 `node $(readlink -f /usr/local/bin/wenyan)` 方式启动。

### 服务管理

```bash
# 检查状态
systemctl status wenyan-cli.service

# 重启
systemctl restart wenyan-cli.service

# 健康检查
curl -s http://localhost:18317/health
# 期望输出: {"status":"ok","service":"wenyan-cli","version":"2.0.8"}
```

---

## 部署流程

### 部署方式

由于服务器 `npm install` 容易超时/失败，采用「**本地构建 → 上传 dist/ + themes/ → 服务器 patch core.js**」的混合部署方式。

### 完整部署步骤

```bash
# ===== 1. 本地构建 =====
cd /path/to/wenyan-cli
git checkout xiaoke-customizations
npm install
npm run build

# ===== 2. 打包上传 =====
tar -czf wenyan-cli-deploy.tar.gz dist/ themes/ package.json
# 上传到服务器 /tmp/

# ===== 3. 服务器部署 =====
ssh root@47.93.150.15
systemctl stop wenyan-cli.service

# 备份旧版本
cp -r /usr/local/lib/node_modules/@wenyan-md/cli /usr/local/lib/node_modules/@wenyan-md/cli.bak

# 解压新版本
rm -rf /usr/local/lib/node_modules/@wenyan-md/cli
tar -xzf /tmp/wenyan-cli-deploy.tar.gz -C /usr/local/lib/node_modules/@wenyan-md/cli

# 重新安装生产依赖
cd /usr/local/lib/node_modules/@wenyan-md/cli
npm install --production

# 确保执行权限
chmod +x /usr/local/lib/node_modules/@wenyan-md/cli/dist/cli.js

# 重启服务
systemctl start wenyan-cli.service
systemctl is-active wenyan-cli.service

# 验证
curl -s http://localhost:18317/health
```

### 仅 Patch 更新（不升级版本）

如果只需要修改 `core.js` 或 `wrapper.js` 的 patch：

```bash
# 直接在服务器上编辑 patch 文件
vim /usr/local/lib/node_modules/@wenyan-md/cli/node_modules/@wenyan-md/core/dist/core.js
vim /usr/local/lib/node_modules/@wenyan-md/cli/node_modules/@wenyan-md/core/dist/wrapper.js

# 重启服务
systemctl restart wenyan-cli.service
```

---

## 发布流程（公众号文章）

### 前置要求

1. 文章 Markdown 文件包含完整 frontmatter
2. 图片使用相对路径 `./images/xxx.jpg`
3. 文件名避免中文和空格

### Frontmatter 规范

```yaml
---
title: "文章标题"
digest: "文章摘要，50-120字，用于朋友圈/会话转发卡片展示"
date: 2026-05-02
tags: [标签1, 标签2]
category: 观点评论
status: published
version: 1.0.2
author: 筱可AI          # 必须统一
cover: "./images/cover_fixed.jpg"
references:              # 可选，主动添加文末参考来源
  - title: 来源名称
    url: https://example.com/article
---
```

### 发布命令

**方式一：本地 Wenyan CLI（需配置 WECHAT_APP_ID / WECHAT_APP_SECRET）**

```bash
wenyan publish -f article.md -c themes/xiaoke-default.css
```

**方式二：Server 模式（推荐，白名单绑定服务器 IP）**

```bash
wenyan publish -f article.md \
  --server http://47.93.150.15:18317/api/wenyan \
  --api-key kT6MOrUnPxB5z3FniyqnLRcaHq979C3x
```

**方式三：服务器直接发布（通过 SSH）**

```bash
# 上传文章和图片到 /tmp/
# SSH 到服务器执行
cd /tmp && node $(readlink -f /usr/local/bin/wenyan) publish -f article.md \
  -c /usr/local/lib/node_modules/@wenyan-md/cli/themes/xiaoke-default.css
```

### 发布成功标志

输出包含 `Media ID`，表示已进入公众号草稿箱：
```
发布成功，Media ID: o1FjzOCh3dTOGu0e39dDHksPckU17g4vi8jraWbepcFCvO3YeuOOKhqP7frWJuc9
```

---

## 故障排查

### 服务无法启动（ESM 模块解析错误）

**症状**：`Error [ERR_MODULE_NOT_FOUND]` 或 `Cannot find module`

**原因**：`wenyan` 是符号链接，ESM 环境下 `import.meta.url` 解析路径错误

**修复**：启动脚本改用 `node $(readlink -f /usr/local/bin/wenyan) serve`

### 40113 图片上传失败

**症状**：发布时报错 `errcode: 40113`

**原因**：封面或正文图片格式不被微信接受（如 WebP、文件名含中文）

**修复**：
1. 所有图片转换为 JPG/PNG
2. 文件名用英文，避免中文和空格
3. 使用本地相对路径 `./images/xxx.jpg`

### digest 未传递

**症状**：公众号草稿的「摘要」字段为空

**原因**：上游 `core.js` / `wrapper.js` 未解析/传递 `digest` 字段

**修复**：确认 `core.js` 的 `handleFrontMatter` 和 `wrapper.js` 的 `publishToWechatDraft` 已 patch

### 重复 URL 生成多个脚注

**症状**：同一链接在文末出现多个编号

**原因**：`addFootnotes` 未对重复 href 去重

**修复**：确认 `core.js` 的 `addFootnotes` 使用了 `Map` 记录已出现的 href

### Node.js 版本警告

**症状**：`npm warn EBADENGINE Unsupported engine { required: { node: '>=22.19.0' } }`

**处理**：当前 Node.js v20.20.0 功能正常，可忽略此警告。如需升级，需测试兼容性。

---

## SSH 连接信息

| 配置 | 值 |
|---|---|
| **Host** | `47.93.150.15` |
| **Port** | `22` |
| **User** | `root` |
| **Password** | `@Li-xiaoke-server` |
| **Wenyan 安装路径** | `/usr/local/lib/node_modules/@wenyan-md/cli` |
| **主题路径** | `/usr/local/lib/node_modules/@wenyan-md/cli/themes/` |
| **core.js 路径** | `/usr/local/lib/node_modules/@wenyan-md/cli/node_modules/@wenyan-md/core/dist/core.js` |
| **wrapper.js 路径** | `/usr/local/lib/node_modules/@wenyan-md/cli/node_modules/@wenyan-md/core/dist/wrapper.js` |

---

## 更新记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-05-02 | v2.0.8 | 升级至上游 v2.0.8；修复 digest 传递；添加 URL 去重；添加 references 支持；修复 ESM 启动问题；发布文章验证通过 |
