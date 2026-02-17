#!/usr/bin/env python3
"""
百度网盘课程一键处理工具
支持递归子目录，自动获取字幕并转换为Markdown文稿

使用方式:
1. 处理默认课程: python process_course.py
2. 指定课程路径: python process_course.py --course-path "/我的资源/课程目录"
3. 完整参数: python process_course.py --course-path "/path" --course-name "课程名" --output-dir "output"
"""

import os
import sys
import argparse
from pathlib import Path

# 添加脚本所在目录到路径，以便导入其他模块
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from get_subtitles import process_videos_recursive, ACCESS_TOKEN as DEFAULT_TOKEN
from convert_srt_to_md import batch_convert


def process_course(course_path: str,
                   output_base_dir: str = 'output',
                   course_name: str = '',
                   access_token: str = '') -> dict:
    """
    一键处理课程：获取字幕并转换为Markdown

    Args:
        course_path: 百度网盘课程目录路径
        output_base_dir: 输出基础目录
        course_name: 课程名称（用于Markdown头部）
        access_token: 百度网盘Access Token

    Returns:
        处理结果统计
    """
    # 设置token
    if access_token:
        import get_subtitles
        get_subtitles.ACCESS_TOKEN = access_token

    # 构建输出目录
    output_path = Path(output_base_dir)
    subtitles_dir = output_path / 'subtitles'
    transcripts_dir = output_path / 'transcripts'

    print("=" * 70)
    print("百度网盘课程一键处理工具")
    print("=" * 70)
    print(f"课程路径: {course_path}")
    if course_name:
        print(f"课程名称: {course_name}")
    print(f"输出目录: {output_base_dir}")
    print("=" * 70)
    print()

    # 步骤1：获取字幕
    print("🎬 步骤 1/2: 获取视频字幕...")
    print("-" * 70)

    os.makedirs(subtitles_dir, exist_ok=True)
    success, skip, total = process_videos_recursive(course_path, str(subtitles_dir))

    print("\n" + "-" * 70)
    print(f"字幕获取完成: 总视频 {total}, 新下载 {success}, 已跳过 {skip}")
    print("-" * 70)
    print()

    # 步骤2：转换为Markdown
    print("📝 步骤 2/2: 转换字幕为Markdown文稿...")
    print("-" * 70)

    converted = batch_convert(str(subtitles_dir), str(transcripts_dir), course_name)

    # 返回统计
    return {
        'total_videos': total,
        'subtitles_downloaded': success,
        'subtitles_skipped': skip,
        'transcripts_converted': len(converted),
        'subtitles_dir': str(subtitles_dir),
        'transcripts_dir': str(transcripts_dir)
    }


def main():
    parser = argparse.ArgumentParser(
        description='百度网盘课程一键处理工具（字幕获取+文稿转换）'
    )
    parser.add_argument(
        '--course-path',
        default='/我的资源/00-转存区域/03-软技能/黄执中-沟通表达课',
        help='百度网盘课程目录路径'
    )
    parser.add_argument(
        '--course-name',
        default='',
        help='课程名称（用于Markdown文档头部）'
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='输出目录名称'
    )
    parser.add_argument(
        '--token',
        default=DEFAULT_TOKEN,
        help='百度网盘Access Token'
    )

    args = parser.parse_args()

    # 执行处理
    result = process_course(
        course_path=args.course_path,
        output_base_dir=args.output_dir,
        course_name=args.course_name,
        access_token=args.token
    )

    # 打印最终报告
    print("\n" + "=" * 70)
    print("✅ 全部处理完成!")
    print("=" * 70)
    print(f"📊 统计:")
    print(f"   - 总视频数: {result['total_videos']}")
    print(f"   - 字幕下载: {result['subtitles_downloaded']} 个")
    print(f"   - 字幕跳过: {result['subtitles_skipped']} 个")
    print(f"   - 文稿转换: {result['transcripts_converted']} 个")
    print()
    print(f"📁 输出位置:")
    print(f"   - 字幕文件: {result['subtitles_dir']}/")
    print(f"   - 文稿文件: {result['transcripts_dir']}/")
    print("=" * 70)


if __name__ == '__main__':
    main()
