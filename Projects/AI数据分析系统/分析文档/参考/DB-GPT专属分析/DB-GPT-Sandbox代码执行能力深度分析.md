# DB-GPT Sandbox 代码执行能力深度分析

> 深入分析 DB-GPT 的代码执行沙箱架构设计，包括四层架构、多运行时支持、有状态会话和安全机制。

---

## 一、概述

### 1.1 设计目标

DB-GPT Sandbox 是一个**可扩展的多容器/本地沙箱执行框架**，旨在解决 AI Agent 在真实环境中的任务隔离性和安全性问题。

**核心特性**：
-  **多运行时支持**：Docker、Podman、Nerdctl、本地进程
-  **多语言支持**：Python、Shell、Node.js、Java、C++、Go、Rust
-  **有状态执行**：同一会话内多次执行共享环境
-  **插件化设计**：统一的沙箱接口，易于扩展
-  **自动选择**：根据环境自动选择最佳运行时

### 1.2 架构全景

```
┌─────────────────────────────────────────────────────────────────┐
│                        DB-GPT Sandbox 架构                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    用户层 (User Layer)                    │  │
│  │  • FastAPI 服务接口                                       │  │
│  │  • 请求验证和转换                                          │  │
│  │  • 会话管理                                               │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │                   控制层 (Control Layer)                  │  │
│  │  • 任务生命周期管理                                        │  │
│  │  • 任务调度和分发                                          │  │
│  │  • 依赖安装管理                                            │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │                  执行层 (Execution Layer)                 │  │
│  │  • Docker / Podman / Nerdctl / Local 运行时               │  │
│  │  • 统一的 SandboxRuntime 抽象                             │  │
│  │  • 自动运行时选择 (RuntimeFactory)                         │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                        │
│  ┌──────────────────────▼───────────────────────────────────┐  │
│  │                  显示层 (Display Layer)                   │  │
│  │  • 执行结果封装                                            │  │
│  │  • GUI/VNC 支持                                           │  │
│  │  • 文件传输                                               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、四层架构详解

### 2.1 用户层 (User Layer)

**位置**：`sandbox/user_layer/`

**职责**：对外提供统一的 API 接口，处理用户请求和会话管理

**核心组件**：
- `service.py`：FastAPI 路由和服务实现
- `schemas.py`：请求/响应数据模型

**任务类型定义**：
```python
TASK_TYPES = [
    "connect",      # 创建新的沙箱会话
    "configure",    # 配置环境，安装依赖
    "execute",      # 执行代码
    "manual",       # 进入手动操作模式（VNC）
    "disconnect",   # 销毁会话
    "status",       # 获取会话状态
    "list",         # 列出所有会话
    "get_file",     # 获取执行产生的文件
]
```

**TaskObject 封装**：
```python
class TaskObject:
    """封装用户任务信息"""
    def __init__(
        self,
        task_type: str,        # 任务类型（必须在TASK_TYPES中）
        user_id: str,          # 用户ID
        task_id: str,          # 任务ID
        session_id: str,       # 会话ID
        language: str,         # 编程语言
        code_content: str,     # 代码内容
        config: dict,          # 配置参数
        file_name: str,        # 文件名（用于get_file）
    )
```

---

### 2.2 控制层 (Control Layer)

**位置**：`sandbox/control_layer/control_layer.py`

**职责**：管理任务生命周期，支持多种任务类型的调度和执行

**核心设计**：

#### 2.2.1 任务锁机制（并发控制）
```python
class ControlLayer:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_locks: Dict[str, asyncio.Lock] = {}  # 每个task_id一个锁

    async def handle_task(self, task: TaskObject) -> ExecutionResult:
        handler = handler_map[task.task_type]
        
        # 为每个task_id创建独立的锁，保证同一任务的串行执行
        lock = self.task_locks.setdefault(task.task_id, asyncio.Lock())
        async with lock:
            return await handler(task)
