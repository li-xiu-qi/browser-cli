# 百度网盘自动化管理专家

**来源**: 融合文件整理 Skill + 2026-02 实战经验 + 自动化脚本库
**适用场景**: 百度网盘目录重构、PARA整理、API自动化操作、批量文件管理
**版本**: v3.0

---

## 技能概述

本 Skill 提供完整的百度网盘管理解决方案，结合：

1. **PARA 文件整理方法论** - 系统化的分类决策框架
2. **自动化脚本工具集** - 20+ 个即用型 Python 脚本（含字幕获取与转换）
3. **API 接口能力** - 完整的百度网盘 API 封装
4. **MCP 集成支持** - 通过 AI 对话直接操作网盘

---

## 核心方法论: PARA + 渐进式整理

### PARA 分类体系

```
┌─────────────────────────────────────────────────────────┐
│                    PARA 分类体系                         │
├─────────────────────────────────────────────────────────┤
│  📁 1-Projects-项目    → 当前进行中的学习/工作项目        │
│  📁 2-Areas-领域       → 持续维护的技能领域               │
│  📁 3-Resources-资源   → 参考材料、工具、数据集          │
│  📁 4-Archives-归档    → 已完成/过期的历史资料          │
│  📁 00-转存区域        → 外部课程、待整理的内容          │
└─────────────────────────────────────────────────────────┘
```

### 分类决策流程

对于每个文件夹，按以下流程判断：

```
                    开始
                     │
                     ▼
            这是课程视频/资料吗？
              /            \
           是              否
           │                │
           ▼                ▼
    移到00-转存区域    这是当前在用的吗？
                          /        \
                       是          否
                       │            │
                       ▼            ▼
                这是技能学习吗？   这是历史资料吗？
                  /        \       /        \
               是          否   是          否
               │           │   │            │
               ▼           ▼   ▼            ▼
        移到Areas      移到Projects  移到Archives   移到Resources
```

---

## 快速开始

### 1. 环境配置

```bash
# 进入 skill 目录
cd .agents/skills/baidu-pan-automation

# 创建虚拟环境
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
uv pip install -r requirements.txt
```

### 2. 配置认证

本 Skill 已包含配置好的 `.env` 文件，位于 `baidu-pan-automation/.env`，包含：

- **APP 凭证** - 百度网盘开放平台应用信息
- **Access Token** - API 访问令牌（有效期30天）
- **MCP Server URL** - AI 对话直连网盘地址
- **本地路径配置** - 同步目录、转写输出目录等

> **注意**: `.env` 文件包含敏感信息，已添加到 `.gitignore`，请勿提交到版本控制。

如需重新获取 Token：

```bash
python scripts/auth/get_access_token.py
```

获取后更新 `.env` 文件中的 `BAIDU_PAN_ACCESS_TOKEN` 字段。

### 3. 基础使用

**查看树状目录：**
```bash
python scripts/analyze/analyze_structure.py
```

**按 PARA 方法整理：**
```bash
python scripts/organize/organize_my_resources.py
```

---

## 脚本工具集

### 认证与配置

| 脚本 | 功能 | 使用场景 |
|------|------|----------|
| `auth/get_access_token.py` | 完整授权流程 | 首次获取 Token |
| `auth/verify_token.py` | 验证 Token 有效性 | 定期检查 |

### 分析与查看

| 脚本 | 功能 | 使用场景 |
|------|------|----------|
| `analyze/analyze_structure.py` | 树状结构展示 | 了解整体结构 |
| `analyze/analyze_my_resources.py` | 详细分析目录 | 深度分析 |
| `analyze/analyze_filtered.py` | 按条件筛选分析 | 特定类型文件分析 |
| `analyze/view_folder_contents.py` | 查看指定目录详情 | 查看特定文件夹 |

### 整理与重组

| 脚本 | 功能 | 使用场景 |
|------|------|----------|
| `organize/organize_my_resources.py` | 按 PARA 整理 | 主要整理脚本 |
| `organize/para_organize.py` | PARA 方法整理 | 纯 PARA 整理 |
| `organize/organize_ebooks.py` | 整理电子书 | 书籍分类管理 |
| `organize/remove_duplicates.py` | 删除重复文件 | 清理重复 |
| `organize/refine_naming.py` | 优化文件命名 | 批量重命名 |

### 课程字幕处理（增强版）

