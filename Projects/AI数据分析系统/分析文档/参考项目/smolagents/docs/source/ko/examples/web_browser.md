# 에이전트를 활용한 웹 브라우저 자동화 [[web-browser-automation-with-agents-]]

[[open-in-colab]]

이 노트북에서는 **에이전트 기반 웹 브라우저 자동화 시스템**을 구축해보겠습니다! 이 시스템은 웹사이트 탐색, 요소 상호작용, 정보 자동 추출이 가능합니다.

에이전트는 다음과 같은 기능을 수행할 수 있습니다.

- [x] 웹 페이지 탐색
- [x] 요소 클릭
- [x] 페이지 내 검색
- [x] 팝업 및 모달 처리
- [x] 정보 추출

단계별로 이 시스템을 구축해보겠습니다!

먼저 필요한 의존성을 설치하기 위해 다음을 실행하세요.

```bash
pip install smolagents selenium helium pillow -q
```

필요한 라이브러리를 가져오고 환경 변수를 설정해보겠습니다.

```python
from io import BytesIO
from time import sleep

import helium
from dotenv import load_dotenv
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from smolagents import CodeAgent, tool
from smolagents.agents import ActionStep

# 환경 변수를 불러옵니다.
load_dotenv()
```

이제 에이전트가 웹 페이지를 탐색하고 상호작용할 수 있도록 하는 핵심 브라우저 상호작용 도구들을 만들어보겠습니다.

```python
@tool
def search_item_ctrl_f(text: str, nth_result: int = 1) -> str:
    """
    현재 페이지에서 Ctrl + F를 사용해 지정된 텍스트를 검색하고, n번째로 등장하는 위치로 이동합니다.
    인자:
        text: 검색할 텍스트
        nth_result: 이동할 n번째 검색 결과 (기본값: 1)
    """
    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{text}')]")
    if nth_result > len(elements):
        raise Exception(f"Match n°{nth_result} not found (only {len(elements)} matches found)")
    result = f"Found {len(elements)} matches for '{text}'."
    elem = elements[nth_result - 1]
    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
    result += f"Focused on element {nth_result} of {len(elements)}"
    return result

@tool
def go_back() -> None:
    """이전 페이지로 돌아갑니다."""
    driver.back()

@tool
def close_popups() -> str:
    """
    Closes any visible modal or pop-up on the page. Use this to dismiss pop-up windows!
    This does not work on cookie consent banners.
    """
    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
```

Chrome으로 브라우저를 설정하고 스크린샷 기능을 구성해보겠습니다.

```python
# Configure Chrome options
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--force-device-scale-factor=1")
chrome_options.add_argument("--window-size=1000,1350")
chrome_options.add_argument("--disable-pdf-viewer")
chrome_options.add_argument("--window-position=0,0")

# Initialize the browser
driver = helium.start_chrome(headless=False, options=chrome_options)

# Set up screenshot callback
def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
    sleep(1.0)  # Let JavaScript animations happen before taking the screenshot
    driver = helium.get_driver()
    current_step = memory_step.step_number
    if driver is not None:
        for previous_memory_step in agent.memory.steps:  # Remove previous screenshots for lean processing
            if isinstance(previous_memory_step, ActionStep) and previous_memory_step.step_number <= current_step - 2:
                previous_memory_step.observations_images = None
        png_bytes = driver.get_screenshot_as_png()
        image = Image.open(BytesIO(png_bytes))
        print(f"Captured a browser screenshot: {image.size} pixels")
        memory_step.observations_images = [image.copy()]  # Create a copy to ensure it persists

    # Update observations with current URL
    url_info = f"Current url: {driver.current_url}"
    memory_step.observations = (
        url_info if memory_step.observations is None else memory_step.observations + "\n" + url_info
    )
```

이제 웹 자동화 에이전트를 만들어보겠습니다.

```python
from smolagents import InferenceClientModel

# Initialize the model
model_id = "Qwen/Qwen2-VL-72B-Instruct"  # You can change this to your preferred VLM model
model = InferenceClientModel(model_id=model_id)

# Create the agent
agent = CodeAgent(
    tools=[go_back, close_popups, search_item_ctrl_f],
    model=model,
    additional_authorized_imports=["helium"],
    step_callbacks=[save_screenshot],
    max_steps=20,
    verbosity_level=2,
)

# Import helium for the agent
agent.python_executor("from helium import *", agent.state)
```

에이전트가 웹 자동화를 위해 Helium을 사용하려면 지침이 필요합니다. 다음은 제공할 지침입니다.

```python
helium_instructions = """
You can use helium to access websites. Don't bother about the helium driver, it's already managed.
We've already ran "from helium import *"
Then you can go to pages!
Code:
```py
go_to('github.com/trending')
```<end_code>

You can directly click clickable elements by inputting the text that appears on them.
Code:
```py
click("Top products")
```<end_code>

If it's a link:
Code:
```py
click(Link("Top products"))
```<end_code>

If you try to interact with an element and it's not found, you'll get a LookupError.
In general stop your action after each button click to see what happens on your screenshot.
Never try to login in a page.

To scroll up or down, use scroll_down or scroll_up with as an argument the number of pixels to scroll from.
Code:
```py
scroll_down(num_pixels=1200) # This will scroll one viewport down
```<end_code>

When you have pop-ups with a cross icon to close, don't try to click the close icon by finding its element or targeting an 'X' element (this most often fails).
Just use your built-in tool `close_popups` to close them:
Code:
```py
close_popups()
```<end_code>

You can use .exists() to check for the existence of an element. For example:
Code:
```py
if Text('Accept cookies?').exists():
    click('I accept')
```<end_code>
"""
```

이제 작업과 함께 에이전트를 실행할 수 있습니다! Wikipedia에서 정보를 찾는 것을 시도해보겠습니다.

```python
search_request = """
Please navigate to https://en.wikipedia.org/wiki/Chicago and give me a sentence containing the word "1992" that mentions a construction accident.
"""

agent_output = agent.run(search_request + helium_instructions)
print("Final output:")
print(agent_output)
```

요청을 수정하여 다른 작업을 실행할 수 있습니다. 예를 들어, 제가 얼마나 열심히 일해야 하는지 알아보는 작업입니다.

```python
github_request = """
I'm trying to find how hard I have to work to get a repo in github.com/trending.
Can you navigate to the profile for the top author of the top trending repo, and give me their total number of commits over the last year?
"""

agent_output = agent.run(github_request + helium_instructions)
print("Final output:")
print(agent_output)
```

이 시스템은 특히 다음과 같은 작업에 효과적입니다.
- 웹사이트에서 데이터 추출
- 웹 리서치 자동화
- UI 테스트 및 검증
- 콘텐츠 모니터링
