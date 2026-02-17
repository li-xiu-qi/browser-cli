# RAGFlow 工作流状态存储机制深度分析

**分析日期**: 2026-02-05  
**项目版本**: RAGFlow v0.23.1  
**核心结论**: **全状态后端持久化** - DSL（JSON）存储工作流定义+执行状态+运行时数据

---

## 一、状态存储架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RAGFlow 工作流状态存储架构                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  【前端】                    【后端】                      【数据库】        │
│  React Flow                 Flask API                    MySQL              │
│     │                           │                           │               │
│     │  1. 保存工作流            │                           │               │
│     │ ──────────────────────>   │                           │               │
│     │  POST /canvas/save        │                           │               │
│     │  {dsl: JSON}              │                           │               │
│     │                           │  2. 存储DSL               │               │
│     │                           │ ──────────────────────>   │               │
│     │                           │  INSERT/UPDATE            │               │
│     │                           │  user_canvas表            │               │
│     │                           │                           │               │
│     │  3. 执行工作流            │                           │               │
│     │ ──────────────────────>   │                           │               │
│     │  POST /canvas/{id}/run    │                           │               │
│     │                           │  4. 加载DSL               │               │
│     │                           │ ──────────────────────>   │               │
│     │                           │  SELECT dsl FROM ...      │               │
│     │                           │                           │               │
│     │                           │  5. 执行并更新状态        │               │
│     │                           │  Canvas.run()             │               │
│     │                           │  dsl[history] += ...      │               │
│     │                           │                           │               │
│     │                           │  6. 保存更新后的DSL       │               │
│     │                           │ ──────────────────────>   │               │
│     │                           │  UPDATE user_canvas       │               │
│     │  7. 返回结果              │                           │               │
│     │ <──────────────────────   │                           │               │
│     │  {result, history}        │                           │               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、数据库模型设计

### 2.1 UserCanvas 表结构

```python
# api/db/db_models.py

class UserCanvas(DataBaseModel):
    """
    用户工作流（Canvas）模型
    
    关键字段：
    - dsl: JSONField - 存储完整的工作流定义+状态
    """
    id = CharField(max_length=32, primary_key=True)
    
    # 基础信息
    user_id = CharField(max_length=255, index=True)  # 所属用户
    title = CharField(max_length=255, null=True)      # 工作流标题
    description = TextField(null=True)                 # 描述
    
    # 权限控制
    permission = CharField(max_length=16, default="me")  # me|team
    
    # 分类标签
    canvas_type = CharField(max_length=32, null=True)     # 工作流类型
    canvas_category = CharField(max_length=32, default="agent_canvas")  # agent_canvas|dataflow_canvas
    
    # ★★★ 核心字段：DSL（Domain Specific Language）★★★
    dsl = JSONField(null=True, default={})
    # dsl 包含：
    # - components: 组件定义（节点、连线、配置）
    # - history: 执行历史记录
    # - path: 当前执行路径
    # - retrieval: 检索结果缓存
    # - globals: 全局变量
    # - variables: 用户自定义变量
    # - memory: 记忆/上下文
    
    class Meta:
        db_table = "user_canvas"
```

### 2.2 DSL 数据结构详解

