#!/usr/bin/env python3
"""精细化重命名分类"""
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

BASE = "/我的资源/00-转存区域"

print("="*70)
print("🚀 精细化整理 - 创建细分分类")
print("="*70)

# 在01-AI课程下创建细分
print("\n📁 01-AI课程 - 细分子分类")
ai_subcats = [
    "01-AI基础与理论",
    "02-AI大模型实战", 
    "03-AI编程开发",
    "04-AI应用与变现",
    "05-AI绘画创作"
]

for cat in ai_subcats:
    path = f"{BASE}/01-AI课程/{cat}"
    if create_folder(path):
        print(f"  ✅ {cat}")
    else:
        print(f"  📌 {cat}")
    time.sleep(0.3)

# 移动AI课程到细分
print("\n📦 移动AI课程到细分分类")
ai_moves = [
    ("多模态论文", "01-AI基础与理论", None),
    ("314页：一站式科研指令手册.pdf", "01-AI基础与理论", None),
    ("百度百科三元组数据.7z", "01-AI基础与理论", None),
    
    ("大模型", "02-AI大模型实战", None),
    ("马士兵-AI大模型实战", "02-AI大模型实战", None),
    ("知乎知学堂AI大模型全栈工程师", "02-AI大模型实战", None),
    ("大数据大模型等课程", "02-AI大模型实战", None),
    ("大模型全栈正式课课件.rar", "02-AI大模型实战", None),
    
    ("ai编程—薛志荣", "03-AI编程开发", None),
    ("Transformers模型量化", "03-AI编程开发", None),
    
    ("破局俱乐部大航海", "04-AI应用与变现", None),
    ("AI自媒体运营课", "04-AI应用与变现", None),
    ("AI解决方案课程资料", "04-AI应用与变现", None),
    
    ("ai绘画", "05-AI绘画创作", None),
]

for item, cat, newname in ai_moves:
    src = f"{BASE}/01-AI课程/{item}"
    dest = f"{BASE}/01-AI课程/{cat}"
    success, info = move(src, dest, newname)
    if success:
        print(f"  ✅ {item[:30]:30s} → {cat}")
    else:
        errno = info.get('errno', 'unknown') if isinstance(info, dict) else 'unknown'
        if errno != -9:
            print(f"  ⚠️  {item[:30]:30s} (errno: {errno})")
    time.sleep(0.5)

# 技术工程细分
print("\n📁 02-技术工程 - 细分子分类")
tech_subcats = [
    "01-嵌入式开发",
    "02-电子仿真", 
    "03-工程设计",
    "04-控制系统"
]

for cat in tech_subcats:
    path = f"{BASE}/02-技术工程/{cat}"
    if create_folder(path):
        print(f"  ✅ {cat}")
    else:
        print(f"  📌 {cat}")
    time.sleep(0.3)

print("\n📦 移动技术工程到细分分类")
tech_moves = [
    ("51单片机入门教程资料", "01-嵌入式开发", None),
    ("STM32入门教程资料", "01-嵌入式开发", None),
    ("PLC", "01-嵌入式开发", None),
    
    ("Proteus-1", "02-电子仿真", None),
    ("Proteus-2", "02-电子仿真", None),
    
    ("CAD 2025", "03-工程设计", None),
    ("eplan2.7电气设计.zip", "03-工程设计", None),
    
    ("双容水箱液位控制系统", "04-控制系统", None),
]

for item, cat, newname in tech_moves:
    src = f"{BASE}/02-技术工程/{item}"
    dest = f"{BASE}/02-技术工程/{cat}"
    success, info = move(src, dest, newname)
    if success:
        print(f"  ✅ {item[:30]:30s} → {cat}")
    time.sleep(0.5)

# 软技能细分
print("\n📁 03-软技能 - 细分子分类")
skill_subcats = ["01-演讲与表达", "02-声乐艺术"]

for cat in skill_subcats:
    path = f"{BASE}/03-软技能/{cat}"
    if create_folder(path):
        print(f"  ✅ {cat}")
    else:
        print(f"  📌 {cat}")
    time.sleep(0.3)

print("\n📦 移动软技能到细分分类")
skill_moves = [
    ("21天演讲口才", "01-演讲与表达", None),
    ("演讲与口才课程", "01-演讲与表达", None),
    ("席瑞", "01-演讲与表达", None),
    
    ("唱歌", "02-声乐艺术", None),
    ("配音达人教程", "02-声乐艺术", None),
]

for item, cat, newname in skill_moves:
    src = f"{BASE}/03-软技能/{item}"
    dest = f"{BASE}/03-软技能/{cat}"
    success, info = move(src, dest, newname)
    if success:
        print(f"  ✅ {item[:30]:30s} → {cat}")
    time.sleep(0.5)

# 商业管理细分
print("\n📁 04-商业管理 - 细分子分类")
biz_subcats = ["01-MBA与商业", "02-个人品牌", "03-求职面试"]

for cat in biz_subcats:
    path = f"{BASE}/04-商业管理/{cat}"
    if create_folder(path):
        print(f"  ✅ {cat}")
    else:
        print(f"  📌 {cat}")
    time.sleep(0.3)

print("\n📦 移动商业管理到细分分类")
biz_moves = [
    ("MBA全套", "01-MBA与商业", None),
    ("胡说老王-商业本质", "01-MBA与商业", None),
    ("启点", "01-MBA与商业", None),
    
    ("刘思毅", "02-个人品牌", None),
    ("夏夏蓝青合集", "02-个人品牌", None),
    
    ("林木求职大礼包", "03-求职面试", None),
    ("求职面试", "03-求职面试", None),
]

for item, cat, newname in skill_moves:
    src = f"{BASE}/04-商业管理/{item}"
    dest = f"{BASE}/04-商业管理/{cat}"
    success, info = move(src, dest, newname)
    if success:
        print(f"  ✅ {item[:30]:30s} → {cat}")
    time.sleep(0.5)

print("\n" + "="*70)
print("✅ 精细化整理完成!")
print("="*70)
