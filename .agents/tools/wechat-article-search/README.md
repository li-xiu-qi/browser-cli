# 微信公众号文章搜索工具

**定位**: 写作对标分析工具  
**用途**: 找对标文章、分析竞品、参考选题和配图

这是你仓库里的一个 **repo-local tool**，不是全局 skill。

- 类型: `.agents/tools` 下的本地执行工具
- 作用: 借助公众号后台登录态，做账号搜索、文章列表分页和单篇文章图片提取
- 边界: 它依赖公众号后台私有接口，不是微信公开 API

现在建议按职责拆成四层：

- `wechat_biz_search.py`：专门搜公众号账号，拿 `fakeid`
- `wechat_biz_list.py`：专门按 `fakeid` 分页列文章
- `wechat_biz_export.py`：专门做分批导出、断点续跑、状态记录
- `wechat_search.py`：兼容旧入口，保留旧的文章搜索 / 图片提取，也可继续调用 `search-biz` / `list-biz`

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
├── wechat_biz_export.py # 分批导出主控脚本
├── wechat_search.py      # 主工具
├── cookies.json          # 登录状态（自动生成）
└── README.md

0_Inbox/image-staging/      # 暂存区
└── 2026-02-16/
    ├── wx_001.jpg
    └── ...
```

当前不再把 `.agents/browser_user_data/` 当成默认共享认证目录。  
如果需要 agent 承接已有浏览器会话里的 cookie，优先导入 `browser-cli` 或其他浏览器工具导出的 JSON。  
这个工具自己的登录状态仍以本目录下的 `cookies.json` 为主。

## 安装依赖

```bash
pip install playwright
playwright install chromium
```

## 使用流程

### 1. 首次登录

```bash
python wechat_biz_search.py login
```

- 会自动打开浏览器
- 扫码登录微信公众号平台
- 登录状态保存到 `cookies.json`

### 2. 搜索公众号账号

```bash
# 搜索公众号，拿 fakeid
python wechat_biz_search.py search "李继刚"

# 保存结果
python wechat_biz_search.py search "李继刚" -o biz.json
```

### 3. 拉取公众号文章列表

```bash
# 用 fakeid 分页拉文章
python wechat_biz_list.py list "MzkxMzc1NzM1Mw=="

# 翻到下一页
python wechat_biz_list.py list "MzkxMzc1NzM1Mw==" -b 5 -n 5

# 保存结果
python wechat_biz_list.py list "MzkxMzc1NzM1Mw==" -b 0 -n 20 -o articles.json
```

### 4. 分批导出到原文库

长批量导出更建议在 WSL 里跑 `python3`，并把会话参数通过运行时环境变量传进去，而不是保存到 repo 文件。

```bash
# 推荐：运行时环境变量，不落 repo
export WECHAT_TOKEN='...'
export WECHAT_COOKIE='...'
export WECHAT_FINGERPRINT='...'
export WECHAT_REFERER='...'

# 先看当前状态
python3 wechat_biz_export.py status "李继刚"

# 每次只跑 1 个批次，每批 3 页
python3 wechat_biz_export.py run "MzkxMzc1NzM1Mw==" "李继刚" \
  --batch-pages 3 \
  --max-batches 1

# 从指定页继续跑
python3 wechat_biz_export.py run "MzkxMzc1NzM1Mw==" "李继刚" \
  --start-page 28 \
  --batch-pages 3 \
  --max-batches 1

# 如果 requests 会话不稳定，但浏览器 Network 里某条 appmsgpublish 已验证可用，
# 可以切到 curl transport 并显式带 referer
python3 wechat_biz_export.py run "MzkxMzc1NzM1Mw==" "李继刚" \
  --transport curl \
  --referer "$WECHAT_REFERER" \
  --batch-pages 1 \
  --max-batches 1
