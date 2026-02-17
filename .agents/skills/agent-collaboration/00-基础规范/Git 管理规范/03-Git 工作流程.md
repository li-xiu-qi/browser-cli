# Git 工作流程

> 知识库日常操作的完整流程指南

---

## 日常提交流程

### 标准流程

```bash
# 1. 查看当前状态
git status

# 2. 查看变更内容（确认修改）
git diff

# 3. 添加文件（建议分批）
git add 文件路径
# 或添加整个目录
git add Areas/哲学/

# 4. 提交（遵循规范）
git commit -m "类型: 描述"

# 5. 推送到远程
git push origin master
```

### VSCode 集成流程

如果使用 VSCode 的 Git 面板：

1. **查看变更**：左侧 Git 图标 → 查看修改的文件
2. **暂存文件**：点击 `+` 或 `暂存更改`
3. **输入消息**：顶部输入框，遵循提交规范
4. **提交**：点击 `✓` 或 `Ctrl+Enter`
5. **推送**：点击 `...` → `推送`

---

## 场景工作流

### 场景 1：写完一篇新笔记

```bash
# 写完 Areas/哲学/康德伦理学.md

# 查看变更
git status
# 输出：
# Untracked files:
#   Areas/哲学/康德伦理学.md

# 添加文件
git add Areas/哲学/康德伦理学.md

# 提交
git commit -m "feat: 添加康德伦理学笔记"

# 推送
git push origin master
```

### 场景 2：修改现有笔记

```bash
# 修改了 Areas/思维模型.md

# 查看变更内容
git diff Areas/思维模型.md

# 确认无误后添加
git add Areas/思维模型.md

# 提交
git commit -m "fix: 修正思维模型的学科分类"

# 推送
git push origin master
```

### 场景 3：整理多个文件

```bash
# 移动了多个文件，需要分批提交

# 第一批：新增文件
git add Areas/经济学/二阶思维.md Areas/经济学/机会成本.md
git commit -m "refactor: 将经济学思维模型迁移到经济学目录"

# 第二批：更新索引
git add Areas/思维模型.md
git commit -m "chore: 更新思维模型索引链接"

# 第三批：删除旧文件
git add -A  # 这会暂存删除操作
git commit -m "chore: 删除哲学目录下的经济学思维模型"

# 一起推送
git push origin master
```

### 场景 4：大规模重构（使用分支）

```bash
# 1. 创建临时分支
git checkout -b temp-重构知识库结构

# 2. 进行大规模修改
# - 移动文件
# - 重命名目录
# - 更新链接

# 3. 分批提交
git add ...
git commit -m "refactor: xxx"

# 4. 回到 master，合并
git checkout master
git merge temp-重构知识库结构

# 5. 删除临时分支
git branch -d temp-重构知识库结构

# 6. 推送
git push origin master
```

### 场景 5：添加 Agent Skill

```bash
# 创建了新 Skill
mkdir -p .agents/skills/new-skill
touch .agents/skills/new-skill/SKILL.md

# 添加并提交
git add .agents/skills/new-skill/
git commit -m "feat: 添加 xxx Skill"

git push origin master
```

### 场景 6：同步多台设备

**设备 A（办公室电脑）：**

```bash
# 工作完成，推送
git add .
git commit -m "feat: 添加今天的学习笔记"
git push origin master
```

**设备 B（家里电脑）：**

```bash
# 开始工作前，先拉取最新
git pull origin master

# 继续工作...
```

---

## 撤销与回退

### 撤销未暂存的修改

```bash
# 撤销对文件的修改（恢复到上次提交）
git checkout -- 文件路径

# 撤销所有未暂存的修改
git checkout -- .
```

### 撤销已暂存但未提交

```bash
# 从暂存区移除，但保留修改
git reset HEAD 文件路径

# 撤销所有暂存
git reset HEAD
```

### 修改最后一次提交

```bash
# 修改提交信息
git commit --amend -m "新的提交信息"

# 添加漏掉的文件到最后一次提交
git add 漏掉的文件
git commit --amend --no-edit
```

### 回退到历史版本

```bash
# 查看历史
git log --oneline

# 回退到某个版本（保留修改）
git reset --soft HEAD~1

# 回退到某个版本（丢弃修改）
git reset --hard 提交哈希

# 推送到远程（强制，谨慎使用）
git push origin master --force
```

---

## 查看与搜索

### 查看状态

```bash
# 简要状态
git status

# 简短状态
git status -s
```

### 查看历史

```bash
# 简洁历史
git log --oneline -20

# 详细历史（含作者、日期）
git log --pretty=format:"%h - %an, %ar : %s" -10

# 图形化历史
git log --graph --oneline --all

# 查看某个文件的修改历史
git log -p Areas/哲学.md
```

### 查看差异

```bash
# 查看未暂存的修改
git diff

# 查看已暂存的修改
git diff --staged

# 查看某个文件的修改
git diff 文件路径
```

### 搜索内容

```bash
# 在 Git 历史中搜索内容
git log -S "搜索关键词" --all

# 搜索提交信息
git log --all --grep="关键词"
```

---

## 与 AI 协作的工作流

### AI 生成内容后的提交流程

```bash
# 1. AI 生成了一批文件
# 检查生成的内容
git status

# 2. 查看 AI 生成的内容
git diff

# 3. 选择性添加（确认质量后）
git add Areas/_探索中/新文件.md

# 4. 提交
git commit -m "feat: 添加 xxx 内容（AI 生成）"

# 5. 推送
git push origin master
```

### AI 大规模整理后的提交流程

```bash
# 1. AI 建议创建临时分支
git checkout -b temp-AI整理任务

# 2. AI 进行整理...

# 3. 检查整理结果
git status
git diff

# 4. 满意后合并
git checkout master
git merge temp-AI整理任务
git branch -d temp-AI整理任务

# 5. 推送
git push origin master
```

---

## 定期维护任务

### 每周维护

```bash
# 1. 检查未提交的修改
git status

# 2. 提交所有修改
git add .
git commit -m "chore: 周度笔记整理"

# 3. 推送
git push origin master

# 4. 查看本周提交
git log --oneline --since="1 week ago"
```

### 每月维护

```bash
# 1. 检查仓库大小
du -sh .git

# 2. 清理（可选）
git gc

# 3. 查看提交统计
git shortlog -sn --since="1 month ago"
```

---

## 快捷命令参考

```bash
# 查看状态
git status                    # gs（别名）

# 添加并提交
git add . && git commit -m "chore: 更新"

# 提交并推送
git commit -m "feat: xxx" && git push

# 快速查看历史
git log --oneline -10         # gl（别名）

# 查看当前分支
git branch                    # gb（别名）
```

---

*参见：[入口导航](_入口导航.md)*
