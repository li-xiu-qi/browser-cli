# smolagents GradioUI与可视化分析

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/gradio_ui.py

---

## 一、GradioUI类设计

### 1.1 类结构概览

GradioUI类是一个轻量级的Web界面包装器，核心职责是将MultiStepAgent的交互过程可视化。类的设计遵循单一职责原则，专注于界面渲染而不涉及Agent逻辑。

```python
class GradioUI:
    def __init__(self, agent: MultiStepAgent, file_upload_folder: str | None = None, reset_agent_memory: bool = False)
    def _save_uploaded_file(self, file_path: str) -> str
    def upload_file(self, file, file_uploads_log: list, allowed_file_types: list | None = None)
    def _process_message(self, message: str | dict) -> tuple[str, list[str] | None]
    def _stream_response(self, message: str | dict, history: list[dict]) -> Generator
    def launch(self, share: bool = True, **kwargs)
    def create_app(self)
```

### 1.2 初始化参数设计

| 参数 | 类型 | 默认值 | 用途 |
|------|------|--------|------|
| agent | MultiStepAgent | 必填 | 被包装的Agent实例 |
| file_upload_folder | str or None | None | 文件上传目录，为None时禁用文件上传 |
| reset_agent_memory | bool | False | 每次交互是否重置Agent记忆 |

**设计要点**：
- file_upload_folder参数控制多模态能力的开关
- 当提供上传目录时，代码自动创建目录结构
- reset_agent_memory用于控制会话连续性

### 1.3 文件上传支持

文件上传功能通过以下机制实现：

**路径处理**：
```python
self.file_upload_folder = Path(file_upload_folder) if file_upload_folder is not None else None
if self.file_upload_folder is not None:
    if not self.file_upload_folder.exists():
        self.file_upload_folder.mkdir(parents=True, exist_ok=True)
```

**文件名安全处理**：
```python
original_name = os.path.basename(file_path)
sanitized_name = re.sub(r"[^\w\-.]", "_", original_name)
dest_path = os.path.join(self.file_upload_folder, sanitized_name)
shutil.copy(file_path, dest_path)
```

**安全策略**：
- 使用正则表达式过滤危险字符
- 保留字母、数字、下划线、连字符和点号
- 通过复制而非移动确保原始文件安全

---

## 二、消息生成机制

### 2.1 核心调度函数 pull_messages_from_step

这是整个消息系统的入口，负责根据Step类型分发到对应处理器：

```python
def pull_messages_from_step(step_log: ActionStep | PlanningStep | FinalAnswerStep, skip_model_outputs: bool = False):
    if isinstance(step_log, ActionStep):
        yield from _process_action_step(step_log, skip_model_outputs)
    elif isinstance(step_log, PlanningStep):
        yield from _process_planning_step(step_log, skip_model_outputs)
    elif isinstance(step_log, FinalAnswerStep):
        yield from _process_final_answer_step(step_log)
```

**skip_model_outputs参数的作用**：
- 当Agent启用stream_outputs时，模型输出已通过流式方式实时展示
- 此时需要跳过ActionStep中的model_output字段，避免重复显示

### 2.2 ActionStep处理流程 _process_action_step

ActionStep的处理是最复杂的，包含7个输出阶段：

**阶段1：步骤编号标识**
```python
step_number = f"Step {step_log.step_number}"
if not skip_model_outputs:
    yield gr.ChatMessage(role=MessageRole.ASSISTANT, content=f"**{step_number}**", metadata={"status": "done"})
```

**阶段2：模型思考过程**
```python
if not skip_model_outputs and getattr(step_log, "model_output", ""):
    model_output = _clean_model_output(step_log.model_output)
    yield gr.ChatMessage(role=MessageRole.ASSISTANT, content=model_output, metadata={"status": "done"})
```

