#!/usr/bin/env python3
import requests
import json

# 读取token
with open('.env', 'r') as f:
    for line in f:
        if line.startswith('BAIDU_PAN_ACCESS_TOKEN='):
            token = line.strip().split('=', 1)[1]
            break

def move_file(src_path, dest_path, new_name):
    '''移动文件'''
    url = 'https://pan.baidu.com/rest/2.0/xpan/file'
    
    params = {
        'method': 'filemanager',
        'access_token': token,
        'opera': 'move'
    }
    
    file_list = [{
        'path': src_path,
        'dest': dest_path,
        'newname': new_name
    }]
    
    data = {'filelist': json.dumps(file_list)}
    
    try:
        response = requests.post(url, params=params, data=data, timeout=30)
        return response.json()
    except Exception as e:
        return {'error': str(e)}

# 读取书籍列表
with open('books_to_move.json', 'r', encoding='utf-8') as f:
    books = json.load(f)

print('=' * 60)
print('📚 开始移动书籍到 资源-电子书')
print('=' * 60)

dest_folder = '/我的资源/3-Resources-资源/资源-电子书'
success_count = 0
failed_books = []

for book in books:
    name = book['name']
    src_path = book['path']
    size_mb = book['size'] / 1024 / 1024
    
    print(f'\n🔄 移动: {name} ({size_mb:.1f}MB)')
    
    result = move_file(src_path, dest_folder, name)
    
    if result.get('errno') == 0:
        print(f'   ✅ 成功')
        success_count += 1
    elif result.get('errno') == -8:
        print(f'   ⚠️ 目标位置已存在同名文件')
        failed_books.append({'book': book, 'reason': '已存在'})
    else:
        errno = result.get('errno', 'unknown')
        print(f'   ❌ 失败: errno={errno}')
        failed_books.append({'book': book, 'reason': f'errno={errno}'})

print('\n' + '=' * 60)
print(f'✅ 移动完成: {success_count}/{len(books)} 本成功')
if failed_books:
    print(f'⚠️ 失败: {len(failed_books)} 本')
    for fb in failed_books:
        print(f'   - {fb["book"]["name"]}: {fb["reason"]}')
print('=' * 60)