```

**关键点**：
- 每个 `task_id` 有独立的 `asyncio.Lock`
- 同一任务的多个操作（如连续执行代码）会串行执行
- 不同任务之间可以并发执行

#### 2.2.2 任务处理器映射
```python
handler_map = {
    "connect": self._handle_connect,       # 创建会话
    "configure": self._handle_configure,   # 安装依赖
    "execute": self._handle_execute,       # 执行代码
    "manual": self._handle_manual,         # VNC手动模式
    "disconnect": self._handle_disconnect, # 销毁会话
    "status": self._handle_status,         # 获取状态
    "list": self._handle_list,             # 列会话
    "get_file": self._handle_get_file,     # 获取文件
}
```

#### 2.2.3 会话配置参数
```python
config = SessionConfig(
    language=task.language,
    working_dir=WORKING_DIR,              # /tmp/sandbox
    max_memory=512 * 1024 * 1024,         # 512MB 内存限制
    max_cpus=task.config.get("max_cpus", 1),  # CPU限制
    environment_vars=task.config.get("env", {}),
    network_disabled=task.config.get("network_disabled", False),
)
```

---

### 2.3 执行层 (Execution Layer)

**位置**：`sandbox/execution_layer/`

#### 2.3.1 基础抽象

**文件**：`base.py`

```python
class SandboxSession(ABC):
    """沙箱会话抽象类 - 代表一个独立的执行环境"""
    
    def __init__(self, session_id: str, config: SessionConfig):
        self.session_id = session_id
        self.config = config
        self.created_at = time.time()
        self.last_accessed = self.created_at
        self._is_active = False
    
    @abstractmethod
    async def start(self) -> bool:
        """启动会话（启动容器/进程）"""
        pass
    
    @abstractmethod
    async def execute(self, code: str) -> ExecutionResult:
        """执行代码"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """停止会话（销毁容器/进程）"""
        pass
    
    async def install_dependencies(self, dependencies: List[str]) -> ExecutionResult:
        """安装依赖（可选）"""
        pass

class SandboxRuntime(ABC):
    """沙箱运行时抽象类 - 管理多个会话"""
    
    def __init__(self, runtime_id: str):
        self.runtime_id = runtime_id
        self.sessions: Dict[str, SandboxSession] = {}
    
    @abstractmethod
    async def create_session(self, session_id: str, config: SessionConfig) -> SandboxSession:
        """创建新会话"""
        pass
    
    async def cleanup_expired_sessions(self, max_idle_time: int = 3600) -> int:
        """清理过期会话（默认1小时）"""
        pass
```

#### 2.3.2 运行时自动选择（RuntimeFactory）

**文件**：`runtime_factory.py`

```python
class RuntimeFactory:
    """自动选择最佳沙箱运行时"""

    @staticmethod
    def create(runtime_preference: str = None):
        # 1. 检查环境变量 SANDBOX_RUNTIME
        env_choice = os.environ.get("SANDBOX_RUNTIME")
        if env_choice:
            runtime_preference = env_choice.lower()

        # 2. 如果指定了运行时，尝试创建
        if runtime_preference:
            if runtime_preference == "docker" and EnvironmentDetector.is_docker_sdk_available():
                return DockerRuntime()
            if runtime_preference == "podman" and EnvironmentDetector.is_podman_available():
                return PodmanRuntime()
            if runtime_preference == "nerdctl" and EnvironmentDetector.is_nerdctl_available():
                return NerdctlRuntime()
            if runtime_preference == "local":
                return LocalRuntime()
            raise RuntimeError(f"指定的运行时不可用: {runtime_preference}")

        # 3. 自动检测（按优先级）
        # 优先级: Docker -> Podman -> Nerdctl -> Local
        if EnvironmentDetector.is_docker_sdk_available():
            try:
                client = docker.from_env()
                client.info()  # 实际连接测试
                return DockerRuntime()
            except Exception:
                pass
        
        if EnvironmentDetector.is_podman_available():
            return PodmanRuntime()
        
        if EnvironmentDetector.is_nerdctl_available():
            return NerdctlRuntime()
        
        # 4. 最终回退到本地执行
        return LocalRuntime()
```

**环境检测工具** (`utils.py`)：
```python
class EnvironmentDetector:
    @staticmethod
    def is_docker_available() -> bool:
        return shutil.which("docker") is not None

    @staticmethod
    def is_docker_sdk_available() -> bool:
        try:
            import docker
            return True
        except ImportError:
            return False

    @staticmethod
    def is_podman_available() -> bool:
        return shutil.which("podman") is not None

    @staticmethod
    def is_nerdctl_available() -> bool:
        return shutil.which("nerdctl") is not None
```

#### 2.3.3 Docker 运行时详解

**文件**：`docker_runtime.py`

**容器配置细节**：
```python
container_config = {
    "image": self.image_name,           # python:3.11-slim 等
    "command": "tail -f /dev/null",     # 保持容器运行
    "detach": True,
    "mem_limit": self.config.max_memory,    # 内存限制
    "cpuset_cpus": str(self.config.max_cpus),  # CPU限制
    "working_dir": self.config.working_dir,
    "environment": self.config.environment_vars,
    "network_disabled": self.config.network_disabled,  # 可禁用网络
    "volumes": {tempfile.gettempdir(): {"bind": "/tmp", "mode": "rw"}},
    "name": f"sandbox_{self.session_id}",
}

# VNC/GUI 模式特殊配置
if self.config.language.endswith("-vnc"):
    container_config["ports"] = {"5900/tcp": None, "6080/tcp": None}
    container_config["command"] = "/startup.sh"
```

**支持的语言镜像**：
```python
LANGUAGE_IMAGES = {
    "python": "python:3.11-slim",
    "python-vnc": "vnc-gui-browser:latest",  # 带VNC的Python
    "javascript": "node:18-slim",
    "java": "openjdk:11-jre-slim",
    "cpp": "gcc:latest",
    "go": "golang:1.21-alpine",
    "rust": "rust:1.75-slim",
}
```

**代码执行流程**：
```python
async def execute(self, code: str, shell=False) -> DisplayResult:
    if shell:
        # 直接执行shell命令
        result = self.container.exec_run(
            code, workdir=self.config.working_dir, demux=True
        )
    else:
        # 1. 创建临时代码文件
        code_file = self._create_code_file(code)
        
        # 2. 打包为tar（Docker文件传输需要）
        tar_data = self._create_tar_from_file(code_file)
        
        # 3. 传输到容器内
        self.container.put_archive(self.config.working_dir, tar_data)
        
        # 4. 执行代码
        exec_command = self._get_exec_command(os.path.basename(code_file))
        result = self.container.exec_run(
            exec_command, workdir=self.config.working_dir, demux=True
        )
```

**依赖安装实现**：
```python
async def install_dependencies(self, dependencies: List[str]) -> ExecutionResult:
    if self.config.language.startswith("python"):
        # Python: 使用清华镜像加速
        for dep in dependencies:
            res = await asyncio.to_thread(
                self.container.exec_run,
                f"pip install --no-input --disable-pip-version-check {dep}",
            )
            
    elif self.config.language.startswith("javascript"):
        # JavaScript: npm安装
        await asyncio.to_thread(
            self.container.exec_run, "npm init -y", 
            workdir=self.config.working_dir
        )
        dep_str = " ".join(dependencies)
        res = await asyncio.to_thread(
            self.container.exec_run,
            f"npm install {dep_str}",
            workdir=self.config.working_dir,
        )
```

**文件获取机制**：
```python
async def get_file_content(self, filename: str) -> DisplayResult:
    # 1. 从容器获取文件（返回tar流）
    bits, stat = self.container.get_archive(file_path)
    
    # 2. 写入内存
    file_data = io.BytesIO()
    for chunk in bits:
        file_data.write(chunk)
    file_data.seek(0)
    
    # 3. 解压tar
    with tarfile.open(fileobj=file_data) as tar:
        member = tar.getmember(filename)
        extracted = tar.extractfile(member)
        content_bytes = extracted.read()
        
    # 4. Base64编码返回（支持二进制文件）
    file_content = base64.b64encode(content_bytes).decode("utf-8")
```

**会话健康检查与清理**：
```python
async def cleanup_expired_sessions(self, max_idle_time: int = 3600) -> int:
    """清理过期会话（默认1小时）"""
    current_time = time.time()
    expired_sessions = [
        sid for sid, sess in self.sessions.items()
        if current_time - sess.last_accessed > max_idle_time
    ]
    
    cleanup_count = 0
    for sid in expired_sessions:
        if await self.destroy_session(sid):
            cleanup_count += 1
    return cleanup_count

async def health_check(self) -> Dict[str, Any]:
    return {
        "status": "healthy",
        "docker_version": info.get("ServerVersion", "unknown"),
        "containers_running": info.get("ContainersRunning", 0),
        "active_sessions": len(self.sessions),
        "supported_languages": self.supported_languages,
    }
```

#### 2.3.4 多语言支持实现机制

DB-GPT Sandbox 支持 **7 种编程语言**的代码执行，通过**配置映射 + 动态检测**的方式实现多语言支持。

#### 核心配置映射

**文件**：`config.py`

```python
# 语言到 Docker 镜像的映射
LANGUAGE_IMAGES = {
    "python": "python:3.11-slim",
    "python-vnc": "vnc-gui-browser:latest",  # 带VNC的Python环境
    "javascript": "node:18-slim",
    "java": "openjdk:11-jre-slim",
    "cpp": "gcc:latest",
    "go": "golang:1.21-alpine",
    "rust": "rust:1.75-slim",
}

# 语言到执行命令的映射
def get_command_by_language(language: str, filename: str) -> str:
    commands = {
        "python-vnc": f"python3 {filename}",
        "python": f"python {filename}",
        "javascript": f"node {filename}",
        "java": f"javac {filename} && java {filename[:-5]}",  # 编译+执行
        "cpp": f"g++ -o program {filename} && ./program",     # 编译+执行
        "go": f"go run {filename}",                           # 直接运行
        "rust": f"rustc {filename} -o program && ./program",  # 编译+执行
    }
    return commands.get(language, f"cat {filename}")  # 默认回退
```

#### 代码文件扩展名映射

**Docker 运行时** (`docker_runtime.py`)：
```python
def _create_code_file(self, code: str) -> str:
    extensions = {
        "python": ".py",
        "javascript": ".js",
        "java": ".java",
        "cpp": ".cpp",
        "go": ".go",
        "rust": ".rs",
        "python-vnc": ".py",
    }
    ext = extensions.get(self.config.language, ".txt")
    timestamp = int(time.time() * 1000)
    filename = f"{self.session_id}_{timestamp}{ext}"
    # ... 写入文件
```

**Local 运行时** (`local_runtime.py`)：
```python
def _create_code_file(self, code: str) -> str:
    extensions = {
        "python": ".py",
        "javascript": ".js",
        "java": ".java",
        "cpp": ".cpp",
        "c": ".c",
        "go": ".go",
        "rust": ".rs",
        "bash": ".sh",
    }
    ext = extensions.get(self.config.language, ".txt")
    # ... 创建临时文件
```

#### 语言特定的执行命令

**Local 运行时执行命令映射**：
```python
def _get_exec_command(self, code_file: str) -> List[str]:
    filename = os.path.basename(code_file)
    
    commands = {
        # 解释型语言：直接执行
        "python": ["python", code_file],
        "javascript": ["node", code_file],
        "go": ["go", "run", code_file],  # Go可直接run
        "bash": ["bash", code_file],
        
        # 编译型语言：编译后执行
        "java": [
            "sh", "-c",
            f"cd {os.path.dirname(code_file)} && javac {filename} && java {filename[:-5]}",
        ],
        "cpp": [
            "sh", "-c",
            f"cd {os.path.dirname(code_file)} && g++ -o program {filename} && ./program",
        ],
        "c": [
            "sh", "-c",
            f"cd {os.path.dirname(code_file)} && gcc -o program {filename} && ./program",
        ],
        "rust": [
            "sh", "-c",
            f"cd {os.path.dirname(code_file)} && rustc {filename} -o program && ./program",
        ],
    }
    
    return commands.get(self.config.language, ["cat", code_file])
```

#### 语言特定的依赖安装

**Docker 运行时依赖安装**：
```python
async def install_dependencies(self, dependencies: List[str]) -> ExecutionResult:
    if self.config.language.startswith("python"):
        # Python: 逐个安装，使用清华镜像
        for dep in dependencies:
            res = await asyncio.to_thread(
                self.container.exec_run,
                f"pip install --no-input --disable-pip-version-check {dep}",
            )
            
    elif self.config.language.startswith("javascript"):
        # JavaScript: npm init + npm install
        await asyncio.to_thread(
            self.container.exec_run, "npm init -y",
            workdir=self.config.working_dir
        )
        dep_str = " ".join(dependencies)
        res = await asyncio.to_thread(
            self.container.exec_run,
            f"npm install {dep_str}",
            workdir=self.config.working_dir,
        )
    else:
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            error=f"不支持的依赖安装语言: {self.config.language}",
        )
```

#### 运行时语言支持检测

**Docker 运行时**：基于 `LANGUAGE_IMAGES` 配置
```python
class DockerRuntime(SandboxRuntime):
    def __init__(self, runtime_id: str = "docker"):
        self.supported_languages = list(LANGUAGE_IMAGES.keys())
    
    def supports_language(self, language: str) -> bool:
        return language.lower() in self.supported_languages
```

**Local 运行时**：动态检测系统安装的语言
```python
class LocalRuntime(SandboxRuntime):
    def __init__(self, runtime_id: str = "local"):
        self.supported_languages = self._detect_supported_languages()
    
    def _detect_supported_languages(self) -> List[str]:
        """检测系统支持的编程语言"""
        languages = []
        
        language_commands = {
            "python": ["python", "--version"],
            "javascript": ["node", "--version"],
            "java": ["java", "-version"],
            "cpp": ["g++", "--version"],
            "c": ["gcc", "--version"],
            "go": ["go", "version"],
            "rust": ["rustc", "--version"],
            "bash": ["bash", "--version"],
        }
        
        for lang, cmd in language_commands.items():
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=2)
                if result.returncode == 0:
                    languages.append(lang)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass  # 命令不可用，跳过
        
        return languages
```

#### 多语言支持流程图

```
用户请求执行代码
       │
       ▼
┌─────────────────┐
│ 1. 指定language  │
│   (python/js等)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     否      ┌──────────────┐
│ 2. 检查运行时    │ ────────▶  │ 返回错误      │
│   是否支持该语言  │            │ 不支持的语言   │
└────────┬────────┘            └──────────────┘
         │ 是
         ▼
┌─────────────────┐
│ 3. 获取对应镜像  │  ← Docker: LANGUAGE_IMAGES[lang]
│   或检测本地环境 │  ← Local: _detect_supported_languages()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 创建代码文件  │  ← 根据语言选择扩展名(.py/.js/.java等)
│   写入工作目录   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 获取执行命令  │  ← get_command_by_language()
│   (解释型/编译型)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. 执行代码     │  ← 解释型: 直接执行
│   返回结果      │  ← 编译型: 编译后执行
└─────────────────┘
```

#### 解释型 vs 编译型语言处理差异

| 类型 | 语言 | 执行方式 | 特点 |
|-----|------|---------|------|
| **解释型** | Python, JavaScript, Go | 直接执行源代码 | 启动快，无需编译步骤 |
| **编译型** | Java, C++, C, Rust | 先编译后执行 | 需要编译时间，可捕获编译错误 |

**编译型语言特殊处理**：
```python
# Java: 先javac编译，再java执行
javac Hello.java && java Hello

# C++: 先g++编译，再执行
g++ -o program hello.cpp && ./program

# Rust: 先rustc编译，再执行
rustc hello.rs -o program && ./program
```

#### 扩展新语言的步骤

如需添加对新语言的支持（如 Ruby）：

1. **添加镜像映射**（`config.py`）：
```python
LANGUAGE_IMAGES = {
    # ... 现有语言
    "ruby": "ruby:3.2-slim",
}
```

2. **添加执行命令**（`config.py`）：
```python
def get_command_by_language(language: str, filename: str) -> str:
    commands = {
        # ... 现有命令
        "ruby": f"ruby {filename}",
    }
```

3. **添加扩展名映射**（`docker_runtime.py` 和 `local_runtime.py`）：
```python
extensions = {
    # ... 现有扩展名
    "ruby": ".rb",
}
```

4. **添加依赖安装支持**（可选）：
```python
if self.config.language == "ruby":
    for dep in dependencies:
        res = await asyncio.to_thread(
            self.container.exec_run,
            f"gem install {dep}",
        )
```

5. **Local 运行时检测**（`local_runtime.py`）：
```python
language_commands = {
    # ... 现有命令
    "ruby": ["ruby", "--version"],
}
```

### 2.3.5 Local 运行时详解

**文件**：`local_runtime.py`

**本地执行的安全设计**：
```python
class LocalSandboxSession(SandboxSession):
    def __init__(self, session_id: str, config: SessionConfig):
        self.work_dir = None
        self.process_pool = []           # 进程池，用于清理
        self.path_utils = PathUtils()
        self.process_manager = ProcessManager()
        self.security_utils = SecurityUtils()
```

**代码安全检查**：
```python
async def execute(self, code: str) -> ExecutionResult:
    # 1. 安全检查
    warnings = self.security_utils.validate_code(code, self.config.language)
    if warnings and any("危险操作" in w for w in warnings):
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            error=f"代码安全检查失败: {'; '.join(warnings)}",
        )
    # ... 执行代码
```

**SecurityUtils 实现细节**：
```python
class SecurityUtils:
    DANGEROUS_PATTERNS = [
        "import os",
        "import subprocess",
        "import sys",
        "__import__",
        "eval(",
        "exec(",
        "open(",
        "socket",
        "urllib",
        "requests",
        "rmdir", "remove", "unlink", "delete",
    ]

    @staticmethod
    def validate_code(code: str, language: str) -> List[str]:
        warnings = []
        code_lower = code.lower()
        for pattern in DANGEROUS_PATTERNS:
            if pattern in code_lower:
                warnings.append(f"检测到潜在危险操作: {pattern}")
        
        if language == "python" and "pickle" in code_lower:
            warnings.append("检测到 pickle 模块使用，可能存在安全风险")
        
        return warnings
```

**资源限制实现**：
```python
async def _run_with_limits(self, command: List[str]) -> Dict[str, Any]:
    # 1. 启动进程
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=self.work_dir,
    )
    
    # 2. 记录PID到进程池
    if process.pid:
        self.process_pool.append(process.pid)
    
    # 3. 实时监控内存使用
    if process.pid:
        proc_info = psutil.Process(process.pid)
        memory_usage = proc_info.memory_info().rss
        
        # 超出内存限制则终止
        if memory_usage > self.config.max_memory:
            process.terminate()
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "内存使用超出限制",
                "memory_usage": memory_usage,
            }
    
    # 4. 带超时等待
    stdout, stderr = await asyncio.wait_for(
        process.communicate(), timeout=self.config.timeout
    )
```

**进程树清理**：
```python
class ProcessManager:
    @staticmethod
    def kill_process_tree(pid: int) -> bool:
        """终止进程树（包括子进程）"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)  # 获取所有子进程
            
            # 先终止子进程
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            gone, alive = psutil.wait_procs(children, timeout=3)
            
            # 强制杀死未终止的进程
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # 最后终止父进程
            parent.terminate()
            parent.wait(timeout=3)
            
            return True
        except Exception as e:
            print(f"终止进程树失败: {e}")
            return False