```json
{
  // 1. 组件定义 - 工作流的结构和配置
  "components": {
    "begin": {
      "obj": {
        "component_name": "Begin",
        "params": {
          "prologue": "你好，我是AI助手",
          "query": "{{sys.query}}"
        }
      },
      "downstream": ["retrieval_0"],  // 下游节点
      "upstream": []                   // 上游节点
    },
    "retrieval_0": {
      "obj": {
        "component_name": "Retrieval",
        "params": {
          "kb_ids": ["kb_123"],
          "top_k": 5
        }
      },
      "downstream": ["generate_0"],
      "upstream": ["begin"]
    },
    "generate_0": {
      "obj": {
        "component_name": "Generate",
        "params": {
          "llm_id": "gpt-4",
          "prompt_template": "基于以下信息回答：\n{context}\n\n问题：{query}"
        }
      },
      "downstream": ["answer_0"],
      "upstream": ["retrieval_0"]
    },
    "answer_0": {
      "obj": {
        "component_name": "Answer",
        "params": {}
      },
      "downstream": [],
      "upstream": ["generate_0"]
    }
  },
  
  // 2. 执行历史 - 记录每次运行的输入输出
  "history": [
    {
      "id": "run_001",
      "timestamp": "2024-11-15T10:30:00Z",
      "input": {"query": "什么是RAG？"},
      "output": {"answer": "RAG是检索增强生成..."},
      "path": ["begin", "retrieval_0", "generate_0", "answer_0"],
      "duration": 2.5
    },
    {
      "id": "run_002",
      "timestamp": "2024-11-15T10:35:00Z",
      "input": {"query": "如何实现RAG？"},
      "output": {"answer": "实现RAG需要..."},
      "path": ["begin", "retrieval_0", "generate_0", "answer_0"],
      "duration": 3.2
    }
  ],
  
  // 3. 当前执行路径 - 记录执行进度
  "path": ["begin", "retrieval_0", "generate_0", "answer_0"],
  
  // 4. 检索结果 - 缓存检索到的文档
  "retrieval": {
    "chunks": [
      {"content": "RAG是...", "doc_id": "doc_1", "score": 0.95},
      {"content": "RAG的优势...", "doc_id": "doc_2", "score": 0.88}
    ],
    "doc_aggs": [
      {"doc_id": "doc_1", "doc_name": "RAG介绍.pdf", "count": 3}
    ]
  },
  
  // 5. 全局变量 - 系统级变量
  "globals": {
    "sys.query": "什么是RAG？",
    "sys.user_id": "user_123",
    "sys.conversation_turns": 5,
    "sys.files": [],
    "sys.history": []
  },
  
  // 6. 用户变量 - 自定义变量
  "variables": {
    "company_name": "InfiniFlow",
    "version": "v0.23.1"
  },
  
  // 7. 记忆 - 长期记忆存储
  "memory": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮你的？"}
  ],
  
  // 8. 图形信息 - 前端展示用
  "graph": {
    "nodes": [
      {"id": "begin", "type": "begin", "position": {"x": 100, "y": 100}},
      {"id": "retrieval_0", "type": "retrieval", "position": {"x": 300, "y": 100}},
      {"id": "generate_0", "type": "generate", "position": {"x": 500, "y": 100}},
      {"id": "answer_0", "type": "answer", "position": {"x": 700, "y": 100}}
    ],
    "edges": [
      {"source": "begin", "target": "retrieval_0"},
      {"source": "retrieval_0", "target": "generate_0"},
      {"source": "generate_0", "target": "answer_0"}
    ]
  },
  
  // 9. 任务ID - 用于异步任务追踪
  "task_id": "task_abc_123"
}
```

---

## 三、状态管理核心代码

### 3.1 Canvas 类 - 状态加载与保存

```python
# agent/canvas.py

class Canvas(Graph):
    """
    Canvas工作流引擎
    
    职责：
    1. 从DSL加载工作流定义和状态
    2. 执行工作流
    3. 更新DSL中的状态
    """
    
    def __init__(self, dsl: str, tenant_id=None, task_id=None, canvas_id=None, custom_header=None):
        """
        Args:
            dsl: JSON字符串，包含完整的工作流定义和状态
            tenant_id: 租户ID（多租户隔离）
            task_id: 任务ID（异步任务追踪）
            canvas_id: Canvas ID（数据库主键）
        """
        # 初始化全局变量
        self.globals = {
            "sys.query": "",
            "sys.user_id": tenant_id,
            "sys.conversation_turns": 0,
            "sys.files": [],
            "sys.history": []
        }
        self.variables = {}
        
        # ★ 调用父类Graph初始化，解析DSL
        super().__init__(dsl, tenant_id, task_id, custom_header=custom_header)
        
        self._id = canvas_id
    
    def load(self):
        """从DSL加载状态"""
        super().load()
        
        # ★ 加载执行历史
        self.history = self.dsl["history"]
        
        # ★ 加载全局变量
        if "globals" in self.dsl:
            self.globals = self.dsl["globals"]
        
        # ★ 加载用户变量
        if "variables" in self.dsl:
            self.variables = self.dsl["variables"]
        
        # ★ 加载检索结果
        self.retrieval = self.dsl["retrieval"]
        
        # ★ 加载记忆
        self.memory = self.dsl.get("memory", [])
    
    def __str__(self):
        """
        序列化DSL（保存前调用）
        
        将运行时的状态写回DSL
        """
        # ★ 保存执行历史
        self.dsl["history"] = self.history
        
        # ★ 保存检索结果
        self.dsl["retrieval"] = self.retrieval
        
        # ★ 保存记忆
        self.dsl["memory"] = self.memory
        
        # ★ 保存全局变量
        self.dsl["globals"] = self.globals
        
        # ★ 保存用户变量
        self.dsl["variables"] = self.variables
        
        # 调用父类序列化
        return super().__str__()
    
    def reset(self, mem=False):
        """重置状态（不清除历史）"""
        super().reset()
        if not mem:
            self.history = []
            self.retrieval = []
            self.memory = []
```

