#!/usr/bin/env python3
"""
Z-Library 搜索脚本 V2 - 基于 sertraline/zlibrary
支持异步搜索
"""

import sys
import asyncio
import json
from pathlib import Path

import zlibrary


async def search_books(query: str, limit: int = 10):
    """搜索书籍"""
    print("=" * 70)
    print(f"🔍 搜索: {query}")
    print("=" * 70)
    
    lib = zlibrary.AsyncZlib()
    
    try:
        # 尝试不登录搜索
        print("📝 正在搜索（无需登录）...")
        paginator = await lib.search(q=query, count=limit)
        results = await paginator.next()
        
        if not results:
            print("❌ 未找到结果")
            return None
        
        print(f"\n✅ 找到 {len(results)} 本书:\n")
        print("-" * 70)
        
        for i, book in enumerate(results, 1):
            print(f"\n[{i}] {book.name}")
            print(f"    作者: {', '.join(a['author'] for a in book.authors) if book.authors else 'N/A'}")
            print(f"    年份: {book.year}")
            print(f"    格式: {book.extension}")
            print(f"    大小: {book.size}")
            print(f"    评分: {book.rating}")
            print(f"    链接: {book.url}")
        
        print("\n" + "=" * 70)
        return results
        
    except Exception as e:
        print(f"❌ 搜索出错: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await lib.close()


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python search_v2.py <搜索关键词>")
        print('示例: python search_v2.py "开口之后"')
        sys.exit(1)
    
    query = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    books = await search_books(query, limit)
    
    if books:
        # 转换为字典保存
        books_data = []
        for book in books:
            books_data.append({
                'name': book.name,
                'url': book.url,
                'id': book.id,
                'year': book.year,
                'extension': book.extension,
                'size': book.size,
                'rating': book.rating,
                'authors': book.authors,
            })
        
        output_file = Path(__file__).parent / "search_results_v2.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(books_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 结果已保存到: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