```

**语言自动检测**：
```python
def _detect_supported_languages(self) -> List[str]:
    """检测系统支持的编程语言"""
    languages = []
    
    language_commands = {
        "python": ["python", "--version"],
        "javascript": ["node", "--version"],
        "java": ["java", "-version"],
        "cpp": ["g++", "--version"],
        "c": ["gcc", "--version"],
        "go": ["go", "version"],
        "rust": ["rustc", "--version"],
        "bash": ["bash", "--version"],
    }
    
    for lang, cmd in language_commands.items():
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=2)
            if result.returncode == 0:
                languages.append(lang)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    
    return languages
```

---

### 2.4 显示层 (Display Layer)

**位置**：`sandbox/display_layer/display_layer.py`

**DisplayResult 封装**：
```python
class DisplayResult:
    """统一的执行结果封装"""
    
    def __init__(
        self,
        status: str,              # "success" | "error" | "timeout"
        output: str,              # 标准输出
        error: str,               # 标准错误
        execution_time: float,    # 执行时间（秒）
        exit_code: int,           # 进程退出码
        files: List[str] = None,  # 生成的文件列表
        memory_usage: int = 0,    # 内存使用（字节）
    )
```

---

## 三、有状态会话设计

### 3.1 什么是有状态执行？

DB-GPT Sandbox 支持**有状态执行**，但与 Jupyter Notebook 的交互式 Cell 执行有所不同。

#### DB-GPT Sandbox 的有状态 vs Jupyter Notebook

| 特性 | DB-GPT Sandbox | Jupyter Notebook |
|-----|----------------|------------------|
| **依赖安装** |  安装后在同一会话中可用 |  安装后在 Notebook 中可用 |
| **变量保持** |  每次 execute 是独立执行 |  Cell 之间变量共享 |
| **执行粒度** | 完整脚本 | 分块 Cell |
| **交互性** | 批处理式 | 交互式 |

#### 有状态的具体含义

```
同一会话内的多次代码执行共享同一个环境：

