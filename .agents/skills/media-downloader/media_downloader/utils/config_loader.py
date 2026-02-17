"""配置管理模块"""
import os
from pathlib import Path
from typing import Optional


class Config:
    """配置管理类"""
    
    def __init__(self):
        self.skill_dir = Path(__file__).parent.parent.parent
        self.downloads_dir = self.skill_dir / 'downloads'
        self.cache_dir = self.skill_dir / 'cache'
        self.config_dir = self.skill_dir / 'config'
        
        # 确保目录存在
        self.downloads_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
        
        # 加载配置
        self._load_env()
    
    def _load_env(self):
        """从 .env 文件加载环境变量"""
        env_file = self.skill_dir / '.env'
        
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"\'')  # 去除引号
                        # 只在环境变量未设置时才设置
                        if key not in os.environ:
                            os.environ[key] = value
    
    @property
    def pexels_api_key(self) -> Optional[str]:
        return os.environ.get('PEXELS_API_KEY') or None
    
    @property
    def unsplash_access_key(self) -> Optional[str]:
        return os.environ.get('UNSPLASH_ACCESS_KEY') or None
    
    @property
    def pixabay_api_key(self) -> Optional[str]:
        return os.environ.get('PIXABAY_API_KEY') or None
    
    def check_provider(self, name: str) -> bool:
        """检查指定提供商是否可用"""
        providers = {
            'pexels': self.pexels_api_key,
            'unsplash': self.unsplash_access_key,
            'pixabay': self.pixabay_api_key,
        }
        return bool(providers.get(name.lower()))
    
    def get_status(self) -> dict:
        """获取配置状态"""
        import shutil
        
        return {
            'api_keys': {
                'pexels': bool(self.pexels_api_key),
                'unsplash': bool(self.unsplash_access_key),
                'pixabay': bool(self.pixabay_api_key),
            },
            'tools': {
                'yt_dlp': bool(shutil.which('yt-dlp')),
                'ffmpeg': bool(shutil.which('ffmpeg')),
            },
            'directories': {
                'skill': str(self.skill_dir),
                'downloads': str(self.downloads_dir),
                'cache': str(self.cache_dir),
            }
        }
