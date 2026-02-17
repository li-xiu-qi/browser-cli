# SVG 复刻经验总结

## 项目背景
复刻 CPU vs GPU 架构对比图，从 PNG 转换为 SVG 矢量图。

---

##  成功经验

### 1. 布局规划优先
- **先画框架再填内容**：先创建 layout-*.svg 文件确定各元素位置，再细化角色
- **使用虚线框占位**：在布局阶段用 `stroke-dasharray` 标记未来元素位置
- **预留足够间距**：文字、图形之间至少保留 20-30px 间隙

### 2. 角色设计技巧
- **使用 `<defs>` + `<use>` 复用**：相同角色（如 12 个小黄人）只定义一次
- **相对坐标系**：角色内部使用相对坐标 (0,0)，外部用 transform 定位
- **简化细节**：扁平化风格比复杂渐变更适合技术图解

### 3. 避免重叠的策略
```svg
<!-- 分层布局法 -->
<!-- 第1层：标题 -->
<!-- 第2层：对话框（放在人物上方，y 坐标较小） -->
<!-- 第3层：人物主体 -->
<!-- 第4层：底部标签/说明 -->
```

### 4. 对话框实现

#### 基础版本（尖角）
```svg
<rect x="0" y="0" width="100" height="40" rx="6" fill="#f4d03f"/>
<path d="M0,30 L-8,38 L0,38 Z" fill="#f4d03f"/>
```

#### 云朵状优化版本
```svg
<path d="M10,0 h90 a8,8 0 0 1 8,8 v18 a8,8 0 0 1 -8,8 h-75 
         l-6,10 l-2,-10 h-7 a8,8 0 0 1 -8,-8 v-18 a8,8 0 0 1 8,-8 z" 
      fill="#fce029" stroke="#d4a00f"/>
```

**关键点**：
- `l-6,10 l-2,-10` 创建小尖角（指向人物）
- `a8,8` 圆角半径保持一致
- 尖角高度 10px，宽度 8px
- 云朵对话框自带指向功能，无需额外连接线

### 5. 配色方案

| 元素 | 颜色值 | 用途 |
|------|--------|------|
| 背景 | `#0d1117` → `#161b22` | 页面渐变背景 |
| 卡片 | `#1c2128` → `#13171d` | 内容区域背景 |
| 小黄人 | `#fce029` | 小黄人身体、强调文字 |
| 教授西装 | `#0d2137` | 教授衣服 |
| 教授头发 | `#0f2744` | 头发、鬓角 |
| 指挥官 | `#1e5aa8` | 制服、帽子 |
| 强调文字 | `#58a6ff` | 蓝色高亮文字 |
| 边框 | `#2d4a6f` | 卡片边框 |
| 对话框边框 | `#4a7c9b` | 教授对话框 |

---

##  常见错误与解决

### 1. 元素重叠
**现象**：文字和图形重叠在一起

**原因**：
- y 坐标计算错误，未考虑元素高度
- 使用 transform 时坐标系混乱

**解决**：
```javascript
// 计算元素位置时考虑完整高度链
标题_y = 38
标题高度 = 约 20px
间距 = 20px

教授_y = 标题_y + 标题高度 + 间距
对话框_y = 教授_y - 教授高度 - 间距 - 对话框高度
```

### 2. 中文括号问题
**错误**：
```svg
<g transform="translate（720, 110）">  <!-- 错误：全角括号 -->
```

**解决**：
```svg
<g transform="translate(720, 110)">   <!-- 正确：半角括号 -->
```

### 3. 颜色不一致
**问题**：同一角色的颜色在不同地方不一致

**解决**：使用 `<defs>` 定义颜色常量：
```svg
<defs>
  <style>
    .minion-yellow { fill: #fce029; }
    .professor-blue { fill: #0d2137; }
  </style>
</defs>
```

### 4. 文字对齐问题
**技巧**：
```svg
<!-- 水平居中 -->
text-anchor="middle"

<!-- 垂直居中（需配合 y 坐标调整） -->
dominant-baseline="middle"

<!-- 实际使用 -->
<text x="100" y="50" text-anchor="middle" dominant-baseline="middle">文字</text>
```

### 5. SVG 坐标系混乱
**理解**：
- SVG 坐标原点在左上角
- y 轴向下为正
- transform 会创建新的坐标系

