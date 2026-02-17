import asyncio
from playwright.async_api import async_playwright

async def extract():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir='.agents/browser_user_data',
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        url = 'https://zh.z-library.sk/book/Yv3yoaz9Rm/%E7%88%86%E6%AC%BE%E6%96%87%E6%A1%88%E5%86%99%E4%BD%9C%E6%8C%87%E5%8D%97.html'
        
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await asyncio.sleep(5)
        
        # 获取页面所有文本
        page_text = await page.inner_text('body')
        
        # 查找评论相关内容
        import re
        
        # 查找时间+评论的模式
        # 模式：时间（如 "3 years ago"）后面跟着评论内容
        time_comment_pattern = r'(\d+\s+(?:years?|months?|days?|hours?)\s+ago)([^\n]{10,500})'
        matches = re.findall(time_comment_pattern, page_text, re.IGNORECASE)
        
        print(f'找到 {len(matches)} 条评论:\n')
        for i, (time, comment) in enumerate(matches[:10]):
            comment = comment.strip().replace('\n', ' ')
            print(f'[{i+1}] 时间: {time}')
            print(f'    评论: {comment[:200]}...')
            print()
        
        # 保存完整页面文本用于分析
        with open('.agents/skills/zlibrary-to-notebooklm/temp/page_text.txt', 'w', encoding='utf-8') as f:
            f.write(page_text)
        
        print('页面文本已保存到 page_text.txt')
        await browser.close()

asyncio.run(extract())
