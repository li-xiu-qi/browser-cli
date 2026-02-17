#!/usr/bin/env python3
"""
YouTube/视频站点下载器
基于 awesome-claude-skills/video-downloader 改编
"""

import argparse
import sys
import subprocess
import json
import os
from pathlib import Path


DEFAULT_OUTPUT = "resources/downloads/media"


def check_yt_dlp():
    """检查 yt-dlp 是否已安装，如未安装则自动安装。"""
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("yt-dlp 未安装，正在安装...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                check=True
            )
            print("✅ yt-dlp 安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 安装失败: {e}")
            print("请手动运行: pip install -U yt-dlp")
            return False


def get_video_info(url):
    """获取视频信息（不下载）。"""
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-playlist", url],
        capture_output=True,
        text=True,
        check=True
    )
    return json.loads(result.stdout)


def download_video(url, output_path=DEFAULT_OUTPUT, quality="best", 
                   format_type="mp4", audio_only=False):
    """
    下载视频。
    
    Args:
        url: 视频 URL
        output_path: 保存目录
        quality: 质量 (best, 1080p, 720p, 480p, 360p, worst)
        format_type: 格式 (mp4, webm, mkv)
        audio_only: 仅下载音频
    """
    if not check_yt_dlp():
        return False
    
    # 确保输出目录存在
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 构建命令
    cmd = ["yt-dlp"]
    
    if audio_only:
        cmd.extend([
            "-x",  # 提取音频
            "--audio-format", "mp3",
            "--audio-quality", "0",  # 最佳质量
        ])
    else:
        # 视频质量设置
        if quality == "best":
            format_string = "bestvideo+bestaudio/best"
        elif quality == "worst":
            format_string = "worstvideo+worstaudio/worst"
        else:
            # 指定分辨率
            height = quality.replace("p", "")
            format_string = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
        
        cmd.extend([
            "-f", format_string,
            "--merge-output-format", format_type,
        ])
    
    # 输出模板
    cmd.extend([
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        "--no-playlist",  # 默认不下载播放列表
    ])
    
    cmd.append(url)
    
    print(f"📥 下载: {url}")
    print(f"   质量: {quality}")
    print(f"   格式: {'MP3 (仅音频)' if audio_only else format_type}")
    print(f"   保存: {output_dir}\n")
    
    try:
        # 先获取视频信息
        info = get_video_info(url)
        print(f"📺 {info.get('title', '未知标题')}")
        duration = info.get('duration', 0)
        if duration:
            print(f"   时长: {duration // 60}:{duration % 60:02d}")
        print(f"   作者: {info.get('uploader', '未知')}\n")
        
        # 下载
        subprocess.run(cmd, check=True)
        print(f"\n✅ 下载完成!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 下载失败: {e}")
        return False
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="下载 YouTube 及其他站点视频"
    )
    parser.add_argument("url", help="视频 URL")
    parser.add_argument(
        "-o", "--output",
        default=DEFAULT_OUTPUT,
        help=f"输出目录 (默认: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "-q", "--quality",
        default="best",
        choices=["best", "1080p", "720p", "480p", "360p", "worst"],
        help="视频质量 (默认: best)"
    )
    parser.add_argument(
        "-f", "--format",
        default="mp4",
        choices=["mp4", "webm", "mkv"],
        help="视频格式 (默认: mp4)"
    )
    parser.add_argument(
        "-a", "--audio-only",
        action="store_true",
        help="仅下载音频 (MP3)"
    )
    
    args = parser.parse_args()
    
    success = download_video(
        url=args.url,
        output_path=args.output,
        quality=args.quality,
        format_type=args.format,
        audio_only=args.audio_only
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
