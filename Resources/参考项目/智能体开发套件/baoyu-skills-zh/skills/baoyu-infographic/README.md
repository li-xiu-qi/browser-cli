# baoyu-infographic (专业信息图生成)

这是一个用于将文本内容转化为出版级信息图 (Infographics) 的 AI 智能体。它采用 "Layout (布局) × Style (风格)" 的二维矩阵设计，支持 20 种专业布局和 17 种视觉风格的自由组合。

## 🌟 核心特性

- **布局 × 风格矩阵**：
    - **布局 (Layouts)**：Bento Grid (便当盒), Timeline (时间轴), Iceberg (冰山图), Funnel (漏斗图), Versus (对比图) 等 20 种。
    - **风格 (Styles)**：Claymation (粘土风), Isometric (等轴测), Cyberpunk (赛博朋克), Hand-drawn (手绘) 等 17 种。
- **数据保真 (Verbatim Principle)**：核心原则是**保留原始内容**。不做概括、不改写数据，确保信息图上的每一个数字和引用都与原文严格一致。
- **结构化中间层**：在生成图片前，会先生成 `structured-content.md`，将非结构化文本转化为适合视觉表现的结构化数据。

## 🛠️ 使用方法

```bash
# 默认生成 (Bento Grid + Craft Handmade)
/baoyu-infographic report.md

# 指定布局与风格
/baoyu-infographic report.md --layout iceberg --style claymation

# 调整画幅
/baoyu-infographic stats.md --aspect portrait  # 9:16 适合手机阅读
/baoyu-infographic stats.md --aspect square    # 1:1 适合 Instagram

# 交互式模式
/baoyu-infographic
[粘贴内容]
```

## 📚 推荐组合 (Best Practices)

- **历史/流程** → `linear-progression` + `craft-handmade`
- **对比/优劣** → `binary-comparison` + `corporate-memphis`
- **深层分析** → `iceberg` + `3d-render`
- **多维度数据** → `bento-grid` + `chalkboard`
- **转化漏斗** → `funnel` + `isometric`

## 📂 输出结构

```text
infographic/{topic-slug}/
├── analysis.md              # 内容分析报告
├── structured-content.md    # 结构化数据 (可人工校对)
├── prompts/infographic.md   # 生成提示词
└── infographic.png          # 最终产出
```

---
*设计理念：信息图不只是好看的图片，更是高效的信息载体。*
