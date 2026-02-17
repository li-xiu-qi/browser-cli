"""输出格式化工具"""
from typing import List, Dict, Any


def format_results_table(results: List[Dict], max_width: int = 80) -> str:
    """格式化搜索结果为表格"""
    if not results:
        return "未找到结果"
    
    lines = []
    lines.append("┌" + "─" * (max_width - 2) + "┐")
    
    for i, item in enumerate(results, 1):
        # 基本信息
        provider = item.get('provider', 'unknown')
        title = item.get('title', item.get('alt', 'Unknown'))[:40]
        author = item.get('author', item.get('photographer', 'Unknown'))[:20]
        
        lines.append(f"│ {i}. [{provider:8}] {title:<40} │")
        lines.append(f"│    作者: {author:<20} 尺寸: {item.get('width', '?')}x{item.get('height', '?')} │")
        
        # 分隔线
        if i < len(results):
            lines.append("├" + "─" * (max_width - 2) + "┤")
    
    lines.append("└" + "─" * (max_width - 2) + "┘")
    return "\n".join(lines)


def format_metadata(metadata: Dict[str, Any]) -> str:
    """格式化元数据为可读文本"""
    lines = []
    lines.append("=" * 50)
    lines.append("文件元数据")
    lines.append("=" * 50)
    
    for key, value in metadata.items():
        if key == 'api_response':
            continue  # 跳过原始 API 响应
        lines.append(f"{key:20}: {value}")
    
    lines.append("=" * 50)
    return "\n".join(lines)


def format_status(config_status: dict) -> str:
    """格式化状态信息"""
    lines = []
    lines.append("╔" + "═" * 58 + "╗")
    lines.append("║" + " Media Downloader 配置状态 ".center(56) + "║")
    lines.append("╠" + "═" * 58 + "╣")
    
    # API Keys
    lines.append("║  API Keys:" + " " * 47 + "║")
    for name, status in config_status['api_keys'].items():
        symbol = "✅" if status else "❌"
        lines.append(f"║    {symbol} {name:12}" + " " * 40 + "║")
    
    lines.append("╠" + "═" * 58 + "╣")
    
    # Tools
    lines.append("║  工具:" + " " * 51 + "║")
    for name, status in config_status['tools'].items():
        symbol = "✅" if status else "❌"
        lines.append(f"║    {symbol} {name:12}" + " " * 40 + "║")
    
    lines.append("╚" + "═" * 58 + "╝")
    
    return "\n".join(lines)
