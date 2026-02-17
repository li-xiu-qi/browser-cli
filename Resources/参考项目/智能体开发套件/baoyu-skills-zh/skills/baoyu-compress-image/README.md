# baoyu-compress-image (智能图片压缩工具)

这是一个智能图片压缩 CLI 工具，旨在通过自动选择最佳底层工具，将图片压缩为 WebP 或优化的 PNG 格式。它封装了多种压缩后端，为用户提供统一、简单的调用接口。

## 🌟 核心特性

- **智能工具链 (Smart Toolchain)**：自动检测系统环境，按优先级调用最佳工具：
  1.  `sips` (macOS 原生，速度极快)
  2.  `cwebp` (Google WebP 官方工具)
  3.  `ImageMagick` (通用图像处理)
  4.  `Sharp` (Node.js 高性能库)
- **极简接口**：无需关心底层复杂的参数，只需指定输入输出和质量即可。
- **批量处理**：支持递归扫描目录 (`-r`)，批量处理整个文件夹的图片。
- **格式灵活**：默认转换为高效的 WebP，也支持 PNG 和 JPEG。

## 🛠️ 使用方法

该工具主要通过 CLI 脚本运行：

```bash
# 基础用法：将图片压缩为 WebP (默认)
npx -y bun ${SKILL_DIR}/scripts/main.ts image.png

# 保持原始格式 (如 PNG 转 压缩PNG)
npx -y bun ${SKILL_DIR}/scripts/main.ts image.png --keep

# 递归压缩整个目录，质量设为 75
npx -y bun ${SKILL_DIR}/scripts/main.ts ./photos/ -r -q 75

# 转换为 JSON 输出 (适合程序集成)
npx -y bun ${SKILL_DIR}/scripts/main.ts input.jpg --json
```

## ⚙️ 配置 (EXTEND.md)

支持通过 `EXTEND.md` 文件进行持久化配置，支持项目级和用户级配置。

**支持的配置项：**
- `default_format`: 默认输出格式 (webp/png/jpeg)
- `default_quality`: 默认压缩质量 (0-100)
- `keep_original`: 是否默认保留原图

## 📂 脚本结构

```text
baoyu-compress-image/
├── SKILL.md          # 技能定义与文档
└── scripts/
    └── main.ts       # 核心 CLI 逻辑实现
```

---
*这个工具通常作为其他技能（如漫画生成、网页截图）的依赖组件使用，用于优化生成的中间产物，减少 Token 消耗和存储空间。*