```

脚本会在作者目录下维护：

- `_导出状态.json`
- `_文章总表.json`
- `_抓取报告.json`

其中：

- `_导出状态.json` 记录当前批次、`next_page`、已完成页、列表/正文状态
- `_文章总表.json` 记录全量文章元数据汇总
- `_抓取报告.json` 在单批抓取过程中持续更新，便于中途中断后检查进度
- 计数字段有两种口径：
  - `total_count` / `publish_record_total_count` 是微信后台 `publish_list` 的分页记录数
  - `catalog_count` / `article_count_collected` 是展开 `appmsgex` 后、按 URL 去重的文章条目数

这两个数不一定相等。像多图文一次群发里包含多篇文章时，展开后的文章条目数会大于后台分页记录数。这不代表抓重了。

如果本次只是 `--list-only`：

- `_导出状态.json` 会写 `run_mode = list-only`
- `complete=true` 仅表示“列表分页已抓完”
- `body_target_count=0`，不会把“正文还没抓”误判成任务未完成
- `_文章列表.json` 会在批次内按页持续刷新，不再等整批结束后才落盘
- 如果批次中途失败，但前面若干页已经成功，导出主控会尽量回收这部分页级进度到 `_文章总表.json` 和 `_导出状态.json`
- `curl` 链路现在会对瞬时网络错误做小次数重试，减少 `curl: (28)` 这类超时把整批打断

这些文件都不会保存 `token/cookie/fingerprint/referer`。

如果要在 Windows 下持续跑很多批次，又不想盯着前台超时，可以用附带的循环包装脚本：

```powershell
$env:WECHAT_TOKEN = "..."
$env:WECHAT_COOKIE = "..."
$env:WECHAT_FINGERPRINT = "..."

powershell.exe -NoProfile -File .\wechat_biz_export_loop.ps1 `
  -FakeId "MzkxMzc1NzM1Mw==" `
  -AuthorDir "李继刚" `
  -OutputDir "C:\path\to\作者目录\公众号" `
  -BatchPages 5

# 需要 curl transport 时
powershell.exe -NoProfile -File .\wechat_biz_export_loop.ps1 `
  -FakeId "MzkxMzc1NzM1Mw==" `
  -AuthorDir "李继刚" `
  -OutputDir "C:\path\to\作者目录\公众号" `
  -Transport curl `
  -Referer $env:WECHAT_REFERER `
  -BatchPages 1
```

如果 repo-local `cookies.json` 里还保留着有效的 `token/cookie`，又不想把整条 cookie 直接写到命令行，可以改用这个薄包装：

```powershell
powershell.exe -NoProfile -File .\wechat_biz_export_loop_from_cookies.ps1 `
  -FakeId "MzkxMzc1NzM1Mw==" `
  -AuthorDir "李继刚" `
  -OutputDir "C:\path\to\作者目录\公众号" `
  -Fingerprint $env:WECHAT_FINGERPRINT `
  -Transport curl `
  -ListOnly `
  -BatchPages 5
```

它会：

- 从本目录 `cookies.json` 读取 `token`
- 自动把 `cookies` 对象拼成可用的 `Cookie` 请求头
- 再转调现有的 `wechat_biz_export_loop.ps1`
- 适合 `bg-runner` 这类不方便传超长 cookie 字符串的后台入口

它会：

- 每次只调用 1 个批次
- 每批结束后回读 `_导出状态.json`
- 持续写 `output_dir/_后台续跑.log`
- 支持从 `next_page` 自动续跑直到 `complete=true`
- 如果分页已经跑完但正文仍未补齐，会停止空转，等待正文回填
- 如果 `requests` 不稳，可以透传 `-Transport curl` 与 `-Referer`

如果这次本来就是 `-ListOnly`，那这里的 `complete=true` 代表的是列表工作完成，不代表正文也抓了。

### 作者作品研究项目的默认执行顺序

如果目标不是临时找几篇文章，而是把某个作者长期收进
`Projects/Operations/作者与机构内容研究/` 这类原文库，默认按下面顺序执行：

