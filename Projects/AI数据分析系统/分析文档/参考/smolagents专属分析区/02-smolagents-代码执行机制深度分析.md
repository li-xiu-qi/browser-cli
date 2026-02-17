# smolagents 代码执行机制深度分析

> **项目**: smolagents (Hugging Face)  
> **分析日期**: 2026-02-06  
> **源码位置**: `src/smolagents/local_python_executor.py`, `src/smolagents/remote_executors.py`  
> **分析范围**: Local / E2B / Docker / Modal / Wasm 执行器

---

## 一、执行器架构总览

### 1.1 执行器继承体系

```
PythonExecutor (ABC)
├── LocalPythonExecutor          # 本地执行（白名单机制）
└── RemotePythonExecutor (ABC)   # 远程执行基类
    ├── E2BExecutor              # E2B 云端沙箱
    ├── DockerExecutor           # Docker 容器
    ├── ModalExecutor            # Modal Serverless
    ├── BlaxelExecutor           # Blaxel 平台
    └── WasmExecutor             # WebAssembly
```

### 1.2 执行器对比

| 执行器 | 安全性 | 启动速度 | 适用场景 | 依赖 |
|--------|--------|----------|----------|------|
| **Local** | ⭐⭐ |  快 | 开发/测试 | 无 |
| **E2B** | ⭐⭐⭐⭐⭐ |  慢 | 生产环境 | e2b-sdk |
| **Docker** | ⭐⭐⭐⭐ |  慢 | 本地隔离 | docker |
| **Modal** | ⭐⭐⭐⭐⭐ |  慢 | 云端部署 | modal-sdk |
| **Wasm** | ⭐⭐⭐⭐ |  快 | 浏览器 | wasmtime |

---

## 二、LocalPythonExecutor - 本地执行

### 2.1 核心设计

**文件位置**: `local_python_executor.py`

**设计哲学**: 在本地 Python 环境中通过**白名单机制**实现安全隔离，而非真正的沙箱。

```python
class LocalPythonExecutor(PythonExecutor):
    """
    本地 Python 代码执行器
    - 通过 AST 解析检查代码安全性
    - 白名单控制可导入的模块
    - 限制危险函数和属性访问
    """
```

### 2.2 安全机制详解

#### 2.2.1 模块白名单

```python
# 默认允许的基础模块（安全）
BASE_BUILTIN_MODULES = [
    "math", "random", "datetime", "collections",
    "itertools", "json", "re", "statistics",
    "typing", "fractions", "decimal", "hashlib",
    # ... 等 30+ 个安全模块
]

# 危险模块（禁止导入）
DANGEROUS_MODULES = [
    "builtins",  # 防止访问底层 builtins
    "io",        # 防止文件读写
    "multiprocessing",  # 防止创建进程
    "os",        # 防止系统调用
    "pathlib",   # 防止文件系统访问
    "pty",       # 防止伪终端
    "shutil",    # 防止文件操作
    "socket",    # 防止网络访问
    "subprocess", # 防止执行命令
    "sys",       # 防止系统信息获取
]
```

**导入检查机制**:

```python
def check_import_authorized(import_to_check: str, authorized_imports: list[str]) -> bool:
    """
    检查导入是否被授权
    支持通配符 '*' 和子模块检查
    """
    current_node = build_import_tree(authorized_imports)
    for part in import_to_check.split("."):
        if "*" in current_node:  # 通配符允许所有
            return True
        if part not in current_node:
            return False
        current_node = current_node[part]
    return True
```

#### 2.2.2 危险函数拦截

```python
DANGEROUS_FUNCTIONS = [
    "builtins.compile",   # 防止编译代码
    "builtins.eval",      # 防止动态执行
    "builtins.exec",      # 防止执行代码
    "builtins.globals",   # 防止访问全局变量
    "builtins.locals",    # 防止访问局部变量
    "builtins.__import__", # 防止动态导入
    "os.popen",           # 防止命令执行
    "os.system",          # 防止系统命令
]
```

#### 2.2.3 AST 解析检查

**代码在编译前通过 AST 进行静态分析**:

