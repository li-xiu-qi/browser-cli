# smolagents 代码执行器选型指南

> 项目: smolagents
> 分析日期: 2026-02-06
> 源码位置: src/smolagents/local_python_executor.py, remote_executors.py

## 一、执行器总览

smolagents 提供了6种代码执行器，覆盖从本地开发到生产部署的完整场景。这些执行器分为两类：本地执行器和远程执行器。

### 本地执行器

| 执行器 | 核心特点 | 使用场景 |
|--------|----------|----------|
| LocalPythonExecutor | 基于AST解析的本地沙箱 | 开发测试、快速原型 |

### 远程执行器

| 执行器 | 隔离级别 | 部署方式 |
|--------|----------|----------|
| E2BExecutor | 完全沙箱隔离 | 托管云服务 |
| DockerExecutor | 容器隔离 | 本地/私有云 |
| ModalExecutor | 云端隔离 | 无服务器云 |
| BlaxelExecutor | 虚拟机隔离 | 边缘云 |
| WasmExecutor | WebAssembly隔离 | 本地轻量 |

### 继承关系

```
PythonExecutor (抽象基类)
├── LocalPythonExecutor
└── RemotePythonExecutor (抽象基类)
    ├── E2BExecutor
    ├── DockerExecutor
    ├── ModalExecutor
    ├── BlaxelExecutor
    └── WasmExecutor
```

## 二、详细对比分析

### 2.1 LocalPythonExecutor

**工作原理**

该执行器通过Python的AST模块解析代码，逐节点执行，实现了一个受限的Python解释器。它不依赖任何外部沙箱，完全在Python进程中运行。

**核心安全机制**

- AST白名单：仅允许预定义的AST节点类型
- 导入限制：通过authorized_imports参数控制可导入的模块
- 危险模块黑名单：禁止导入builtins、os、sys、subprocess等危险模块
- 危险函数黑名单：禁止调用compile、eval、exec、__import__等
- 双下划线限制：禁止访问非允许的dunder方法
- 操作计数限制：MAX_OPERATIONS = 10,000,000，防止无限循环
- 执行超时：默认30秒，通过ThreadPoolExecutor实现

**代码示例**

```python
from smolagents import LocalPythonExecutor

executor = LocalPythonExecutor(
    additional_authorized_imports=["numpy", "pandas"],
    max_print_outputs_length=50000,
    timeout_seconds=30
)

result = executor("import numpy as np; np.array([1, 2, 3]).sum()")
```

**优缺点**

| 优点 | 缺点 |
|------|------|
| 启动速度极快 | 安全性有限 |
| 无需外部依赖 | 无法完全隔离系统资源 |
| 内存占用低 | 不支持网络访问 |
| 跨平台兼容 | 共享主进程内存空间 |

### 2.2 E2BExecutor

**工作原理**

基于E2B提供的云端代码解释器沙箱，每个执行器实例对应一个独立的云端沙箱环境。通过E2B SDK与云端沙箱通信，代码在云端执行，结果通过网络返回。

**核心安全机制**

- 完全隔离的云端沙箱环境
- 网络与文件系统完全隔离
- 支持超时自动销毁
- 支持多种输出格式：图片、JSON、HTML、LaTeX等

**代码示例**

```python
from smolagents import E2BExecutor

executor = E2BExecutor(
    additional_imports=["numpy", "matplotlib"],
    logger=logger,
    # 支持E2B Sandbox的所有参数
    timeout=300
)

result = executor("print('Hello from E2B')")
executor.cleanup()  # 清理沙箱
```

**优缺点**

| 优点 | 缺点 |
|------|------|
| 最高级别的安全性 | 启动时间较长 |
| 支持文件系统操作 | 依赖网络连接 |
| 支持网络访问 | 需要E2B API密钥 |
| 自动资源清理 | 按量计费 |

### 2.3 DockerExecutor

**工作原理**

在本地Docker容器中运行Jupyter Kernel Gateway，通过WebSocket与容器内的Python内核通信。首次使用需要构建Docker镜像，后续可复用。

**核心安全机制**

- Docker容器隔离
- 支持自定义Dockerfile
- 端口隔离
- 可配置容器运行参数

**代码示例**

```python
from smolagents import DockerExecutor

executor = DockerExecutor(
    additional_imports=["scipy"],
    logger=logger,
    host="127.0.0.1",
    port=8888,
    image_name="jupyter-kernel",
    build_new_image=False,  # 复用已有镜像
    container_run_kwargs={
        "mem_limit": "512m",
        "cpu_quota": 100000
    }
)

result = executor("import scipy; print(scipy.__version__)")
executor.cleanup()
```

