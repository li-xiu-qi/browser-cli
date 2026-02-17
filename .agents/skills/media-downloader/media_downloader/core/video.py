"""视频处理模块"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from ..utils.config_loader import Config


class VideoProcessor:
    """视频处理器 - YouTube 下载和剪辑"""
    
    def __init__(self, config: Optional[Config] = None,
                 output_dir: Optional[str] = None):
        self.config = config or Config()
        self.output_dir = Path(output_dir) if output_dir else self.config.downloads_dir
        self.output_dir.mkdir(exist_ok=True)
        
        # 检查工具可用性
        self.ytdlp_available = bool(shutil.which('yt-dlp'))
        self.ffmpeg_available = bool(shutil.which('ffmpeg'))
    
    def download_youtube(self, url: str, 
                         audio_only: bool = False,
                         start_time: Optional[float] = None,
                         end_time: Optional[float] = None) -> Optional[Path]:
        """下载 YouTube 视频
        
        Args:
            url: YouTube URL
            audio_only: 仅下载音频
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
        
        Returns:
            下载的文件路径
        """
        if not self.ytdlp_available:
            print("错误: 需要安装 yt-dlp")
            return None
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if audio_only:
            output_template = self.output_dir / f"yt_audio_{timestamp}.%(ext)s"
            cmd = [
                'yt-dlp',
                '-o', str(output_template),
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                url
            ]
        else:
            output_template = self.output_dir / f"yt_video_{timestamp}.%(ext)s"
            cmd = [
                'yt-dlp',
                '-o', str(output_template),
                '-f', 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
                '--merge-output-format', 'mp4',
                url
            ]
        
        try:
            print(f"⬇️  下载 YouTube: {url}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"❌ 下载失败: {result.stderr}")
                return None
            
            # 找到下载的文件
            downloaded_file = None
            for f in self.output_dir.iterdir():
                if f.stem.startswith(f"yt_{'audio' if audio_only else 'video'}_{timestamp}"):
                    downloaded_file = f
                    break
            
            if not downloaded_file:
                print("❌ 找不到下载的文件")
                return None
            
            print(f"✅ 下载完成: {downloaded_file.name}")
            
            # 如果需要剪辑
            if start_time is not None or end_time is not None:
                return self.trim_video(downloaded_file, start_time, end_time)
            
            return downloaded_file
            
        except subprocess.TimeoutExpired:
            print("❌ 下载超时")
        except Exception as e:
            print(f"❌ 下载错误: {e}")
        
        return None
    
    def trim_video(self, input_path: Path,
                   start: Optional[float] = None,
                   end: Optional[float] = None,
                   duration: Optional[float] = None,
                   output_path: Optional[Path] = None) -> Optional[Path]:
        """剪辑视频
        
        Args:
            input_path: 输入文件路径
            start: 开始时间（秒）
            end: 结束时间（秒）
            duration: 目标时长（秒），如果指定则从中间截取
            output_path: 输出路径，None 则覆盖原文件
        
        Returns:
            输出文件路径
        """
        if not self.ffmpeg_available:
            print("错误: 需要安装 ffmpeg")
            return None
        
        if not input_path.exists():
            print(f"错误: 文件不存在: {input_path}")
            return None
        
        # 如果指定 duration，计算 start 和 end
        if duration and start is None and end is None:
            total = self.get_duration(input_path)
            if total > duration:
                start = (total - duration) / 2
                end = start + duration
        
        if start is None and end is None:
            print("警告: 未指定剪辑范围")
            return input_path
        
        # 生成输出路径
        if not output_path:
            suffix = input_path.suffix
            output_path = input_path.with_suffix(f".trimmed{suffix}")
        
        # 构建 ffmpeg 命令
        cmd = ['ffmpeg', '-y', '-i', str(input_path)]
        
        if start:
            cmd.extend(['-ss', str(start)])
        
        if end:
            target_duration = end - (start or 0)
            cmd.extend(['-t', str(target_duration)])
        elif duration:
            cmd.extend(['-t', str(duration)])
        
        # 使用快速编码预设
        cmd.extend(['-c:v', 'libx264', '-preset', 'fast', '-crf', '23'])
        cmd.extend(['-c:a', 'aac', '-b:a', '128k'])
        cmd.append(str(output_path))
        
        try:
            print(f"✂️  剪辑视频: {start or 0}s - {end or 'end'}s")
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            
            if result.returncode == 0:
                print(f"✅ 剪辑完成: {output_path.name}")
                
                # 如果输出路径和输入路径不同，且成功，可以选择删除原文件
                if output_path != input_path and input_path.exists():
                    input_path.unlink()
                    output_path.rename(input_path)
                    output_path = input_path
                
                return output_path
            else:
                print(f"❌ 剪辑失败: {result.stderr.decode()[:200]}")
        except subprocess.TimeoutExpired:
            print("❌ 剪辑超时")
        except Exception as e:
            print(f"❌ 剪辑错误: {e}")
        
        return None
    
    def get_duration(self, filepath: Path) -> float:
        """获取视频时长"""
        if not self.ffmpeg_available:
            return 0
        
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(filepath)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        
        return 0
    
    def get_info(self, filepath: Path) -> dict:
        """获取视频信息"""
        if not self.ffmpeg_available:
            return {}
        
        try:
            cmd = [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration,bit_rate,size',
                '-show_entries', 'stream=width,height,codec_name',
                '-of', 'json',
                str(filepath)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
        except:
            pass
        
        return {}
