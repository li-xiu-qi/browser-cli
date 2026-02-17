# 浏览器登录工具 - 通用版

通用的浏览器登录工具，支持任意网站的登录，将 session 保存到**共享浏览器数据目录**，供其他工具使用。

## 特点

- **通用**: 支持任意网站登录
- **共享**: 使用 `.agents/browser_user_data/` 共享浏览器数据
- **持久化**: 基于 Playwright 持久化上下文，session 长期有效
- **简单**: 一行命令完成登录

## 架构设计

```
┌─────────────────────────────────────────────────────────────────────┐
│                         通用登录流程                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐         ┌──────────────────────────────┐        │
│   │ 用户执行登录  │  ──▶   │ browser-login 启动浏览器      │        │
│   │   命令       │         │ (使用 browser_user_data)      │        │
│   └──────────────┘         └──────────────────────────────┘        │
│                                         │                          │
│                                         ▼                          │
│                            ┌──────────────────────────────┐        │
│                            │ 用户手动登录目标网站          │        │
│                            │ 输入账号密码，完成验证        │        │
│                            └──────────────────────────────┘        │
│                                         │                          │
│                                         ▼                          │
│                            ┌──────────────────────────────┐        │
│                            │ 按 Enter 保存 session        │        │
│                            │ 数据写入 browser_user_data   │        │
│                            └──────────────────────────────┘        │
│                                         │                          │
│                                         ▼                          │
│   ┌────────────────────────────────────────────────────────────┐   │
│   │                    其他工具使用                              │   │
│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │   │
│   │  │ Z-Library API│  │ Web Clipper  │  │ 其他工具...      │   │   │
│   │  │ 提取 token   │  │ 读取 cookies │  │ 读取所需数据     │   │   │
│   │  └──────────────┘  └──────────────┘  └─────────────────┘   │   │
│   └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 使用方法

### 登录网站

```powershell
uv run python .agents/tools/browser-login/login.py <URL> [--name <站点名称>]
```

**示例:**

```powershell
# Z-Library 登录
uv run python .agents/tools/browser-login/login.py https://zh.zlib.li --name zlibrary

# 微信网页版（用于抓取公众号文章）
uv run python .agents/tools/browser-login/login.py https://wx.qq.com --name wechat

# 其他网站登录
uv run python .agents/tools/browser-login/login.py https://example.com --name example
```

**操作步骤:**
1. 浏览器自动打开目标网站
2. 手动完成登录（输入账号密码）
3. 看到已登录页面后，回到终端按 **Enter** 保存 session
4. 数据自动保存到 `.agents/browser_user_data/`

### 查看已保存的 session

```powershell
uv run python .agents/tools/browser-login/login.py --list
```

## 其他工具如何使用

### 方式 1: 直接读取 Cookies 文件（推荐简单场景）

```python
import json
from pathlib import Path

# 读取指定站点的 cookies
cookies_file = Path(".agents/tools/browser-login/config/zlibrary_cookies.json")
with open(cookies_file, 'r') as f:
    cookies = json.load(f)

# 使用 cookies 进行请求
```

### 方式 2: 启动浏览器会话读取（推荐复杂场景）

适用于需要从浏览器数据中提取特定 token 的场景（如 Z-Library）：

```python
from playwright.sync_api import sync_playwright
from pathlib import Path

def extract_from_browser(browser_data_dir: Path):
    with sync_playwright() as p:
        # 启动持久化上下文（读取已有的 browser_user_data）
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(browser_data_dir),
            headless=True,  # 无头模式
        )
        
        # 获取所有 cookies
        cookies = browser.cookies()
        browser.close()
        
        # 提取特定 token
        for cookie in cookies:
            if cookie['name'] == 'target_token':
                return cookie['value']
        
        return None
```

### 方式 3: 各工具自行处理（如 Z-Library API）

Z-Library API 内部实现：
1. 检查本地 `zl_tokens.json`
2. 如不存在，启动浏览器会话从 `browser_user_data` 提取
3. 提取后保存到本地，下次直接使用

参考实现: `.agents/skills/resource-crawler/tools/zlibrary/zlib_api.py`

## 配置目录

| 数据类型 | 路径 | 说明 |
|----------|------|------|
| 浏览器数据 | `.agents/browser_user_data/` | **核心目录**，包含所有登录状态 |
| Cookies 导出 | `.agents/tools/browser-login/config/<site>_cookies.json` | 备份导出 |

## 最佳实践

### 1. 登录与使用分离

```bash
# 1. 先登录（只需一次）
uv run python .agents/tools/browser-login/login.py https://site.com --name site

# 2. 各工具独立使用，自动读取 session
# （无需关心登录细节）
```

### 2. 多站点管理

```bash
# 不同站点使用不同名称
uv run python .agents/tools/browser-login/login.py https://zh.zlib.li --name zlibrary
uv run python .agents/tools/browser-login/login.py https://wx.qq.com --name wechat
```

### 3. 登录失效处理

```bash
# 检查已保存的 session
uv run python .agents/tools/browser-login/login.py --list

# 删除特定站点的 cookies（如需重新登录）
rm .agents/tools/browser-login/config/<site>_cookies.json

# 或清除整个 browser_user_data（彻底重置）
rm -rf .agents/browser_user_data/*
```

## 注意事项

1. **安全**: `browser_user_data` 包含敏感登录信息，请勿上传到 GitHub
2. **共享**: 所有工具共享同一目录，登录一次多处使用
3. **持久化**: 只要不删除 `browser_user_data`，session 长期有效
4. **冲突**: 同一网站多账号登录会覆盖，建议同一网站使用固定账号

## 集成示例

### 为自己的工具添加登录支持

```python
from pathlib import Path
from playwright.sync_api import sync_playwright

class MyTool:
    def __init__(self):
        self.browser_data = Path(".agents/browser_user_data")
    
    def ensure_login(self):
        """确保已登录，如未登录则启动浏览器让用户登录"""
        if not self._check_login():
            print("请先登录...")
            self._launch_login_browser()
    
    def _launch_login_browser(self):
        """启动浏览器让用户登录"""
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(self.browser_data),
                headless=False,  # 有头模式，方便用户操作
            )
            page = browser.new_page()
            page.goto("https://your-site.com/login")
            input("登录完成后按 Enter...")
            browser.close()
```
