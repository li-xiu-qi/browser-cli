#!/usr/bin/env python3
import requests

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

print('=' * 60)
print('📋 移动结果验证')
print('=' * 60)

# 检查资源-电子书
print('\n📁 3-Resources-资源/资源-电子书 (新增书籍):')
print('-' * 60)
ebooks = list_dir('/我的资源/3-Resources-资源/资源-电子书')
book_count = 0
for item in ebooks:
    name = item.get('server_filename', '')
    if name.endswith(('.pdf', '.epub', '.mobi')):
        size_mb = item.get('size', 0) / 1024 / 1024
        print(f'   📖 {name[:50]}... ({size_mb:.1f}MB)')
        book_count += 1

print(f'\n   共 {book_count} 本书籍')

# 检查技术阅读里还剩什么书
print('\n📁 2-Areas-领域/领域-技术阅读 (剩余书籍):')
print('-' * 60)

folders = ['产品与设计', '其他技术', '写作']
remaining_books = []
for folder in folders:
    items = list_dir(f'/我的资源/2-Areas-领域/领域-技术阅读/{folder}')
    for item in items:
        name = item.get('server_filename', '')
        if not item.get('isdir', 0) and name.endswith(('.pdf', '.epub', '.mobi', '.azw3', '.txt')):
            remaining_books.append({'folder': folder, 'name': name})

if remaining_books:
    for book in remaining_books:
        print(f"   ❌ [{book['folder']}] {book['name'][:40]}...")
    print(f'\n   还剩 {len(remaining_books)} 本需要手动移动')
else:
    print('   (已清空)')

print('\n' + '=' * 60)
print('✅ 验证完成')
print('=' * 60)
