# xiaoke-writing

`xiaoke-writing` 现在是这套公众号写作方法论的开发侧单一事实源。

以后稳定的写作规则、标题方法、复盘资产和方法演化材料，优先收在这里。  
`筱可-公众号写作项目` 里已经不再保留独立的 `04_写作规则与复盘/` 目录。

---

## 当前结构

```text
xiaoke-writing/
├── README.md
├── SKILL.md
├── current/
│   ├── README.md
│   ├── 筱可公众号写作规范.md
│   ├── 用词偏好.md
│   ├── 敏感内容检查清单.md
│   ├── 思考类文章生产SOP.md
│   ├── 内容形态优先级-基于对标研究.md
│   └── 贴图写作规范/
├── methods/
│   └── 标题与小标题/
├── versions/
├── 复盘模板/
├── 复盘实例/
├── 方法演化/
├── drafts/
├── 更新日志.md
└── 版本对比.md
```

---

## 快速入口

- 当前最短入口：[current/筱可公众号写作规范.md](./current/筱可公众号写作规范.md)
- 标题方法入口：[methods/标题与小标题/README.md](./methods/标题与小标题/README.md)
- 当前最细主线：[versions/v9/写作规范.md](./versions/v9/写作规范.md)
- 我的视角补充线：[versions/perspective-v2/写作规范.md](./versions/perspective-v2/写作规范.md)
- Skill 运行入口：[SKILL.md](./SKILL.md)
- 版本变化：[版本对比.md](./版本对比.md) 和 [更新日志.md](./更新日志.md)

---

## 边界

- 稳定写作规则：留在这里
- 标题与小标题方法：留在这里
- 历史版本和专题补充：留在这里
- 复盘模板和复盘实例：留在这里
- 提示词试验和项目期方法沉淀：留在这里
- 公众号发布链路：看 [../wechat-writing/current/Wenyan服务器发布SOP.md](../wechat-writing/current/Wenyan服务器发布SOP.md)
- 临时素材、过时内容、待清理文件：移入 `_archive/`（定期清理）

---

## 归档机制

需要定期清理的临时文件、过时素材，统一移入 [`_archive/`](./_archive/)。

- 已发布文章的临时工作文件 → `_archive/已发布文章临时文件/`
- 过时的提示词试验 → `_archive/过时提示词与试验/`
- 废弃的旧版本规范 → `_archive/废弃版本/`
- 长期未动的草稿 → `_archive/待整理草稿/`（见 `drafts/`）

**清理周期**：每季度末检查一次，删除超过保留期的文件。

## 同步口径

当 `SKILL.md` 更新后，同步到正式 skills：

```powershell
Copy-Item SKILL.md ../../../../.agents/skills/xiaoke-writing/SKILL.md
```

如果更新的是 `current/`、`methods/`、`versions/` 下的规则正文，也要顺手检查：

- `SKILL.md` 是否需要一起更新
- `Projects/Operations/筱可-公众号写作项目/AGENTS.md` 是否还指向旧入口
- 项目侧兼容入口是否需要一起改
