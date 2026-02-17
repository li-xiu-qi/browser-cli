#!/usr/bin/env python3
"""合并两个 A-Resources 目录"""
import requests
import json
from pathlib import Path

env_path = Path(__file__).parent.parent / '.env'
config = {}
if env_path.exists():
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

ACCESS_TOKEN = config.get('BAIDU_PAN_ACCESS_TOKEN', '')

# 源目录（将被移动的）
SOURCE_DIR = "/来自：本地电脑/A-Resources"
# 目标目录（保留的）
TARGET_DIR = "/我的资源/A-Resources"

def api_request(endpoint, method='GET', params=None, data=None):
    """API 请求"""
    url = f"https://pan.baidu.com/rest/2.0/xpan/{endpoint}"
    params = params or {}
    params['access_token'] = ACCESS_TOKEN
    
    try:
        if method == 'GET':
            response = requests.get(url, params=params, timeout=30)
        else:
            response = requests.post(url, params=params, data=data, timeout=30)
        
        result = response.json()
        if result.get('errno') == 0:
            return result
        else:
            print(f"   ⚠️ API 错误: {result}")
            return None
    except Exception as e:
        print(f"   ❌ 请求失败: {e}")
        return None

def list_dir(dir_path):
    """列出目录内容"""
    result = api_request('file', params={
        'method': 'list',
        'dir': dir_path,
        'num': 1000
    })
    return result.get('list', []) if result else []

def move_file(src_path, dest_dir, new_name=None):
    """移动文件/文件夹"""
    if new_name is None:
        new_name = src_path.split('/')[-1]
    
    filelist = [{
        "path": src_path,
        "dest": dest_dir,
        "newname": new_name
    }]
    
    result = api_request('file', method='POST', data={
        'method': 'move',
        'filelist': json.dumps(filelist),
        'async': 0,
        'ondup': 'newcopy'  # 如果存在则重命名
    })
    
    return result

def merge_directories():
    """执行合并"""
    print("="*60)
    print("🚀 开始合并 A-Resources 目录")
    print("="*60)
    print(f"\n📤 源目录: {SOURCE_DIR}")
    print(f"📥 目标目录: {TARGET_DIR}")
    print()
    
    # 获取源目录内容
    print("🔍 扫描源目录内容...")
    source_items = list_dir(SOURCE_DIR)
    
    if not source_items:
        print("✅ 源目录为空，无需合并")
        return
    
    print(f"   发现 {len(source_items)} 个项目")
    
    # 获取目标目录已存在的项目
    print("🔍 扫描目标目录...")
    target_items = list_dir(TARGET_DIR)
    target_names = {item['server_filename'] for item in target_items}
    
    # 分类处理
    to_move = []  # 需要移动的（目标没有）
    to_compare = []  # 需要比较的（目标有同名）
    
    for item in source_items:
        name = item['server_filename']
        if name in target_names:
            to_compare.append(item)
        else:
            to_move.append(item)
    
    print(f"\n📊 处理计划:")
    print(f"   - 直接移动: {len(to_move)} 个项目")
    print(f"   - 同名需比较: {len(to_compare)} 个项目")
    
    # 1. 直接移动不冲突的项目
    if to_move:
        print(f"\n📦 第 1 步: 移动不冲突的项目...")
        for i, item in enumerate(to_move, 1):
            name = item['server_filename']
            item_type = "📁" if item.get('isdir') == 1 else "📄"
            print(f"   {i}/{len(to_move)} {item_type} {name}")
            
            result = move_file(f"{SOURCE_DIR}/{name}", TARGET_DIR)
            if result:
                print(f"      ✅ 移动成功")
            else:
                print(f"      ❌ 移动失败")
    
    # 2. 处理同名的项目
    if to_compare:
        print(f"\n⚠️ 第 2 步: 处理同名项目...")
        print("   (由于涉及目录递归比较，建议手动处理以下项目:)")
        
        for item in to_compare:
            name = item['server_filename']
            item_type = "文件夹" if item.get('isdir') == 1 else "文件"
            size = item.get('size', 0)
            size_str = f"{size/1024**3:.2f} GB" if size > 1024**3 else f"{size/1024**2:.2f} MB"
            
            print(f"\n   - {item_type}: {name}")
            print(f"     大小: {size_str}")
            print(f"     建议: 两个目录都有 '{name}'，请检查内容后决定保留哪个")
    
    # 3. 检查源目录是否为空
    print(f"\n🧹 第 3 步: 检查源目录...")
    remaining = list_dir(SOURCE_DIR)
    
    if not remaining:
        print("   ✅ 源目录已空，可以删除")
        print(f"\n💡 请手动删除空目录: {SOURCE_DIR}")
        print("   操作: 在百度网盘网页版或客户端中删除此空文件夹")
    else:
        print(f"   ⚠️ 源目录还有 {len(remaining)} 个项目")
        print("   (请手动处理剩余项目)")
    
    print("\n" + "="*60)
    print("✅ 合并操作完成")
    print("="*60)
    
    # 生成总结
    print("\n📋 操作总结:")
    print(f"   - 成功移动: {len(to_move)} 个项目到 {TARGET_DIR}")
    if to_compare:
        print(f"   - 需要手动处理: {len(to_compare)} 个同名项目")
    if not remaining:
        print(f"   - 可以删除: {SOURCE_DIR}")

if __name__ == "__main__":
    merge_directories()
