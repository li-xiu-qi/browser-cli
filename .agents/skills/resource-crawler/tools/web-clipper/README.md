# Web Clipper Agent Skill

此技能专为 Obsidian 知识库设计，利用 Playwright 实现高质量的网页（尤其是微信公众号）内容抓取。

## 目录结构
- `SKILL.md`: Agent 指令定义。
- `scripts/web_clipper.js`: 核心抓取脚本。
- `scripts/package.json`: 依赖定义。

## 手动使用
如果你需要手动运行此脚本（不通过 Agent）：
```bash
cd .gemini/skills/web-clipper/scripts
node web_clipper.js "https://mp.weixin.qq.com/s/..."
```

## 共享环境
此工具共享 `~/.gemini/shared_browser_data` 目录下的浏览器数据，一次登录，全域复用。
