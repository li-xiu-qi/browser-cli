#!/usr/bin/env python3
"""
分批上传本地电子书到百度网盘
使用: python upload_batch.py [批次号]
"""

import requests
import json
import os
import time
import sys
from pathlib import Path
from typing import TypedDict, List, Dict

# 加载token
def load_token() -> str:
    env_paths = [Path("Archives/2026-02-百度网盘自动化集成/.env")]
    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("BAIDU_PAN_ACCESS_TOKEN="):
                        return line.strip().split("=", 1)[1]
    return ""

ACCESS_TOKEN = load_token()
BASE_URL = "https://pan.baidu.com/rest/2.0/xpan/file"
LOCAL_LIBRARY = Path("Areas/书籍/Library")
BOOK_EXTENSIONS = {".pdf", ".epub", ".mobi", ".azw3"}

UPLOAD_MAPPING: Dict[str, str] = {
    "Python Web开发实战": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "Python工匠": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "Python设计模式": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "Python高性能编程": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "PYTHON与AI编程": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "Python与AI编程": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "AI辅助编程实战": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "Vibe Coding": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "代码整洁之道": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "代码精进之路": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "代码阅读": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "企业IT架构转型之道": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "凤凰架构": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "单元测试的艺术": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "架构整洁之道": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "架构真意": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "微服务架构设计模式": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "测试驱动开发": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "编程珠玑": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "程序之美": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "程序员修炼之道": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "程序员的底层思维": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "秒懂AI编程": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "软件架构": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "软件架构理论与实践": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "软件架构设计：大型网站技术架构与业务架构融合之道": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "软件测试的艺术": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "软件设计的哲学": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "设计模式之禅": "/我的资源/3-Resources-资源/领域-电子书/02-软件工程与代码质量/",
    "主角模式": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "从零开始做自媒体": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "打造个人IP": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "学会成长": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "学会写作": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "成事的时间管理": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "公众号运营实战手册": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
}

DEFAULT_TARGET = "/我的资源/3-Resources-资源/领域-电子书/00-待分类/"


def find_local_books():
    books = []
    if not LOCAL_LIBRARY.exists():
        return books

    for file_path in LOCAL_LIBRARY.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in BOOK_EXTENSIONS:
            filename_without_ext = file_path.stem
            target_dir = DEFAULT_TARGET
            for key, target in UPLOAD_MAPPING.items():
                if key in filename_without_ext:
                    target_dir = target
                    break
            books.append({
                "filename": file_path.name,
                "local_path": file_path,
                "target_dir": target_dir,
                "size": file_path.stat().st_size
            })
    return sorted(books, key=lambda x: x["size"])  # 按大小排序，小文件先传


def get_file_size(size):
    if size < 1024 * 1024:
        return f"{size/1024:.1f}KB"
    return f"{size/1024/1024:.1f}MB"


def create_directory(path: str) -> bool:
    url = f"{BASE_URL}"
    params = {
        "method": "create",
        "access_token": ACCESS_TOKEN,
        "path": path,
        "size": 0,
        "isdir": 1,
        "rtype": 1
    }
    try:
        r = requests.post(url, params=params, timeout=30)
        data = r.json()
        return data.get("errno") == 0 or data.get("errno") == -8
    except Exception as e:
        print(f"创建目录出错: {e}")
        return False


def upload_file(local_path: Path, remote_path: str) -> bool:
    url = f"{BASE_URL}"
    params = {
        "method": "upload",
        "access_token": ACCESS_TOKEN,
        "path": remote_path,
        "ondup": "overwrite"
    }
    try:
        with open(local_path, "rb") as f:
            files = {"file": (local_path.name, f)}
            r = requests.post(url, params=params, files=files, timeout=300)
        data = r.json()
        return data.get("errno") == 0
    except Exception as e:
        print(f"上传出错: {e}")
        return False


def main():
    books = find_local_books()
    if not books:
        print("没有找到书籍")
        return

    total = len(books)
    batch_size = 5  # 每批5本

    # 获取批次号
    if len(sys.argv) > 1:
        try:
            batch_num = int(sys.argv[1])
        except:
            batch_num = 1
    else:
        batch_num = 1

    start_idx = (batch_num - 1) * batch_size
    end_idx = min(start_idx + batch_size, total)

    if start_idx >= total:
        print(f"批次 {batch_num} 超出范围，总共只有 {total} 本书")
        return

    batch_books = books[start_idx:end_idx]

    print(f"=" * 70)
    print(f"上传第 {batch_num} 批 ({start_idx+1}-{end_idx} / {total})")
    print(f"=" * 70)

    success_count = 0
    for i, book in enumerate(batch_books, start_idx + 1):
        print(f"\n[{i}/{total}] {book['filename'][:40]} ({get_file_size(book['size'])})")

        if not create_directory(book["target_dir"]):
            print(f"  ❌ 创建目录失败")
            continue

        remote_path = f"{book['target_dir']}{book['filename']}"

        if upload_file(book["local_path"], remote_path):
            print(f"  ✅ 上传成功")
            success_count += 1
        else:
            print(f"  ❌ 上传失败")

        time.sleep(1)

    print(f"\n{'=' * 70}")
    print(f"本批完成: 成功 {success_count}/{len(batch_books)}")
    print(f"{'=' * 70}")

    if end_idx < total:
        print(f"\n还有 {total - end_idx} 本未上传")
        print(f"继续上传请运行: python upload_batch.py {batch_num + 1}")
    else:
        print("\n🎉 所有书籍上传完成！")


if __name__ == "__main__":
    main()