第 1 次执行: pip install pandas
              ↓
              安装在会话环境中（容器内）
              ↓
第 2 次执行: import pandas   成功（依赖已存在）
              ↓
最后: disconnect → 销毁会话，释放资源

（如果是无状态，第 2 次执行会失败，因为每次都在新环境）
```

**关键区别说明**：

```python
#  DB-GPT Sandbox 不支持这种跨执行的变量保持
# 第 1 次执行
data = [1, 2, 3, 4, 5]  # 这个变量不会保留

# 第 2 次执行
print(data)  #  报错：name 'data' is not defined
```

```python
#  DB-GPT Sandbox 支持这种依赖的有状态
# 第 1 次执行：安装依赖
!pip install pandas

# 第 2 次执行：使用已安装的依赖
import pandas as pd  #  成功，因为 pandas 已在容器环境中
df = pd.DataFrame({'A': [1, 2, 3]})
print(df)
```

#### 为什么不做成 Notebook 式的变量保持？

DB-GPT Sandbox 的设计目标是**安全隔离的代码执行**，而非交互式开发：

1. **安全考虑**：每次执行都是独立脚本，避免变量污染和状态累积带来的安全隐患
2. **简单可控**：不需要维护复杂的内核状态（kernel）
3. **语言无关**：统一脚本执行模式，支持所有编译型和解释型语言
4. **易于调试**：每次执行结果独立，不依赖之前的执行历史

#### 如何实现类似 Notebook 的体验？

如果需要变量保持的 Notebook 体验，可以：

**方案 1：代码拼接（客户端处理）**
```python
# 在客户端维护代码历史
code_history = []

