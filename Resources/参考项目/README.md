# 参考项目

**定位**: 开源项目本地镜像  
**作用**: 存放他人的优秀开源项目，用于学习、参考和二次开发

---

## 目录用途

本目录专门存放从 GitHub 等渠道获取的第三方开源项目，作为个人知识库的参考资料库。

### 存放原则

| 原则 | 说明 |
|------|------|
| **只读参考** | 不对原项目进行直接修改，保持上游可更新 |
| **本地学习** | 用于代码阅读、架构学习、最佳实践参考 |
| **二次开发** | 如需修改，应在 Projects 目录创建独立项目 |

---

## 现有项目

| 项目名称 | 来源 | 用途 |
|----------|------|------|
| Personal_AI_Infrastructure | [danielmiessler](https://github.com/danielmiessler/Personal_AI_Infrastructure) | PAI 个人 AI 基础设施，学习 AI 系统架构设计 |
| claude-code-skills | - | Claude Code 技能库参考 |
| RAG后端实现 | - | RAG 技术实现参考 |
| 应用与工具 | - | 各类应用工具实现参考 |
| 文档与框架 | - | 文档框架和工具参考 |
| 智能体开发套件 | - | AI Agent 开发相关参考 |
| 最佳实践手册 | - | 各类最佳实践集合 |

---

## 管理规范

### 添加新项目

```powershell
# 进入参考项目目录
Set-Location "resources/参考项目"

# 克隆项目
git clone https://github.com/username/repo-name.git
```

### 更新已有项目

```powershell
# 进入具体项目目录
Set-Location "resources/参考项目/repo-name"

# 拉取最新更新
git pull origin main
```

### 项目记录

添加新项目后，应在本文档的**现有项目**表格中补充记录：
- 项目名称
- 来源链接
- 主要用途/学习点

---

## 与 Projects 的区别

| 维度 | 参考项目 (Resources) | 个人项目 (Projects) |
|------|---------------------|---------------------|
| 来源 | 他人开源项目 | 自己创建/修改 |
| 修改 | 不直接修改 | 主动开发迭代 |
| 目的 | 学习参考 | 产出成果 |
| 归属 | PARA 中的 Resources | PARA 中的 Projects |

---

## 关联文档

- [[02-PARA方法论]]: PARA 分类详细说明
- [[06-项目目录结构]]: 知识库目录体系
