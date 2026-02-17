# -*- coding: utf-8 -*-
import os
import sys
import argparse
import datetime
import subprocess
from pathlib import Path
from config import DEFAULT_OUTPUT_DIR, DEFAULT_TAGS
from processor import process_pdf, process_image

def main():
    parser = argparse.ArgumentParser(description="Paddle Layout Parsing to Obsidian Converter")
    parser.add_argument("file_path", help="Path to the input file (PDF or Image)")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT_DIR, help="Output directory for Obsidian notes")
    parser.add_argument("-t", "--tags", default=None, help="Comma separated tags (e.g., 'AI,Research')")
    parser.add_argument("-c", "--category", default="未分类", help="Category for the note (e.g., '论文', '报告')")
    parser.add_argument("--dump-json", action="store_true", help="Save raw API JSON response for debugging")
    parser.add_argument("--rebuild", action="store_true", help="Generate a rebuilt Markdown file using JSON layout data (Experimental)")
    parser.add_argument("--save-images", action="store_true", help="Download images to local assets folder (Default: use remote links)")
    parser.add_argument("-bg", "--background", action="store_true", help="Run in background process (Recommended for large files)")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file_path):
        print(f"错误: 文件不存在 -> {args.file_path}")
        return

    # --- 后台进程启动逻辑 ---
    if args.background:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = Path(args.file_path).stem
        safe_stem = "".join([c for c in file_stem if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
        if not safe_stem: safe_stem = "task"
        
        log_file = log_dir / f"{timestamp}_{safe_stem}.log"
        
        # 2. 构建子进程命令
        # 必须使用绝对路径调用 python，以防环境问题
        # 添加 -u 参数以禁用缓冲，确保日志实时写入
        cmd = [sys.executable, "-u", sys.argv[0]]
        
        # 重新组装参数，排除 -bg 和 --background
        for arg in sys.argv[1:]:
            if arg not in ["-bg", "--background"]:
                cmd.append(arg)
        
        print(f"========================================")
        print(f"正在后台启动任务: {file_stem}")
        print(f"日志文件位置: {log_file.absolute()}")
        print(f"========================================")
        
        with open(log_file, "w", encoding="utf-8") as f_log:
            f_log.write(f"Task started at {datetime.datetime.now()}\n")
            f_log.write(f"Command: {' '.join(cmd)}\n")
            f_log.write("-" * 40 + "\n")
            f_log.flush()
            
            subprocess.Popen(cmd, stdout=f_log, stderr=subprocess.STDOUT)
            
        print("任务已脱管。你可以安全关闭此窗口。")
        return
    # -----------------------

    # 解析 tags
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",")]
    else:
        tags = DEFAULT_TAGS

    out_dir = os.path.abspath(args.output)
    ext = os.path.splitext(args.file_path)[1].lower()
    
    if ext == ".pdf":
        process_pdf(args.file_path, out_dir, tags, args.category, args.dump_json, args.rebuild, args.save_images)
    elif ext in [".jpg", ".jpeg", ".png", ".bmp"]:
        process_image(args.file_path, out_dir, tags, args.category, args.dump_json, args.save_images)
    else:
        print(f"不支持的文件类型: {ext}")

if __name__ == "__main__":
    main()
