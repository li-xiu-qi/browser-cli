#!/usr/bin/env python3
"""
批量转录工具 - 批量获取多个文件的转录文稿
"""

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.progress import Progress, TaskID

from transcribe import BaiduPanTranscriber

console = Console()


class BatchTranscriber(BaiduPanTranscriber):
    """批量转录工具."""

    def batch_get_meta(self, fsids: list, batch_size: int = 10) -> list:
        """批量获取文件信息.
        
        Args:
            fsids: 文件 ID 列表
            batch_size: 每批数量（API限制最多10个）
            
        Returns:
            文件信息列表
        """
        all_results = []
        
        with Progress() as progress:
            task = progress.add_task("获取文件信息...", total=len(fsids))
            
            for i in range(0, len(fsids), batch_size):
                batch = fsids[i:i + batch_size]
                results = self.get_file_meta(batch)
                all_results.extend(results)
                progress.update(task, advance=len(batch))
        
        return all_results

    def process_file(self, meta: dict, output_dir: str, format_type: str) -> dict:
        """处理单个文件.
        
        Args:
            meta: 文件信息
            output_dir: 输出目录
            format_type: 输出格式
            
        Returns:
            处理结果
        """
        fsid = meta.get("fsid")
        filename = meta.get("filename", f"file_{fsid}")
        md5 = meta.get("md5", "")
        content = meta.get("content", "")
        abstract = meta.get("abstract", "")
        category = meta.get("category", 0)

        result = {
            "fsid": fsid,
            "filename": filename,
            "status": "success",
            "output_path": None,
            "error": None,
        }

        # 检查是否是音视频
        if category not in [1, 2]:
            result["status"] = "skipped"
            result["error"] = "Not a media file"
            return result

        try:
            # 获取内容
            if content and format_type == "simple":
                output = self.format_transcript_simple(filename, content, abstract)
            else:
                detailed = self.get_full_transcription(fsid, md5)
                if format_type == "detailed":
                    output = self.format_transcript_detailed(filename, detailed, abstract)
                else:
                    full_text = "\n".join([item.get("t", "") for item in detailed])
                    output = self.format_transcript_simple(filename, full_text, abstract)

            # 保存文件
            safe_name = "".join(c for c in filename if c.isalnum() or c in "._- ")
            output_path = os.path.join(output_dir, f"{safe_name}.md")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
            
            result["output_path"] = output_path
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)

        return result


def main():
    parser = argparse.ArgumentParser(
        description="批量转录百度网盘音视频文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从文件读取 fsid 列表批量转录
  python batch_transcribe.py --input-file fsids.txt --output ./transcripts/
  
  # 批量转录指定目录下的所有音视频
  python batch_transcribe.py --scan-dir "/转存区域/课程" --output ./transcripts/
  
  # 直接指定多个 fsid
  python batch_transcribe.py --fsids 111,222,333,444,555 --output ./transcripts/
        """
    )

    parser.add_argument("--input-file", type=str, help="包含 fsid 列表的文件（每行一个）")
    parser.add_argument("--scan-dir", type=str, help="扫描目录中的所有音视频文件")
    parser.add_argument("--fsids", type=str, help="逗号分隔的文件 ID 列表")
    parser.add_argument("--output", type=str, required=True, help="输出目录")
    parser.add_argument("--format", type=str, choices=["simple", "detailed"], default="simple")
    parser.add_argument("--workers", type=int, default=3, help="并发数（默认3）")
    parser.add_argument("--token", type=str, help="access token")

    args = parser.parse_args()

    # 收集 fsids
    fsids = []

    if args.input_file:
        with open(args.input_file, "r", encoding="utf-8") as f:
            fsids = [int(line.strip()) for line in f if line.strip().isdigit()]
    elif args.fsids:
        fsids = [int(x.strip()) for x in args.fsids.split(",")]
    elif args.scan_dir:
        # 扫描目录
        tool = BatchTranscriber(access_token=args.token)
        files = tool.list_media_files(args.scan_dir)
        fsids = [f.get("fs_id") for f in files]
    else:
        parser.print_help()
        sys.exit(1)

    if not fsids:
        console.print("[red]没有找到要处理的文件[/red]")
        sys.exit(1)

    console.print(f"[blue]准备处理 {len(fsids)} 个文件[/blue]")

    # 创建输出目录
    os.makedirs(args.output, exist_ok=True)

    # 初始化工具
    tool = BatchTranscriber(access_token=args.token)

    # 批量获取文件信息
    console.print("[blue]获取文件信息...[/blue]")
    file_metas = tool.batch_get_meta(fsids)

    # 筛选音视频文件
    media_metas = [m for m in file_metas if m.get("category") in [1, 2]]
    console.print(f"[green]找到 {len(media_metas)} 个音视频文件[/green]")

    # 并发处理
    results = []
    with Progress() as progress:
        task = progress.add_task("转录中...", total=len(media_metas))
        
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    tool.process_file, meta, args.output, args.format
                ): meta for meta in media_metas
            }
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                progress.update(task, advance=1)

    # 统计结果
    success = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")

    console.print(f"\n[green]完成！成功: {success}, 跳过: {skipped}, 失败: {errors}[/green]")

    # 保存报告
    report_path = os.path.join(args.output, "_transcribe_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    console.print(f"[blue]报告已保存: {report_path}[/blue]")


if __name__ == "__main__":
    main()