1. 先在 `02_原始作品库/<作者>/公众号/` 建目录
2. 先跑 `--list-only`，每次只跑少量分页，先把 URL 和元数据拿稳
3. 续跑时优先读取 `_导出状态.json`、`_文章总表.json`、`_抓取报告.json`
4. 列表稳定后，再后台慢速补正文，不要一上来就全量抓正文
5. 如果分页已经完成但正文有缺口，优先用缺失正文回填，而不是继续空跑分页

补充约束：

- `list-only` 完成后，`complete=true` 只表示列表完成
- 如果中途中断，先看 `next_page`，不要机械相信残留的 `run_state = running`
- transport 敏感时，优先使用 `--transport curl` 并显式传 `--referer`
- 增量判重以文章 `source URL` 为准，不再只靠标题
- 不要把 `total_count` 和 `article_count_collected` 直接拿来互相比大小判断“是否有重复”；它们的统计口径不同

### 4.1 分页结束后回填缺失正文

如果 `_导出状态.json` 已经是：

- `list_complete = true`
- `body_complete = false`

说明分页列表拿全了，但正文 Markdown 还没补齐。此时不要继续跑分页导出，而是运行缺失正文回填：

```powershell
uv run --with requests python .\wechat_biz_backfill_missing.py "孔某人" `
  --output-dir "C:\path\to\作者目录\公众号" `
  --max-articles 15
```

它会：

- 对比 `_文章总表.json` 和现有 Markdown 的 `source:`
- 只处理缺失 URL
- 持续写 `_正文回填报告.json`
- 回填后自动刷新 `_导出状态.json`

如果要后台持续回填，可以用：

```powershell
powershell.exe -NoProfile -File .\wechat_biz_backfill_loop.ps1 `
  -AuthorDir "孔某人" `
  -OutputDir "C:\path\to\作者目录\公众号" `
  -MaxArticlesPerBatch 15
```

补充说明：

- `wechat_biz_backfill_loop.ps1` 现在会优先使用仓库内的 `.venv\Scripts\python.exe`
- 只有本地虚拟环境不存在时，才回退到 `uv run --with requests`
- 这样可以避开部分机器上 `uv` 访问用户缓存目录时报 `拒绝访问` 的问题

### 4.2 单作者：列表跑完后自动接正文

如果一个新作者已经在跑 `list-only`，但你已经确定“列表跑完就直接接正文”，可以再开一个等待接棒任务：

```powershell
powershell.exe -NoProfile -File .\wechat_wait_then_backfill.ps1 `
  -AuthorDir "张无常" `
  -OutputDir "C:\path\to\作者目录\公众号" `
  -MaxArticlesPerBatch 15 `
  -PollSeconds 120
```

它会：

- 定时轮询 `_导出状态.json`
- 在 `list_complete=true` 后自动启动 `wechat_biz_backfill_loop.ps1`
- 把等待与接棒过程写到 `output_dir/_正文接棒等待.log`

这个脚本只负责“等列表完成后再接正文”，不会和当前 `list-only` 抢同一个分页状态。

### 4.3 多作者：全局正文队列

如果后面会有多个作者同时在跑 `list-only`，更推荐把“正文内容抓取”交给一个全局队列，而不是给每个作者都单独开等待任务。

正文队列入口：

```powershell
.venv\Scripts\python.exe .\wechat_body_queue.py enqueue "张无常" `
  --output-dir "C:\path\to\作者目录\公众号" `
  --priority 50

.venv\Scripts\python.exe .\wechat_body_queue.py status

# 后面要调整处理顺序
.venv\Scripts\python.exe .\wechat_body_queue.py set-priority "张无常" 20
```

队列 dispatcher：

```powershell
.venv\Scripts\python.exe .\wechat_body_queue.py dispatch `
  --poll-seconds 120 `
  --max-articles-per-batch 5 `
  --pause-seconds 15 `
  --max-concurrent 2
