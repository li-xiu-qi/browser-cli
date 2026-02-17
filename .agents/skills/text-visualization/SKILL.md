---
name: text-visualization
description: 文本可视化专家。提供多种文本可视化方案：Graphviz图表、HTML表格模板、JSON Canvas画板。
---

# 文本可视化

**定位**: 将文本数据转化为可视化图形的解决方案  
**适用场景**:
- 场景1: Graphviz 图表（流程图、架构图、关系图）
- 场景2: HTML 表格（文章配图、数据可视化）
- 场景3: JSON Canvas（无限画布、思维导图）

---

## 快速选择指南

| 你的需求 | 选择场景 | 工具路径 |
|----------|----------|----------|
| 绘制流程图、架构图、关系图 | [[#场景1 Graphviz 图表\|场景1]] | 系统安装 `dot` 命令 |
| 创建风格化表格用于文章配图 | [[#场景2 HTML 表格模板\|场景2]] | `templates/html-tables/` |
| 制作思维导图、无限画布 | [[#场景3 JSON Canvas\|场景3]] | 手动编辑 `.canvas` 文件 |

---

## 场景1: Graphviz 图表

**用途**: 创建高质量的流程图、架构图、关系图

**前置要求**: 安装 Graphviz (`winget install Graphviz`)

**使用方式**:

```powershell
# DOT 转 SVG
dot -Tsvg input.dot -o output.svg

# DOT 转 PNG（高 DPI）
dot -Tpng -Gdpi=300 file.dot -o file.png

# 不同布局引擎
neato -Tsvg file.dot -o file.svg    # 力导向布局
circo -Tsvg file.dot -o file.svg    # 环形布局
```

**最佳实践**:
- 控制节点数在 15-25 个以内
- 不要用于时序图（用 PlantUML/Mermaid 替代）
- 不要强制设置 size，让 Graphviz 自动计算

**详细文档**: `templates/graphviz/README.md`

---

## 场景2: HTML 表格模板

**用途**: 创建风格化表格用于文章配图、技术文档、数据可视化

**模板数量**: 50+ 风格模板

**分类**:
| 分类 | 数量 | 示例 |
|------|------|------|
| 基础笔记风格 | 37 | 学术极简、日式方格、深色模式 |
| 技术文档图表 | 8 | Graphviz风格、API文档、流程图 |
| 编辑设计风格 | 5 | 杂志风、包豪斯、侘寂 |
| 现代风格 | 6 | 瑞士网格、粗野主义、北欧 |

**使用方式**:

1. 复制模板: `templates/html-tables/sources/XX-模板名.html`
2. 编辑内容（修改数据、文字）
3. 浏览器打开 → 截图生成 PNG

**预览**: `templates/html-tables/previews/` 目录下有所有模板的预览图

**详细文档**: `templates/html-tables/README.md`

---

## 场景3: JSON Canvas

**用途**: 创建和编辑 JSON Canvas 文件（Obsidian 无限画布格式）

**文件格式**: `.canvas` 文件，遵循 [JSON Canvas Spec 1.0](https://jsoncanvas.org/spec/1.0/)

**基本结构**:
```json
{
  "nodes": [],
  "edges": []
}
```

**节点类型**:
- `text` - 文本内容（支持 Markdown）
- `file` - 引用文件/附件
- `link` - 外部 URL
- `group` - 视觉容器

**详细文档**: `templates/json-canvas/README.md`

---

## 对比与选择

| 维度 | Graphviz | HTML表格 | JSON Canvas |
|------|----------|----------|-------------|
| **最佳用途** | 流程图、架构图 | 数据表格、对比表 | 思维导图、白板 |
| **输出格式** | SVG/PNG | HTML → PNG | `.canvas` |
| **交互性** | 静态 | 静态 | Obsidian中可交互 |
| **学习曲线** | 中等 | 低 | 低 |
| **风格化** | 有限 | 丰富（50+模板） | 基础 |

---

## 来源说明

本 Skill 合并自：
- `graphviz-best-practices`: Graphviz 图表最佳实践
- `html-table-templates`: HTML 表格模板库（50+模板）
- `json-canvas`: JSON Canvas 规范
