#!/usr/bin/env python3
"""查看资源-安装包的内容"""
import requests
from pathlib import Path
from collections import defaultdict

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
        return r.json().get('list', [])
    except:
        return []

BASE = '/我的资源/3-Resources-资源/资源-安装包'

print('='*70)
print('📦 资源-安装包 内容分析')
print('='*70)

items = list_dir(BASE)

# 按类型分类
categories = defaultdict(list)

for item in items:
    name = item['server_filename'].lower()
    is_dir = item.get('isdir') == 1
    
    # 分类规则
    if any(k in name for k in ['python', 'pycharm', 'vscode', 'cursor', 'trae', 'git', 'node', 'go', 'rust', 'webstorm', 'matlab', 'anaconda', 'jupyter', 'mysql', 'postgresql', 'neo4j', 'redis', 'elasticsearch', 'mongodb', 'java', 'jdk', 'maven', 'gradle', 'docker', 'kubernetes']):
        categories['开发工具'].append(item['server_filename'])
    elif any(k in name for k in ['ollama', 'chatbox', 'lm-studio', 'aipc', 'qyueai', 'glm', 'chatglm', 'ima', 'flowy']):
        categories['AI工具'].append(item['server_filename'])
    elif any(k in name for k in ['chrome', 'firefox', 'edge', 'obsidian', 'notion', 'xmind', 'bookxnote', 'koodo', 'neatreader', 'typora']):
        categories['效率工具'].append(item['server_filename'])
    elif any(k in name for k in ['wechat', 'qq', 'dingtalk', 'lark', '飞书', '腾讯会议', 'zoom', 'discord', 'telegram']):
        categories['通讯协作'].append(item['server_filename'])
    elif any(k in name for k in ['bandicam', 'obs', 'screen', '录屏', '剪映', 'capcut', 'ffmpeg', 'potplayer', 'vlc']):
        categories['音视频工具'].append(item['server_filename'])
    elif any(k in name for k in ['clash', 'v2ray', 'shadowsocks', 'ssr', 'vpn', 'proxy']):
        categories['网络工具'].append(item['server_filename'])
    elif any(k in name for k in ['7z', 'winrar', 'bandizip', 'everything', 'snipaste', 'listary', 'wox', 'uTools', 'quicker']):
        categories['系统工具'].append(item['server_filename'])
    elif any(k in name for k in ['draw.io', 'figma', 'sketch', 'ps', 'photoshop', 'illustrator', 'xd']):
        categories['设计工具'].append(item['server_filename'])
    elif any(k in name for k in ['百度网盘', '阿里云盘', '夸克', '115', '天翼云']):
        categories['网盘工具'].append(item['server_filename'])
    else:
        categories['其他软件'].append(item['server_filename'])

# 显示分类
print(f'\n总计: {len(items)} 个安装包\n')
for cat, files in sorted(categories.items(), key=lambda x: -len(x[1])):
    print(f'\n📁 {cat} ({len(files)}个)')
    for f in files[:8]:
        print(f'   • {f}')
    if len(files) > 8:
        print(f'   ... 还有 {len(files)-8} 个')
