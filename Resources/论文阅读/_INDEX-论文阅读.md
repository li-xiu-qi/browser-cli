# 论文阅读索引

本索引汇总所有收录的学术论文，采用文件夹式管理（每篇论文一个文件夹）。

---

## 索引填写规范

### 新增论文模板

复制以下模板添加到对应分类表格：

```markdown
| [论文标题] | [作者] | [年份] | [会议] | [标签] | [翻译] | [OCR] | [阅读] | [[papers/[文件夹]/\|[打开]]] |
```

### 字段说明

| 字段 | 可选值 | 说明 |
|------|--------|------|
| **翻译** | 是/否 | 是否有中文翻译版 |
| **OCR** | 是/否 | 是否有 OCR 提取的 Markdown |
| **阅读** | 未读/进行中/已读 | 阅读进度 |

---

## 论文清单

### 注意力机制 (Attention)

| 论文 | 作者 | 年份 | 会议 | 标签 | 翻译 | OCR | 阅读 | 文件夹 |
|------|------|------|------|------|:----:|:---:|:----:|--------|
| Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention | Katharopoulos, et al. | 2020 | ICML 2020 | #LLM #Architecture | 否 | 是 | 已读 | [[papers/LinearAttention_Transformers_are_RNNs_Fast_Autoregressive_Transformers_with_Linear_Attention/\|[打开]]] |

### 参数高效微调 (PEFT)

| 论文 | 作者 | 年份 | 会议 | 标签 | 翻译 | OCR | 阅读 | 文件夹 |
|------|------|------|------|------|:----:|:---:|:----:|--------|
| LoRA: Low-Rank Adaptation of Large Language Models | Edward J. Hu, et al. | 2021 | ICLR 2022 | #PEFT #LLM | 是 | 是 | 未读 | [[papers/LoRA_Low-Rank_Adaptation_of_Large_Language_Models/\|[打开]]] |

---

## 按主题分类

###  注意力机制 (Attention)
- [[papers/LinearAttention_Transformers_are_RNNs_Fast_Autoregressive_Transformers_with_Linear_Attention/|Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention]]

###  参数高效微调 (PEFT)
- [[papers/LoRA_Low-Rank_Adaptation_of_Large_Language_Models/|LoRA: Low-Rank Adaptation of Large Language Models]]

---

## 按阅读状态分类

###  未读
- (暂无)
- [[papers/LoRA_Low-Rank_Adaptation_of_Large_Language_Models/|LoRA: Low-Rank Adaptation of Large Language Models]]

###  进行中
- (暂无)

###  已读
- [[papers/LinearAttention_Transformers_are_RNNs_Fast_Autoregressive_Transformers_with_Linear_Attention/|Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention]]

---

## 统计

| 指标 | 数量 |
|------|------|
| 论文总数 | 2 |
| 已翻译 | 1 |
| OCR完成 | 2 |
| 已读 | 1 |
| 进行中 | 0 |
| 未读 | 1 |

---

## 文件夹结构示例

```
papers/
└── LoRA_Low-Rank_Adaptation_of_Large_Language_Models/
    ├── meta.json              # 元数据
    ├── original.pdf           # 原始论文
    ├── translated-zh.pdf      # 中文翻译
    ├── translated-dual.pdf    # 中英对照
    ├── ocr.md                 # OCR 文本
    ├── images/                # 提取的图片
    └── notes.md               # 阅读笔记
```

点击 [打开] 链接可快速进入论文文件夹。

---

**最后更新**: 2026-02-16