**阶段3：工具调用展示**
```python
if getattr(step_log, "tool_calls", []):
    first_tool_call = step_log.tool_calls[0]
    used_code = first_tool_call.name == "python_interpreter"
    
    # 参数提取
    args = first_tool_call.arguments
    if isinstance(args, dict):
        content = str(args.get("answer", str(args)))
    else:
        content = str(args).strip()
    
    # 代码格式化
    if used_code:
        content = _format_code_content(content)
    
    # 生成带metadata的消息
    parent_message_tool = gr.ChatMessage(
        role=MessageRole.ASSISTANT,
        content=content,
        metadata={
            "title": f"️ Used tool {first_tool_call.name}",
            "status": "done",
        },
    )
```

**metadata字段的作用**：
- title：控制Gradio Chatbot中折叠面板的标题
- status：控制消息状态标记

**阶段4：执行日志展示**
```python
if getattr(step_log, "observations", "") and step_log.observations.strip():
    log_content = step_log.observations.strip()
    log_content = re.sub(r"^Execution logs:\s*", "", log_content)
    yield gr.ChatMessage(
        role=MessageRole.ASSISTANT,
        content=f"```bash\n{log_content}\n",
        metadata={"title": " Execution Logs", "status": "done"},
    )
```

**阶段5：图片输出展示**
```python
if getattr(step_log, "observations_images", []):
    for image in step_log.observations_images:
        path_image = AgentImage(image).to_string()
        yield gr.ChatMessage(
            role=MessageRole.ASSISTANT,
            content={"path": path_image, "mime_type": f"image/{path_image.split('.')[-1]}"},
            metadata={"title": "️ Output Image", "status": "done"},
        )
```

**阶段6：错误信息展示**
```python
if getattr(step_log, "error", None):
    yield gr.ChatMessage(
        role=MessageRole.ASSISTANT, content=str(step_log.error), metadata={"title": " Error", "status": "done"}
    )
```

**阶段7：步骤脚注与分隔线**
```python
yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content=get_step_footnote_content(step_log, step_number),
    metadata={"status": "done"},
)
yield gr.ChatMessage(role=MessageRole.ASSISTANT, content="-----", metadata={"status": "done"})
```

### 2.3 脚注信息生成 get_step_footnote_content

脚注包含三类信息：
- Token使用量：input_tokens和output_tokens
- 执行时长：duration字段，保留2位小数
- 步骤名称：Step N或Planning step

```python
def get_step_footnote_content(step_log: ActionStep | PlanningStep, step_name: str) -> str:
    step_footnote = f"**{step_name}**"
    if step_log.token_usage is not None:
        step_footnote += f" | Input tokens: {step_log.token_usage.input_tokens:,} | Output tokens: {step_log.token_usage.output_tokens:,}"
    step_footnote += f" | Duration: {round(float(step_log.timing.duration), 2)}s" if step_log.timing.duration else ""
    return f"""<span style="color: #bbbbc2; font-size: 12px;">{step_footnote}</span> """
```

### 2.4 PlanningStep处理 _process_planning_step

规划步骤的输出相对简单：

```python
def _process_planning_step(step_log: PlanningStep, skip_model_outputs: bool = False):
    if not skip_model_outputs:
        yield gr.ChatMessage(role=MessageRole.ASSISTANT, content="**Planning step**", metadata={"status": "done"})
        yield gr.ChatMessage(role=MessageRole.ASSISTANT, content=step_log.plan, metadata={"status": "done"})
    yield gr.ChatMessage(
        role=MessageRole.ASSISTANT,
        content=get_step_footnote_content(step_log, "Planning step"),
        metadata={"status": "done"},
    )
    yield gr.ChatMessage(role=MessageRole.ASSISTANT, content="-----", metadata={"status": "done"})
