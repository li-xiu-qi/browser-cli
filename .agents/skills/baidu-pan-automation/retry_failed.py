#!/usr/bin/env python3
import requests
import json
import time

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

# 失败的书籍
failed_books = [
    {'name': '写给大家看的设计书 ([美] Robin Williams) .pdf', 'path': '/我的资源/2-Areas-领域/领域-技术阅读/产品与设计/写给大家看的设计书 ([美] Robin Williams) .pdf'},
    {'name': '《思考快与慢》.pdf', 'path': '/我的资源/2-Areas-领域/领域-技术阅读/其他技术/《思考快与慢》.pdf'},
    {'name': '如何阅读一本书.pdf', 'path': '/我的资源/2-Areas-领域/领域-技术阅读/其他技术/如何阅读一本书.pdf'},
]

print('=' * 60)
print('🔄 重试移动失败的书籍')
print('=' * 60)

dest_folder = '/我的资源/3-Resources-资源/资源-电子书'

for book in failed_books:
    name = book['name']
    src_path = book['path']
    
    print(f'\n🔄 重试: {name}')
    
    # 等待2秒
    time.sleep(2)
    
    result = move_file(src_path, dest_folder, name)
    
    if result.get('errno') == 0:
        print(f'   ✅ 成功')
    else:
        errno = result.get('errno', 'unknown')
        print(f'   ❌ 仍失败: errno={errno}')
        print(f'   可能需要手动移动此文件')

print('\n' + '=' * 60)
print('✅ 重试完成')
print('=' * 60)
