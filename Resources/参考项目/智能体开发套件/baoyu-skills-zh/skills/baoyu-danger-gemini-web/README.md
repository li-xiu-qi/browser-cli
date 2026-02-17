# baoyu-danger-gemini-web (Gemini Web 客户端)

这是一个基于逆向工程 (Reverse-Engineered) 的 Gemini Web API 客户端，它允许你直接调用 Gemini 网页版的强大能力，包括文本生成、图像生成、多模态视觉识别以及多轮对话。

> ⚠️ **风险提示**：本工具使用了非官方的 API 接口，可能面临账号封禁风险或接口失效问题。初次使用时需要通过交互式流程确认免责声明。

## 🌟 核心能力

- **全功能访问**：支持 Gemini 网页版的所有核心功能（包括付费模型 gemini-advance/ultra）。
- **原生图像生成**：直接调用 Gemini 的文生图能力。
- **视觉理解**：支持上传参考图 (`--reference`) 进行多模态对话。
- **多轮对话管理**：通过 `--sessionId` 保持上下文记忆，实现连续对话。
- **自动化登录**：自动复用本地 Chrome 浏览器的 Cookie，无需复杂的抓包配置。

## 🛠️ 使用方法

### 首次设置 (Consent & Login)
初次运行时，工具会要求你接受免责声明，并会自动打开浏览器完成 Google 登录以获取 Cookie。

### 常用指令

```bash
# 文本生成
npx -y bun ${SKILL_DIR}/scripts/main.ts "Explain quantum physics"

# 指定模型 (gemini-2.5-pro/flash)
npx -y bun ${SKILL_DIR}/scripts/main.ts "Hello" -m gemini-2.5-pro

# 图像生成 (Text-to-Image)
npx -y bun ${SKILL_DIR}/scripts/main.ts -p "A cyberpunk city" --image city.png

# 视觉参考 (Image-to-Image / Vision)
npx -y bun ${SKILL_DIR}/scripts/main.ts -p "Describe this" --ref image.jpg

# 多轮对话
npx -y bun ${SKILL_DIR}/scripts/main.ts "My name is Ke" --sessionId session-001
npx -y bun ${SKILL_DIR}/scripts/main.ts "What is my name?" --sessionId session-001
```

## ⚙️ 配置与鉴权

- **鉴权方式**：工具优先尝试从环境变量读取配置，如果失败则会自动启动本地 Chrome 浏览器进行登录并提取 Cookie。
    - 强制刷新 Cookie：使用 `--login` 参数。
- **配置文件 (EXTEND.md)**：支持配置默认模型、代理服务器 (Proxy) 等。

## 📂 脚本结构

```text
baoyu-danger-gemini-web/
├── SKILL.md
└── scripts/
    ├── main.ts           # CLI 入口
    └── gemini-webapi/    # 逆向 API 核心实现 (Ported from Python)
```

---
*此工具适合作为其他高阶智能体（如需要复杂推理或免费图像生成后端）的底层驱动。*
