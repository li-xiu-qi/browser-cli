import asyncio
from playwright.async_api import async_playwright

async def fetch_reviews():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir='.agents/browser_user_data',
            headless=True,  # 无头模式更快
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        url = 'https://zh.z-library.sk/book/Yv3yoaz9Rm/%E7%88%86%E6%AC%BE%E6%96%87%E6%A1%88%E5%86%99%E4%BD%9C%E6%8C%87%E5%8D%97%E6%95%85%E4%BA%8B%E8%90%A5%E9%94%80%E7%9A%8424%E5%A0%82%E6%A0%B8%E5%BF%83%E8%AF%BE%E7%A8%8B%E5%8F%AF%E6%8B%86%E8%A7%A3%E5%8F%AF%E5%A4%8D%E5%88%B6%E4%BB%BB%E4%BD%95%E4%BA%BA%E9%83%BD%E5%8F%AF%E4%BB%A5%E5%AD%A6%E4%BC%9A%E7%9A%84%E7%88%86%E6%AC%BE%E6%96%87%E6%A1%88%E5%86%99%E4%BD%9C%E6%8C%87%E5%8D%97-%E4%B8%A4%E5%B0%8F%E6%97%B6%E5%AD%A6%E4%BC%9A%E6%95%85%E4%BA%8B%E8%90%A5%E9%94%80%E7%9A%8424%E5%A0%82%E6%A0%B8%E5%BF%83%E8%AF%BE%E5%92%8C%E5%AE%9E%E7%94%A8%E5%85%AC%E5%BC%8F.html'
        
        print(f'访问页面...')
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        await asyncio.sleep(3)
        
        # 保存HTML
        html = await page.content()
        with open('.agents/skills/zlibrary-to-notebooklm/temp/review_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        
        # 查找评论相关元素
        selectors = [
            '.comment', '.review', '.rating', 
            '[class*="comment"]', '[class*="review"]', '[class*="rating"]',
            '.book-comment', '.user-review'
        ]
        
        print('\n查找评论元素:')
        found = False
        for sel in selectors:
            try:
                elems = await page.query_selector_all(sel)
                if elems:
                    print(f'\n✅ {sel}: {len(elems)} 个')
                    found = True
                    # 显示第一个的结构
                    html_content = await elems[0].inner_html()
                    print(f'HTML: {html_content[:500]}')
            except:
                pass
        
        if not found:
            print('没有找到标准评论元素，查找包含"评论"文本的元素...')
            # 尝试查找包含"评论"的元素
            all_elems = await page.query_selector_all('*')
            for elem in all_elems:
                try:
                    text = await elem.inner_text()
                    if text and ('评论' in text or '评价' in text) and len(text) < 100:
                        tag = await elem.evaluate('el => el.tagName')
                        cls = await elem.get_attribute('class') or ''
                        print(f'<{tag} class="{cls}">: {text[:50]}')
                except:
                    pass
        
        await browser.close()
        print('\n✅ 完成！HTML已保存到 temp/review_page.html')

asyncio.run(fetch_reviews())
