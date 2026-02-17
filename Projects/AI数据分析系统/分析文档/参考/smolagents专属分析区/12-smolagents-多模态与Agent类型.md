# smolagents 多模态与Agent类型深度分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/agent_types.py, vision_web_browser.py, gradio_ui.py, memory.py, models.py

---

## 一、Agent类型体系

smolagents 定义了一套完整的Agent输出类型系统，核心设计目标是让Agent返回的对象能够同时满足三种需求：行为上像原始类型、可以被字符串化、在Jupyter环境中正确展示。

### 1.1 类型继承结构

```
AgentType (抽象基类)
    ├── AgentText (继承 str)
    ├── AgentImage (继承 PIL.Image.Image)
    └── AgentAudio (继承 str)
```

### 1.2 AgentType 基类

```python
class AgentType:
    """
    抽象类，定义Agent可以返回的类型
    
    这些对象有三个用途：
    - 行为上像它们代表的类型，例如AgentText像字符串，AgentImage像PIL图片
    - 可以被字符串化: str(object) 返回描述对象的字符串
    - 在ipython notebooks/colab/jupyter中正确显示
    """
    def __init__(self, value):
        self._value = value

    def __str__(self):
        return self.to_string()

    def to_raw(self):
        # 子类必须实现，返回原始数据
        pass

    def to_string(self) -> str:
        # 子类必须实现，返回字符串表示
        pass
```

### 1.3 _AGENT_TYPE_MAPPING 映射表

```python
_AGENT_TYPE_MAPPING = {
    "string": AgentText, 
    "image": AgentImage, 
    "audio": AgentAudio
}
```

这个映射表用于根据字符串类型名快速获取对应的Agent类型类，在工具输出类型转换和输出处理中发挥作用。

### 1.4 输入输出类型处理函数

```python
def handle_agent_input_types(*args, **kwargs):
    """将AgentType转换为原始类型，供工具使用"""
    args = [(arg.to_raw() if isinstance(arg, AgentType) else arg) for arg in args]
    kwargs = {k: (v.to_raw() if isinstance(v, AgentType) else v) for k, v in kwargs.items()}
    return args, kwargs

def handle_agent_output_types(output: Any, output_type: str | None = None) -> Any:
    """将原始输出转换为AgentType"""
    if output_type in _AGENT_TYPE_MAPPING:
        decoded_outputs = _AGENT_TYPE_MAPPING[output_type](output)
        return decoded_outputs
    
    # 自动类型推断
    if isinstance(output, str):
        return AgentText(output)
    if isinstance(output, PIL.Image.Image):
        return AgentImage(output)
    # ... 其他类型处理
    return output
```

---

## 二、AgentImage详解

AgentImage 是 smolagents 多模态能力的核心组件，支持多种图像数据源的无缝转换和展示。

### 2.1 支持的数据源类型

| 输入类型 | 处理方式 |
|---------|---------|
| AgentImage | 直接复制内部状态 |
| PIL.Image.Image | 存储到 _raw |
| bytes | 通过 BytesIO 转换为 PIL Image |
| str / pathlib.Path | 存储为文件路径 _path |
| torch.Tensor | 存储为张量 _tensor |
| numpy.ndarray | 转换为 torch.Tensor 存储 |

### 2.2 初始化逻辑

```python
class AgentImage(AgentType, PIL.Image.Image):
    def __init__(self, value):
        AgentType.__init__(self, value)
        PIL.Image.Image.__init__(self)
        
        self._path = None      # 文件路径
        self._raw = None       # PIL Image 对象
        self._tensor = None    # PyTorch 张量
        
        # 根据输入类型进行分发处理
        if isinstance(value, AgentImage):
            self._raw, self._path, self._tensor = value._raw, value._path, value._tensor
        elif isinstance(value, PIL.Image.Image):
            self._raw = value
        elif isinstance(value, bytes):
            self._raw = PIL.Image.open(BytesIO(value))
        elif isinstance(value, (str, pathlib.Path)):
            self._path = value
        elif isinstance(value, torch.Tensor):
            self._tensor = value
        elif isinstance(value, np.ndarray):
            self._tensor = torch.from_numpy(value)
```

### 2.3 to_raw 方法

将各种内部存储形式统一转换为 PIL.Image.Image：

```python
def to_raw(self):
    """返回PIL.Image.Image对象"""
    if self._raw is not None:
        return self._raw
    
    if self._path is not None:
        self._raw = PIL.Image.open(self._path)
        return self._raw
    
    if self._tensor is not None:
        array = self._tensor.cpu().detach().numpy()
        return PIL.Image.fromarray((255 - array * 255).astype(np.uint8))
```

