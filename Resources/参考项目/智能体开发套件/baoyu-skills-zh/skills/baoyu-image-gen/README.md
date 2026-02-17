# baoyu-image-gen (官方 API 图像生成)

这是一个基于官方 API (OpenAI DALL-E & Google Imagen) 的图像生成工具。与 `danger-gemini-web` 不同，它使用稳定、合规的官方接口，适合生产环境使用。

## 🌟 核心特性

- **多供应商支持**：
    - **Google (默认)**：支持 Imagen 和 Gemini 多模态模型，支持**参考图 (Reference Image)** 输入。
    - **OpenAI**：支持 DALL-E 3，生成质量高，逻辑理解力强。
- **并行生成 (Parallel Gen)**：专为批量任务设计，推荐使用 4 个并发子 Agent 进行加速（如生成 PPT 插图、漫画分页）。
- **多模态控制**：支持 `--ref` 参数上传参考图（仅 Google 模型），实现以图生图或风格迁移。
- **画幅控制**：支持主流比例（16:9, 1:1, 4:3 等），并自动适配不同模型的参数要求。

## 🛠️ 使用方法

```bash
# 基础生成 (默认 Google)
npx -y bun ${SKILL_DIR}/scripts/main.ts -p "A futuristic city" --image city.png

# 强制使用 OpenAI DALL-E 3
npx -y bun ${SKILL_DIR}/scripts/main.ts -p "A cute cat" --provider openai --image cat.png

# 带参考图生成 (仅 Google)
npx -y bun ${SKILL_DIR}/scripts/main.ts -p "Make it cyberpunk style" --ref original.jpg --image out.png

# 指定画幅与质量
npx -y bun ${SKILL_DIR}/scripts/main.ts -p "Landscape" --ar 16:9 --quality 2k --image wallpaper.png
```

## ⚙️ 配置 (Env Vars & EXTEND.md)

**API Keys (必需):**
- `GOOGLE_API_KEY`: 用于 Google 模型。
- `OPENAI_API_KEY`: 用于 OpenAI 模型。

**EXTEND.md 配置:**
- 支持设置默认 Provider、默认质量预设 (`normal`/`2k`) 和默认画幅。

## 🚀 性能优化

- **并发建议**：当需要生成 4 张以上图片时（如漫画、幻灯片），强烈建议在调用方（如 Agent）开启 `run_in_background=true`，以并行方式同时生成，显著缩短总耗时。
- **质量预设**：
    - `normal`: 1K 分辨率，适合快速预览。
    - `2k`: 2K/2048px 分辨率，适合最终成品。

---
*这是 baoyu-skills 套件中最稳健的图像生成后端，推荐作为默认首选。*
