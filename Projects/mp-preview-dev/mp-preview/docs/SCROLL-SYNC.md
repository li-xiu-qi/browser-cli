# 同步滚动功能说明

## 功能概述

mp-preview 插件现在支持基于锚点的同步滚动功能，类似于 markdown-preview-enhanced 的实现方式。

## 核心特性

### 1. 基于锚点的定位

不同于简单的百分比同步，本功能使用**内容锚点**实现精准同步：

- **data-source-line**: 每个预览元素（标题、段落、列表等）都标记了对应的 Markdown 源文件行号
- **标题匹配**: 通过标题文本内容精确匹配源文件行号
- **近似估算**: 对于无法精确匹配的元素，基于最近标题行号进行智能估算

### 2. 双向交互

- **预览 → 编辑器**: 点击预览中的任意元素，自动跳转到编辑器对应位置
- **高亮提示**: 当前可见的预览元素会高亮显示，便于定位

### 3. 使用方法

1. **开启同步**: 点击工具栏中的 🔗 图标按钮
   - 按钮变为紫色表示已开启
   - 图标变为 🔗 表示可点击跳转

2. **点击跳转**: 在预览中点击任意段落、标题或列表项
   - 编辑器会自动跳转到对应位置
   - 光标定位到该行开头

3. **关闭同步**: 再次点击 🔗 按钮即可关闭

## 技术实现

### 行号映射机制

```typescript
// 1. 精确匹配 - 标题
const headingText = heading.textContent;
for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes(headingText)) {
        heading.setAttribute('data-source-line', String(i));
        break;
    }
}

// 2. 近似估算 - 其他元素
const estimatedLine = lastHeadingLine + blockIndex;
element.setAttribute('data-source-line', String(estimatedLine));
```

### 点击跳转流程

```
用户点击预览元素
    ↓
获取 data-source-line 属性
    ↓
调用 editor.setCursor({line, ch: 0})
    ↓
编辑器跳转到对应行
```

### CSS 交互效果

```css
/* 可点击元素 */
[data-scroll-anchor] {
    cursor: pointer;
    border-left: 3px solid transparent;
}

/* 悬停效果 */
[data-scroll-anchor]:hover {
    background-color: rgba(128, 90, 213, 0.08);
    border-left-color: #805AD5;
}

/* 当前可见元素 */
.mp-scroll-active {
    background-color: rgba(128, 90, 213, 0.12);
}
```

## 适用场景

- ✅ 长文档编辑时快速定位
- ✅ 对照预览修改源文件
- ✅ 查看特定段落在源文件中的位置

## 限制说明

由于 Obsidian API 限制，目前实现为**预览 → 编辑器单向同步**：

- ✅ 点击预览 → 跳转编辑器
- ❌ 编辑器滚动 → 自动同步预览（需要 Obsidian 内部 API）

如需双向同步，建议结合 Obsidian 原生分屏功能使用。

## 相关文件

- `src/scrollSync.ts` - 同步滚动核心逻辑
- `src/view.ts` - UI 集成
- `styles.css` - 交互样式
