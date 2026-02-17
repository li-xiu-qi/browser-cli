# 强调文字颜色修复说明

## 问题描述

在使用 mp-preview 插件时，发现以下现象：

- **复制到公众号后**：加粗文字（`<strong>`）显示为正确的主题颜色（如优雅主题的紫色 `#553C9A`）✅
- **Obsidian 预览界面**：加粗文字显示为黑色/深灰色 ❌

## 根本原因

Obsidian 编辑器本身有一套默认的 CSS 样式，其中对 `<strong>` 和 `<em>` 元素定义了默认颜色（通常是黑色或深灰色）。

当插件通过 JavaScript 给元素设置 `style` 属性时，由于 Obsidian 默认样式的 CSS 选择器优先级更高，导致主题配置的颜色被覆盖。

### 样式优先级分析

```
1. Obsidian 默认 CSS: .markdown-preview-view strong { color: var(--text-normal); }
   ↓ 优先级更高
2. 插件内联样式: <strong style="color: #553C9A;">
   ↓ 被覆盖
3. 最终结果: 显示为黑色（Obsidian 默认颜色）
```

## 修复方案

### 方案一：CSS 层修复

在 `styles.css` 中添加基础样式，确保颜色可继承：

```css
.mp-content-section strong {
  color: inherit;
}

.mp-content-section em {
  color: inherit;
}
```

### 方案二：JavaScript 层修复（主要方案）

在 `templateManager.ts` 中，给颜色样式添加 `!important`，强制覆盖 Obsidian 默认样式：

```typescript
// 确保颜色应用 !important 以覆盖 Obsidian 默认样式
const strongStyleWithImportant = strongStyle.replace(/color:\s*([^;]+);/, 'color: $1 !important;');
const emStyleWithImportant = emStyle.replace(/color:\s*([^;]+);/, 'color: $1 !important;');
const delStyleWithImportant = delStyle.replace(/color:\s*([^;]+);/, 'color: $1 !important;');

element.querySelectorAll('strong').forEach(el => {
    el.setAttribute('style', `${strongStyleWithImportant} font-family: ${this.currentFont} !important;`);
});
```

### 修复后的效果

```html
<!-- 修复前 -->
<strong style="font-weight: bold; color: #553C9A; font-family: KaiTi;">
  文字显示为黑色（被 Obsidian 覆盖）
</strong>

<!-- 修复后 -->
<strong style="font-weight: bold; color: #553C9A !important; font-family: KaiTi !important;">
  文字显示为紫色（强制应用主题色）
</strong>
```

## 相关文件

- `src/templateManager.ts` - 应用模板样式的核心逻辑
- `styles.css` - 插件的基础 CSS 样式
- `src/templates/*.json` - 各主题的样式配置

## 测试验证

1. 选择任意主题（如优雅主题、橙心主题）
2. 在 Markdown 中使用 `**加粗文字**`
3. 在 Obsidian 右侧预览面板检查颜色是否为主题色
4. 点击"复制到公众号"，粘贴到微信编辑器检查颜色是否一致

## 注意事项

- 所有预设主题（default, scarlet, orange, elegant, dark 等）的 `emphasis` 配置均已更新
- 自定义模板如果手动编辑过，可能需要重新选择参考模板来同步最新配置
- 如果用户通过 Style Settings 等插件自定义了 Obsidian 主题，可能需要检查是否有冲突

## 主题配置示例

以优雅主题为例：

```json
{
  "emphasis": {
    "strong": "font-weight: bold; color: #553C9A;",
    "em": "font-style: italic; color: #805AD5;",
    "del": "text-decoration: line-through; color: #9F7AEA;"
  }
}
```

各强调元素的配色逻辑：
- **strong（加粗）**: 主题深色（最深）
- **em（斜体）**: 主题主色（中等）
- **del（删除线）**: 主题浅色（最浅）
