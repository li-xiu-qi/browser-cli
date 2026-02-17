# 微信公众号文章搜索工具

**定位**: 写作对标分析工具  
**用途**: 找对标文章、分析竞品、参考选题和配图

## 核心场景

### 场景一：找对标（写作前）

```
"要写关于'AI编程'的文章，先看看别人怎么写的"
↓
搜索公众号文章 → 分析标题/结构/数据 → 确定自己文章的差异化角度
```

### 场景二：选题参考

```
"最近什么话题火？"
↓
搜索关键词 → 看高阅读量文章 → 找选题灵感
```

### 场景三：配图参考

```
"别人的技术文章配图怎么做？"
↓
打开对标文章 → 截图参考排版和配图风格
```

## 与图片库的关系

**不是图片库收集工具！**

- 图片库：存放**无版权/可用**的精选素材
- 微信搜索：用于**参考/对标**，不直接入库

## 目录结构

```
.agents/tools/wechat-article-search/
├── wechat_search.py      # 主工具
├── cookies.json          # 登录状态（自动生成）
└── README.md

.agents/browser_user_data/  # 浏览器数据（共享）
└── Default/
    ├── Cookies
    └── ...

0_Inbox/image-staging/      # 暂存区
└── 2026-02-16/
    ├── wx_001.jpg
    └── ...
```

## 安装依赖

```bash
pip install playwright
playwright install chromium
```

## 使用流程

### 1. 首次登录

```bash
python wechat_search.py login
```

- 会自动打开浏览器
- 扫码登录微信公众号平台
- 登录状态保存到 `cookies.json`

### 2. 搜索文章

```bash
# 基本搜索
python wechat_search.py search "AI编程"

# 保存结果
python wechat_search.py search "Claude Code" -o articles.json
```

### 3. 提取文章图片

```bash
# 提取指定文章的图片
python wechat_search.py extract "https://mp.weixin.qq.com/s/xxx" --download

# 带前缀（方便识别来源）
python wechat_search.py extract "https://mp.weixin.qq.com/s/xxx" --download --prefix "ai_article"
```

## 完整 Workflow 示例

### 场景：写作前对标分析

```bash
# 1. 登录（首次）
python wechat_search.py login

# 2. 搜索同主题文章（找对标）
python wechat_search.py search "AI编程工具" -o 对标文章.json

# 3. 查看搜索结果，选择几篇深入分析
# 提取其中一篇的详细内容参考
python wechat_search.py extract "https://mp.weixin.qq.com/s/xxx" 

# 4. （可选）参考别人的配图风格
# 打开文章链接，截图参考
```

### 分析维度

拿到对标文章后，分析：

| 维度 | 问题 |
|------|------|
| 标题 | 用了什么钩子？数字/悬念/反常识？ |
| 角度 | 技术解读/个人体验/行业分析？ |
| 结构 | 总分总？故事线？问题-解决？ |
| 配图 | 风格统一吗？信息图还是截图？ |
| 数据 | 用了什么案例/数据支撑？ |

### 写作工作流集成

参考 `.agents/skills/ai-writing-collaborator/01-场景协作/04-从零创作.md` 步骤1.1

## 注意事项

1. **登录有效期**：Token 约 4-8 小时过期，过期后需重新登录
2. **使用小号**：建议用非主力微信号登录
3. **频率限制**：不要频繁搜索，避免触发风控
4. **版权问题**：提取的图片仅用于个人学习参考，注意版权

## 与其他工具配合

| 工具 | 用途 |
|------|------|
| image-collector | 从 Markdown/网页提取图片（暂存区） |
| image-analyzer | 生成图片描述（JSON） |
| wechat_search | 从公众号文章搜索配图 |

三者共享同一个 **暂存区** (`0_Inbox/image-staging/`) 和 **图片库** (`resources/image-library/`)。
