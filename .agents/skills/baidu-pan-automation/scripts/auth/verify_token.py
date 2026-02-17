#!/usr/bin/env python3
"""验证 token 是否有效"""
import requests
import json
from pathlib import Path

# 直接从 token_info.json 读取
token_path = Path(__file__).parent.parent / '.token_info.json'
with open(token_path, 'r') as f:
    token_data = json.load(f)

ACCESS_TOKEN = token_data['access_token']

print("="*60)
print("🔑 Token 验证")
print("="*60)
print(f"\nToken: {ACCESS_TOKEN[:30]}...")

# 测试 API 调用
url = "https://pan.baidu.com/rest/2.0/xpan/nas"
params = {
    'method': 'uinfo',
    'access_token': ACCESS_TOKEN
}

try:
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    if data.get('errno') == 0:
        print("\n✅ Token 有效！")
        print(f"\n用户信息:")
        print(f"   用户名: {data.get('baidu_name', 'N/A')}")
        print(f"   用户ID: {data.get('uk', 'N/A')}")
        print(f"   VIP类型: {data.get('vip_type', 'N/A')}")
    elif data.get('errno') == -6 or data.get('errno') == 31034:
        print("\n❌ Token 已过期！")
        print(f"   错误码: {data.get('errno')}")
        print(f"   需要重新授权获取新的 token")
    else:
        print(f"\n⚠️ API 返回错误: {data}")
        
except Exception as e:
    print(f"\n❌ 请求失败: {e}")
