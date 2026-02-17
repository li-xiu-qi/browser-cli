# 书籍资源库

**定位**: 从 PDF/EPUB 转换的 Markdown 书籍  
**来源**: OCR 识别、EPUB 转换

## 目录结构

```
resources/books/
├── 00_待分类/          # 新转换的书籍，待整理
├── 01_哲学/            # 哲学类
├── 02_经济学/          # 经济学类
├── 03_认知科学/        # 认知科学类
├── 04_技术/            # 技术类
├── assets/             # 书籍图片资源
│   └── <书名>/
└── README.md
```

## 命名规范

- Markdown: `<书名>.md`
- 图片: `assets/<书名>/图片名.png`

## 转换工具

参见: `.agents/skills/content-converter/SKILL.md`

## 处理流程

1. PDF/EPUB → Markdown (OCR 或 pandoc)
2. 放入 `00_待分类/`
3. 手动整理到对应分类目录
4. 更新个人书架索引
