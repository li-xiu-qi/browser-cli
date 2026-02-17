#!/usr/bin/env python3
"""
图片收集器 - 从网页/文章提取图片
配合 Cliper 使用，保存有价值的配图
"""
import os
import sys
import re
import shutil
import requests
from pathlib import Path
from urllib.parse import urlparse, urljoin
from typing import List, Optional, Tuple

# 暂存区路径（Inbox）
STAGING_DIR = Path(__file__).parent.parent.parent.parent / "0_Inbox" / "image-staging"
STAGING_DIR.mkdir(parents=True, exist_ok=True)

# 正式库路径
LIBRARY_DIR = Path(__file__).parent.parent.parent.parent / "resources" / "image-library"
LIBRARY_DIR.mkdir(exist_ok=True)


class ImageCollector:
    """图片收集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.downloaded = []
    
    def extract_from_markdown(self, md_file: Path) -> List[Tuple[str, str]]:
        """
        从 Markdown 文件提取图片 URL
        
        Returns:
            [(图片URL, 上下文描述), ...]
        """
        if not md_file.exists():
            print(f"❌ 文件不存在: {md_file}")
            return []
        
        content = md_file.read_text(encoding='utf-8')
        results = []
        
        # 匹配 Markdown 图片: ![alt](url)
        md_pattern = r'!\[([^\]]*)\]\((https?://[^)]+)\)'
        for alt, url in re.findall(md_pattern, content):
            results.append((url, alt or "配图"))
        
        # 匹配 HTML img 标签
        html_pattern = r'<img[^>]+src=["\'](https?://[^"\']+)["\'][^>]*>'
        for url in re.findall(html_pattern, content):
            # 尝试提取 alt
            alt_match = re.search(r'alt=["\']([^"\']*)["\']', content[content.find(url)-100:content.find(url)+200])
            alt = alt_match.group(1) if alt_match else "配图"
            results.append((url, alt))
        
        # 去重
        seen = set()
        unique = []
        for url, alt in results:
            if url not in seen:
                seen.add(url)
                unique.append((url, alt))
        
        return unique
    
    def extract_from_url(self, url: str) -> List[Tuple[str, str]]:
        """
        从网页 URL 提取图片
        """
        print(f"🔍 分析网页: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text
            
            results = []
            
            # 提取所有 img 标签
            img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
            for img_src in re.findall(img_pattern, html):
                # 处理相对路径
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif img_src.startswith('/'):
                    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    img_src = base + img_src
                elif not img_src.startswith('http'):
                    img_src = urljoin(url, img_src)
                
                # 只保留常见图片格式
                if any(img_src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                    results.append((img_src, "网页图片"))
            
            # 提取背景图片
            bg_pattern = r'background(?:-image)?\s*:\s*url\(["\']?([^"\')]+)'
            for bg_src in re.findall(bg_pattern, html):
                if bg_src.startswith('//'):
                    bg_src = 'https:' + bg_src
                elif bg_src.startswith('/'):
                    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    bg_src = base + bg_src
                
                if any(bg_src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    results.append((bg_src, "背景图"))
            
            # 去重
            seen = set()
            unique = []
            for img_url, desc in results:
                if img_url not in seen:
                    seen.add(img_url)
                    unique.append((img_url, desc))
            
            print(f"  找到 {len(unique)} 张图片")
            return unique
            
        except Exception as e:
            print(f"❌ 获取网页失败: {e}")
            return []
    
    def download_image(self, url: str, alt: str = "", suggested_name: str = None, 
                       to_staging: bool = True) -> Optional[Path]:
        """
        下载单张图片
        
        Args:
            url: 图片URL
            alt: 图片描述（用于生成文件名）
            suggested_name: 建议的文件名
            to_staging: 是否保存到暂存区（True=暂存区，False=正式库）
        
        Returns:
            下载后的本地路径
        """
        try:
            print(f"  ⬇️  下载: {url[:60]}...")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 确定文件扩展名
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'webp' in content_type:
                ext = '.webp'
            elif 'gif' in content_type:
                ext = '.gif'
            else:
                # 从 URL 提取
                ext = Path(urlparse(url).path).suffix
                if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                    ext = '.jpg'
            
            # 确定保存目录
            if to_staging:
                # 暂存区按日期组织
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                save_dir = STAGING_DIR / today
                save_dir.mkdir(exist_ok=True)
                # 暂存区使用简单编号命名
                existing = list(save_dir.glob(f"*{ext}"))
                filename = f"img_{len(existing)+1:03d}{ext}"
            else:
                save_dir = LIBRARY_DIR
                # 生成有意义的文件名
                if suggested_name:
                    filename = suggested_name + ext
                elif alt and len(alt) > 3:
                    safe_alt = self._safe_filename(alt)[:30]
                    filename = f"{safe_alt}{ext}"
                else:
                    url_name = Path(urlparse(url).path).stem
                    if url_name and len(url_name) > 3:
                        filename = f"{self._safe_filename(url_name)}{ext}"
                    else:
                        import hashlib
                        hash_id = hashlib.md5(url.encode()).hexdigest()[:8]
                        filename = f"image_{hash_id}{ext}"
                
                # 检查是否已存在
                target = save_dir / filename
                counter = 1
                original_target = target
                while target.exists():
                    stem = original_target.stem
                    filename = f"{stem}_{counter}{ext}"
                    target = save_dir / filename
                    counter += 1
            
            target = save_dir / filename
            
            # 保存
            with open(target, 'wb') as f:
                f.write(response.content)
            
            size_kb = len(response.content) // 1024
            location = "暂存区" if to_staging else "图片库"
            print(f"  ✅ 已保存到{location}: {target.name} ({size_kb}KB)")
            
            self.downloaded.append(target)
            return target
            
        except Exception as e:
            print(f"  ❌ 下载失败: {e}")
            return None
    
    def collect_from_article(self, source: str, selected_indices: List[int] = None):
        """
        从文章收集图片
        
        Args:
            source: Markdown 文件路径或网页 URL
            selected_indices: 指定要下载的图片序号（None 则列出供选择）
        """
        # 判断来源类型
        if source.startswith('http'):
            images = self.extract_from_url(source)
        else:
            md_file = Path(source)
            if not md_file.exists():
                # 尝试相对路径
                md_file = Path.cwd() / source
            images = self.extract_from_markdown(md_file)
        
        if not images:
            print("❌ 未找到图片")
            return []
        
        # 显示列表
        print(f"\n📋 找到 {len(images)} 张图片:\n")
        for i, (url, alt) in enumerate(images, 1):
            print(f"  {i}. {alt[:40] if alt else '无描述'}")
            print(f"     {url[:60]}...")
        
        # 下载选中的
        if selected_indices:
            to_download = [(images[i-1][0], images[i-1][1]) for i in selected_indices if 1 <= i <= len(images)]
        else:
            # 交互式选择
            print("\n输入要下载的序号（逗号分隔，如: 1,3,5），或 'all' 下载全部:")
            choice = input("> ").strip()
            
            if choice.lower() == 'all':
                to_download = images
            else:
                try:
                    indices = [int(x.strip()) for x in choice.split(',')]
                    to_download = [(images[i-1][0], images[i-1][1]) for i in indices if 1 <= i <= len(images)]
                except:
                    print("❌ 输入无效")
                    return []
        
        print(f"\n⬇️  开始下载 {len(to_download)} 张图片...\n")
        
        for url, alt in to_download:
            self.download_image(url, alt)
        
        print(f"\n✅ 完成: 下载了 {len(self.downloaded)} 张图片")
        print(f"📁 保存位置: {LIBRARY_DIR}")
        
        return self.downloaded
    
    def _safe_filename(self, name: str) -> str:
        """生成安全的文件名"""
        import re
        # 移除危险字符
        safe = re.sub(r'[^\w\s-]', '', name)
        # 替换空格为下划线
        safe = re.sub(r'[-\s]+', '_', safe)
        return safe.strip('_')


def list_staging():
    """列出暂存区的所有图片"""
    if not STAGING_DIR.exists():
        print("暂存区为空")
        return []
    
    # 获取所有日期目录
    date_dirs = [d for d in STAGING_DIR.iterdir() if d.is_dir()]
    date_dirs.sort()
    
    all_images = []
    for date_dir in date_dirs:
        images = list(date_dir.glob("*.jpg")) + list(date_dir.glob("*.png")) + list(date_dir.glob("*.webp"))
        if images:
            print(f"\n📁 {date_dir.name} ({len(images)} 张)")
            for img in sorted(images):
                size_kb = img.stat().st_size // 1024
                print(f"  • {img.name} ({size_kb}KB)")
            all_images.extend(images)
    
    print(f"\n📊 暂存区总计: {len(all_images)} 张图片")
    return all_images


def import_to_library(staging_path: Path, new_name: str = None) -> Optional[Path]:
    """
    将暂存区的图片导入正式库
    
    Args:
        staging_path: 暂存区图片路径
        new_name: 新文件名（不含扩展名）
    
    Returns:
        正式库路径
    """
    import shutil
    
    if not staging_path.exists():
        print(f"❌ 文件不存在: {staging_path}")
        return None
    
    # 确定新文件名
    if new_name:
        safe_name = re.sub(r'[^\w\s-]', '', new_name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name).strip('_')
        filename = f"{safe_name}{staging_path.suffix}"
    else:
        filename = staging_path.name
    
    # 检查是否已存在
    target = LIBRARY_DIR / filename
    counter = 1
    original_target = target
    while target.exists():
        stem = original_target.stem
        filename = f"{stem}_{counter}{staging_path.suffix}"
        target = LIBRARY_DIR / filename
        counter += 1
    
    try:
        shutil.move(str(staging_path), str(target))
        print(f"✅ 已入库: {target.name}")
        print(f"   原位置: {staging_path}")
        print(f"   新位置: {target}")
        return target
    except Exception as e:
        print(f"❌ 移动失败: {e}")
        return None


def clean_staging(days: int = 7):
    """
    清理暂存区的旧文件
    
    Args:
        days: 删除多少天前的文件
    """
    import time
    from datetime import datetime, timedelta
    
    if not STAGING_DIR.exists():
        return
    
    cutoff = time.time() - (days * 86400)
    deleted = 0
    
    for date_dir in STAGING_DIR.iterdir():
        if not date_dir.is_dir():
            continue
        
        # 检查目录日期
        try:
            dir_date = datetime.strptime(date_dir.name, "%Y-%m-%d")
            if (datetime.now() - dir_date).days > days:
                # 删除整个日期目录
                import shutil
                shutil.rmtree(date_dir)
                deleted += 1
                print(f"🗑️  清理旧目录: {date_dir.name}")
        except:
            pass
    
    if deleted == 0:
        print("暂存区无需清理")
    else:
        print(f"✅ 清理完成，删除了 {deleted} 个旧目录")


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="图片收集器 - 从文章提取配图",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从 Markdown 文件提取（到暂存区）
  python collector.py article.md
  
  # 从网页提取
  python collector.py https://example.com/article
  
  # 指定下载序号
  python collector.py article.md --indices 1,3,5
  
  # 查看暂存区
  python collector.py --staging
  
  # 入库（从暂存区移到正式库）
  python collector.py --import "0_Inbox/image-staging/2026-02-16/img_001.jpg" --name "claude-workflow"
        """
    )
    
    parser.add_argument("source", nargs="?", help="Markdown 文件或网页 URL")
    parser.add_argument("--indices", "-i", help="要下载的图片序号，逗号分隔")
    parser.add_argument("--all", "-a", action="store_true", help="下载全部图片")
    parser.add_argument("--staging", "-s", action="store_true", help="查看暂存区")
    parser.add_argument("--import", dest="import_path", help="将暂存区图片入库")
    parser.add_argument("--name", "-n", help="入库后的文件名（不含扩展名）")
    parser.add_argument("--clean", type=int, metavar="DAYS", help="清理多少天前的暂存文件")
    
    args = parser.parse_args()
    
    # 查看暂存区
    if args.staging:
        list_staging()
        return 0
    
    # 入库
    if args.import_path:
        path = Path(args.import_path)
        import_to_library(path, args.name)
        return 0
    
    # 清理
    if args.clean:
        clean_staging(args.clean)
        return 0
    
    # 提取图片
    if not args.source:
        parser.print_help()
        return 1
    
    collector = ImageCollector()
    
    if args.all:
        selected = list(range(1, 1000))
    elif args.indices:
        try:
            selected = [int(x.strip()) for x in args.indices.split(',')]
        except:
            print("❌ 序号格式错误")
            return 1
    else:
        selected = None
    
    collector.collect_from_article(args.source, selected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