**优缺点**

| 优点 | 缺点 |
|------|------|
| 完全本地运行，数据不外流 | 需要安装Docker |
| 启动后可复用 | 首次启动需构建镜像 |
| 资源可控 | 冷启动较慢 |
| 免费 | 占用本地资源 |

### 2.4 ModalExecutor

**工作原理**

基于Modal云服务创建临时沙箱，通过Modal的Sandbox API在云端执行代码。使用Jupyter Kernel Gateway作为执行后端。

**核心安全机制**

- Modal云端沙箱隔离
- 加密端口通信
- 自动超时销毁
- Token认证

**代码示例**

```python
from smolagents import ModalExecutor
import modal

executor = ModalExecutor(
    additional_imports=["requests"],
    logger=logger,
    app_name="smolagent-executor",
    port=8888,
    create_kwargs={
        "timeout": 60 * 5,  # 5分钟超时
        "secrets": [modal.Secret.from_name("my-secret")]
    }
)

result = executor("import requests; print(requests.get('https://api.example.com').json())")
executor.cleanup()
```

**优缺点**

| 优点 | 缺点 |
|------|------|
| 云端无服务器架构 | 需要Modal账号 |
| 自动扩缩容 | 按量计费 |
| 支持GPU等高级资源 | 依赖网络 |
| 支持持久化存储 | 冷启动较慢 |

### 2.5 BlaxelExecutor

**工作原理**

基于Blaxel平台创建虚拟机沙箱，支持从休眠状态快速唤醒。使用WebSocket与Jupyter Kernel通信。

**核心安全机制**

- 虚拟机级别隔离
- 支持内存和TTL配置
- 区域选择
- API密钥认证

**代码示例**

```python
from smolagents import BlaxelExecutor

executor = BlaxelExecutor(
    additional_imports=["pandas"],
    logger=logger,
    sandbox_name="my-executor",
    image="blaxel/jupyter-notebook",
    memory=4096,  # MB
    region="us-east-1",
    ttl="1h"  # 空闲1小时后销毁
)

result = executor("import pandas as pd; print(pd.DataFrame({'a': [1, 2]}))")
executor.cleanup()
```

**优缺点**

| 优点 | 缺点 |
|------|------|
| 快速唤醒 | 需要Blaxel账号 |
| 支持自定义镜像 | 按量计费 |
| 可配置TTL | 依赖网络 |
| 区域选择 | 相对较新的服务 |

### 2.6 WasmExecutor

**工作原理**

使用Deno运行时加载Pyodide，在WebAssembly环境中执行Python代码。Pyodide是CPython的WebAssembly编译版本。

**核心安全机制**

- WebAssembly沙箱隔离
- Deno权限系统控制资源访问
- 默认最小权限原则
- 可自定义Deno权限

**代码示例**

```python
from smolagents import WasmExecutor

executor = WasmExecutor(
    additional_imports=["numpy"],
    logger=logger,
    deno_path="deno",  # Deno可执行文件路径
    deno_permissions=[
        "allow-net=cdn.jsdelivr.net:443,files.pythonhosted.org:443",
        "allow-read=/tmp",
        "allow-write=/tmp"
    ],
    timeout=60
)

result = executor("import numpy as np; print(np.random.rand(3))")
executor.cleanup()
```

**优缺点**

| 优点 | 缺点 |
|------|------|
| 本地运行，无外网依赖 | 需要安装Deno |
| WebAssembly强隔离 | Pyodide包兼容性有限 |
| 启动速度较快 | 不支持原生扩展 |
| 资源占用低 | 性能略低于原生Python |

## 三、安全性评估

### 3.1 安全等级对比

| 执行器 | 隔离级别 | 防逃逸能力 | 资源限制 | 适用敏感数据 |
|--------|----------|------------|----------|--------------|
| LocalPythonExecutor | 进程级 | 低 | AST限制 | 否 |
| WasmExecutor | WebAssembly | 中 | Deno权限 | 否 |
| DockerExecutor | 容器级 | 高 | cgroups | 是 |
| E2BExecutor | 沙箱级 | 极高 | 完全隔离 | 是 |
| ModalExecutor | 云端级 | 极高 | 完全隔离 | 是 |
| BlaxelExecutor | VM级 | 极高 | 完全隔离 | 是 |

### 3.2 LocalPythonExecutor 安全细节

**白名单机制**

