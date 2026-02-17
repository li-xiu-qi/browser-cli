# 阅读笔记：线性注意力机制 (Linear Attention)

**论文**: Transformers are RNNs: Fast Autoregressive Transformers with Linear Attention  
**作者**: Angelos Katharopoulos, Apoorv Vyas, Nikolaos Pappas, François Fleuret  
**发表**: ICML 2020  
**标签**: #注意力机制 #Transformer #模型架构 #推理优化

---

## 一句话总结

线性注意力机制通过**核函数技巧**将 Transformer 的复杂度从 $O(n^2)$ 降到 **$O(n)$**，并证明它可以被重写为 **RNN**，从而实现数千倍的推理加速。

---

## 什么是线性注意力？

### 一句话概括

**就是改了一个乘法顺序！** 

传统注意力：先算 $Q$ 和 $K$ 的相似度（得到 $n \times n$ 矩阵），再乘 $V$
$$
\text{Attention} \approx (Q \cdot K^T) \cdot V \quad \text{→ 中间结果 } n \times n \text{，复杂度 } O(n^2)
$$

线性注意力：先算 $K$ 和 $V$ 的累积（得到固定大小的矩阵），再和 $Q$ 相乘
$$
\text{Attention} = \phi(Q) \cdot (\phi(K)^T \cdot V) \quad \text{→ 中间结果 } c \times d_v \text{（固定大小，不随}n\text{增长），复杂度 } O(n)
$$

**关键**：利用矩阵乘法结合律 $(A \cdot B) \cdot C = A \cdot (B \cdot C)$，改变计算顺序，避免产生巨大的 $n \times n$ 矩阵！

---

### 核心思想

传统 Transformer 的瓶颈在于自注意力的**二次复杂度**——处理 $n$ 个 token 需要 $n^2$ 的计算量。线性注意力通过**改变乘法顺序**来解决这个问题。

### 直观对比

假设序列长度 $n = 1000$，维度 $d = 64$：

| 计算方式 | 关键矩阵运算 | 结果矩阵尺寸 | 复杂度 |
|---------|-------------|-------------|--------|
| **传统**: $\text{softmax}(QK^T) \cdot V$ | $QK^T$ (每个Q和所有K算) | $n \times n = 1000 \times 1000$ | $O(n^2)$ |
| **线性**: $\phi(Q) \cdot (\phi(K)^T V)$ | $\phi(K)^T V$ (所有K和V累积) | $d \times d_v = 64 \times 64$ | $O(n)$ |

**看出区别了吗？**
- **传统方法**: 先算 $QK^T$，得到一个 $n \times n$ 的巨大注意力矩阵（1000×1000 = 100万个数）
- **线性方法**: 先算 $\phi(K)^T V$，得到一个 $c \times d_v$ 的小矩阵（如 64×64 = 4096个数），虽然计算这个矩阵本身还是需要遍历所有 $n$ 个 token，但结果是**固定大小**，不随序列增长而增长

**关键区别**:
- **传统**：每个 Query 都要和 $n$ 个 Key 算一遍 → $n$ 个 Query × $n$ 个 Key = $n^2$ 次运算
- **线性**：所有 Key-Value 先累积成一个 $d \times d_v$ 小矩阵（计算量 $O(n)$）→ 每个 Query 只和这个小矩阵算（$n$ 次 × 常数）→ 总共 $O(n)$ 次运算

### 数学原理

**传统 Softmax 注意力**:
$$
\text{Attention} = \text{softmax}\left(\frac{QK^T}{\sqrt{d}}\right) V \quad \text{(复杂度 } O(n^2)\text{)}
$$

**线性注意力**（去掉 Softmax，改用核函数 $\phi$）:
$$
\text{Attention} = \phi(Q) \cdot (\phi(K)^T \cdot V) \quad \text{(复杂度 } O(n)\text{)}
$$

其中 $\phi(x) = \text{elu}(x) + 1$ 是一个特征映射函数，把 $Q, K$ 映射到另一个空间。

### 为什么改了顺序就能加速？

**关键**: 矩阵乘法的结合律允许我们改变计算顺序：

$$(A \cdot B) \cdot C = A \cdot (B \cdot C)$$

但矩阵乘法的复杂度是：**结果矩阵的行 × 列 × 中间维度**

