"""图库提供商基类"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class MediaItem:
    """媒体项目数据类"""
    id: str
    provider: str
    type: str  # 'image' or 'video'
    url: str  # 下载 URL
    preview_url: str  # 预览 URL
    title: Optional[str] = None
    alt: Optional[str] = None
    author: Optional[str] = None
    author_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None  # 视频时长
    source_url: Optional[str] = None  # 原始页面 URL
    license: str = "Free for commercial use"
    raw_data: Optional[dict] = None  # 原始 API 响应


class BaseProvider(ABC):
    """图库提供商基类"""
    
    name: str = ""
    supports_video: bool = False
    requires_attribution: bool = False
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
        self._init_session()
    
    def _init_session(self):
        """初始化 HTTP 会话"""
        try:
            import requests
            self.session = requests.Session()
            self.session.timeout = (5, 15)  # (连接超时, 读取超时)
        except ImportError:
            self.session = None
    
    @abstractmethod
    def search_images(self, query: str, count: int = 10, **kwargs) -> List[MediaItem]:
        """搜索图片"""
        pass
    
    def search_videos(self, query: str, count: int = 10, **kwargs) -> List[MediaItem]:
        """搜索视频（可选实现）"""
        if not self.supports_video:
            return []
        return []
    
    def get_attribution(self, item: MediaItem) -> str:
        """获取署名信息"""
        if self.requires_attribution and item.author:
            return f"Photo by {item.author} on {self.name.title()}"
        return ""
    
    def _get(self, url: str, headers: Optional[dict] = None, params: Optional[dict] = None) -> Optional[dict]:
        """发送 GET 请求"""
        if not self.session:
            return None
        
        try:
            response = self.session.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[{self.name}] 请求失败: {e}")
            return None
