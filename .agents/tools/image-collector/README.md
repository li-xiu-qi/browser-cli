# 图片收集器

从网页/文章提取图片到暂存区，支持精选后入库。

## 目录结构

```
0_Inbox/
└── image-staging/              # 暂存区
    └── 2026-02-16/             # 按日期组织
        ├── img_001.jpg
        └── img_002.png

resources/
└── image-library/              # 正式图片库
    ├── claude-workflow.jpg
    └── claude-workflow.jpg.json
```

## 使用流程

### 1. 提取图片（到暂存区）

```bash
# 从 Markdown 文件
python collector.py article.md

# 从网页
python collector.py https://example.com/article

# 自动交互选择
python collector.py article.md
# → 显示图片列表 → 输入序号（如: 1,3,5）或 all
```

### 2. 查看暂存区

```bash
python collector.py --staging
```

### 3. 入库（移到正式库）

```bash
# 单张入库
python collector.py --import "0_Inbox/image-staging/2026-02-16/img_001.jpg" --name "claude-interface"

# 结果: resources/image-library/claude-interface.jpg
```

### 4. 清理暂存区

```bash
# 删除7天前的暂存文件
python collector.py --clean 7
```

## 为什么有暂存区？

1. **预筛选**: 不是所有提取的图片都值得保存
2. **重命名**: 暂存区是简单编号，入库时重命名为有意义的名称
3. **避免污染**: 正式库只保留精选图片
4. **批量处理**: 先批量下载，再慢慢挑选

## 完整示例

```bash
# 1. 抓取文章并提取图片
python collector.py "Projects/写作/文章.md"
# → 保存到 0_Inbox/image-staging/2026-02-16/

# 2. 查看暂存区
python collector.py --staging
# → 显示: img_001.jpg, img_002.jpg

# 3. 选择好的图片入库
python collector.py --import "0_Inbox/image-staging/2026-02-16/img_001.jpg" --name "workflow-demo"

# 4. 生成描述
python analyzer.py resources/image-library/workflow-demo.jpg
# → 生成 workflow-demo.jpg.json

# 5. 清理暂存区
python collector.py --clean 7
```
