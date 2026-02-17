#!/usr/bin/env python3
"""
Z-Library 登录脚本

基于通用 browser-login 工具的包装器。
登录成功后，Z-Library API 会自动从 browser_user_data 提取 token。

使用方法:
    uv run python login.py

登录步骤:
    1. 浏览器自动打开 Z-Library
    2. 手动完成登录
    3. 按 Enter 保存 session
    4. API 会自动提取 token（无需手动操作）
"""

import sys
from pathlib import Path

# 添加 browser-login 到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "tools" / "browser-login"))

try:
    from login import browser_login
except ImportError as e:
    print("❌ 无法导入 browser-login 工具")
    print(f"错误: {e}")
    print("请确保 .agents/tools/browser-login/login.py 存在")
    sys.exit(1)


def main():
    """Z-Library 登录入口"""
    print("="*70)
    print("🔐 Z-Library 登录")
    print("="*70)
    print("")
    print("📖 使用说明:")
    print("-" * 70)
    print("1. 浏览器将自动打开 Z-Library 网站")
    print("2. 请在浏览器中手动完成登录（输入账号密码）")
    print("3. 登录成功后，回到此窗口按 Enter 键保存")
    print("")
    print("💡 提示:")
    print("   - 登录成功后，API 会自动提取 token，无需手动操作")
    print("   - Token 长期有效，下次直接使用")
    print("   - 如遇问题，删除 zl_tokens.json 后重新登录")
    print("="*70)
    print("")
    
    # 调用通用登录工具
    browser_login("https://zh.zlib.li/", "zlibrary")
    
    print("")
    print("✅ 登录流程已完成！")
    print("")
    print("📚 现在可以使用 Z-Library API 搜索下载书籍:")
    print('   uv run python zlib_api.py auto "书名" --format pdf')
    print("")


if __name__ == "__main__":
    main()
