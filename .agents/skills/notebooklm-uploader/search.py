#!/usr/bin/env python3
"""
Z-Library 搜索脚本 - 基于 Zlibrary-API
"""

import sys
import json
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from Zlibrary import Zlibrary


def search_books(query: str, limit: int = 10):
    """搜索书籍"""
    print("=" * 70)
    print(f"🔍 搜索: {query}")
    print("=" * 70)
    
    # 创建 Zlibrary 实例（不登录，使用匿名搜索）
    Z = Zlibrary()
    
    try:
        # 搜索书籍
        results = Z.search(message=query, limit=limit)
        
        if not results or "books" not in results:
            print("❌ 未找到结果或搜索失败")
            return None
        
        books = results["books"]
        
        if not books:
            print("❌ 没有找到相关书籍")
            return None
        
        print(f"\n✅ 找到 {len(books)} 本书:\n")
        print("-" * 70)
        
        for i, book in enumerate(books, 1):
            print(f"\n[{i}] {book.get('name', 'Unknown Title')}")
            print(f"    作者: {book.get('author', 'Unknown Author')}")
            print(f"    年份: {book.get('year', 'N/A')}")
            print(f"    格式: {book.get('extension', 'N/A')}")
            print(f"    大小: {book.get('size', 'N/A')}")
            print(f"    评分: {book.get('rating', 'N/A')}")
            print(f"    ID: {book.get('id', 'N/A')}")
            if book.get('href'):
                print(f"    链接: {book.get('href')}")
        
        print("\n" + "=" * 70)
        return books
        
    except Exception as e:
        print(f"❌ 搜索出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python search.py <搜索关键词>")
        print('示例: python search.py "开口之后"')
        sys.exit(1)
    
    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    books = search_books(query, limit)
    
    if books:
        # 保存结果到 JSON 文件
        output_file = Path(__file__).parent / "search_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(books, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