### 3.2 Graph 基类 - DSL解析

```python
# agent/canvas.py

class Graph:
    """图结构基类"""
    
    def __init__(self, dsl: str, tenant_id=None, task_id=None, custom_header=None):
        self.path = []          # 执行路径
        self.components = {}    # 组件实例
        self.error = ""
        
        # ★ 解析DSL JSON
        self.dsl = json.loads(dsl)
        
        self._tenant_id = tenant_id
        self.task_id = task_id or get_uuid()
        self.custom_header = custom_header
        
        # ★ 加载组件
        self.load()
    
    def load(self):
        """加载组件定义"""
        self.components = self.dsl["components"]
        
        # 实例化组件
        for k, cpn in self.components.items():
            # 创建组件参数对象
            param = component_class(cpn["obj"]["component_name"] + "Param")()
            cpn["obj"]["params"]["custom_header"] = self.custom_header
            param.update(cpn["obj"]["params"])
            
            # 参数校验
            param.check()
            
            # 实例化组件
            cpn["obj"] = component_class(cpn["obj"]["component_name"])(self, k, param)
        
        # ★ 加载执行路径
        self.path = self.dsl["path"]
    
    def __str__(self):
        """序列化为JSON字符串"""
        self.dsl["path"] = self.path
        self.dsl["task_id"] = self.task_id
        
        dsl = {"components": {}}
        
        # 复制非组件字段
        for k in self.dsl.keys():
            if k in ["components"]:
                continue
            dsl[k] = deepcopy(self.dsl[k])
        
        # ★ 序列化组件（将对象转为字典）
        for k, cpn in self.components.items():
            if k not in dsl["components"]:
                dsl["components"][k] = {}
            for c in cpn.keys():
                if c == "obj":
                    # 组件对象转为JSON
                    dsl["components"][k][c] = json.loads(str(cpn["obj"]))
                else:
                    dsl["components"][k][c] = deepcopy(cpn[c])
        
        return json.dumps(dsl, ensure_ascii=False)
```

---

## 四、状态持久化流程

### 4.1 完整执行流程

```python
# 简化的执行流程（agent/canvas.py 中的 run 方法）

class Canvas(Graph):
    
    async def run(self, **kwargs):
        """执行工作流"""
        
        # 1. 初始化输入
        self.globals["sys.query"] = kwargs.get("query", "")
        self.globals["sys.files"] = kwargs.get("files", [])
        
        # 2. 执行路径遍历
        exe_path = self.path if self.path else self._build_execute_path()
        
        # 3. 逐个执行组件
        for cpn_id in exe_path:
            # 检查是否取消
            if self.is_canceled():
                raise TaskCanceledException()
            
            # 获取组件
            cpn = self.get_component(cpn_id)
            if not cpn:
                continue
            
            # 执行组件
            result = await cpn["obj"].run()
            
            # ★ 更新路径（记录执行进度）
            if cpn_id not in self.path:
                self.path.append(cpn_id)
        
        # 4. 构建结果
        result = {
            "answer": self.get_final_answer(),
            "reference": self.retrieval.get("chunks", []),
            "history": self.history
        }
        
        # 5. ★ 更新历史记录
        self.history.append({
            "id": get_uuid(),
            "timestamp": datetime.now().isoformat(),
            "input": kwargs,
            "output": result,
            "path": self.path.copy()
        })
        
        return result
    
    def get_final_answer(self):
        """获取最终答案"""
        # 从Answer组件获取输出
        for cpn_id, cpn in self.components.items():
            if cpn["obj"].component_name == "Answer":
                return cpn["obj"].get_output()
        return ""
```