**传统做法** - 先算 $Q \cdot K^T$:
- $Q$: $(n \times d)$，$K^T$: $(d \times n)$
- 结果: $(n \times n)$，计算量: $n \cdot n \cdot d = O(n^2)$
- 这个 $n \times n$ 的注意力矩阵就是瓶颈！

**线性做法** - 先算 $\phi(K)^T \cdot V$:
- $\phi(K)^T$: $(c \times n)$，$V$: $(n \times d_v)$  
- 结果: $(c \times d_v)$，计算量: $c \cdot d_v \cdot n = O(n)$（只算一次！）
- 然后每个 Query 和这个小矩阵相乘，每步 $O(1)$，总共 $O(n)$

---

## 复杂度计算详解

### 符号定义

- $n$: 序列长度（token 数量）
- $d_k$: Query/Key 的维度
- $d_v$: Value 的维度
- $Q \in \mathbb{R}^{n \times d_k}$: Query 矩阵
- $K \in \mathbb{R}^{n \times d_k}$: Key 矩阵  
- $V \in \mathbb{R}^{n \times d_v}$: Value 矩阵

### 传统 Softmax 注意力复杂度

**计算步骤**：

1. **计算 $QK^T$**: $(n \times d_k) \cdot (d_k \times n) = n \times n$ 矩阵
   - 计算量：$n \cdot n \cdot d_k = O(n^2 d_k)$
   
2. **Softmax 归一化**: 对 $n \times n$ 矩阵逐行计算
   - 计算量：$O(n^2)$
   
3. **乘以 $V$**: $(n \times n) \cdot (n \times d_v) = n \times d_v$ 矩阵
   - 计算量：$n \cdot n \cdot d_v = O(n^2 d_v)$

**总复杂度**：
$$
\text{时间复杂度} = O(n^2 d_k + n^2 d_v) = O(n^2 \cdot \max(d_k, d_v))
$$

**内存复杂度**：需要存储 $n \times n$ 的注意力矩阵
$$
\text{空间复杂度} = O(n^2)
$$

### 线性注意力复杂度

线性注意力使用核函数 $\phi$ 将 $Q, K$ 映射到特征空间（维度为 $c$）：

**计算步骤**：

1. **特征映射**: $\phi(Q) \in \mathbb{R}^{n \times c}$, $\phi(K) \in \mathbb{R}^{n \times c}$
   - 计算量：$O(n \cdot c)$

2. **计算 $\phi(K)^T V$（关键步骤）**: $(c \times n) \cdot (n \times d_v) = c \times d_v$ 矩阵
   - 计算量：$c \cdot n \cdot d_v = O(n \cdot c \cdot d_v)$
   - **重要**：这个结果只需要计算 **一次**！

3. **计算输出**: $\phi(Q) \cdot (K^T V)$: $(n \times c) \cdot (c \times d_v) = n \times d_v$ 矩阵
   - 计算量：$n \cdot c \cdot d_v = O(n \cdot c \cdot d_v)$

**总复杂度**：
$$
\text{时间复杂度} = O(n \cdot c \cdot d_v)
$$

当 $c$ 为常数（或较小）时：
$$
\text{时间复杂度} = O(n)
$$

**内存复杂度**：不需要存储 $n \times n$ 矩阵
$$
\text{空间复杂度} = O(n \cdot \max(c, d_v)) = O(n)
$$

### 对比总结

| 步骤 | 传统注意力 | 线性注意力 | 说明 |
|------|-----------|-----------|------|
| 主要矩阵运算 | $QK^T$ ($n \times n$) | $\phi(K)^T V$ ($c \times d_v$) | 后者与序列长度无关 |
| 时间复杂度 | $O(n^2)$ | $O(n)$ | 线性 attention 快 $n$ 倍 |
| 空间复杂度 | $O(n^2)$ | $O(n)$ | 内存随序列线性增长 |
| 适用场景 | 短序列 | 长序列 | $n > d^2$ 时优势明显 |

### 直观理解

**为什么能加速？**

传统注意力：每个 token 都要和 **所有其他 token** 计算相似度 → 全连接图 → $n^2$ 复杂度

线性注意力：每个 token 只和 **累积的状态** 交互 → 类似 RNN → $n$ 复杂度