```python
def evaluate_ast(
    expression: ast.AST,
    state: dict[str, Any],
    static_tools: dict[str, Callable],
    custom_tools: dict[str, Callable],
    authorized_imports: list[str],
) -> Any:
    """
    递归求值 AST 节点，同时进行安全检查
    """
    if isinstance(expression, ast.Import):
        # 检查导入是否被授权
        for alias in expression.names:
            if not check_import_authorized(alias.name, authorized_imports):
                raise InterpreterError(f"Import {alias.name} is not allowed")
    
    elif isinstance(expression, ast.Call):
        # 检查函数调用是否安全
        func = evaluate_ast(expression.func, state, ...)
        check_safer_result(func, static_tools, authorized_imports)
    
    elif isinstance(expression, ast.Attribute):
        # 禁止访问双下划线属性
        if expression.attr.startswith("__") and expression.attr.endswith("__"):
            raise InterpreterError(f"Forbidden access to dunder attribute: {expression.attr}")
```

### 2.3 执行限制

```python
# 执行限制常量
MAX_OPERATIONS = 10000000           # 最大操作数
MAX_WHILE_ITERATIONS = 1000000      # while 循环最大迭代
MAX_EXECUTION_TIME_SECONDS = 30     # 最大执行时间
DEFAULT_MAX_LEN_OUTPUT = 50000      # 输出长度限制
```

**超时机制** (跨平台实现):

```python
def timeout(timeout_seconds: int):
    """
    使用 ThreadPoolExecutor 实现超时控制
    兼容 Windows，线程安全
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    return future.result(timeout=timeout_seconds)
                except FuturesTimeoutError:
                    raise ExecutionTimeoutError(
                        f"Code execution exceeded {timeout_seconds} seconds"
                    )
        return wrapper
    return decorator
```

### 2.4 状态保持

```python
class LocalPythonExecutor:
    def __init__(self, additional_authorized_imports: list[str], ...):
        self.state: dict = {}  # 执行状态保持
        
    def __call__(self, code: str) -> CodeOutput:
        """执行代码并返回结果"""
        # 1. 解析 AST
        # 2. 安全检查
        # 3. 执行代码
        # 4. 返回结果
        
    def send_variables(self, variables: dict[str, Any]):
        """向执行环境发送变量"""
        self.state.update(variables)
```

---

## 三、E2BExecutor - 云端沙箱

### 3.1 E2B 简介

**E2B (Execution to Be)** 是一个云端代码执行平台，提供安全的沙箱环境。

```python
class E2BExecutor(RemotePythonExecutor):
    """
    使用 E2B 云端沙箱执行 Python 代码
    - 完全隔离的执行环境
    - 自动销毁，无状态保持
    - 支持文件系统操作
    """
```

### 3.2 执行流程

```python
def __init__(self, additional_imports: list[str], logger, **kwargs):
    from e2b_code_interpreter import Sandbox
    
    # 创建沙箱实例
    self.sandbox = Sandbox.create(**kwargs)
    
    # 安装依赖包
    self.installed_packages = self.install_packages(additional_imports)

def run_code_raise_errors(self, code: str) -> CodeOutput:
    """在 E2B 沙箱中执行代码"""
    execution = self.sandbox.run_code(code)
    
    # 收集输出
    execution_logs = "\n".join([str(log) for log in execution.logs.stdout])
    
    # 处理错误
    if execution.error:
        if execution.error.name == "FinalAnswerException":
            final_answer = pickle.loads(base64.b64decode(execution.error.value))
            return CodeOutput(output=final_answer, logs=execution_logs, is_final_answer=True)
        raise AgentError(f"Execution error: {execution.error}")
    
    # 处理结果（支持图片、HTML、JSON 等）
    for result in execution.results:
        if result.jpeg or result.png:
            return CodeOutput(output=PIL.Image.open(...), logs=execution_logs)
        elif result.json:
            return CodeOutput(output=result.json, logs=execution_logs)
        # ... 其他格式
```

### 3.3 特点

| 特性 | 说明 |
|------|------|
| **完全隔离** | 代码在云端沙箱执行，与本地完全隔离 |
| **自动销毁** | 执行完毕后沙箱自动销毁，无残留 |
| **多格式支持** | 支持图片(JPEG/PNG)、HTML、JSON、PDF、SVG 等 |
| **依赖管理** | 自动安装 pip 依赖 |

---

## 四、DockerExecutor - 容器隔离

### 4.1 架构设计

**使用 Jupyter Kernel Gateway 在 Docker 容器中执行代码**:

