---
name: remotion-renderer
description: 基于 Remotion 的视频渲染工具，将 React 组件渲染为视频文件。
version: 1.0.0
---

# Remotion Renderer Skill

基于 [Remotion](https://www.remotion.dev/) 的视频渲染工具，将 React/TypeScript 组件渲染为 MP4 视频。

## 工具位置

- **工具脚本**: `skills/remotion-renderer/tools/`
- **入口**: `tools/render.mjs`

## 功能特点

-  将 React/TypeScript 组件渲染为 MP4 视频
-  支持有头/无头浏览器模式
-  自动检测 Chrome/Edge 浏览器
-  使用 Webpack 打包

## 安装依赖

```powershell
cd .agents/skills/remotion-renderer/tools
npm install
```

**依赖说明**: 本工具需要独立的 node_modules（在 tools/ 目录内），包含：
- `@remotion/bundler` - Remotion 打包器
- `@remotion/renderer` - Remotion 渲染器

## 使用方法

```powershell
# 默认输出到 output.mp4
cd .agents/skills/remotion-renderer/tools
node render.mjs

# 指定输出路径
node render.mjs ./videos/my-video.mp4
```

## 配置

### 入口文件

在 `tools/render.mjs` 中修改入口文件路径：

```javascript
const bundleLocation = await bundle({
  entryPoint: path.resolve('src/index.ts'),  // 修改这里
  webpackOverride: (config) => config,
});
```

### Composition ID

确保你的 Remotion 组件导出了名为 `UserComposition` 的 composition：

```typescript
// tools/src/index.ts
export const UserComposition = () => {
  // 你的视频组件
};
```

## 浏览器检测

工具会自动按以下顺序查找浏览器：
1. `C:\Program Files\Google\Chrome\Application\chrome.exe`
2. `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`

## 渲染配置

当前配置：
- **编码器**: H.264
- **GL 后端**: ANGLE
- **浏览器模式**: 有头模式 (headless: false)

## 注意事项

- 首次运行会自动下载 Chromium
- 渲染过程会显示浏览器窗口（当前配置）
- 确保有足够的磁盘空间用于临时文件

## 相关资源

- [Remotion 文档](https://www.remotion.dev/docs/)
- [Remotion GitHub](https://github.com/remotion-dev/remotion)
