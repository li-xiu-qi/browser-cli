---
title: "LoRA 论文 - 笔记索引"
date: 2026-02-09
tags: [LoRA, PEFT, LLM, Fine-tuning]
category: 论文阅读
status: 未读
---

# LoRA: Low-Rank Adaptation of Large Language Models - 笔记索引

本文件为笔记索引，具体笔记内容分散在 `notes/` 文件夹中。

---

## 基本信息

- **作者**: Edward J. Hu, Yelong Shen, et al.
- **年份**: 2021
- **会议**: ICLR 2022
- **链接**: https://arxiv.org/abs/2106.09685

---

## 笔记列表

| 笔记 | 说明 | 最后更新 |
|------|------|---------|
| [[notes/01-核心发现-q_proj和v_proj的选择\|01-核心发现-q_proj和v_proj的选择]] | 应该微调哪些权重矩阵 | 2026-02-09 |

---

## 论文资源

- 原始论文：[[original.pdf]]
- 中文翻译：[[translated-zh.pdf]]
- 中英对照：[[translated-dual.pdf]]
- OCR 文本：[[ocr.md]]

---

## 快速参考

### 核心结论

**推荐微调的矩阵**: `q_proj` + `v_proj` (查询和值投影矩阵)

### 典型配置

```python
from peft import LoraConfig

config = LoraConfig(
    r=4,
    lora_alpha=8,
    target_modules=["q_proj", "v_proj"],  # （推荐） 推荐组合
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM",
)
```

---

**索引创建日期**: 2026-02-09
