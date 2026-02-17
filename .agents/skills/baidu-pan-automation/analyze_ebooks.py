#!/usr/bin/env python3
import requests
import os

# 读取token
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('BAIDU_PAN_ACCESS_TOKEN='):
            token = line.strip().split('=', 1)[1]
            break

def list_dir(path):
    url = 'https://pan.baidu.com/rest/2.0/xpan/file'
    params = {
        'method': 'list',
        'access_token': token,
        'dir': path,
        'num': 1000
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        if data.get('errno') == 0:
            return data.get('list', [])
        return []
    except:
        return []

def format_size(size):
    if size > 1024**3:
        return f'{size/1024**3:.1f}GB'
    elif size > 1024**2:
        return f'{size/1024**2:.1f}MB'
    elif size > 1024:
        return f'{size/1024:.1f}KB'
    return f'{size}B'

print('=' * 70)
print('📚 电子书目录现状分析')
print('=' * 70)

ebooks_path = '/我的资源/3-Resources-资源/资源-电子书'
items = list_dir(ebooks_path)

# 分类统计
books = []
subfolders = []

for item in items:
    name = item.get('server_filename', '')
    is_dir = item.get('isdir', 0) == 1
    
    if is_dir:
        subfolders.append(name)
    else:
        ext = os.path.splitext(name)[1].lower()
        books.append({
            'name': name,
            'ext': ext,
            'size': item.get('size', 0)
        })

# 显示子文件夹
if subfolders:
    print(f'\n📁 现有子文件夹 ({len(subfolders)}个):')
    for sf in subfolders:
        print(f'   📂 {sf}')

# 显示书籍统计
print(f'\n📖 书籍文件 ({len(books)}本):')
print('-' * 70)

# 按扩展名分组
ext_count = {}
for book in books:
    ext = book['ext']
    ext_count[ext] = ext_count.get(ext, 0) + 1

print('\n按格式统计:')
for ext, count in sorted(ext_count.items(), key=lambda x: x[1], reverse=True):
    print(f'   {ext}: {count}本')

# 显示所有书籍
print('\n所有书籍列表:')
print('-' * 70)
for i, book in enumerate(books, 1):
    size_str = format_size(book['size'])
    ext = book['ext']
    name = book['name']
    # 截断长文件名
    display_name = name[:55] + '...' if len(name) > 58 else name
    print(f'{i:2d}. [{ext}] {display_name} ({size_str})')

print('\n' + '=' * 70)
