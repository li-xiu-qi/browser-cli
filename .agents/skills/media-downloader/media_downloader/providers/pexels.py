"""Pexels 图库提供商"""
from typing import List, Optional
from urllib.parse import quote_plus
from .base import BaseProvider, MediaItem


class PexelsProvider(BaseProvider):
    """Pexels API 提供商"""
    
    name = "pexels"
    supports_video = True
    requires_attribution = False
    
    BASE_URL = "https://api.pexels.com/v1"
    VIDEO_URL = "https://api.pexels.com/videos"
    
    def _init_session(self):
        super()._init_session()
        if self.session:
            self.session.headers.update({
                "Authorization": self.api_key
            })
    
    def search_images(self, query: str, count: int = 10, 
                      orientation: Optional[str] = None,
                      size: Optional[str] = None,
                      color: Optional[str] = None,
                      page: int = 1) -> List[MediaItem]:
        """搜索图片
        
        Args:
            orientation: landscape, portrait, square
            size: large, medium, small
            color: red, orange, yellow, green, turquoise, blue, violet, pink, brown, black, gray, white
        """
        url = f"{self.BASE_URL}/search"
        params = {
            "query": query,
            "per_page": min(count, 80),
            "page": page,
        }
        
        if orientation:
            params["orientation"] = orientation
        if size:
            params["size"] = size
        if color:
            params["color"] = color
        
        data = self._get(url, params=params)
        if not data:
            return []
        
        results = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            results.append(MediaItem(
                id=str(photo.get("id")),
                provider=self.name,
                type="image",
                url=src.get("large", src.get("medium", "")),
                preview_url=src.get("small", ""),
                title=None,
                alt=photo.get("alt"),
                author=photo.get("photographer"),
                author_url=photo.get("photographer_url"),
                width=photo.get("width"),
                height=photo.get("height"),
                source_url=photo.get("url"),
                raw_data=photo
            ))
        
        return results
    
    def search_videos(self, query: str, count: int = 10,
                      orientation: Optional[str] = None,
                      min_duration: Optional[int] = None,
                      max_duration: Optional[int] = None,
                      page: int = 1) -> List[MediaItem]:
        """搜索视频"""
        url = f"{self.VIDEO_URL}/search"
        params = {
            "query": query,
            "per_page": min(count, 80),
            "page": page,
        }
        
        if orientation:
            params["orientation"] = orientation
        if min_duration:
            params["min_duration"] = min_duration
        if max_duration:
            params["max_duration"] = max_duration
        
        data = self._get(url, params=params)
        if not data:
            return []
        
        results = []
        for video in data.get("videos", []):
            # 获取最佳质量视频文件
            files = video.get("video_files", [])
            best_file = max(files, key=lambda x: x.get("width", 0)) if files else None
            
            # 获取预览图
            pictures = video.get("video_pictures", [])
            preview = pictures[0] if pictures else None
            
            if best_file:
                results.append(MediaItem(
                    id=str(video.get("id")),
                    provider=self.name,
                    type="video",
                    url=best_file.get("link", ""),
                    preview_url=preview.get("picture", "") if preview else "",
                    title=None,
                    alt=video.get("alt"),
                    author=video.get("user", {}).get("name"),
                    author_url=video.get("user", {}).get("url"),
                    width=best_file.get("width"),
                    height=best_file.get("height"),
                    duration=video.get("duration"),
                    source_url=video.get("url"),
                    raw_data=video
                ))
        
        return results
    
    def get_curated(self, count: int = 10, page: int = 1) -> List[MediaItem]:
        """获取精选图片"""
        url = f"{self.BASE_URL}/curated"
        params = {"per_page": min(count, 80), "page": page}
        
        data = self._get(url, params=params)
        if not data:
            return []
        
        results = []
        for photo in data.get("photos", []):
            src = photo.get("src", {})
            results.append(MediaItem(
                id=str(photo.get("id")),
                provider=self.name,
                type="image",
                url=src.get("large", ""),
                preview_url=src.get("small", ""),
                alt=photo.get("alt"),
                author=photo.get("photographer"),
                author_url=photo.get("photographer_url"),
                width=photo.get("width"),
                height=photo.get("height"),
                source_url=photo.get("url"),
                raw_data=photo
            ))
        
        return results
