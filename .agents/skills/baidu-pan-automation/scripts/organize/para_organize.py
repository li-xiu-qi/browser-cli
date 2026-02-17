#!/usr/bin/env python3
"""按照PARA方法重新整理我的资源"""
import requests
import json
from pathlib import Path
import time

env_path = Path(__file__).parent.parent / '.env'
config = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

ACCESS_TOKEN = config.get('BAIDU_PAN_ACCESS_TOKEN', '')

def create_folder(path):
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {'method': 'create', 'access_token': ACCESS_TOKEN}
    data = {'size': 0, 'isdir': 1, 'path': path, 'rtype': 1}
    try:
        r = requests.post(url, params=params, data=data, timeout=30)
        result = r.json()
        return result.get('errno') == 0 or result.get('errno') == -8
    except:
        return False

def move(src, dest, newname=None):
    if newname is None:
        newname = Path(src).name
    url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={ACCESS_TOKEN}&opera=move"
    data = {'async': 0, 'filelist': json.dumps([{'path': src, 'dest': dest, 'newname': newname}])}
    try:
        r = requests.post(url, data=data, timeout=30)
        result = r.json()
        info = result.get('info', [{}])[0] if result.get('info') else {}
        return info.get('errno') == 0, info
    except:
        return False, {}

def rename(src, newname):
    url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={ACCESS_TOKEN}&opera=rename"
    data = {'async': 0, 'filelist': json.dumps([{'path': src, 'newname': newname}])}
    try:
        r = requests.post(url, data=data, timeout=30)
        result = r.json()
        info = result.get('info', [{}])[0] if result.get('info') else {}
        return info.get('errno') == 0, info
    except:
        return False, {}

BASE = "/我的资源"

print("="*70)
print("🚀 PARA方法整理 - 创建一级分类")
print("="*70)

# 创建PARA一级分类
para_folders = [
    "1-Projects-项目",       # 当前进行中的项目
    "2-Areas-领域",          # 持续维护的领域
    "3-Resources-资源",      # 参考材料
    "4-Archives-归档",       # 已完成/过期
]

for folder in para_folders:
    path = f"{BASE}/{folder}"
    if create_folder(path):
        print(f"  ✅ {folder}")
    else:
        print(f"  📌 {folder}")
    time.sleep(0.3)

print("\n" + "="*70)
print("📦 移动文件夹到PARA分类")
print("="*70)

# 定义移动规则 (原位置, PARA分类, 新名称)
move_rules = [
    # === Projects - 当前进行的项目 ===
    ("01-AI资源总库/课程-AI", "1-Projects-项目", "项目-AI课程学习"),
    ("01-AI资源总库/AI-模型", "1-Projects-项目", "项目-AI模型部署"),
    ("01-AI资源总库/方法论-笔记", "1-Projects-项目", "项目-笔记方法论实践"),
    
    # === Areas - 持续维护的领域 ===
    ("04-技术书籍", "2-Areas-领域", "领域-技术阅读"),
    ("04-阅读清单", "2-Areas-领域", "领域-阅读管理"),
    ("01-AI资源总库/AI-Obsidian模板", "2-Areas-领域", "领域-知识管理"),
    ("05-媒体资源", "2-Areas-领域", "领域-媒体素材"),
    ("09-图片", "2-Areas-领域", "领域-图片库"),
    
    # === Resources - 参考资源 ===
    ("01-AI资源总库/AI-配置", "3-Resources-资源", "资源-AI配置"),
    ("01-AI资源总库/AI-Docker", "3-Resources-资源", "资源-AI-Docker"),
    ("01-AI资源总库/工具-drawio", "3-Resources-资源", "资源-绘图工具"),
    ("01-AI资源总库/工具-SpaceSniffer", "3-Resources-资源", "资源-磁盘分析工具"),
    ("01-AI资源总库/工具-浏览器扩展", "3-Resources-资源", "资源-浏览器扩展"),
    ("06-软件工具", "3-Resources-资源", "资源-软件工具库"),
    ("07-学校资料", "3-Resources-资源", "资源-学校资料"),
    
    # === Archives - 归档 ===
    ("08-实习资料", "4-Archives-归档", "归档-实习资料"),
    ("08-杂物", "4-Archives-归档", "归档-杂物"),
    ("99-临时文件", "4-Archives-归档", "归档-临时文件"),
]

success_count = 0
for src_rel, para_cat, new_name in move_rules:
    src = f"{BASE}/{src_rel}"
    dest = f"{BASE}/{para_cat}"
    
    success, info = move(src, dest, new_name)
    if success:
        print(f"  ✅ {new_name}")
        success_count += 1
    else:
        errno = info.get('errno', 'unknown') if isinstance(info, dict) else 'unknown'
        if errno != -9:  # -9表示源不存在
            print(f"  ⚠️  {src_rel}: errno={errno}")
    time.sleep(0.5)

print(f"\n📊 移动完成: {success_count}/{len(move_rules)}")

print("\n" + "="*70)
print("📁 整理AI资源总库的其他内容")
print("="*70)

# 将其他-books等资源移动到Resources
other_moves = [
    ("01-AI资源总库/其他-books", "3-Resources-资源", "资源-AI相关书籍"),
    ("01-AI资源总库/其他-数据集", "3-Resources-资源", "资源-数据集"),
    ("01-AI资源总库/其他-极客时间", "3-Resources-资源", "资源-极客时间"),
    ("01-AI资源总库/其他-职业认证", "3-Resources-资源", "资源-职业认证"),
    ("01-AI资源总库/其他-重要文件", "3-Resources-资源", "资源-重要文件备份"),
    ("01-AI资源总库/其他-文学创作", "4-Archives-归档", "归档-文学创作"),
    ("01-AI资源总库/其他-图片", "4-Archives-归档", "归档-AI图片"),
    ("01-AI资源总库/其他-文件", "4-Archives-归档", "归档-AI文件"),
    ("01-AI资源总库/其他-安装包", "3-Resources-资源", "资源-安装包"),
]

for src_rel, para_cat, new_name in other_moves:
    src = f"{BASE}/{src_rel}"
    dest = f"{BASE}/{para_cat}"
    
    success, info = move(src, dest, new_name)
    if success:
        print(f"  ✅ {new_name}")
    else:
        errno = info.get('errno', 'unknown') if isinstance(info, dict) else 'unknown'
        if errno != -9:
            print(f"  ⚠️  {src_rel}: errno={errno}")
    time.sleep(0.5)

print("\n" + "="*70)
print("✅ PARA整理第一阶段完成!")
print("="*70)
