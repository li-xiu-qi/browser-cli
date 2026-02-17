# RAGFlow 核心类图分析

> **分析日期**: 2026-02-05  
> **分析范围**: RAGFlow 核心模块类关系与架构设计

---

## 1. 整体类架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          RAGFlow 核心类架构                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Agent 层 (agent/)                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │    Graph     │◄─┤    Canvas    │  │      ComponentBase       │   │   │
│  │  │   (DAG基类)   │  │  (画布引擎)   │  │       (组件基类)          │   │   │
│  │  └──────────────┘  └──────────────┘  └───────────┬──────────────┘   │   │
│  │                                                  │                   │   │
│  │                          ┌───────────────────────┼───────────┐       │   │
│  │                          ▼                       ▼           ▼       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────┐  │   │
│  │  │     LLM      │  │  Retrieval   │  │   Begin      │  │ Message │  │   │
│  │  │  (对话组件)   │  │  (检索组件)   │  │  (开始节点)   │  │(消息组件)│  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └─────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        RAG 层 (rag/)                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │    Dealer    │  │  Fulltext    │  │      Splitter            │   │   │
│  │  │  (检索调度器) │  │   Queryer    │  │     (分块器)              │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  │                                                                              │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │    Prompt    │  │     Base     │  │    EmbeddingModel        │   │   │
│  │  │   Generator  │  │  (Chat模型)   │  │      (嵌入模型)           │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     DeepDoc 层 (deepdoc/)                            │   │
│  │  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │ RAGFlowPdfParser │  │    OCR       │  │ LayoutRecognizer     │   │   │
│  │  │    (PDF解析器)    │  │  (文字识别)   │  │    (版面识别器)       │   │   │
│  │  └──────────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  │                                                                              │
│  │  ┌──────────────────┐  ┌──────────────┐  ┌──────────────────────┐   │   │
│  │  │   DocxParser     │  │  TxtParser   │  │ TableStructure       │   │   │
│  │  │   (DOCX解析器)    │  │  (文本解析)   │  │   Recognizer         │   │   │
│  │  └──────────────────┘  └──────────────┘  └──────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        API 层 (api/)                                 │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │   │
│  │  │DialogService │  │Conversation  │  │   KnowledgebaseService   │   │   │
│  │  │  (对话服务)   │  │   Service    │  │      (知识库服务)         │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent 层核心类

### 2.1 Graph / Canvas 类层次

**文件**: `agent/canvas.py:40-148` (Graph), `281-369` (Canvas)

```python
class Graph:
    """
    DAG 执行引擎基类
    
    职责:
    - 组件管理 (components)
    - 执行路径管理 (path)
    - 变量系统 (globals/variables)
    - 序列化/反序列化 (dsl)
    """
    def __init__(self, dsl: str, tenant_id=None, task_id=None):
        self.components = {}    # 组件字典 {id: {obj, downstream, upstream}}
        self.path = []          # 执行路径
        self.dsl = json.loads(dsl)  # DSL 配置
        self._tenant_id = tenant_id
        self.task_id = task_id
    
    def get_component(self, cpn_id) -> Union[None, dict]:
        """获取组件配置"""
        
    def get_component_obj(self, cpn_id) -> ComponentBase:
        """获取组件对象"""
        
    def get_variable_value(self, exp: str) -> Any:
        """获取变量值 (支持 cpn_id@var_name 语法)"""
        
    def run(self, **kwargs):
        """执行 DAG (子类实现)"""
        raise NotImplementedError()


class Canvas(Graph):
    """
    Agent 画布引擎
    
    在 Graph 基础上增加了:
    - 对话历史管理 (history)
    - 检索结果管理 (retrieval)
    - 记忆管理 (memory)
    - 全局变量 (sys.query, sys.user_id 等)
    """
    def __init__(self, dsl: str, tenant_id=None, task_id=None, canvas_id=None):
        super().__init__(dsl, tenant_id, task_id)
        self._id = canvas_id
        self.globals = {
            "sys.query": "",
            "sys.user_id": tenant_id,
            "sys.conversation_turns": 0,
            "sys.files": [],
            "sys.history": []
        }
        self.history = []      # 对话历史
        self.retrieval = []    # 检索结果
        self.memory = []       # 记忆
    
    async def run(self, **kwargs):
        """异步执行工作流"""
        
    def get_history(self, window_size) -> list:
        """获取最近 N 轮对话历史"""
        
    def add_reference(self, chunks: list, doc_infos: list):
        """添加引用信息"""
```

### 2.2 ComponentBase 组件基类

**文件**: `agent/component/base.py:40-300`

