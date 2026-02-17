#!/usr/bin/env python3
"""
百度网盘简化模式授权 - 自动获取 Access Token
使用 Playwright 自动完成浏览器授权流程

使用方法:
    python scripts/get_access_token.py

流程:
    1. 自动打开百度授权页面
    2. 用户手动登录百度账号（如未登录）
    3. 用户点击"同意授权"
    4. 脚本自动提取 access_token
    5. 保存到 MCP 配置文件
"""
import asyncio
import json
import urllib.parse
from playwright.async_api import async_playwright

# 你的应用凭证
APP_KEY = "s4muIqE7Nv9sXk6IV841pQc7iUEQwZiP"
APP_ID = "122089754"

# 授权 URL（使用 oob 表示不跳转，token 会在 URL fragment 中）
AUTH_URL = (
    f"https://openapi.baidu.com/oauth/2.0/authorize?"
    f"response_type=token&"
    f"client_id={APP_KEY}&"
    f"redirect_uri=oob&"
    f"scope=basic,netdisk&"
    f"display=page"
)


async def get_access_token():
    """通过简化模式获取 access_token"""
    
    print("=" * 60)
    print("🚀 百度网盘 Access Token 获取工具")
    print("=" * 60)
    print()
    
    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        
        page = await context.new_page()
        
        # 监听所有请求和导航
        token_data = {}
        
        async def handle_route(route, request):
            """拦截请求，检查是否包含 access_token"""
            url = request.url
            if "access_token=" in url:
                print(f"\n🎯 检测到包含 token 的 URL!")
                print(f"URL: {url[:100]}...")
                
                # 解析 URL fragment 中的参数
                if "#" in url:
                    fragment = url.split("#")[1]
                    params = urllib.parse.parse_qs(fragment)
                    
                    for key, value in params.items():
                        token_data[key] = value[0] if value else ""
                    
                    print(f"\n✅ 成功提取到以下信息:")
                    for key, value in token_data.items():
                        if key in ['access_token', 'refresh_token', 'expires_in', 'scope']:
                            display_value = value[:30] + "..." if len(value) > 30 else value
                            print(f"  {key}: {display_value}")
            
            await route.continue_()
        
        # 监听页面导航
        async def handle_navigate(frame):
            url = frame.url
            print(f"📍 页面导航到: {url[:80]}...")
            
            # 检查 URL 中是否有 access_token
            if "access_token=" in url:
                print(f"\n🎯 检测到包含 token 的 URL!")
                
                if "#" in url:
                    fragment = url.split("#")[1]
                    params = urllib.parse.parse_qs(fragment)
                    
                    for key, value in params.items():
                        token_data[key] = value[0] if value else ""
                    
                    print(f"\n✅ 成功提取到以下信息:")
                    for key, value in token_data.items():
                        if key in ['access_token', 'refresh_token', 'expires_in', 'scope']:
                            display_value = value[:30] + "..." if len(value) > 30 else value
                            print(f"  {key}: {display_value}")
                    
                    # 关闭浏览器
                    await browser.close()
        
        page.on("framenavigated", lambda frame: asyncio.create_task(handle_navigate(frame)))
        
        print("🌐 正在打开百度授权页面...")
        print(f"URL: {AUTH_URL}")
        print()
        
        await page.goto(AUTH_URL)
        
        print("📋 请按以下步骤操作:")
        print("  1. 如果未登录，请输入百度账号密码登录")
        print("  2. 点击页面上的【同意授权】按钮")
        print("  3. 授权成功后，脚本会自动提取 token")
        print()
        
        # 等待用户完成授权
        max_wait = 300  # 最多等待 5 分钟
        for i in range(max_wait):
            if token_data.get('access_token'):
                break
            await asyncio.sleep(1)
            if i % 10 == 0:
                print(f"⏳ 等待授权中... ({i}s)")
        
        if not token_data.get('access_token'):
            print("\n❌ 等待超时，未能获取到 access_token")
            print("提示: 请确保点击了【同意授权】按钮")
            await browser.close()
            return None
        
        # 保存配置
        print("\n" + "=" * 60)
        print("💾 保存配置...")
        
        # 1. 保存到 .agents/mcp.json
        agents_config = {
            "mcpServers": {
                "baidu-netdisk": {
                    "url": f"https://mcp-pan.baidu.com/sse?access_token={token_data['access_token']}"
                }
            }
        }
        
        agents_path = ".agents/mcp.json"
        with open(agents_path, 'w') as f:
            json.dump(agents_config, f, indent=2)
        print(f"✅ MCP 配置已保存: {agents_path}")
        
        # 2. 保存到项目 .env
        env_content = f"""# 百度网盘开放平台凭证
BAIDU_PAN_APP_ID={APP_ID}
BAIDU_PAN_APP_KEY={APP_KEY}

# Access Token（简化模式获取，有效期30天）
BAIDU_PAN_ACCESS_TOKEN={token_data['access_token']}

# Token 信息
# 过期时间: {token_data.get('expires_in', 'unknown')} 秒
# Scope: {token_data.get('scope', 'unknown')}
# 获取时间: {asyncio.get_event_loop().time()}
"""
        
        env_path = "Projects/2026-02-百度网盘自动化集成/.env"
        with open(env_path, 'w') as f:
            f.write(env_content)
        print(f"✅ 环境变量已保存: {env_path}")
        
        # 3. 保存完整 token 信息
        token_info_path = "Projects/2026-02-百度网盘自动化集成/.token_info.json"
        with open(token_info_path, 'w') as f:
            json.dump(token_data, f, indent=2)
        print(f"✅ Token 详情已保存: {token_info_path}")
        
        print("\n" + "=" * 60)
        print("🎉 授权成功！")
        print("=" * 60)
        print(f"\nAccess Token: {token_data['access_token'][:40]}...")
        print(f"有效期: {int(token_data.get('expires_in', 0)) // 86400} 天")
        print(f"\n现在你可以使用以下命令测试 MCP:")
        print(f"  kimi --mcp-config-file .agents/mcp.json")
        print()
        
        return token_data


if __name__ == "__main__":
    try:
        result = asyncio.run(get_access_token())
        if result:
            print("✨ 完成！")
        else:
            print("❌ 获取失败")
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