| 脚本 | 功能 | 使用场景 |
|------|------|----------|
| `course/process_course.py` | **一键处理课程**（字幕+文稿） | 完整处理整个课程 |
| `course/get_subtitles.py` | 下载视频字幕(SRT) | 支持递归子目录 |
| `course/convert_srt_to_md.py` | SRT转Markdown文稿 | 支持章节前缀解析 |

#### 1. 一键处理课程（推荐）

```bash
# 处理默认课程（使用默认配置）
python scripts/course/process_course.py

# 指定课程路径和名称
python scripts/course/process_course.py \
    --course-path "/我的资源/00-转存区域/03-软技能/黄执中-沟通表达课/02.【黄执中：说服高手实战营】9章+答疑" \
    --course-name "黄执中：说服高手实战营" \
    --output-dir "output"
```

输出结构：
```
output/
├── subtitles/          # SRT字幕文件
│   ├── 【开营仪式】_开营仪式.srt
│   ├── 【战略篇】第1章_1.1定位...srt
│   └── ...
└── transcripts/        # Markdown文稿
    ├── 【开营仪式】_开营仪式.md
    ├── 【战略篇】第1章_1.1定位...md
    └── ...
```

#### 2. 仅获取字幕（递归子目录）

```bash
# 使用默认配置
python scripts/course/get_subtitles.py

# 指定课程路径和输出目录
python scripts/course/get_subtitles.py \
    --course-path "/我的资源/课程目录" \
    --output-dir "subtitles"

# 指定Access Token
python scripts/course/get_subtitles.py --token "your_access_token"
```

**特性：**
- ✅ 自动递归子目录（如：【第1章】/【第2章】）
- ✅ 智能文件名前缀（避免章节内视频重名）
- ✅ 断点续传（已下载的字幕自动跳过）
- ✅ 120秒超时重试（3次重试）

#### 3. 仅转换SRT为Markdown

```bash
# 批量转换（使用默认目录）
python scripts/course/convert_srt_to_md.py

# 指定输入输出目录和课程名
python scripts/course/convert_srt_to_md.py \
    --input-dir "subtitles" \
    --output-dir "transcripts" \
    --course-name "黄执中：说服高手实战营"
```

**特性：**
- ✅ 智能解析章节前缀（如：`【战略篇】第1章_1.1定位...`）
- ✅ Markdown标题格式：`章节 - 视频标题`
- ✅ 智能分段（300字左右自动分段）
- ✅ 过滤AI字幕元信息

---

## 整理工作流

### 阶段 1: 根目录 PARA 化

将根目录整理为 PARA 结构：

```
/我的资源/
├── 📁 1-Projects-项目          # 当前进行的学习项目
│   ├── 📁 项目-AI课程学习
│   ├── 📁 项目-大模型实战
│   └── 📁 项目-笔记方法论
│
├── 📁 2-Areas-领域             # 持续维护的领域
│   ├── 📁 领域-技术阅读
│   ├── 📁 领域-专业课程资料    # 现控/过控/PLC等
│   ├── 📁 领域-阅读管理
│   └── 📁 领域-媒体素材
│
├── 📁 3-Resources-资源         # 参考资源
│   ├── 📁 资源-AI-Docker
│   ├── 📁 资源-安装包          # 已分类的软件
│   └── 📁 资源-机器学习训练数据集
│
├── 📁 4-Archives-归档          # 历史资料
│   ├── 📁 归档-学校资料
│   ├── 📁 归档-职业认证
│   └── 📁 归档-实习资料
│
└── 📁 00-转存区域              # 外部课程
    ├── 📁 01-AI课程
    ├── 📁 02-技术工程
    └── 📁 一堂最佳实践
```

### 阶段 2: 转存区域细分

将课程类内容按主题细分：

```
00-转存区域/
├── 📁 01-AI课程              (AI基础/大模型/编程/应用/绘画)
├── 📁 02-技术工程            (嵌入式/仿真/设计/控制)
├── 📁 03-软技能              (演讲/声乐)
├── 📁 04-商业管理            (MBA/个人品牌/求职)
├── 📁 99-其他                (电影/儿歌等)
└── 📁 一堂最佳实践          (保持独立系列)
```

### 阶段 3: 安装包分类

```
资源-安装包/
├── 📁 01-开发工具            # IDE、数据库、开发环境
├── 📁 02-AI工具              # Ollama、Chatbox、LM Studio
├── 📁 03-效率软件            # Obsidian、WPS、浏览器
└── 📁 04-通讯协作            # 微信、钉钉、飞书
```

---

## 分类判断标准

### 保留在 Areas（领域）的条件

