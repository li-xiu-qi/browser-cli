# 贡献指南

感谢您对 MP Preview 项目的关注！本文档将帮助您了解如何为项目做出贡献。

## 行为准则

- 尊重所有参与者
- 接受建设性的批评
- 关注对社区最有利的事情

## 如何贡献

### 报告 Bug

如果您发现了 bug，请通过 [GitHub Issues](https://github.com/li-xiu-qi/mp-preview/issues) 报告，并包含以下信息：

1. 使用的 Obsidian 版本
2. 插件版本
3. 操作系统
4. 重现步骤
5. 期望行为与实际行为
6. 截图（如果适用）

### 提出新功能

欢迎提出新功能建议！请通过 GitHub Issues 提交，并描述：

1. 功能的使用场景
2. 期望的行为
3. 可能的实现方案（可选）

### 提交代码

1. Fork 本仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

#### 代码规范

- 使用 TypeScript 编写代码
- 遵循现有代码风格
- 添加必要的注释
- 确保代码通过 TypeScript 编译

#### 提交信息规范

提交信息应清晰描述更改内容，建议格式：

```
<type>: <subject>

<body>
```

类型包括：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式（不影响代码运行的变动）
- `refactor`: 重构
- `perf`: 性能优化
- `test`: 测试相关
- `chore`: 构建过程或辅助工具的变动

## 开发环境设置

1. 克隆仓库
```bash
git clone https://github.com/li-xiu-qi/mp-preview.git
cd mp-preview
```

2. 安装依赖
```bash
npm install
```

3. 启动开发模式
```bash
npm run dev
```

4. 在 Obsidian 中创建软链接（用于测试）
```powershell
# Windows PowerShell (以管理员身份运行)
New-Item -ItemType Junction -Path "{vault}/.obsidian/plugins/mp-preview" -Target "{project-path}"
```

## 测试

- 在提交前确保代码可以正常编译
- 在本地 Obsidian 中测试功能
- 检查是否有控制台错误

## 许可证

通过贡献代码，您同意您的贡献将在 MIT 许可证下发布。
