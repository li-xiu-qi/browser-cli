# baoyu-cover-image (文章封面生成专家)

这是一个专为文章生成高质量、富有设计感封面的 AI 智能体。它引入了独创的 **"5维度 (5-Dimensions)"** 控制系统，能够根据文章内容自动匹配或精确定制封面的视觉语言，解决“配图难、风格乱”的问题。

## 🌟 核心特性 (5D 控制系统)

该工具将封面设计解构为 5 个独立可控的维度，实现精细化定制：

1.  **类型 (Type)**：决定构图和信息结构。
    *   *Gallery*: `hero` (首图), `conceptual` (概念), `typography` (排版), `metaphor` (隐喻), `scene` (场景), `minimal` (极简)。
2.  **色板 (Palette)**：决定色彩心理。
    *   *Gallery*: `warm` (暖色), `elegant` (优雅), `cool` (冷色/科技), `dark` (暗黑/影视), `vivid` (鲜艳), `retro` (复古) 等。
3.  **渲染 (Rendering)**：决定质感与技法。
    *   *Gallery*: `flat-vector` (扁平矢量), `hand-drawn` (手绘), `painterly` (绘画感), `3d-render` (3D), `pixel` (像素风)。
4.  **文本 (Text)**：决定信息密度。
    *   *Levels*: `none` (无字), `title-only` (仅标题), `title-subtitle` (标题+副标), `text-rich` (信息密集)。
5.  **情绪 (Mood)**：决定视觉冲击力。
    *   *Levels*: `subtle` (含蓄), `balanced` (平衡), `bold` (大胆/强对比)。

## 🛠️ 自动化与灵活性

- **智能自动选择**：如果你不指定参数，智能体会深度分析文章内容（主题、语调、受众），自动从 5 个维度中挑选最佳组合。
- **预设系统 (Presets)**：支持 `--style` 快捷指令（如 `--style blueprint`），一键应用经过验证的“色板+渲染”组合。
- **多种画幅**：支持 16:9 (默认), 2.35:1 (电影感), 4:3, 1:1 (正方) 等多种比例。

## 🚀 使用示例

```bash
# 全自动模式（最简单）
/baoyu-cover-image article.md

# 快速模式（跳过确认步骤）
/baoyu-cover-image article.md --quick

# 精细控制（指定 5D 参数）
/baoyu-cover-image article.md --type conceptual --palette warm --rendering flat-vector

# 风格预设（蓝图风格）
/baoyu-cover-image article.md --style blueprint

# 视觉优先（不要文字）
/baoyu-cover-image article.md --no-title
```

## 📂 输出管理

支持三种输出模式（通过 `EXTEND.md` 配置）：
1.  `independent` (默认)：在 `cover-image/{topic-slug}/` 目录下生成，方便统一管理。
2.  `same-dir`：直接在文章同级目录生成。
3.  `imgs-subdir`：在文章下的 `imgs/` 子目录生成。

---
*设计理念：一张好的封面图不应只是好看，更应该准确传达文章的“核心隐喻”和“情绪基调”。*
