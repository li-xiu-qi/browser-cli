---
name: wechat-publishing
description: Publish Markdown articles to WeChat Official Account drafts using wenyan-cli. Trigger when users mention publishing to WeChat, 公众号发布, wenyan, markdown to WeChat, or entering WeChat draft box. Make sure to use this skill when the article is finalized and ready for publishing, especially when users mention wechat, 微信公众号, 草稿箱, or wenyan publish.
---

# wechat-publishing

使用 wenyan-cli 将 Markdown 文章发布到微信公众号草稿箱。

## 适用场景

- Markdown 文章已定稿，需要进入公众号草稿箱
- 需要标准化处理封面、图片、HTML 渲染
- 需要通过自动化脚本或 CI/CD 发布
- 需要保留发布历史记录和可复现流程

## 不适用的场景

- 文章还在起稿阶段
- 需要边写边预览
- 只需要简单的复制粘贴

## 前置要求

- 已安装 wenyan-cli（本地或服务器部署）
- 已配置微信公众号环境变量或 Server 模式 API Key
- Markdown 文件包含完整的 frontmatter

## 核心工作流

### 1. 内容检查

发布前必须检查：

```markdown
---
title: "文章标题"
digest: "文章摘要，50-100字，用于公众号列表展示"
cover: "./assets/cover.png"
author: "筱可AI"
share_text: "分享文章时使用的话术，1-2句话"
---
```

**必须项**：`title`、`digest`、`author`
- `digest`：转发摘要，50-120字，用于朋友圈/会话转发卡片展示。**wenyan 默认不传递此字段，需确保服务器版本已 patch `digest` 支持（见下方运维教训）**
- `author`：统一写 `筱可AI`
**可选项**：`cover`（不写则 Wenyan 默认取正文第一张图）、`source_url`（原文链接）

### 2. 本地模式发布

适合：单人手动发布，本机已配置公众号白名单

```bash
wenyan publish -f article.md
```

环境变量要求：
- `WECHAT_APP_ID`
- `WECHAT_APP_SECRET`

### 3. 主题选择

根据文章类型选择对应 CSS 主题：

| 主题 | 适用文章类型 | 文件 |
|------|-------------|------|
| `xiaoke-default` | 思辨/思考类/方法论长文 | `themes/xiaoke-default.css` |
| `xiaoke-comparison` | 对比/汇总/集合整理类文章 | `themes/xiaoke-comparison.css` |

发布时通过 `--custom-theme`（`-c`）指定自定义主题文件路径：

```bash
wenyan publish -f article.md -c themes/xiaoke-default.css
```

### 4. Server 模式发布（推荐）

适合：多设备共用、AI 自动化、CI/CD

```bash
wenyan publish -f article.md \
  --server http://<server>/api/wenyan \
  --api-key <api-key>
```

当前推荐 Server 模式，因为：
- 公众号白名单绑定的是服务器公网 IP
- 对外入口统一为路由形式，更适合长期维护
- 支持 AI 自动化和脚本调用

### 5. 检查发布结果

发布成功后会返回 `media_id`，表示已进入公众号草稿箱。

```bash
# 验证服务状态
curl http://<server>/api/wenyan/health
```

## 排版规范

发布到公众号的内容应遵循：

1. **不改核心观点** —— 保持原文观点不漂移
2. **标题层级控制** —— 三级以内
3. **段落尽量短** —— 移动端优先可读
4. **表格按需保留** —— 对比/汇总类文章保留表格便于横向比较；其他类型可转为分点
5. **封面图位置** —— 建议将 `![封面](./assets/cover.png)` 放在 `# 标题` 之后、正文第一段之前
6. **链接格式** —— 正文使用标准 `[文本](URL)`，Wenyan 默认生成文末脚注；如需正文直接显示 URL，加 `--no-footnote`
7. **结尾建议** —— 给出行动建议或总结句

## 禁止项

- 过度营销化语气
- 大段未分段文本
- 未校对即标记完成
- 在规则正文中记录 API Key、AppSecret 或服务器密码

## 敏感信息管理

以下信息**不要**写入：
- 草稿正文
- 普通项目说明
- ai-rules 正文

统一存放位置：`resources/账号/`

## 故障排查

### 发布失败

1. 检查 frontmatter 是否包含 `title` 和 `digest`
2. 检查封面图片路径是否可访问
3. 检查正文图片路径是否可访问
4. 检查 Server 地址和 API Key 是否正确
5. 检查服务器健康状态：`curl <server>/api/wenyan/health`

### 摘要为空

wenyan 上游 v2.0.4 默认不传递 `digest` 到微信 API。解决方案：
1. 手动 patch `core.js` + `wrapper.js`（当前服务器已应用）
2. 或升级到 v2.0.5+ 并验证官方是否已修复

patch 位置：
- `/usr/local/lib/node_modules/@wenyan-md/cli/node_modules/@wenyan-md/core/dist/core.js`
- `/usr/local/lib/node_modules/@wenyan-md/cli/node_modules/@wenyan-md/core/dist/wrapper.js`

### 图片不显示

检查图片路径：
- 使用相对路径 `./assets/xxx.png`
- 文件名避免空格，使用英文小写或中文
- Windows 绝对路径（尤其含空格时）可能导致 marked 解析失败

## 项目维护与服务器同步

### 分支策略

```
upstream (caol64/wenyan-cli)
    └── main (上游原始分支)
            │
            ▼  fork
    li-xiu-qi/wenyan-cli
            ├── main (同步上游，只读，不部署)
            └── xiaoke-customizations (私有分支，部署到服务器)
```