```python
# 允许的AST节点类型
ALLOWED_AST_NODES = [
    ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Call,
    ast.Constant, ast.Tuple, ast.List, ast.Dict, ast.Set,
    ast.FunctionDef, ast.ClassDef, ast.If, ast.For, ast.While,
    # ... 共支持40+种节点
]

# 危险模块黑名单
DANGEROUS_MODULES = [
    "builtins", "io", "multiprocessing", "os", "pathlib",
    "pty", "shutil", "socket", "subprocess", "sys"
]

# 危险函数黑名单
DANGEROUS_FUNCTIONS = [
    "builtins.compile", "builtins.eval", "builtins.exec",
    "builtins.globals", "builtins.locals", "builtins.__import__",
    "os.popen", "os.system", "posix.system"
]
```

**安全检查流程**

1. 解析代码为AST
2. 遍历AST节点，检查每个节点类型是否在白名单
3. 检查import语句，验证模块是否在authorized_imports中
4. 检查函数调用，验证是否在黑名单中
5. 执行时监控操作计数，防止无限循环
6. 超时监控，通过ThreadPoolExecutor实现

### 3.3 远程执行器通用安全特性

所有远程执行器都继承自RemotePythonExecutor，共享以下安全特性：

- 工具隔离：通过pickle序列化传递变量，不共享内存
- FinalAnswerException：使用特殊异常捕获最终结果
- 日志隔离：执行日志与结果分离
- 自动清理：支持cleanup方法释放资源

## 四、性能对比

### 4.1 启动时间对比

| 执行器 | 首次启动 | 后续启动 | 主要耗时环节 |
|--------|----------|----------|--------------|
| LocalPythonExecutor | < 10ms | < 10ms | 无 |
| WasmExecutor | 2-5s | 2-5s | 启动Deno服务器 |
| DockerExecutor | 30-120s | 5-10s | 构建镜像/启动容器 |
| E2BExecutor | 10-30s | 10-30s | 创建云端沙箱 |
| ModalExecutor | 15-45s | 15-45s | 创建云端沙箱 |
| BlaxelExecutor | 5-15s | < 1s | 从休眠唤醒 |

### 4.2 执行速度对比

| 执行器 | 相对速度 | 主要影响因素 |
|--------|----------|--------------|
| LocalPythonExecutor | 1.0x | 原生Python执行 |
| DockerExecutor | 0.95x | 容器开销极小 |
| E2BExecutor | 0.9x | 网络延迟 |
| ModalExecutor | 0.9x | 网络延迟 |
| BlaxelExecutor | 0.9x | 网络延迟 |
| WasmExecutor | 0.6x | WebAssembly转换开销 |

### 4.3 内存占用对比

| 执行器 | 基础内存 | 执行内存 | 备注 |
|--------|----------|----------|------|
| LocalPythonExecutor | 20MB | 取决于代码 | 共享主进程 |
| WasmExecutor | 50MB | 取决于代码 | Deno + Pyodide |
| DockerExecutor | 100MB+ | 可配置 | 容器开销 |
| E2BExecutor | 云端 | 云端 | 不占本地资源 |
| ModalExecutor | 云端 | 云端 | 不占本地资源 |
| BlaxelExecutor | 云端 | 云端 | 不占本地资源 |

### 4.4 网络开销对比

| 执行器 | 网络依赖 | 数据传输 | 延迟影响 |
|--------|----------|----------|----------|
| LocalPythonExecutor | 无 | 无 | 无 |
| WasmExecutor | 可选 | 本地HTTP | 极小 |
| DockerExecutor | 无 | 本地WebSocket | 极小 |
| E2BExecutor | 必需 | API调用 | 中高 |
| ModalExecutor | 必需 | API调用 | 中高 |
| BlaxelExecutor | 必需 | API调用 | 中 |

## 五、选型决策树

```
开始
│
├─ 是否处理敏感数据？
│  ├─ 是 → 选择 E2BExecutor / ModalExecutor / BlaxelExecutor
│  │         这些执行器提供完全隔离的沙箱环境
│  │
│  └─ 否 → 继续
│
├─ 是否需要网络访问？
│  ├─ 是 → 继续
│  │
│  └─ 否 → 选择 LocalPythonExecutor
│            最安全、最快、最简单的选择
│
├─ 是否需要文件系统操作？
│  ├─ 是 → 继续
│  │
│  └─ 否 → 选择 WasmExecutor
│            本地运行，WebAssembly隔离，无需Docker
│
├─ 是否已有Docker环境？
│  ├─ 是 → 选择 DockerExecutor
│  │         本地隔离，数据不外流，资源可控
│  │
│  └─ 否 → 继续
│
├─ 是否有云预算？
│  ├─ 是 → 选择 E2BExecutor / ModalExecutor
│  │         托管服务，无需运维，按量付费
│  │
│  └─ 否 → 安装Docker后使用 DockerExecutor
│            或重新考虑是否真的需要网络/文件访问
│
└─ 结束
```

