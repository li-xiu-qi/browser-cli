# Wenyan-CLI Skill 入口导航

> Wenyan-CLI 项目专属 Skill 的 canonical 位置。如需修改 Skill，请在 `skill-development/<skill-name>/` 中迭代，评测后发布到 `skills/`。

---

## AI 必读

1. **确定任务意图**：涉及 wenyan-cli 升级、patch、部署、发布 → 读取 `wenyan-cli-ops`
2. **分支关系**：`main` 仅同步上游，`xiaoke-customizations` 是私有开发分支，服务器从此分支部署
3. **禁止直改**：所有修改必须先在 `skill-development/` 完成，再发布到 `skills/`

---

## Skill 快速选择表

| 意图/关键词 | Skill | 说明 |
|---|---|---|
| wenyan-cli 升级、patch、部署、发布、服务器运维 | `wenyan-cli-ops` | 项目运维总入口 |

---

## 使用原则

- 禁止直接修改 `skills/` 下的任何文件
- 所有修改必须先在 `skill-development/<skill>/` 中完成
- 发布后通过同步脚本更新到 `.agents/skills/` 和 `.kimi/skills/`