```python
class ComponentParamBase(ABC):
    """组件参数基类"""
    def __init__(self):
        self.message_history_window_size = 13  # 历史窗口大小
        self.inputs = {}    # 输入定义
        self.outputs = {}   # 输出定义
        self.max_retries = 0           # 最大重试次数
        self.delay_after_error = 2.0   # 错误后延迟
        self.exception_method = None   # 异常处理方法
        self.exception_default_value = None  # 异常默认值
        self.exception_goto = None     # 异常跳转目标


class ComponentBase(ABC):
    """
    组件基类
    
    所有 Agent 组件(LLM/Retrieval/Message等)的基类
    """
    component_name = "Base"
    
    def __init__(self, canvas, component_id, param: ComponentParamBase):
        self._canvas = canvas           # 所属画布
        self._id = component_id         # 组件ID
        self._param = param             # 参数配置
        self._outputs = {}              # 输出值
        self._inputs = {}               # 输入值
    
    def invoke(self, **kwargs) -> dict:
        """同步调用组件"""
        
    async def invoke_async(self, **kwargs) -> dict:
        """异步调用组件"""
        
    def output(self, key: str) -> Any:
        """获取输出值"""
        
    def set_output(self, key: str, value: Any):
        """设置输出值"""
        
    def get_input(self) -> dict:
        """获取输入值"""
        
    def get_input_elements(self) -> dict:
        """获取输入元素定义"""
        
    def string_format(self, template: str, variables: dict) -> str:
        """字符串模板格式化 (支持 {var@component} 语法)"""
```

### 2.3 LLM 组件

**文件**: `agent/component/llm.py:33-351`

```python
class LLMParam(ComponentParamBase):
    """LLM 组件参数"""
    def __init__(self):
        super().__init__()
        self.llm_id = ""           # LLM 模型ID
        self.sys_prompt = ""       # 系统提示词
        self.prompts = []          # 用户提示词列表
        self.max_tokens = 0        # 最大生成Token数
        self.temperature = 0       # 温度参数
        self.top_p = 0             # Top-p 采样
        self.cite = True           # 是否启用引用


class LLM(ComponentBase):
    """
    LLM 对话组件
    
    职责:
    - 管理 LLM 调用
    - 处理流式输出
    - 引用标注管理
    - 结构化输出支持
    """
    component_name = "LLM"
    
    def __init__(self, canvas, component_id, param: LLMParam):
        super().__init__(canvas, component_id, param)
        self.chat_mdl = LLMBundle(...)  # 聊天模型封装
        self.imgs = []                  # 图片输入
    
    def _prepare_prompt_variables(self):
        """准备提示词变量"""
        
    def _extract_prompts(self, sys_prompt):
        """提取特殊提示词标签 (TASK_ANALYSIS, PLAN_GENERATION等)"""
        
    async def _generate_async(self, msg: list, **kwargs) -> str:
        """异步生成"""
        
    async def _generate_streamly(self, msg: list, **kwargs) -> AsyncGenerator[str, None]:
        """流式生成"""
        
    async def add_memory(self, user: str, assist: str, func_name: str, 
                        params: dict, results: str):
        """添加记忆"""
```

### 2.4 Retrieval 组件

**文件**: `agent/tools/retrieval.py:36-305`

```python
class RetrievalParam(ToolParamBase):
    """检索组件参数"""
    def __init__(self):
        super().__init__()
        self.similarity_threshold = 0.2     # 相似度阈值
        self.keywords_similarity_weight = 0.5  # 关键词相似度权重
        self.top_n = 8                      # 返回结果数
        self.top_k = 1024                   # 检索候选数
        self.kb_ids = []                    # 知识库ID列表
        self.rerank_id = ""                 # 重排序模型ID
        self.use_kg = False                 # 是否使用知识图谱
        self.toc_enhance = False            # 是否启用目录增强


class Retrieval(ToolBase):
    """
    检索工具组件
    
    职责:
    - 知识库检索
    - 记忆检索
    - 元数据过滤
    - 跨语言处理
    """
    component_name = "Retrieval"
    
    async def _retrieve_kb(self, query_text: str):
        """知识库检索"""
        
    async def _retrieve_memory(self, query_text: str):
        """记忆检索"""
```

---

## 3. RAG 层核心类

### 3.1 Dealer 检索调度器

**文件**: `rag/nlp/search.py:36-702`

