"""Media Downloader - 智能媒体下载器"""

__version__ = "2.0.0"
__author__ = "AI Assistant"

from .core import SearchEngine, DownloadManager, MetadataManager, VideoProcessor
from .utils import Config

__all__ = [
    'SearchEngine',
    'DownloadManager', 
    'MetadataManager',
    'VideoProcessor',
    'Config',
]
