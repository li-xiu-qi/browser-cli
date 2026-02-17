import asyncio
from playwright.async_api import async_playwright

async def fetch_reviews():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir='.agents/browser_user_data',
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        
        url = 'https://zh.z-library.sk/book/Yv3yoaz9Rm/%E7%88%86%E6%AC%BE%E6%96%87%E6%A1%88%E5%86%99%E4%BD%9C%E6%8C%87%E5%8D%97.html'
        
        print('访问页面...')
        await page.goto(url, wait_until='networkidle', timeout=60000)
        
        # 等待评论组件加载
        print('等待评论组件加载...')
        try:
            await page.wait_for_selector('z-comments', timeout=10000)
        except:
            print('z-comments 组件未找到')
        
        # 再等待几秒让评论数据加载
        await asyncio.sleep(5)
        
        # 查找评论内容
        print('\n查找评论内容:')
        
        # 1. 直接查找 z-comments 内的内容
        comments = await page.query_selector_all('z-comments')
        print(f'z-comments 组件: {len(comments)} 个')
        
        if comments:
            html = await comments[0].inner_html()
            print(f'z-comments HTML: {html[:1000]}')
        
        # 2. 查找可能的评论项
        comment_items = await page.query_selector_all('.comment-item, .review-item, [class*="comment"]')
        print(f'\n评论项: {len(comment_items)} 个')
        
        for i, item in enumerate(comment_items[:5]):
            text = await item.inner_text()
            if text.strip():
                print(f'[{i}] {text[:200]}...')
        
        # 3. 查找包含用户名的元素
        print('\n查找用户名:')
        user_elems = await page.query_selector_all('.username, .user-name, [class*="user"]')
        for elem in user_elems[:5]:
            text = await elem.inner_text()
            print(f'User: {text[:50]}')
        
        # 4. 检查页面所有文本内容找评论
        print('\n查找可能的评论段落:')
        paragraphs = await page.query_selector_all('p, div')
        for p in paragraphs:
            text = await p.inner_text()
            if text and len(text) > 20 and len(text) < 500:
                # 可能是评论的内容
                if any(kw in text for kw in ['书', '好', '不错', '推荐', '作者', '内容', '读']):
                    print(f'可能评论: {text[:100]}...')
                    print('---')
        
        print('\n等待 5 秒...')
        await asyncio.sleep(5)
        await browser.close()

asyncio.run(fetch_reviews())
