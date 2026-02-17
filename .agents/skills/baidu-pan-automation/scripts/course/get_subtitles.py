#!/usr/bin/env python3
"""
获取百度网盘视频字幕脚本（增强版）
支持递归子目录处理，自动处理多层级课程结构

使用方式:
1. 直接运行（使用默认配置）: python get_subtitles.py
2. 指定课程路径: python get_subtitles.py --course-path "/我的资源/课程目录"
3. 指定输出目录: python get_subtitles.py --output-dir "custom_output"
"""

import requests
import json
import os
import time
import re
import sys
from pathlib import Path
from urllib.parse import quote

# 默认配置
ACCESS_TOKEN = "123.fe97bdb74eb2238a360649ba4e640f3b.YCnmz8Y2wF3Egn4nxS-K8j4cR-yblsFlhbG8p0A.xyMOUA"
BASE_DIR = "/我的资源/00-转存区域/03-软技能/黄执中-沟通表达课"

# 设置代理（如果需要）
PROXIES = {
    # "http": "http://127.0.0.1:7890",
    # "https": "http://127.0.0.1:7890",
}


def list_dir(dir_path):
    """列出目录内容"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {
        "method": "list",
        "access_token": ACCESS_TOKEN,
        "dir": dir_path,
        "num": 100
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, timeout=120, proxies=PROXIES)
            data = r.json()
            if data.get("errno") == 0:
                return data.get("list", [])
            else:
                print(f"    API 错误: {data}")
                return []
        except requests.exceptions.Timeout:
            print(f"    超时，重试 {attempt + 1}/{max_retries}...")
            time.sleep(5)
        except Exception as e:
            print(f"    请求失败: {e}")
            time.sleep(2)
    return []


def get_subtitle_m3u8(video_path):
    """获取视频字幕 M3U8"""
    url = "https://pan.baidu.com/rest/2.0/xpan/file"
    params = {
        "method": "streaming",
        "access_token": ACCESS_TOKEN,
        "path": video_path,
        "type": "M3U8_SUBTITLE_SRT"
    }
    headers = {
        "User-Agent": "xpanvideo;netdisk;iPhone13;ios-iphone;15.1;ts"
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=120, proxies=PROXIES)
            return r.text
        except requests.exceptions.Timeout:
            print(f"    获取字幕超时，重试 {attempt + 1}/{max_retries}...")
            time.sleep(5)
        except Exception as e:
            print(f"    获取字幕失败: {e}")
            time.sleep(2)
    return None


def download_srt(subtitle_m3u8, output_path):
    """从 M3U8 下载 SRT 字幕"""
    lines = subtitle_m3u8.strip().split('\n')
    srt_urls = [line.strip() for line in lines if line.strip() and not line.startswith('#')]

    if not srt_urls:
        return False

    try:
        r = requests.get(srt_urls[0], timeout=60, proxies=PROXIES)
        if r.status_code == 200:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(r.text)
            return True
    except Exception as e:
        print(f"    下载字幕失败: {e}")
    return False


def process_videos_recursive(course_path, subtitles_dir, prefix=""):
    """
    递归处理目录中的视频文件
    返回: (success_count, skip_count, total_count)
    """
    success_count = 0
    skip_count = 0
    total_count = 0

    # 获取当前目录内容
    items = list_dir(course_path)
    videos = [v for v in items if v.get("server_filename", "").endswith(".mp4")]
    subdirs = [v for v in items if v.get("isdir", 0) == 1]

    # 处理当前目录的视频
    for video in videos:
        total_count += 1
        name = video["server_filename"]
        path = video["path"]

        # 使用前缀避免文件名冲突
        safe_name = re.sub(r'[\\/*?:"<>|]', '_', name)[:80]
        if prefix:
            safe_name = f"{prefix}_{safe_name}"

        srt_path = os.path.join(subtitles_dir, safe_name.replace(".mp4", ".srt"))

        display_name = f"[{prefix}] {name[:40]}" if prefix else name[:50]
        print(f"📹 {display_name}")

        # 检查是否已存在
        if os.path.exists(srt_path):
            print(f"    ⏭️  已存在，跳过")
            skip_count += 1
            continue

        # 获取字幕
        subtitle_m3u8 = get_subtitle_m3u8(path)

        if subtitle_m3u8 and ("m3u8" in subtitle_m3u8.lower() or "#extm3u" in subtitle_m3u8.lower()):
            if download_srt(subtitle_m3u8, srt_path):
                print(f"    ✅ 字幕下载完成")
                success_count += 1
            else:
                print(f"    ❌ 下载字幕失败")
        else:
            print(f"    ❌ 无字幕或获取失败")

    # 递归处理子目录
    for subdir in subdirs:
        subdir_name = subdir["server_filename"]
        subdir_path = subdir["path"]

        # 跳过隐藏目录和特殊目录
        if subdir_name.startswith('.') or subdir_name in ['subtitles', 'transcripts']:
            continue

        print(f"\n📁 进入子目录: {subdir_name}")

        # 构建新的前缀，保留层级信息
        new_prefix = f"{prefix}_{subdir_name}" if prefix else subdir_name
        new_prefix = re.sub(r'[\\/*?:"<>|]', '_', new_prefix)[:50]

        sub_success, sub_skip, sub_total = process_videos_recursive(
            subdir_path, subtitles_dir, new_prefix
        )
        success_count += sub_success
        skip_count += sub_skip
        total_count += sub_total

    return success_count, skip_count, total_count


def main():
    """主函数 - 支持命令行参数"""
    import argparse

    parser = argparse.ArgumentParser(description='获取百度网盘视频字幕')
    parser.add_argument('--course-path', default=BASE_DIR, help='课程目录路径')
    parser.add_argument('--output-dir', default='subtitles', help='字幕输出目录')
    parser.add_argument('--token', default=ACCESS_TOKEN, help='百度网盘Access Token')

    args = parser.parse_args()

    course_path = args.course_path
    output_dir = args.output_dir

    # 更新全局token
    global ACCESS_TOKEN
    ACCESS_TOKEN = args.token

    print("=" * 70)
    print("百度网盘课程字幕获取工具（增强版）")
    print("=" * 70)
    print(f"课程路径: {course_path}")
    print(f"输出目录: {output_dir}")
    print("=" * 70)
    print()

    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)

    # 递归处理所有视频
    success, skip, total = process_videos_recursive(course_path, output_dir)

    print("\n" + "=" * 70)
    print("处理完成!")
    print(f"总视频数: {total}")
    print(f"新下载: {success}")
    print(f"已跳过: {skip}")
    print(f"字幕保存位置: {output_dir}/")
    print("=" * 70)


if __name__ == "__main__":
    main()