```

### 2.5 FinalAnswerStep处理 _process_final_answer_step

最终答案支持四种类型：

| 类型 | 处理方式 | 输出格式 |
|------|----------|----------|
| AgentText | 提取字符串 | Markdown文本 |
| AgentImage | 获取路径 | image/png |
| AgentAudio | 获取路径 | audio/wav |
| 其他 | 强制转字符串 | 纯文本 |

```python
def _process_final_answer_step(step_log: FinalAnswerStep):
    final_answer = step_log.output
    if isinstance(final_answer, AgentText):
        yield gr.ChatMessage(role=MessageRole.ASSISTANT, content=f"**Final answer:**\n{final_answer.to_string()}\n", metadata={"status": "done"})
    elif isinstance(final_answer, AgentImage):
        yield gr.ChatMessage(role=MessageRole.ASSISTANT, content={"path": final_answer.to_string(), "mime_type": "image/png"}, metadata={"status": "done"})
    elif isinstance(final_answer, AgentAudio):
        yield gr.ChatMessage(role=MessageRole.ASSISTANT, content={"path": final_answer.to_string(), "mime_type": "audio/wav"}, metadata={"status": "done"})
    else:
        yield gr.ChatMessage(role=MessageRole.ASSISTANT, content=f"**Final answer:** {str(final_answer)}", metadata={"status": "done"})
```

### 2.6 输出清理函数

**_clean_model_output**：处理模型输出的格式问题

```python
def _clean_model_output(model_output: str) -> str:
    if not model_output:
        return ""
    model_output = model_output.strip()
    # 处理 <end_code> 标签与代码块的各种组合
    model_output = re.sub(r"```\s*<end_code>", "```", model_output)
    model_output = re.sub(r"<end_code>\s*```", "```", model_output)
    model_output = re.sub(r"```\s*\n\s*<end_code>", "```", model_output)
    return model_output.strip()
```

**_format_code_content**：确保代码块格式正确

```python
def _format_code_content(content: str) -> str:
    content = content.strip()
    # 移除已存在的代码块标记
    content = re.sub(r"```.*?\n", "", content)
    content = re.sub(r"\s*<end_code>\s*", "", content)
    content = content.strip()
    # 添加Python代码块标记
    if not content.startswith("```python"):
        content = f"```python\n{content}\n```"
    return content
```

---

## 三、流式响应实现

### 3.1 两种流式处理模式

smolagents提供两种流式处理入口：

| 函数 | 使用场景 | 返回值 |
|------|----------|--------|
| stream_to_gradio | 独立使用Agent时 | Generator |
| GradioUI._stream_response | GradioUI内部使用 | Generator |

### 3.2 stream_to_gradio函数

这是Agent的通用流式包装器：

```python
def stream_to_gradio(
    agent,
    task: str,
    task_images: list | None = None,
    reset_agent_memory: bool = False,
    additional_args: dict | None = None,
) -> Generator:
    accumulated_events: list[ChatMessageStreamDelta] = []
    for event in agent.run(task, images=task_images, stream=True, reset=reset_agent_memory, additional_args=additional_args):
        if isinstance(event, ActionStep | PlanningStep | FinalAnswerStep):
            # 输出完整的Step消息
            for message in pull_messages_from_step(event, skip_model_outputs=getattr(agent, "stream_outputs", False)):
                yield message
            accumulated_events = []
        elif isinstance(event, ChatMessageStreamDelta):
            # 累积流式片段并输出
            accumulated_events.append(event)
            text = agglomerate_stream_deltas(accumulated_events).render_as_markdown()
            yield text
```

**核心逻辑**：
- 使用accumulated_events列表累积流式片段
- 通过agglomerate_stream_deltas合并片段
- 遇到完整Step时清空累积列表

### 3.3 GradioUI._stream_response方法

这是GradioUI内部的流式处理实现，与stream_to_gradio的主要区别是需要维护消息历史：

```python
def _stream_response(self, message: str | dict, history: list[dict]) -> Generator:
    import gradio as gr
    
    task, task_files = self._process_message(message)
    
    all_messages: list[gr.ChatMessage] = []
    accumulated_events: list[ChatMessageStreamDelta] = []
    streaming_msg_idx: int | None = None
    
    for event in self.agent.run(task, images=task_files, stream=True, reset=self.reset_agent_memory, additional_args=None):
        if isinstance(event, ActionStep | PlanningStep | FinalAnswerStep):
            # 移除临时的流式消息
            if streaming_msg_idx is not None:
                all_messages.pop(streaming_msg_idx)
                streaming_msg_idx = None
            
            # 添加完整的Step消息
            for msg in pull_messages_from_step(event, skip_model_outputs=getattr(self.agent, "stream_outputs", False)):
                all_messages.append(gr.ChatMessage(role=msg.role, content=msg.content, metadata=msg.metadata))
                yield all_messages
            accumulated_events = []
            
        elif isinstance(event, ChatMessageStreamDelta):
            accumulated_events.append(event)
            text = agglomerate_stream_deltas(accumulated_events).render_as_markdown()
            text = text.replace("<", r"\<").replace(">", r"\>")
            msg = gr.ChatMessage(role="assistant", content=text)
            
            if streaming_msg_idx is None:
                streaming_msg_idx = len(all_messages)
                all_messages.append(msg)
            else:
                all_messages[streaming_msg_idx] = msg
            yield all_messages