### 4.2 API 层 - 保存与加载

```python
# api/apps/canvas_app.py 简化示意

from flask import Blueprint, request
from api.db.services.canvas_service import UserCanvasService

@canvas_blueprint.route('/<canvas_id>/run', methods=['POST'])
def run_canvas(canvas_id):
    """执行工作流"""
    
    # 1. 从数据库加载DSL
    canvas_record = UserCanvasService.get_by_id(canvas_id)
    dsl = canvas_record.dsl
    
    # 2. 创建Canvas实例（加载状态）
    canvas = Canvas(
        dsl=json.dumps(dsl),
        tenant_id=canvas_record.tenant_id,
        canvas_id=canvas_id
    )
    
    # 3. 获取用户输入
    input_data = request.json
    
    # 4. 执行工作流
    result = canvas.run(**input_data)
    
    # 5. ★ 保存更新后的DSL（包含新的历史记录）
    updated_dsl = json.loads(str(canvas))
    UserCanvasService.update(canvas_id, dsl=updated_dsl)
    
    return jsonify(result)


@canvas_blueprint.route('/save', methods=['POST'])
def save_canvas():
    """保存工作流"""
    data = request.json
    
    canvas_data = {
        "id": data.get("id") or get_uuid(),
        "user_id": current_user.id,
        "title": data["title"],
        "dsl": data["dsl"]  # ★ 直接存储前端传来的DSL
    }
    
    if data.get("id"):
        UserCanvasService.update(data["id"], **canvas_data)
    else:
        UserCanvasService.create(**canvas_data)
    
    return jsonify({"id": canvas_data["id"]})
```

---

## 五、状态存储设计亮点

### 5.1 与RATH的对比

| 特性 | RAGFlow | RATH |
|------|---------|------|
| **状态存储** |  完整DSL持久化 |  仅配置，无执行历史 |
| **执行历史** |  每次运行都记录 |  不记录 |
| **断点续传** | ⚠️ 可恢复到最后节点 |  无 |
| **版本管理** |  UserCanvasVersion表 |  无 |
| **运行时数据** |  retrieval/memory存DSL |  仅内存存储 |

### 5.2 设计亮点

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        RAGFlow状态存储亮点                                 │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  【1】DSL即状态 - 单JSON存储所有信息                                        │
│                                                                            │
│  优势：                                                                    │
│  - 原子性：整个工作流是一个JSON文档                                        │
│  - 可移植：导出导入只需复制JSON                                            │
│  - 版本友好：Git diff友好，易于版本控制                                    │
│  - 灵活：可随时添加新字段而不影响旧数据                                    │
│                                                                            │
│  劣势：                                                                    │
│  - DSL过大时查询性能下降（MySQL JSON字段限制）                             │
│  - 无法对DSL内部字段建索引（如按历史记录查询）                             │
│                                                                            │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  【2】分离运行时状态（Redis）+ 持久化状态（MySQL）                          │
│                                                                            │
│  MySQL（持久化）：                                                          │
│  - 工作流定义（components）                                                │
│  - 执行历史（history）                                                     │
│  - 全局配置（globals）                                                     │
│                                                                            │
│  Redis（临时）：                                                            │
│  - 任务取消信号（{task_id}-cancel）                                        │
│  - 执行日志（{task_id}-logs）                                              │
│  - 当前运行状态（执行中节点）                                              │
│                                                                            │
│  设计理由：                                                                 │
│  - Redis数据可丢失，MySQL数据必须持久化                                    │
│  - Redis读写快，适合实时状态同步                                           │
│                                                                            │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  【3】版本控制 - UserCanvasVersion 表                                       │
│                                                                            │
│  每次保存都创建版本：                                                       │
│  - 支持回滚到历史版本                                                      │
│  - 支持对比不同版本                                                        │
│  - 支持发布/草稿状态                                                       │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 六、生产环境注意事项

### 6.1 性能优化建议

