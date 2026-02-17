#!/usr/bin/env python3
"""
硅基流动 Embedding 工具
支持 BAAI/bge-m3 等模型
API 文档: https://docs.siliconflow.cn/cn/api-reference/embeddings/create-embeddings
"""

import os
import sys
import json
import argparse
from typing import Union, List, Optional
from pathlib import Path

# API 配置
API_BASE = "https://api.siliconflow.cn/v1"
DEFAULT_MODEL = "BAAI/bge-m3"
MAX_TOKENS = {
    "BAAI/bge-large-zh-v1.5": 512,
    "BAAI/bge-large-en-v1.5": 512,
    "netease-youdao/bce-embedding-base_v1": 512,
    "BAAI/bge-m3": 8192,
    "Pro/BAAI/bge-m3": 8192,
    "Qwen/Qwen3-Embedding-8B": 32768,
    "Qwen/Qwen3-Embedding-4B": 32768,
    "Qwen/Qwen3-Embedding-0.6B": 32768,
}


class SiliconFlowEmbedding:
    """硅基流动 Embedding 客户端"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        """
        初始化客户端
        
        Args:
            api_key: API Key，None 则从环境变量 SILICONFLOW_API_KEY 读取
            model: 模型名称，默认 BAAI/bge-m3
        """
        self.api_key = api_key or os.environ.get('SILICONFLOW_API_KEY')
        if not self.api_key:
            raise ValueError("需要提供 API Key 或设置 SILICONFLOW_API_KEY 环境变量")
        
        self.model = model
        self.api_url = f"{API_BASE}/embeddings"
        
        # 检查模型
        if model not in MAX_TOKENS:
            print(f"警告: 未知模型 {model}，使用默认 token 限制 8192")
            self.max_tokens = 8192
        else:
            self.max_tokens = MAX_TOKENS[model]
        
        # 初始化 HTTP 会话
        try:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            })
        except ImportError:
            raise ImportError("需要安装 requests: pip install requests")
    
    def embed(self, 
              input_text: Union[str, List[str]], 
              encoding_format: str = "float",
              dimensions: Optional[int] = None) -> dict:
        """
        获取文本的 embedding
        
        Args:
            input_text: 输入文本，可以是字符串或字符串列表
            encoding_format: 编码格式，默认 float (可选: base64)
            dimensions: 指定输出维度（部分模型支持）
        
        Returns:
            API 响应结果
        """
        # 处理输入
        if isinstance(input_text, str):
            texts = [input_text]
        else:
            texts = input_text
        
        # 检查空输入
        if not texts or all(not t.strip() for t in texts):
            raise ValueError("输入不能为空")
        
        # 构建请求
        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": encoding_format
        }
        
        if dimensions:
            payload["dimensions"] = dimensions
        
        # 发送请求
        try:
            response = self.session.post(
                self.api_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            raise Exception(f"Embedding API 调用失败: {e}")
    
    def embed_single(self, text: str, **kwargs) -> List[float]:
        """
        获取单条文本的 embedding 向量
        
        Args:
            text: 输入文本
            **kwargs: 其他参数
        
        Returns:
            embedding 向量（列表）
        """
        result = self.embed(text, **kwargs)
        
        if "data" in result and len(result["data"]) > 0:
            return result["data"][0].get("embedding", [])
        
        raise Exception("API 响应中未找到 embedding 数据")
    
    def embed_batch(self, texts: List[str], **kwargs) -> List[List[float]]:
        """
        批量获取文本的 embedding 向量
        
        Args:
            texts: 文本列表
            **kwargs: 其他参数
        
        Returns:
            embedding 向量列表
        """
        if not texts:
            return []
        
        result = self.embed(texts, **kwargs)
        
        embeddings = []
        if "data" in result:
            # 按 index 排序
            sorted_data = sorted(result["data"], key=lambda x: x.get("index", 0))
            embeddings = [item.get("embedding", []) for item in sorted_data]
        
        return embeddings
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（余弦相似度）
        
        Args:
            text1: 文本1
            text2: 文本2
        
        Returns:
            相似度分数 (-1 到 1)
        """
        import math
        
        # 获取 embedding
        embeddings = self.embed_batch([text1, text2])
        
        if len(embeddings) != 2:
            raise Exception("无法获取 embedding")
        
        vec1, vec2 = embeddings[0], embeddings[1]
        
        # 计算余弦相似度
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


