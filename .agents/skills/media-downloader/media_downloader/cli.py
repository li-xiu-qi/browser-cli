#!/usr/bin/env python3
"""
Media Downloader CLI
智能媒体下载器命令行工具
"""
import sys
import argparse
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from media_downloader.core import SearchEngine, DownloadManager, MetadataManager, VideoProcessor
from media_downloader.utils import Config, format_results_table, format_status


def cmd_search(args):
    """搜索媒体"""
    print(f"🔍 搜索: {args.query}\n")
    
    engine = SearchEngine()
    providers = args.providers.split(',') if args.providers else None
    
    if args.type in ['image', 'all']:
        print("📷 搜索图片...")
        images = engine.search_images(
            args.query, 
            count=args.count,
            providers=providers
        )
        
        if images:
            print(f"\n找到 {len(images)} 张图片:\n")
            for i, img in enumerate(images[:args.count], 1):
                print(f"  {i}. [{img.provider:8}] {img.alt or img.title or 'N/A'[:40]}")
                print(f"     作者: {img.author or 'Unknown'} | 尺寸: {img.width}x{img.height}")
        else:
            print("  未找到图片")
    
    if args.type in ['video', 'all']:
        print("\n🎬 搜索视频...")
        videos = engine.search_videos(
            args.query,
            count=args.count,
            providers=providers
        )
        
        if videos:
            print(f"\n找到 {len(videos)} 个视频:\n")
            for i, vid in enumerate(videos[:args.count], 1):
                print(f"  {i}. [{vid.provider:8}] {vid.duration}s | 尺寸: {vid.width}x{vid.height}")
        else:
            print("  未找到视频")
        
        # YouTube
        print("\n📺 搜索 YouTube...")
        youtube = engine.search_youtube(args.query, count=args.count)
        if youtube:
            print(f"\n找到 {len(youtube)} 个 YouTube 视频:\n")
            for i, vid in enumerate(youtube[:args.count], 1):
                duration = vid.get('duration', 0)
                mins, secs = divmod(duration, 60) if duration else (0, 0)
                print(f"  {i}. {vid['title'][:50]}...")
                print(f"     时长: {mins}:{secs:02d} | 频道: {vid.get('channel', 'Unknown')}")
                print(f"     链接: {vid['url']}")
        else:
            print("  未找到 YouTube 视频")
    
    return 0


def cmd_image(args):
    """下载图片"""
    print(f"🔍 搜索图片: {args.query}\n")
    
    engine = SearchEngine()
    images = engine.search_images(args.query, count=args.count * 2)
    
    if not images:
        print("❌ 未找到图片")
        print("提示: 检查 API Key 配置 (.env 文件)")
        return 1
    
    print(f"✅ 找到 {len(images)} 张图片\n")
    
    # 下载
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    downloader = DownloadManager(output_dir=output_dir)
    metadata_mgr = MetadataManager(output_dir=output_dir)
    
    downloaded = 0
    for i, img in enumerate(images[:args.count], 1):
        print(f"[{i}/{args.count}]")
        
        filepath = downloader.download(img)
        if filepath:
            # 创建元数据
            metadata_mgr.create_sidecar(img, filepath)
            downloaded += 1
    
    print(f"\n✅ 下载完成: {downloaded}/{args.count} 张图片")
    print(f"📁 保存位置: {output_dir}")
    return 0


def cmd_video(args):
    """下载视频素材"""
    print(f"🔍 搜索视频: {args.query}\n")
    
    engine = SearchEngine()
    videos = engine.search_videos(
        args.query, 
        count=args.count,
    )
    
    if not videos:
        print("❌ 未找到视频")
        return 1
    
    print(f"✅ 找到 {len(videos)} 个视频\n")
    
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    downloader = DownloadManager(output_dir=output_dir)
    metadata_mgr = MetadataManager(output_dir=output_dir)
    
    downloaded = 0
    for i, vid in enumerate(videos[:args.count], 1):
        print(f"[{i}/{args.count}]")
        
        filepath = downloader.download(vid)
        if filepath:
            # 如果需要剪辑
            if args.duration and vid.duration and vid.duration > args.duration:
                processor = VideoProcessor(output_dir=output_dir)
                filepath = processor.trim_video(
                    filepath, 
                    duration=args.duration
                )
            
            if filepath:
                metadata_mgr.create_sidecar(vid, filepath)
                downloaded += 1
    
    print(f"\n✅ 下载完成: {downloaded}/{args.count} 个视频")
    print(f"📁 保存位置: {output_dir}")
    return 0


