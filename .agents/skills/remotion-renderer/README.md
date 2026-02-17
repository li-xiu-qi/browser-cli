# Remotion Renderer

基于 [Remotion](https://www.remotion.dev/) 的视频渲染工具，将 React 组件渲染为视频文件。

## 功能特点

-  将 React/TypeScript 组件渲染为 MP4 视频
-  支持有头/无头浏览器模式
-  自动检测 Chrome/Edge 浏览器
-  使用 Webpack 打包

## 环境要求

```bash
# 安装依赖（在 tools/ 目录）
cd .agents/skills/remotion-renderer/tools
npm install
```

依赖：
- `@remotion/bundler` - Remotion 打包器
- `@remotion/renderer` - Remotion 渲染器
- Chrome 或 Edge 浏览器

## 使用方法

```bash
cd .agents/skills/remotion-renderer/tools
node render.mjs [输出路径]
```

### 参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `output` | 输出视频文件路径 | `./output.mp4` |

### 示例

```bash
# 默认输出到 output.mp4
node render.mjs

# 指定输出路径
node render.mjs ./videos/my-video.mp4
```

## 文件结构

```
remotion-renderer/
├── SKILL.md            # 使用规范
├── README.md           # 本文件
└── tools/              # 工具脚本
    ├── render.mjs      # 渲染入口
    ├── src/            # Remotion 组件
    ├── package.json    # 依赖配置
    └── tsconfig.json   # TypeScript 配置
```

## 项目配置

### 入口文件

在 `render.mjs` 中修改入口文件路径：

```javascript
const bundleLocation = await bundle({
  entryPoint: path.resolve('src/index.ts'),  // 修改这里
  webpackOverride: (config) => config,
});
```

### Composition ID

确保你的 Remotion 组件导出了名为 `UserComposition` 的 composition：

```javascript
// src/index.ts
export const UserComposition = () => {
  // 你的视频组件
};
```

## 浏览器检测

工具会自动按以下顺序查找浏览器：
1. `C:\Program Files\Google\Chrome\Application\chrome.exe`
2. `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`

如需自定义浏览器路径，修改 `findBrowser()` 函数。

## 渲染配置

当前配置：
- **编码器**: H.264
- **GL 后端**: ANGLE
- **浏览器模式**: 有头模式 (headless: false)

如需修改，编辑 `render.mjs` 中的 `renderMedia` 配置。

## 注意事项

- 首次运行会自动下载 Chromium
- 渲染过程会显示浏览器窗口（当前配置）
- 确保有足够的磁盘空间用于临时文件

## 官方文档

- [Remotion 文档](https://www.remotion.dev/docs/)
- [Remotion GitHub](https://github.com/remotion-dev/remotion)
