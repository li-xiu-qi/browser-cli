#!/usr/bin/env python3
"""
Z-Library to NotebookLM 环境检查脚本
验证所有依赖是否正确安装
"""

import sys
from pathlib import Path

def check_python_dependencies():
    """检查 Python 依赖"""
    print("=" * 60)
    print("🔍 检查 Python 依赖")
    print("=" * 60)
    
    checks = []
    
    # 检查 playwright
    try:
        from playwright.sync_api import sync_playwright
        print("✅ Playwright: 已安装")
        checks.append(True)
    except ImportError as e:
        print(f"❌ Playwright: 未安装 ({e})")
        checks.append(False)
    
    # 检查 ebooklib
    try:
        from ebooklib import epub
        print("✅ ebooklib: 已安装")
        checks.append(True)
    except ImportError as e:
        print(f"❌ ebooklib: 未安装 ({e})")
        checks.append(False)
    
    # 检查 beautifulsoup4
    try:
        from bs4 import BeautifulSoup
        print("✅ BeautifulSoup4: 已安装")
        checks.append(True)
    except ImportError as e:
        print(f"❌ BeautifulSoup4: 未安装 ({e})")
        checks.append(False)
    
    # 检查 lxml
    try:
        import lxml
        print("✅ lxml: 已安装")
        checks.append(True)
    except ImportError as e:
        print(f"❌ lxml: 未安装 ({e})")
        checks.append(False)
    
    return all(checks)

def check_playwright_browsers():
    """检查 Playwright 浏览器"""
    print()
    print("=" * 60)
    print("🔍 检查 Playwright 浏览器")
    print("=" * 60)
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
                browser.close()
                print("✅ Chromium 浏览器: 已安装")
                return True
            except Exception as e:
                print(f"❌ Chromium 浏览器: 未安装 ({e})")
                print("💡 请运行: .venv\Scripts\python.exe -m playwright install chromium")
                return False
    except ImportError:
        print("❌ Playwright 未安装，无法检查浏览器")
        return False

def check_project_structure():
    """检查项目目录结构"""
    print()
    print("=" * 60)
    print("🔍 检查项目目录结构")
    print("=" * 60)
    
    project_root = Path(__file__).parent.parent.parent.parent
    skill_dir = project_root / ".agents" / "skills" / "notebooklm-uploader"
    
    checks = []
    
    # 检查下载目录
    downloads_dir = project_root / "resources" / "downloads" / "books"
    if downloads_dir.exists():
        print(f"✅ 下载目录: {downloads_dir}")
        checks.append(True)
    else:
        print(f"❌ 下载目录不存在: {downloads_dir}")
        checks.append(False)
    
    # 检查配置目录
    config_dir = skill_dir / "config"
    if config_dir.exists():
        print(f"✅ 配置目录: {config_dir}")
        checks.append(True)
    else:
        print(f"❌ 配置目录不存在: {config_dir}")
        checks.append(False)
    
    # 检查临时目录
    temp_dir = skill_dir / "temp"
    if temp_dir.exists():
        print(f"✅ 临时目录: {temp_dir}")
        checks.append(True)
    else:
        print(f"❌ 临时目录不存在: {temp_dir}")
        checks.append(False)
    
    # 检查脚本文件
    upload_script = skill_dir / "scripts" / "upload.py"
    login_script = skill_dir / "scripts" / "login.py"
    
    if upload_script.exists():
        print(f"✅ 上传脚本: {upload_script}")
        checks.append(True)
    else:
        print(f"❌ 上传脚本不存在: {upload_script}")
        checks.append(False)
    
    if login_script.exists():
        print(f"✅ 登录脚本: {login_script}")
        checks.append(True)
    else:
        print(f"❌ 登录脚本不存在: {login_script}")
        checks.append(False)
    
    return all(checks)

def main():
    """主函数"""
    print()
    print("🚀 Z-Library to NotebookLM 环境检查")
    print()
    
    py_deps_ok = check_python_dependencies()
    browser_ok = check_playwright_browsers()
    structure_ok = check_project_structure()
    
    print()
    print("=" * 60)
    print("📋 检查结果")
    print("=" * 60)
    
    if py_deps_ok and browser_ok and structure_ok:
        print("✅ 所有检查通过！环境配置正确。")
        print()
        print("💡 首次使用请先运行登录脚本:")
        print("   .venv\\Scripts\\python.exe .agents\\tools\\zlibrary\\login.py")
        return 0
    else:
        print("❌ 环境检查未通过，请修复上述问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())
