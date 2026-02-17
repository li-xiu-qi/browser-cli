#!/usr/bin/env python3
"""
Z-Library AI API - 非交互式搜索下载工具
供AI自动调用，无需用户交互
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Optional, Callable

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from Zlibrary import Zlibrary
from zlib_reviews import ZLibraryReviews


class ZLibraryAPI:
    """Z-Library AI API - 非交互式接口"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.config_dir = self.project_root / "config"
        self.downloads_dir = Path(__file__).parent.parent.parent.parent / "resources" / "downloads" / "books"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def get_saved_tokens(self) -> Optional[Dict]:
        """获取保存的登录 token"""
        # 1. 先检查本地 token 文件
        token_file = self.config_dir / "zl_tokens.json"
        if token_file.exists():
            with open(token_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 2. 检查 storage_state.json
        storage_state = self.config_dir / "storage_state.json"
        if storage_state.exists():
            tokens = self._extract_tokens_from_storage(storage_state)
            if tokens:
                return tokens
        
        # 3. 从 browser_user_data 提取（Playwright 持久化数据）
        tokens = self._extract_tokens_from_browser_data()
        if tokens:
            # 保存到本地，下次直接使用
            self._save_tokens(tokens)
            return tokens
        
        return None
    
    def _extract_tokens_from_storage(self, storage_file: Path) -> Optional[Dict]:
        """从 storage_state.json 提取 token"""
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            cookies = data.get('cookies', [])
            return self._parse_tokens_from_cookies(cookies)
        except Exception as e:
            print(f"⚠️ 解析 storage_state 失败: {e}")
            return None
    
    def _extract_tokens_from_browser_data(self) -> Optional[Dict]:
        """从 browser_user_data 目录提取 Z-Library token"""
        # 查找 Playwright 的 cookie 数据库
        # 从 zlibrary → tools → resource-crawler → skills → .agents → 项目根目录 (笔记专用)
        project_root = Path(__file__).parent.parent.parent.parent.parent.parent
        browser_data_dir = project_root / ".agents" / "browser_user_data"
        
        print(f"🔍 查找 browser_user_data: {browser_data_dir}")
        
        if not browser_data_dir.exists():
            print(f"   目录不存在")
            return None
        
        print(f"   目录存在，尝试提取 cookies...")
        
        try:
            # 方法1: 启动浏览器会话读取 cookies（最可靠）
            print(f"   尝试启动浏览器读取 cookies...")
            tokens = self._extract_from_browser_session(browser_data_dir)
            if tokens:
                return tokens
            
            # 方法2: 查找 Default/Cookies 数据库 (Chrome)
            cookie_db = browser_data_dir / "Default" / "Cookies"
            if cookie_db.exists():
                print(f"   尝试读取 Cookies 数据库...")
                tokens = self._extract_from_chrome_cookies(cookie_db)
                if tokens:
                    return tokens
            
            # 方法3: 查找 Network/Cookies (Playwright)
            cookie_db = browser_data_dir / "Default" / "Network" / "Cookies"
            if cookie_db.exists():
                print(f"   尝试读取 Network Cookies 数据库...")
                tokens = self._extract_from_chrome_cookies(cookie_db)
                if tokens:
                    return tokens
                
        except Exception as e:
            print(f"⚠️ 从 browser_user_data 提取 token 失败: {e}")
        
        return None
    
    def _extract_from_browser_session(self, browser_data_dir: Path) -> Optional[Dict]:
        """启动浏览器会话读取 cookies"""
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                # 启动持久化上下文（会读取已有的 browser_user_data）
                browser = p.chromium.launch_persistent_context(
                    user_data_dir=str(browser_data_dir),
                    headless=True,  # 无头模式
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                # 获取所有 cookies
                cookies = browser.cookies()
                browser.close()
                
                print(f"   获取到 {len(cookies)} 个 cookies")
                
                return self._parse_tokens_from_cookies(cookies)
                
        except Exception as e:
            print(f"⚠️ 浏览器会话读取失败: {e}")
            return None
    
    def _extract_from_chrome_cookies(self, db_path: Path) -> Optional[Dict]:
        """从 Chrome cookie 数据库提取 Z-Library token"""
        import sqlite3
        import tempfile
        import shutil
        
        try:
            # 复制数据库到临时文件（避免锁定）
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                tmp_path = tmp.name
            shutil.copy2(db_path, tmp_path)
            
            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            
            # 查找 Z-Library 相关的 cookies
            cursor.execute("""
                SELECT name, value, host_key FROM cookies 
                WHERE host_key LIKE '%1lib.sk%' 
                   OR host_key LIKE '%z-lib%' 
                   OR host_key LIKE '%z-library%'
            """)
            
            cookies = []
            for row in cursor.fetchall():
                cookies.append({
                    'name': row[0],
                    'value': row[1],
                    'domain': row[2]
                })
            
            conn.close()
            import os
            os.unlink(tmp_path)
            
            return self._parse_tokens_from_cookies(cookies)
            
        except Exception as e:
            print(f"⚠️ 读取 Chrome cookies 失败: {e}")
            return None
    
    def _parse_tokens_from_cookies(self, cookies: list) -> Optional[Dict]:
        """从 cookies 列表解析 Z-Library token"""
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
    
    def _save_tokens(self, tokens: Dict):
        """保存 token 到本地文件"""
        token_file = self.config_dir / "zl_tokens.json"
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump(tokens, f, indent=2)
        print(f"💾 Token 已保存到: {token_file}")
    
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        tokens = self.get_saved_tokens()
        return tokens is not None and 'remix_userid' in tokens and 'remix_userkey' in tokens
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """
        搜索书籍 - 返回结构化数据供AI分析
        
        Returns:
            List[Dict]: 书籍列表，每个包含:
                - id: 书籍ID
                - name: 书名
                - author: 作者
                - year: 年份
                - extension: 格式 (pdf/epub/mobi等)
                - size: 文件大小
                - rating: 评分
                - href: 详情页链接
                - hash: 书籍hash（用于下载）
        """
        if not self.is_logged_in():
            return {"error": "NOT_LOGGED_IN", "message": "请先运行登录脚本"}
        
        tokens = self.get_saved_tokens()
        Z = Zlibrary(
            remix_userid=tokens['remix_userid'],
            remix_userkey=tokens['remix_userkey']
        )
        
        try:
            results = Z.search(message=query, limit=limit)
            
            if not results or "books" not in results:
                return {"error": "SEARCH_FAILED", "message": "搜索失败或返回空结果", "raw": results}
            
            books = results["books"]
            
            # 规范化数据
            normalized = []
            for book in books:
                href = book.get('href', '')
                # 提取 hash
                book_hash = book.get('hash', '')
                if not book_hash and href:
                    parts = href.split('/')
                    if len(parts) >= 3:
                        book_hash = parts[2] if not parts[2].startswith('http') else ''
                
                normalized.append({
                    "id": book.get('id'),
                    "name": book.get('name') or book.get('title') or 'Unknown Title',
                    "author": book.get('author') or book.get('authors') or 'Unknown Author',
                    "year": book.get('year'),
                    "extension": book.get('extension', 'unknown').lower(),
                    "size": book.get('size', 'N/A'),
                    "rating": book.get('rating', 'N/A'),
                    "href": href,
                    "hash": book_hash,
                    "raw": book  # 保留原始数据
                })
            
            return normalized
            
        except Exception as e:
            return {"error": "EXCEPTION", "message": str(e)}
    
    def get_book_reviews(self, book_id: str, max_reviews: int = 5) -> Dict:
        """获取书籍评论"""
        reviews_api = ZLibraryReviews()
        return reviews_api.get_reviews(book_id, max_reviews)
    
    def search_with_reviews(self, query: str, limit: int = 5, max_reviews: int = 3) -> Dict:
        """
        搜索书籍并获取每本书的评论
        
        Returns:
            {
                "query": "搜索词",
                "books": [...],
                "books_with_reviews": [
                    {
                        "book": {...},
                        "reviews": {...}
                    }
                ]
            }
        """
        # 搜索书籍
        books = self.search(query, limit)
        
        if isinstance(books, dict) and "error" in books:
            return books
        
        result = {
            "query": query,
            "total_books": len(books),
            "books": books,
            "books_with_reviews": []
        }
        
        # 为每本书获取评论
        for book in books:
            book_id = book.get('id')
            if book_id:
                reviews = self.get_book_reviews(str(book_id), max_reviews)
                result["books_with_reviews"].append({
                    "book": book,
                    "reviews": reviews
                })
        
        return result
    
    def select_best_book(self, books: List[Dict], prefer_format: str = "pdf") -> Optional[Dict]:
        """
        自动选择最佳书籍 - AI决策逻辑
        
        Args:
            books: 书籍列表
            prefer_format: 优先格式 (pdf/epub/mobi)
        
        Returns:
            最佳匹配的书籍，如果没有则返回None
        """
        if not books or isinstance(books, dict) and "error" in books:
            return None
        
        # 1. 优先选择指定格式
        format_priority = {prefer_format.lower(): 3, "epub": 2, "mobi": 1, "azw3": 1}
        
        scored_books = []
        for book in books:
            score = 0
            ext = book.get('extension', '').lower()
            
            # 格式得分
            score += format_priority.get(ext, 0) * 10
            
            # 有评分加分
            if book.get('rating') and book.get('rating') != 'N/A':
                try:
                    score += float(book.get('rating', 0))
                except:
                    pass
            
            # 较新年份加分
            if book.get('year'):
                try:
                    year = int(book.get('year'))
                    if year >= 2020:
                        score += 5
                    elif year >= 2015:
                        score += 3
                except:
                    pass
            
            scored_books.append((score, book))
        
        # 按得分排序
        scored_books.sort(key=lambda x: x[0], reverse=True)
        
        if scored_books:
            return scored_books[0][1]
        return None
    
    def download(self, book: Dict, output_dir: Optional[Path] = None) -> Dict:
        """
        下载指定书籍
        
        Args:
            book: 书籍信息字典（必须包含 id 和 hash）
            output_dir: 下载目录，默认使用 resources/downloads/books/
        
        Returns:
            Dict: {"success": True/False, "filepath": "...", "filename": "...", "error": "..."}
        """
        if not self.is_logged_in():
            return {"success": False, "error": "未登录"}
        
        tokens = self.get_saved_tokens()
        Z = Zlibrary(
            remix_userid=tokens['remix_userid'],
            remix_userkey=tokens['remix_userkey']
        )
        
        download_dir = output_dir or self.downloads_dir
        
        try:
            book_id = book.get('id')
            book_hash = book.get('hash')
            
            if not book_id or not book_hash:
                # 尝试从 href 提取
                href = book.get('href', '')
                if href:
                    parts = href.split('/')
                    if len(parts) >= 3:
                        book_hash = parts[2]
                        # ID 可能是第一个数字部分
                        for part in parts:
                            if part.isdigit():
                                book_id = part
                                break
            
            if not book_id or not book_hash:
                return {"success": False, "error": "缺少书籍ID或Hash"}
            
            print(f"📥 正在下载: {book.get('name', 'Unknown')} (ID: {book_id}, Hash: {book_hash})...")
            
            book_info = {'id': book_id, 'hash': book_hash}
            result = Z.downloadBook(book_info)
            
            if result:
                filename, content = result
                filepath = download_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                file_size = filepath.stat().st_size / 1024
                
                return {
                    "success": True,
                    "filepath": str(filepath),
                    "filename": filename,
                    "size_kb": round(file_size, 2)
                }
            else:
                return {"success": False, "error": "下载失败，API返回空结果"}
                
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "traceback": traceback.format_exc()}


def main():
    """命令行入口 - AI调用示例"""
    api = ZLibraryAPI()
    
    if len(sys.argv) < 2:
        print("Z-Library AI API")
        print("")
        print("用法:")
        print("  1. 搜索书籍:")
        print('     python zlib_api.py search "认知觉醒"')
        print("")
        print("  2. 搜索并自动选择最佳书籍:")
        print('     python zlib_api.py auto "认知觉醒" --format pdf')
        print("")
        print("  3. 搜索并包含评论:")
        print('     python zlib_api.py auto "认知觉醒" --format pdf --with-reviews')
        print("")
        print("  4. 获取书籍评论:")
        print("     python zlib_api.py reviews <book_id> [max_reviews]")
        print("     python zlib_api.py reviews 11005990 5")
        print("")
        print("  5. 下载指定书籍（JSON格式）:")
        print('     python zlib_api.py download \'{"id": "123", "hash": "abc", "name": "书名"}\'')
        print("")
        print("  6. 检查登录状态:")
        print("     python zlib_api.py status")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "status":
        if api.is_logged_in():
            tokens = api.get_saved_tokens()
            print("✅ 已登录")
            print(f"   User ID: {tokens.get('remix_userid')}")
        else:
            print("❌ 未登录")
            print("   请运行: python scripts/login.py")
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("❌ 请提供搜索关键词")
            sys.exit(1)
        
        query = sys.argv[2]
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        
        results = api.search(query, limit)
        
        if isinstance(results, dict) and "error" in results:
            print(f"❌ 搜索失败: {results['message']}")
            sys.exit(1)
        
        # 输出JSON格式供AI解析
        print(json.dumps(results, ensure_ascii=False, indent=2))
    
    elif command == "auto":
        if len(sys.argv) < 3:
            print("❌ 请提供搜索关键词")
            sys.exit(1)
        
        query = sys.argv[2]
        prefer_format = "pdf"
        with_reviews = "--with-reviews" in sys.argv
        
        # 解析参数
        for i, arg in enumerate(sys.argv):
            if arg == "--format" and i + 1 < len(sys.argv):
                prefer_format = sys.argv[i + 1]
        
        print(f"🔍 搜索: {query}")
        print(f"🎯 优先格式: {prefer_format}")
        if with_reviews:
            print(f"💬 包含评论")
        print("")
        
        results = api.search(query, 10)
        
        if isinstance(results, dict) and "error" in results:
            print(f"❌ 搜索失败: {results['message']}")
            sys.exit(1)
        
        best = api.select_best_book(results, prefer_format)
        
        if not best:
            print("❌ 未找到合适的书籍")
            sys.exit(1)
        
        print("✅ 自动选择最佳匹配:")
        print(f"   书名: {best['name']}")
        print(f"   作者: {best['author']}")
        print(f"   格式: {best['extension']}")
        print(f"   年份: {best['year']}")
        print("")
        
        # 获取评论
        if with_reviews:
            book_id = best.get('id')
            if book_id:
                print("💬 获取评论...")
                reviews = api.get_book_reviews(str(book_id), 5)
                if reviews.get('success') and reviews.get('total_reviews', 0) > 0:
                    print(f"   找到 {reviews['total_reviews']} 条评论:")
                    for i, r in enumerate(reviews['reviews'][:3], 1):
                        print(f"      [{i}] {r['user']}: {r['text'][:50]}...")
                else:
                    print("   暂无评论")
                print("")
        
        # 执行下载
        download_result = api.download(best)
        
        if download_result['success']:
            print("✅ 下载成功!")
            print(f"   文件: {download_result['filename']}")
            print(f"   路径: {download_result['filepath']}")
            print(f"   大小: {download_result['size_kb']} KB")
        else:
            print(f"❌ 下载失败: {download_result['error']}")
            sys.exit(1)
    
    elif command == "reviews":
        if len(sys.argv) < 3:
            print("❌ 请提供书籍ID")
            sys.exit(1)
        
        book_id = sys.argv[2]
        max_reviews = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        
        reviews = api.get_book_reviews(book_id, max_reviews)
        print(json.dumps(reviews, ensure_ascii=False, indent=2))
    
    elif command == "download":
        if len(sys.argv) < 3:
            print("❌ 请提供书籍信息JSON")
            sys.exit(1)
        
        book_json = sys.argv[2]
        try:
            book = json.loads(book_json)
            result = api.download(book)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            sys.exit(1)
    
    else:
        print(f"❌ 未知命令: {command}")
        print("可用命令: status, search, auto, download")
        sys.exit(1)


if __name__ == "__main__":
    main()
