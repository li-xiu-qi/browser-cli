# baoyu-comic (知识漫画创作专家)

这是一个用于将复杂知识、教程或故事转化为高质量“知识漫画”的 AI 智能体。它不仅仅是简单的文生图，而是一套完整的**漫画创作流水线**，涵盖了从分镜脚本设计、角色设定到连续画面生成及最终 PDF 合成的全过程。

## 🌟 核心特性

- **专业级分镜设计**：自动将文本内容转化为包含分镜描述、景别、对白和旁白的标准漫画脚本。
- **角色一致性控制 (CRITICAL)**：
    - **强制角色设定图**：在绘制正文前，必须先生成包含三视图的角色设定图 (`character sheet`)。
    - **引用生成 (Reference-based)**：每一页漫画的生成都会强制引用角色设定图，确保主角形象在不同分镜中保持高度一致。
- **多维视觉风格矩阵**：
    - **画风 (Art)**：清线风 (Tintin/Logicomix)、日漫、写实、水墨、粉笔画。
    - **基调 (Tone)**：中性、温馨、戏剧、浪漫、活力、复古、动作。
    - **布局 (Layout)**：标准、电影感、密集、跨页、长条漫。
- **智能预设 (Presets)**：
    - `ohmsha`：欧姆社风格（技术科普，无废话，强调图解）。
    - `wuxia`：武侠风格（水墨+动作，气流特效）。
    - `shoujo`：少女漫风格（浪漫+日漫，装饰性元素）。

## 🛠️ 技术原理与工作流

本工具采用 **"Storyboard-First" (分镜优先)** 和 **"Character-Anchored" (角色锚定)** 的设计理念：

1.  **内容分析 (Analyze)**：提取核心知识点或故事情节。
2.  **分镜脚本 (Storyboard)**：生成详细的 `storyboard.md`，规划每一页的画面构成。
3.  **角色标准化 (Character Sheet)**：生成 `characters/characters.png`，锁定人物特征。
4.  **一致性生成 (Consistency Gen)**：利用 Image Gen 模型的参考图功能 (`--ref`)，以角色设定图为锚点，逐页生成漫画内容。
5.  **合成交付 (Merge)**：最后将所有单页合成一份完整的 PDF 文档。

## 📂 项目结构

```text
baoyu-comic/
├── SKILL.md                # 技能核心定义
├── scripts/                # 核心执行脚本
│   └── merge-to-pdf.ts     # PDF 合成脚本
├── references/             # 风格库与模板
│   ├── art-styles/         # 画风定义
│   ├── layouts/            # 布局定义
│   └── ...
└── comic/                  # 输出目录（示例）
    └── {topic-slug}/       # 独立漫画项目文件夹
        ├── storyboard.md   # 分镜脚本
        ├── characters/     # 角色设定资料
        ├── prompts/        # 生成提示词
        ├── *.png           # 漫画单页
        └── {slug}.pdf      # 最终成品
```

## 🚀 快速开始

```bash
# 从文章生成（默认清线风+中性调）
/baoyu-comic article.md

# 指定风格（日漫+温馨）
/baoyu-comic story.md --art manga --tone warm

# 使用预设（欧姆社技术科普风）
/baoyu-comic tutorial.md --style ohmsha

# 交互式粘贴内容
/baoyu-comic
```

## 📝 最佳实践

- **技术教程**：推荐使用 `--style ohmsha`，它会更注重图解逻辑而非人物对话。
- **人物传记**：推荐默认的 `ligne-claire` (清线风)，类似《逻辑漫画》的质感，适合叙事。
- **语言支持**：支持 `--lang` 参数，可自动翻译脚本和对白，实现多语言漫画输出。

---
*本项目旨在探索 AI 在教育科普领域的应用，让知识传递更加生动直观。*
