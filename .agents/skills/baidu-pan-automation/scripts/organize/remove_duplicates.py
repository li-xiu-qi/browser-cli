#!/usr/bin/env python3
"""删除重复的安装包"""
import requests
import json
from pathlib import Path
import time
import re

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

def delete(path):
    url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={ACCESS_TOKEN}&opera=delete"
    data = {'async': 0, 'filelist': json.dumps([path])}
    try:
        r = requests.post(url, data=data, timeout=30)
        result = r.json()
        info = result.get('info', [{}])[0] if result.get('info') else {}
        return info.get('errno') == 0
    except:
        return False

BASE = "/我的资源/3-Resources-资源/资源-安装包"

print("="*70)
print("🗑️ 删除重复的安装包")
print("="*70)

items = list_dir(BASE)
duplicates = [i for i in items if re.search(r'\(\d+\)', i['server_filename'])]

print(f"\n发现 {len(duplicates)} 个重复文件\n")

deleted = 0
for dup in duplicates[:50]:  # 先处理前50个
    name = dup['server_filename']
    path = f"{BASE}/{name}"
    if delete(path):
        print(f"✅ {name[:60]}")
        deleted += 1
    else:
        print(f"❌ {name[:60]}")
    time.sleep(0.5)

print(f"\n已删除: {deleted}/{len(duplicates[:50])}")
print("="*70)