### 2.4 to_string 方法

返回文件路径，必要时自动创建临时文件：

```python
def to_string(self):
    """返回图片的文件路径"""
    if self._path is not None:
        return self._path
    
    if self._raw is not None:
        directory = tempfile.mkdtemp()
        self._path = os.path.join(directory, str(uuid.uuid4()) + ".png")
        self._raw.save(self._path, format="png")
        return self._path
    
    if self._tensor is not None:
        # 张量转图片，保存到临时文件
        directory = tempfile.mkdtemp()
        self._path = os.path.join(directory, str(uuid.uuid4()) + ".png")
        img = self.to_raw()  # 先转换为PIL Image
        img.save(self._path, format="png")
        return self._path
```

### 2.5 save 方法

```python
def save(self, output_bytes, format: str = None, **params):
    """保存图片到文件"""
    img = self.to_raw()
    img.save(output_bytes, format=format, **params)
```

### 2.6 IPython 展示支持

```python
def _ipython_display_(self, include=None, exclude=None):
    """在Jupyter notebook中正确显示图片"""
    from IPython.display import Image, display
    display(Image(self.to_string()))
```

---

## 三、AgentAudio详解

AgentAudio 处理音频数据，需要安装额外的音频依赖。

### 3.1 依赖要求

```python
def __init__(self, value, samplerate=16_000):
    if not _is_package_available("soundfile") or not _is_package_available("torch"):
        raise ModuleNotFoundError(
            "请安装 audio 额外依赖以使用 AgentAudio: `pip install 'smolagents[audio]'`"
        )
```

### 3.2 支持的数据源

| 输入类型 | 处理方式 |
|---------|---------|
| str / pathlib.Path | 存储为文件路径 _path，支持HTTP URL |
| torch.Tensor | 存储为 _tensor |
| tuple (samplerate, array) | 分离采样率和音频数据 |

### 3.3 初始化逻辑

```python
def __init__(self, value, samplerate=16_000):
    super().__init__(value)
    self._path = None
    self._tensor = None
    self.samplerate = samplerate
    
    if isinstance(value, (str, pathlib.Path)):
        self._path = value
    elif isinstance(value, torch.Tensor):
        self._tensor = value
    elif isinstance(value, tuple):
        self.samplerate = value[0]
        if isinstance(value[1], np.ndarray):
            self._tensor = torch.from_numpy(value[1])
        else:
            self._tensor = torch.tensor(value[1])
```

### 3.4 to_raw 方法

```python
def to_raw(self):
    """返回torch.Tensor对象"""
    import soundfile as sf
    
    if self._tensor is not None:
        return self._tensor
    
    if self._path is not None:
        if "://" in str(self._path):  # HTTP URL
            response = requests.get(self._path)
            response.raise_for_status()
            tensor, self.samplerate = sf.read(BytesIO(response.content))
        else:  # 本地文件
            tensor, self.samplerate = sf.read(self._path)
        self._tensor = torch.tensor(tensor)
        return self._tensor
```

### 3.5 to_string 方法

```python
def to_string(self):
    """返回音频文件路径，WAV格式"""
    import soundfile as sf
    
    if self._path is not None:
        return self._path
    
    if self._tensor is not None:
        directory = tempfile.mkdtemp()
        self._path = os.path.join(directory, str(uuid.uuid4()) + ".wav")
        sf.write(self._path, self._tensor, samplerate=self.samplerate)
        return self._path
```

### 3.6 IPython 展示支持

```python
def _ipython_display_(self, include=None, exclude=None):
    """在Jupyter中播放音频"""
    from IPython.display import Audio, display
    display(Audio(self.to_string(), rate=self.samplerate))
```

---

## 四、视觉输入支持

smolagents 的视觉输入支持贯穿整个Agent执行流程，从任务输入到步骤观察都能携带图像信息。

### 4.1 MultiStepAgent.run 的 images 参数

```python
def run(
    self,
    task: str,
    images: list["PIL.Image.Image"] | None = None,  # 视觉输入
    additional_args: dict | None = None,
    max_steps: int | None = None,
    return_full_result: bool | None = None,
    # ...
):
    # 存储到TaskStep
    self.memory.steps.append(TaskStep(task=self.task, task_images=images))
```

### 4.2 TaskStep 任务步骤