```

**关键设计**：
- all_messages列表维护完整的对话历史
- streaming_msg_idx跟踪当前流式消息的位置
- 遇到完整Step时移除临时流式消息，避免重复
- HTML转义处理防止Gradio解析标签

### 3.4 ChatMessageStreamDelta处理

ChatMessageStreamDelta是模型流式输出的基本单元：

```python
elif isinstance(event, ChatMessageStreamDelta):
    accumulated_events.append(event)
    text = agglomerate_stream_deltas(accumulated_events).render_as_markdown()
```

**agglomerate_stream_deltas的作用**：
- 将多个StreamDelta片段合并为完整的ChatMessage
- 处理增量文本的拼接
- 提供render_as_markdown方法输出格式化文本

---

## 四、多模态展示

### 4.1 文本消息展示

文本消息使用gr.ChatMessage的content字段直接传递字符串：

```python
yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content="**Step 1**",
    metadata={"status": "done"}
)
```

Gradio 5.x与6.x的兼容处理：
```python
type_messages_kwarg = {"type": "messages"} if gr.__version__.startswith("5") else {}
```

### 4.2 图片展示 AgentImage

图片输出通过content字典指定路径和MIME类型：

```python
yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content={
        "path": path_image,
        "mime_type": f"image/{path_image.split('.')[-1]}"
    },
    metadata={"title": "️ Output Image", "status": "done"},
)
```

**处理流程**：
1. 从step_log.observations_images获取原始图片数据
2. 使用AgentImage包装并转换为路径字符串
3. 提取文件扩展名作为MIME类型后缀

### 4.3 音频展示 AgentAudio

音频输出与图片类似：

```python
elif isinstance(final_answer, AgentAudio):
    yield gr.ChatMessage(
        role=MessageRole.ASSISTANT,
        content={"path": final_answer.to_string(), "mime_type": "audio/wav"},
        metadata={"status": "done"},
    )
```

### 4.4 文件上传处理

文件上传通过_process_message方法处理：

```python
def _process_message(self, message: str | dict) -> tuple[str, list[str] | None]:
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

**消息格式转换**：
- Gradio ChatInterface的多模态输入是dict格式，包含text和files字段
- 将文件路径列表追加到文本末尾，作为Agent的输入
- 返回处理后的文本和文件列表

---

## 五、交互设计

### 5.1 聊天界面布局

GradioUI使用gr.ChatInterface构建界面：

```python
def create_app(self):
    import gradio as gr
    
    type_messages_kwarg = {"type": "messages"} if gr.__version__.startswith("5") else {}
    
    chatbot = gr.Chatbot(
        label="Agent",
        avatar_images=(
            None,
            "https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/smolagents/mascot_smol.png",
        ),
        latex_delimiters=[
            {"left": r"$$", "right": r"$$", "display": True},
            {"left": r"$", "right": r"$", "display": False},
            {"left": r"\[", "right": r"\]", "display": True},
            {"left": r"\(", "right": r"\)", "display": False},
        ],
        **type_messages_kwarg,
    )
    
    demo = gr.ChatInterface(
        fn=self._stream_response,
        chatbot=chatbot,
        title=self.name.replace("_", " ").capitalize(),
        multimodal=self.file_upload_folder is not None,
        save_history=True,
        **type_messages_kwarg,
    )
    return demo
```

