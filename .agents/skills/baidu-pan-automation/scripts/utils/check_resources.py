#!/usr/bin/env python3
"""检查资源文件夹结构"""
import requests
from pathlib import Path

env_path = Path(__file__).parent.parent / '.env'
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
        data = r.json()
        return data.get('list', [])
    except Exception as e:
        print(f'Error: {e}')
        return []

BASE = '/我的资源/3-Resources-资源'

print('='*70)
print('📂 资源文件夹详细结构')
print('='*70)

items = list_dir(BASE)
print(f'\n找到 {len(items)} 个项目\n')

for item in items:
    name = item['server_filename']
    is_dir = item.get('isdir') == 1
    
    if is_dir:
        sub_items = list_dir(f'{BASE}/{name}')
        print(f'\n📁 {name} ({len(sub_items)} 项)')
        
        # 显示前10个
        for sub in sub_items[:10]:
            sub_name = sub['server_filename']
            sub_is_dir = sub.get('isdir') == 1
            icon = '📁' if sub_is_dir else '📄'
            print(f'   {icon} {sub_name}')
        
        if len(sub_items) > 10:
            print(f'   ... 还有 {len(sub_items)-10} 项')
    else:
        print(f'📄 {name}')

print('\n' + '='*70)
