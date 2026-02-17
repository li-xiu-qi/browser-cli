#!/usr/bin/env python3
"""
Media Downloader CLI Entry Point
向后兼容的入口文件
"""
import sys
from pathlib import Path

# 确保模块路径正确
sys.path.insert(0, str(Path(__file__).parent))

from media_downloader.cli import main

if __name__ == '__main__':
    sys.exit(main())