```python
@dataclass
class TaskStep(MemoryStep):
    task: str
    task_images: list["PIL.Image.Image"] | None = None
    
    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        content = [{"type": "text", "text": f"New task:\n{self.task}"}]
        if self.task_images:
            # 将图片添加到消息内容
            content.extend([{"type": "image", "image": image} for image in self.task_images])
        
        return [ChatMessage(role=MessageRole.USER, content=content)]
```

### 4.3 ActionStep 观察图像

```python
@dataclass
class ActionStep(MemoryStep):
    step_number: int
    observations: str | None = None
    observations_images: list["PIL.Image.Image"] | None = None  # 观察到的图像
    # ...
    
    def to_messages(self, summary_mode: bool = False) -> list[ChatMessage]:
        messages = []
        # ...
        if self.observations_images:
            messages.append(
                ChatMessage(
                    role=MessageRole.USER,
                    content=[
                        {"type": "image", "image": image}
                        for image in self.observations_images
                    ],
                )
            )
        # ...
        return messages
```

### 4.4 执行流程中的图像传递

```python
def _run_stream(
    self, task: str, max_steps: int, images: list["PIL.Image.Image"] | None = None
):
    # 第一步使用传入的图片作为观察图像
    action_step = ActionStep(
        step_number=self.step_number,
        observations_images=images,  # 图片传递给观察
    )
```

### 4.5 内存管理优化

在 vision_web_browser.py 中可以看到，为了避免内存过度占用，系统会清理旧截图：

```python
def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
    # 清理两步之前的旧截图，减少内存占用
    for previous_memory_step in agent.memory.steps:
        if isinstance(previous_memory_step, ActionStep) and \
           previous_memory_step.step_number <= current_step - 2:
            previous_memory_step.observations_images = None
```

---

## 五、Vision Web浏览器

vision_web_browser.py 展示了 smolagents 如何将视觉能力与浏览器自动化结合，实现视觉驱动的Web操作。

### 5.1 技术栈

- **Helium**: 高级的Selenium封装，提供更简洁的浏览器操作API
- **Selenium WebDriver**: 底层的浏览器控制
- **Chrome**: 浏览器引擎

### 5.2 截图捕获流程

```python
def save_screenshot(memory_step: ActionStep, agent: CodeAgent) -> None:
    sleep(1.0)  # 等待JavaScript动画完成
    driver = helium.get_driver()
    current_step = memory_step.step_number
    
    if driver is not None:
        # 内存优化：清理旧截图
        for previous_memory_step in agent.memory.steps:
            if isinstance(previous_memory_step, ActionStep) and \
               previous_memory_step.step_number <= current_step - 2:
                previous_memory_step.observations_images = None
        
        # 捕获截图
        png_bytes = driver.get_screenshot_as_png()
        image = PIL.Image.open(BytesIO(png_bytes))
        print(f"Captured a browser screenshot: {image.size} pixels")
        
        # 存储到当前步骤，必须使用copy确保持久化
        memory_step.observations_images = [image.copy()]
    
    # 更新观察信息，附加当前URL
    url_info = f"Current url: {driver.current_url}"
    memory_step.observations = url_info if memory_step.observations is None \
        else memory_step.observations + "\n" + url_info
```

### 5.3 浏览器工具集

```python
@tool
def search_item_ctrl_f(text: str, nth_result: int = 1) -> str:
    """使用Ctrl+F搜索页面内容并跳转到指定匹配项"""
    escaped_text = _escape_xpath_string(text)
    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), {escaped_text})]")
    if nth_result > len(elements):
        raise Exception(f"Match n°{nth_result} not found")
    elem = elements[nth_result - 1]
    driver.execute_script("arguments[0].scrollIntoView(true);", elem)
    return f"Focused on element {nth_result} of {len(elements)}"

@tool
def go_back() -> None:
    """返回上一页"""
    driver.back()

@tool  
def close_popups() -> str:
    """关闭弹窗，发送ESC键"""
    webdriver.ActionChains(driver).send_keys(Keys.ESCAPE).perform()
```

### 5.4 浏览器初始化配置

```python
def initialize_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--force-device-scale-factor=1")
    chrome_options.add_argument("--window-size=1000,1350")
    chrome_options.add_argument("--disable-pdf-viewer")
    chrome_options.add_argument("--window-position=0,0")
    return helium.start_chrome(headless=False, options=chrome_options)
```

### 5.5 Agent配置

```python
def initialize_agent(model):
    return CodeAgent(
        tools=[WebSearchTool(), go_back, close_popups, search_item_ctrl_f],
        model=model,
        additional_authorized_imports=["helium"],
        step_callbacks=[save_screenshot],  # 每步后自动截图
        max_steps=20,
        verbosity_level=2,
    )
```