```
┌────────────────────────────────────────────────────────────────┐
│                     DockerExecutor 架构                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│   本地代码                                                      │
│      │                                                          │
│      ▼                                                          │
│   WebSocket 连接                                                │
│      │                                                          │
│      ▼                                                          │
│   ┌─────────────────────┐                                       │
│   │ Docker Container    │                                       │
│   │ ┌─────────────────┐ │                                       │
│   │ │ Jupyter Kernel  │ │                                       │
│   │ │ Gateway         │ │                                       │
│   │ │ (Port 8888)     │ │                                       │
│   │ └─────────────────┘ │                                       │
│   └─────────────────────┘                                       │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 核心实现

```python
class DockerExecutor(RemotePythonExecutor):
    def __init__(self, additional_imports, logger, 
                 host="127.0.0.1", port=8888,
                 image_name="jupyter-kernel", ...):
        
        # Dockerfile 定义
        self.dockerfile_content = """
        FROM python:3.12-bullseye
        RUN pip install jupyter_kernel_gateway jupyter_client ipykernel
        EXPOSE 8888
        CMD ["jupyter", "kernelgateway", 
             "--KernelGatewayApp.ip='0.0.0.0'",
             "--KernelGatewayApp.port=8888"]
        """
        
        # 构建镜像
        self.client.images.build(fileobj=dockerfile_obj, tag=image_name)
        
        # 启动容器
        self.container = self.client.containers.run(
            self.image_name,
            ports={'8888/tcp': (host, port)},
            detach=True
        )
        
        # 创建 Jupyter Kernel
        self.kernel_id = _create_kernel_http(f"{base_url}/api/kernels", logger)
        self.ws_url = f"ws://{host}:{port}/api/kernels/{self.kernel_id}/channels"
```

### 4.3 WebSocket 通信

```python
def _websocket_run_code_raise_errors(code: str, ws, logger) -> CodeOutput:
    """通过 WebSocket 与 Jupyter Kernel 通信"""
    
    # 1. 发送执行请求
    msg_id = str(uuid.uuid4())
    execute_request = {
        "header": {
            "msg_id": msg_id,
            "msg_type": "execute_request",
            "version": "5.0",
        },
        "content": {
            "code": code,
            "silent": False,
            "store_history": True,
        },
    }
    ws.send(json.dumps(execute_request))
    
    # 2. 接收执行结果
    while True:
        msg = json.loads(ws.recv())
        msg_type = msg.get("msg_type", "")
        
        if msg_type == "stream":
            outputs.append(msg_content["text"])
        elif msg_type == "execute_result":
            result = msg_content["data"].get("text/plain")
        elif msg_type == "error":
            raise AgentError(msg_content.get("traceback"))
        elif msg_type == "status" and msg_content["execution_state"] == "idle":
            break
```

### 4.4 清理机制

```python
def cleanup(self):
    """清理 Docker 容器"""
    if hasattr(self, "container"):
        self.container.stop()
        self.container.remove()
```

---

## 五、其他远程执行器

### 5.1 ModalExecutor

**Modal** 是一个 serverless 计算平台，提供弹性扩展的云端执行环境。

```python
class ModalExecutor(RemotePythonExecutor):
    def __init__(self, additional_imports, logger, app_name="smolagent-executor", ...):
        import modal
        
        # 创建沙箱
        self.sandbox = modal.Sandbox.create(
            image=modal.Image.debian_slim().uv_pip_install(
                "jupyter_kernel_gateway", "ipykernel"
            ),
            timeout=60 * 5,
            encrypted_ports=[port],
            secrets=[modal.Secret.from_dict({"KG_AUTH_TOKEN": token})],
        )
        
        # 获取隧道连接
        tunnel = self.sandbox.tunnels()[port]
        self.ws_url = f"wss://{tunnel.host}/api/kernels/{kernel_id}/channels?token={token}"
```

### 5.2 执行器对比总结

| 维度 | Local | E2B | Docker | Modal |
|------|-------|-----|--------|-------|
| **隔离级别** | 进程级 | 虚拟机级 | 容器级 | 虚拟机级 |
| **网络访问** |  受限 |  允许 |  允许 |  允许 |
| **文件系统** |  受限 |  独立 |  独立 |  独立 |
| **冷启动** | 无 | 2-5s | 5-10s | 3-8s |
| **成本** | 免费 | 按量计费 | 本地免费 | 按量计费 |
| **持久化** | state 保持 | 无 | 容器内 | 无 |

---

## 六、Final Answer 检测机制

### 6.1 问题背景

远程执行器无法像本地执行器那样直接访问 Python 对象，需要通过异常机制传递最终结果。

### 6.2 实现方案

```python
def _patch_final_answer_with_exception(self, final_answer_tool: FinalAnswerTool):
    """
    修改 FinalAnswerTool，使其抛出异常来传递最终结果
    """
    class _FinalAnswerTool(final_answer_tool.__class__):
        def forward(self, *args, **kwargs):
            import base64, pickle
            
            class FinalAnswerException(BaseException):
                def __init__(self, value):
                    self.value = value
            
            # 抛出异常，value 是 pickle + base64 编码的最终结果
            raise FinalAnswerException(
                base64.b64encode(pickle.dumps(self._forward(*args, **kwargs))).decode()
            )
    
    # 替换原始类
    final_answer_tool.__class__ = _FinalAnswerTool
