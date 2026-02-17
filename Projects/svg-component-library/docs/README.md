# SVG 复刻项目 - CPU vs GPU 架构图

## 项目简介
将 PNG 格式的 CPU vs GPU 架构对比图转换为高质量 SVG 矢量图。

## 文件结构

```
svg-test/
├── docs/                          # 文档目录
│   ├── README.md                 # 项目说明
│   └── svg-lessons-learned.md    # 经验总结
├── cpu-gpu-architecture.svg      # 最终完整 SVG 文件
├── baseline.png                  # 原图参考
├── 45e48f1324cd466cbc535c66727ea4f1.png  # 原始 PNG
│
├── 组件文件（独立角色）
├── professor.svg                 # 教授角色
├── minion.svg                    # 小黄人角色
├── commander.svg                 # 指挥官角色
│
└── 布局文件（框架草稿）
    ├── layout-cpu-section.svg    # CPU 区域布局
    └── layout-gpu-section.svg    # GPU 区域布局
```

## 主要特性

-  完全矢量，可无损缩放
-  使用 `<defs>` + `<use>` 高效复用组件
-  云朵状对话框设计
-  扁平化风格，符合现代设计
-  无字体依赖（使用系统字体）

## 技术亮点

### 1. 组件化设计
所有角色在 `<defs>` 中定义，通过 `<use>` 复用：
- 12 个小黄人只定义一次
- 2 个教授使用同一组件

### 2. 云朵状对话框
使用 SVG Path 实现柔和圆角和尖角：
```svg
<path d="M10,0 h90 a8,8 0 0 1 8,8 v18 a8,8 0 0 1 -8,8 h-75 
         l-6,10 l-2,-10 h-7 a8,8 0 0 1 -8,-8 v-18 a8,8 0 0 1 8,-8 z" />
```

### 3. 配色方案
| 元素 | 颜色 |
|------|------|
| 背景 | `#0d1117` → `#161b22` |
| 小黄人 | `#fce029` |
| 教授西装 | `#0d2137` |
| 指挥官 | `#1e5aa8` |
| 强调文字 | `#58a6ff` |

## 预览

用浏览器打开 `cpu-gpu-architecture.svg` 即可查看效果。

## 经验总结

详见 `svg-lessons-learned.md`，包含：
- 布局规划技巧
- 避免重叠的策略
- 对话框实现方法
- 常见错误及解决

## 使用方式

### 直接使用
```html
<img src="cpu-gpu-architecture.svg" alt="CPU vs GPU">
```

### 嵌入 HTML
```html
<svg viewBox="0 0 1422 690">
  <!-- 复制 svg 内容 -->
</svg>
```

### 提取组件
```svg
<use href="cpu-gpu-architecture.svg#minion" />
```

## 尺寸信息

- **画布尺寸**: 1422 x 690 px
- **左侧区域**: 640 x 550 px
- **右侧区域**: 640 x 550 px
- **小黄人**: 50 x 70 px
- **教授**: 70 x 85 px (近似)
- **指挥官**: 70 x 78 px (近似)

## 开发记录

| 日期 | 进度 |
|------|------|
| 2026-02-06 | 完成初版，解决重叠问题 |
| 2026-02-06 | 优化对话框为云朵状 |
| 2026-02-06 | 完善文档，优化小黄人眼睛 |

## License

MIT
