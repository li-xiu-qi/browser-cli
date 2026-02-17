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
    except Exception as e:
        print(f"Error listing {path}: {e}")
        return []

book_exts = ['.pdf', '.epub', '.mobi', '.azw3', '.txt']
books = []

# 查找书籍的文件夹列表
folders_to_check = [
    '/我的资源/2-Areas-领域/领域-技术阅读/产品与设计',
    '/我的资源/2-Areas-领域/领域-技术阅读/其他技术', 
    '/我的资源/2-Areas-领域/领域-技术阅读/写作',
]

for folder in folders_to_check:
    print(f"检查: {folder}")
    items = list_dir(folder)
    for item in items:
        name = item.get('server_filename', '')
        is_dir = item.get('isdir', 0) == 1
        
        if not is_dir:
            ext = name.lower()
            if any(ext.endswith(e) for e in book_exts):
                books.append({
                    'name': name,
                    'path': f"{folder}/{name}",
                    'size': item.get('size', 0)
                })
                size_mb = item.get('size', 0) / 1024 / 1024
                print(f"  找到: {name} ({size_mb:.1f}MB)")

print(f"\n总共找到 {len(books)} 本书籍")

# 保存到文件
with open('books_to_move.json', 'w', encoding='utf-8') as f:
    json.dump(books, f, ensure_ascii=False, indent=2)
