# Git 分支策略

> 个人知识库的分支管理规范

---

## 分支模型

对于个人知识库，推荐使用**简化版 Git Flow**：

```
master (主分支)
  ↑
  ├── 直接提交（日常小更新）
  └── temp-* (临时分支，大规模整理时使用)
```

### 主分支：master

- **用途**：存储稳定、可发布的知识库版本
- **保护**：不要 force push
- **提交**：日常直接提交到 master，无需分支

### 临时分支：temp-描述

- **用途**：大规模重构或整理时使用
- **命名**：`temp-整理哲学目录`, `temp-重构MOC`
- **生命周期**：完成后合并到 master，删除分支

---

## 何时使用分支？

### 不需要分支（直接提交 master）

- 日常笔记更新
- 添加新的学习记录
- 修改现有文档
- 小规模结构调整

### 需要分支

- 大规模目录重构（涉及 >10 个文件）
- 实验性结构调整（不确定是否保留）
- 跨领域的知识迁移
- 与 AI 协作的大规模整理任务

---

## 分支操作示例

### 创建临时分支

```bash
# 从 master 创建
git checkout -b temp-重构思维模型

# 进行大规模修改...
# 移动文件、重命名、结构调整

# 完成后合并
git checkout master
git merge temp-重构思维模型

# 删除临时分支
git branch -d temp-重构思维模型
```

### 放弃实验性分支

```bash
# 如果实验不满意，直接删除分支
git checkout master
git branch -D temp-实验性功能
```

---

## 分支命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `temp-` | 临时整理分支 | `temp-整理哲学目录` |
| `exp-` | 实验性分支 | `exp-新的MOC结构` |
| `sync-` | 同步相关 | `sync-移动端整理` |

---

## 远程分支

### 单人使用

```bash
# 本地 master 直接推送到远程 master
git push origin master
```

### 多设备同步

```bash
# 设备 A：推送
git push origin master

# 设备 B：拉取
git pull origin master

# 如果冲突，手动解决后提交
git add .
git commit -m "chore: 解决设备间同步冲突"
```

---

## 冲突解决

### 常见冲突场景

1. **同一文件在不同设备编辑**
2. **目录结构调整冲突**

### 解决原则

1. **保留两边内容**（知识库冲突通常是内容补充而非互斥）
2. **手动合并后提交**
3. **不要自动接受某一方**

### 解决步骤

```bash
# 1. 拉取远程变更
git pull origin master

# 2. 如果冲突，Git 会提示冲突文件
#    手动编辑冲突文件，保留需要的内容

# 3. 标记冲突已解决
git add 冲突文件

# 4. 提交合并
git commit -m "chore: 解决同步冲突"
```

---

## 备份策略

### 远程仓库作为备份

```bash
# 定期推送
git push origin master

# 推送所有分支
git push --all origin
```

### 本地备份（可选）

```bash
# 创建归档包
git bundle create backup-$(date +%Y%m%d).bundle --all

# 恢复时使用
git clone backup-20260217.bundle
```

---

*参见：[入口导航](_入口导航.md)*
