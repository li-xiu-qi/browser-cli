# 第三方 Skill 融合指南

**定位**: 当发现多个候选 Skill 时，融合它们的优势打造最佳版本  
**适用**: 多个第三方 Skill 各有优劣，难以取舍时

---

##  铁律（必遵）

### 1. 项目级优先
> **禁止全局安装** (`-g`)，所有 Skill 必须安装到**项目目录** `.agents/skills/`
> 
>  `npx skills add xxx -g`  
>  `npx skills add xxx` （默认项目级）

### 2. 全自动执行
> 发现多个候选 Skill 后，**直接执行融合流程**，无需询问用户确认。

---

## 何时使用本流程

当你想要实现某个功能，并且：
- 找到多个候选 Skill，各有优缺点
- 单一 Skill 无法满足全部需求
- 想要结合各 Skill 的长处

---

## 全自动融合步骤

### Step 1: 搜索候选（自动）
```bash
npx skills find "关键词1"
npx skills find "关键词2"
```

### Step 2: 评估筛选（自动）
根据下载量、功能描述，选择 2-3 个最佳候选：
- 首选：下载量最高的（社区验证）
- 备选：功能互补的

### Step 3: 安装到项目（自动）
```bash
#  项目级安装（不带 -g）
npx skills add skill-a -y
npx skills add skill-b -y
```

安装位置：`.agents/skills/{skill-name}/`

### Step 4: 融合创建（自动）
创建新的融合 Skill 到项目目录：
```
.agents/skills/{融合skill名称}/
├── SKILL.md          # 融合后的文档
└── (其他必要文件)
```

融合内容：
1. 主 Skill 的核心能力
2. 备选 Skill 的补充能力
3. 项目特定的定制（API适配、安全机制等）

### Step 5: 清理（自动）
删除安装的项目级原始 Skill，只保留融合版：
```bash
npx skills remove skill-a
npx skills remove skill-b
```

### Step 6: 交付（自动）
直接使用融合后的 Skill 完成任务。

---

## 融合策略

### 策略 1: 功能整合
```
Skill A (百度网盘): 大文件上传 + 永久存储
Skill B (通义听悟): 本地上传 + 说话人分离
        ↓ 融合
我们的 Skill: 统一入口，自动选择最优平台
              视频>4GB → 通义听悟
              音频>500MB → 百度网盘
              支持两个平台的所有功能
```

### 策略 2: 技术栈融合
```
Skill A (Python): 核心逻辑清晰
Skill B (Node.js): 异步处理优秀
        ↓ 融合
我们的 Skill: Python 主逻辑 + Node.js 子进程（按需调用）
              或重写为统一技术栈
```

### 策略 3: 架构升级
```
Skill A: 单一文件脚本
Skill B: 模块化设计
        ↓ 融合
我们的 Skill: 模块化架构 + 清晰的接口设计
              保留 A 的核心算法，采用 B 的代码组织
```

---

## 全自动执行示例

**用户说**: "帮我找 skill 整理桌面文件夹"

**你应该自动执行**:

```bash
# 1. 搜索（自动）
npx skills find "file organization"
npx skills find "folder organize"

# 2. 发现 5 个候选，选择 top 2（自动）
#    - sickn33/file-organizer (234⭐)
#    - delphine-l/folder-organization (21⭐)

# 3. 项目级安装（自动，不带 -g）
npx skills add sickn33/antigravity-awesome-skills@file-organizer -y
npx skills add delphine-l/claude_global@folder-organization -y

# 4. 创建融合版（自动）
mkdir .agents/skills/desktop-organizer
cat > .agents/skills/desktop-organizer/SKILL.md << 'EOF'
# 桌面整理专家（融合版）
# 来源：sickn33/file-organizer + delphine-l/folder-organization
# 定制：添加桌面特定逻辑
...
EOF

# 5. 删除原始 skills（自动清理）
npx skills remove file-organizer
npx skills remove folder-organization

# 6. 直接使用融合版完成任务（自动）
# 7. 完成后报告结果
```

---

## 能力拆解模板

| Skill | 优势 | 劣势 | 下载量 |
|-------|------|------|--------|
| 候选 A | ... | ... | X⭐ |
| 候选 B | ... | ... | Y⭐ |

**决策**: 主选 A（下载量高），补充 B（功能互补），融合创建 C。

---

## 来源记录模板

在融合后的 SKILL.md 顶部添加：

```yaml
---
name: skill-name
description: 功能描述
sources:
  - name: 原始 Skill A
    url: GitHub 链接
    license: 许可证
    reference: 引用的具体能力
  - name: 原始 Skill B
    url: GitHub 链接
    license: 许可证
    reference: 引用的具体能力
fusion_strategy: 功能整合/技术栈融合/架构升级
custom_features:
  - 项目特定的定制能力1
  - 项目特定的定制能力2
---
```

---

## 融合 checklist

- [x] 发现多个候选 Skill
- [x] **项目级安装**（禁止 `-g` 全局安装）
- [x] 创建融合版到项目目录
- [x] 记录来源和引用
- [x] 添加项目特定定制
- [x] **删除原始 skills**（只保留融合版）
- [x] 直接使用融合版完成任务

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 2.2 | 2026-02-15 | **强制项目级安装，禁止全局安装** |
| 2.1 | 2026-02-15 | 明确全自动执行原则，无需询问用户 |
| 2.0 | 2026-02-15 | 重构为专注融合的精简版本 |
| 1.0 | 2026-02-01 | 初始版本 |

---

*版本: 2.2*  
*更新: 强制项目级安装规范*  
*维护者: 筱可*
