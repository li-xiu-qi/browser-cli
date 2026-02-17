# Directory Indexer

目录结构索引生成器。扫描任意目录，生成标准格式的目录结构 Markdown 文件。

## 功能

- 扫描任意目录生成树形结构
- 统计 Markdown 笔记数量、总文件数和子目录数
- 输出为标准 Markdown 格式

## 使用方法

```powershell
# 扫描当前目录
uv run python .agents/tools/directory-indexer/generate_index.py

# 扫描指定目录
uv run python .agents/tools/directory-indexer/generate_index.py ./resources/一堂课程

# 指定输出文件
uv run python .agents/tools/directory-indexer/generate_index.py ./resources/一堂课程 -o ./output.md
```

## 详细文档

规范和使用说明：[[02-知识运营/目录索引工具/README|目录索引工具]]
