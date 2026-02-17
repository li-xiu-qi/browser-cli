import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir='.agents/browser_user_data',
            headless=False,  # 显示浏览器看看
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        await page.goto('https://1lib.sk/book/14003399/877ca6', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(5)
        
        # 滚动页面加载更多内容
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(2)
        
        # 查找评论相关文本
        page_text = await page.inner_text('body')
        
        # 检查是否有评论关键词
        if 'review' in page_text.lower() or '评论' in page_text or '评价' in page_text:
            print('页面包含评论相关关键词')
        
        # 查找特定元素
        # 尝试点击"评论"或"Reviews"按钮/链接
        review_links = await page.query_selector_all('a:has-text("Review"), a:has-text("review"), a:has-text("评论")')
        print(f'找到 {len(review_links)} 个评论链接')
        
        # 获取页面所有文本块
        texts = await page.query_selector_all('p, div')
        for elem in texts:
            text = await elem.inner_text()
            if len(text) > 50 and len(text) < 500:  # 可能是评论的文本长度
                print(f'Text: {text[:200]}...')
                print('-' * 50)
                break  # 只显示一个
        
        await asyncio.sleep(10)  # 让用户看看页面
        await browser.close()

asyncio.run(debug())
