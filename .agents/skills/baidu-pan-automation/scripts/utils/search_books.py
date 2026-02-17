#!/usr/bin/env python3
"""
搜索百度网盘中的电子书文件
支持格式：PDF, EPUB, MOBI, AZW3, TXT, DOCX
"""

import requests
import json
import os
import time
from collections import defaultdict

ACCESS_TOKEN = "123.fe97bdb74eb2238a360649ba4e640f3b.YCnmz8Y2wF3Egn4nxS-K8j4cR-yblsFlhbG8p0A.xyMOUA"

# 电子书格式
BOOK_EXTENSIONS = ['.pdf', '.epub', '.mobi', '.azw3', '.txt', '.docx', '.djvu']


def search_files(keyword, page=1, num=100):
    """搜索文件"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {
        "method": "search",
        "access_token": ACCESS_TOKEN,
        "key": keyword,
        "page": page,
        "num": num,
        "dir": "/"
    }

    try:
        r = requests.get(url, params=params, timeout=60)
        data = r.json()
        if data.get("errno") == 0:
            return data.get("list", [])
        else:
            print(f"搜索错误: {data}")
            return []
    except Exception as e:
        print(f"请求失败: {e}")
        return []


def list_dir(dir_path, num=1000):
    """列出目录内容"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {
        "method": "list",
        "access_token": ACCESS_TOKEN,
        "dir": dir_path,
        "num": num
    }

    try:
        r = requests.get(url, params=params, timeout=60)
        data = r.json()
        if data.get("errno") == 0:
            return data.get("list", [])
        else:
            return []
    except Exception as e:
        print(f"请求失败: {e}")
        return []


def is_book_file(filename):
    """检查是否为电子书文件"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in BOOK_EXTENSIONS


def get_file_size_str(size):
    """转换文件大小为人类可读格式"""
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size/1024:.1f}KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/1024/1024:.1f}MB"
    else:
        return f"{size/1024/1024/1024:.2f}GB"


def search_all_books():
    """搜索所有电子书"""
    print("=" * 70)
    print("正在搜索百度网盘中的电子书...")
    print("=" * 70)

    all_books = []

    # 按格式搜索
    for ext in BOOK_EXTENSIONS:
        print(f"\n搜索 *{ext} 文件...")
        # 去掉点号进行搜索
        keyword = ext[1:] if ext.startswith('.') else ext
        results = search_files(keyword)

        books = [f for f in results if is_book_file(f.get("server_filename", ""))]
        print(f"  找到 {len(books)} 个{ext}文件")
        all_books.extend(books)

        time.sleep(0.5)  # 避免请求过快

    return all_books


def analyze_books(books):
    """分析书籍分布情况"""
    if not books:
        print("\n没有找到电子书文件")
        return

    print("\n" + "=" * 70)
    print(f"共找到 {len(books)} 本电子书")
    print("=" * 70)

    # 按格式统计
    format_count = defaultdict(int)
    format_size = defaultdict(int)

    # 按目录统计
    dir_count = defaultdict(int)

    for book in books:
        filename = book.get("server_filename", "")
        ext = os.path.splitext(filename)[1].lower()
        size = book.get("size", 0)
        path = book.get("path", "")
        parent_dir = os.path.dirname(path)

        format_count[ext] += 1
        format_size[ext] += size
        dir_count[parent_dir] += 1

    # 打印格式统计
    print("\n📚 按格式分布:")
    print("-" * 50)
    for ext in sorted(format_count.keys()):
        count = format_count[ext]
        size = format_size[ext]
        print(f"  {ext:8s}: {count:4d} 本 ({get_file_size_str(size)})")

    # 打印目录分布
    print("\n📁 按目录分布 (Top 15):")
    print("-" * 50)
    sorted_dirs = sorted(dir_count.items(), key=lambda x: x[1], reverse=True)[:15]
    for dir_path, count in sorted_dirs:
        display_path = dir_path if len(dir_path) < 60 else "..." + dir_path[-57:]
        print(f"  {count:3d} 本 - {display_path}")

    # 列出所有书籍（前30本）
    print("\n📖 书籍列表 (前30本):")
    print("-" * 70)
    for i, book in enumerate(books[:30], 1):
        filename = book.get("server_filename", "")
        size = get_file_size_str(book.get("size", 0))
        print(f"  {i:2d}. {filename[:50]:50s} ({size})")

    if len(books) > 30:
        print(f"\n  ... 还有 {len(books) - 30} 本 ...")

    return format_count, dir_count


def main():
    books = search_all_books()

    # 去重
    unique_books = {b.get("fs_id"): b for b in books}.values()
    unique_books = list(unique_books)

    analyze_books(unique_books)

    print("\n" + "=" * 70)
    print("搜索完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
