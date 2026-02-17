from bs4 import BeautifulSoup

# 读取HTML
with open('.agents/skills/zlibrary-to-notebooklm/temp/review_page.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# 查找包含评论时间标识的元素
time_patterns = ['years ago', 'months ago', 'days ago']
comments = []

# 查找所有文本节点
for elem in soup.find_all(text=True):
    text = elem.strip()
    if any(pattern in text for pattern in time_patterns):
        # 找到时间元素，向上查找父元素获取完整评论
        parent = elem.parent
        if parent:
            # 获取包含时间的容器
            container = parent
            for _ in range(3):  # 向上查找最多3层
                if container:
                    container_text = container.get_text(strip=True)
                    if len(container_text) > 50:  # 可能是包含完整评论的容器
                        comments.append({
                            'time': text,
                            'container': container_text[:300]
                        })
                        break
                    container = container.parent

print(f'找到 {len(comments)} 条评论:\n')
for i, c in enumerate(comments[:5]):
    print(f'[{i}] 时间: {c["time"]}')
    print(f'    内容: {c["container"]}...')
    print()