**建议**：
- 先定义角色在 (0,0)
- 再用 transform 移动到正确位置
- 避免嵌套过深的 transform

---

## ️ 调试技巧

### 1. 可视化边界
```svg
<!-- 给元素添加红色边框调试 -->
<g transform="translate(100, 100)" stroke="red" stroke-width="1">
  <!-- 内容 -->
</g>
```

### 2. 半透明显示
```svg
<rect x="0" y="0" width="100" height="100" fill="red" opacity="0.3"/>
```

### 3. 分步验证
1. 先画背景和边框
2. 再添加静态文字
3. 最后添加角色和交互元素

---

##  文件组织建议

```
svg-test/
├── docs/                          # 文档
│   ├── svg-lessons-learned.md    # 本文件
│   └── README.md                 # 项目说明
├── components/                    # 可复用组件
│   ├── professor.svg
│   ├── minion.svg
│   └── commander.svg
├── layouts/                       # 布局草稿
│   ├── cpu-section.svg
│   └── gpu-section.svg
├── assets/                        # 参考图
│   ├── baseline.png
│   └── reference.png
└── cpu-gpu-architecture.svg      # 最终文件
```

---

##  进阶技巧

### 1. 响应式 SVG
```svg
<svg viewBox="0 0 1422 690" preserveAspectRatio="xMidYMid meet">
```

### 2. 阴影效果
```svg
<defs>
  <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="2"/>
    <feOffset dx="1" dy="2" result="offsetblur"/>
    <feComponentTransfer>
      <feFuncA type="linear" slope="0.25"/>
    </feComponentTransfer>
    <feMerge> 
      <feMergeNode/>
      <feMergeNode in="SourceGraphic"/> 
    </feMerge>
  </filter>
</defs>

<g filter="url(#softShadow)">
  <!-- 带阴影的内容 -->
</g>
```

### 3. 渐变背景
```svg
<linearGradient id="bgGradient" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0%" style="stop-color:#0d1117"/>
  <stop offset="100%" style="stop-color:#161b22"/>
</linearGradient>

<rect width="100%" height="100%" fill="url(#bgGradient)"/>
```

### 4. 简化路径
使用 [SVG Path Editor](https://yqnn.github.io/svg-path-editor/) 可视化编辑路径。

---

##  性能优化

### 1. 减少节点数
- 使用 `<use>` 复用重复元素
- 合并路径命令

### 2. 优化渲染
- 避免过度使用滤镜
- 使用 `transform` 代替修改坐标

---

##  PNG 到 SVG 复刻流程

### Step 1: 分析原图
1. 打开原图，记录整体尺寸（如 1422x690）
2. 识别主要区域划分（如左右分栏）
3. 统计可复用的元素（如小黄人 x12）

### Step 2: 搭建框架
```svg
<svg viewBox="0 0 1422 690">
  <!-- 背景 -->
  <rect width="1422" height="690" fill="#0d1117"/>
  
  <!-- 左侧区域 -->
  <g transform="translate(50, 100)">
    <rect width="640" height="550" fill="#1c2128"/>
  </g>
  
  <!-- 右侧区域 -->
  <g transform="translate(720, 100)">
    <rect width="640" height="550" fill="#1c2128"/>
  </g>
</svg>
```

### Step 3: 创建组件
1. 在 `<defs>` 中定义角色（小黄人、教授、指挥官）
2. 使用相对坐标 (0,0) 定义
3. 测试组件显示效果

### Step 4: 布局定位
1. 用虚线框标记各元素位置
2. 逐步替换为实际组件
3. 调整间距避免重叠

### Step 5: 细节优化
1. 调整颜色与原图一致
2. 优化对话框形状
3. 添加文字标签

### Step 6: 验证
1. 在不同缩放比例下查看
2. 检查是否有重叠
3. 对比原图确认还原度

---

##  推荐工具

| 工具 | 用途 |
|------|------|
| Figma/Sketch | 测量原图尺寸和颜色 |
| SVG Path Editor | 可视化编辑路径 |
| SVG Viewer | 实时预览 SVG |
| Chrome DevTools | 调试 SVG 样式 |

---

## 版本记录

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-02-06 | v1.0 | 初始版本，完成 CPU/GPU 架构图复刻 |
| 2026-02-06 | v1.1 | 优化对话框为云朵状，修复重叠问题 |
| 2026-02-06 | v1.2 | 优化小黄人眼睛设计，完善文档 |
