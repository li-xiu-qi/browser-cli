#!/usr/bin/env python3
"""
搜索并转录 - 先搜索网盘中的音视频文件，然后获取转录文稿
"""

import argparse
import sys
from typing import List

from rich.console import Console
from rich.table import Table

from transcribe import BaiduPanTranscriber

console = Console()


class SearchAndTranscribe(BaiduPanTranscriber):
    """搜索并转录工具."""

    def search_files(self, key: str, dir: str = "/", recursion: int = 1) -> List[dict]:
        """搜索文件.
        
        Args:
            key: 搜索关键词
            dir: 搜索目录
            recursion: 是否递归（1=是，0=否）
            
        Returns:
            文件列表
        """
        result = self._api_request(
            "file",
            params={
                "method": "search",
                "key": key,
                "dir": dir,
                "recursion": recursion,
            }
        )

        if result.get("errno") != 0:
            console.print(f"[red]搜索失败: {result}[/red]")
            return []

        return result.get("list", [])

    def semantic_search(self, query: str, dir: str = "/") -> List[dict]:
        """语义搜索（通过 MCP，这里用普通搜索模拟）.
        
        Args:
            query: 自然语言查询
            dir: 搜索目录
            
        Returns:
            文件列表
        """
        # 简化处理：提取关键词进行搜索
        # 实际使用时可以通过 MCP 调用真正的语义搜索
        console.print(f"[yellow]注意：语义搜索需要通过 MCP，这里使用关键词搜索模拟[/yellow]")
        
        # 简单提取关键词（去除常见词）
        stop_words = {"的", "了", "和", "是", "在", "有", "我", "找", "一下", "关于", "的", "文件", "视频", "音频"}
        keywords = [w for w in query.split() if w not in stop_words]
        
        if keywords:
            return self.search_files(keywords[0], dir)
        return []

    def list_media_files(self, dir: str = "/", page: int = 1, num: int = 100) -> List[dict]:
        """列出目录中的音视频文件.
        
        Args:
            dir: 目录路径
            page: 页码
            num: 每页数量
            
        Returns:
            音视频文件列表
        """
        result = self._api_request(
            "file",
            params={
                "method": "list",
                "dir": dir,
                "page": page,
                "num": num,
                "order": "time",
            }
        )

        if result.get("errno") != 0:
            console.print(f"[red]获取文件列表失败: {result}[/red]")
            return []

        # 筛选音视频文件
        all_files = result.get("list", [])
        media_files = [f for f in all_files if f.get("category") in [1, 2]]  # 1=视频, 2=音频
        
        return media_files


def main():
    parser = argparse.ArgumentParser(
        description="搜索网盘中的音视频文件并获取转录文稿",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 搜索文件名包含"一堂"的视频
  python search_and_transcribe.py --search "一堂"
  
  # 列出某个目录的所有音视频
  python search_and_transcribe.py --list "/转存区域/课程"
  
  # 搜索并自动转录前3个结果
  python search_and_transcribe.py --search "一堂" --auto-transcribe 3
        """
    )

    parser.add_argument("--search", type=str, help="关键词搜索")
    parser.add_argument("--semantic", type=str, help="语义搜索（自然语言）")
    parser.add_argument("--list", dest="list_dir", type=str, help="列出指定目录的音视频文件")
    parser.add_argument("--dir", type=str, default="/", help="搜索目录（默认根目录）")
    parser.add_argument("--auto-transcribe", type=int, help="自动转录前 N 个结果")
    parser.add_argument("--format", type=str, choices=["simple", "detailed"], default="simple")
    parser.add_argument("--output", type=str, help="输出目录")
    parser.add_argument("--token", type=str, help="access token")

    args = parser.parse_args()

    # 初始化
    tool = SearchAndTranscribe(access_token=args.token)

    files = []

    # 搜索模式
    if args.search:
        console.print(f"[blue]搜索关键词: {args.search}[/blue]")
        files = tool.search_files(args.search, args.dir)
    elif args.semantic:
        console.print(f"[blue]语义搜索: {args.semantic}[/blue]")
        files = tool.semantic_search(args.semantic, args.dir)
    elif args.list_dir is not None:
        console.print(f"[blue]列出目录: {args.list_dir or '/'}[/blue]")
        files = tool.list_media_files(args.list_dir or "/")
    else:
        parser.print_help()
        sys.exit(1)

    # 筛选音视频文件
    media_files = [f for f in files if f.get("category") in [1, 2]]

    if not media_files:
        console.print("[yellow]未找到音视频文件[/yellow]")
        sys.exit(0)

    # 显示结果
    table = Table(title=f"找到 {len(media_files)} 个音视频文件")
    table.add_column("序号", style="cyan", width=6)
    table.add_column("文件名", style="green")
    table.add_column("类型", style="yellow", width=8)
    table.add_column("大小", style="blue", width=12)
    table.add_column("修改时间", style="magenta", width=20)

    cat_map = {1: "视频", 2: "音频"}
    
    for i, f in enumerate(media_files[:20], 1):  # 最多显示20个
        filename = f.get("server_filename", "未知")
        category = cat_map.get(f.get("category"), "其他")
        size = f.get("size", 0) / (1024 * 1024)  # MB
        mtime = f.get("server_mtime", "")
        
        # 格式化时间
        if mtime:
            import time
            mtime_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
        else:
            mtime_str = "未知"

        table.add_row(str(i), filename, category, f"{size:.1f} MB", mtime_str)

    console.print(table)

    if len(media_files) > 20:
        console.print(f"[yellow]... 还有 {len(media_files) - 20} 个文件未显示[/yellow]")

    # 自动转录模式
    if args.auto_transcribe and args.auto_transcribe > 0:
        to_transcribe = media_files[:args.auto_transcribe]
        fsids = [f.get("fs_id") for f in to_transcribe]
        
        console.print(f"\n[blue]开始转录前 {len(fsids)} 个文件...[/blue]")
        
        # 调用 transcribe.py 的逻辑
        import os
        os.makedirs(args.output or "./transcripts", exist_ok=True)
        
        for fsid in fsids:
            # 使用 subprocess 调用 transcribe.py
            import subprocess
            cmd = [
                "python", "transcribe.py",
                "--fsid", str(fsid),
                "--format", args.format,
            ]
            if args.output:
                cmd.extend(["--output", args.output])
            
            subprocess.run(cmd)


if __name__ == "__main__":
    main()
