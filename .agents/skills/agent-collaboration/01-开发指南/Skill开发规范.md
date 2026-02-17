# Skill 开发规范

**定位**: AI Skill 的编写标准和发布流程  
**适用范围**: `.agents/skills/` 目录下的所有 Skill

---

## Skill 结构

### 文件组织

```
.agents/skills/
└── skill-name/              # 使用小写连字符命名
    ├── SKILL.md             # 主文档（必须）
    ├── 样例模板/             # 可选：模板目录
    └── 样例/                 # 可选：具体示例
```

### SKILL.md 格式

```markdown
---
name: skill-name
description: 一句话描述 Skill 功能
---

# Skill 名称

## 概述

本 Skill 提供什么功能，解决什么问题。

## 架构说明（可选）

如果涉及软连接或多工具共享，说明架构。

## 核心功能

| 功能 | 说明 |
|------|------|
| 功能A | 描述 |
| 功能B | 描述 |

## 使用方法

### 场景1: XXX

步骤说明...

### 场景2: YYY

步骤说明...

## 规范检查（可选）

- [ ] 检查项1
- [ ] 检查项2

## 关联 Skill

- [[skill-a]]: 关联说明
- [[skill-b]]: 关联说明
```

---

## 命名规范

### Skill 名称

- 使用小写字母
- 单词间用连字符 `-` 连接
- 清晰描述功能

示例:
- `knowledge-base-manager`
- `learning-notes`
- `resource-crawler`

### 描述规范

```yaml
---
name: skill-name
description: 一句话描述 Skill 功能，50字以内
---
```

---

## 文档规范

### 语言

- 使用中文编写
- 术语可用英文，无需翻译

### 格式

- 遵循 [[../00-基础规范/写作规范]]
- 使用 wikilink 关联其他文档
- 重要内容用表格呈现

### 完整性

| 必须包含 | 说明 |
|----------|------|
| 概述 | Skill 是什么，解决什么问题 |
| 使用方法 | 具体步骤和示例 |
| 关联文档 | 相关的 Skill 或规范 |

---

## 软连接架构

### 策略

`.agents/skills/` 作为唯一事实来源，其他工具通过软连接引用。

### 当前配置

```
.agents/skills/              # 实际文件（核心）
├── knowledge-base-manager/
├── learning-notes/
└── ...

.gemini/skills/              # 目录联接
├── knowledge-base-manager/  [JUNC → .agents/skills/]
└── ...
```

### 新增 Skill 流程

1. 在 `.agents/skills/` 创建目录和 SKILL.md
2. 在 `.gemini/skills/` 创建目录联接:
   ```powershell
   New-Item -ItemType Junction -Path ".gemini/skills/skill-name" -Target ".agents/skills/skill-name"
   ```
3. 更新 [[../00-基础规范/_入口导航]] 中的技能库列表

---

## 更新与迭代

### 更新触发条件

| 场景 | 操作 |
|------|------|
| 发现输出不符合预期 | 更新 SKILL.md 的约束部分 |
| 新的最佳实践 | 添加到执行步骤 |
| 常见错误模式 | 添加到注意事项 |
| Skill 过于复杂 | 拆分为多个 Skill |

### 版本管理

- 重大变更更新 SKILL.md 头部的描述
- 记录变更到 [[../changelogs/README|变更日志]]

---

## 技术栈与依赖管理

### 核心原则

**统一共享环境，禁止私有依赖目录**

Skill 加载时会将整个文件树传递给 AI 上下文，私有的 `node_modules/` 或 `.venv/` 会严重污染上下文，降低 AI 效率。因此：

-  **优先使用共享环境** - 能用根目录依赖解决的，绝不新建私有环境
-  **必须私有时内置到 tools/** - 确实需要特殊依赖的，直接放在 `tools/` 下作为代码一部分
-  **禁止 skill 根目录有 node_modules/** - 这会污染 AI 上下文
-  **禁止独立 package.json/requirements.txt** - 统一使用根目录的环境配置

### Python 环境

**统一环境**: 项目根目录 `.venv/`

```bash
# 运行脚本
uv run python script.py

# 添加依赖（根目录）
uv add package-name
```

**规范**:
- Python 脚本使用 `uv run python` 运行
- 依赖统一安装到根目录 `.venv/`
- **禁止**在 skill 目录内创建虚拟环境
- 所有工具通过根目录 `pyproject.toml` 管理依赖

**当前已安装的 Python 依赖**:

| 依赖 | 用途 |
|------|------|
| `playwright` | 浏览器自动化 |
| `requests` | HTTP 请求 |
| `beautifulsoup4` | HTML 解析 |
| `paddlepaddle/paddleocr` | OCR 文字识别 |
| `rich` | 终端美化 |
| `python-dotenv` | 环境变量管理 |

### Node.js 环境

**统一环境**: 项目根目录 `node_modules/`

```bash
# 安装依赖（在项目根目录）
npm install --legacy-peer-deps

# 运行脚本
node .agents/skills/xxx/tools/script.js
```

**规范**:
- **禁止**在 skill 目录内创建 `package.json` 和 `node_modules/`
- 所有 Node.js 依赖统一通过根目录 `package.json` 管理
- 需要新依赖时，在根目录运行 `npm install package-name`
- 脚本中使用 `require()` 会自动解析到根目录的 `node_modules/`

**当前已安装的 Node.js 依赖**:

| 依赖 | 用途 |
|------|------|
| `playwright` | 浏览器自动化、网页抓取 |
| `puppeteer` | 浏览器自动化 |
| `jsdom` | DOM 解析 |
| `turndown` | HTML 转 Markdown |
| `defuddle` | 网页内容提取 |
| `fast-xml-parser` | XML 解析 |
| `adm-zip` | ZIP 文件处理 |
| `node-html-markdown` | HTML 转 Markdown |
| `pdf-lib` | PDF 处理 |
| `sharp` | 图像处理 |

### 工具目录结构

对于有私有依赖需求的工具，使用以下结构：

```
.agents/skills/skill-name/
├── SKILL.md
└── tools/               # 工具代码目录
    ├── tool.js          # 直接内置，无 node_modules
    └── lib/             # 工具内部库文件
```

**规则**:
1. `tools/` 目录只包含源代码，**禁止**有 `node_modules/`
2. 工具通过 `require('../../../../../node_modules/package-name')` 或 Node.js 模块解析机制使用根目录依赖
3. 确实需要打包的依赖，直接内联到代码中（单文件或少数文件）

### 依赖添加流程

1. **评估必要性**: 该依赖是否在整个项目范围内有用？是否可以用现有依赖替代？
2. **添加到根目录**: 在项目根目录运行 `npm install package-name` 或 `uv add package-name`
3. **更新文档**: 在本文档的依赖列表中添加新依赖及其用途
4. **测试**: 确保新依赖在 skill 中可用
5. **提交**: 提交 `package.json`/`pyproject.toml` 和 `uv.lock`/`package-lock.json` 的变更

### 违规检查

定期检查命令：

```powershell
# 检查 skill 根目录是否有 node_modules
Get-ChildItem .agents/skills -Directory | Where-Object { Test-Path "$($_.FullName)/node_modules" }

# 检查 skill 根目录是否有 package.json
Get-ChildItem .agents/skills -Directory | Where-Object { Test-Path "$($_.FullName)/package.json" }
```

---

## 关联文档

- [[../00-基础规范/_入口导航]]: Skill 库导航
- [[../00-基础规范/写作规范]]: 文档写作规范
- [[find-skills]]: 外部 Skill 发现工具