def save_embedding(data: dict, output_path: str):
    """保存 embedding 结果到文件"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 结果已保存: {output_file}")


def cmd_embed(args):
    """单条文本 embedding"""
    client = SiliconFlowEmbedding(api_key=args.api_key, model=args.model)
    
    print(f"📝 输入文本: {args.text[:50]}..." if len(args.text) > 50 else f"📝 输入文本: {args.text}")
    print(f"🤖 使用模型: {args.model}")
    
    try:
        result = client.embed(args.text, encoding_format=args.format)
        
        # 显示结果摘要
        if "data" in result and len(result["data"]) > 0:
            embedding = result["data"][0].get("embedding", [])
            print(f"✅ Embedding 维度: {len(embedding)}")
            print(f"📊 前 5 个值: {embedding[:5]}")
        
        # 保存结果
        if args.output:
            save_embedding(result, args.output)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        
        return 0
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1


def cmd_embed_batch(args):
    """批量 embedding"""
    client = SiliconFlowEmbedding(api_key=args.api_key, model=args.model)
    
    # 读取输入文件
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"❌ 文件不存在: {input_file}")
        return 1
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            if args.input.endswith('.json'):
                texts = json.load(f)
            else:
                texts = [line.strip() for line in f if line.strip()]
        
        if not isinstance(texts, list):
            print("❌ 输入文件必须是 JSON 数组或文本行")
            return 1
        
        print(f"📝 批量处理 {len(texts)} 条文本")
        print(f"🤖 使用模型: {args.model}")
        
        results = client.embed_batch(texts, encoding_format=args.format)
        
        print(f"✅ 成功获取 {len(results)} 个 embedding")
        print(f"📊 维度: {len(results[0]) if results else 0}")
        
        # 保存结果
        output_data = {
            "model": args.model,
            "count": len(results),
            "dimensions": len(results[0]) if results else 0,
            "embeddings": [
                {"index": i, "text": texts[i], "embedding": emb}
                for i, emb in enumerate(results)
            ]
        }
        
        save_embedding(output_data, args.output or "embeddings.json")
        return 0
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1


def cmd_similarity(args):
    """计算文本相似度"""
    client = SiliconFlowEmbedding(api_key=args.api_key, model=args.model)
    
    print(f"📝 文本1: {args.text1}")
    print(f"📝 文本2: {args.text2}")
    print(f"🤖 使用模型: {args.model}")
    
    try:
        similarity = client.similarity(args.text1, args.text2)
        
        print(f"\n📊 相似度: {similarity:.4f}")
        
        # 解释结果
        if similarity > 0.9:
            print("💡 说明: 高度相似")
        elif similarity > 0.7:
            print("💡 说明: 中等相似")
        elif similarity > 0.5:
            print("💡 说明: 弱相似")
        else:
            print("💡 说明: 不相似")
        
        return 0
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="硅基流动 Embedding 工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单条文本 embedding
  python embedding.py embed "这是一段测试文本"
  
  # 指定模型
  python embedding.py embed "测试文本" -m "BAAI/bge-m3"
  
  # 批量处理
  python embedding.py embed-batch texts.txt -o embeddings.json
  
  # 计算相似度
  python embedding.py similarity "苹果" "香蕉"
        """
    )
    
    # 全局选项
    parser.add_argument("--api-key", "-k", 
                       help="API Key (默认从 SILICONFLOW_API_KEY 环境变量读取)")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL,
                       help=f"模型名称 (默认: {DEFAULT_MODEL})")
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # embed 命令
    embed_parser = subparsers.add_parser('embed', help='单条文本 embedding')
    embed_parser.add_argument('text', help='输入文本')
    embed_parser.add_argument('--format', default='float', 
                             choices=['float', 'base64'],
                             help='编码格式 (默认: float)')
    embed_parser.add_argument('--output', '-o', help='输出文件路径')
    embed_parser.set_defaults(func=cmd_embed)
    
    # embed-batch 命令
    batch_parser = subparsers.add_parser('embed-batch', help='批量 embedding')
    batch_parser.add_argument('input', help='输入文件 (每行一个文本或 JSON 数组)')
    batch_parser.add_argument('--format', default='float',
                             choices=['float', 'base64'],
                             help='编码格式 (默认: float)')
    batch_parser.add_argument('--output', '-o', help='输出文件路径 (默认: embeddings.json)')
    batch_parser.set_defaults(func=cmd_embed_batch)
    
    # similarity 命令
    sim_parser = subparsers.add_parser('similarity', help='计算文本相似度')
    sim_parser.add_argument('text1', help='文本1')
    sim_parser.add_argument('text2', help='文本2')
    sim_parser.set_defaults(func=cmd_similarity)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