### 5.6 给Agent的浏览器操作指令

```python
helium_instructions = """
使用 web_search 工具获取Google搜索结果。
使用 helium 访问网站，不要用于Google搜索。
Helium驱动已预先管理，已执行 "from helium import *"

访问页面：
<code>
go_to('github.com/trending')
</code>

点击元素：
<code>
click("Top products")
click(Link("Top products"))  # 如果是链接
</code>

滚动页面：
<code>
scroll_down(num_pixels=1200)
</code>

关闭弹窗：
<code>
close_popups()
</code>

每步代码执行后，会自动提供更新的浏览器截图和当前URL。
"""
```

---

## 六、Gradio多模态展示

gradio_ui.py 实现了完整的Gradio界面，支持文本、图片、音频的多模态展示。

### 6.1 处理ActionStep中的图像

```python
def _process_action_step(step_log: ActionStep, skip_model_outputs: bool = False):
    # ... 其他处理
    
    # 展示观察中的图片
    if getattr(step_log, "observations_images", []):
        for image in step_log.observations_images:
            path_image = AgentImage(image).to_string()  # 转换为文件路径
            yield gr.ChatMessage(
                role=MessageRole.ASSISTANT,
                content={
                    "path": path_image, 
                    "mime_type": f"image/{path_image.split('.')[-1]}"
                },
                metadata={"title": "️ Output Image", "status": "done"},
            )
```

### 6.2 处理最终答案中的多模态内容

```python
def _process_final_answer_step(step_log: FinalAnswerStep):
    final_answer = step_log.output
    
    if isinstance(final_answer, AgentText):
        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT,
            content=f"**Final answer:**\n{final_answer.to_string()}\n",
            metadata={"status": "done"},
        )
    elif isinstance(final_answer, AgentImage):
        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT,
            content={"path": final_answer.to_string(), "mime_type": "image/png"},
            metadata={"status": "done"},
        )
    elif isinstance(final_answer, AgentAudio):
        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT,
            content={"path": final_answer.to_string(), "mime_type": "audio/wav"},
            metadata={"status": "done"},
        )
```

### 6.3 GradioUI 类

```python
class GradioUI:
    """
    Gradio界面用于与MultiStepAgent交互
    
    特性：
    - 支持文件上传
    - 多模态消息渲染
    - 可重置Agent记忆
    """
    def __init__(self, agent: MultiStepAgent, 
                 file_upload_folder: str | None = None, 
                 reset_agent_memory: bool = False):
        self.agent = agent
        self.file_upload_folder = Path(file_upload_folder) if file_upload_folder else None
        self.reset_agent_memory = reset_agent_memory
        
    def _process_message(self, message: str | dict) -> tuple[str, list[str] | None]:
        """处理传入消息，提取文本和文件"""
        if isinstance(message, str):
            return message, None
        
        text = message.get("text", "")
        files = message.get("files", [])
        
        if files and self.file_upload_folder:
            saved_files = [self._save_uploaded_file(f) for f in files]
            if saved_files:
                text += f"\nYou have been provided with these files: {saved_files}"
            return text, saved_files
        
        return text, files if files else None
```

### 6.4 流式响应处理

```python
def _stream_response(self, message: str | dict, history: list[dict]):
    """流式输出Agent响应"""
    task, task_files = self._process_message(message)
    
    for event in self.agent.run(
        task, 
        images=task_files,  # 传递图片文件
        stream=True, 
        reset=self.reset_agent_memory
    ):
        if isinstance(event, ActionStep | PlanningStep | FinalAnswerStep):
            for msg in pull_messages_from_step(event):
                all_messages.append(msg)
                yield all_messages
```

### 6.5 创建Gradio应用

```python
def create_app(self):
    import gradio as gr
    
    chatbot = gr.Chatbot(
        label="Agent",
        avatar_images=(None, "...mascot_smol.png"),
        latex_delimiters=[...],  # 支持LaTeX公式
    )
    
    demo = gr.ChatInterface(
        fn=self._stream_response,
        chatbot=chatbot,
        title=self.name.replace("_", " ").capitalize(),
        multimodal=self.file_upload_folder is not None,  # 启用多模态
        save_history=True,
    )
    return demo
```

---

## 七、多模态Prompt处理

### 7.1 图像Base64编码

utils.py 中的核心函数：

```python
def encode_image_base64(image):
    """将PIL Image编码为base64字符串"""
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def make_image_url(base64_image):
    """创建data URL格式的图片链接"""
    return f"data:image/png;base64,{base64_image}"
```

### 7.2 消息格式转换

