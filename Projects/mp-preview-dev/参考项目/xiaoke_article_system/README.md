# Markdown 文章管理器

一个功能完整的 Markdown 文章管理全栈项目，支持本地存储、实时预览、文件管理和批量操作。

## 🎯 项目特色

- 📝 **实时编辑预览**：左侧编辑器 + 右侧实时预览，支持数学公式渲染
- 💾 **双重存储**：本地 IndexedDB + 后端文件存储，数据更安全
- 🎨 **现代化界面**：基于 Ant Design 的美观 UI，响应式布局
- ⚡ **高性能优化**：图片懒加载、滚动同步、快捷键支持
- 🔧 **统一配置**：环境配置统一管理，开发生产环境一键切换
- 📦 **批量操作**：支持文件批量删除、导出为 ZIP 包

## 📁 目录结构

```text
md_article_manager/
├── config.json                # 统一环境配置文件
├── start.js                   # 跨平台启动脚本
├── start.bat                  # Windows 启动脚本
├── validate-config.js         # 配置验证工具
├── design.md                  # 项目设计文档
├── backend/                   # 后端服务（Next.js）
│   ├── app/
│   │   ├── api/               # API 路由
│   │   │   ├── file/          # 单文件操作 API
│   │   │   └── files/         # 批量文件操作 API
│   │   └── ...                # Next.js 应用文件
│   └── data/                  # Markdown 文件存储目录
├── frontend/                  # 前端界面（React + Vite）
│   ├── src/
│   │   ├── components/        # React 组件
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── styles/            # 样式文件
│   │   └── utils/             # 工具函数
│   └── ...
└── 参考格式化逻辑/             # 格式化相关工具
    └── 文章链接处理/           # 文章链接处理工具
```

## ⚙️ 环境配置

项目使用统一的配置管理系统，支持开发和生产环境的灵活切换。

### 配置文件结构

`config.json` 为单一环境配置（不再区分 dev/prod）：

```json
{
  "frontend": {
    "port": 3335,
    "host": "localhost",
    "basePath": "/"
  },
  "backend": {
    "host": "localhost",
    "port": 4445,
    "paths": {
      "articlesDir": "data/articles",
      "imageUrlsDir": "data/image_urls",
      "markdownFilesDir": "data/markdown_files"
    }
  },
  "cors": {
    "allowedOrigins": [
      "http://localhost:3335"
    ]
  }
}
```

### 配置与启动

- 仅使用根级 `config.json` 与 `start.js`。
- `start.js` 读取配置并：
  - 为后端注入环境变量：`PORT`、`HOSTNAME`、`BACKEND_*_DIR` 三项数据目录。
  - 为前端注入环境变量：`VITE_BACKEND_HOST`、`VITE_BACKEND_PORT` 用于拼接 API 基础 URL。
- 前端通过 `import.meta.env.VITE_BACKEND_HOST/PORT` 访问后端。

### 配置验证

使用配置验证工具检查配置文件的正确性：

```bash
npm run validate-config
```

验证内容包括：

- 配置文件加载状态
- 开发/生产环境配置
- 端口冲突检查
- CORS 配置验证

## 🚀 快速开始

### 方法一：一键启动（推荐）

**Windows:**

```bash
start.bat
```

**跨平台:**

```bash
node start.js
```

启动脚本会自动：

- 读取配置文件
- 按顺序启动后端和前端服务
- 显示访问地址

### 方法二：分步安装启动

1. **安装依赖**

   ```bash
   # 安装所有依赖（根目录执行）
   npm run install
   
   # 或分别安装
   npm run install:backend
   npm run install:frontend
   ```

2. **启动服务**

   ```bash
   # 同时启动前后端（推荐）
   npm run dev
   
   # 或分别启动
   npm run dev:backend    # 启动后端
   npm run dev:frontend   # 启动前端
   ```

### 方法三：手动启动

```bash
# 后端服务
cd backend
npm install
npm run dev:win    # Windows
npm run dev        # Linux/Mac

# 前端服务
cd frontend
npm install
npm run dev
   ```

## 🌐 访问地址

默认端口：

- **前端界面**: <http://localhost:3335>
- **后端 API**: <http://localhost:4445>

可通过修改 `config.json` 自定义端口和主机地址。

## 📚 使用指南

### 前端获取 API 基础 URL 示例

```js
// frontend/src/config/api.js
export function getApiBaseUrl() {
  const host = import.meta.env.VITE_BACKEND_HOST || 'localhost';
  const port = import.meta.env.VITE_BACKEND_PORT || '4445';
  return `http://${host}:${port}`;
}
export const API_BASE_URL = getApiBaseUrl();
```

### 主要功能

#### 📝 Markdown 编辑

- **实时预览**：编辑器与预览区同步显示
- **数学公式**：支持 LaTeX 数学公式渲染
- **GFM 支持**：GitHub Flavored Markdown 完整支持
- **快捷键**：Ctrl+S 保存，Alt+Shift+F 格式化
- **自动保存**：内容自动保存到 IndexedDB

#### 📁 文件管理

- **新建文件**：点击新建按钮，输入文件名即可创建
- **重命名**：双击文件名进行重命名
- **删除文件**：支持单个删除和批量删除
- **文件同步**：本地 IndexedDB 与后端文件同步

#### 💾 存储机制

- **本地存储**：使用 IndexedDB 存储，支持离线编辑
- **后端存储**：文件保存到 `backend/data/` 目录
- **同步状态**：蓝色圆点表示未同步到后端的文件
- **一键同步**：支持本地与后端内容同步

#### 🔧 批量操作

- **批量删除**：选择多个文件进行删除
- **导出 ZIP**：一键导出所有文件为 ZIP 包
- **复制内容**：快速复制 Markdown 内容到剪贴板

#### ⚡ 高级功能

- **滚动同步**：编辑器与预览区滚动同步
- **图片懒加载**：大量图片时的性能优化
- **内容插入**：支持平台特定内容插入（知乎、公众号等）
- **格式化工具**：基于 remark 的代码格式化

## 🛠️ 开发工具

### 可用脚本

```bash
# 安装依赖
npm run install              # 安装所有依赖
npm run install:backend      # 仅安装后端依赖
npm run install:frontend     # 仅安装前端依赖

# 开发
npm run dev                  # 启动开发服务器
npm run dev:backend          # 仅启动后端
npm run dev:frontend         # 仅启动前端

# 构建
npm run build                # 构建所有项目
npm run build:backend        # 仅构建后端
npm run build:frontend       # 仅构建前端

# 生产环境
npm run start                # 启动生产服务器
npm run start:backend        # 仅启动后端生产服务器

# 工具
npm run validate-config      # 验证配置文件
npm run clean                # 清理构建文件和依赖
```

### 技术栈

**前端：**

- React 18 + Vite
- Ant Design 5.x
- React Markdown + rehype-katex
- remark 生态插件

**后端：**

- Next.js 15
- TypeScript
- 文件系统 API

**存储：**

- IndexedDB（本地）
- 文件系统（后端）

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 `LICENSE` 文件。

## 📞 问题反馈

如有问题或建议，欢迎提交 Issue 或 Pull Request。
