#!/usr/bin/env python3
"""
目录结构生成器 - Directory Indexer
扫描指定目录，生成标准格式的目录结构 Markdown 文件

用法:
    # 默认模式：扫描当前目录
    python generate_index.py
    
    # 指定目录模式
    python generate_index.py /path/to/directory
    
    # 指定输出文件
    python generate_index.py /path/to/directory -o output.md
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Set, Dict, Tuple


# 默认配置
DEFAULT_SKIP_PATTERNS: Set[str] = {
    "scripts",
    "assets",
    ".obsidian",
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    ".agent",
    ".agents",
    ".kimi",
    ".gemini",
    ".opencode",
    ".smart-env",
    ".vscode",
}

DEFAULT_SKIP_FILES: Set[str] = {
    "README.md",
}


class DirectoryStats:
    """目录统计信息"""
    def __init__(self):
        self.file_count = 0      # 总文件数
        self.md_count = 0        # Markdown 文件数
        self.dir_count = 0       # 子目录数
        self.subdirs: Dict[str, 'DirectoryStats'] = {}
    
    def get_top_level_stats(self) -> list:
        """获取一级子目录统计"""
        return sorted([
            (name, stats.md_count, stats.file_count, stats.dir_count)
            for name, stats in self.subdirs.items()
        ])


class DirectoryIndexGenerator:
    """目录结构生成器"""
    
    def __init__(
        self,
        target_dir: Path,
        output_file: Path,
        skip_patterns: Set[str] = None,
        skip_files: Set[str] = None,
    ):
        self.target_dir = Path(target_dir).resolve()
        self.output_file = Path(output_file).resolve()
        self.skip_patterns = skip_patterns or DEFAULT_SKIP_PATTERNS
        self.skip_files = skip_files or DEFAULT_SKIP_FILES
        
    def should_skip(self, name: str) -> bool:
        """判断是否应该跳过该文件/目录"""
        if name.startswith("."):
            return True
        if name in self.skip_patterns:
            return True
        if name in self.skip_files:
            return True
        return False
    
    def is_md_file(self, path: Path) -> bool:
        """判断是否为 Markdown 文件"""
        return path.suffix.lower() == '.md'
    
    def scan_directory(self, path: Path, prefix: str = "", is_last: bool = True) -> Tuple[list, DirectoryStats]:
        """递归扫描目录，返回 (树状结构行列表, 统计信息)"""
        lines = []
        stats = DirectoryStats()
        
        try:
            entries = sorted(
                [e for e in path.iterdir() if not self.should_skip(e.name)],
                key=lambda e: (e.is_file(), e.name.lower())
            )
        except PermissionError:
            return lines, stats
        
        # 分离目录和文件，目录在前
        dirs = [e for e in entries if e.is_dir()]
        files = [e for e in entries if e.is_file()]
        
        # 统计文件数
        stats.file_count = len(files)
        stats.md_count = sum(1 for f in files if self.is_md_file(f))
        
        # 先处理目录
        for i, entry in enumerate(dirs):
            is_last_entry = (i == len(dirs) - 1 and len(files) == 0)
            connector = "└── " if is_last_entry else "├── "
            
            lines.append(f"{prefix}{connector}{entry.name}")
            
            # 递归处理子目录
            extension = "    " if is_last_entry else "│   "
            sub_lines, sub_stats = self.scan_directory(entry, prefix + extension, is_last_entry)
            lines.extend(sub_lines)
            
            # 累计统计
            stats.dir_count += 1  # 当前目录
            stats.subdirs[entry.name] = sub_stats
            stats.file_count += sub_stats.file_count
            stats.md_count += sub_stats.md_count
            stats.dir_count += sub_stats.dir_count
        
        # 再处理文件
        for i, entry in enumerate(files):
            is_last_file = (i == len(files) - 1)
            connector = "└── " if is_last_file else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
        
        return lines, stats
    
    def generate(self) -> str:
        """生成目录结构内容"""
        print(f"正在扫描目录: {self.target_dir}")
        
        # 生成树状结构和统计
        tree_lines, stats = self.scan_directory(self.target_dir)
        
        # 构建 Markdown 内容
        content = f"""# {self.target_dir.name} 目录结构

本文件由脚本自动生成，最后更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

```
{self.target_dir.name}/
"""
        
        # 添加树状结构
        for line in tree_lines:
            content += line + "\n"
        
        content += """```

---

## 目录统计

### 一级子目录概览

| 目录 | 笔记(.md) | 总文件 | 子目录 |
|------|-----------|--------|--------|
"""
        
        # 只显示一级子目录统计
        for name, md_count, file_count, dir_count in stats.get_top_level_stats():
            content += f"| {name} | {md_count} | {file_count} | {dir_count} |\n"
        
        content += f"| **总计** | **{stats.md_count}** | **{stats.file_count}** | **{stats.dir_count}** |\n"
        
        content += """

---

## 维护说明

本目录树由脚本自动生成。

### 更新命令

```bash
python {script_path} [{target_dir}]
```
""".format(
            script_path=Path(__file__),
            target_dir=self.target_dir,
        )
        
        return content
    
    def save(self) -> None:
        """生成并保存目录结构文件"""
        content = self.generate()
        self.output_file.write_text(content, encoding="utf-8")
        print(f"目录结构已生成: {self.output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="生成目录结构的 Markdown 索引文件",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 扫描当前目录
  python generate_index.py
  
  # 指定目录
  python generate_index.py /path/to/directory
  
  # 指定输出文件
  python generate_index.py /path/to/directory -o output.md
        """
    )
    
    parser.add_argument(
        "target_dir",
        nargs="?",
        type=Path,
        default=Path.cwd(),
        help=f"要扫描的目录路径（默认: 当前目录）"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="输出文件路径（默认: <target_dir>_目录结构.md）"
    )
    
    args = parser.parse_args()
    
    # 确定输出文件路径
    if args.output:
        output_file = args.output
    else:
        output_file = args.target_dir / f"{args.target_dir.name}_目录结构.md"
    
    # 创建生成器
    generator = DirectoryIndexGenerator(
        target_dir=args.target_dir,
        output_file=output_file,
    )
    
    # 生成目录结构
    try:
        generator.save()
    except Exception as e:
        print(f"错误: 生成目录结构失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
