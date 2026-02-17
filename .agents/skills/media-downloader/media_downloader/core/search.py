"""搜索聚合模块"""
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..providers import PROVIDERS
from ..providers.base import MediaItem
from ..utils.config_loader import Config


class SearchEngine:
    """搜索聚合引擎"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.providers: Dict[str, any] = {}
        self._init_providers()
    
    def _init_providers(self):
        """初始化所有可用的提供商"""
        if self.config.pexels_api_key:
            self.providers['pexels'] = PROVIDERS['pexels'](self.config.pexels_api_key)
        
        if self.config.unsplash_access_key:
            self.providers['unsplash'] = PROVIDERS['unsplash'](self.config.unsplash_access_key)
        
        if self.config.pixabay_api_key:
            self.providers['pixabay'] = PROVIDERS['pixabay'](self.config.pixabay_api_key)
    
    def search_images(self, query: str, count: int = 10, 
                      providers: Optional[List[str]] = None,
                      **kwargs) -> List[MediaItem]:
        """聚合搜索图片
        
        Args:
            query: 搜索关键词
            count: 每个提供商的结果数量
            providers: 指定提供商列表，None 表示全部
            **kwargs: 额外的搜索参数
        """
        target_providers = self._get_target_providers(providers)
        if not target_providers:
            print("警告: 没有可用的图片提供商，请先配置 API Key")
            return []
        
        results = []
        
        # 串行搜索（避免并发导致 API 限制）
        for name, provider in target_providers.items():
            try:
                items = provider.search_images(query, count, **kwargs)
                results.extend(items)
                print(f"  [{name}] 找到 {len(items)} 张图片")
            except Exception as e:
                print(f"  [{name}] 搜索失败: {e}")
        
        return results
    
    def search_videos(self, query: str, count: int = 10,
                      providers: Optional[List[str]] = None,
                      **kwargs) -> List[MediaItem]:
        """聚合搜索视频"""
        target_providers = self._get_target_providers(providers)
        if not target_providers:
            print("警告: 没有可用的视频提供商")
            return []
        
        results = []
        
        for name, provider in target_providers.items():
            if not provider.supports_video:
                continue
            
            try:
                items = provider.search_videos(query, count, **kwargs)
                results.extend(items)
                print(f"  [{name}] 找到 {len(items)} 个视频")
            except Exception as e:
                print(f"  [{name}] 搜索失败: {e}")
        
        return results
    
    def search_youtube(self, query: str, count: int = 5) -> List[Dict]:
        """搜索 YouTube 视频"""
        import shutil
        import subprocess
        
        if not shutil.which('yt-dlp'):
            print("警告: 未安装 yt-dlp，无法搜索 YouTube")
            return []
        
        try:
            cmd = [
                'yt-dlp',
                f'ytsearch{count}:{query}',
                '--dump-json',
                '--no-download',
                '--flat-playlist',
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                results = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            import json
                            data = json.loads(line)
                            results.append({
                                'id': data.get('id'),
                                'title': data.get('title'),
                                'url': f"https://www.youtube.com/watch?v={data.get('id')}",
                                'duration': data.get('duration'),
                                'channel': data.get('channel'),
                                'provider': 'youtube',
                            })
                        except json.JSONDecodeError:
                            pass
                return results
        except Exception as e:
            print(f"YouTube 搜索失败: {e}")
        
        return []
    
    def _get_target_providers(self, providers: Optional[List[str]]) -> Dict[str, any]:
        """获取目标提供商"""
        if providers is None:
            return self.providers
        
        return {name: self.providers[name] 
                for name in providers 
                if name in self.providers}
    
    def list_providers(self) -> Dict[str, bool]:
        """列出所有提供商及其可用状态"""
        return {
            'pexels': 'pexels' in self.providers,
            'unsplash': 'unsplash' in self.providers,
            'pixabay': 'pixabay' in self.providers,
        }