```

### 6.3 异常捕获

```python
def run_code_raise_errors(self, code: str) -> CodeOutput:
    execution = self.sandbox.run_code(code)
    
    if execution.error:
        # 检查是否是 FinalAnswerException
        if execution.error.name == "FinalAnswerException":
            final_answer = pickle.loads(base64.b64decode(execution.error.value))
            return CodeOutput(
                output=final_answer,
                logs=execution_logs,
                is_final_answer=True  # 标记为最终答案
            )
```

---

## 七、安全建议与最佳实践

### 7.1 不同场景选择

| 场景 | 推荐执行器 | 理由 |
|------|-----------|------|
| 本地开发 | Local | 启动快，调试方便 |
| 数据处理 | E2B/Docker | 隔离性好，支持文件操作 |
| 生产部署 | E2B/Modal | 自动扩展，无服务器管理 |
| 网络访问 | E2B/Docker/Modal | 完全网络隔离环境 |
| 敏感数据 | E2B/Modal | 云端沙箱，无本地残留 |

### 7.2 Local 执行器加固

```python
# 严格的白名单配置
executor = LocalPythonExecutor(
    additional_authorized_imports=[
        "pandas", "numpy", "matplotlib"
    ],
    # 不要添加 "*" 通配符
)

# 设置超时时间
MAX_EXECUTION_TIME_SECONDS = 10  # 缩短执行时间
```

### 7.3 与 TaskWeaver 对比

| 特性 | smolagents | TaskWeaver |
|------|-----------|------------|
| **本地执行** | LocalPythonExecutor (白名单) | IPython Kernel (有状态) |
| **沙箱选项** | E2B, Docker, Modal, Wasm | 仅本地 |
| **安全检查** | AST 解析 + 白名单 | 依赖注入隔离 |
| **状态保持** | 简单的 state dict | IPython namespace |
| **多执行器** | 支持多种远程执行器 | 单一执行器 |

---

## 八、对我们项目的启示

### 8.1 推荐实现

```python
class CodeExecutor:
    """
    我们的代码执行器设计
    """
    def __init__(self, executor_type: str = "local", **kwargs):
        self.executor_type = executor_type
        self.executor = self._create_executor(**kwargs)
    
    def _create_executor(self, **kwargs):
        if self.executor_type == "local":
            return LocalExecutor(
                authorized_imports=kwargs.get("authorized_imports", []),
                timeout=kwargs.get("timeout", 30)
            )
        elif self.executor_type == "docker":
            return DockerExecutor(
                image=kwargs.get("image", "python:3.11-slim")
            )
        elif self.executor_type == "e2b":
            return E2BExecutor(api_key=kwargs["api_key"])
    
    def execute(self, code: str, variables: dict = None) -> ExecutionResult:
        """执行代码"""
        if variables:
            self.executor.send_variables(variables)
        
        result = self.executor.execute(code)
        
        return ExecutionResult(
            output=result.output,
            logs=result.logs,
            is_final_answer=result.is_final_answer,
            execution_time=result.execution_time
        )
```

### 8.2 关键借鉴点

1. **多种执行器**: 本地开发用 Local，生产用 E2B/Docker
2. **白名单机制**: Local 执行器严格控制导入
3. **超时控制**: ThreadPoolExecutor 实现跨平台超时
4. **状态传递**: pickle + base64 传递复杂对象
5. **结果检测**: 异常机制传递 Final Answer

### 8.3 安全 checklist

- [ ] 禁用危险模块 (os, sys, subprocess)
- [ ] 禁用危险函数 (eval, exec, compile)
- [ ] 设置执行超时
- [ ] 限制输出长度
- [ ] 生产环境使用沙箱执行器
