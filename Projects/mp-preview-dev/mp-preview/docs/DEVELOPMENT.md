# 开发指南

本文档面向开发者，介绍 MP Preview 插件的架构和开发流程。

## 项目结构

```
mp-preview/
├── src/                    # 源代码
│   ├── main.ts            # 插件入口
│   ├── view.ts            # 预览视图
│   ├── converter.ts       # 内容转换器
│   ├── templateManager.ts # 模板管理
│   ├── settings/          # 设置相关
│   │   ├── settings.ts
│   │   └── settingsTab.ts
│   └── styles/            # 样式文件
│       └── index.css
├── docs/                  # 文档
├── manifest.json          # 插件清单
├── package.json           # 依赖配置
├── tsconfig.json          # TypeScript 配置
└── esbuild.config.mjs     # 构建配置
```

## 核心组件

### 1. MPPlugin (main.ts)

插件主类，负责：
- 插件生命周期管理（加载/卸载）
- 注册视图和命令
- 初始化设置

### 2. MPView (view.ts)

预览视图，负责：
- 渲染预览界面
- 处理用户交互
- 调用复制功能

### 3. TemplateManager (templateManager.ts)

模板管理器，负责：
- 加载和管理模板
- 应用样式到元素
- 处理字体设置

### 4. MPConverter (converter.ts)

内容转换器，负责：
- 处理特殊元素（代码块、列表等）
- 转换 Obsidian 特有语法

## 开发流程

### 环境准备

1. 克隆仓库
```bash
git clone https://github.com/li-xiu-qi/mp-preview.git
cd mp-preview
```

2. 安装依赖
```bash
npm install
```

3. 创建软链接（推荐）
```powershell
# Windows PowerShell (管理员)
New-Item -ItemType Junction `
  -Path "C:\path\to\vault\.obsidian\plugins\mp-preview" `
  -Target "C:\path\to\project"
```

### 开发模式

```bash
npm run dev
```

- 监听文件变化自动重新构建
- 在 Obsidian 中按 Ctrl+R 重新加载插件

### 构建发布

```bash
npm run build
```

- 生产模式构建
- 生成压缩后的 main.js

## 代码规范

### TypeScript

- 使用严格类型检查
- 避免使用 `any` 类型
- 为函数参数和返回值添加类型注解

### 命名规范

- 类名：PascalCase（如 `TemplateManager`）
- 方法名：camelCase（如 `applyTemplate`）
- 常量：UPPER_SNAKE_CASE
- 私有成员：以 `_` 开头（可选）

### 注释规范

```typescript
/**
 * 应用模板样式到元素
 * @param element - 目标 HTML 元素
 * @param template - 可选的自定义模板
 */
public applyTemplate(element: HTMLElement, template?: Template): void {
    // 实现...
}
```

## 添加新功能

### 添加新模板

1. 在 `src/settings/settings.ts` 中定义模板
2. 添加模板样式到 `styles` 对象
3. 在设置面板中添加选项

### 添加新设置

1. 在 `Settings` 接口中添加字段
2. 在 `DEFAULT_SETTINGS` 中设置默认值
3. 在 `SettingsTab` 中添加 UI 控件
4. 在需要使用的地方读取设置

### 修改复制逻辑

复制逻辑主要在 `CopyManager` 类中：

1. `processImages()` - 处理图片转换
2. `cleanupHtml()` - 清理 HTML
3. `copyToClipboard()` - 执行复制

## 调试技巧

### 使用控制台

```typescript
console.log('[MP Debug]', variable);
console.error('[MP Error]', error);
```

### 断点调试

1. 在 Obsidian 中按 Ctrl+Shift+I 打开开发者工具
2. 在 Sources 标签页找到插件代码
3. 设置断点

### 热重载

使用 `obsidian-dev` 或其他热重载工具可以在代码变化时自动重新加载插件。

## 发布流程

1. 更新版本号
   - 修改 `manifest.json` 中的 `version`
   - 修改 `package.json` 中的 `version`
   - 更新 `versions.json`

2. 更新 CHANGELOG.md

3. 提交代码
```bash
git add .
git commit -m "release: v1.x.x"
git push
```

4. 创建 GitHub Release
   - 打标签：`git tag v1.x.x`
   - 推送标签：`git push origin v1.x.x`
   - 在 GitHub 上创建 Release
   - 上传 main.js, manifest.json, styles.css

## 常见问题

### Q: 修改后没有生效？
A: 
1. 确保 `npm run dev` 正在运行
2. 在 Obsidian 中按 Ctrl+R 重新加载
3. 检查控制台是否有编译错误

### Q: 如何调试样式问题？
A:
1. 打开开发者工具
2. 使用 Elements 标签页检查元素
3. 实时修改 CSS 查看效果

### Q: 如何添加新的 Obsidian API 调用？
A:
1. 查看 Obsidian API 文档
2. 确保类型定义在 `obsidian` 包中
3. 如果不存在，可以声明全局类型

## 参考资源

- [Obsidian API 文档](https://docs.obsidian.md/Reference/TypeScript+API)
- [Obsidian 示例插件](https://github.com/obsidianmd/obsidian-sample-plugin)
- [社区插件开发指南](https://docs.obsidian.md/Plugins/Getting+started/Build+a+plugin)
