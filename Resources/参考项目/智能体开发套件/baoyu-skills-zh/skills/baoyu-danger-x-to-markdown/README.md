# baoyu-danger-x-to-markdown (X/Twitter 内容抓取)

这是一个专门用于将 X (原 Twitter) 的推文 (Tweets)、推文串 (Threads) 和长文章 (Articles) 转换为 Markdown 格式的工具。它能够完美提取内容、图片链接和元数据，适合用于构建个人知识库或归档。

> ⚠️ **风险提示**：本工具使用了逆向工程的 X API，属于非官方访问方式。请勿高频大量抓取，以免账号受限。初次使用需确认免责声明。

## 🌟 核心功能

- **推文串完整抓取**：自动识别并抓取完整的 Thread 对话链。
- **长文章支持**：支持 X Article (长文) 的完整内容提取。
- **元数据保留**：生成的 Markdown 包含 YAML Frontmatter（作者、发布时间、推文数、原链接等）。
- **格式完美**：自动处理推文中的图片、视频占位符和引用推文。

## 🛠️ 使用方法

```bash
# 抓取单条推文或 Thread
npx -y bun ${SKILL_DIR}/scripts/main.ts https://x.com/user/status/123456789

# 指定输出路径
npx -y bun ${SKILL_DIR}/scripts/main.ts <url> -o saved/tweet.md

# 输出 JSON 格式 (适合程序调用)
npx -y bun ${SKILL_DIR}/scripts/main.ts <url> --json
```

## ⚙️ 鉴权配置

本工具需要有效的 X 登录凭证才能工作。支持两种方式：

1.  **环境变量 (推荐)**：设置 `X_AUTH_TOKEN` 和 `X_CT0`。
2.  **浏览器 Cookie (Fallback)**：如果未设置环境变量，工具会尝试调用本地 Chrome 浏览器的登录状态（需先在 Chrome 登录 X）。

## 📂 输出示例

生成的 Markdown 文件示例：

```markdown
---
url: https://x.com/username/status/123456
author: "Display Name (@username)"
created_at: "2023-10-27T10:00:00Z"
tweet_count: 5
---

这里是推文正文内容...

![image](https://pbs.twimg.com/media/...)

> 引用推文内容...
```

---
*此工具是构建“稍后读”或“知识剪藏”工作流的强力组件。*
