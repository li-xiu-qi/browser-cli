#!/usr/bin/env python3
"""
上传本地书籍到百度网盘
"""

import os
import sys
import requests
import json
from pathlib import Path
from typing import List, Tuple

# 配置
ACCESS_TOKEN = "123.fe97bdb74eb2238a360649ba4e640f3b.YCnmz8Y2wF3Egn4nxsFlhbG8p0A.xyMOUA"
BASE_DIR = "Areas/书籍/Library"

# 上传目标路径映射
TARGET_PATHS = {
    # Python类
    'python': '/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/',
    # 软件工程类
    '代码': '/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/',
    '编程': '/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/',
    '软件': '/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/',
    '架构': '/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/',
    '设计模式': '/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/',
    '测试': '/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/',
    '程序员': '/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/',
    # 粥左罗
    '粥左罗': '/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/',
    # 其他默认
    'default': '/我的资源/3-Resources-资源/领域-电子书/00-待分类/',
}

def get_target_path(filename: str) -> str:
    """根据文件名判断目标路径"""
    name_lower = filename.lower()

    # 检查关键词
    for keyword, path in TARGET_PATHS.items():
        if keyword != 'default' and keyword in name_lower:
            return path

    # Python相关
    if 'python' in name_lower:
        return TARGET_PATHS['python']

    return TARGET_PATHS['default']

def list_local_books() -> List[Tuple[str, str]]:
    """列出本地所有书籍文件"""
    books = []
    base_path = Path(BASE_DIR)

    if not base_path.exists():
        print(f"❌ 目录不存在: {base_path}")
        return books

    extensions = ['.pdf', '.epub', '.mobi', '.azw3']

    for ext in extensions:
        for file_path in base_path.glob(f'*{ext}'):
            target = get_target_path(file_path.name)
            books.append((str(file_path), target))

    return books

def ensure_dir_exists(path: str) -> bool:
    """确保网盘目录存在"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"

    # 检查目录是否存在
    params = {
        "method": "list",
        "access_token": ACCESS_TOKEN,
        "dir": path,
        "limit": 1
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
        if data.get("errno") == 0:
            return True  # 目录已存在
    except:
        pass

    # 创建目录
    create_params = {
        "method": "create",
        "access_token": ACCESS_TOKEN,
    }

    data = {
        "path": path,
        "size": 0,
        "isdir": 1,
        "rtype": 1
    }

    try:
        r = requests.post(url, params=create_params, data=data, timeout=30)
        result = r.json()
        if result.get("errno") == 0:
            print(f"  ✅ 创建目录: {path}")
            return True
        else:
            print(f"  ⚠️  创建目录失败: {result}")
            return False
    except Exception as e:
        print(f"  ❌ 创建目录出错: {e}")
        return False

def upload_file(local_path: str, remote_dir: str) -> bool:
    """上传单个文件到百度网盘"""
    filename = os.path.basename(local_path)
    file_size = os.path.getsize(local_path)

    print(f"  上传: {filename} ({file_size/1024/1024:.1f}MB)")

    # 注意：百度网盘API的文件上传需要预上传+分片上传，这里简化处理
    # 实际使用建议通过百度网盘客户端或网页版批量上传

    return True

def generate_upload_plan():
    """生成上传计划"""
    books = list_local_books()

    print("=" * 70)
    print("📚 本地书籍上传计划")
    print("=" * 70)

    # 按目标路径分组
    by_target = {}
    for local_path, target in books:
        if target not in by_target:
            by_target[target] = []
        by_target[target].append(local_path)

    # 显示计划
    for target, files in sorted(by_target.items()):
        print(f"\n📁 {target}")
        print("-" * 50)
        for f in files:
            size = os.path.getsize(f) / 1024 / 1024
            print(f"  • {os.path.basename(f)} ({size:.1f}MB)")

    print(f"\n{'=' * 70}")
    print(f"📊 总计: {len(books)} 本书")
    print(f"{'=' * 70}")

    return books, by_target

def main():
    books, by_target = generate_upload_plan()

    if not books:
        print("❌ 没有找到本地书籍")
        return

    print("\n⚠️  注意: 百度网盘API上传大文件较复杂")
    print("💡 建议使用以下方式上传:")
    print("   1. 在百度网盘网页版创建上述目录")
    print("   2. 使用百度网盘客户端批量拖拽上传")
    print("   3. 或使用命令行工具 baidupcs-go")

    # 生成本地上传脚本
    script_path = "upload_books_manual.sh"
    with open(script_path, "w", encoding="utf-8") as f:
        f.write("#!/bin/bash\n")
        f.write("# 本地书籍上传脚本\n\n")

        for target, files in sorted(by_target.items()):
            f.write(f"# {target}\n")
            for local_file in files:
                filename = os.path.basename(local_file)
                # 使用rsync或cp命令示例
                f.write(f'# cp "{local_file}" "{target}{filename}"\n')
            f.write("\n")

    print(f"\n📝 已生成参考脚本: {script_path}")

if __name__ == "__main__":
    main()
