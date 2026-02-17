#!/usr/bin/env python3
"""
百度网盘文件上传工具

支持：
- 本地文件上传到百度网盘
- 秒传（文件已存在时快速完成）
- 分片上传（大文件）
- 上传后自动开始转写（SVIP）
- 自动等待转写完成并获取文稿
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from config import get_access_token, get_app_id
from transcribe import BaiduPanTranscriber

console = Console()


class BaiduPanUploader(BaiduPanTranscriber):
    """百度网盘上传客户端."""

    # 分片大小：4MB
    CHUNK_SIZE = 4 * 1024 * 1024

    def __init__(self, access_token: Optional[str] = None):
        super().__init__(access_token)
        self.app_id = get_app_id()

    def _api_request(self, endpoint: str, method: str = "GET", params: dict = None, data: dict = None, **kwargs) -> dict:
        """发送 API 请求."""
        base_url = "https://pan.baidu.com/rest/2.0/xpan"
        url = f"{base_url}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token

        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=30, **kwargs)
            else:
                response = requests.post(url, params=params, data=data, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]请求失败: {e}[/red]")
            return {"errno": -1, "error": str(e)}

    def calculate_md5(self, file_path: str) -> str:
        """计算文件 MD5."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def calculate_chunk_md5s(self, file_path: str) -> list:
        """计算每个分片的 MD5."""
        md5s = []
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(self.CHUNK_SIZE)
                if not chunk:
                    break
                md5s.append(hashlib.md5(chunk).hexdigest())
        return md5s

    def precreate(self, remote_path: str, size: int, isdir: int = 0, block_list: list = None) -> dict:
        """
        预上传，获取上传地址。
        
        Args:
            remote_path: 网盘中的目标路径
            size: 文件大小
            isdir: 是否为目录
            block_list: 分片 MD5 列表
            
        Returns:
            预上传结果，包含 uploadid 和 upload 地址
        """
        data = {
            "path": remote_path,
            "size": size,
            "isdir": isdir,
            "rtype": 1,  # 1=如果存在则重命名
        }
        
        if block_list:
            data["block_list"] = json.dumps(block_list)
        
        result = self._api_request("file", method="POST", params={"method": "precreate"}, data=data)
        return result

    def upload_chunk(self, upload_url: str, file_path: str, chunk_index: int, total_chunks: int) -> bool:
        """
        上传单个分片。
        
        Args:
            upload_url: 上传地址
            file_path: 本地文件路径
            chunk_index: 分片索引
            total_chunks: 总分片数
            
        Returns:
            是否成功
        """
        try:
            with open(file_path, "rb") as f:
                f.seek(chunk_index * self.CHUNK_SIZE)
                chunk_data = f.read(self.CHUNK_SIZE)
            
            files = {"file": (f"chunk_{chunk_index}", chunk_data)}
            response = requests.post(upload_url, files=files, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("md5"):
                    return True
            
            return False
        except Exception as e:
            console.print(f"[red]分片 {chunk_index + 1}/{total_chunks} 上传失败: {e}[/red]")
            return False

    def create_file(self, remote_path: str, size: int, uploadid: str, block_list: list, isdir: int = 0) -> dict:
        """
        完成文件创建。
        
        Args:
            remote_path: 网盘中的目标路径
            size: 文件大小
            uploadid: 上传 ID
            block_list: 分片 MD5 列表
            isdir: 是否为目录
            
        Returns:
            创建结果
        """
        data = {
            "path": remote_path,
            "size": size,
            "uploadid": uploadid,
            "block_list": json.dumps(block_list),
            "isdir": isdir,
            "rtype": 1,
        }
        
        result = self._api_request("file", method="POST", params={"method": "create"}, data=data)
        return result

    def upload_file(self, local_path: str, remote_dir: str = "/", remote_name: str = None, 
                    progress_callback=None) -> Tuple[bool, dict]:
        """
        上传本地文件到百度网盘。
        
        Args:
            local_path: 本地文件路径
            remote_dir: 网盘目标目录
            remote_name: 网盘文件名（默认使用本地文件名）
            progress_callback: 进度回调函数
            
        Returns:
            (是否成功, 结果信息)
        """
        if not os.path.exists(local_path):
            return False, {"error": f"文件不存在: {local_path}"}
        
        file_size = os.path.getsize(local_path)
        file_name = remote_name or os.path.basename(local_path)
        remote_path = f"{remote_dir.rstrip('/')}/{file_name}"
        
        console.print(f"[blue]准备上传: {file_name}[/blue]")
        console.print(f"  本地路径: {local_path}")
        console.print(f"  文件大小: {file_size / 1024 / 1024:.2f} MB")
        console.print(f"  网盘路径: {remote_path}")
        
        # 计算分片 MD5
        console.print("[blue]计算文件 MD5...[/blue]")
        block_list = self.calculate_chunk_md5s(local_path)
        total_chunks = len(block_list)
        
        # 预上传
        console.print("[blue]预上传...[/blue]")
        precreate_result = self.precreate(remote_path, file_size, block_list=block_list)
        
        if precreate_result.get("errno") != 0:
            return False, {"error": f"预上传失败: {precreate_result}"}
        
        # 检查是否秒传成功
        if precreate_result.get("return_type") == 2:
            console.print("[green]✅ 秒传成功！文件已存在于网盘[/green]")
            return True, precreate_result
        
        # 需要上传
        uploadid = precreate_result.get("uploadid")
        upload_urls = precreate_result.get("upload", [])
        
        if not upload_urls:
            return False, {"error": "未获取到上传地址"}
        
        # 上传分片
        console.print(f"[blue]开始上传，共 {total_chunks} 个分片...[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            upload_task = progress.add_task("上传中...", total=total_chunks)
            
            for i in range(total_chunks):
                upload_url = upload_urls[i % len(upload_urls)]
                
                # 重试 3 次
                for attempt in range(3):
                    if self.upload_chunk(upload_url, local_path, i, total_chunks):
                        progress.update(upload_task, advance=1)
                        if progress_callback:
                            progress_callback(i + 1, total_chunks)
                        break
                    else:
                        if attempt < 2:
                            console.print(f"[yellow]分片 {i + 1} 重试 {attempt + 1}/3...[/yellow]")
                        else:
                            return False, {"error": f"分片 {i + 1} 上传失败"}
        
        # 完成创建
        console.print("[blue]完成上传，创建文件...[/blue]")
        create_result = self.create_file(remote_path, file_size, uploadid, block_list)
        
        if create_result.get("errno") != 0:
            return False, {"error": f"创建文件失败: {create_result}"}
        
        console.print("[green]✅ 上传成功！[/green]")
        return True, create_result

    def upload_and_transcribe(self, local_path: str, remote_dir: str = "/", 
                              wait_transcript: bool = True, timeout_minutes: int = 60) -> dict:
        """
        上传文件并等待转写完成。
        
        Args:
            local_path: 本地文件路径
            remote_dir: 网盘目标目录
            wait_transcript: 是否等待转写完成
            timeout_minutes: 等待超时时间（分钟）
            
        Returns:
            转录结果
        """
        # 1. 上传文件
        success, result = self.upload_file(local_path, remote_dir)
        
        if not success:
            console.print(f"[red]上传失败: {result.get('error')}[/red]")
            return {"success": False, "error": result.get("error")}
        
        # 获取上传后的文件信息
        fsid = result.get("fs_id")
        if not fsid:
            # 秒传的情况，需要搜索文件获取 fsid
            file_name = os.path.basename(local_path)
            from transcribe import BaiduPanTranscriber
            temp_transcriber = BaiduPanTranscriber(self.access_token)
            fsid = temp_transcriber.search_file_by_path(f"{remote_dir}/{file_name}")
            if not fsid:
                return {"success": True, "uploaded": True, "fsid": None, 
                        "message": "上传成功，但无法获取文件ID，请稍后手动获取转录"}
        
        console.print(f"[green]文件ID: {fsid}[/green]")
        
        if not wait_transcript:
            return {
                "success": True,
                "uploaded": True,
                "fsid": fsid,
                "message": "上传成功，SVIP将自动开始转写，请稍后使用 transcribe.py 获取文稿"
            }
        
        # 2. 等待转写完成
        console.print(f"[blue]等待转写完成（最多等待 {timeout_minutes} 分钟）...[/blue]")
        console.print("[yellow]提示：SVIP 上传音视频后会自动开始转写，这可能需要几分钟到几十分钟[/yellow]")
        
        import time
        start_time = time.time()
        check_interval = 30  # 每 30 秒检查一次
        
        while time.time() - start_time < timeout_minutes * 60:
            # 检查转写状态
            meta = self.get_file_meta([fsid])
            if meta:
                file_info = meta[0]
                content = file_info.get("content", "")
                
                if content:
                    console.print("[green]✅ 转写完成！[/green]")
                    # 导出转录结果
                    filename = file_info.get("filename", os.path.basename(local_path))
                    output = self.format_transcript_simple(filename, content, file_info.get("abstract", ""))
                    return {
                        "success": True,
                        "uploaded": True,
                        "transcribed": True,
                        "fsid": fsid,
                        "content": output
                    }
                else:
                    # 显示进度
                    elapsed = int(time.time() - start_time)
                    console.print(f"[yellow]⏳ 转写进行中... 已等待 {elapsed // 60} 分 {elapsed % 60} 秒[/yellow]", end="\r")
            
            time.sleep(check_interval)
        
        # 超时
        console.print(f"\n[yellow]等待超时，文件已上传但转写尚未完成[/yellow]")
        return {
            "success": True,
            "uploaded": True,
            "transcribed": False,
            "fsid": fsid,
            "message": f"上传成功，转写进行中。请稍后使用 --fsid {fsid} 获取文稿"
        }


def main():
    parser = argparse.ArgumentParser(
        description="上传本地文件到百度网盘",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 上传单个文件
  python upload.py "./一堂课程.mp4"
  
  # 上传到指定目录
  python upload.py "./一堂课程.mp4" --remote-dir "/转存区域/课程"
  
  # 上传并等待转写完成
  python upload.py "./一堂课程.mp4" --wait-transcript
  
  # 上传并重命名
  python upload.py "./一堂课程.mp4" --remote-name "会员日课程.mp4"
        """
    )
    
    parser.add_argument("file", help="要上传的本地文件路径")
    parser.add_argument("--remote-dir", default="/", help="网盘目标目录（默认根目录）")
    parser.add_argument("--remote-name", help="网盘文件名（默认使用本地文件名）")
    parser.add_argument("--wait-transcript", action="store_true", 
                       help="上传后等待转写完成（仅适用于音视频文件）")
    parser.add_argument("--timeout", type=int, default=60, 
                       help="等待转写超时时间（分钟，默认60）")
    parser.add_argument("--token", help="access token")
    
    args = parser.parse_args()
    
    # 检查文件
    if not os.path.exists(args.file):
        console.print(f"[red]错误：文件不存在: {args.file}[/red]")
        sys.exit(1)
    
    # 检查是否是音视频文件
    ext = Path(args.file).suffix.lower()
    video_audio_exts = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.m4v', '.flv', '.webm',
                        '.mp3', '.wav', '.m4a', '.aac', '.wma', '.ogg', '.flac']
    is_media = ext in video_audio_exts
    
    if args.wait_transcript and not is_media:
        console.print("[yellow]警告：该文件不是音视频格式，无法转写[/yellow]")
        args.wait_transcript = False
    
    # 初始化上传器
    uploader = BaiduPanUploader(access_token=args.token)
    
    # 执行上传
    if args.wait_transcript:
        result = uploader.upload_and_transcribe(
            args.file,
            remote_dir=args.remote_dir,
            remote_name=args.remote_name,
            wait_transcript=True,
            timeout_minutes=args.timeout
        )
        
        if result.get("transcribed"):
            # 保存转录结果
            output_path = f"{os.path.splitext(args.file)[0]}.md"
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result["content"])
            console.print(f"[green]转录结果已保存: {output_path}[/green]")
    else:
        success, result = uploader.upload_file(args.file, args.remote_dir, args.remote_name)
        
        if success:
            console.print(f"\n[green]✅ 文件上传成功！[/green]")
            if is_media:
                console.print(f"[blue]文件ID: {result.get('fs_id', 'N/A')}[/blue]")
                console.print("[yellow]提示：SVIP 将自动开始转写，请稍后使用 transcribe.py 获取文稿[/yellow]")
        else:
            console.print(f"\n[red]❌ 上传失败: {result.get('error')}[/red]")
            sys.exit(1)


if __name__ == "__main__":
    main()
