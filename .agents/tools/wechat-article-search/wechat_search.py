#!/usr/bin/env python3
"""
微信公众号文章搜索工具
用于搜索公众号文章并提取配图

工作流程：
1. 驱动浏览器登录微信公众号平台（mp.weixin.qq.com）
2. 获取 Cookie 和 Token
3. 搜索公众号文章
4. 提取文章中的图片到暂存区
"""
import os
import sys
import json
import time
import re
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass
from urllib.parse import quote

# 配置
USER_DATA_DIR = Path(__file__).parent.parent / "browser_user_data"
COOKIES_FILE = Path(__file__).parent / "cookies.json"
BASE_URL = "https://mp.weixin.qq.com"


@dataclass
class Article:
    """文章数据结构"""
    title: str
    url: str
    nickname: str  # 公众号名称
    author: str
    digest: str  # 摘要
    create_time: str
    cover_url: Optional[str] = None  # 封面图


class WechatArticleSearch:
    """微信公众号文章搜索器"""
    
    def __init__(self):
        self.token: Optional[str] = None
        self.cookies: Dict[str, str] = {}
        self.session = None
        self._load_cookies()
    
    def _load_cookies(self):
        """加载保存的 cookies"""
        if COOKIES_FILE.exists():
            try:
                with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cookies = data.get('cookies', {})
                    self.token = data.get('token')
                    print(f"✅ 已加载登录状态 (Token: {self.token[:10] if self.token else 'None'}...)")
            except Exception as e:
                print(f"⚠️ 加载 cookies 失败: {e}")
    
    def _save_cookies(self, cookies: dict, token: str):
        """保存 cookies"""
        data = {
            'cookies': cookies,
            'token': token,
            'saved_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 登录状态已保存")
    
    def login(self, headless: bool = False) -> bool:
        """
        驱动浏览器登录
        
        Args:
            headless: 是否无头模式（调试用）
        
        Returns:
            是否登录成功
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("❌ 需要安装 playwright: pip install playwright")
            print("   然后运行: playwright install chromium")
            return False
        
        print("🌐 启动浏览器...")
        
        with sync_playwright() as p:
            # 使用已存在的 user_data_dir
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(USER_DATA_DIR),
                headless=headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            page = context.new_page()
            
            # 访问公众号平台
            print("🌐 访问微信公众号平台...")
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            
            # 检查是否已经登录
            if "/cgi-bin/home" in page.url or "/cgi-bin/appmsg" in page.url:
                print("✅ 检测到已登录")
            else:
                print("⏳ 请手动扫码登录...")
                print(f"   页面: {page.url}")
                
                # 等待登录完成
                try:
                    page.wait_for_url("**/cgi-bin/home**", timeout=120000)
                    print("✅ 登录成功")
                except:
                    print("❌ 登录超时")
                    context.close()
                    return False
            
            # 提取 token
            current_url = page.url
            token_match = re.search(r'token=(\d+)', current_url)
            if token_match:
                self.token = token_match.group(1)
                print(f"✅ 获取 Token: {self.token}")
            else:
                print("⚠️ 无法从 URL 提取 Token，尝试从页面获取...")
                # 尝试从页面脚本获取
                try:
                    self.token = page.evaluate("() => window.wxData && window.wxData.token")
                    if self.token:
                        print(f"✅ 从页面获取 Token: {self.token}")
                except:
                    pass
            
            if not self.token:
                print("❌ 无法获取 Token")
                context.close()
                return False
            
            # 获取 cookies
            cookies = context.cookies()
            self.cookies = {c['name']: c['value'] for c in cookies}
            
            # 保存
            self._save_cookies(self.cookies, self.token)
            
            context.close()
            return True
    
    def search_articles(self, query: str, count: int = 10) -> List[Article]:
        """
        搜索公众号文章
        
        Args:
            query: 搜索关键词
            count: 返回数量
        
        Returns:
            文章列表
        """
        if not self.token:
            print("❌ 未登录，请先调用 login()")
            return []
        
        import requests
        
        url = f"{BASE_URL}/cgi-bin/operate_appmsg"
        
        params = {
            'sub': 'check_appmsg_copyright_stat',
            'token': self.token,
            'lang': 'zh_CN',
            'f': 'json',
            'ajax': '1',
        }
        
        data = {
            'url': query,  # 搜索关键词
            'begin': '0',
            'count': str(count),
            'allow_reprint': '0',  # 0=全部
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': f'{BASE_URL}/cgi-bin/appmsg?t=media/appmsg_edit_v2&action=edit&isNew=1&type=10&token={self.token}&lang=zh_CN',
        }
        
        # 添加 cookies
        cookie_str = '; '.join([f"{k}={v}" for k, v in self.cookies.items()])
        headers['Cookie'] = cookie_str
        
        print(f"🔍 搜索文章: '{query}'")
        
        try:
            resp = requests.post(url, params=params, data=data, headers=headers, timeout=30)
            resp.raise_for_status()
            
            result = resp.json()
            
            if result.get('base_resp', {}).get('ret') != 0:
                err_msg = result.get('base_resp', {}).get('err_msg', '未知错误')
                print(f"❌ 搜索失败: {err_msg}")
                return []
            
            articles = []
            for item in result.get('list', []):
                articles.append(Article(
                    title=item.get('title', ''),
                    url=item.get('url', ''),
                    nickname=item.get('nickname', ''),
                    author=item.get('author', ''),
                    digest=item.get('digest', ''),
                    create_time=item.get('create_time', ''),
                    cover_url=item.get('cover_url')
                ))
            
            print(f"✅ 找到 {len(articles)} 篇文章")
            return articles
            
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            return []
    
    def extract_images_from_article(self, article_url: str) -> List[str]:
        """
        从文章URL提取图片
        
        Args:
            article_url: 文章链接
        
        Returns:
            图片URL列表
        """
        import requests
        from bs4 import BeautifulSoup
        
        print(f"🔍 分析文章图片: {article_url[:60]}...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        try:
            resp = requests.get(article_url, headers=headers, timeout=30)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            images = []
            
            # 提取正文图片
            for img in soup.find_all('img'):
                src = img.get('data-src') or img.get('src')
                if src and src.startswith('http'):
                    # 微信图片通常是 CDN 链接
                    if 'mmbiz.qpic.cn' in src or 'mmbiz_jpg' in src or 'mmbiz_png' in src:
                        images.append(src)
            
            # 去重
            images = list(dict.fromkeys(images))
            
            print(f"✅ 找到 {len(images)} 张图片")
            return images
            
        except Exception as e:
            print(f"❌ 获取文章失败: {e}")
            return []
    
    def download_images_to_staging(self, image_urls: List[str], prefix: str = "") -> List[Path]:
        """
        下载图片到暂存区
        
        Args:
            image_urls: 图片URL列表
            prefix: 文件名前缀
        
        Returns:
            下载的文件路径列表
        """
        import requests
        from datetime import datetime
        
        # 暂存区路径
        staging_dir = Path(__file__).parent.parent.parent.parent / "0_Inbox" / "image-staging"
        today_dir = staging_dir / datetime.now().strftime("%Y-%m-%d")
        today_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded = []
        
        for i, url in enumerate(image_urls, 1):
            try:
                print(f"  ⬇️  下载图片 {i}/{len(image_urls)}...")
                
                resp = requests.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }, timeout=30)
                resp.raise_for_status()
                
                # 确定扩展名
                content_type = resp.headers.get('content-type', '')
                if 'jpeg' in content_type or 'jpg' in content_type:
                    ext = '.jpg'
                elif 'png' in content_type:
                    ext = '.png'
                elif 'webp' in content_type:
                    ext = '.webp'
                else:
                    ext = '.jpg'
                
                # 文件名
                name_prefix = f"{prefix}_" if prefix else ""
                filename = f"{name_prefix}wx_{i:03d}{ext}"
                filepath = today_dir / filename
                
                with open(filepath, 'wb') as f:
                    f.write(resp.content)
                
                size_kb = len(resp.content) // 1024
                print(f"  ✅ 已保存: {filename} ({size_kb}KB)")
                downloaded.append(filepath)
                
            except Exception as e:
                print(f"  ❌ 下载失败: {e}")
        
        print(f"\n✅ 共下载 {len(downloaded)} 张图片到暂存区")
        print(f"📁 位置: {today_dir}")
        
        return downloaded


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def cmd_login(args):
    """登录"""
    searcher = WechatArticleSearch()
    success = searcher.login(headless=args.headless)
    return 0 if success else 1


def cmd_search(args):
    """搜索文章"""
    searcher = WechatArticleSearch()
    
    # 检查是否需要登录
    if not searcher.token:
        print("⚠️ 未登录，请先运行: python wechat_search.py login")
        return 1
    
    articles = searcher.search_articles(args.query, args.count)
    
    if not articles:
        print("❌ 未找到文章")
        return 1
    
    print(f"\n📋 搜索结果:\n")
    for i, art in enumerate(articles, 1):
        print(f"{i}. {art.title}")
        print(f"   公众号: {art.nickname}")
        print(f"   作者: {art.author}")
        print(f"   时间: {art.create_time}")
        print(f"   链接: {art.url}")
        if art.cover_url:
            print(f"   封面: {art.cover_url}")
        print()
    
    # 保存结果到文件
    if args.output:
        data = [{
            'title': a.title,
            'url': a.url,
            'nickname': a.nickname,
            'author': a.author,
            'digest': a.digest,
            'cover_url': a.cover_url
        } for a in articles]
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 结果已保存: {args.output}")
    
    return 0


def cmd_extract(args):
    """提取文章图片"""
    searcher = WechatArticleSearch()
    
    # 从URL提取
    images = searcher.extract_images_from_article(args.url)
    
    if not images:
        print("❌ 未找到图片")
        return 1
    
    print(f"\n📷 找到 {len(images)} 张图片:\n")
    for i, img in enumerate(images[:20], 1):  # 最多显示20张
        print(f"{i}. {img[:80]}...")
    
    if len(images) > 20:
        print(f"... 还有 {len(images) - 20} 张")
    
    # 下载
    if args.download:
        prefix = args.prefix or ""
        searcher.download_images_to_staging(images, prefix)
    
    return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="微信公众号文章搜索工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 登录（会弹出浏览器）
  python wechat_search.py login
  
  # 搜索文章
  python wechat_search.py search "人工智能"
  
  # 搜索并保存结果
  python wechat_search.py search "Claude Code" -o articles.json
  
  # 提取文章图片
  python wechat_search.py extract "https://mp.weixin.qq.com/s/xxx" --download
  
  # 搜索文章并提取配图
  python wechat_search.py search "AI绘画" --extract-images
        """
    )
    
    sub = parser.add_subparsers(dest='cmd', help='命令')
    
    # login
    login_cmd = sub.add_parser('login', help='浏览器登录')
    login_cmd.add_argument('--headless', action='store_true', help='无头模式')
    login_cmd.set_defaults(func=cmd_login)
    
    # search
    search_cmd = sub.add_parser('search', help='搜索文章')
    search_cmd.add_argument('query', help='搜索关键词')
    search_cmd.add_argument('-n', '--count', type=int, default=10, help='返回数量')
    search_cmd.add_argument('-o', '--output', help='保存结果到文件')
    search_cmd.add_argument('--extract-images', action='store_true', help='自动提取配图')
    search_cmd.set_defaults(func=cmd_search)
    
    # extract
    extract_cmd = sub.add_parser('extract', help='提取文章图片')
    extract_cmd.add_argument('url', help='文章URL')
    extract_cmd.add_argument('--download', '-d', action='store_true', help='下载到暂存区')
    extract_cmd.add_argument('--prefix', '-p', help='文件名前缀')
    extract_cmd.set_defaults(func=cmd_extract)
    
    args = parser.parse_args()
    
    if not args.cmd:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