models.py 中的 get_clean_message_list 函数处理多模态消息：

```python
def get_clean_message_list(
    message_list: list[ChatMessage | dict],
    convert_images_to_image_urls: bool = False,  # 是否转为image_url格式
    flatten_messages_as_text: bool = False,
) -> list[dict[str, Any]]:
    
    for message in message_list:
        # 编码图片
        if isinstance(message.content, list):
            for element in message.content:
                if element["type"] == "image":
                    if convert_images_to_image_urls:
                        # 转为OpenAI格式的image_url
                        element.update({
                            "type": "image_url",
                            "image_url": {
                                "url": make_image_url(encode_image_base64(element.pop("image")))
                            },
                        })
                    else:
                        # 直接嵌入base64
                        element["image"] = encode_image_base64(element["image"])
```

### 7.3 消息内容格式

内存中的消息使用统一格式：

```python
# 文本内容
{"type": "text", "text": "..."}

# 图片内容（内部格式）
{"type": "image", "image": PIL.Image.Image}

# 图片内容（API格式）
{"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
```

### 7.4 不同模型的图像格式适配

不同模型类通过 convert_images_to_image_urls 参数控制图像格式：

```python
# OpenAI格式模型：使用image_url
class OpenAIServerModel:
    def __call__(self, ...):
        messages = get_clean_message_list(
            messages,
            convert_images_to_image_urls=True,  # OpenAI需要这种格式
        )

# 本地Transformers模型：使用base64
class TransformersModel:
    def __call__(self, ...):
        messages = get_clean_message_list(
            messages,
            convert_images_to_image_urls=False,  # 本地模型通常直接支持
        )
```

---

## 八、对我们项目的启示

### 8.1 类型系统设计

smolagents 的 AgentType 设计提供了很好的参考：

1. **多态封装**: 通过继承原始类型 + 混入AgentType，实现行为与元数据的统一
2. **延迟加载**: AgentImage 的三种存储形式实现按需转换，避免不必要的IO
3. **自动序列化**: to_string 方法统一处理持久化，调用者无需关心底层细节

可借鉴点：
- 在我们的AI数据分析系统中，可以设计类似的 DataType 类，封装 DataFrame、Chart、Table 等输出类型
- 实现统一的 to_raw / to_string / to_display 接口，便于前后端交互

### 8.2 多模态输入设计

smolagents 的视觉输入设计思路：

1. **统一入口**: MultiStepAgent.run 接受 images 参数，作为初始观察
2. **步骤级图像**: ActionStep.observations_images 支持每步附加图像
3. **内存管理**: 主动清理旧截图避免OOM

可借鉴点：
- 数据分析任务可能涉及多图表输入，可以参考这种分步骤携带图像的设计
- 对于长会话，需要实现类似的图像内存清理机制

### 8.3 图像编码策略

smolagents 的处理流程：

```
PIL Image -> encode_image_base64 -> data:image/png;base64,... -> LLM API
```

可借鉴点：
- PNG格式保证无损，适合数据可视化场景
- base64编码虽然增加体积，但简化了API传输
- 对于大量图像，考虑实现URL引用或对象存储方案

### 8.4 UI多模态展示

GradioUI 的实现提供了完整的参考：

1. **统一消息流**: 所有内容都转为 ChatMessage，包含 role / content / metadata
2. **类型分发**: _process_final_answer_step 根据输出类型选择展示方式
3. **文件管理**: 自动处理上传文件，保存到指定目录

可借鉴点：
- 设计统一的消息协议，支持文本、图片、表格、图表的混合展示
- 实现流式输出，提升用户体验

### 8.5 视觉浏览器模式

vision_web_browser.py 展示了视觉Agent的经典模式：

```
观察：截图 -> 推理：LLM分析 -> 行动：执行工具 -> 循环
```

可借鉴点：
- 对于数据探索场景，可以实现类似的数据可视化迭代模式
- 截图回调机制可以替换为图表生成回调，实现"可视化驱动分析"

---

## 参考链接

- [[AI数据分析系统/参考项目/smolagents/src/smolagents/agent_types.py|agent_types.py 源码]]
- [[AI数据分析系统/参考项目/smolagents/src/smolagents/vision_web_browser.py|vision_web_browser.py 源码]]
- [[AI数据分析系统/参考项目/smolagents/src/smolagents/gradio_ui.py|gradio_ui.py 源码]]
- [[AI数据分析系统/参考项目/smolagents/src/smolagents/memory.py|memory.py 源码]]
- [[AI数据分析系统/参考项目/smolagents/src/smolagents/models.py|models.py 源码]]