**界面配置要素**：
- avatar_images：设置Agent头像，用户头像为None使用默认
- latex_delimiters：配置LaTeX数学公式解析规则
- multimodal：根据file_upload_folder是否配置启用文件上传
- save_history：启用对话历史保存

### 5.2 思考过程折叠展开

思考过程通过metadata的title字段实现折叠面板：

```python
yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content=model_output,
    metadata={"status": "done"}  # 无title，直接展示
)

yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content=content,
    metadata={
        "title": f"️ Used tool {first_tool_call.name}",  # 有title，可折叠
        "status": "done",
    },
)
```

**折叠规则**：
- 带title的消息显示为可折叠面板
- 无title的消息直接展开显示
- 模型输出和思考过程通常直接展示
- 工具调用和执行日志通常折叠展示

### 5.3 代码块展示

代码通过markdown代码块格式展示：

**Python代码**：
```python
content = f"```python\n{content}\n```"
```

**Bash执行日志**：
```python
yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content=f"```bash\n{log_content}\n",
    metadata={"title": " Execution Logs", "status": "done"},
)
```

**代码格式化逻辑**：
- _format_code_content函数确保代码块格式统一
- 自动添加python标记
- 清理残留的<end_code>标签

### 5.4 工具调用展示

工具调用信息分层次展示：

1. **工具名称**：作为折叠面板标题
2. **调用参数**：代码块形式展示
3. **执行结果**：独立的折叠面板
4. **错误信息**：特殊标记的折叠面板

```python
# 工具调用
yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content=content,  # 格式化的代码
    metadata={"title": f"️ Used tool {first_tool_call.name}", "status": "done"},
)

# 执行日志
yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content=f"```bash\n{log_content}\n",
    metadata={"title": " Execution Logs", "status": "done"},
)

# 错误信息
yield gr.ChatMessage(
    role=MessageRole.ASSISTANT,
    content=str(step_log.error),
    metadata={"title": " Error", "status": "done"}
)
```

---

## 六、启动与集成

### 6.1 launch方法

launch方法是对Gradio launch的薄封装：

```python
def launch(self, share: bool = True, **kwargs):
    self.create_app().launch(debug=True, share=share, **kwargs)
```

**默认配置**：
- debug=True：启用调试模式
- share=True：默认创建公开分享链接
- **kwargs：透传其他Gradio参数

### 6.2 内联展示与独立服务器

Gradio应用支持多种启动模式：

**Jupyter Notebook内联展示**：
```python
# 在Notebook单元格中
gradio_ui.launch(share=False, inline=True)
```

**独立服务器**：
```python
# 作为独立Web服务
gradio_ui.launch(server_name="0.0.0.0", server_port=7860)
```

**公共分享**：
```python
# 生成gradio.live分享链接
gradio_ui.launch(share=True)
```

### 6.3 与Agent的集成方式

GradioUI与Agent的集成是引用关系而非继承：

```python
class GradioUI:
    def __init__(self, agent: MultiStepAgent, ...):
        self.agent = agent  # 保存Agent引用
```

**调用链**：
1. 用户输入 -> GradioUI._stream_response
2. _stream_response -> agent.run(stream=True)
3. agent.run -> 产生Step事件和Delta事件
4. GradioUI处理事件 -> 生成gr.ChatMessage
5. Gradio渲染消息 -> 展示给用户

### 6.4 状态管理策略

GradioUI本身不维护复杂的内部状态：

- Agent记忆由Agent自身维护
- 对话历史由Gradio ChatInterface组件维护
- 文件上传记录通过Gradio的状态管理机制传递
- 流式过程中的临时状态使用streaming_msg_idx跟踪

---

## 七、对我们项目的启示

### 7.1 可借鉴的设计模式

**分离式架构**：
smolagents将Agent核心与UI完全分离，通过事件机制通信。这种设计使Agent可独立测试和复用，UI层可自由替换。我们的项目可以采用类似的Core+Adapter模式。

**渐进式展示**：
通过Generator和yield实现渐进式输出，用户无需等待完整响应。这比一次性返回全部结果的体验更好。我们实现Streamlit或Web界面时应采用类似模式。

**metadata驱动的UI控制**：
Gradio通过ChatMessage的metadata控制展示行为，如折叠、状态标记等。这种声明式方法比手动操作DOM更简洁。我们可以设计类似的属性系统。

### 7.2 可复用的代码片段

**文件上传安全处理**：
```python
sanitized_name = re.sub(r"[^\w\-.]", "_", original_name)
```
这段代码可有效防止路径遍历攻击，直接复用。

**流式消息去重逻辑**：
```python
if streaming_msg_idx is not None:
    all_messages.pop(streaming_msg_idx)
    streaming_msg_idx = None
