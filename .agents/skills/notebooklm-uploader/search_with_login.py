#!/usr/bin/env python3
"""
Z-Library 搜索脚本 - 使用已保存的登录 token
"""

import sys
import json
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from Zlibrary import Zlibrary


def get_saved_tokens():
    """获取保存的 token"""
    project_root = Path(__file__).parent.parent.parent.parent
    config_dir = project_root / ".agents" / "tools" / "zlibrary" / "config"
    
    # 尝试读取提取的 token
    token_file = config_dir / "zl_tokens.json"
    if token_file.exists():
        with open(token_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # 如果没有提取的 token，尝试从 storage_state.json 读取
    storage_state = config_dir / "storage_state.json"
    if storage_state.exists():
        with open(storage_state, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cookies = data.get('cookies', [])
        tokens = {}
        for cookie in cookies:
            name = cookie.get('name', '')
            if name == 'remix_userid':
                tokens['remix_userid'] = cookie.get('value')
            elif name == 'remix_userkey':
                tokens['remix_userkey'] = cookie.get('value')
        
        if tokens.get('remix_userid') and tokens.get('remix_userkey'):
            return tokens
    
    return None


def search_books(query: str, limit: int = 10):
    """搜索书籍"""
    print("=" * 70)
    print(f"🔍 搜索: {query}")
    print("=" * 70)
    
    # 获取保存的 token
    tokens = get_saved_tokens()
    
    if not tokens:
        print("❌ 未找到登录 token")
        print("💡 请先运行以下步骤:")
        print("   1. python scripts/login.py  (完成登录)")
        print("   2. python extract_cookies.py  (提取 token)")
        return None
    
    print(f"✅ 使用已保存的登录 token")
    
    # 使用 token 创建 Zlibrary 实例
    Z = Zlibrary(
        remix_userid=tokens['remix_userid'],
        remix_userkey=tokens['remix_userkey']
    )
    
    try:
        # 搜索书籍
        print(f"📝 正在搜索...")
        results = Z.search(message=query, limit=limit)
        
        if not results or "books" not in results:
            print("❌ 未找到结果或搜索失败")
            print(f"   响应: {results}")
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
                print(f"    链接: https://zh.zlib.li{book.get('href')}")
        
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
        print("用法: python search_with_login.py <搜索关键词>")
        print('示例: python search_with_login.py "开口之后"')
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
