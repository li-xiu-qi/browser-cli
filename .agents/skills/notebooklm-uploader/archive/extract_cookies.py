#!/usr/bin/env python3
"""
从 Playwright 保存的 storage_state.json 中提取 Z-Library 登录 token
"""

import json
from pathlib import Path


def extract_zlibrary_tokens():
    """提取 Z-Library 登录 token"""
    
    # 项目路径
    project_root = Path(__file__).parent.parent.parent.parent
    config_dir = project_root / ".agents" / "skills" / "zlibrary-to-notebooklm" / "config"
    storage_state = config_dir / "storage_state.json"
    
    if not storage_state.exists():
        print("❌ 未找到会话文件")
        print(f"💡 请先运行登录脚本: python scripts/login.py")
        return None
    
    print("🔍 正在读取会话文件...")
    
    with open(storage_state, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 查找 cookies
    cookies = data.get('cookies', [])
    
    remix_userid = None
    remix_userkey = None
    
    for cookie in cookies:
        name = cookie.get('name', '')
        if name == 'remix_userid':
            remix_userid = cookie.get('value')
        elif name == 'remix_userkey':
            remix_userkey = cookie.get('value')
    
    if remix_userid and remix_userkey:
        print("\n✅ 成功提取到登录 token！")
        print(f"   remix_userid: {remix_userid}")
        print(f"   remix_userkey: {remix_userkey[:20]}..." if len(remix_userkey) > 20 else f"   remix_userkey: {remix_userkey}")
        
        # 保存到单独的 token 文件
        token_file = config_dir / "zl_tokens.json"
        with open(token_file, 'w', encoding='utf-8') as f:
            json.dump({
                'remix_userid': remix_userid,
                'remix_userkey': remix_userkey
            }, f, indent=2)
        
        print(f"\n💾 Token 已保存到: {token_file}")
        return {
            'remix_userid': remix_userid,
            'remix_userkey': remix_userkey
        }
    else:
        print("\n❌ 未找到登录 token")
        print("   可能 cookies 已过期或登录未成功")
        return None


if __name__ == "__main__":
    extract_zlibrary_tokens()
