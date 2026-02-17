#!/usr/bin/env python3
"""
音视频转录文稿统一入口

自动根据文件大小、时长和平台限制选择最优方案：
- 视频 > 4GB 或 > 4小时 → 通义听悟
- 音频 > 500MB → 百度网盘
- 文件已在网盘 → 百度网盘
- 本地文件 → 通义听悟（一键上传）
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# 平台限制常量
BAIDU_VIDEO_MAX = 4 * 1024 * 1024 * 1024  # 4GB
BAIDU_AUDIO_MAX = 4 * 1024 * 1024 * 1024  # 4GB
BAIDU_DURATION_MAX = 4 * 3600  # 4小时

TONGYI_VIDEO_MAX = 6 * 1024 * 1024 * 1024  # 6GB
TONGYI_AUDIO_MAX = 500 * 1024 * 1024  # 500MB
TONGYI_DURATION_MAX = 6 * 3600  # 6小时


def get_file_info(file_path: str) -> dict:
    """获取文件信息（大小、时长等）."""
    info = {
        "path": file_path,
        "exists": False,
        "size": 0,
        "duration": 0,
        "is_video": False,
        "is_audio": False,
        "extension": "",
    }
    
    if not os.path.exists(file_path):
        return info
    
    info["exists"] = True
    info["size"] = os.path.getsize(file_path)
    info["extension"] = Path(file_path).suffix.lower()
    
    # 判断文件类型
    video_exts = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.m4v', '.flv', '.webm', '.mpeg', '.3gp', '.ogg', '.rmvb']
    audio_exts = ['.mp3', '.wav', '.m4a', '.aac', '.wma', '.ogg', '.amr', '.flac', '.aiff']
    
    if info["extension"] in video_exts:
        info["is_video"] = True
    elif info["extension"] in audio_exts:
        info["is_audio"] = True
    
    # 尝试获取视频时长（如果有 ffprobe）
    try:
        import subprocess
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            info["duration"] = float(result.stdout.strip())
    except:
        pass
    
    return info


def analyze_file(file_info: dict) -> dict:
    """分析文件适合哪个平台."""
    size = file_info["size"]
    duration = file_info["duration"]
    is_video = file_info["is_video"]
    is_audio = file_info["is_audio"]
    
    result = {
        "baidu_eligible": False,
        "tongyi_eligible": False,
        "recommended": None,
        "reasons": []
    }
    
    # 检查百度网盘
    if is_video:
        if size <= BAIDU_VIDEO_MAX and duration <= BAIDU_DURATION_MAX:
            result["baidu_eligible"] = True
        else:
            if size > BAIDU_VIDEO_MAX:
                result["reasons"].append(f"视频大小 {size/1024/1024/1024:.2f}GB > 百度限制 4GB")
            if duration > BAIDU_DURATION_MAX:
                result["reasons"].append(f"视频时长 {duration/3600:.1f}小时 > 百度限制 4小时")
    elif is_audio:
        if size <= BAIDU_AUDIO_MAX and duration <= BAIDU_DURATION_MAX:
            result["baidu_eligible"] = True
        else:
            if size > BAIDU_AUDIO_MAX:
                result["reasons"].append(f"音频大小 {size/1024/1024/1024:.2f}GB > 百度限制 4GB")
    
    # 检查通义听悟
    if is_video:
        if size <= TONGYI_VIDEO_MAX and duration <= TONGYI_DURATION_MAX:
            result["tongyi_eligible"] = True
        else:
            if size > TONGYI_VIDEO_MAX:
                result["reasons"].append(f"视频大小 {size/1024/1024/1024:.2f}GB > 通义限制 6GB")
            if duration > TONGYI_DURATION_MAX:
                result["reasons"].append(f"视频时长 {duration/3600:.1f}小时 > 通义限制 6小时")
    elif is_audio:
        if size <= TONGYI_AUDIO_MAX and duration <= TONGYI_DURATION_MAX:
            result["tongyi_eligible"] = True
        else:
            if size > TONGYI_AUDIO_MAX:
                result["reasons"].append(f"音频大小 {size/1024/1024:.2f}MB > 通义限制 500MB")
    
    # 推荐平台
    if result["baidu_eligible"] and result["tongyi_eligible"]:
        # 两者都支持，推荐通义听悟（功能更强）
        result["recommended"] = "tongyi"
        result["reasons"].append("两个平台都支持，推荐通义听悟（功能更强）")
    elif result["tongyi_eligible"]:
        result["recommended"] = "tongyi"
    elif result["baidu_eligible"]:
        result["recommended"] = "baidu"
    else:
        result["recommended"] = None
    
    return result


def print_analysis(file_info: dict, analysis: dict):
    """打印文件分析结果."""
    # 文件信息表
    info_table = Table(title="文件信息", show_header=True)
    info_table.add_column("属性", style="cyan")
    info_table.add_column("值", style="green")
    
    info_table.add_row("文件名", Path(file_info["path"]).name)
    info_table.add_row("大小", f"{file_info['size'] / 1024 / 1024:.2f} MB")
    
    if file_info["duration"] > 0:
        hours = int(file_info["duration"] // 3600)
        minutes = int((file_info["duration"] % 3600) // 60)
        info_table.add_row("时长", f"{hours}小时{minutes}分钟")
    else:
        info_table.add_row("时长", "未知")
    
    info_table.add_row("类型", "视频" if file_info["is_video"] else "音频" if file_info["is_audio"] else "未知")
    
    console.print(info_table)
    
    # 平台支持情况
    support_table = Table(title="平台支持情况", show_header=True)
    support_table.add_column("平台", style="cyan")
    support_table.add_column("支持", style="green")
    support_table.add_column("限制", style="yellow")
    
    support_table.add_row(
        "百度网盘",
        "✅ 支持" if analysis["baidu_eligible"] else "❌ 不支持",
        "视频/音频 4GB，时长 4小时"
    )
    support_table.add_row(
        "通义听悟",
        "✅ 支持" if analysis["tongyi_eligible"] else "❌ 不支持",
        "视频 6GB/音频 500MB，时长 6小时"
    )
    
    console.print(support_table)
    
    # 推荐平台
    if analysis["recommended"]:
        provider_name = "通义听悟" if analysis["recommended"] == "tongyi" else "百度网盘"
        console.print(Panel(
            f"[bold green]推荐使用: {provider_name}[/bold green]\n" + 
            "\n".join([f"• {r}" for r in analysis["reasons"]]),
            title="推荐方案",
            border_style="green"
        ))
    else:
        console.print(Panel(
            "[bold red]文件超出两个平台的限制[/bold red]\n" +
            "\n".join([f"• {r}" for r in analysis["reasons"]]),
            title="无法处理",
            border_style="red"
        ))


def run_baidu_pan(file_path: str = None, fsid: str = None, output: str = None, 
                  upload_first: bool = False, wait_transcript: bool = False, **kwargs):
    """运行百度网盘转录."""
    console.print("[blue]使用百度网盘转录...[/blue]")
    
    script_dir = Path(__file__).parent / "baidu-pan"
    
    if fsid:
        # 已有文件ID，直接获取转录
        cmd = ["python", "transcribe.py", "--fsid", str(fsid)]
        if output:
            cmd.extend(["--output", output])
        result = subprocess.run(cmd, cwd=script_dir)
        return result.returncode == 0
    
    elif file_path:
        if upload_first:
            # 本地文件，先上传再转录
            console.print("[blue]本地文件将先上传到百度网盘...[/blue]")
            cmd = ["python", "upload.py", file_path]
            if wait_transcript:
                cmd.append("--wait-transcript")
            if output:
                cmd.extend(["--remote-dir", output])
            result = subprocess.run(cmd, cwd=script_dir)
            return result.returncode == 0
        else:
            # 尝试通过路径查找文件
            cmd = ["python", "transcribe.py", "--path", file_path]
            if output:
                cmd.extend(["--output", output])
            result = subprocess.run(cmd, cwd=script_dir)
            return result.returncode == 0
    else:
        console.print("[red]错误：使用百度网盘需要提供 fsid 或文件路径[/red]")
        return False


def run_tongyi_tingwu(file_path: str, output: str = None, **kwargs):
    """运行通义听悟转录."""
    console.print("[blue]使用通义听悟转录...[/blue]")
    
    script_dir = Path(__file__).parent / "tongyi-tingwu"
    
    if not os.path.exists(file_path):
        console.print(f"[red]错误：文件不存在: {file_path}[/red]")
        return False
    
    cmd = ["node", "core_transcribe.js", file_path]
    
    if output:
        cmd.append(output)
    
    result = subprocess.run(cmd, cwd=script_dir)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="音视频转录文稿统一入口 - 自动选择最优平台",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自动分析并选择平台
  python transcribe.py "./我的视频.mp4"
  
  # 强制使用指定平台
  python transcribe.py "./我的视频.mp4" --provider tongyi
  python transcribe.py "./我的视频.mp4" --provider baidu --fsid 123456
  
  # 本地上传到百度网盘并转录
  python transcribe.py "./我的视频.mp4" --provider baidu --upload
  python transcribe.py "./我的视频.mp4" --provider baidu --upload --wait
  
  # 指定输出目录
  python transcribe.py "./我的视频.mp4" --output ./notes/
        """
    )
    
    parser.add_argument("file", nargs="?", help="要转录的音视频文件路径")
    parser.add_argument("--provider", choices=["baidu", "tongyi", "auto"], 
                       default="auto", help="选择平台（默认自动）")
    parser.add_argument("--fsid", help="百度网盘文件ID（使用百度网盘时）")
    parser.add_argument("--output", "-o", help="输出目录")
    parser.add_argument("--upload", action="store_true", 
                       help="本地文件先上传到百度网盘（仅百度网盘平台）")
    parser.add_argument("--wait", action="store_true",
                       help="上传后等待转写完成（仅配合 --upload 使用）")
    parser.add_argument("--analyze-only", action="store_true", help="仅分析文件，不执行转录")
    parser.add_argument("--list-providers", action="store_true", help="列出支持的转录平台")
    
    args = parser.parse_args()
    
    # 列出平台
    if args.list_providers:
        table = Table(title="支持的转录平台")
        table.add_column("平台", style="cyan")
        table.add_column("视频大小", style="green")
        table.add_column("音频大小", style="green")
        table.add_column("时长", style="green")
        table.add_column("特点", style="yellow")
        
        table.add_row("百度网盘", "4GB", "4GB", "4小时", "永久保存、支持本地上传")
        table.add_row("通义听悟", "6GB", "500MB", "6小时", "说话人分离、功能更强")
        console.print(table)
        return
    
    # 检查文件
    if not args.file and not args.fsid:
        parser.print_help()
        sys.exit(1)
    
    # 如果指定了 fsid，强制使用百度网盘
    if args.fsid and args.provider == "auto":
        args.provider = "baidu"
    
    # 分析文件
    if args.file and os.path.exists(args.file):
        console.print(f"\n[bold]分析文件: {args.file}[/bold]\n")
        file_info = get_file_info(args.file)
        analysis = analyze_file(file_info)
        print_analysis(file_info, analysis)
        
        if args.analyze_only:
            return
        
        # 自动选择平台
        if args.provider == "auto":
            if analysis["recommended"]:
                args.provider = analysis["recommended"]
            else:
                console.print("[red]错误：文件超出所有平台的限制，无法处理[/red]")
                sys.exit(1)
    elif args.provider == "baidu" and args.fsid:
        console.print(f"[bold]使用百度网盘转录，文件ID: {args.fsid}[/bold]\n")
    else:
        console.print(f"[red]错误：文件不存在: {args.file}[/red]")
        sys.exit(1)
    
    console.print()
    
    # 执行转录
    if args.provider == "baidu":
        success = run_baidu_pan(
            file_path=args.file,
            fsid=args.fsid,
            output=args.output,
            upload_first=args.upload,
            wait_transcript=args.wait
        )
    elif args.provider == "tongyi":
        if not args.file:
            console.print("[red]错误：使用通义听悟需要提供本地文件路径[/red]")
            sys.exit(1)
        success = run_tongyi_tingwu(
            file_path=args.file,
            output=args.output
        )
    else:
        console.print("[red]错误：无法确定使用哪个平台[/red]")
        sys.exit(1)
    
    if success:
        console.print("\n[green]✅ 转录完成！[/green]")
    else:
        console.print("\n[red]❌ 转录失败[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
