"""Pixabay 图库提供商"""
from typing import List, Optional
from urllib.parse import quote_plus
from .base import BaseProvider, MediaItem


class PixabayProvider(BaseProvider):
    """Pixabay API 提供商"""
    
    name = "pixabay"
    supports_video = True
    requires_attribution = False
    
    BASE_URL = "https://pixabay.com/api/"
    VIDEO_URL = "https://pixabay.com/api/videos/"
    
    def search_images(self, query: str, count: int = 10,
                      orientation: Optional[str] = None,
                      image_type: str = "photo",
                      colors: Optional[str] = None,
                      page: int = 1) -> List[MediaItem]:
        """搜索图片
        
        Args:
            orientation: horizontal, vertical
            image_type: photo, illustration, vector, all
            colors: comma separated colors (grayscale, transparent, red, orange, yellow, green, turquoise, blue, lilac, pink, white, gray, black, brown)
        """
        params = {
            "key": self.api_key,
            "q": quote_plus(query),
            "per_page": min(count, 200),
            "page": page,
            "image_type": image_type,
            "safesearch": "true",
        }
        
        if orientation:
            params["orientation"] = orientation
        if colors:
            params["colors"] = colors
        
        data = self._get(self.BASE_URL, params=params)
        if not data:
            return []
        
        results = []
        for hit in data.get("hits", []):
            results.append(MediaItem(
                id=str(hit.get("id")),
                provider=self.name,
                type="image",
                url=hit.get("largeImageURL", hit.get("webformatURL", "")),
                preview_url=hit.get("previewURL", ""),
                title=hit.get("tags"),
                alt=None,
                author=hit.get("user"),
                author_url=f"https://pixabay.com/users/{hit.get('user')}-{hit.get('user_id')}/",
                width=hit.get("imageWidth"),
                height=hit.get("imageHeight"),
                source_url=hit.get("pageURL"),
                raw_data=hit
            ))
        
        return results
    
    def search_videos(self, query: str, count: int = 10,
                      orientation: Optional[str] = None,
                      page: int = 1) -> List[MediaItem]:
        """搜索视频"""
        params = {
            "key": self.api_key,
            "q": quote_plus(query),
            "per_page": min(count, 200),
            "page": page,
        }
        
        if orientation:
            params["orientation"] = orientation
        
        data = self._get(self.VIDEO_URL, params=params)
        if not data:
            return []
        
        results = []
        for hit in data.get("hits", []):
            # 获取最佳质量视频
            videos = hit.get("videos", {})
            # 优先选择 large > medium > small > tiny
            for quality in ["large", "medium", "small", "tiny"]:
                if quality in videos:
                    video_data = videos[quality]
                    results.append(MediaItem(
                        id=str(hit.get("id")),
                        provider=self.name,
                        type="video",
                        url=video_data.get("url", ""),
                        preview_url=hit.get("picture_id", ""),
                        title=hit.get("tags"),
                        alt=None,
                        author=hit.get("user"),
                        author_url=f"https://pixabay.com/users/{hit.get('user')}-{hit.get('user_id')}/",
                        width=video_data.get("width"),
                        height=video_data.get("height"),
                        duration=hit.get("duration"),
                        source_url=hit.get("pageURL"),
                        raw_data=hit
                    ))
                    break
        
        return results
