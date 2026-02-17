"""下载管理模块"""
import os
import shutil
from pathlib import Path
from typing import Optional, Callable
from urllib.parse import urlparse
from ..providers.base import MediaItem
from ..utils.config_loader import Config


class DownloadManager:
    """下载管理器"""
    
    def __init__(self, config: Optional[Config] = None, 
                 output_dir: Optional[str] = None):
        self.config = config or Config()
        self.output_dir = Path(output_dir) if output_dir else self.config.downloads_dir
        self.output_dir.mkdir(exist_ok=True)
        
        # 确保 requests 可用
        try:
            import requests
            self.session = requests.Session()
            self.session.timeout = (10, 60)
        except ImportError:
            self.session = None
    
    def download(self, item: MediaItem, 
                 filename: Optional[str] = None,
                 progress_callback: Optional[Callable[[int, int], None]] = None) -> Optional[Path]:
        """下载单个媒体文件
        
        Args:
            item: MediaItem 对象
            filename: 自定义文件名，None 则自动生成
            progress_callback: 进度回调函数 (downloaded, total)
        
        Returns:
            下载后的文件路径，失败返回 None
        """
        if not self.session:
            print("错误: 需要安装 requests: pip install requests")
            return None
        
        if not item.url:
            print("错误: 无效的下载 URL")
            return None
        
        # 生成文件名
        if not filename:
            ext = self._get_extension(item.url, item.type)
            safe_name = self._safe_filename(item.alt or item.title or f"{item.provider}_{item.id}")
            filename = f"{safe_name}.{ext}"
        
        filepath = self.output_dir / filename
        
        # 检查文件是否已存在
        if filepath.exists():
            print(f"  文件已存在: {filepath.name}")
            return filepath
        
        # 下载
        try:
            print(f"  ⬇️  下载: {filename}")
            response = self.session.get(item.url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            
            print(f"  ✅ 完成: {filepath.name} ({self._format_size(downloaded)})")
            return filepath
            
        except Exception as e:
            print(f"  ❌ 下载失败: {e}")
            # 清理部分下载的文件
            if filepath.exists():
                filepath.unlink()
            return None
    
    def download_batch(self, items: list, 
                       prefix: str = "",
                       max_workers: int = 3) -> list:
        """批量下载
        
        Args:
            items: MediaItem 列表
            prefix: 文件名前缀
            max_workers: 并发下载数
        
        Returns:
            成功下载的文件路径列表
        """
        from concurrent.futures import ThreadPoolExecutor
        
        results = []
        
        def download_with_index(args):
            index, item = args
            filename = f"{prefix}_{index+1}_{item.provider}.{self._get_extension(item.url, item.type)}" if prefix else None
            return self.download(item, filename)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = executor.map(download_with_index, enumerate(items))
            results = [f for f in futures if f]
        
        return results
    
    def _get_extension(self, url: str, media_type: str) -> str:
        """从 URL 获取文件扩展名"""
        path = urlparse(url).path
        ext = Path(path).suffix.lstrip('.').lower()
        
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg']:
            return ext if ext != 'jpeg' else 'jpg'
        elif ext in ['mp4', 'mov', 'avi', 'webm', 'mkv']:
            return ext
        
        # 默认扩展名
        return 'jpg' if media_type == 'image' else 'mp4'
    
    def _safe_filename(self, name: str) -> str:
        """生成安全的文件名"""
        import re
        # 替换不安全字符
        safe = re.sub(r'[^\w\s-]', '', name)
        safe = re.sub(r'[-\s]+', '_', safe)
        return safe[:50]  # 限制长度
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