def cmd_youtube(args):
    """下载 YouTube 视频"""
    processor = VideoProcessor()
    
    if not processor.ytdlp_available:
        print("❌ 需要安装 yt-dlp: pip install yt-dlp")
        return 1
    
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    processor.output_dir = output_dir
    
    filepath = processor.download_youtube(
        args.url,
        audio_only=args.audio_only,
        start_time=args.start,
        end_time=args.end
    )
    
    if filepath:
        print(f"\n📁 保存位置: {filepath}")
        return 0
    return 1


def cmd_trim(args):
    """剪辑视频"""
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 文件不存在: {input_path}")
        return 1
    
    processor = VideoProcessor()
    
    if not processor.ffmpeg_available:
        print("❌ 需要安装 ffmpeg")
        return 1
    
    output_path = Path(args.output) if args.output else None
    
    result = processor.trim_video(
        input_path,
        start=args.start,
        end=args.end,
        duration=args.duration,
        output_path=output_path
    )
    
    if result:
        print(f"\n📁 输出文件: {result}")
        return 0
    return 1


def cmd_status(args):
    """检查配置状态"""
    config = Config()
    status = config.get_status()
    
    print(format_status(status))
    
    # 显示详细配置
    print("\n📂 目录:")
    for name, path in status['directories'].items():
        print(f"  {name:12}: {path}")
    
    # 提示
    if not any(status['api_keys'].values()):
        print("\n💡 提示: 编辑 .env 文件配置 API Key 以启用图片搜索")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Media Downloader - 智能媒体下载器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 搜索图片
  python -m media_downloader search "nature" -t image
  
  # 下载图片
  python -m media_downloader image "cats" -n 5
  
  # 下载视频素材
  python -m media_downloader video "ocean" -n 3 -d 30
  
  # 下载 YouTube
  python -m media_downloader youtube "https://youtube.com/watch?v=xxx" -s 60 -e 120
  
  # 剪辑视频
  python -m media_downloader trim video.mp4 -s 10 -e 30
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # search 命令
    search_parser = subparsers.add_parser('search', help='搜索媒体')
    search_parser.add_argument('query', help='搜索关键词')
    search_parser.add_argument('-t', '--type', choices=['image', 'video', 'all'], 
                               default='all', help='媒体类型')
    search_parser.add_argument('-n', '--count', type=int, default=5, help='结果数量')
    search_parser.add_argument('-p', '--providers', help='提供商列表，逗号分隔 (pexels,unsplash,pixabay)')
    search_parser.set_defaults(func=cmd_search)
    
    # image 命令
    image_parser = subparsers.add_parser('image', help='下载图片')
    image_parser.add_argument('query', help='搜索关键词')
    image_parser.add_argument('-n', '--count', type=int, default=5, help='下载数量')
    image_parser.add_argument('-o', '--output', default='downloads', help='输出目录')
    image_parser.set_defaults(func=cmd_image)
    
    # video 命令
    video_parser = subparsers.add_parser('video', help='下载视频素材')
    video_parser.add_argument('query', help='搜索关键词')
    video_parser.add_argument('-n', '--count', type=int, default=3, help='下载数量')
    video_parser.add_argument('-d', '--duration', type=int, help='目标时长(秒)，超过则剪辑')
    video_parser.add_argument('-o', '--output', default='downloads', help='输出目录')
    video_parser.set_defaults(func=cmd_video)
    
    # youtube 命令
    youtube_parser = subparsers.add_parser('youtube', help='下载 YouTube 视频')
    youtube_parser.add_argument('url', help='YouTube URL')
    youtube_parser.add_argument('-s', '--start', type=float, help='开始时间(秒)')
    youtube_parser.add_argument('-e', '--end', type=float, help='结束时间(秒)')
    youtube_parser.add_argument('-a', '--audio-only', action='store_true', help='仅下载音频')
    youtube_parser.add_argument('-o', '--output', default='downloads', help='输出目录')
    youtube_parser.set_defaults(func=cmd_youtube)
    
    # trim 命令
    trim_parser = subparsers.add_parser('trim', help='剪辑视频')
    trim_parser.add_argument('input', help='输入文件')
    trim_parser.add_argument('-s', '--start', type=float, help='开始时间(秒)')
    trim_parser.add_argument('-e', '--end', type=float, help='结束时间(秒)')
    trim_parser.add_argument('-d', '--duration', type=float, help='目标时长(秒)')
    trim_parser.add_argument('-o', '--output', help='输出文件')
    trim_parser.set_defaults(func=cmd_trim)
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='检查配置状态')
    status_parser.set_defaults(func=cmd_status)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
