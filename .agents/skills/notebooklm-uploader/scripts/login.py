#!/usr/bin/env python3
"""
Z-Library Login - 自动保存会话状态

统一使用 .agents/browser_user_data/ 作为浏览器数据目录
关闭浏览器时自动保存 storage_state.json 和 token
"""

import sys
import time
import json
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("❌ Playwright 未安装")
    print("请运行: .venv\\Scripts\\python.exe -m pip install playwright")
    sys.exit(1)


def extract_tokens_from_cookies(cookies):
    """从 cookies 中提取 Z-Library token"""
    tokens = {}
    for cookie in cookies:
        name = cookie.get('name', '')
        if name == 'remix_userid':
            tokens['remix_userid'] = cookie.get('value')
        elif name == 'remix_userkey':
            tokens['remix_userkey'] = cookie.get('value')
    return tokens


def save_session(storage_state_path, config_dir, context):
    """保存浏览器会话状态"""
    token_file = config_dir / "zl_tokens.json"
    
    try:
        # 保存完整的 storage_state
        context.storage_state(path=str(storage_state_path))
        
        # 读取并显示 cookies 信息
        with open(storage_state_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cookies = data.get('cookies', [])
        print(f"\n📊 共导出 {len(cookies)} 个 cookies")
        
        # 查找 Z-Library 相关的 cookies
        zlib_cookies = [c for c in cookies if 'zlib' in c.get('domain', '') or 'z-lib' in c.get('domain', '')]
        if zlib_cookies:
            print(f"✅ 找到 {len(zlib_cookies)} 个 Z-Library cookies:")
            for c in zlib_cookies:
                name = c.get('name')
                value = c.get('value', '')
                display_value = value[:30] + '...' if len(value) > 30 else value
                print(f"   - {name}: {display_value}")
        
        # 提取关键 token
        tokens = extract_tokens_from_cookies(cookies)
        
        if tokens.get('remix_userid') and tokens.get('remix_userkey'):
            with open(token_file, 'w', encoding='utf-8') as f:
                json.dump(tokens, f, indent=2)
            print(f"\n✅ Token 已保存到: {token_file}")
            return True
        else:
            print("\n⚠️ 未找到登录 token，可能登录未成功")
            return False
        
    except Exception as e:
        print(f"\n⚠️ 保存会话时出错: {e}")
        return False


def zlibrary_login():
    """Z-Library 登录并保存会话"""
    
    # 统一使用共享的浏览器数据目录
    project_root = Path(__file__).parent.parent.parent.parent.parent
    shared_user_data = project_root / ".agents" / "browser_user_data"
    shared_user_data.mkdir(parents=True, exist_ok=True)
    
    # Z-Library 专用配置目录
    config_dir = project_root / ".agents" / "tools" / "zlibrary" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    storage_state_path = config_dir / "storage_state.json"

    print("="*70)
    print("🔐 Z-Library 登录")
    print("="*70)
    print("")
    print("说明:")
    print("  1. 浏览器会自动打开并访问 Z-Library")
    print("  2. 请手动完成登录")
    print("  3. 登录成功后，回到此终端按 Enter 键保存")
    print("  4. 或直接关闭浏览器退出")
    print("")
    print(f"📁 浏览器数据目录: {shared_user_data}")
    print("")

    browser = None
    context = None
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
        
        # 在持久化上下文中，pages[0] 已经存在
        page = browser.pages[0] if browser.pages else browser.new_page()
        
        try:
            print("📖 访问 Z-Library...")
            page.goto("https://zh.zlib.li/", wait_until='domcontentloaded', timeout=30000)

            print("")
            print("="*70)
            print("📋 操作步骤:")
            print("="*70)
            print("1. 在浏览器中完成登录")
            print("2. 确保看到已登录的 Z-Library 主页")
            print("3. 回到此终端按 Enter 键保存 session")
            print("   (或按 Ctrl+C 直接退出不保存)")
            print("="*70)
            print("")
            
            # 等待用户按 Enter
            try:
                input("⏳ 登录完成后请按 Enter 键保存 session...")
                
                # 保存会话
                print("\n" + "="*70)
                print("💾 正在保存会话状态...")
                print("="*70)
                
                saved = save_session(storage_state_path, config_dir, browser)
                
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
                print("")
                print("💡 现在可以使用搜索功能了：")
                print("   .venv\\Scripts\\python.exe .agents\\tools\\zlibrary\\zlib_api.py auto \"书名\"")
            else:
                print("⚠️ 未保存 session，请重新运行登录脚本")
            print("")
            print("👋 脚本已退出")


def main():
    """主函数"""
    zlibrary_login()


if __name__ == "__main__":
    main()