def execute_cell(code):
    code_history.append(code)
    full_code = "\n".join(code_history)  # 拼接所有代码
    return sandbox.execute(full_code)    # 发送到 Sandbox

# 第 1 个 Cell
execute_cell("data = [1, 2, 3, 4, 5]")

# 第 2 个 Cell
execute_cell("print(sum(data))")  # 可以访问 data，因为代码已拼接
```

**方案 2：使用持久化存储**
```python
# 第 1 次执行：保存到文件
import pickle
with open('/workspace/data.pkl', 'wb') as f:
    pickle.dump({'data': [1, 2, 3]}, f)

# 第 2 次执行：从文件读取
import pickle
with open('/workspace/data.pkl', 'rb') as f:
    saved = pickle.load(f)
print(saved['data'])
```

**方案 3：使用 Jupyter Kernel（扩展实现）**
如果需要真正的 Notebook 体验，可以在 Sandbox 中集成 Jupyter Kernel：
```python
# 在容器内启动 Jupyter Kernel
from jupyter_client import KernelManager
km = KernelManager(kernel_name='python3')
km.start_kernel()

# 通过 Kernel 执行代码（支持变量保持）
client = km.client()
client.execute("data = [1, 2, 3]")
client.execute("print(data)")  #  可以访问
```

#### 与无状态执行的对比

| 场景 | 无状态执行 | DB-GPT 有状态执行 |
|-----|-----------|------------------|
| 每次执行环境 | 全新容器/进程 | 复用同一容器 |
| 依赖安装 | 每次都需要重装 | 只需安装一次 |
| 执行速度 | 慢（冷启动） | 快（热容器） |
| 资源占用 | 高（频繁创建销毁） | 低（容器复用） |
| 适用场景 | 一次性脚本 | 多轮对话、工具链执行 |

### 3.2 实现机制

**会话生命周期管理**：
```python
# ControlLayer 中的会话跟踪
self.tasks: Dict[str, Dict[str, Any]] = {}