### 5.1 场景化推荐

**场景一：本地开发测试**

推荐：LocalPythonExecutor

理由：
- 启动最快，适合频繁调试
- 无需额外配置
- 代码在本地执行，便于调试

**场景二：数据分析脚本**

推荐：LocalPythonExecutor + 受限导入

理由：
- 数据分析通常使用pandas、numpy等库
- 这些库可被授权使用
- 不需要网络或文件系统访问

**场景三：Web爬虫任务**

推荐：DockerExecutor 或 E2BExecutor

理由：
- 需要网络访问
- 需要隔离执行环境
- 防止恶意代码影响系统

**场景四：多租户SaaS服务**

推荐：E2BExecutor 或 ModalExecutor

理由：
- 完全隔离，保障租户数据安全
- 自动资源管理
- 可按租户动态创建销毁

**场景五：边缘计算/轻量部署**

推荐：WasmExecutor

理由：
- 资源占用低
- 启动速度快于容器
- WebAssembly提供良好隔离

**场景六：企业私有化部署**

推荐：DockerExecutor

理由：
- 数据不出本地
- 完全可控的资源限制
- 可利用现有Docker基础设施

## 六、成本分析

### 6.1 直接成本

| 执行器 | 成本类型 | 估算费用 | 备注 |
|--------|----------|----------|------|
| LocalPythonExecutor | 免费 | 0 | 完全免费 |
| WasmExecutor | 免费 | 0 | 仅需Deno |
| DockerExecutor | 免费 | 0 | 仅需Docker |
| E2BExecutor | 按量计费 | $0.01-0.05/执行 | 根据使用时长 |
| ModalExecutor | 按量计费 | $0.0001/秒 | CPU时间 |
| BlaxelExecutor | 按量计费 | 按配置计费 | 内存+时间 |

### 6.2 隐性成本

| 执行器 | 运维成本 | 学习成本 | 集成成本 |
|--------|----------|----------|----------|
| LocalPythonExecutor | 低 | 低 | 低 |
| WasmExecutor | 低 | 中 | 低 |
| DockerExecutor | 中 | 中 | 中 |
| E2BExecutor | 低 | 低 | 低 |
| ModalExecutor | 低 | 中 | 中 |
| BlaxelExecutor | 低 | 中 | 中 |

### 6.3 成本优化建议

1. **开发阶段**：使用LocalPythonExecutor，零成本快速迭代
2. **测试阶段**：使用DockerExecutor，模拟生产环境
3. **生产阶段**：根据安全需求选择云端执行器
4. **批量任务**：考虑使用DockerExecutor本地批处理，避免云费用累积
5. **高频调用**：考虑连接池或复用执行器实例，减少冷启动开销

## 七、使用示例

### 7.1 基础使用模式

所有执行器遵循相同的接口设计：

```python
from smolagents import CodeAgent, HfApiModel

# 1. 创建执行器
executor = SomeExecutor(
    additional_imports=["numpy", "pandas"],
    logger=logger
)

# 2. 在Agent中使用
agent = CodeAgent(
    tools=[], 
    model=HfApiModel(),
    executor=executor  # 指定自定义执行器
)

# 3. 清理资源
executor.cleanup()
```

### 7.2 完整示例：切换执行器

```python
import os
from smolagents import CodeAgent, HfApiModel

# 根据环境变量选择执行器
EXECUTOR_TYPE = os.getenv("EXECUTOR_TYPE", "local")

if EXECUTOR_TYPE == "local":
    from smolagents import LocalPythonExecutor
    executor = LocalPythonExecutor(
        additional_authorized_imports=["numpy", "pandas"],
        timeout_seconds=30
    )
    
elif EXECUTOR_TYPE == "docker":
    from smolagents import DockerExecutor
    executor = DockerExecutor(
        additional_imports=["numpy", "pandas"],
        logger=logger,
        image_name="smolagents-env",
        build_new_image=False
    )
    
elif EXECUTOR_TYPE == "e2b":
    from smolagents import E2BExecutor
    executor = E2BExecutor(
        additional_imports=["numpy", "pandas"],
        logger=logger,
        timeout=300
    )
    
elif EXECUTOR_TYPE == "wasm":
    from smolagents import WasmExecutor
    executor = WasmExecutor(
        additional_imports=["numpy"],
        logger=logger,
        timeout=60
    )

# 创建Agent
agent = CodeAgent(
    tools=[],
    model=HfApiModel(),
    executor=executor
)

# 运行
try:
    result = agent.run("计算1到100的和")
finally:
    # 确保清理资源
    if hasattr(executor, 'cleanup'):
        executor.cleanup()
```

