# AI 友好的可视化工具索引

你好！这是一份整理好的 AI 友好可视化工具清单。这些工具通常支持通过代码或文本描述来生成图像/模型，非常适合与 AI 配合使用。

## 结构与关系图

### Graphviz
- **简介**: 老牌的开源图形可视化软件。使用 DOT 语言描述图形结构，特别适合生成流程图、网络图和依赖关系图。
- **官网下载**: [https://graphviz.org/download/](https://graphviz.org/download/)
- **源码仓库**: [https://gitlab.com/graphviz/graphviz/](https://gitlab.com/graphviz/graphviz/)
- **AI 适用性**: ⭐⭐⭐⭐⭐ (AI 非常擅长编写 DOT 代码)

### Mermaid
- **简介**: 基于 JavaScript 的绘图工具，支持在 Markdown 中直接渲染流程图、时序图、甘特图等。
- **官网**: [https://mermaid.js.org/](https://mermaid.js.org/)
- **AI 适用性**: ⭐⭐⭐⭐⭐ (主流 AI 均熟练掌握 Mermaid 语法)

### D2 (Declarative Diagramming)
- **简介**: 一种现代化的图表脚本语言，旨在将文本转换为图表。它专注于声明式绘图，语法简洁且功能强大，支持多种布局引擎（如 dagre, elk）。
- **官网**: [https://d2lang.com/](https://d2lang.com/)
- **源码与下载**: [https://github.com/terrastruct/d2/releases](https://github.com/terrastruct/d2/releases)
- **AI 适用性**: ⭐⭐⭐⭐⭐ (语法清晰，非常适合 LLM 生成结构化描述)

## 数据可视化

### Vega-Lite
- **简介**: 一种交互式图形的高级语法。它通过简洁的 JSON 格式（Declarative JSON syntax）来定义可视化，类似于 ggplot2 或 Tableau 的理念。非常适合生成统计图表（如散点图、柱状图、热力图等）。
- **官网**: [https://vega.github.io/vega-lite/](https://vega.github.io/vega-lite/)
- **文档**: [https://vega.github.io/vega-lite/docs/](https://vega.github.io/vega-lite/docs/)
- **AI 适用性**: ⭐⭐⭐⭐⭐ (AI 可以轻松生成符合规范的 JSON配置)

## 代码驱动的视频与动画

### Manim
- **简介**: 一个用于创建精确数学动画的动画引擎（由 3Blue1Brown 开发）。适合制作高质量的解释性视频。
- **安装指南 (使用 uv)**: [https://docs.manim.community/en/stable/installation/uv.html](https://docs.manim.community/en/stable/installation/uv.html)
- **推荐安装方式**: 官方推荐使用 `uv` 进行 Python 环境管理和安装，比纯 pip 更稳定。
- **AI 适用性**: ⭐⭐⭐⭐ (AI 可以生成 Python 脚本来制作动画)

### Revideo
- **简介**: 一个基于 TypeScript 和 React 的高性能视频创作框架。它允许开发者像编写网页应用一样编写视频，支持复杂的动画和音频集成。
- **官网与安装**: [https://docs.re.video/installation-and-setup/](https://docs.re.video/installation-and-setup/)
- **源码仓库**: [https://github.com/redotvideo/revideo](https://github.com/redotvideo/revideo)
- **AI 适用性**: ⭐⭐⭐⭐ (基于 TS/React 语法，非常适合大模型辅助开发视频逻辑)

### Motion Canvas
- **简介**: 一个用于创建代码驱动型动画的 TypeScript 库。它提供了一个基于 Web 的编辑器，支持实时预览，使用生成器函数（Generators）来描述复杂的动画流程。
- **官网**: [https://motioncanvas.io/](https://motioncanvas.io/)
- **文档**: [https://motioncanvas.io/docs/quickstart](https://motioncanvas.io/docs/quickstart)
- **源码仓库**: [https://github.com/motion-canvas/motion-canvas](https://github.com/motion-canvas/motion-canvas)
- **AI 适用性**: ⭐⭐⭐⭐⭐ (TypeScript 结合生成器语法，逻辑清晰，AI 编写动画脚本的成功率极高)


## 3D 建模

### OpenSCAD
- **简介**: "程序员的 3D CAD 建模器"。不同于交互式建模软件，它通过编写脚本代码来创建 3D 模型。
- **下载地址**: [https://openscad.org/downloads.html](https://openscad.org/downloads.html)
- **源码**: [https://github.com/openscad/openscad/](https://github.com/openscad/openscad/)
- **特点**: 
  - 专注于 CAD 及其部件的设计，而非艺术 3D 建模。
  - 支持参数化设计。
- **AI 适用性**: ⭐⭐⭐⭐⭐ (AI 可以生成 SCAD 脚本来构建 3D 物体)


