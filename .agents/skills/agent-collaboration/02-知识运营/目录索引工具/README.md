# Directory Indexer Skill

目录结构索引生成器。扫描任意目录，生成标准格式的目录结构 Markdown 文件，支持统计 Markdown 笔记数量、总文件数和子目录数。

---

## 用途

- 为 Obsidian 知识库生成目录索引
- 为课程/资源库建立结构文档
- 为 AI 阅读提供目录导航
- 文档化项目结构

---

## 使用方法

### 基本用法

```bash
# 扫描当前目录（生成 <目录名>_目录结构.md）
uv run python .agents/tools/directory-indexer/generate_index.py

# 扫描指定目录
uv run python .agents/skills/directory-indexer/scripts/generate_index.py ./resources/一堂课程

# 指定输出文件
uv run python .agents/skills/directory-indexer/scripts/generate_index.py ./resources/一堂课程 -o ./output.md
```

### 在 Python 中使用

```python
from pathlib import Path
from .agents.tools.directory_indexer.generate_index import DirectoryIndexGenerator

generator = DirectoryIndexGenerator(
    target_dir=Path("./resources/一堂课程"),
    output_file=Path("./一堂课程_目录结构.md")
)
generator.save()
```

---

## 配置选项

### 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `target_dir` | 要扫描的目录路径 | `./resources/一堂课程` |
| `-o, --output` | 输出文件路径 | `-o ./output.md` |

### 默认排除规则

自动跳过以下文件/目录：
- 隐藏文件（以 `.` 开头）
- `scripts`, `assets`, `.obsidian`, `.git`
- `node_modules`, `__pycache__`, `.venv`
- `.agent`, `.agents`, `.kimi`, `.gemini`
- `README.md`（避免自引用）

---

## 输出格式

生成文件包含：

1. **目录树**：标准的树状结构（`├──` / `└──`）
2. **统计表格**：一级子目录的笔记数/总文件数/子目录数
3. **时间戳**：自动生成时间
4. **维护说明**：更新命令提示

示例：
```markdown
# 一堂课程 目录结构

本文件由脚本自动生成，最后更新时间：2026-02-04 12:55:00

```
一堂课程/
├── 个人篇
│   ├── 不断提认知
│   │   └── 知识管理.md
│   └── ...
```

## 目录统计

### 一级子目录概览

| 目录 | 笔记(.md) | 总文件 | 子目录 |
|------|-----------|--------|--------|
| 个人篇 | 16 | 17 | 14 |
| 创业篇 | 39 | 40 | 18 |
| **总计** | **68** | **70** | **44** |
```

---

## 集成到工作流

### 1. 课程资源入库

当新增课程时，运行脚本更新目录索引：

```bash
# 添加新课程后
uv run python .agents/skills/directory-indexer/scripts/generate_index.py ./resources/一堂课程
```

### 2. AI 助手指令

在需要目录索引的场景，AI 助手会自动调用此 skill：

> 用户：给这个目录生成一个索引文档
> 
> AI：运行 directory-indexer skill 生成目录结构...

### 3. 定期维护

作为季度审查的一部分，更新所有索引：

```bash
# 更新一堂课程索引
uv run python .agents/skills/directory-indexer/scripts/generate_index.py ./resources/一堂课程

# 更新其他资源索引
uv run python .agents/skills/directory-indexer/scripts/generate_index.py ./resources/其他资源
```

---

## 扩展开发

### 自定义排除规则

修改脚本中的 `DEFAULT_SKIP_PATTERNS` 和 `DEFAULT_SKIP_FILES`：

```python
DEFAULT_SKIP_PATTERNS: Set[str] = {
    "scripts", "assets", ".git",
    # 添加自定义排除目录
    "temp", "backup",
}

DEFAULT_SKIP_FILES: Set[str] = {
    "README.md",
    # 添加自定义排除文件
    "LICENSE", "CHANGELOG.md",
}
```

### 自定义统计维度

在 `DirectoryStats` 类中添加新的统计字段：

```python
class DirectoryStats:
    def __init__(self):
        self.file_count = 0
        self.md_count = 0
        self.image_count = 0  # 新增：图片数量
        self.dir_count = 0
```

---

## 关联资源

- [[../01-知识库管理手册|知识库管理手册]]
- [[resources/一堂课程/一堂课程_目录结构|一堂课程_目录结构]]（示例输出）
