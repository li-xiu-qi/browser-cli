#!/usr/bin/env python3
import requests
from pathlib import Path

env_path = Path('.env')
config = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

TOKEN = config.get('BAIDU_PAN_ACCESS_TOKEN', '')

def list_dir(path):
    url = 'https://pan.baidu.com/rest/2.0/xpan/file'
    params = {'method': 'list', 'dir': path, 'num': 1000, 'access_token': TOKEN}
    try:
        r = requests.get(url, params=params, timeout=30)
        return r.json().get('list', [])
    except:
        return []

BASE = '/我的资源/4-Archives-归档/归档-学校资料'
folders = ['作业', '考试', '课件']

print('='*70)
print('查看作业、考试、课件内容')
print('='*70)

for folder in folders:
    print(f'\n📁 {folder}:')
    print('-'*50)
    items = list_dir(f'{BASE}/{folder}')
    for item in items:
        name = item['server_filename']
        is_dir = item.get('isdir') == 1
        icon = '📁' if is_dir else '📄'
        print(f'  {icon} {name}')
        
        if is_dir:
            sub_items = list_dir(f'{BASE}/{folder}/{name}')
            for sub in sub_items[:5]:
                sub_name = sub['server_filename']
                print(f'      └─ {sub_name}')
            if len(sub_items) > 5:
                print(f'      └─ ... 还有 {len(sub_items)-5} 项')
