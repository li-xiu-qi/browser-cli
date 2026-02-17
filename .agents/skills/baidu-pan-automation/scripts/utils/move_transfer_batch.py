#!/usr/bin/env python3
"""分批将转存区域内容移动到 我的资源/00-转存区域"""
import requests
import json
from pathlib import Path
import time

env_path = Path(__file__).parent.parent / '.env'
config = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

ACCESS_TOKEN = config.get('BAIDU_PAN_ACCESS_TOKEN', '')

def list_dir(path):
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {'method': 'list', 'dir': path, 'num': 1000, 'access_token': ACCESS_TOKEN}
    try:
        r = requests.get(url, params=params, timeout=30)
        return r.json().get('list', [])
    except:
        return []

def filemanager_op(opera, filelist):
    url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={ACCESS_TOKEN}&opera={opera}"
    data = {'async': 0, 'filelist': json.dumps(filelist)}
    try:
        r = requests.post(url, data=data, timeout=30)
        return r.json()
    except Exception as e:
        return {'errno': -1, 'error': str(e)}

def create_folder(path):
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {'method': 'create', 'access_token': ACCESS_TOKEN}
    data = {'size': 0, 'isdir': 1, 'path': path, 'rtype': 1}
    try:
        r = requests.post(url, params=params, data=data, timeout=30)
        result = r.json()
        return result.get('errno') == 0 or result.get('errno') == -8
    except:
        return False

def move(src, dest, newname=None):
    if newname is None:
        newname = Path(src).name
    result = filemanager_op('move', [{'path': src, 'dest': dest, 'newname': newname}])
    info = result.get('info', [{}])[0] if result.get('info') else {}
    return info.get('errno') == 0, info

print("="*70)
print("🚀 分批移动转存区域内容")
print("="*70)

# 先创建目标文件夹
print("\n📁 Step 1: 创建 00-转存区域")
dest_folder = "/我的资源/00-转存区域"
if create_folder(dest_folder):
    print("  ✅ 创建成功")
else:
    print("  📌 已存在或创建失败")

# 获取转存区域内容
print("\n📦 Step 2: 获取转存区域内容")
src_items = list_dir("/转存区域")
print(f"  发现 {len(src_items)} 个项目")

# 优先移动我们关心的项目
priority_items = ['03-破局俱乐部大航海', '一堂最佳实践', '大模型全栈正式课课件.rar', 
                  '视频号下载视频', '知乎知学堂AI大模型全栈工程师', '马士兵-AI大模型全链路实战']

print("\n📦 Step 3: 移动优先项目")
success_count = 0
fail_count = 0

for item_name in priority_items:
    # 在列表中查找
    found = False
    for item in src_items:
        if item['server_filename'] == item_name:
            found = True
            src = f"/转存区域/{item_name}"
            success, info = move(src, dest_folder)
            if success:
                print(f"  ✅ {item_name}")
                success_count += 1
            else:
                errno = info.get('errno', 'unknown') if isinstance(info, dict) else info
                print(f"  ❌ {item_name}: {errno}")
                fail_count += 1
            time.sleep(0.8)
            break
    
    if not found:
        print(f"  ⚠️  未找到: {item_name}")

print(f"\n📊 优先项目: 成功 {success_count}, 失败 {fail_count}")

# 移动其他项目（前10个）
print("\n📦 Step 4: 移动其他项目（前10个）")
other_success = 0
for item in src_items[:10]:
    name = item['server_filename']
    if name not in priority_items:
        src = f"/转存区域/{name}"
        success, info = move(src, dest_folder)
        if success:
            print(f"  ✅ {name[:40]}")
            other_success += 1
        else:
            errno = info.get('errno', 'unknown') if isinstance(info, dict) else info
            print(f"  ❌ {name[:40]}: {errno}")
        time.sleep(0.8)

print(f"\n📊 其他项目: 成功 {other_success}")

# 检查剩余
print("\n📦 Step 5: 检查剩余内容")
remaining = list_dir("/转存区域")
print(f"  转存区域剩余: {len(remaining)} 个项目")

print("\n📦 Step 6: 检查 00-转存区域 内容")
moved_items = list_dir(dest_folder)
print(f"  00-转存区域现有: {len(moved_items)} 个项目")
for item in moved_items[:10]:
    print(f"    - {item['server_filename']}")
if len(moved_items) > 10:
    print(f"    ... 还有 {len(moved_items)-10} 个")

print("\n" + "="*70)
print("✅ 分批移动完成")
print("="*70)