```
这种先插入临时消息、再替换为完整消息的模式值得参考。

**HTML转义处理**：
```python
text = text.replace("<", r"\<").replace(">", r"\>")
```
在展示用户生成内容时，这种基础转义可防止XSS攻击。

### 7.3 需要规避的设计

**重度依赖Gradio特性**：
smolagents的UI实现深度绑定Gradio，如metadata折叠面板、ChatInterface组件等。这种深度绑定使迁移成本较高。我们的项目如果需要支持多种前端，应设计更抽象的UI接口。

**版本兼容处理**：
代码中需要检测Gradio版本以处理不同API：
```python
type_messages_kwarg = {"type": "messages"} if gr.__version__.startswith("5") else {}
```
这种硬编码版本判断不够健壮，建议使用特性检测替代版本检测。

**Token使用量展示限制**：
脚注只展示当前步骤的Token使用量，缺乏全局统计。如果Agent执行多步，用户难以获知总消耗。我们的项目应提供完整的资源使用报告。

### 7.4 对我们Web界面设计的建议

**侧边栏时间线设计**：
参考smolagents的步骤编号和脚注，我们的Web界面可在侧边栏展示执行时间线，包含每个步骤的耗时和Token消耗。

**思考过程可视化**：
模型输出和工具调用的分层展示模式值得参考。我们可以设计更丰富的交互，如点击展开代码执行过程、悬停查看参数详情等。

**多模态输出支持**：
smolagents支持文本、图片、音频三种输出格式。我们的数据分析Agent应重点支持图片展示，如数据可视化结果、图表输出等。

**错误处理展示**：
错误信息作为独立消息类型展示，并支持折叠。我们可以增加错误分类，如代码错误、网络错误、模型错误等，用不同颜色区分。

### 7.5 技术选型建议

| 场景 | 推荐方案 | 理由 |
|------|----------|------|
| 快速原型验证 | Gradio | smolagents已验证，生态成熟 |
| 生产环境Web应用 | FastAPI + React | 更灵活的UI控制，更好的性能 |
| Notebook环境 | ipywidgets | 与Jupyter生态深度集成 |
| 独立桌面应用 | PyQt/PySide | 无需浏览器，本地体验更好 |

---

## 附录：类图与流程图

### GradioUI类结构

```
GradioUI
├── agent: MultiStepAgent
├── file_upload_folder: Path or None
├── reset_agent_memory: bool
├── name: str
├── description: str or None
├── __init__(agent, file_upload_folder, reset_agent_memory)
├── _save_uploaded_file(file_path) -> str
├── upload_file(file, file_uploads_log, allowed_file_types) -> tuple
├── _process_message(message) -> tuple[str, list or None]
├── _stream_response(message, history) -> Generator
├── launch(share, **kwargs)
└── create_app() -> gr.ChatInterface
```

### 消息处理流程

```
agent.run(stream=True)
    │
    ├─> ChatMessageStreamDelta ──> 累积 ──> agglomerate_stream_deltas ──> 流式输出
    │
    └─> ActionStep or PlanningStep or FinalAnswerStep
            │
            └─> pull_messages_from_step
                    │
                    ├─> _process_action_step ──> gr.ChatMessage列表
                    ├─> _process_planning_step ──> gr.ChatMessage列表
                    └─> _process_final_answer_step ──> gr.ChatMessage列表
```

---

*文档结束*
