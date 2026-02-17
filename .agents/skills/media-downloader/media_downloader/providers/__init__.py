"""图库提供商模块"""
from .pexels import PexelsProvider
from .unsplash import UnsplashProvider
from .pixabay import PixabayProvider

__all__ = ['PexelsProvider', 'UnsplashProvider', 'PixabayProvider']

# 提供商注册表
PROVIDERS = {
    'pexels': PexelsProvider,
    'unsplash': UnsplashProvider,
    'pixabay': PixabayProvider,
}
