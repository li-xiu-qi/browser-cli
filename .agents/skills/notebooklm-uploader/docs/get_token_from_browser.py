#!/usr/bin/env python3
"""
从浏览器获取 Z-Library token 的指南
"""

print("""
🔐 获取 Z-Library 登录 Token 的方法
=====================================

方法一：从浏览器开发者工具获取（推荐）
---------------------------------------

1. 在浏览器中打开 https://zh.zlib.li/ 并登录

2. 按 F12 打开开发者工具，切换到 "Application"（应用）标签

3. 在左侧菜单找到 "Storage" -> "Cookies" -> "https://zh.zlib.li"

4. 找到以下两个 cookie：
   - remix_userid
   - remix_userkey

5. 复制这两个值

方法二：从浏览器地址栏获取
--------------------------

1. 登录 Z-Library 后，查看地址栏
2. 如果 URL 中有类似 `?remix_userid=12345&remix_userkey=abc...` 的参数
3. 复制这两个参数的值

保存 Token
----------

获取到 token 后，运行以下命令保存：

```powershell
cd .agents/skills/zlibrary-to-notebooklm
.venv\\Scripts\\python.exe save_token.py <remix_userid> <remix_userkey>
```

示例：
```powershell
.venv\\Scripts\\python.exe save_token.py 12345678 abcdef123456...
```

验证 Token
----------

保存后，可以运行以下命令验证：

```powershell
.venv\\Scripts\\python.exe search_with_login.py "测试"
```

""")
