#!/usr/bin/env python3
"""比较两个 A-Resources 目录的内容"""
import requests
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

def list_dir(dir_path):
    """获取目录内容（递归）"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    all_items = []
    page = 1
    
    while True:
        params = {
            'method': 'list',
            'dir': dir_path,
            'num': 1000,
            'page': page,
            'access_token': ACCESS_TOKEN
        }
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            if data.get('errno') == 0:
                items = data.get('list', [])
                all_items.extend(items)
                if len(items) < 1000:
                    break
                page += 1
            else:
                break
        except:
            break
    
    return all_items

def analyze_dir(name, path):
    """分析目录"""
    print(f"\n📂 {name}")
    print(f"   路径: {path}")
    print("-" * 60)
    
    items = list_dir(path)
    
    if not items:
        print("   (空目录)")
        return None
    
    # 统计
    dirs = [i for i in items if i.get('isdir') == 1]
    files = [i for i in items if i.get('isdir') != 1]
    
    total_size = sum(f.get('size', 0) for f in files)
    
    # 按类型统计
    types = defaultdict(lambda: {'count': 0, 'size': 0})
    for f in files:
        cat = f.get('category', 6)
        type_names = {1: '视频', 2: '音频', 3: '图片', 4: '文档', 5: '应用', 6: '其他', 7: '种子'}
        type_name = type_names.get(cat, '其他')
        types[type_name]['count'] += 1
        types[type_name]['size'] += f.get('size', 0)
    
    print(f"   文件夹: {len(dirs)} 个")
    print(f"   文件: {len(files)} 个")
    print(f"   总大小: {total_size / 1024**3:.2f} GB")
    
    if types:
        print(f"\n   文件类型分布:")
        for t, info in sorted(types.items()):
            size_str = f"{info['size'] / 1024**3:.2f} GB" if info['size'] > 1024**3 else f"{info['size'] / 1024**2:.2f} MB"
            print(f"      {t}: {info['count']} 个 ({size_str})")
    
    if dirs:
        print(f"\n   子目录:")
        for d in sorted(dirs, key=lambda x: x['server_filename'])[:10]:
            print(f"      📁 {d['server_filename']}")
        if len(dirs) > 10:
            print(f"      ... 还有 {len(dirs)-10} 个")
    
    if files and len(files) <= 20:
        print(f"\n   文件列表:")
        for f in sorted(files, key=lambda x: x['server_filename'])[:20]:
            size = f.get('size', 0)
            size_str = f"{size / 1024**3:.2f} GB" if size > 1024**3 else f"{size / 1024**2:.2f} MB"
            print(f"      📄 {f['server_filename'][:40]:40s} {size_str}")
    
    return {
        'name': name,
        'path': path,
        'dirs': dirs,
        'files': files,
        'total_size': total_size,
        'types': dict(types)
    }

print("=" * 60)
print("🔍 比较两个 A-Resources 目录")
print("=" * 60)

# 分析两个目录
dir1 = analyze_dir("我的资源/A-Resources", "/我的资源/A-Resources")
dir2 = analyze_dir("来自：本地电脑/A-Resources", "/来自：本地电脑/A-Resources")

# 比较建议
print("\n" + "=" * 60)
print("💡 合并建议")
print("=" * 60)

if dir1 and dir2:
    print(f"\n📊 对比:")
    print(f"   {'指标':<20} {'我的资源':<20} {'来自：本地电脑':<20}")
    print(f"   {'-'*60}")
    print(f"   {'文件夹数':<20} {len(dir1['dirs']):<20} {len(dir2['dirs']):<20}")
    print(f"   {'文件数':<20} {len(dir1['files']):<20} {len(dir2['files']):<20}")
    print(f"   {'总大小':<20} {dir1['total_size']/1024**3:.2f} GB{'':<10} {dir2['total_size']/1024**3:.2f} GB")
    
    # 检查是否有同名文件
    files1 = {f['server_filename']: f for f in dir1['files']}
    files2 = {f['server_filename']: f for f in dir2['files']}
    
    common_files = set(files1.keys()) & set(files2.keys())
    
    if common_files:
        print(f"\n⚠️ 发现 {len(common_files)} 个同名文件:")
        for fname in list(common_files)[:5]:
            s1 = files1[fname].get('size', 0)
            s2 = files2[fname].get('size', 0)
            print(f"   - {fname}")
            print(f"     我的资源: {s1/1024**2:.2f} MB, 本地电脑: {s2/1024**2:.2f} MB")
    else:
        print(f"\n✅ 没有发现同名文件冲突")
    
    print(f"\n📝 建议策略:")
    if dir1['total_size'] >= dir2['total_size']:
        print(f"   1. 保留: 我的资源/A-Resources/ (内容更多)")
        print(f"   2. 将 '来自：本地电脑/A-Resources/' 的内容移动到前者")
        print(f"   3. 删除空的 '来自：本地电脑/A-Resources/'")
    else:
        print(f"   1. 保留: 来自：本地电脑/A-Resources/ (内容更多)")
        print(f"   2. 将 '我的资源/A-Resources/' 的内容移动到前者")
        print(f"   3. 删除空的 '我的资源/A-Resources/'")
        
    if common_files:
        print(f"   4. 对于同名文件，保留较大的版本")

print("\n" + "=" * 60)
