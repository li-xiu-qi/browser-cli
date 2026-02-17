# Git 提交规范

> Conventional Commits 适配知识库的提交规范

---

## 提交信息格式

```
类型: 简短描述（50字以内）

可选的详细说明（72字换行）

可选的引用信息：相关文件、背景说明
```

### 格式示例

```bash
# 简单提交
feat: 添加思维模型五层架构

# 带详细说明
refactor: 迁移经济学笔记到独立目录

- 将二阶思维、机会成本从哲学迁移到经济学
- 更新哲学导航和经济学导航的链接
- 删除哲学目录下的重复文件

背景：根据知识管理方法论对比研究的结论，
经济学思维模型应该归类到经济学领域而非哲学。
```

---

## 提交类型

| 类型 | 用途 | 示例 |
|------|------|------|
| **feat:** | 新增内容/功能 | `feat: 添加康德伦理学笔记` |
| **refactor:** | 重构/结构调整 | `refactor: 迁移笔记到学科目录` |
| **chore:** | 日常维护 | `chore: 更新 MOC 索引链接` |
| **fix:** | 修正错误 | `fix: 修正辩证思维的概念定义` |
| **docs:** | 文档更新 | `docs: 完善 Git 管理手册` |
| **style:** | 格式调整 | `style: 调整标题层级` |
| **merge:** | 合并分支 | `merge: 合并 temp-整理分支` |

---

## 类型详解

### feat: 新增内容

用于新增知识、新建文件、添加功能。

```bash
# ✅ 好的示例
feat: 添加 _探索中/ 缓冲层结构
feat: 创建 2026-Q1 哲学基础深化学习项目
feat: 添加 agent-collaboration Skill

# ❌ 避免
feat: update                     # 太模糊
feat: 添加了一些东西              # 不具体
```

### refactor: 重构调整

用于结构调整、文件移动、重命名。

```bash
# ✅ 好的示例
refactor: 将思维模型按学科重新分类
refactor: 迁移经济学笔记到 Areas/经济学/
refactor: 重命名哲学导航为 _INDEX-哲学导航.md

# ❌ 避免
refactor: 修改                      # 太简单
refactor: 调整了一些文件的位置       # 不具体
```

### chore: 日常维护

用于索引更新、链接修复、格式调整。

```bash
# ✅ 好的示例
chore: 更新哲学导航的 MOC 链接
chore: 修复失效的双向链接
chore: 同步 Persona 规范

# ❌ 避免
chore: 更新                         # 不说明更新了什么
```

### fix: 修正错误

用于纠正错误信息、修复 broken link。

```bash
# ✅ 好的示例
fix: 修正二阶思维的学科归属错误
fix: 修复 404 链接
fix: 纠正康德生卒年份

# ❌ 避免
fix: bug                            # 太模糊
```

### docs: 文档更新

用于更新规范、添加说明、完善文档。

```bash
# ✅ 好的示例
docs: 添加 Git 管理规范入口导航
docs: 完善 PARA 方法论使用说明
docs: 更新 README 的使用指南
```

### style: 格式调整

纯格式修改，不改变内容含义。

```bash
# ✅ 好的示例
style: 调整标题层级（H2→H3）
style: 统一列表符号为 -
style: 修复 Markdown 表格对齐
```

---

## 提交粒度

### 原则：一个提交只做一件事

**好的粒度：**

```bash
# ✅ 每个提交都是独立的逻辑单元
git commit -m "feat: 添加 _探索中/ 缓冲层"
git commit -m "feat: 添加 _学习区/ 学习项目模板"
git commit -m "chore: 更新 Areas/ 索引链接"
```

**差的粒度：**

```bash
# ❌ 不要一次性提交所有修改
git add .
git commit -m "update"              # 太模糊
git commit -m "整理了很多东西"       # 粒度太大
```

### 分批提交示例

```bash
# 整理思维模型后，分批提交：

# 第一批：结构调整
git add Areas/哲学/辩证思维.md Areas/哲学/批判性思维.md
git commit -m "refactor: 将辩证思维和批判性思维迁移到哲学目录"

# 第二批：索引更新
git add Areas/思维模型.md Areas/哲学/_INDEX-哲学导航.md
git commit -m "chore: 更新思维模型和哲学导航的索引"

# 第三批：删除旧文件
git add -A  # 删除的文件
git commit -m "chore: 删除思维模型的旧位置文件"
```

---

## 提交模板

创建 `.gitmessage` 文件：

```bash
# 类型: 简短描述（50字以内）
#
# 详细说明：
# - 做了什么
# - 为什么做
# - 影响范围
#
# 类型选项:
# feat: 新增内容/功能
# refactor: 重构/结构调整
# chore: 日常维护/索引更新
# fix: 修正错误
# docs: 文档更新
# style: 格式调整
# merge: 合并分支
```

配置使用：

```bash
git config commit.template .gitmessage
```

---

## 常见错误

### 提交信息太模糊

```bash
# ❌ 错误
update
修改
整理

# ✅ 正确
feat: 添加 PARA 与主题学习的张力分析
refactor: 迁移经济学思维模型到学科目录
chore: 更新思维模型索引链接
```

### 提交粒度太大

```bash
# ❌ 错误
git add .
git commit -m "修改了很多东西"

# ✅ 正确
git add Areas/_探索中/
git commit -m "feat: 添加探索中缓冲层结构"

git add Areas/_学习区/
git commit -m "feat: 添加学习区项目模板"
```

### 类型使用不当

```bash
# ❌ 错误
fix: 添加新笔记              # fix 用于修复，不是新增
feat: 修正链接错误           # feat 用于新增，修复用 fix

# ✅ 正确
feat: 添加新笔记
fix: 修正链接错误
```

---

## 查看提交历史

```bash
# 简洁查看
git log --oneline -20

# 图形化查看
git log --graph --oneline --all

# 查看具体提交的修改
git show 提交哈希

# 查看某个文件的修改历史
git log -p 文件路径
```

---

*参见：[入口导航](_入口导航.md)*
