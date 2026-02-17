#!/usr/bin/env python3
"""
Z-Library 交互式搜索工具
支持搜索、选择、下载一体化
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from Zlibrary import Zlibrary


class ZLibrarySearchTool:
    """Z-Library 搜索工具"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.config_dir = self.project_root / "config"
        self.downloads_dir = Path(__file__).parent.parent.parent.parent / "resources" / "downloads" / "books"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        
    def get_saved_tokens(self) -> Optional[Dict]:
        """获取保存的登录 token"""
        # 尝试读取提取的 token
        token_file = self.config_dir / "zl_tokens.json"
        if token_file.exists():
            with open(token_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 如果没有提取的 token，尝试从 storage_state.json 读取
        storage_state = self.config_dir / "storage_state.json"
        if storage_state.exists():
            with open(storage_state, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cookies = data.get('cookies', [])
            if not cookies:
                return None
                
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
    
    def check_login(self) -> bool:
        """检查是否已登录（简化版，只检查 token 是否存在）"""
        tokens = self.get_saved_tokens()
        return tokens is not None and 'remix_userid' in tokens and 'remix_userkey' in tokens
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索书籍"""
        print("=" * 70)
        print(f"🔍 搜索: {query}")
        print("=" * 70)
        
        tokens = self.get_saved_tokens()
        if not tokens:
            print("❌ 未找到登录 token")
            self.show_login_guide()
            return []
        
        print(f"✅ 使用已保存的登录 token")
        
        Z = Zlibrary(
            remix_userid=tokens['remix_userid'],
            remix_userkey=tokens['remix_userkey']
        )
        
        try:
            print(f"📝 正在搜索...")
            results = Z.search(message=query, limit=limit)
            
            if not results or "books" not in results:
                print("❌ 未找到结果或搜索失败")
                if results:
                    print(f"   响应: {results}")
                return []
            
            books = results["books"]
            
            if not books:
                print("❌ 没有找到相关书籍")
                return []
            
            print(f"\n✅ 找到 {len(books)} 本书:\n")
            return books
            
        except Exception as e:
            print(f"❌ 搜索出错: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def display_books(self, books: List[Dict]):
        """显示书籍列表"""
        print("-" * 70)
        for i, book in enumerate(books, 1):
            # API 可能返回 name 或 title
            title = book.get('name') or book.get('title') or 'Unknown Title'
            author = book.get('author') or book.get('authors') or 'Unknown Author'
            print(f"\n[{i}] {title}")
            print(f"    作者: {author}")
            print(f"    年份: {book.get('year', 'N/A')}")
            print(f"    格式: {book.get('extension', 'N/A')}")
            print(f"    大小: {book.get('size', 'N/A')}")
            print(f"    评分: {book.get('rating', 'N/A')}")
            print(f"    ID: {book.get('id', 'N/A')}")
            # 修复链接拼接问题
            href = book.get('href', '')
            if href:
                if href.startswith('http'):
                    print(f"    链接: {href}")
                else:
                    print(f"    链接: https://zh.zlib.li{href}")
        print("\n" + "=" * 70)
    
    def select_book(self, books: List[Dict]) -> Optional[Dict]:
        """交互式选择书籍"""
        while True:
            try:
                choice = input("\n请选择书籍编号 (1-{}, 0=退出): ".format(len(books)))
                idx = int(choice)
                if idx == 0:
                    return None
                if 1 <= idx <= len(books):
                    return books[idx - 1]
                print("❌ 无效的选择，请重新输入")
            except ValueError:
                print("❌ 请输入数字")
    
    def download_book(self, book: Dict) -> bool:
        """下载书籍"""
        print("\n" + "=" * 70)
        print(f"📥 开始下载: {book.get('name')}")
        print("=" * 70)
        
        tokens = self.get_saved_tokens()
        Z = Zlibrary(
            remix_userid=tokens['remix_userid'],
            remix_userkey=tokens['remix_userkey']
        )
        
        try:
            # 获取书籍详情以获取 hash
            book_id = book.get('id')
            book_hash = book.get('hash')
            
            if not book_hash and book.get('href'):
                # 从 href 中提取 hash
                href = book.get('href', '')
                parts = href.split('/')
                if len(parts) >= 3:
                    book_hash = parts[2]
            
            if not book_hash:
                print("❌ 无法获取书籍 hash")
                return False
            
            print(f"📖 获取书籍信息 (ID: {book_id}, Hash: {book_hash})...")
            
            # 获取书籍文件
            book_info = {
                'id': book_id,
                'hash': book_hash
            }
            
            result = Z.downloadBook(book_info)
            
            if result:
                filename, content = result
                filepath = self.downloads_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                file_size = filepath.stat().st_size / 1024
                print(f"✅ 下载成功!")
                print(f"   文件: {filename}")
                print(f"   路径: {filepath}")
                print(f"   大小: {file_size:.1f} KB")
                return True
            else:
                print("❌ 下载失败")
                return False
                
        except Exception as e:
            print(f"❌ 下载出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def show_login_guide(self):
        """显示登录指南"""
        print("\n" + "=" * 70)
        print("💡 请先完成登录")
        print("=" * 70)
        print("步骤 1: 运行登录脚本")
        print("   .venv\\Scripts\\python.exe .agents\\tools\\zlibrary\\login.py")
        print("")
        print("步骤 2: 在浏览器中完成登录")
        print("   - 浏览器会自动打开 Z-Library")
        print("   - 输入账号密码完成登录")
        print("   - 关闭浏览器窗口")
        print("")
        print("步骤 3: 重新运行搜索")
        print("   .venv\\Scripts\\python.exe .agents\\tools\\zlibrary\\zlib_search.py \"书名\"")
        print("=" * 70)
    
    def run(self):
        """运行交互式搜索"""
        # 检查命令行参数
        if len(sys.argv) < 2:
            print("用法: python zlib_search.py <搜索关键词>")
            print('示例: python zlib_search.py "认知觉醒"')
            print("")
            print("交互式操作:")
            print("  1. 输入书名搜索")
            print("  2. 从结果列表中选择")
            print("  3. 自动下载选中的书籍")
            sys.exit(1)
        
        query = sys.argv[1]
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        
        # 检查登录状态
        if not self.check_login():
            self.show_login_guide()
            return
        
        # 搜索
        books = self.search(query, limit)
        
        if not books:
            return
        
        # 显示结果
        self.display_books(books)
        
        # 交互式选择
        while True:
            book = self.select_book(books)
            if book is None:
                print("👋 已退出")
                break
            
            # 询问操作
            print(f"\n已选择: {book.get('name')}")
            print("操作选项:")
            print("  1. 下载此书")
            print("  2. 查看详情")
            print("  3. 返回列表")
            
            action = input("请选择操作 (1-3): ").strip()
            
            if action == "1":
                self.download_book(book)
            elif action == "2":
                print(f"\n详情:")
                print(f"  书名: {book.get('name')}")
                print(f"  作者: {book.get('author')}")
                print(f"  出版社: {book.get('publisher', 'N/A')}")
                print(f"  年份: {book.get('year', 'N/A')}")
                print(f"  语言: {book.get('language', 'N/A')}")
                print(f"  页数: {book.get('pages', 'N/A')}")
                print(f"  格式: {book.get('extension', 'N/A')}")
                print(f"  大小: {book.get('size', 'N/A')}")
                print(f"  评分: {book.get('rating', 'N/A')}")
                if book.get('href'):
                    print(f"  链接: https://zh.zlib.li{book.get('href')}")
            elif action == "3":
                self.display_books(books)
            else:
                print("❌ 无效的选择")


def main():
    """主函数"""
    tool = ZLibrarySearchTool()
    tool.run()


if __name__ == "__main__":
    main()
