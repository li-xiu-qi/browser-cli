# smolagents Vision Web浏览器深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/vision_web_browser.py

---

## 一、技术栈介绍

Vision Web浏览器基于以下技术栈构建：

| 技术 | 用途 | 特点 |
|------|------|------|
| Helium | 浏览器自动化 | Selenium的高级封装，API更简洁 |
| Selenium | 底层浏览器控制 | WebDriver标准实现，支持Chrome |
| PIL/Pillow | 图像处理 | 截图保存与格式转换 |
| gradio | UI展示 | 可选，用于交互式界面 |

### Helium 与 Selenium 的关系

代码中通过 `helium.start_chrome` 启动浏览器，但实际元素查找仍使用 Selenium 的 API：

```python
# 初始化使用 Helium
from helium import *
go_to('github.com/trending')
click("Top products")

# 底层仍可用 Selenium 的 find_elements
elements = driver.find_elements(By.XPATH, f"//*[contains(text(), {escaped_text})]")
```

Helium 简化了常见的浏览器操作，如点击、填写表单等，无需直接操作 WebDriver。

---

## 二、核心工具函数

Vision Web浏览器提供4个核心工具供Agent调用：

### 1. search_item_ctrl_f - 页面搜索

```python
@tool
def search_item_ctrl_f(text: str, nth_result: int = 1) -> str:
    """
    Searches for text on the current page via Ctrl + F and jumps to the nth occurrence.
    """
    escaped_text = _escape_xpath_string(text)
    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), {escaped_text})]")
    elem = elements[nth_result - 1]
    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
```

**功能**：在页面中搜索指定文本，并滚动到第n个匹配项的位置。用于快速定位页面上的关键信息。

### 2. go_back - 返回上一页

```python
@tool
def go_back() -> None:
    """Goes back to previous page."""
    driver.back()
```

**功能**：浏览器后退操作，Agent 误操作或需要回溯时使用。

### 3. close_popups - 关闭弹窗

```python
@tool
def close_popups() -> str:
    """
    Closes any visible modal or pop-up on the page.
    This does not work on cookie consent banners.
    """
    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
```

**功能**：发送 ESC 键关闭模态框和弹窗。明确说明对 Cookie 同意横幅无效。

### 4. WebSearchTool - 网络搜索

通过 `WebSearchTool()` 集成，Agent 可以先搜索获取目标网址，再用 Helium 访问。

> 设计原则：搜索用 WebSearchTool，网页浏览用 Helium，职责分离清晰。

---

## 三、截图机制详解

截图机制是 Vision Web 浏览器的核心，让 Agent 能够"看到"页面内容。

### save_screenshot 回调函数

```python
def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
    sleep(1.0)  # 等待 JavaScript 动画完成
    driver = helium.get_driver()
    current_step = memory_step.step_number
    
    if driver is not None:
        # 清理历史截图，只保留最近2步
        for previous_memory_step in agent.memory.steps:
            if isinstance(previous_memory_step, ActionStep) and \
               previous_memory_step.step_number <= current_step - 2:
                previous_memory_step.observations_images = None
        
        # 获取并保存截图
        png_bytes = driver.get_screenshot_as_png()
        image = PIL.Image.open(BytesIO(png_bytes))
        memory_step.observations_images = [image.copy()]
    
    # 同时记录当前 URL
    url_info = f"Current url: {driver.current_url}"
    memory_step.observations = url_info
```

### 关键设计点

| 设计点 | 实现方式 | 目的 |
|--------|----------|------|
| 延迟1秒 | `sleep(1.0)` | 等待页面动画和加载完成 |
| 历史清理 | 删除 step-2 之前的截图 | **节省 Token**，防止上下文溢出 |
| 图像复制 | `image.copy()` | 确保图像对象持久化，避免被GC回收 |
| URL记录 | 写入 observations | Agent 知道当前所在页面 |

### 何时触发截图

截图作为 `step_callbacks` 注册到 CodeAgent：

```python
agent = CodeAgent(
    tools=[...],
    model=model,
    step_callbacks=[save_screenshot],  # 每步结束后自动调用
    max_steps=20,
)
```

每个 ActionStep 执行完成后，自动触发截图，Agent 在下一次决策时能看到最新页面状态。

---

## 四、浏览器Agent设计

### 为什么使用 CodeAgent 而非 ToolCallingAgent

代码明确选择了 `CodeAgent`：

```python
agent = CodeAgent(
    tools=[WebSearchTool(), go_back, close_popups, search_item_ctrl_f],
    model=model,
    additional_authorized_imports=["helium"],  # 允许导入 Helium
    step_callbacks=[save_screenshot],
    max_steps=20,
    verbosity_level=2,
)
```

**原因分析**：

| 维度 | CodeAgent | ToolCallingAgent |
|------|-----------|------------------|
| 推理能力 | **更高**，可写完整代码逻辑 | 较低，单次工具调用 |
| 灵活性 | **可循环、条件判断** | 线性执行 |
| 复杂度 | 适合多步骤、条件分支任务 | 适合简单任务 |
| 浏览器场景 | 需要循环点击、判断元素存在 | 不适合 |

浏览器操作需要复杂的决策流程：判断元素是否存在、循环查找、条件点击等，CodeAgent 的代码生成能力更匹配。

### max_steps 设置

代码设置 `max_steps=20`，远高于默认值。原因：