✅ **同时满足**：
1. 是当前正在学习/使用的技能
2. 需要持续维护更新
3. 未来还会参考

**示例**：
- 现控、过控、PLC（专业课）
- 技术书籍、阅读清单
- Obsidian知识库模板

### 移到 Archives（归档）的条件

✅ **满足任一**：
1. 已经学习/使用完毕
2. 过期不再更新
3. 历史记录性质

**示例**：
- 学校课件、作业、考试
- 已考过的职业认证资料
- 实习资料
- 入党/贫困生材料

### 移到 Resources（资源）的条件

✅ **满足任一**：
1. 工具软件安装包
2. 配置文件
3. 数据集
4. 参考资料（不常更新）

**示例**：
- SpaceSniffer、drawio
- Docker配置
- 机器学习数据集

### 移到 00-转存区域（课程）的条件

✅ **满足任一**：
1. 外部转存的视频课程
2. 待进一步整理的资料
3. 系列课程合集

**示例**：
- 破局俱乐部大航海
- 一堂课程
- 极客时间文档

---

## 命名规范

### 一级分类命名

```
1-Projects-项目          # PARA类别-中文描述
2-Areas-领域
3-Resources-资源
4-Archives-归档
00-转存区域              # 课程合集
```

### 二级分类命名

```
领域-技术阅读             # 领域-具体领域
领域-专业课程资料
领域-阅读管理
资源-安装包
资源-AI-Docker
归档-学校资料
归档-职业认证
```

### 三级分类命名

```
01-现控                   # 数字-核心课程名
02-过程控制
03-PLC
AI与机器学习              # 分类名
数据与算法
编程与开发
```

---

## API 操作速查

### 删除文件
```python
POST /rest/2.0/xpan/file?method=filemanager&access_token={token}&opera=delete
filelist=["/path/to/file"]
```

### 移动文件
```python
POST /rest/2.0/xpan/file?method=filemanager&access_token={token}&opera=move
filelist=[{"path": "/src", "dest": "/dest", "newname": "name"}]
```

### 重命名
```python
POST /rest/2.0/xpan/file?method=filemanager&access_token={token}&opera=rename
filelist=[{"path": "/old", "newname": "new"}]
```

### 创建文件夹
```python
POST /rest/2.0/xpan/file?method=create&access_token={token}
data={"path": "/new/folder", "isdir": 1, "rtype": 1}
```

### 列出目录
```python
GET /rest/2.0/xpan/file?method=list&access_token={token}&dir=/path
```

---

## 常见问题处理

### Q: 文件夹里有重复内容怎么办？

**A**: 先删除带 `(1)` `(2)` 后缀的重复文件，然后按PARA分类移动剩余内容。

### Q: 一个文件夹里既有课程又有自己的资料？

**A**: 拆分处理：
- 课程视频 → 00-转存区域
- 自己的笔记/素材 → Areas对应分类

### Q: 安装包太多太乱怎么办？

**A**:
1. 先删除重复版本（保留最新版）
2. 按用途分类：开发工具/AI工具/效率软件/通讯协作
3. 合并小工具到效率软件分类

### Q: 不确定该不该删的文件？

**A**: 保守策略：
1. 先移动到 Archives（归档）
2. 观察一段时间是否真的不需要
3. 确认不需要后再删除

---

## 文档导航

本 Skill 包含以下文档：

- `docs/API_CHEATSHEET.md` - API 速查表
- `docs/FAQ.md` - 常见问题解答
- `docs/SIMPLE_MERGE_GUIDE.md` - 极简合并指南
- `docs/SCRIPTS_USAGE_GUIDE.md` - 脚本详细使用说明

---

## MCP 集成

配置 MCP Server 后，可以通过 AI 对话直接操作网盘：

```bash
kimi --mcp-config-file .agents/mcp.json
```

示例对话：
- "帮我列出百度网盘根目录的文件"
- "搜索我网盘里的音频文件"
- "分析我的网盘结构并给出整理建议"

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v3.1 | 2026-02-17 | 字幕处理增强版：递归子目录支持、一键处理脚本、智能章节前缀解析 |
| v3.0 | 2026-02-16 | 整合项目代码，合并 skill，重命名为 baidu-pan-automation |
| v2.0 | 2026-02-15 | 加入 PARA 方法论、实战整理流程、分类判断标准 |
| v1.0 | 2026-02-15 | 初始版本，基于 A-Resources 合并经验 |

---

**维护者**: 筱可
**标签**: #automation #baidu-pan #file-management #PARA #api
