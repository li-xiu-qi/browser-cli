"""配置文件."""

import json
from pathlib import Path

# 默认配置
DEFAULT_CONFIG = {
    "app_id": 122089754,
    "base_url": "https://pan.baidu.com/rest/2.0/xpan",
    "transcribe_url": "https://pan.baidu.com/apaas/1.0/bas/aitrans/video2doc",
}

# Token 文件路径（支持多种路径）
TOKEN_FILE_PATHS = [
    # 相对于工具目录的路径
    Path(__file__).parent.parent.parent.parent.parent / "Projects/2026-02-百度网盘自动化集成/.token_info.json",
    # 相对于当前工作目录的路径
    Path("Projects/2026-02-百度网盘自动化集成/.token_info.json"),
    # 绝对路径（从笔记专用根目录）
    Path("C:/Users/ke/Documents/projects/obsidian_projects/笔记专用/Projects/2026-02-百度网盘自动化集成/.token_info.json"),
]


def get_token_file() -> Path:
    """查找 token 文件."""
    for path in TOKEN_FILE_PATHS:
        if path.exists():
            return path
    # 返回默认路径
    return TOKEN_FILE_PATHS[0]


TOKEN_FILE = get_token_file()


def get_access_token() -> str:
    """从 token 文件获取 access_token."""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("access_token", "")
    return ""


def get_app_id() -> int:
    """获取 App ID."""
    return DEFAULT_CONFIG["app_id"]


def get_base_url() -> str:
    """获取 API 基础 URL."""
    return DEFAULT_CONFIG["base_url"]


def get_transcribe_url() -> str:
    """获取转录 API URL."""
    return DEFAULT_CONFIG["transcribe_url"]