- **`main`**：仅用于同步上游更新，保持与 upstream/main 一致，不直接部署
- **`xiaoke-customizations`**：私有功能分支，包含：
  - 自定义主题（xiaoke-default、xiaoke-comparison）
  - 上游兼容性修复（import.meta.main → Node.js 兼容）
  - `digest` 字段传递修复
  - URL 去重与主动引用支持（`references` frontmatter）
  - 所有部署到服务器的代码必须来自此分支

**合并上游更新流程**：
```bash
# 1. 本地 main 同步上游
git checkout main
git fetch upstream
git merge --ff-only upstream/main

# 2. 合并到私有分支
git checkout xiaoke-customizations
git rebase main

# 3. 重新应用私有 patch（如有冲突）
# - import.meta.main 修复
# - digest 字段修复
# - URL 去重与 references 支持

# 4. 构建并部署
npm install && npm run build
# 部署到服务器...
```

### 开源地址

- **上游项目**：`https://github.com/caol64/wenyan-cli`
- **本组织 Fork**：`https://github.com/li-xiu-qi/wenyan-cli`

### 自定义主题

Fork 的 `xiaoke-customizations` 分支维护了两个私有主题：

| 主题 | 文件 | 说明 |
|------|------|------|
| `xiaoke-default` | `themes/xiaoke-default.css` | 思辨/思考类/方法论长文 |
| `xiaoke-comparison` | `themes/xiaoke-comparison.css` | 对比/汇总/集合整理类文章 |

自定义主题通过 `--custom-theme`（`-c`）在**客户端**指定文件路径使用，不需要在服务器注册主题。

### 服务器更新流程

当上游发布新版本或自定义主题有更新时，执行以下步骤：

1. **本地合并上游**
   ```bash
   cd Projects/CodeProjects/WSL-Native/wenyan-cli
   git fetch origin
   git checkout main
   git merge --ff-only origin/main
   ```

2. **同步到自定义分支并构建**
   ```bash
   git checkout xiaoke-customizations
   git rebase main
   npm install
   npm run build
   ```

3. **部署到服务器**
   使用 Python + paramiko 脚本一键上传并重启：
   - 停止 `wenyan-cli.service`
   - 用 `git archive` 打包 `xiaoke-customizations` 分支
   - 上传 tar.gz 到服务器 `/tmp/`
   - 解压覆盖 `/usr/local/lib/node_modules/@wenyan-md/cli/`
   - 在服务器上执行 `npm install` 和 `npm run build`
   - 执行 `chmod +x dist/cli.js`（关键！`tsc` 编译产物默认无执行权限）
   - 启动 `wenyan-cli.service`
   - 验证 `curl http://127.0.0.1:18317/health`

4. **验证**
   ```bash
   systemctl is-active wenyan-cli.service
   curl -s http://127.0.0.1:18317/health
   curl -s http://127.0.0.1/api/wenyan/health
   ```

### 版本更新建议

当前服务器部署版本为 **v2.0.4**，npm 最新版本为 **v2.0.8**。

**v2.0.6 新增功能**（当前服务器未升级）：
- 支持发布图片消息（小绿书）
- 支持评论开关参数 `--comment`

**建议升级时机**：
- 需要自动开启文章评论时
- 需要发布图片消息（小绿书）时
- 升级前需重新验证 `import.meta.main` 修复和 `digest` patch

升级命令（服务器上执行）：
```bash
npm install -g @wenyan-md/cli@latest
```

### 已知兼容性问题

**上游 v2.0.4 的 `import.meta.main` 问题**

上游 `src/cli.ts` 末尾使用了 `if (import.meta.main)` 来防止测试时意外触发 `program.parse()`，但 `import.meta.main` 是 Bun/Deno 特性，**Node.js 不支持**。这会导致在 Node.js 环境下运行 `wenyan` 时没有任何输出（`program.parse()` 永远不会执行）。

**修复方式**（已打在 `xiaoke-customizations` 分支）：
```ts
import { realpathSync } from "node:fs";
const isMainModule = (process.argv[1] && import.meta.url === `file://${realpathSync(process.argv[1])}`) || (typeof import.meta.main !== "undefined" && import.meta.main);
if (isMainModule) {
    program.parse(process.argv);
}
```

每次合并上游后，需检查 `src/cli.ts` 末尾是否被上游改回了 `import.meta.main`，如有则需要重新应用此修复。

### 运维教训

- **不要依赖 `plink` 做文件传输**：`plink` 只能执行远程命令，没有原生文件传输能力。Windows 下向服务器传文件，优先使用 Python + `paramiko`（SFTP）写脚本。
- **不要依赖 `npm link`**：服务器上全局安装的 `wenyan` 是一个手工维护的符号链接（`/usr/local/bin/wenyan -> ../lib/node_modules/@wenyan-md/cli/dist/cli.js`）。重新部署后只需 `chmod +x dist/cli.js`，不需要也不应该运行 `npm link`。
- **Node 版本告警可忽略**：上游 `undici@8.1.0` 要求 Node >= 22.19.0，当前服务器运行 Node 20.20.0 会报 `EBADENGINE`，但实际功能不受影响。
- **`digest` 字段需手动 patch**：wenyan 上游 v2.0.4 解析了 frontmatter 的 `description` 但没有把它映射到微信 API 的 `digest` 字段。已在服务器手动 patch `core.js` 和 `wrapper.js` 解决。升级新版本后需重新验证此 patch 是否仍然必要。

## 相关资源

- wenyan-cli 本地仓库：`Projects/CodeProjects/WSL-Native/wenyan-cli/`
- 服务器部署文档：`wenyan-cli/docs/deployment-alicloud-ecs-nginx.md`
- 服务器资源与凭据：`resources/账号/服务器资源管理-阿里云ECS-北京-wenyan.md`