```

推荐在后台挂起：

```powershell
.venv\Scripts\python.exe ..\bg-runner\bg.py run `
  "C:\Users\ke\Documents\projects\obsidian_projects\pkm-hub\.venv\Scripts\python.exe .agents/tools/wechat-article-search/wechat_body_queue.py dispatch --poll-seconds 120 --max-articles-per-batch 5 --pause-seconds 15 --max-concurrent 2" `
  --name wechat-body-queue-dispatcher
```

它会：

- 把多个作者登记到同一个 `data/body_queue.json`
- 自动识别谁还在等列表完成，谁已经可以开始抓正文
- 每次最多并行调度 `--max-concurrent` 个作者的一小批正文（默认 2）
- 一轮结束后再回到队列里挑下一个 ready 作者
- 用 `_导出状态.json` 和 `_正文回填报告.json` 判断真实进度

当前状态语义大致是：

- `waiting-list`：列表还没跑完，继续等
- `ready`：列表已完成，且还有正文缺口
- `running`：本轮正在由 dispatcher 调度
- `external-running`：检测到这个作者已经有别的正文任务在跑，队列先不抢
- `completed`：正文已经补齐
- `paused`：人工暂停
- `blocked`：上一轮没有推进或脚本报错，需要人工看一下

建议：

- 单作者临时接棒，用 `wechat_wait_then_backfill.ps1` 就够
- 多作者长期排队，默认用 `wechat_body_queue.py`
- 优先级数字越小越靠前，后续可用 `set-priority` 随时调整
- 不要同时给同一个作者开“单作者等待任务”和“全局正文队列”，避免重复回填

### 5. 兼容旧入口：搜索文章

```bash
# 基本搜索
python wechat_search.py search "AI编程"

# 保存结果
python wechat_search.py search "Claude Code" -o articles.json
```

### 6. 提取文章图片

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
python wechat_biz_search.py login

# 2. 搜公众号，拿 fakeid
python wechat_biz_search.py search "李继刚"

# 3. 分页列文章
python wechat_biz_list.py list "MzkxMzc1NzM1Mw==" -b 0 -n 10 -o 文章列表.json

# 4. 小批量导出到原文库
python3 wechat_biz_export.py run "MzkxMzc1NzM1Mw==" "李继刚" --batch-pages 2 --max-batches 1

# 5. 查看搜索结果，选择几篇深入分析
# 提取其中一篇的详细内容参考
python wechat_search.py extract "https://mp.weixin.qq.com/s/xxx" 

# 6. （可选）参考别人的配图风格
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
5. **接口性质**：`search-biz` 和 `list-biz` 依赖公众号后台私有接口，不是微信公开 API，后续可能变动
6. **基础限速**：导出脚本内已加随机等待，但这不等于绝对安全，批量抓取仍要控制节奏
7. **长任务建议**：单次建议只跑 `2 ~ 4` 页，跑完人工看一眼状态再继续
8. **断点续跑**：优先使用 `wechat_biz_export.py` 的状态文件续跑，不要每次从第 1 页重新翻
9. **增量判定**：当前以文章 `source URL` 为准判断是否已存在，不再只靠标题，避免同标题文章误跳过
10. **同标题保护**：如果不同文章标题相同，落盘时会自动生成带附加后缀的唯一文件名，避免正文互相覆盖
11. **项目主线**：如果这是作者长期语料收集任务，默认先 `list-only`，后正文回填

## 与其他工具配合

| 工具 | 用途 |
|------|------|
| image-tools/image-collector | 从 Markdown/网页提取图片（暂存区） |
| image-tools/image-analyzer | 生成图片描述（JSON） |
| wechat_search | 从公众号文章搜索配图 |

三者共享同一个 **暂存区** (`0_Inbox/image-staging/`) 和 **图片库** (`resources/image-library/`)。