# 创建会话
async def _handle_connect(self, task: TaskObject) -> ExecutionResult:
    session = await self.runtime.create_session(session_id, config)
    self.tasks[task.task_id] = {
        "task": task,
        "session_id": session.session_id,
        "status": "connected",  # connected -> configured -> finished
    }

# 销毁会话
async def _handle_disconnect(self, task: TaskObject) -> ExecutionResult:
    success = await self.runtime.destroy_session(session_id)
    self.tasks[task.task_id]["status"] = "stopped"
```

**Docker 有状态实现**：
```python
# 第 1 次：安装依赖
result1 = await session.install_dependencies(["pandas", "numpy"])
# → 在容器内执行 pip install，依赖保留在容器中

# 第 2 次：使用依赖
result2 = await session.execute("import pandas; print(pandas.__version__)")
# → 同一容器，依赖可用

# 最后停止
await session.stop()  # 销毁容器，清理资源
```

---

## 四、工具类详解

### 4.1 资源限制配置

**文件**：`config.py`

```python
# 默认资源限制
MAX_MEMORY = 256 * 1024 * 1024      # 256MB 内存
MAX_CPU_PERCENT = 50.0              # 50% CPU
MAX_EXECUTION_TIME = 30             # 30秒超时
MAX_FILE_SIZE = 10 * 1024 * 1024    # 10MB 文件大小
MAX_PROCESSES = 10                  # 最大进程数
```

### 4.2 路径安全处理

```python
class PathUtils:
    @staticmethod
    def ensure_safe_path(path: str, base_dir: str) -> str:
        """防止路径遍历攻击"""
        normalized_path = os.path.normpath(path)
        normalized_base = os.path.normpath(base_dir)
        
        if not normalized_path.startswith(normalized_base):
            raise ValueError(f"不安全的路径: {path}")
        
        return normalized_path
