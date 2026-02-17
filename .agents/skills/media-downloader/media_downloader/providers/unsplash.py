"""Unsplash 图库提供商"""
from typing import List, Optional
from urllib.parse import quote_plus
from .base import BaseProvider, MediaItem


class UnsplashProvider(BaseProvider):
    """Unsplash API 提供商"""
    
    name = "unsplash"
    supports_video = False
    requires_attribution = True
    
    BASE_URL = "https://api.unsplash.com"
    
    def _init_session(self):
        super()._init_session()
        if self.session:
            self.session.headers.update({
                "Authorization": f"Client-ID {self.api_key}"
            })
    
    def search_images(self, query: str, count: int = 10,
                      orientation: Optional[str] = None,
                      order_by: str = "relevant",
                      page: int = 1) -> List[MediaItem]:
        """搜索图片
        
        Args:
            orientation: landscape, portrait, squarish
            order_by: relevant, latest
        """
        url = f"{self.BASE_URL}/search/photos"
        params = {
            "query": query,
            "per_page": min(count, 30),
            "page": page,
            "order_by": order_by,
        }
        
        if orientation:
            params["orientation"] = orientation
        
        data = self._get(url, params=params)
        if not data:
            return []
        
        results = []
        for photo in data.get("results", []):
            urls = photo.get("urls", {})
            user = photo.get("user", {})
            
            results.append(MediaItem(
                id=photo.get("id"),
                provider=self.name,
                type="image",
                url=urls.get("regular", urls.get("small", "")),
                preview_url=urls.get("thumb", ""),
                title=photo.get("description"),
                alt=photo.get("alt_description"),
                author=user.get("name"),
                author_url=user.get("links", {}).get("html"),
                width=photo.get("width"),
                height=photo.get("height"),
                source_url=photo.get("links", {}).get("html"),
                raw_data=photo
            ))
        
        return results
    
    def get_random(self, query: Optional[str] = None, count: int = 1,
                   orientation: Optional[str] = None) -> List[MediaItem]:
        """获取随机图片"""
        url = f"{self.BASE_URL}/photos/random"
        params = {"count": min(count, 30)}
        
        if query:
            params["query"] = query
        if orientation:
            params["orientation"] = orientation
        
        data = self._get(url, params=params)
        if not data:
            return []
        
        # 处理单个结果或列表
        photos = data if isinstance(data, list) else [data]
        
        results = []
        for photo in photos:
            urls = photo.get("urls", {})
            user = photo.get("user", {})
            
            results.append(MediaItem(
                id=photo.get("id"),
                provider=self.name,
                type="image",
                url=urls.get("regular", ""),
                preview_url=urls.get("thumb", ""),
                title=photo.get("description"),
                alt=photo.get("alt_description"),
                author=user.get("name"),
                author_url=user.get("links", {}).get("html"),
                width=photo.get("width"),
                height=photo.get("height"),
                source_url=photo.get("links", {}).get("html"),
                raw_data=photo
            ))
        
        return results
    
    def get_attribution(self, item: MediaItem) -> str:
        """Unsplash 需要署名"""
        if item.author:
            return f'Photo by <a href="{item.author_url}?utm_source=media_downloader&utm_medium=referral">{item.author}</a> on <a href="https://unsplash.com/?utm_source=media_downloader&utm_medium=referral">Unsplash</a>'
        return ""
