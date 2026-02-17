#!/usr/bin/env python3
import requests
import json

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

# 查找所有书籍文件
book_exts = ['.pdf', '.epub', '.mobi', '.azw3', '.txt']
books = []

def find_books(path):
    items = list_dir(path)
    for item in items:
        name = item.get('server_filename', '')
        is_dir = item.get('isdir', 0) == 1
        full_path = f'{path}/{name}'
        
        if is_dir:
            find_books(full_path)
        else:
            ext = name.lower()
            if any(ext.endswith(e) for e in book_exts):
                books.append({
                    'name': name,
                    'path': full_path,
                    'size': item.get('size', 0)
                })

print('正在查找技术阅读中的书籍...')
find_books('/我的资源/2-Areas-领域/领域-技术阅读')

print(f'找到 {len(books)} 本书籍:')
for book in books:
    size_mb = book['size'] / 1024 / 1024
    print(f'  - {book["name"]} ({size_mb:.1f}MB)')

# 保存书籍列表到文件供后续使用
with open('books_to_move.json', 'w', encoding='utf-8') as f:
    json.dump(books, f, ensure_ascii=False, indent=2)

print(f'\\n书籍列表已保存到 books_to_move.json')
