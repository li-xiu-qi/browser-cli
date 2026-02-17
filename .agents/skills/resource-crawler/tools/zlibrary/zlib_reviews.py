#!/usr/bin/env python3
"""
Z-Library 评论获取工具
使用官方 API 获取书籍评论
"""

import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Optional


class ZLibraryReviews:
    """Z-Library 评论获取器"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
    def get_saved_tokens(self) -> Optional[Dict]:
        """获取保存的登录 token"""
        token_file = self.config_dir / "zl_tokens.json"
        if token_file.exists():
            with open(token_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def get_reviews(self, book_id: str, max_reviews: int = 10) -> Dict:
        """
        获取书籍评论
        
        Args:
            book_id: 书籍 ID
            max_reviews: 最大评论数量
            
        Returns:
            {
                "success": bool,
                "book_id": "...",
                "total_reviews": int,
                "reviews": [
                    {
                        "id": int,
                        "user": "用户名",
                        "text": "评论内容",
                        "date": "日期",
                        "date_relative": "相对时间",
                        "likes": int
                    }
                ]
            }
        """
        tokens = self.get_saved_tokens()
        if not tokens:
            return {"success": False, "error": "未登录，请先运行登录脚本"}
        
        # API endpoint
        url = f'https://zh.z-library.sk/papi/comments/book/{book_id}/0'
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': f'https://zh.z-library.sk/book/{book_id}/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        cookies = {
            'remix_userid': str(tokens['remix_userid']),
            'remix_userkey': tokens['remix_userkey'],
            'siteLanguage': 'zh'
        }
        
        try:
            response = requests.get(url, headers=headers, cookies=cookies, timeout=30)
            data = response.json()
            
            if data.get('success') != 1:
                return {
                    "success": False,
                    "error": "API返回失败",
                    "book_id": book_id
                }
            
            comments = data.get('comments', [])
            reactions_info = data.get('reactionsInfo', {}).get('reactions', [])
            
            # 构建点赞数映射
            likes_map = {}
            for reaction in reactions_info:
                if reaction.get('status') == 1:
                    likes_map[reaction['item_id']] = reaction.get('count', 0)
            
            # 格式化评论
            reviews = []
            for comment in comments[:max_reviews]:
                review = {
                    "id": comment.get('id'),
                    "user": comment.get('user', {}).get('name', 'Anonymous'),
                    "user_hash": comment.get('user', {}).get('hash'),
                    "text": comment.get('text', ''),
                    "date": comment.get('date'),
                    "date_relative": comment.get('dateRelative'),
                    "likes": likes_map.get(comment.get('id'), 0)
                }
                reviews.append(review)
            
            return {
                "success": True,
                "book_id": book_id,
                "total_reviews": len(reviews),
                "comments_disabled": data.get('commentsDisabled', False),
                "reviews": reviews
            }
            
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"网络请求失败: {str(e)}",
                "book_id": book_id
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"JSON解析失败: {str(e)}",
                "book_id": book_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"未知错误: {str(e)}",
                "book_id": book_id
            }


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("Z-Library 评论获取工具")
        print("")
        print("用法:")
        print("  python zlib_reviews.py <book_id> [max_reviews]")
        print("")
        print("示例:")
        print("  python zlib_reviews.py 11005990")
        print("  python zlib_reviews.py 11005990 5")
        print("")
        print("你也可以配合 zlib_api.py 使用:")
        print("  1. 搜索书籍: python zlib_api.py search '书名'")
        print("  2. 获取评论: python zlib_reviews.py <book_id>")
        sys.exit(1)
    
    book_id = sys.argv[1]
    max_reviews = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"🔍 获取书籍 {book_id} 的评论...")
    print("")
    
    api = ZLibraryReviews()
    result = api.get_reviews(book_id, max_reviews)
    
    if not result.get('success'):
        print(f"❌ 获取失败: {result.get('error', '未知错误')}")
        sys.exit(1)
    
    print(f"💬 评论数: {result['total_reviews']}")
    if result.get('comments_disabled'):
        print("⚠️ 评论已禁用")
    print("")
    
    if result['reviews']:
        print("=" * 70)
        for i, review in enumerate(result['reviews'], 1):
            print(f"\n[{i}] 👤 {review['user']}")
            print(f"    📅 {review['date_relative']} ({review['date']})")
            if review['likes'] > 0:
                print(f"    👍 {review['likes']} 赞")
            print(f"    💭 {review['text']}")
        print("\n" + "=" * 70)
    else:
        print("ℹ️ 没有找到评论")
    
    # 输出JSON格式
    print("\n📄 完整数据 (JSON):")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
