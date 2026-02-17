import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir='.agents/browser_user_data',
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        await page.goto('https://1lib.sk/book/14003399/877ca6', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        
        # 获取所有评论相关元素
        elems = await page.query_selector_all('[class*="review"]')
        print(f'找到 {len(elems)} 个包含 review 的元素')
        
        for i, elem in enumerate(elems[:5]):
            class_name = await elem.get_attribute('class')
            text = await elem.inner_text()
            print(f'\n[{i}] class={class_name}')
            print(f'text={text[:300]}...')
            print('-' * 50)
        
        await browser.close()

asyncio.run(debug())