- 网页浏览任务通常需要多步操作
- 搜索→点击→滚动→再点击→提取信息
- 复杂任务如"找到GitHub趋势榜第一作者的年度提交数"可能需要 10+ 步

### 预设指令 helium_instructions

系统提示中注入详细的 Helium 使用指南：

```
Use your web_search tool when you want to get Google search results.
Then you can use helium to access websites.
...
```

包含以下关键约束：

- **禁止用 Helium 做 Google 搜索**，用专门的 WebSearchTool
- **每次点击后暂停**，等待截图更新
- **禁止尝试登录**
- **优先用 close_popups 关闭弹窗**，而非查找 X 按钮
- **用 exists() 检查元素存在性**，避免 LookupError

---

## 五、多模态处理

### 截图如何传递给模型

1. **截图保存到 ActionStep**：
   ```python
   memory_step.observations_images = [image.copy()]
   ```

2. **Agent 下次决策时读取**：
   CodeAgent 会将 `observations_images` 中的图像转换为模型可理解的格式

3. **base64 编码**：
   内部实现中，图像会被编码为 base64，作为多模态消息的一部分发送给模型

### 模型如何处理图像输入

支持视觉的模型如 GPT-4o、Claude-3.5-sonnet：

- 接收 base64 编码的图像
- 理解页面布局、元素位置、文字内容
- 决定下一步操作，如点击哪个按钮、滚动多少像素

### 截图尺寸控制

```python
chrome_options.add_argument("--window-size=1000,1350")
```

固定窗口大小确保截图一致性，便于模型理解页面比例。

---

## 六、使用场景

Vision Web浏览器适用于以下场景：

### 1. 网页信息收集

示例请求：
```
Navigate to https://en.wikipedia.org/wiki/Chicago 
and give me a sentence containing the word "1992" 
that mentions a construction accident.
```

Agent 行为：
- 使用 WebSearchTool 或直接 go_to
- 用 search_item_ctrl_f 查找 "1992"
- 滚动到目标位置，阅读上下文
- 提取满足条件的句子

### 2. 复杂网页导航

示例请求：
```
Find how hard I have to work to get a repo in github.com/trending.
Navigate to the profile for the top author of the top trending repo,
and give me their total number of commits over the last year.
```

Agent 行为：
- 访问 GitHub Trending
- 识别排名第一的仓库
- 点击作者头像进入个人主页
- 查找贡献统计信息

> 代码注释明确说明：此任务只有 GPT-4o 或 Claude-3.5-sonnet 能够完成

### 3. 可视化测试

可用于自动化网页功能验证，通过视觉反馈判断页面状态是否正确。

---

## 七、与其他方案对比

### 与 OpenAI GPT-4V 函数调用的差异

| 维度 | smolagents Vision Web | GPT-4V + Function Calling |
|------|----------------------|---------------------------|
| 架构 | CodeAgent 生成 Python 代码控制浏览器 | 模型直接输出工具调用 |
| 截图频率 | **每步自动截图**，Agent 持续"看到"页面 | 需手动设计截图时机 |
| 历史管理 | **自动清理旧截图**，控制 Token 消耗 | 需自行实现 |
| 灵活性 | **可写任意代码逻辑**，循环、条件判断 | 单次函数调用 |
| 工具扩展 | 容易添加自定义工具 | 需定义 Schema |
| 模型依赖 | 支持多模型，通过 LiteLLM 统一调用 | 仅 OpenAI |
| 实现复杂度 | 需部署 Selenium/Helium 环境 | 仅需 API 调用 |

### 成本对比

| 方案 | 成本因素 |
|------|----------|
| smolagents | 需维护浏览器实例，截图占用 Token，但支持 cheaper 模型 |
| GPT-4V API | 图像输入按像素收费，高频截图成本高 |

### 灵活性对比

smolagents 方案更灵活：

- 可替换底层模型，从 GPT-4o 切换到 Claude 或本地模型
- 可扩展自定义工具，如保存页面内容到数据库
- 可修改截图策略，如只在关键步骤截图

---

## 八、对我们项目的启示

### 可借鉴的设计

| 设计点 | 应用建议 |
|--------|----------|
| 截图历史清理 | 控制多模态 Token 消耗的关键策略，**必须实现** |
| CodeAgent + 视觉 | 复杂任务优先用 CodeAgent，ToolCallingAgent 适合简单任务 |
| 延迟截图 | 等待动画完成，避免截图到中间状态 |
| 工具分离 | 搜索和浏览分离，职责清晰 |
| 详细系统提示 | 预设指令减少模型犯错概率 |

### 潜在改进方向

1. **异步截图**：当前使用 `sleep(1.0)`，可改为等待特定元素出现
2. **截图压缩**：大图可压缩后再传给模型，进一步节省 Token
3. **智能清理**：根据任务类型动态决定保留几步历史截图
4. **错误重试**：截图失败时可自动重试或回退

### 技术债务注意点

```python
# 代码中使用全局变量存储 driver
global driver
driver = initialize_driver()
```

全局变量在多线程/多用户场景下会有问题，生产环境需改为依赖注入或上下文管理。

---

## 参考链接

- 源码文件: `src/smolagents/vision_web_browser.py`
- Helium 文档: https://github.com/mherrmann/selenium-python-helium
- smolagents 文档: https://github.com/huggingface/smolagents

---

## 标签

项目: [[Projects/AI数据分析系统/_INDEX-AI数据分析系统|AI数据分析系统]]
类型: 源码分析
关联: smolagents, 多模态Agent, 浏览器自动化