```python
class Dealer:
    """
    RAG 检索调度器
    
    职责:
    - 混合检索 (全文 + 向量)
    - 重排序
    - 引用插入
    - SQL 检索
    """
    def __init__(self, dataStore: DocStoreConnection):
        self.qryr = query.FulltextQueryer()  # 全文查询器
        self.dataStore = dataStore           # 文档存储连接
    
    @dataclass
    class SearchResult:
        total: int
        ids: list[str]
        query_vector: list[float] | None
        field: dict | None
        highlight: dict | None
        keywords: list[str] | None
    
    async def search(self, req, idx_names, kb_ids, emb_mdl=None, ...):
        """执行混合检索"""
        
    def rerank(self, sres, query, tkweight=0.3, vtweight=0.7, ...):
        """重排序 (基于混合相似度)"""
        
    def rerank_by_model(self, rerank_mdl, sres, query, ...):
        """使用重排序模型重排序"""
        
    def insert_citations(self, answer, chunks, chunk_v, embd_mdl, ...):
        """在答案中插入引用标记"""
        
    async def retrieval(self, question, embd_mdl, tenant_ids, kb_ids, ...):
        """完整检索流程"""
        
    def retrieval_by_children(self, chunks: list, tenant_ids: list):
        """基于子 Chunk 检索父 Chunk"""
```

### 3.2 FulltextQueryer 全文查询器

**文件**: `rag/nlp/query.py:27-237`

```python
class FulltextQueryer(QueryBase):
    """
    全文查询构建器
    
    职责:
    - 查询解析与分词
    - 同义词扩展
    - 查询权重分配
    - 混合相似度计算
    """
    def __init__(self):
        self.tw = term_weight.Dealer()      # 词权重计算器
        self.syn = synonym.Dealer()         # 同义词处理器
        self.query_fields = [               # 查询字段及权重
            "title_tks^10",
            "title_sm_tks^5",
            "important_kwd^30",
            "content_ltks^2",
        ]
    
    def question(self, txt, tbl="qa", min_match: float = 0.6):
        """
        构建查询表达式
        
        支持中英文不同处理逻辑
        """
        
    def hybrid_similarity(self, avec, bvecs, atks, btkss, 
                         tkweight=0.3, vtweight=0.7):
        """
        计算混合相似度
        
        tkweight: 关键词相似度权重
        vtweight: 向量相似度权重
        """
        
    def token_similarity(self, atks, btkss):
        """计算关键词相似度"""
```

### 3.3 Prompt Generator

**文件**: `rag/prompts/generator.py`

```python
# 核心函数

def message_fit_in(msg, max_length=4000):
    """
    确保消息适合 LLM 上下文窗口
    
    策略:
    1. 保留 system + 最后一条 user
    2. 按比例截断 system 或 user
    """

def kb_prompt(kbinfos, max_tokens, hash_id=False):
    """
    组装知识块 Prompt
    
    按 Token 预算截断检索结果
    格式化引用信息
    """

def citation_prompt(user_defined_prompts: dict = {}) -> str:
    """生成引用提示词"""

def chunks_format(reference) -> list:
    """格式化 Chunk 引用"""
```

### 3.4 Splitter 分块器

**文件**: `rag/flow/splitter/splitter.py`

```python
class SplitterParam(ProcessParamBase):
    """分块器参数"""
    chunk_token_size = 512      # Chunk Token 大小
    delimiters = ["\n"]         # 分隔符
    overlapped_percent = 0      # 重叠百分比
    children_delimiters = []    # 子分隔符
    table_context_size = 0      # 表格上下文大小
    image_context_size = 0      # 图片上下文大小


class Splitter(ProcessBase):
    """
    文档分块组件
    
    职责:
    - 文本分割与合并
    - 重叠处理
    - 媒体上下文附加
    """
    async def _invoke(self, **kwargs):
        # 1. 解析输入格式
        # 2. 执行 naive_merge
        # 3. 处理子分隔符
        # 4. 附加媒体上下文
```

---

## 4. DeepDoc 层核心类

### 4.1 RAGFlowPdfParser

**文件**: `deepdoc/parser/pdf_parser.py:55-300`

```python
class RAGFlowPdfParser:
    """
    PDF 深度解析器
    
    职责:
    - OCR 文字识别
    - 版面分析
    - 表格结构识别
    - 阅读顺序恢复
    """
    def __init__(self, **kwargs):
        self.ocr = OCR()                              # OCR 引擎
        self.layouter = LayoutRecognizer(...)        # 版面识别器
        self.tbl_det = TableStructureRecognizer()     # 表格识别器
        self.updown_cnt_mdl = xgb.Booster()           # 文本合并模型
    
    def __call__(self, filename, binary=None, from_page=0, to_page=100000):
        """解析 PDF"""
        # 1. OCR 识别
        # 2. 版面分析
        # 3. 表格识别
        # 4. 文本合并
        
    def _table_transformer_job(self, ZM, auto_rotate=True):
        """表格结构识别"""
        
    def _text_merge(self, zoomin=3):
        """文本段落合并"""
```

### 4.2 LayoutRecognizer

**文件**: `deepdoc/vision/layout_recognizer.py`

