# Skill 管理手册

**定位**: 本知识库中所有 Skill 的管理、评估和维护指南  
**范围**: 涵盖自建 Skill 和第三方 Skill 的全生命周期管理

---

## 目录

1. [Skill 概述](#skill-概述)
2. [Skill 生命周期](#skill-生命周期)
3. [第三方 Skill 管理](#第三方-skill-管理)
4. [自建 Skill 管理](#自建-skill-管理)
5. [Skill 目录维护](#skill-目录维护)
6. [附录](#附录)

---

## Skill 概述

### 什么是 Skill

Skill 是扩展 AI 能力的模块化组件，位于 `.agents/skills/` 目录下，包含：
- **SKILL.md**: 使用规范文档
- **工具脚本**: 实现特定功能的代码
- **配置模板**: 标准化输出格式

### Skill 分类

| 类型 | 位置 | 示例 | 特点 |
|------|------|------|------|
| 核心 Skill | `.agents/skills/agent-collaboration/` | 写作规范、PARA方法论 | 必须掌握的基础 |
| 工具 Skill | `.agents/tools/*` | zlibrary、browser-login | 可执行的工具脚本 |
| 专项 Skill | `.agents/skills/{name}/` | resource-crawler、notebooklm-uploader | 特定功能领域 |

---

## Skill 生命周期

### 1. 发现与评估

**发现渠道**:
- 社区/市场搜索
- 用户推荐
- 自主开发

**发现记录流程**:

当通过 `npx skills find` 或其他方式发现潜在新 Skill 时：

1. **临时存储到 Inbox**（防止丢失，避免污染公共目录）
   ```
   0_Inbox/skill-discovery/YYYY-MM-DD-{关键词}.md
   ```

2. **记录模板**:
   ```markdown
   # Skill 发现记录 - {关键词}
   
   **发现时间**: YYYY-MM-DD
   **搜索来源**: `npx skills find {关键词}`
   **状态**: 待评估
   
   ## 候选 Skill 列表
   | Skill | 安装命令 | 热度 | 链接 |
   |-------|----------|------|------|
   | ... | ... | ... | ... |
   
   ## 待处理事项
   - [ ] 评估功能匹配度
   - [ ] 决定安装/放弃/创建
   ```

3. **定期清理**: 每周评估 Inbox 中的发现记录，决策后归档或删除

**评估标准**:

| 维度 | 权重 | 评估要点 |
|------|------|----------|
| 功能匹配 | 40% | 是否解决实际问题 |
| 代码质量 | 25% | 可读性、健壮性、安全性 |
| 维护状态 | 20% | 最近更新、issue响应 |
| 社区热度 | 15% | 下载量、star数 |

**评估工具**: [[第三方Skill评估指南]]

### 2. 安装与集成

**安装原则**:
-  **项目级安装**: 所有 Skill 安装在 `.agents/skills/`
-  **禁止全局安装**: 不使用 `-g` 参数

**安装流程**:
```bash
# 发现候选
npx skills find "关键词"

# 评估选择
# 参考: [[第三方Skill评估指南]]

# 项目级安装
npx skills add skill-name

# 验证安装
ls .agents/skills/skill-name/
```

### 3. 日常使用

**激活条件**:
- 用户明确提到 Skill 相关需求
- 触发词匹配 SKILL.md 中的激活条件

**使用规范**:
1. 先阅读 SKILL.md 了解使用方式
2. 检查环境依赖是否满足
3. 按文档流程执行
4. 记录使用效果和问题

### 4. 更新与维护

**更新检查**:
```bash
# 检查可更新
npx skills outdated

# 更新指定 Skill
npx skills update skill-name
```

**更新原则**:
- 定期（每月）检查更新
- 关注 breaking changes
- 更新后验证功能正常

### 5. 废弃与移除

**废弃条件**:
- 功能被其他 Skill 完全替代
- 长期无人维护（>6个月）
- 存在严重安全问题
- 使用率极低（<1次/月）

**移除流程**:
```bash
# 备份配置
cp -r .agents/skills/skill-name ./archive/

# 移除
npx skills remove skill-name

# 更新 AGENTS.md 移除引用
```

---

## 第三方 Skill 管理

### 评估与选择

详细流程参考: [[第三方Skill评估指南]]

**快速决策矩阵**:

| 场景 | 推荐策略 |
|------|----------|
| 单一优秀 Skill | 直接使用 |
| 多个互补 Skill | 融合使用 [[第三方Skill评估指南]] |
| 功能不匹配 | 考虑自建或 fork 修改 |

### 风险管理

| 风险 | 应对措施 |
|------|----------|
| 作者停止维护 | 提前 fork，准备替代方案 |
| 安全漏洞 | 定期审计，隔离敏感操作 |
| 功能漂移 | 锁定版本，测试后升级 |
| 依赖冲突 | 使用虚拟环境，隔离依赖 |

---

## 自建 Skill 管理

### 创建流程

参考: [[../../01-开发指南/00-Skill开发规范]]

**创建检查清单**:
- [ ] 明确功能定位和使用场景
- [ ] 编写 SKILL.md 规范文档
- [ ] 实现核心功能脚本
- [ ] 添加使用示例
- [ ] 更新 AGENTS.md 索引
- [ ] 提交到 changelogs

### 命名规范

```
.agents/skills/{skill-name}/
```

**命名规则**:
- 小写字母
- 短横线分隔
- 语义明确

**示例**:
```
resource-crawler     
WebClipper            大写
web_clipper           下划线

```

### 版本管理

**版本号格式**: `主版本.次版本.修订号`

| 版本变化 | 说明 | 示例 |
|----------|------|------|
| 主版本 | 破坏性变更 | `1.x` → `2.x` |
| 次版本 | 功能新增 | `1.1` → `1.2` |
| 修订号 | Bug修复 | `1.1.0` → `1.1.1` |

**版本记录**: 在 SKILL.md 头部添加

```yaml
---
version: 1.2.0
updated_at: 2026-02-15
changelog: "新增XX功能，修复XX问题"
---
```

---

## Skill 目录维护

### 目录结构标准

```
.agents/skills/{skill-name}/
├── SKILL.md              # 规范文档（必须）
├── README.md             # 使用说明（可选）
├── skill.yaml            # 元数据（可选）
├── scripts/              # 工具脚本
├── templates/            # 模板文件
└── assets/               # 图片资源
```

### 定期审查

**审查周期**: 每季度

**审查内容**:
1. 所有 Skill 是否正常使用
2. 是否有 Skill 可被合并或废弃
3. 文档是否与实际功能一致
4. 是否存在冗余或重复功能

**审查输出**: 更新 [[changelogs/README|变更日志]]

---

## 附录

### A. 常用命令

```bash
# 发现
npx skills find "关键词"
npx skills list

# 安装
npx skills add skill-name

# 更新
npx skills update skill-name
npx skills update --all

# 移除
npx skills remove skill-name

# 信息
npx skills info skill-name
```

### B. 相关文档

- [[第三方Skill评估指南]] - 评估和融合第三方 Skill
- [[../../01-开发指南/00-Skill开发规范]] - 开发新 Skill
- [[changelogs/README]] - 变更日志
- [[AGENTS.md]] - 全局 Skill 索引

### C. 术语表

| 术语 | 说明 |
|------|------|
| Skill | AI 能力扩展模块 |
| 第三方 Skill | 社区/外部开发的 Skill |
| 自建 Skill | 本项目开发的 Skill |
| 项目级安装 | 安装在项目目录，非全局 |
| Trigger | 激活 Skill 的条件/关键词 |

---

**版本**: 1.0.0  
**更新**: 2026-02-15