```

### 4.3 系统资源监控

```python
class EnvironmentDetector:
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        return {
            "platform": platform.platform(),
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": psutil.disk_usage("/").percent,
        }
    
    @staticmethod
    def check_resource_availability(limits: ResourceLimits) -> Dict[str, bool]:
        memory = psutil.virtual_memory()
        return {
            "memory_ok": memory.available >= limits.max_memory,
            "cpu_ok": psutil.cpu_count() >= 1,
            "disk_ok": True,
        }
```

---

## 五、使用示例

### 5.1 基础使用

```python
from dbgpt_sandbox import Sandbox

# 创建沙箱（自动选择运行时）
sandbox = Sandbox()

# 创建会话
session = await sandbox.create_session(
    session_id="session_001",
    language="python",
    config={
        "timeout": 60,
        "max_memory": 512 * 1024 * 1024,  # 512MB
    }
)

# 安装依赖
await session.install_dependencies(["pandas", "numpy"])

# 执行代码
result = await session.execute("""
import pandas as pd
import numpy as np

df = pd.DataFrame({
    'A': np.random.randn(100),
    'B': np.random.randn(100)
})

print(df.describe())
""")

print(result.output)  # 输出执行结果

# 销毁会话
await session.stop()
```

### 5.2 多语言支持

```python
# JavaScript 执行
session = await sandbox.create_session(language="javascript")

