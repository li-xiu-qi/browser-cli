# 硅基流动 Embedding 工具

基于 SiliconFlow API 的文本 Embedding 工具，支持 BAAI/bge-m3 等模型。

## 功能特性

- ✅ 单条/批量文本 embedding
- ✅ 文本相似度计算（余弦相似度）
- ✅ 支持多种模型（BAAI/bge-m3, Qwen3-Embedding 等）
- ✅ JSON 输出格式

## 支持的模型

| 模型 | 最大 Tokens | 特点 |
|------|------------|------|
| BAAI/bge-m3 | 8192 | 默认模型，中英双语，高质量 |
| BAAI/bge-large-zh-v1.5 | 512 | 中文优化 |
| BAAI/bge-large-en-v1.5 | 512 | 英文优化 |
| Qwen/Qwen3-Embedding-8B | 32768 | 长文本支持 |
| Qwen/Qwen3-Embedding-4B | 32768 | 长文本支持 |

## 配置

### 1. 设置 API Key

**方式一**: 环境变量（推荐）
```bash
# Windows PowerShell
$env:SILICONFLOW_API_KEY="sk-tcgyvneoqksdohcvgarkduafhmjvcvcmzcfvspgltookbygk"

# 永久设置（用户级）
[Environment]::SetEnvironmentVariable('SILICONFLOW_API_KEY', 'your_key', 'User')
```

**方式二**: 命令行参数
```bash
python embedding.py -k "your_key" embed "测试文本"
```

### 2. 检查配置

```bash
python embedding.py embed "测试"
```

## 使用示例

### 单条文本 Embedding

```bash
# 默认模型 (BAAI/bge-m3)
python embedding.py embed "这是一段测试文本"

# 指定模型
python embedding.py embed "测试文本" -m "BAAI/bge-m3"

# 保存到文件
python embedding.py embed "测试文本" -o output.json
```

输出示例：
```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.0123, -0.0456, ...],
      "index": 0
    }
  ],
  "model": "BAAI/bge-m3",
  "usage": {
    "prompt_tokens": 10,
    "total_tokens": 10
  }
}
```

### 批量 Embedding

创建文本文件 `texts.txt`（每行一个文本）：
```
这是一段测试文本
这是另一段文本
第三段文本
```

或者 JSON 文件 `texts.json`：
```json
["文本1", "文本2", "文本3"]
```

执行批量处理：
```bash
python embedding.py embed-batch texts.txt -o embeddings.json
```

### 文本相似度计算

```bash
python embedding.py similarity "苹果" "香蕉"

python embedding.py similarity "机器学习" "深度学习"
```

输出示例：
```
📊 相似度: 0.8234
💡 说明: 高度相似
```

## Python API 使用

```python
from embedding import SiliconFlowEmbedding

# 初始化客户端
client = SiliconFlowEmbedding(
    api_key="your_key",
    model="BAAI/bge-m3"
)

# 单条 embedding
vector = client.embed_single("测试文本")
print(f"维度: {len(vector)}")

# 批量 embedding
vectors = client.embed_batch(["文本1", "文本2", "文本3"])

# 计算相似度
score = client.similarity("文本A", "文本B")
print(f"相似度: {score}")
```

## 在 Obsidian 中使用

配合 Templater 或 Dataview 插件：

```javascript
// 获取当前笔记内容的 embedding
const content = tp.file.content;
const result = await app.plugins.plugins["obsidian-shellcommands"].execute(
    `python .agents/tools/siliconflow-embedding/embedding.py embed "${content.substring(0, 500)}"`
);
```

## API 文档

参考官方文档：https://docs.siliconflow.cn/cn/api-reference/embeddings/create-embeddings

## 依赖

```bash
pip install requests
```

## 注意事项

1. API Key 请妥善保管，不要提交到 GitHub
2. 长文本注意模型 token 限制（BAAI/bge-m3 支持 8192 tokens）
3. 批量请求有速率限制，建议控制并发
