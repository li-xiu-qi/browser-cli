"""元数据管理模块"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from ..providers.base import MediaItem


class MetadataManager:
    """元数据管理器 - 自动创建 sidecar 文件"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path.cwd()
    
    def create_sidecar(self, item: MediaItem, 
                       filepath: Path,
                       extra_metadata: Optional[Dict] = None) -> Path:
        """为下载的文件创建元数据 sidecar 文件
        
        Args:
            item: MediaItem 对象
            filepath: 下载的文件路径
            extra_metadata: 额外的元数据
        
        Returns:
            sidecar 文件路径
        """
        sidecar_path = filepath.parent / f"{filepath.name}.meta.json"
        
        metadata = {
            # 基本信息
            'source': item.provider,
            'type': item.type,
            'id': item.id,
            'url': item.source_url,
            'download_url': item.url,
            
            # 文件信息
            'filename': filepath.name,
            'filepath': str(filepath.absolute()),
            'file_size': filepath.stat().st_size if filepath.exists() else None,
            
            # 媒体信息
            'width': item.width,
            'height': item.height,
            'duration': item.duration,
            
            # 作者信息
            'author': item.author,
            'author_url': item.author_url,
            
            # 描述
            'title': item.title,
            'alt': item.alt,
            
            # 版权
            'license': item.license,
            'attribution': self._generate_attribution(item),
            
            # 时间戳
            'downloaded_at': datetime.now().isoformat(),
        }
        
        # 添加额外元数据
        if extra_metadata:
            metadata.update(extra_metadata)
        
        # 保存原始 API 响应（可选）
        if item.raw_data:
            metadata['_raw_api_response'] = item.raw_data
        
        # 写入文件
        with open(sidecar_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        return sidecar_path
    
    def load_sidecar(self, filepath: Path) -> Optional[Dict]:
        """加载 sidecar 元数据"""
        sidecar_path = filepath.parent / f"{filepath.name}.meta.json"
        
        if not sidecar_path.exists():
            return None
        
        try:
            with open(sidecar_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载元数据失败: {e}")
            return None
    
    def _generate_attribution(self, item: MediaItem) -> str:
        """生成署名信息"""
        if item.author:
            return f"Photo by {item.author} on {item.provider.title()}"
        return f"Source: {item.provider.title()}"
    
    def scan_directory(self, directory: Path) -> list:
        """扫描目录中的所有元数据"""
        results = []
        
        for meta_file in directory.glob("*.meta.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    results.append(data)
            except Exception:
                pass
        
        return results
