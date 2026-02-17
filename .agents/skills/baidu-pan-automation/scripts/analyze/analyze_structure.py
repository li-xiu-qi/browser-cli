#!/usr/bin/env python3
"""
分析百度网盘目录结构
"""
import requests
import os
from pathlib import Path

# 加载 .env
env_path = Path(__file__).parent.parent / '.env'
config = {}
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

ACCESS_TOKEN = config.get('BAIDU_PAN_ACCESS_TOKEN', '')

def api_request(endpoint, params=None):
    """API 请求封装"""
    url = f"https://pan.baidu.com/rest/2.0/xpan/{endpoint}"
    params = params or {}
    params['access_token'] = ACCESS_TOKEN
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        if data.get("errno") == 0:
            return data
        else:
            print(f"API 错误: {data}")
            return None
    except Exception as e:
        print(f"请求失败: {e}")
        return None

def list_files(dir="/", page=1, num=1000):
    """获取目录文件列表"""
    result = api_request('file', {
        'method': 'list',
        'dir': dir,
        'page': page,
        'num': num,
        'order': 'time'
    })
    return result.get('list', []) if result else []

def get_quota():
    """获取容量信息"""
    return api_request('quota', {'method': 'info'})

def analyze_directory(dir_path, depth=0, max_depth=2):
    """递归分析目录结构"""
    if depth > max_depth:
        return None
    
    files = list_files(dir_path)
    
    dirs = []
    files_count = 0
    total_size = 0
    
    for item in files:
        if item.get('isdir') == 1:
            subdir = analyze_directory(item['path'], depth + 1, max_depth)
            if subdir:
                dirs.append(subdir)
        else:
            files_count += 1
            total_size += item.get('size', 0)
    
    return {
        'name': dir_path.split('/')[-1] or '根目录',
        'path': dir_path,
        'dirs': dirs,
        'files_count': files_count,
        'total_size': total_size
    }

def print_tree(node, prefix="", is_last=True):
    """打印树形结构"""
    if node is None:
        return
    
    connector = "└── " if is_last else "├── "
    size_str = format_size(node.get('total_size', 0))
    files_info = f"[{node.get('files_count', 0)} 个文件]" if node.get('files_count', 0) > 0 else ""
    
    print(f"{prefix}{connector}{node['name']} {files_info} {size_str}")
    
    children = node.get('dirs', [])
    for i, child in enumerate(children):
        is_last_child = (i == len(children) - 1)
        extension = "    " if is_last else "│   "
        print_tree(child, prefix + extension, is_last_child)

def format_size(size):
    """格式化文件大小"""
    if size == 0:
        return ""
    if size > 1024**4:
        return f"({size / 1024**4:.2f} TB)"
    elif size > 1024**3:
        return f"({size / 1024**3:.2f} GB)"
    elif size > 1024**2:
        return f"({size / 1024**2:.2f} MB)"
    return f"({size / 1024:.2f} KB)"

def analyze_by_category():
    """按文件类型分析"""
    print("\n" + "="*60)
    print("📊 文件类型分布")
    print("="*60)
    
    categories = {
        1: ("视频", 0, 0),
        2: ("音频", 0, 0),
        3: ("图片", 0, 0),
        4: ("文档", 0, 0),
        5: ("应用", 0, 0),
        6: ("其他", 0, 0),
        7: ("种子", 0, 0),
    }
    
    # 递归统计（简化版，只搜索前几个目录）
    root_files = list_files("/", num=1000)
    
    for item in root_files:
        if item.get('isdir') != 1:
            cat = item.get('category', 6)
            name, count, size = categories.get(cat, ("其他", 0, 0))
            categories[cat] = (name, count + 1, size + item.get('size', 0))
    
    for cat_id, (name, count, size) in sorted(categories.items()):
        if count > 0:
            print(f"{name:8s}: {count:4d} 个文件 {format_size(size)}")

def main():
    print("="*60)
    print("🔍 百度网盘目录结构分析")
    print("="*60)
    
    # 容量信息
    quota = get_quota()
    if quota:
        total = quota.get('total', 0)
        used = quota.get('used', 0)
        free = total - used
        print(f"\n💾 容量使用情况:")
        print(f"   总容量: {total / 1024**4:.2f} TB")
        print(f"   已使用: {used / 1024**4:.2f} TB ({used/total*100:.1f}%)")
        print(f"   剩余:   {free / 1024**4:.2f} TB")
    
    # 根目录结构
    print(f"\n📁 根目录结构 (前2层):")
    print("-"*60)
    root = analyze_directory("/", max_depth=2)
    if root:
        print_tree(root)
    
    # 文件类型分析
    analyze_by_category()
    
    print("\n" + "="*60)
    print("✅ 分析完成")
    print("="*60)

if __name__ == "__main__":
    main()
