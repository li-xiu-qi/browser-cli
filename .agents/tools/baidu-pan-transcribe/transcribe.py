#!/usr/bin/env python3
"""
百度网盘媒体文件转录文稿工具

通过百度网盘 API 获取音视频文件的 AI 转录文稿。
"""

import argparse
import json
import sys
import time
from typing import List, Optional

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from config import get_access_token, get_app_id, get_base_url, get_transcribe_url

console = Console()


class BaiduPanTranscriber:
    """百度网盘转录客户端."""

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or get_access_token()
        self.app_id = get_app_id()
        self.base_url = get_base_url()
        self.transcribe_url = get_transcribe_url()

        if not self.access_token:
            console.print("[red]错误：未找到 access_token，请检查 token 文件或手动指定[/red]")
            sys.exit(1)

    def _api_request(self, endpoint: str, method: str = "GET", params: dict = None, data: dict = None) -> dict:
        """发送 API 请求."""
        url = f"{self.base_url}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token

        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=30)
            else:
                response = requests.post(url, params=params, data=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]请求失败: {e}[/red]")
            return {"errno": -1, "error": str(e)}

    def get_file_meta(self, fsids: List[int]) -> List[dict]:
        """获取文件详细信息（含转录文稿）.
        
        Args:
            fsids: 文件 ID 列表（最多10个）
            
        Returns:
            文件信息列表
        """
        if len(fsids) > 10:
            console.print("[yellow]警告：每次最多查询 10 个文件，已截取前 10 个[/yellow]")
            fsids = fsids[:10]

        result = self._api_request(
            "multimedia",
            params={
                "method": "filemetas",
                "fsids": f"[{','.join(map(str, fsids))}]",
                "dlink": 1,
                "thumb": 1,
                "extra": 1,
            }
        )

        if result.get("errno") != 0:
            console.print(f"[red]获取文件信息失败: {result}[/red]")
            return []

        return result.get("list", [])

    def search_file_by_path(self, path: str) -> Optional[int]:
        """通过文件路径获取 fsid.
        
        Args:
            path: 文件完整路径
            
        Returns:
            文件 ID 或 None
        """
        # 获取父目录和文件名
        import urllib.parse
        
        dir_path = "/".join(path.split("/")[:-1]) or "/"
        filename = path.split("/")[-1]

        result = self._api_request(
            "file",
            params={
                "method": "list",
                "dir": dir_path,
                "order": "time",
            }
        )

        if result.get("errno") != 0:
            console.print(f"[red]获取目录列表失败: {result}[/red]")
            return None

        for file in result.get("list", []):
            if file.get("server_filename") == filename:
                return file.get("fs_id")

        console.print(f"[red]未找到文件: {path}[/red]")
        return None

    def submit_transcription_task(self, fsid: int, md5: str) -> dict:
        """提交转录任务（SVIP 通常会自动转写，此接口备用）.
        
        Args:
            fsid: 文件 ID
            md5: 文件 MD5
            
        Returns:
            任务提交结果
        """
        url = f"{self.transcribe_url}/start"
        params = {
            "access_token": self.access_token,
            "appid": self.app_id,
            "fsid": fsid,
            "md5": md5,
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]提交任务失败: {e}[/red]")
            return {"errno": -1, "error": str(e)}

    def query_transcription_result(self, fsid: int, md5: str, page: int = 0) -> dict:
        """查询转录结果（带时间戳的详细数据）.
        
        Args:
            fsid: 文件 ID
            md5: 文件 MD5
            page: 页码
            
        Returns:
            转录结果
        """
        url = f"{self.transcribe_url}/get"
        params = {
            "access_token": self.access_token,
            "appid": self.app_id,
            "fsid": fsid,
            "md5": md5,
            "page": page,
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            console.print(f"[red]查询结果失败: {e}[/red]")
            return {"errno": -1, "error": str(e)}

    def get_full_transcription(self, fsid: int, md5: str, callback=None) -> List[dict]:
        """获取完整转录内容（自动轮询所有页面）.
        
        Args:
            fsid: 文件 ID
            md5: 文件 MD5
            callback: 进度回调函数
            
        Returns:
            转录内容列表（带时间戳）
        """
        all_content = []
        page = 0
        max_pages = 100  # 安全限制

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("获取转录内容...", total=None)

            while page < max_pages:
                result = self.query_transcription_result(fsid, md5, page)
                data = result.get("data", {})

                if result.get("errno") != 0:
                    progress.update(task, description=f"[red]查询出错: {result}[/red]")
                    break

                if data.get("res_code") != 0:
                    progress.update(task, description=f"[yellow]{data.get('res_msg', '未知错误')}[/yellow]")
                    break

                # 收集内容
                content_list = data.get("content_list", [])
                for item in content_list:
                    all_content.extend(item.get("content", []))

                finished = data.get("finished", 0)
                page_count = data.get("page_count", 0)

                progress.update(
                    task,
                    description=f"获取第 {page + 1}/{max(page_count, 1)} 页"
                )

                if callback:
                    callback(page, page_count, finished)

                # 检查是否完成
                if finished == 1 and page >= page_count - 1:
                    progress.update(task, description="[green]转录获取完成！[/green]")
                    break

                # 如果已完成但还有更多页
                if finished == 1 and page >= page_count:
                    break

                page += 1
                time.sleep(0.5)  # 避免请求过快

        return all_content

    def format_transcript_simple(self, filename: str, content: str, abstract: str = "") -> str:
        """格式化为简单文本."""
        lines = [
            f"# {filename}",
            "",
            content if content else "（暂无转录内容，可能转写未完成或文件不支持）",
            "",
            "---",
            f"**文件**: {filename}",
        ]
        if abstract:
            lines.extend([
                "",
                "**AI 摘要**:",
                abstract,
            ])
        return "\n".join(lines)

    def format_transcript_detailed(self, filename: str, contents: List[dict], abstract: str = "") -> str:
        """格式化为带时间戳的详细文本."""
        lines = [f"# {filename}", "", "## 转录内容", ""]

        if not contents:
            lines.append("（暂无转录内容，可能转写未完成或文件不支持）")
        else:
            for item in contents:
                start = item.get("s", 0)
                text = item.get("t", "")
                # 格式化时间为 MM:SS
                minutes = int(start // 60)
                seconds = int(start % 60)
                time_str = f"{minutes:02d}:{seconds:02d}"
                lines.append(f"[{time_str}] {text}")

        lines.extend([
            "",
            "---",
            f"**文件**: {filename}",
        ])

        if abstract:
            lines.extend([
                "",
                "**AI 摘要**:",
                abstract,
            ])

        return "\n".join(lines)

    def check_transcription_status(self, file_info: dict) -> str:
        """检查转录状态.
        
        Args:
            file_info: 文件信息字典
            
        Returns:
            状态描述
        """
        content = file_info.get("content", "")
        abstract = file_info.get("abstract", "")

        if content:
            return "✅ 已完成"
        elif abstract:
            return "⏳ 摘要已生成，文稿处理中"
        else:
            return "⏳ 转写进行中或未开始"


def main():
    parser = argparse.ArgumentParser(
        description="百度网盘媒体文件转录文稿工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python transcribe.py --fsid 465930705301366
  python transcribe.py --path "/视频/课程.mp4" --format detailed
  python transcribe.py --fsids 111,222,333 --output ./transcripts/
        """
    )

    parser.add_argument("--fsid", type=int, help="单个文件 ID")
    parser.add_argument("--fsids", type=str, help="多个文件 ID（逗号分隔）")
    parser.add_argument("--path", type=str, help="文件完整路径")
    parser.add_argument(
        "--format",
        type=str,
        choices=["simple", "detailed"],
        default="simple",
        help="输出格式: simple=纯文本, detailed=带时间戳"
    )
    parser.add_argument("--output", type=str, help="输出文件路径（目录或文件）")
    parser.add_argument("--check-only", action="store_true", help="仅检查转写状态")
    parser.add_argument("--token", type=str, help="手动指定 access token")

    args = parser.parse_args()

    # 初始化客户端
    transcriber = BaiduPanTranscriber(access_token=args.token)

    # 收集要处理的文件 ID
    fsids = []
    file_paths = {}  # fsid -> path mapping

    if args.fsid:
        fsids.append(args.fsid)
    elif args.fsids:
        fsids = [int(x.strip()) for x in args.fsids.split(",")]
    elif args.path:
        fsid = transcriber.search_file_by_path(args.path)
        if fsid:
            fsids.append(fsid)
            file_paths[fsid] = args.path
        else:
            sys.exit(1)
    else:
        console.print("[red]错误：请指定 --fsid、--fsids 或 --path[/red]")
        parser.print_help()
        sys.exit(1)

    # 获取文件信息
    console.print(f"[blue]正在获取 {len(fsids)} 个文件的信息...[/blue]")
    file_metas = transcriber.get_file_meta(fsids)

    if not file_metas:
        console.print("[red]未获取到文件信息[/red]")
        sys.exit(1)

    # 仅检查状态模式
    if args.check_only:
        table = Table(title="转写状态检查")
        table.add_column("文件名", style="cyan")
        table.add_column("类型", style="green")
        table.add_column("大小", style="yellow")
        table.add_column("转写状态", style="magenta")

        for meta in file_metas:
            filename = meta.get("filename", "未知")
            category = meta.get("category", 0)
            size = meta.get("size", 0)
            
            cat_map = {1: "视频", 2: "音频", 3: "图片", 4: "文档"}
            cat_name = cat_map.get(category, "其他")
            size_mb = size / (1024 * 1024)
            
            status = transcriber.check_transcription_status(meta)
            table.add_row(filename, cat_name, f"{size_mb:.1f} MB", status)

        console.print(table)
        return

    # 处理每个文件
    results = []
    for meta in file_metas:
        fsid = meta.get("fsid")
        filename = meta.get("filename", f"file_{fsid}")
        md5 = meta.get("md5", "")
        content = meta.get("content", "")
        abstract = meta.get("abstract", "")
        category = meta.get("category", 0)

        console.print(f"\n[blue]处理文件: {filename}[/blue]")

        # 检查是否是音视频文件
        if category not in [1, 2]:  # 1=视频, 2=音频
            console.print(f"[yellow]警告: {filename} 不是音视频文件（类型: {category}），跳过[/yellow]")
            continue

        # 如果已经有 content，直接格式化输出
        if content and args.format == "simple":
            result = transcriber.format_transcript_simple(filename, content, abstract)
            results.append((filename, result))
        else:
            # 获取详细转录（带时间戳）
            console.print(f"[blue]获取详细转录内容...[/blue]")
            detailed_contents = transcriber.get_full_transcription(fsid, md5)
            
            if args.format == "detailed":
                result = transcriber.format_transcript_detailed(filename, detailed_contents, abstract)
            else:
                # simple 模式但没有 content，用 detailed 的内容拼接
                full_text = "\n".join([item.get("t", "") for item in detailed_contents])
                result = transcriber.format_transcript_simple(filename, full_text, abstract)
            
            results.append((filename, result))

    # 输出结果
    if not results:
        console.print("[red]没有成功获取到任何转录内容[/red]")
        sys.exit(1)

    # 保存或输出
    if args.output:
        import os
        
        # 判断是文件还是目录
        if len(results) == 1 and not args.output.endswith(("/", "\\")):
            # 单文件模式，直接写入
            output_path = args.output
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(results[0][1])
            console.print(f"[green]已保存到: {output_path}[/green]")
        else:
            # 多文件模式，创建目录
            os.makedirs(args.output, exist_ok=True)
            for filename, content in results:
                # 清理文件名
                safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ")
                output_path = os.path.join(args.output, f"{safe_name}.md")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(content)
                console.print(f"[green]已保存: {output_path}[/green]")
    else:
        # 输出到控制台
        for filename, content in results:
            console.print("\n" + "=" * 60)
            console.print(content)
            console.print("=" * 60)


if __name__ == "__main__":
    main()
