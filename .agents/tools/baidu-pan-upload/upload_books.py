#!/usr/bin/env python3
"""
上传本地电子书到百度网盘
"""

import requests
import json
import os
import time
from pathlib import Path
from typing import TypedDict, List, Dict

# 配置 - 从环境变量或.env文件读取token
import os

def load_token() -> str:
    """加载百度网盘access token"""
    # 优先从环境变量读取
    token = os.getenv("BAIDU_PAN_ACCESS_TOKEN")
    if token:
        return token

    # 尝试从.env文件读取
    env_paths = [
        Path(".env"),
        Path("Archives/2026-02-百度网盘自动化集成/.env"),
        Path("../.env"),
        Path("../../.env"),
    ]

    for env_path in env_paths:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("BAIDU_PAN_ACCESS_TOKEN="):
                        return line.strip().split("=", 1)[1]

    # 默认token
    return "123.fe97bdb74eb2238a360649ba4e640f3b.YCnmz8Y2wF3Egn4nxS-K8j4cR-yblsFlhbG8p0A.xyMOUA"

ACCESS_TOKEN = load_token()
BASE_URL = "https://pan.baidu.com/rest/2.0/xpan/file"

# 本地书籍目录
LOCAL_LIBRARY = Path("Areas/书籍/Library")

# 上传目标映射
UPLOAD_MAPPING: Dict[str, str] = {
    # 01-编程开发/Python
    "Python Web开发实战": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "Python工匠": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "Python设计模式": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "Python高性能编程": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "PYTHON与AI编程": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",
    "Python与AI编程": "/我的资源/3-Resources-资源/领域-电子书/01-编程开发/Python/",

    # 02-软件工程与代码质量
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

    # 05-认知成长与软技能
    "主角模式": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "从零开始做自媒体": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "打造个人IP": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "学会成长": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "学会写作": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "成事的时间管理": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
    "公众号运营实战手册": "/我的资源/3-Resources-资源/领域-电子书/05-认知成长与软技能/",
}

# 未匹配的书放到00-待分类
DEFAULT_TARGET = "/我的资源/3-Resources-资源/领域-电子书/00-待分类/"

BOOK_EXTENSIONS = {".pdf", ".epub", ".mobi", ".azw3"}


class BookInfo(TypedDict):
    filename: str
    local_path: Path
    target_dir: str
    size: int


def get_file_size(size: int) -> str:
    if size < 1024 * 1024:
        return f"{size/1024:.1f}KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size/1024/1024:.1f}MB"
    else:
        return f"{size/1024/1024/1024:.2f}GB"


def find_local_books() -> List[BookInfo]:
    books = []

    if not LOCAL_LIBRARY.exists():
        print(f"目录不存在: {LOCAL_LIBRARY}")
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

    return books


def check_token() -> bool:
    """检查token是否有效"""
    url = f"{BASE_URL}"
    params = {
        "method": "list",
        "access_token": ACCESS_TOKEN,
        "dir": "/",
        "num": 10
    }

    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
        if data.get("errno") == 0:
            print("Token有效")
            return True
        else:
            print(f"Token无效: {data}")
            return False
    except Exception as e:
        print(f"检查token出错: {e}")
        return False


def create_directory(path: str) -> bool:
    """在网盘上创建目录"""
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
        if data.get("errno") == 0 or data.get("errno") == -8:
            return True
        else:
            print(f"  创建目录失败: {data}")
            return False
    except Exception as e:
        print(f"  创建目录出错: {e}")
        return False


def upload_file(local_path: Path, remote_path: str) -> bool:
    """上传文件到百度网盘"""
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
        if data.get("errno") == 0:
            return True
        else:
            print(f"  上传失败: errno={data.get('errno')}, {data.get('errmsg', '')}")
            return False
    except Exception as e:
        print(f"  上传出错: {e}")
        return False


def display_books(books: List[BookInfo]) -> Dict[str, List[BookInfo]]:
    """显示书籍清单，返回分组结果"""
    if not books:
        print("没有找到需要上传的书籍")
        return {}

    print(f"\n共找到 {len(books)} 本书籍")
    print("=" * 70)

    # 按目标目录分组显示
    by_target: Dict[str, List[BookInfo]] = {}
    for book in books:
        target = book["target_dir"]
        if target not in by_target:
            by_target[target] = []
        by_target[target].append(book)

    for target, book_list in sorted(by_target.items()):
        print(f"\n{target} ({len(book_list)}本)")
        for book in book_list:
            print(f"  • {book['filename'][:50]} ({get_file_size(book['size'])})")

    return by_target


def upload_books(books: List[BookInfo], auto_confirm: bool = False) -> None:
    if not books:
        print("没有找到需要上传的书籍")
        return

    by_target = display_books(books)

    print("\n" + "=" * 70)

    if not auto_confirm:
        confirm = input("\n确认上传以上书籍到百度网盘? (yes/no): ")
        if confirm.lower() not in ("yes", "y"):
            print("已取消上传")
            return

    print("\n" + "=" * 70)
    print("开始上传...")
    print("=" * 70)

    success_count = 0
    fail_count = 0

    for i, book in enumerate(books, 1):
        print(f"\n[{i}/{len(books)}] {book['filename'][:40]}")

        if not create_directory(book["target_dir"]):
            print(f"  创建目录失败，跳过")
            fail_count += 1
            continue

        remote_path = f"{book['target_dir']}{book['filename']}"

        if upload_file(book["local_path"], remote_path):
            print(f"  上传成功")
            success_count += 1
        else:
            print(f"  上传失败")
            fail_count += 1

        time.sleep(0.5)

    print("\n" + "=" * 70)
    print(f"上传完成: 成功 {success_count} 本, 失败 {fail_count} 本")
    print("=" * 70)


def main():
    import sys

    print("=" * 70)
    print("本地电子书上传工具")
    print("=" * 70)

    # 解析简单参数
    auto_confirm = "--yes" in sys.argv or "-y" in sys.argv
    dry_run = "--list" in sys.argv or "-l" in sys.argv

    if not check_token():
        print("\nToken无效，请更新ACCESS_TOKEN")
        print("获取方式: https://pan.baidu.com/union/doc/0ksg0sbig")
        return

    books = find_local_books()

    if dry_run:
        display_books(books)
        print("\n(--list 模式: 仅显示清单，未执行上传)")
        return

    upload_books(books, auto_confirm=auto_confirm)


if __name__ == "__main__":
    main()