result = await session.execute("""
const axios = require('axios');

async function main() {
    const response = await axios.get('https://api.github.com');
    console.log(response.headers);
}

main();
""")
```

### 5.3 指定运行时

```python
import os

# 强制使用 Docker
os.environ["SANDBOX_RUNTIME"] = "docker"
sandbox = Sandbox()

# 或强制使用 Local（无容器）
os.environ["SANDBOX_RUNTIME"] = "local"
sandbox = Sandbox()
```

### 5.4 VNC/GUI 模式

```python
# 创建带 VNC 的会话（用于浏览器自动化等）
session = await sandbox.create_session(language="python-vnc")

# 获取 VNC 连接地址
vnc_info = await session.get_vnc_info()
print(f"VNC端口: {vnc_info['vnc_port']}")
print(f"noVNC端口: {vnc_info['novnc_port']}")
# 用户可以通过浏览器连接到 VNC 查看 GUI
```

---

## 六、与其他项目对比

| 特性 | DB-GPT Sandbox | RAGFlow Sandbox | TaskWeaver | Open-Interpreter |
|------|----------------|-----------------|------------|------------------|
| **运行时** | Docker/Podman/Local | Docker/E2B/阿里云 | 内置/外部 | 本地/远程 |
| **语言支持** | 7+ 种 | Python/JS | Python | Python/Shell/JS |
| **有状态** |  |  |  | ⚠️ 有限 |
| **VNC/GUI** |  |  |  |  |
| **自动选择运行时** |  |  |  |  |
| **安全隔离** | 强 | 强 | 中 | 弱 |
| **依赖安装** |  自动 |  手动 |  自动 |  自动 |
| **任务锁机制** |  |  |  |  |
| **过期会话清理** |  |  |  |  |

---

## 七、核心设计亮点总结

### 7.1 架构设计

1. **四层架构清晰**：用户层 → 控制层 → 执行层 → 显示层，职责分明，易于扩展

2. **多运行时支持**：Docker/Podman/Nerdctl/Local 四种运行时自动选择，适应不同部署环境

3. **统一的抽象接口**：`SandboxRuntime` 和 `SandboxSession` 抽象，新增运行时只需实现接口

### 7.2 并发与任务管理

4. **任务级锁机制**：每个 `task_id` 独立的 `asyncio.Lock`，保证同一任务串行执行，不同任务并发

5. **会话生命周期管理**：自动跟踪会话状态（connected → configured → finished），支持过期清理

### 7.3 安全设计

6. **多层安全防护**：
   - 代码层：危险操作检测（SecurityUtils）
   - 运行时层：容器隔离、资源限制
   - 系统层：路径安全检查、进程树清理

7. **进程级资源限制**：Local 运行时通过 `psutil` 实时监控内存，超出限制自动终止

### 7.4 实用功能

8. **依赖自动安装**：支持 Python(pip) 和 JavaScript(npm) 的依赖安装，使用清华镜像加速

9. **文件传输机制**：Docker 运行时通过 tar 归档 + base64 编码传输文件，支持二进制

10. **健康检查与监控**：运行时健康检查、系统资源监控、会话状态查询

---

## 八、适用场景

| 场景 | 推荐运行时 | 理由 |
|------|-----------|------|
| 生产环境 | Docker | 最强隔离，资源可控，多语言支持 |
| 无 Docker 环境 | Podman/Local | 无需守护进程，rootless 安全 |
| 快速开发测试 | Local | 启动快（无容器开销），易于调试 |
| GUI 自动化 | python-vnc | 支持浏览器等 GUI 操作，带 VNC 远程 |
| 资源受限环境 | Local | 低内存占用，无需容器运行时 |

---

## 九、一句话总结

> **DB-GPT Sandbox 是一个企业级代码执行沙箱，通过四层架构提供统一的代码执行抽象，支持多种容器运行时和本地执行，实现了有状态会话、多语言支持、任务级并发控制和多层安全防护。**

---

*文档生成时间: 2026-02-06*  
*更新内容: 补充了 RuntimeFactory、DockerRuntime、LocalRuntime、工具类的详细实现*
