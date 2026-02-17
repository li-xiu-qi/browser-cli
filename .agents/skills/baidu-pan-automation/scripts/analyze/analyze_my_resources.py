#!/usr/bin/env python3
"""分析'我的资源'文件夹并给出整理建议"""
import requests
import json
from pathlib import Path
from collections import defaultdict

env_path = Path(__file__).parent.parent / '.env'
config = {}
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

ACCESS_TOKEN = config.get('BAIDU_PAN_ACCESS_TOKEN', '')

def list_dir(dir_path, recursion=False):
    """获取目录列表"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {
        'method': 'list',
        'dir': dir_path,
        'num': 1000,
        'access_token': ACCESS_TOKEN
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        return data.get('list', []) if data.get('errno') == 0 else []
    except Exception as e:
        print(f"  ⚠️  获取失败: {dir_path} - {e}")
        return []

def get_file_extension(filename):
    """获取文件扩展名"""
    return Path(filename).suffix.lower()

def categorize_file(filename):
    """根据文件名分类"""
    ext = get_file_extension(filename)
    categories = {
        'video': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.ts', '.m3u8'],
        'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'],
        'document': ['.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.xls', '.xlsx', '.csv', '.md'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'],
        'archive': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'],
        'code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.h', '.go', '.rs'],
        'executable': ['.exe', '.msi', '.dmg', '.pkg', '.deb', '.rpm'],
    }
    for cat, exts in categories.items():
        if ext in exts:
            return cat
    return 'other'

def analyze_folder(path, name, depth=0, max_depth=2):
    """递归分析文件夹"""
    items = list_dir(path)
    if not items:
        return {'dirs': [], 'files': [], 'stats': {}}, 0
    
    dirs = [i for i in items if i.get('isdir') == 1]
    files = [i for i in items if i.get('isdir') != 1]
    
    total_size = sum(f.get('size', 0) for f in files)
    
    # 文件类型统计
    file_stats = defaultdict(lambda: {'count': 0, 'size': 0})
    for f in files:
        cat = categorize_file(f['server_filename'])
        file_stats[cat]['count'] += 1
        file_stats[cat]['size'] += f.get('size', 0)
    
    result = {
        'dirs': dirs,
        'files': files,
        'stats': dict(file_stats),
        'total_size': total_size,
        'file_count': len(files),
        'dir_count': len(dirs)
    }
    
    # 递归分析子目录（限制深度）
    if depth < max_depth:
        for d in dirs[:5]:  # 只分析前5个子目录避免太慢
            sub_path = path + '/' + d['server_filename']
            sub_result, _ = analyze_folder(sub_path, d['server_filename'], depth + 1, max_depth)
            d['_analysis'] = sub_result
    
    return result, total_size

def format_size(size):
    """格式化文件大小"""
    if size > 1024**4:
        return f"{size/1024**4:.2f} TB"
    elif size > 1024**3:
        return f"{size/1024**3:.2f} GB"
    elif size > 1024**2:
        return f"{size/1024**2:.2f} MB"
    else:
        return f"{size/1024:.2f} KB"

# ========== 主分析 ==========
print("="*70)
print("📊 我的资源 - 深度分析报告")
print("="*70)

TARGET_DIR = "/我的资源"
result, total_size = analyze_folder(TARGET_DIR, "我的资源")

print(f"\n📁 总览:")
print(f"   文件夹数: {result['dir_count']} 个")
print(f"   文件数: {result['file_count']} 个")
print(f"   总大小: {format_size(result['total_size'])}")

print(f"\n📂 子文件夹结构:")
print("-"*70)

for d in sorted(result['dirs'], key=lambda x: x['server_filename']):
    name = d['server_filename']
    sub = d.get('_analysis', {})
    sub_dirs = sub.get('dir_count', 0)
    sub_files = sub.get('file_count', 0)
    sub_size = sub.get('total_size', 0)
    
    size_str = format_size(sub_size)
    detail = f"({sub_dirs} 文件夹, {sub_files} 文件)"
    
    # 分类标记
    category = "📁"
    if any(k in name.lower() for k in ['书', 'book', 'pdf']):
        category = "📚"
    elif any(k in name.lower() for k in ['视频', 'video', 'movie', '课']):
        category = "🎬"
    elif any(k in name.lower() for k in ['软件', '安装', 'exe', 'app']):
        category = "💿"
    elif any(k in name.lower() for k in ['资源', 'resource', '素材']):
        category = "📦"
    elif any(k in name.lower() for k in ['obsidian', '笔记', 'note']):
        category = "📝"
    
    print(f"  {category} {name:30s} {size_str:>12s} {detail}")

# 文件类型统计
print(f"\n📊 文件类型分布:")
print("-"*70)
for cat, stats in sorted(result['stats'].items(), key=lambda x: -x[1]['size']):
    cat_icon = {
        'video': '🎬', 'audio': '🎵', 'document': '📄',
        'image': '🖼️', 'archive': '📦', 'code': '💻',
        'executable': '⚙️', 'other': '📎'
    }.get(cat, '📎')
    print(f"  {cat_icon} {cat:12s}: {stats['count']:4d} 个, {format_size(stats['size']):>12s}")

# 整理建议
print(f"\n💡 整理建议:")
print("-"*70)

suggestions = []

# 根据内容给出建议
for d in result['dirs']:
    name = d['server_filename'].lower()
    
    # 检查是否需要合并
    if 'a-resource' in name or 'aresource' in name:
        suggestions.append(f"🔀 检查是否有重复的 A-Resources 文件夹，考虑合并")
    
    # 检查是否有零散文档
    if d.get('_analysis', {}).get('file_count', 0) > 50 and d.get('_analysis', {}).get('dir_count', 0) == 0:
        suggestions.append(f"📂 '{d['server_filename']}' 文件过多，建议按类型或日期分文件夹")
    
    # 检查是否有大文件
    if d.get('_analysis', {}).get('total_size', 0) > 10 * 1024**3:
        suggestions.append(f"💾 '{d['server_filename']}' 超过 10GB，建议细分或归档")

# 检查重复名称
names = [d['server_filename'].lower() for d in result['dirs']]
from collections import Counter
dupes = {k: v for k, v in Counter(names).items() if v > 1}
if dupes:
    suggestions.append(f"⚠️  发现重复名称: {', '.join(dupes.keys())}")

if not suggestions:
    suggestions.append("✅ 结构较为清晰，建议定期清理临时文件")
    suggestions.append("💡 可考虑按 '学习/工作/娱乐' 建立一级分类")

for s in suggestions[:10]:
    print(f"  {s}")

print("\n" + "="*70)