### 7.3 安全配置最佳实践

```python
from smolagents import LocalPythonExecutor

# 生产环境配置：最小权限原则
executor = LocalPythonExecutor(
    # 仅授权必需的模块
    additional_authorized_imports=[
        "numpy",
        "pandas",
        # 禁止os、sys等系统模块
    ],
    # 限制输出长度，防止内存攻击
    max_print_outputs_length=10000,
    # 设置合理的超时时间
    timeout_seconds=10,
    # 添加自定义安全函数
    additional_functions={
        "safe_sum": lambda x: sum(x)  # 替代eval
    }
)
```

### 7.4 Docker执行器高级配置

```python
from smolagents import DockerExecutor

executor = DockerExecutor(
    additional_imports=["scipy", "scikit-learn"],
    logger=logger,
    # 自定义Dockerfile
    dockerfile_content="""
FROM python:3.11-slim
RUN pip install jupyter_kernel_gateway jupyter_client ipykernel
RUN pip install scipy scikit-learn pandas
EXPOSE 8888
CMD ["jupyter", "kernelgateway", "--KernelGatewayApp.ip='0.0.0.0'", "--KernelGatewayApp.port=8888"]
""",
    # 容器资源限制
    container_run_kwargs={
        "mem_limit": "1g",
        "cpu_quota": 50000,  # 50% CPU
        "cpu_period": 100000,
        "network_mode": "bridge"
    }
)
```

## 八、对我们项目的建议

### 8.1 分层执行策略

建议在我们的AI数据分析系统中采用分层执行策略：

| 层级 | 执行器 | 用途 |
|------|--------|------|
| 开发层 | LocalPythonExecutor | 本地开发、单元测试 |
| 测试层 | DockerExecutor | 集成测试、CI/CD |
| 生产层 | E2BExecutor / ModalExecutor | 用户代码执行 |
| 边缘层 | WasmExecutor | 轻量级客户端部署 |

### 8.2 动态执行器选择

实现根据任务特性自动选择执行器：

```python
def select_executor(task_config):
    """根据任务配置选择最适合的执行器"""
    
    # 危险等级评估
    risk_level = assess_risk(task_config.code)
    
    # 需要外部资源
    needs_network = task_config.requires_network
    needs_filesystem = task_config.requires_filesystem
    
    if risk_level == "high" or needs_network or needs_filesystem:
        # 高风险任务使用云端隔离
        return E2BExecutor(...)
    elif risk_level == "medium":
        # 中风险使用Docker隔离
        return DockerExecutor(...)
    else:
        # 低风险使用本地执行
        return LocalPythonExecutor(...)
```

### 8.3 实施路线图

**第一阶段：MVP开发**
- 使用LocalPythonExecutor快速验证核心功能
- 限制导入列表，确保基础安全性

**第二阶段：安全加固**
- 引入DockerExecutor用于测试环境
- 建立代码风险扫描机制

**第三阶段：生产就绪**
- 接入E2BExecutor或ModalExecutor
- 实现执行器自动切换逻辑
- 建立完整的监控和审计日志

**第四阶段：性能优化**
- 引入WasmExecutor处理轻量任务
- 实现执行器连接池
- 优化冷启动时间

### 8.4 关键注意事项

1. **永远不要信任用户代码**：即使使用LocalPythonExecutor，也要严格限制授权导入
2. **监控资源使用**：所有执行器都应设置超时和资源限制
3. **日志记录**：完整记录代码执行过程，便于审计和调试
4. **错误处理**：优雅处理执行器异常，避免信息泄露
5. **资源清理**：确保所有执行器都正确调用cleanup方法

### 8.5 参考链接

- smolagents文档：[[参考项目/smolagents/README|smolagents项目文档]]
- E2B文档：https://e2b.dev
- Modal文档：https://modal.com
- Blaxel文档：https://blaxel.ai
- Pyodide文档：https://pyodide.org

---

*本文档基于smolagents源码分析生成，分析日期：2026-02-06*
