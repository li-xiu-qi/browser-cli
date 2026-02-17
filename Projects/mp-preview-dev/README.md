# MP Preview 编辑器改造项目

## 项目说明

本项目用于改造 Obsidian 插件 mp-preview，使其支持更多功能，以更好地编辑和预览 Markdown 文章，特别是针对微信公众号排版优化。

## 来源

- 原项目：https://github.com/li-xiu-qi/mp-preview
- 克隆时间：2026-02-08
- 当前位置：`Projects/mp-preview-dev/mp-preview/`

## 当前痛点

在编辑模型评测文章时遇到以下编辑器不支持的功能：

1. **表格中嵌套图片/视频** - 当前编辑器无法渲染表格内的媒体元素
2. **LaTeX 公式渲染** - 数学公式无法正确显示
3. **视频嵌入支持** - 不支持 `<video>` 标签，需手动转 GIF
4. **代码块样式** - 需要更好的代码高亮

## 临时解决方案（视频转 GIF）

由于编辑器不支持视频，目前使用 FFmpeg 将视频转为 GIF。

### 预先压缩策略

**重要**：在生成或转换 GIF 时，应预先进行压缩，避免文件过大（微信公众号限制 <5MB）。

根据原视频时长选择压缩参数：

| 原视频时长 | 推荐参数 | 预期大小 |
|-----------|---------|---------|
| < 20秒 | `fps=4,scale=720:-1,max_colors=128` | 2-5 MB |
| 20-40秒 | `fps=3,scale=480:-1,max_colors=64` | 2-4 MB |
| 40-70秒 | `fps=2,scale=360:-1,max_colors=32` | 2-3 MB |

### 压缩命令

```bash
# 轻度压缩（短视频 <20s）
ffmpeg -i input.mp4 -vf "fps=4,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse" -loop 0 output.gif

# 中度压缩（中等视频 20-40s）
ffmpeg -i input.mp4 -vf "fps=3,scale=480:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=64[p];[s1][p]paletteuse=dither=bayer" -loop 0 output.gif

# 重度压缩（长视频 >40s）
ffmpeg -i input.mp4 -vf "fps=2,scale=360:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=32[p];[s1][p]paletteuse=dither=bayer" -loop 0 output.gif
```

### 限制要求
- 文件大小不超过 5MB（微信公众号限制）
- 帧数不超过 300 帧
- 宽度建议 360-720px（根据时长调整）
- 颜色数建议 32-128 色（根据时长调整）

### 实际案例

本次项目中 6 个演示视频的压缩结果：
- Earth.gif (16s): 1.18 MB ✓
- Agentic_Coding_with_text.gif (45s): 1.36 MB ✓
- Deepresearch_explore.gif (67s): 1.87 MB ✓
- Ocean_v2_4k.gif (39s): 2.09 MB ✓
- DataAnaly_en_4k_v2.gif (42s): 3.17 MB ✓
- SolarDisplay.gif (48s): 3.72 MB ✓

## 计划改造功能

- [ ] 支持表格中嵌套图片和视频
- [ ] 支持 LaTeX 数学公式渲染
- [ ] 支持 `<video>` 标签嵌入（或自动转 GIF 预览）
- [ ] 优化 Markdown 排版兼容性

## 项目结构

```
Projects/mp-preview-dev/
├── mp-preview/           ← 插件源代码（软链接到 .obsidian/plugins/mp-preview）
│     ├── src/            ← TypeScript 源码
│     ├── package.json
│     └── ...
└── README.md             ← 本文件
```

## 开发环境

### 目录结构

插件已通过目录联接(junction)链接到 Obsidian：
```
.obsidian/plugins/mp-preview  →  Projects/mp-preview-dev/mp-preview
```

### 热重载 (Hot Reload)

本项目已集成 [Hot Reload](https://github.com/pjeby/hot-reload) 插件，开发时自动重载插件。

**使用方法**：
1. 在 Obsidian 中启用 Hot Reload 插件
2. 运行 `npm run dev` 进入开发模式（自动监听文件变化并编译）
3. 修改 `mp-preview/src/` 下的源代码
4. Hot Reload 会自动检测 `main.js` 变化并重载插件

**手动启用热重载**：
- 命令面板 → "Hot Reload: Watch for changes" → 选择 `mp-preview`

**安装依赖并开始开发**：
```bash
cd mp-preview
npm install
npm run dev
```

## 相关文章

本项目主要用于支持 `阶跃Step-3.5-Flash模型评测` 文章的编辑工作。