```python
class LayoutRecognizer(Recognizer):
    """
    版面识别器
    
    识别文档元素类型:
    - 文本 (text)
    - 标题 (title)
    - 表格 (table)
    - 图片 (figure)
    - 页眉/页脚 (header/footer)
    """
    def __call__(self, image_list, ...):
        """识别版面布局"""
```

---

## 5. API 层核心类

### 5.1 DialogService

**文件**: `api/db/services/dialog_service.py:50-1000`

```python
class DialogService(CommonService):
    """
    对话服务
    
    职责:
    - 对话管理
    - RAG 流程编排
    - 模型调用协调
    """
    model = Dialog
    
    @classmethod
    def save(cls, **kwargs):
        """保存对话配置"""
        
    @classmethod
    def get_list(cls, tenant_id, page_number, items_per_page, ...):
        """获取对话列表"""


async def async_chat(dialog, messages, stream=True, **kwargs):
    """
    异步对话核心流程
    
    流程:
    1. 获取模型配置
    2. 查询优化
    3. 元数据过滤
    4. 混合检索
    5. 目录增强
    6. 子 Chunk 检索
    7. Prompt 组装
    8. LLM 生成
    9. 引用插入
    """


async def async_chat_solo(dialog, messages, stream=True):
    """无知识库的对话 (纯 LLM)"""
```

### 5.2 ConversationService

**文件**: `api/db/services/conversation_service.py`

```python
class ConversationService(CommonService):
    """
    会话服务
    
    职责:
    - 会话管理
    - 消息历史维护
    - 引用信息维护
    """
    model = Conversation
    
    @classmethod
    def structure_answer(cls, conv, answer, message_id, conv_id):
        """结构化答案 (包含引用信息)"""
```

---

## 6. 类关系图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            核心类继承关系                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                    ComponentParamBase (抽象参数基类)                          │
│                           △                                                  │
│           ┌───────────────┼───────────────┐                                  │
│           │               │               │                                  │
│           ▼               ▼               ▼                                  │
│    LLMParam      RetrievalParam    ProcessParamBase                          │
│                                                    △                         │
│                                                    │                         │
│                                               SplitterParam                  │
│                                                                              │
│                                                                              │
│                    ComponentBase (抽象组件基类)                               │
│                           △                                                  │
│           ┌───────────────┼───────────────┬───────────────┐                  │
│           │               │               │               │                  │
│           ▼               ▼               ▼               ▼                  │
│          LLM          Retrieval       ProcessBase       ToolBase              │
│                                           △               △                  │
│                                           │               │                  │
│                                       Splitter      Retrieval                │
│                                                                              │
│                                                                              │
│                    Graph (DAG基类)                                           │
│                           △                                                  │
│                           │                                                  │
│                       Canvas (Agent画布)                                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. 关键设计模式

### 7.1 模板方法模式

```python
# ProcessBase 定义算法骨架
class ProcessBase(ComponentBase):
    async def invoke(self, **kwargs):
        self.set_output("_created_time", time.perf_counter())
        try:
            await asyncio.wait_for(
                self._invoke(**kwargs),
                timeout=self._param.timeout
            )
        except Exception as e:
            self.set_output("_ERROR", str(e))
        self.set_output("_elapsed_time", ...)
    
    async def _invoke(self, **kwargs):
        """子类实现具体逻辑"""
        raise NotImplementedError()
```

### 7.2 策略模式

```python
# Dealer.rerank 支持多种重排序策略
class Dealer:
    def rerank(self, sres, query, ...):
        """基于规则的重排序"""
        
    def rerank_by_model(self, rerank_mdl, sres, query, ...):
        """基于模型的重排序"""
```

### 7.3 观察者模式

```python
# Canvas 的事件流机制
class Canvas(Graph):
    async def run(self, **kwargs):
        # 触发节点开始事件
        yield decorate("node_started", {...})
        
        # 执行组件
        await _run_batch(...)
        
        # 触发节点结束事件
        yield _node_finished(cpn_obj)
        
        # 触发工作流结束
        yield decorate("workflow_finished", {...})
```

---

## 8. 总结

RAGFlow 的类架构设计体现了以下原则：

1. **单一职责**: 每个类专注于一个核心功能 (检索、分块、生成等)
2. **开闭原则**: 通过 ComponentBase 扩展新组件
3. **依赖倒置**: 高层模块依赖抽象 (ComponentBase)，不依赖具体实现
4. **组合优于继承**: Canvas 组合多个 Component 完成复杂流程

关键架构亮点：
- **Canvas/Graph**: 灵活的工作流编排引擎
- **Dealer**: 统一的检索调度器
- **Component体系**: 可扩展的组件化设计
- **DeepDoc**: 深度文档理解的强大能力
