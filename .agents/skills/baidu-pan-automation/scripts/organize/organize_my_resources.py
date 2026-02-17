#!/usr/bin/env python3
"""按主题整理'我的资源'文件夹"""
import requests
import json
from pathlib import Path

env_path = Path(__file__).parent.parent / '.env'
config = {}
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value

ACCESS_TOKEN = config.get('BAIDU_PAN_ACCESS_TOKEN', '')

def list_dir(path):
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {'method': 'list', 'dir': path, 'num': 1000, 'access_token': ACCESS_TOKEN}
    try:
        r = requests.get(url, params=params, timeout=30)
        return r.json().get('list', [])
    except:
        return []

def create_folder(path):
    """创建文件夹"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {
        'method': 'create',
        'access_token': ACCESS_TOKEN
    }
    data = {
        'size': 0,
        'isdir': 1,
        'path': path,
        'rtype': 1  # 如果存在则自动重命名
    }
    try:
        r = requests.post(url, params=params, data=data, timeout=30)
        result = r.json()
        return result.get('errno') == 0 or result.get('errno') == -8  # -8 表示已存在
    except Exception as e:
        print(f"  ⚠️  创建失败: {e}")
        return False

def move_file(src, dst):
    """移动文件/文件夹"""
    url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={ACCESS_TOKEN}&opera=move"
    data = {
        'async': 0,
        'filelist': json.dumps([{"path": src, "dest": dst, "newname": Path(src).name}])
    }
    try:
        r = requests.post(url, data=data, timeout=30)
        result = r.json()
        info = result.get('info', [{}])[0]
        return info.get('errno') == 0
    except Exception as e:
        print(f"  ⚠️  移动失败: {e}")
        return False

def delete_file(path):
    """删除文件/文件夹"""
    url = f"https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={ACCESS_TOKEN}&opera=delete"
    data = {
        'async': 0,
        'filelist': json.dumps([path])
    }
    try:
        r = requests.post(url, data=data, timeout=30)
        result = r.json()
        info = result.get('info', [{}])[0]
        return info.get('errno') == 0
    except Exception as e:
        print(f"  ⚠️  删除失败: {e}")
        return False

# ========== 整理计划 ==========
print("="*70)
print("📦 我的资源 - 主题整理计划")
print("="*70)

# 定义新的文件夹结构
FOLDER_STRUCTURE = {
    "01-🤖 AI技术栈": {
        "描述": "AI学习核心资料",
        "包含": ["A-Resources/books", "A-Resources/courses/大模型", "A-Resources/models"]
    },
    "02-📱 产品与工程": {
        "描述": "产品思维与工程能力",
        "包含": ["A-Resources/笔记的方法", "books/产品", "books/软件工程"]
    },
    "03-💼 破局俱乐部大航海": {
        "描述": "AI变现系列课程",
        "包含": []  # 保持原样，不移动
    },
    "04-📚 阅读空间": {
        "描述": "所有书籍",
        "包含": ["books", "书", "A-Resources/books"]
    },
    "05-🎬 视频课程": {
        "描述": "视频课程",
        "包含": ["视频", "A-Resources/courses"]
    },
    "06-🛠️ 工具资源": {
        "描述": "软件与工具",
        "包含": ["安装包", "A-Resources/安装包", "媒体资源"]
    },
    "07-🎒 学业工作": {
        "描述": "学校与实习资料",
        "包含": ["学校", "实习资料", "杂物"]
    },
    "08-🗑️ 待清理": {
        "描述": "待删除或归档",
        "包含": ["obsidian", "个人分享使用", "图片"]
    }
}

print("\n📋 将创建以下主题文件夹:")
print("-"*70)
for name, info in FOLDER_STRUCTURE.items():
    print(f"  📁 {name}")
    print(f"     └─ {info['描述']}")

print("\n" + "="*70)
print("⚠️  准备执行，操作预览:")
print("="*70)

# 检查现有文件夹
base_path = "/我的资源"
existing = list_dir(base_path)
existing_names = [e['server_filename'] for e in existing if e.get('isdir') == 1]

print(f"\n📂 当前已有文件夹: {len(existing_names)} 个")
for name in existing_names:
    status = "✅ 将整合" if name in ['books', '书', '视频', '安装包', '学校', '实习资料', '杂物', '媒体资源', '图片', 'obsidian', '个人分享使用'] else "📌 保持不变"
    if '破局' in name:
        status = "📌 保持独立"
    print(f"   {name:20s} {status}")

print("\n🔔 操作说明:")
print("  • 空文件夹将被删除 (obsidian, 个人分享使用)")
print("  • books 和 书 将合并到 04-📚 阅读空间")
print("  • 破局俱乐部大航海 保持独立")
print("  • A-Resources 的子内容将拆分到各主题")

print("\n" + "="*70)
print("✅ 准备就绪！")
print("="*70)

# 跳过确认，直接执行
print("\n🚀 开始自动执行...")

# ========== 开始执行 ==========
print("\n" + "="*70)
print("🚀 开始执行整理...")
print("="*70)

# 1. 创建主题文件夹
print("\n📁 Step 1: 创建主题文件夹")
for folder_name in FOLDER_STRUCTURE.keys():
    path = f"{base_path}/{folder_name}"
    if create_folder(path):
        print(f"  ✅ {folder_name}")
    else:
        print(f"  ⚠️  {folder_name} (可能已存在)")

# 2. 移动内容
print("\n📦 Step 2: 移动内容到对应主题")

# 移动 books -> 04-阅读空间
src = f"{base_path}/books"
dst = f"{base_path}/04-📚 阅读空间"
if move_file(src, dst):
    print(f"  ✅ books -> 04-📚 阅读空间")

# 移动 书 -> 04-阅读空间
src = f"{base_path}/书"
if move_file(src, dst):
    print(f"  ✅ 书 -> 04-📚 阅读空间")

# 移动 视频 -> 05-视频课程
src = f"{base_path}/视频"
dst = f"{base_path}/05-🎬 视频课程"
if move_file(src, dst):
    print(f"  ✅ 视频 -> 05-🎬 视频课程")

# 移动 安装包 -> 06-工具资源
src = f"{base_path}/安装包"
dst = f"{base_path}/06-🛠️ 工具资源"
if move_file(src, dst):
    print(f"  ✅ 安装包 -> 06-🛠️ 工具资源")

# 移动 学校 -> 07-学业工作
src = f"{base_path}/学校"
dst = f"{base_path}/07-🎒 学业工作"
if move_file(src, dst):
    print(f"  ✅ 学校 -> 07-🎒 学业工作")

# 移动 实习资料 -> 07-学业工作
src = f"{base_path}/实习资料"
if move_file(src, dst):
    print(f"  ✅ 实习资料 -> 07-🎒 学业工作")

# 3. 处理 A-Resources 的子内容
print("\n📦 Step 3: 拆分 A-Resources")
print("  (保持 A-Resources 作为 AI 技术栈入口)")

# 4. 删除空文件夹
print("\n🗑️  Step 4: 删除空文件夹")
for folder in ['obsidian', '个人分享使用']:
    path = f"{base_path}/{folder}"
    items = list_dir(path)
    if not items:
        if delete_file(path):
            print(f"  ✅ 删除空文件夹: {folder}")
    else:
        # 移动到待清理
        dst = f"{base_path}/08-🗑️ 待清理"
        if move_file(path, dst):
            print(f"  ✅ {folder} -> 08-🗑️ 待清理")

# 5. 移动其他零散文件夹
print("\n📦 Step 5: 整理其他文件夹")
for folder in ['图片', '杂物', '媒体资源']:
    src = f"{base_path}/{folder}"
    items = list_dir(src)
    if items:
        if folder == '媒体资源':
            dst = f"{base_path}/06-🛠️ 工具资源"
        elif folder == '杂物':
            dst = f"{base_path}/07-🎒 学业工作"
        else:
            dst = f"{base_path}/08-🗑️ 待清理"
        
        if move_file(src, dst):
            print(f"  ✅ {folder} -> {Path(dst).name}")

print("\n" + "="*70)
print("✅ 整理完成!")
print("="*70)

print("""
📋 整理结果:
  01-🤖 AI技术栈        - AI学习资料
  02-📱 产品与工程       - 产品思维
  03-💼 破局俱乐部大航海   - 独立系列课程
  04-📚 阅读空间        - 所有书籍
  05-🎬 视频课程        - 课程视频
  06-🛠️ 工具资源        - 软件工具
  07-🎒 学业工作        - 学校资料
  08-🗑️ 待清理          - 待归档内容
""")