```python
# 1. DSL过大时的处理
# 问题：当history积累过多时，DSL会变得很大

# 解决方案：定期归档历史记录
class CanvasArchiveService:
    def archive_old_history(self, canvas_id, keep_days=30):
        """归档旧的历史记录"""
        canvas = UserCanvasService.get_by_id(canvas_id)
        dsl = canvas.dsl
        
        # 保留最近30天的记录
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        recent_history = [
            h for h in dsl["history"] 
            if datetime.fromisoformat(h["timestamp"]) > cutoff_date
        ]
        
        # 归档旧记录到单独的表
        CanvasArchiveService.create({
            "canvas_id": canvas_id,
            "archived_history": [
                h for h in dsl["history"] 
                if datetime.fromisoformat(h["timestamp"]) <= cutoff_date
            ]
        })
        
        # 更新DSL
        dsl["history"] = recent_history
        UserCanvasService.update(canvas_id, dsl=dsl)


# 2. 大DSL查询优化
# 问题：SELECT dsl FROM user_canvas 会加载整个JSON

# 解决方案：添加摘要字段
class UserCanvas(DataBaseModel):
    # ... 原字段 ...
    dsl = JSONField(null=True, default={})
    
    # 冗余字段用于查询（避免解析JSON）
    last_run_at = DateTimeField(null=True, index=True)
    run_count = IntegerField(default=0)
    component_count = IntegerField(default=0)
    
    def update_summary(self):
        """更新摘要信息"""
        self.last_run_at = self.dsl["history"][-1]["timestamp"] if self.dsl["history"] else None
        self.run_count = len(self.dsl["history"])
        self.component_count = len(self.dsl.get("components", {}))
        self.save()
```

### 6.2 数据安全

```python
# DSL中可能包含敏感信息（如API Key）

# 敏感字段加密存储
from cryptography.fernet import Fernet

class SecureCanvasService:
    def __init__(self):
        self.cipher = Fernet(os.environ['DSL_ENCRYPTION_KEY'])
    
    def encrypt_sensitive_fields(self, dsl):
        """加密DSL中的敏感字段"""
        secure_dsl = deepcopy(dsl)
        
        for cpn_id, cpn in secure_dsl.get("components", {}).items():
            params = cpn.get("obj", {}).get("params", {})
            
            # 加密API Key等敏感信息
            if "api_key" in params:
                params["api_key"] = self.cipher.encrypt(
                    params["api_key"].encode()
                ).decode()
        
        return secure_dsl
    
    def decrypt_sensitive_fields(self, secure_dsl):
        """解密敏感字段"""
        dsl = deepcopy(secure_dsl)
        
        for cpn_id, cpn in dsl.get("components", {}).items():
            params = cpn.get("obj", {}).get("params", {})
            
            if "api_key" in params:
                params["api_key"] = self.cipher.decrypt(
                    params["api_key"].encode()
                ).decode()
        
        return dsl
```

---

## 七、总结

### 一句话结论

> **RAGFlow 的工作流状态是全后端持久化的，DSL（JSON）存储了工作流定义、执行历史、运行时数据等完整信息，是一个设计优雅的全状态管理系统。**

### 核心设计

```
┌─────────────────────────────────────────────────────────────┐
│                    DSL = 定义 + 状态                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MySQL user_canvas.dsl (JSONField)                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ {                                                   │   │
│  │   "components": { ... },     ← 工作流定义          │   │
│  │   "history": [ ... ],        ← 执行历史            │   │
│  │   "path": [ ... ],           ← 当前执行路径        │   │
│  │   "globals": { ... },        ← 全局变量            │   │
│  │   "retrieval": { ... },      ← 检索结果            │   │
│  │   "memory": [ ... ]          ← 记忆                │   │
│  │ }                                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Redis（临时状态）                                           │
│  - {task_id}-cancel: 任务取消信号                           │
│  - {task_id}-logs: 实时日志                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 与RATH的本质区别

| 特性 | RAGFlow | RATH |
|------|---------|------|
| **状态持久化** |  完整DSL存储 |  仅服务配置 |
| **执行历史** |  每次运行记录 |  无 |
| **断点恢复** |  支持 |  不支持 |
| **版本管理** |  有版本表 |  无 |
| **适用场景** | 有状态对话/复杂工作流 | 无状态分析任务 |

**RAGFlow 的状态管理更适合对话式AI Agent场景，RATH更适合传统的数据分析任务。**
