#!/usr/bin/env python3
"""
浏览器登录工具 - 通用版

统一使用 .agents/browser_user_data/ 作为浏览器数据目录
支持任意网站的登录，保存 session 供其他工具使用

使用方法:
    python login.py <url> [--name <site_name>]

示例:
    python login.py https://zh.zlib.li --name zlibrary
    python login.py https://www.example.com --name example
"""

import sys
import time
import json
from pathlib import Path
from urllib.parse import urlparse

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright 未安装")
    print("请运行: .venv\\Scripts\\python.exe -m pip install playwright")
    sys.exit(1)


def save_cookies(context, config_dir, site_name):
    """保存 cookies 到文件"""
    cookies_file = config_dir / f"{site_name}_cookies.json"
    
    try:
        # 获取 cookies
        cookies = context.cookies()
        
        # 保存到文件
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, indent=2, ensure_ascii=False)
        
        print(f"\n📊 共导出 {len(cookies)} 个 cookies")
        
        # 显示关键 cookies
        important_cookies = ['session', 'token', 'auth', 'user', 'login', 'id', 'key']
        found_important = []
        for cookie in cookies:
            name = cookie.get('name', '').lower()
            if any(key in name for key in important_cookies):
                value = cookie.get('value', '')
                display_value = value[:30] + '...' if len(value) > 30 else value
                found_important.append(f"   - {cookie.get('name')}: {display_value}")
        
        if found_important:
            print(f"✅ 关键 cookies:")
            for line in found_important[:5]:  # 只显示前5个
                print(line)
        
        print(f"\n✅ Cookies 已保存到: {cookies_file}")
        return True
        
    except Exception as e:
        print(f"⚠️ 保存 cookies 时出错: {e}")
        return False


def browser_login(url: str, site_name: str = None):
    """
    通用浏览器登录
    
    Args:
        url: 登录页面 URL
        site_name: 站点名称（用于保存 cookies 文件名）
    """
    # 如果没有提供 site_name，从 URL 解析
    if not site_name:
        parsed = urlparse(url)
        site_name = parsed.netloc.replace('.', '_')
    
    # 统一使用共享的浏览器数据目录
    # 从 browser-login/login.py → tools → .agents → 项目根目录
    project_root = Path(__file__).parent.parent.parent.parent
    shared_user_data = project_root / ".agents" / "browser_user_data"
    shared_user_data.mkdir(parents=True, exist_ok=True)
    
    # 配置目录
    config_dir = project_root / ".agents" / "tools" / "browser-login" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print(f"🔐 浏览器登录 - {site_name}")
    print("="*70)
    print(f"目标: {url}")
    print("")
    print("说明:")
    print("  1. 浏览器会自动打开目标网站")
    print("  2. 请手动完成登录")
    print("  3. 登录成功后，回到此终端按 Enter 键保存")
    print("  4. 或直接关闭浏览器退出")
    print("")
    print(f"📁 浏览器数据目录: {shared_user_data}")
    print(f"💾 配置保存目录: {config_dir}")
    print("")

    browser = None
    saved = False
    
    with sync_playwright() as p:
        print("🚀 启动浏览器...")
        
        # 使用持久化上下文模式
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(shared_user_data),
            headless=False,
            args=['--disable-blink-features=AutomationControlled'],
            viewport={'width': 1280, 'height': 800}
        )
        
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        try:
            print(f"📖 访问: {url}")
            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            print("")
            print("="*70)
            print("📋 操作步骤:")
            print("="*70)
            print("1. 在浏览器中完成登录")
            print("2. 确保看到已登录的页面")
            print("3. 回到此终端按 Enter 键保存 cookies")
            print("   (或按 Ctrl+C 直接退出不保存)")
            print("="*70)
            print("")
            
            # 等待用户按 Enter
            try:
                input("⏳ 登录完成后请按 Enter 键保存 session...")
                
                # 保存 cookies
                print("\n" + "="*70)
                print("💾 正在保存 cookies...")
                print("="*70)
                
                saved = save_cookies(browser, config_dir, site_name)
                
            except KeyboardInterrupt:
                print("\n\n⚠️ 已取消保存")

        except Exception as e:
            print(f"\n❌ 发生错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 确保浏览器已关闭
            try:
                if browser:
                    browser.close()
            except:
                pass
            
            print("")
            if saved:
                print("✅ 登录 session 已保存!")
                print(f"   站点: {site_name}")
                print(f"   配置: {config_dir / (site_name + '_cookies.json')}")
            else:
                print("⚠️ 未保存 session")
            print("")
            print("👋 脚本已退出")


def list_saved_sessions():
    """列出已保存的登录 session"""
    config_dir = Path(__file__).parent / "config"
    
    if not config_dir.exists():
        print("❌ 配置目录不存在")
        return
    
    cookie_files = list(config_dir.glob("*_cookies.json"))
    
    if not cookie_files:
        print("ℹ️ 没有找到已保存的登录 session")
        return
    
    print("📋 已保存的登录 session:")
    print("=" * 70)
    for f in cookie_files:
        site_name = f.stem.replace('_cookies', '')
        # 获取文件修改时间
        mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(f.stat().st_mtime))
        print(f"  • {site_name}")
        print(f"    文件: {f.name}")
        print(f"    时间: {mtime}")
    print("=" * 70)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("浏览器登录工具 - 通用版")
        print("")
        print("用法:")
        print("  1. 登录网站:")
        print("     python login.py <url> [--name <site_name>]")
        print("")
        print("  2. 查看已保存的 session:")
        print("     python login.py --list")
        print("")
        print("示例:")
        print("  python login.py https://zh.zlib.li --name zlibrary")
        print("  python login.py https://example.com")
        print("  python login.py --list")
        sys.exit(1)
    
    if sys.argv[1] == '--list':
        list_saved_sessions()
        return
    
    url = sys.argv[1]
    site_name = None
    
    # 解析参数
    if '--name' in sys.argv:
        name_idx = sys.argv.index('--name')
        if name_idx + 1 < len(sys.argv):
            site_name = sys.argv[name_idx + 1]
    
    browser_login(url, site_name)


if __name__ == "__main__":
    main()