```
传统: 每对 token 之间都有连接    线性: 每个 token 只连接状态
     ○ ←──→ ○ ←──→ ○                ○ ──→ [状态] ←── ○
     ↕      ↕      ↕                      ↓
     ○ ←──→ ○ ←──→ ○                     ○
```

---

## 核心创新点

### 1. 复杂度优化
| 指标 | 传统 Transformer | 线性 Transformer |
|------|------------------|------------------|
| 时间复杂度 | $O(n^2)$ | **$O(n)$** |
| 内存复杂度 | $O(n^2)$ | **$O(n)$** |
| 推理速度 | 随序列平方增长 | **恒定每步** |

### 2. Transformers are RNNs（论文标题的由来）

通过引入因果掩码，作者证明：**任何带因果掩码的 Transformer 都可以重写为 RNN 形式**。

**RNN 形式的状态更新**:
$$
s_i = s_{i-1} + \phi(K_i) \cdot V_i^T \quad \text{(注意力状态，累加历史信息)}
$$

$$
z_i = z_{i-1} + \phi(K_i) \quad \text{(归一化状态)}
$$

$$
\text{output}_i = f\left( \frac{\phi(Q_i)^T \cdot s_i}{\phi(Q_i)^T \cdot z_i} \right)
$$

这意味着：
- **训练时**: 像 Transformer 一样并行计算（高效）
- **推理时**: 像 RNN 一样恒定内存、线性时间（超快）

---

## 实验结果

| 任务 | 性能 | 速度提升 |
|------|------|----------|
| MNIST 图像生成 | 与 Softmax 相当 | **300×** |
| CIFAR-10 图像生成 | 与 Softmax 相当 | **4,000×** |
| 语音识别 (WSJ) | 优于 LSTM 和 Reformer | **3×** 训练加速 |

---

## 应用场景

线性注意力特别适合以下场景：

1. **超长序列**: DNA/蛋白质序列、长文档处理
2. **自回归生成**: 图像生成、语音合成、文本生成
3. **实时推理**: 需要低延迟的在线服务
4. **资源受限设备**: 移动端、嵌入式设备

---

## 与后续工作的关系

线性注意力是后续一系列高效 Transformer 的基础：

| 方法 | 关系 | 特点 |
|------|------|------|
| **Performer** | 同期工作 | 用随机特征近似 Softmax |
| **Linformer** | 同期工作 | 低秩投影压缩注意力矩阵 |
| **RWKV** | 后续发展 | 完全 RNN 化的线性注意力语言模型 |
| **Mamba** | 后续发展 | 选择性状态空间模型 (SSM) |

---

## 个人思考

### 优点
- 优雅的数学技巧，将 $O(n^2)$ 问题转化为 $O(n)$
- 训练和推理可以灵活切换模式（并行 vs 串行）
- 揭示了 Transformer 和 RNN 的深层联系

### 局限
- 使用了 $\text{elu}(x) + 1$ 代替 Softmax，可能损失部分表达能力
- 需要足够长的序列才能体现优势（$N > D^2$）
- 注意力矩阵不再是标准的概率分布（无显式归一化）

### 启发
这篇论文的价值不仅在于加速，更在于**统一了两种看似不同的架构**。理解这种联系有助于设计新的模型架构。

---

## 关键公式速查

**特征映射**:
$$
\phi(x) = \text{elu}(x) + 1
$$

**线性注意力计算**:
$$
V'_i = \frac{\phi(Q_i)^T \sum_j \phi(K_j) V_j^T}{\phi(Q_i)^T \sum_j \phi(K_j)}
$$

**RNN 形式**:
$$
s_i = s_{i-1} + \phi(K_i) \cdot V_i^T
$$

$$
z_i = z_{i-1} + \phi(K_i)
$$

---

## 延伸阅读

- [[resources/论文阅读/papers/LinearAttention_Transformers_are_RNNs_Fast_Autoregressive_Transformers_with_Linear_Attention/ocr|论文全文 (OCR)]]
- Performer: Rethinking Attention with Performers (FAVOR+)
- RWKV: Reinventing RNNs for the Transformer Era
- Mamba: Linear-Time Sequence Modeling with Selective State Spaces

---

**阅读日期**: 2026-02-16  
**阅读状态**: ✅ 已读（核心概念理解）
