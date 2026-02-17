import asyncio
from playwright.async_api import async_playwright

async def save_reviews():
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
        
        # 查找评论项
        comment_items = await page.query_selector_all('.comment-item, .review-item, [class*="comment"]')
        
        print(f'找到 {len(comment_items)} 个评论相关元素\n')
        
        reviews = []
        for i, item in enumerate(comment_items):
            text = await item.inner_text()
            if text.strip() and ('ago' in text.lower() or '谢谢' in text or '确实' in text):
                print(f'[{i}] {text[:300]}...')
                print('-' * 50)
                reviews.append(text)
        
        # 保存到文件
        with open('.agents/skills/zlibrary-to-notebooklm/temp/reviews_found.txt', 'w', encoding='utf-8') as f:
            for r in reviews:
                f.write(r + '\n' + '='*50 + '\n')
        
        print(f'\n已保存 {len(reviews)} 条评论')
        
        # 也检查z-comments shadow DOM
        zcomments = await page.query_selector('z-comments')
        if zcomments:
            # 尝试获取shadow DOM内容
            shadow_html = await zcomments.evaluate('el => el.shadowRoot ? el.shadowRoot.innerHTML : el.innerHTML')
            with open('.agents/skills/zlibrary-to-notebooklm/temp/shadow_dom.html', 'w', encoding='utf-8') as f:
                f.write(shadow_html)
            print('Shadow DOM 内容已保存')
        
        await browser.close()

asyncio.run(save_reviews())
