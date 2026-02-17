# CSS 优先级与 !important 技术解析

## 问题现象

加粗文字颜色修复经历了三个阶段：

1. **初始状态**：复制到公众号紫色正确，Obsidian 预览黑色 ❌
2. **第一次修复**：加 `!important` 后预览紫色正确，但偏暗/发黑 ❌
3. **最终修复**：在 CSS 层加 `!important` 后颜色正确 ✅

## 根本原因分析

### 三层样式叠加

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: CSS 文件 (styles.css)                              │
│  .mp-content-section strong { color: #805AD5 !important; }   │
│  ✅ 优先级最高，因为在外部 CSS 文件且用 !important           │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: JS 内联样式 (templateManager.ts)                   │
│  <strong style="color: #805AD5 !important; ...">             │
│  ⚠️ 被 CSS 层覆盖或 Obsidian 主题干扰                       │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Obsidian 默认主题                                  │
│  .markdown-preview-view strong { color: var(--text-normal); }│
│  ❌ 初始覆盖源                                               │
└─────────────────────────────────────────────────────────────┘
```

### 为什么 JS 层加 `!important` 不够？

Obsidian 的样式系统中，某些主题（包括默认主题）可能对 `strong` 有复杂的样式规则：

```css
/* Obsidian 可能的样式 */
.markdown-preview-view strong {
  color: var(--text-normal) !important;  /* 有些主题自己也用 !important */
}

/* 或者父级继承 */
.markdown-preview-view {
  color: #333;  /* 父级颜色通过继承影响 strong */
}
```

当 JS 设置 `element.style.color` 时，如果 Obsidian 的主题 CSS 在 **更高的选择器层级** 也使用了 `!important`，就会产生冲突。

### 为什么 CSS 层的 `!important` 能生效？

```css
/* styles.css 作为插件样式加载 */
.mp-content-section strong {
  color: #805AD5 !important;
}
```

1. **选择器特异性**：`.mp-content-section strong` 比 Obsidian 的 `.markdown-preview-view strong` 更具体
2. **加载顺序**：插件 CSS 在 Obsidian 主题之后加载，后加载的 `!important` 规则优先级更高
3. **作用域隔离**：`.mp-content-section` 是插件特有的 class，不受 Obsidian 主题变量影响

## 代码对比

### 方案 A：仅 JS 层（不够）
```typescript
element.querySelectorAll('strong').forEach(el => {
    el.setAttribute('style', `color: #805AD5 !important; font-family: ${font} !important;`);
});
```
**结果**：颜色仍然偏暗/发黑

### 方案 B：JS + CSS 层（正确）
```typescript
// JS 层：确保字体生效
element.querySelectorAll('strong').forEach(el => {
    el.setAttribute('style', `color: #805AD5 !important; font-family: ${font} !important;`);
});
```
```css
/* CSS 层：最终颜色保险 */
.mp-content-section strong {
  color: #805AD5 !important;
}
```
**结果**：颜色完全正确 ✅

## 最佳实践总结

对于需要**精确控制颜色**的样式：

1. **字体类样式**：在 JS 层用 `!important` 强制应用
2. **颜色类样式**：同时在 CSS 层用 `!important` 兜底
3. **保持两层一致**：JS 和 CSS 使用相同的颜色值

## 相关文件

- `styles.css` - 第 397-403 行，CSS 层颜色定义
- `src/templateManager.ts` - 第 182-201 行，JS 层样式应用
- `src/templates/elegant.json` - 主题配置（颜色值应与 CSS 保持一致）

## 注意事项

⚠️ **当前实现限制**：CSS 层写死了 `#805AD5` 紫色，这意味着：
- 优雅主题 ✅ 颜色正确
- 其他主题 ⚠️ 也会显示紫色（而非各自的主题色）

**如需多主题支持**，应移除 CSS 层的固定颜色，改为：
```css
.mp-content-section strong {
  color: inherit !important;  /* 继承父级或内联样式 */
}
```

然后在 JS 层确保颜色通过 `!important` 正确注入。
