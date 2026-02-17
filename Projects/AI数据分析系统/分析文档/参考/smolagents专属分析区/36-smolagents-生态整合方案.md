# smolagents 生态整合方案

> 项目: AI数据分析系统  
> 分析日期: 2026-02-06  
> 文档版本: 1.0  
> 关联文档: [[19-smolagents-MCP与扩展机制]]

---

## 文档概述

本文档描述 smolagents 与主流 AI 框架及基础设施的整合方案，包括 LangChain、LlamaIndex、FastAPI、数据库、消息队列等生态系统的集成方法。通过标准化接口和适配层设计，实现工具互用、数据共享和服务封装。

---

## 一、整合架构总览

### 1.1 生态整合全景图

![生态整合架构图](graphviz/ecosystem-integration.svg)

### 1.2 整合层次说明

整合方案分为三个层次：

| 层次 | 组件 | 整合目标 |
|------|------|----------|
| 框架整合层 | LangChain、LlamaIndex、FastAPI | 工具互用、RAG增强、服务封装 |
| 基础设施层 | 数据库、消息队列、缓存 | 状态持久化、异步执行、性能优化 |
| 外部生态层 | MCP、HF Hub、第三方API | 标准化协议、工具市场、模型接入 |

---

## 二、与LangChain整合

### 2.1 工具互用机制

smolagents 与 LangChain 的工具可以双向转换，实现生态互通。

#### 2.1.1 smolagents Tool转为LangChain Tool

smolagents Tool 可通过适配器转换为 LangChain 的 BaseTool：

```python
from smolagents import Tool
from langchain.tools import BaseTool as LangChainBaseTool
from langchain.pydantic_v1 import BaseModel, Field
from typing import Type


class SmolAgentsToolAdapter(LangChainBaseTool):
    """将smolagents Tool适配为LangChain Tool"""
    
    def __init__(self, smol_tool: Tool):
        self.smol_tool = smol_tool
        self.name = smol_tool.name
        self.description = smol_tool.description
        
        # 构建输入schema
        self.args_schema = self._build_args_schema()
    
    def _build_args_schema(self) -> Type[BaseModel]:
        """将smolagents inputs转为LangChain args_schema"""
        fields = {}
        for param_name, param_info in self.smol_tool.inputs.items():
            param_type = self._map_type(param_info.get("type", "string"))
            description = param_info.get("description", "")
            nullable = param_info.get("nullable", False)
            
            if nullable:
                param_type = Type[param_type, None]
            
            fields[param_name] = (param_type, Field(description=description))
        
        return type(f"{self.name}Schema", (BaseModel,), fields)
    
    def _map_type(self, smol_type: str) -> type:
        """类型映射"""
        type_map = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        return type_map.get(smol_type, str)
    
    def _run(self, **kwargs) -> str:
        """执行工具调用"""
        return self.smol_tool.forward(**kwargs)
    
    async def _arun(self, **kwargs) -> str:
        """异步执行"""
        return self._run(**kwargs)


# 使用示例
from smolagents import tool

@tool
def analyze_data(query: str, dataset: str) -> str:
    """
    分析数据集并返回结果。
    
    Args:
        query: 分析查询语句
        dataset: 数据集名称
    
    Returns:
        分析结果
    """
    return f"分析 {dataset}: {query}"

# 转换为LangChain Tool
langchain_tool = SmolAgentsToolAdapter(analyze_data)
```

#### 2.1.2 LangChain Tool转为smolagents Tool

smolagents 内置了从 LangChain 工具转换的方法：

```python
from smolagents import Tool
from langchain.tools import WikipediaQueryRun
from langchain.utilities import WikipediaAPIWrapper

# 创建LangChain工具
wikipedia_tool = WikipediaQueryRun(
    api_wrapper=WikipediaAPIWrapper()
)

# 转换为smolagents Tool
smol_tool = Tool.from_langchain(wikipedia_tool)

# 在Agent中使用
from smolagents import CodeAgent, InferenceClientModel

model = InferenceClientModel()
agent = CodeAgent(
    tools=[smol_tool],
    model=model
)

result = agent.run("查询Python编程语言的相关信息")
```

**转换原理**：

```python
class LangChainToolWrapper(Tool):
    """LangChain工具包装器"""
    
    def __init__(self, langchain_tool):
        self.name = langchain_tool.name.lower().replace("-", "_")
        self.description = langchain_tool.description
        self.inputs = self._convert_inputs(langchain_tool.args)
        self.output_type = "string"
        self.langchain_tool = langchain_tool
    
    def forward(self, **kwargs):
        return self.langchain_tool.run(kwargs)
```

### 2.2 Chain集成

#### 2.2.1 smolagents Agent作为Chain节点

将 smolagents Agent 封装为 LangChain 的 Runnable 组件：

```python
from langchain_core.runnables import Runnable
from langchain_core.pydantic_v1 import BaseModel
from typing import Any, Optional
from smolagents import MultiStepAgent


class SmolAgentsChainNode(Runnable):
    """将smolagents Agent包装为LangChain Chain节点"""
    
    def __init__(self, agent: MultiStepAgent, output_key: str = "result"):
        self.agent = agent
        self.output_key = output_key
    
    def invoke(self, input_data: dict, config: Optional[dict] = None) -> dict:
        """同步调用"""
        query = input_data.get("query", "")
        
        # 执行Agent
        result = self.agent.run(query)
        
        # 返回标准化格式
        return {
            self.output_key: result,
            "intermediate_steps": self.agent.logs if hasattr(self.agent, "logs") else []
        }
    
    async def ainvoke(self, input_data: dict, config: Optional[dict] = None) -> dict:
        """异步调用"""
        # 使用asyncio在后台线程运行
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.invoke, input_data, config)


# 构建完整Chain
from langchain import hub
from langchain.chains import LLMChain
from langchain_openai import ChatOpenAI

# 创建smolagents Agent
from smolagents import CodeAgent, InferenceClientModel

smol_agent = CodeAgent(
    tools=[],
    model=InferenceClientModel()
)

# 包装为Chain节点
agent_node = SmolAgentsChainNode(smol_agent)

# 与LangChain组件组合
llm = ChatOpenAI()
prompt = hub.pull("langchain/initial-analysis")
analysis_chain = LLMChain(llm=llm, prompt=prompt)

# 组合Chain：先分析，再让Agent执行
combined_chain = analysis_chain | agent_node

# 执行
result = combined_chain.invoke({"query": "分析销售数据趋势"})
```

#### 2.2.2 复杂工作流组合

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class AgentState(TypedDict):
    query: str
    analysis: str
    agent_result: str
    final_output: str

# 创建状态图
workflow = StateGraph(AgentState)

# 添加节点
workflow.add_node("analyzer", analysis_node)
workflow.add_node("smol_agent", agent_node)
workflow.add_node("formatter", formatter_node)

# 定义边
workflow.set_entry_point("analyzer")
workflow.add_edge("analyzer", "smol_agent")
workflow.add_edge("smol_agent", "formatter")
workflow.add_edge("formatter", END)

# 编译执行
app = workflow.compile()
result = app.invoke({"query": "复杂数据分析任务"})
```

### 2.3 Memory共享

#### 2.3.1 统一Memory接口

实现 smolagents 与 LangChain 的 Memory 系统互通：

```python
from langchain.memory import ConversationBufferMemory
from smolagents.memory import AgentMemory
from typing import List, Dict, Any


class UnifiedMemory:
    """统一内存管理器，桥接smolagents和LangChain"""
    
    def __init__(self, langchain_memory: ConversationBufferMemory = None):
        self.langchain_memory = langchain_memory or ConversationBufferMemory()
        self.smol_memory = AgentMemory()
    
    def add_user_message(self, message: str):
        """添加用户消息到双端内存"""
        # LangChain端
        self.langchain_memory.chat_memory.add_user_message(message)
        
        # smolagents端
        self.smol_memory.add_user_message(message)
    
    def add_assistant_message(self, message: str):
        """添加助手消息到双端内存"""
        self.langchain_memory.chat_memory.add_ai_message(message)
        self.smol_memory.add_assistant_message(message)
    
    def get_langchain_history(self) -> List[Dict[str, Any]]:
        """获取LangChain格式的对话历史"""
        return self.langchain_memory.load_memory_variables({})
    
    def get_smolagents_history(self) -> List[Dict[str, Any]]:
        """获取smolagents格式的对话历史"""
        return self.smol_memory.messages
    
    def clear(self):
        """清空内存"""
        self.langchain_memory.clear()
        self.smol_memory.clear()


# 使用示例
memory = UnifiedMemory()

# 在LangChain Chain中使用
from langchain.chains import ConversationChain

conversation = ConversationChain(
    llm=ChatOpenAI(),
    memory=memory.langchain_memory
)

# 在smolagents Agent中使用
from smolagents import MultiStepAgent

agent = MultiStepAgent(
    tools=[],
    model=InferenceClientModel(),
    memory=memory.smol_memory
)
```

---

## 三、与LlamaIndex整合

### 3.1 RAG场景整合

#### 3.1.1 smolagents作为查询引擎

将 smolagents Agent 封装为 LlamaIndex 的查询引擎：

```python
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.response.schema import Response
from llama_index.core.base.base_query_engine import BaseQueryEngine
from smolagents import CodeAgent, Tool


class SmolAgentsQueryEngine(BaseQueryEngine):
    """基于smolagents的LlamaIndex查询引擎"""
    
    def __init__(self, agent: CodeAgent, **kwargs):
        self.agent = agent
        super().__init__(**kwargs)
    
    def _query(self, query_str: str) -> Response:
        """执行查询"""
        result = self.agent.run(query_str)
        
        return Response(
            response=result,
            source_nodes=[],  # 可添加源节点信息
            metadata={
                "agent_logs": self.agent.logs if hasattr(self.agent, "logs") else []
            }
        )
    
    async def _aquery(self, query_str: str) -> Response:
        """异步查询"""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._query, query_str)


# 使用示例
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

# 加载文档
documents = SimpleDirectoryReader("data/").load_data()
index = VectorStoreIndex.from_documents(documents)

# 创建retriever
retriever = index.as_retriever(similarity_top_k=5)

# 创建检索工具
@Tool
def retrieve_documents(query: str) -> str:
    """
    从知识库检索相关文档。
    
    Args:
        query: 检索查询
    
    Returns:
        检索结果文本
    """
    nodes = retriever.retrieve(query)
    return "\n\n".join([node.text for node in nodes])

# 创建Agent
agent = CodeAgent(
    tools=[retrieve_documents],
    model=InferenceClientModel()
)

# 包装为查询引擎
query_engine = SmolAgentsQueryEngine(agent)

# 执行查询
response = query_engine.query("解释什么是神经网络")
print(response.response)
```

#### 3.1.2 LlamaIndex索引作为Tool

将 LlamaIndex 索引直接作为 smolagents 的工具使用：

```python
from smolagents import Tool
from llama_index.core import VectorStoreIndex
from llama_index.core.tools import QueryEngineTool


class LlamaIndexTool(Tool):
    """LlamaIndex索引工具包装器"""
    name = "llama_index_retriever"
    description = "从向量索引中检索相关信息"
    inputs = {
        "query": {
            "type": "string",
            "description": "检索查询语句"
        },
        "top_k": {
            "type": "integer",
            "description": "返回结果数量",
            "nullable": True
        }
    }
    output_type = "string"
    
    def __init__(self, index: VectorStoreIndex, **kwargs):
        super().__init__()
        self.index = index
        self.query_engine = index.as_query_engine()
    
    def forward(self, query: str, top_k: int = 5) -> str:
        """执行检索"""
        # 更新top_k
        self.query_engine = self.index.as_query_engine(
            similarity_top_k=top_k
        )
        
        response = self.query_engine.query(query)
        return str(response)


# 使用示例
from llama_index.core import StorageContext, load_index_from_storage

# 加载已有索引
storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = load_index_from_storage(storage_context)

# 创建工具
llama_tool = LlamaIndexTool(index)

# 在Agent中使用
from smolagents import CodeAgent

agent = CodeAgent(
    tools=[llama_tool],
    model=InferenceClientModel()
)

result = agent.run("基于知识库解释机器学习基础概念")
```

### 3.2 索引共享

#### 3.2.1 向量存储共享

实现 smolagents 与 LlamaIndex 共享同一个向量存储：

```python
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext, VectorStoreIndex
import chromadb
from smolagents import Tool


class SharedVectorStore:
    """共享向量存储管理器"""
    
    def __init__(self, collection_name: str = "shared_collection"):
        # 初始化ChromaDB
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name
        )
        
        # LlamaIndex向量存储
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )
    
    def get_llama_index(self, documents=None) -> VectorStoreIndex:
        """获取或创建LlamaIndex索引"""
        if documents:
            return VectorStoreIndex.from_documents(
                documents,
                storage_context=self.storage_context
            )
        return VectorStoreIndex.from_vector_store(
            self.vector_store,
            storage_context=self.storage_context
        )
    
    def get_smolagents_retriever(self) -> Tool:
        """获取smolagents检索工具"""
        
        class SharedRetrieverTool(Tool):
            name = "shared_retriever"
            description = "从共享向量存储检索文档"
            inputs = {
                "query": {"type": "string", "description": "查询语句"},
                "n_results": {
                    "type": "integer",
                    "description": "结果数量",
                    "nullable": True
                }
            }
            output_type = "string"
            
            def forward(self, query: str, n_results: int = 5) -> str:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results
                )
                
                documents = results["documents"][0]
                metadatas = results["metadatas"][0]
                
                output = []
                for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                    output.append(f"[{i+1}] {doc[:200]}...")
                    if meta:
                        output.append(f"    来源: {meta.get('source', 'unknown')}")
                
                return "\n\n".join(output)
        
        return SharedRetrieverTool()


# 使用示例
shared_store = SharedVectorStore()

# 添加文档到共享存储
from llama_index.core import SimpleDirectoryReader

docs = SimpleDirectoryReader("documents/").load_data()
index = shared_store.get_llama_index(docs)

# smolagents使用共享存储
retriever_tool = shared_store.get_smolagents_retriever()
agent = CodeAgent(tools=[retriever_tool], model=InferenceClientModel())

# LlamaIndex使用共享存储
query_engine = index.as_query_engine()
```

### 3.3 检索增强

#### 3.3.1 混合检索策略

结合多种检索方法提升效果：

```python
from llama_index.core.retrievers import VectorIndexRetriever, KeywordTableSimpleRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.tools import RetrieverTool
from smolagents import Tool


class HybridRetrieverTool(Tool):
    """混合检索工具，结合向量检索和关键词检索"""
    name = "hybrid_retriever"
    description = "使用混合策略检索信息，结合语义相似度和关键词匹配"
    inputs = {
        "query": {"type": "string", "description": "查询语句"},
        "use_vector": {
            "type": "boolean",
            "description": "是否使用向量检索",
            "nullable": True
        },
        "use_keyword": {
            "type": "boolean",
            "description": "是否使用关键词检索",
            "nullable": True
        }
    }
    output_type = "string"
    
    def __init__(self, index, **kwargs):
        super().__init__()
        self.index = index
        self.vector_retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=5
        )
        # 关键词检索器
        self.keyword_retriever = None  # 根据实际索引类型初始化
    
    def forward(self, query: str, use_vector: bool = True, 
                use_keyword: bool = True) -> str:
        results = []
        
        # 向量检索
        if use_vector:
            vector_nodes = self.vector_retriever.retrieve(query)
            results.extend([(node, "vector") for node in vector_nodes])
        
        # 关键词检索
        if use_keyword and self.keyword_retriever:
            keyword_nodes = self.keyword_retriever.retrieve(query)
            results.extend([(node, "keyword") for node in keyword_nodes])
        
        # 去重和排序
        seen = set()
        unique_results = []
        for node, method in results:
            if node.id_ not in seen:
                seen.add(node.id_)
                unique_results.append((node, method))
        
        # 格式化输出
        output_lines = []
        for i, (node, method) in enumerate(unique_results[:10]):
            output_lines.append(f"[{i+1}] [方法:{method}] 相似度:{node.score:.3f}")
            output_lines.append(f"    {node.text[:300]}...")
        
        return "\n".join(output_lines)


# 在Agent中使用混合检索
from smolagents import CodeAgent

hybrid_tool = HybridRetrieverTool(index)
agent = CodeAgent(
    tools=[hybrid_tool],
    model=InferenceClientModel()
)

# Agent会自动选择检索策略
result = agent.run("查找关于深度学习的最新研究")
```

---

## 四、与FastAPI整合

### 4.1 API服务封装

#### 4.1.1 RESTful API设计

```python
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid
from datetime import datetime

from smolagents import CodeAgent, Tool, InferenceClientModel

app = FastAPI(
    title="smolagents API服务",
    description="基于smolagents的智能Agent服务",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class AgentRequest(BaseModel):
    query: str = Field(..., description="用户查询", min_length=1, max_length=4000)
    session_id: Optional[str] = Field(None, description="会话ID，用于保持上下文")
    tools: Optional[List[str]] = Field(None, description="指定使用的工具列表")
    max_steps: Optional[int] = Field(10, description="最大执行步数", ge=1, le=50)
    stream: Optional[bool] = Field(False, description="是否流式返回")
    metadata: Optional[Dict[str, Any]] = Field(None, description="额外元数据")

class AgentResponse(BaseModel):
    request_id: str
    session_id: str
    result: str
    execution_time: float
    steps_taken: int
    tools_used: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# 全局Agent实例池
class AgentPool:
    """Agent实例管理池"""
    
    def __init__(self):
        self.agents: Dict[str, CodeAgent] = {}
        self.sessions: Dict[str, Dict] = {}
        self.tasks: Dict[str, TaskResponse] = {}
        self.model = InferenceClientModel()
        
        # 注册基础工具
        self.tools = self._load_tools()
    
    def _load_tools(self) -> Dict[str, Tool]:
        """加载可用工具"""
        from smolagents import DuckDuckGoSearchTool
        
        return {
            "search": DuckDuckGoSearchTool(),
            # 添加更多工具
        }
    
    def get_or_create_agent(self, session_id: str, tool_names: List[str] = None) -> CodeAgent:
        """获取或创建Agent实例"""
        if session_id not in self.agents:
            tools = []
            if tool_names:
                tools = [self.tools[name] for name in tool_names if name in self.tools]
            
            self.agents[session_id] = CodeAgent(
                tools=tools,
                model=self.model,
                max_steps=10
            )
            self.sessions[session_id] = {
                "created_at": datetime.now(),
                "message_count": 0
            }
        
        return self.agents[session_id]
    
    def get_task(self, task_id: str) -> Optional[TaskResponse]:
        return self.tasks.get(task_id)
    
    def create_task(self) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = TaskResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )
        return task_id
    
    def update_task(self, task_id: str, **kwargs):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            for key, value in kwargs.items():
                setattr(task, key, value)


# 全局实例
agent_pool = AgentPool()


# API端点
@app.post("/agent/run", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """同步执行Agent任务"""
    import time
    
    request_id = str(uuid.uuid4())
    session_id = request.session_id or str(uuid.uuid4())
    start_time = time.time()
    
    try:
        # 获取Agent
        agent = agent_pool.get_or_create_agent(
            session_id,
            request.tools
        )
        
        # 更新最大步数
        if request.max_steps:
            agent.max_steps = request.max_steps
        
        # 执行任务
        result = agent.run(request.query)
        
        # 收集执行信息
        steps_taken = len(agent.logs) if hasattr(agent, "logs") else 0
        tools_used = list(set([
            log.tool_calls[0].name 
            for log in agent.logs 
            if hasattr(log, "tool_calls") and log.tool_calls
        ])) if hasattr(agent, "logs") else []
        
        execution_time = time.time() - start_time
        
        # 更新会话
        agent_pool.sessions[session_id]["message_count"] += 1
        
        return AgentResponse(
            request_id=request_id,
            session_id=session_id,
            result=result,
            execution_time=execution_time,
            steps_taken=steps_taken,
            tools_used=tools_used,
            timestamp=datetime.now(),
            metadata=request.metadata or {}
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agent/run/async", response_model=TaskResponse)
async def run_agent_async(
    request: AgentRequest,
    background_tasks: BackgroundTasks
):
    """异步执行Agent任务"""
    task_id = agent_pool.create_task()
    
    # 添加到后台任务
    background_tasks.add_task(
        _execute_agent_task,
        task_id,
        request
    )
    
    return agent_pool.get_task(task_id)


async def _execute_agent_task(task_id: str, request: AgentRequest):
    """后台执行任务"""
    agent_pool.update_task(task_id, status=TaskStatus.RUNNING)
    
    try:
        session_id = request.session_id or str(uuid.uuid4())
        agent = agent_pool.get_or_create_agent(session_id, request.tools)
        
        result = agent.run(request.query)
        
        agent_pool.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            result=result,
            completed_at=datetime.now()
        )
    except Exception as e:
        agent_pool.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=str(e),
            completed_at=datetime.now()
        )


@app.get("/agent/task/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str):
    """查询任务状态"""
    task = agent_pool.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@app.get("/agent/sessions/{session_id}")
async def get_session_info(session_id: str):
    """获取会话信息"""
    if session_id not in agent_pool.sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    return agent_pool.sessions[session_id]


@app.delete("/agent/sessions/{session_id}")
async def clear_session(session_id: str):
    """清理会话"""
    if session_id in agent_pool.agents:
        del agent_pool.agents[session_id]
    if session_id in agent_pool.sessions:
        del agent_pool.sessions[session_id]
    return {"message": "会话已清理"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "active_sessions": len(agent_pool.sessions),
        "active_tasks": len(agent_pool.tasks)
    }


# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 4.1.2 请求响应模型完整示例

```python
from fastapi import FastAPI
from pydantic import BaseModel, validator
from typing import Literal, Union
import json


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str
    parameters: Dict[str, Any]
    
    @validator("parameters")
    def validate_params(cls, v, values):
        # 参数验证逻辑
        return v


class StreamingChunk(BaseModel):
    """流式响应块"""
    chunk_type: Literal["thought", "tool_call", "tool_result", "final_answer"]
    content: str
    timestamp: datetime
    step_number: Optional[int] = None


class AgentError(BaseModel):
    """错误响应"""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    suggestion: Optional[str] = None


# 客户端调用示例
"""
import requests

# 同步调用
response = requests.post(
    "http://localhost:8000/agent/run",
    json={
        "query": "分析2024年销售数据趋势",
        "tools": ["data_analysis", "chart_generation"],
        "max_steps": 15
    }
)
result = response.json()

# 异步调用
response = requests.post(
    "http://localhost:8000/agent/run/async",
    json={"query": "复杂任务"}
)
task_id = response.json()["task_id"]

# 轮询任务状态
import time
while True:
    status = requests.get(f"http://localhost:8000/agent/task/{task_id}").json()
    if status["status"] in ["completed", "failed"]:
        break
    time.sleep(1)
"""
```

### 4.2 异步支持

#### 4.2.1 async/await集成

```python
import asyncio
from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager
from typing import AsyncGenerator

app = FastAPI()


class AsyncAgentRunner:
    """异步Agent执行器"""
    
    def __init__(self):
        self.semaphore = asyncio.Semaphore(5)  # 并发限制
    
    async def run_with_streaming(
        self, 
        agent: CodeAgent, 
        query: str
    ) -> AsyncGenerator[str, None]:
        """流式执行Agent"""
        async with self.semaphore:
            # 在后台线程运行同步Agent
            loop = asyncio.get_event_loop()
            
            # 使用生成器模式模拟流式输出
            step_queue = asyncio.Queue()
            
            def run_agent():
                try:
                    # 重写agent的step回调来发送中间结果
                    original_step = agent.step
                    
                    def step_with_callback(*args, **kwargs):
                        result = original_step(*args, **kwargs)
                        asyncio.run_coroutine_threadsafe(
                            step_queue.put({
                                "type": "step",
                                "content": result
                            }),
                            loop
                        )
                        return result
                    
                    agent.step = step_with_callback
                    result = agent.run(query)
                    
                    asyncio.run_coroutine_threadsafe(
                        step_queue.put({
                            "type": "final",
                            "content": result
                        }),
                        loop
                    )
                except Exception as e:
                    asyncio.run_coroutine_threadsafe(
                        step_queue.put({
                            "type": "error",
                            "content": str(e)
                        }),
                        loop
                    )
            
            # 启动执行线程
            import threading
            thread = threading.Thread(target=run_agent)
            thread.start()
            
            # 流式返回结果
            while True:
                try:
                    item = await asyncio.wait_for(step_queue.get(), timeout=30.0)
                    yield json.dumps(item)
                    
                    if item["type"] in ["final", "error"]:
                        break
                except asyncio.TimeoutError:
                    yield json.dumps({"type": "error", "content": "执行超时"})
                    break
            
            thread.join()


runner = AsyncAgentRunner()


@app.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket):
    """WebSocket实时交互"""
    await websocket.accept()
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()
            query = data.get("query", "")
            session_id = data.get("session_id")
            
            # 创建Agent
            agent = agent_pool.get_or_create_agent(session_id or str(uuid.uuid4()))
            
            # 流式发送结果
            async for chunk in runner.run_with_streaming(agent, query):
                await websocket.send_text(chunk)
    
    except Exception as e:
        await websocket.send_json({"type": "error", "content": str(e)})
    finally:
        await websocket.close()
```

#### 4.2.2 后台任务队列

```python
from fastapi import BackgroundTasks
from celery import Celery
import redis

# Redis连接
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Celery配置
celery_app = Celery(
    "smolagents_tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)


@celery_app.task(bind=True)
def execute_agent_task(self, query: str, tools: List[str], session_id: str):
    """Celery任务：执行Agent"""
    # 更新任务状态
    self.update_state(
        state='PROGRESS',
        meta={'current': 0, 'total': 100, 'status': '初始化Agent'}
    )
    
    try:
        agent = agent_pool.get_or_create_agent(session_id, tools)
        
        self.update_state(
            state='PROGRESS',
            meta={'current': 30, 'total': 100, 'status': '执行中'}
        )
        
        result = agent.run(query)
        
        self.update_state(
            state='SUCCESS',
            meta={'current': 100, 'total': 100, 'result': result}
        )
        
        return {
            'result': result,
            'steps': len(agent.logs) if hasattr(agent, 'logs') else 0
        }
    
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise


@app.post("/agent/task/celery")
async def create_celery_task(request: AgentRequest):
    """创建Celery异步任务"""
    task = execute_agent_task.delay(
        query=request.query,
        tools=request.tools or [],
        session_id=request.session_id or str(uuid.uuid4())
    )
    
    return {
        "task_id": task.id,
        "status": "submitted",
        "check_url": f"/agent/task/celery/{task.id}"
    }


@app.get("/agent/task/celery/{task_id}")
async def get_celery_task_status(task_id: str):
    """查询Celery任务状态"""
    task_result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": task_result.status,
        "result": task_result.result if task_result.ready() else None,
        "info": task_result.info if not task_result.ready() else None
    }
```

### 4.3 依赖注入

#### 4.3.1 FastAPI DI集成

```python
from fastapi import Depends, Request
from functools import lru_cache
from typing import Annotated


class AgentConfig:
    """Agent配置"""
    def __init__(self):
        self.model_name = "Qwen/Qwen2.5-Coder-32B-Instruct"
        self.max_steps = 10
        self.timeout = 60


class DatabaseConnection:
    """数据库连接"""
    def __init__(self):
        self.connection_string = "postgresql://user:pass@localhost/db"
    
    def get_session(self):
        # 返回数据库会话
        pass


# 依赖提供者
@lru_cache()
def get_agent_config() -> AgentConfig:
    return AgentConfig()


@lru_cache()
def get_database() -> DatabaseConnection:
    return DatabaseConnection()


def get_current_session(request: Request) -> str:
    """从请求头获取会话ID"""
    return request.headers.get("X-Session-ID", str(uuid.uuid4()))


def get_agent_with_deps(
    config: Annotated[AgentConfig, Depends(get_agent_config)],
    session_id: Annotated[str, Depends(get_current_session)],
    db: Annotated[DatabaseConnection, Depends(get_database)]
) -> CodeAgent:
    """依赖注入创建Agent"""
    
    # 从数据库加载会话状态
    session_data = db.get_session().get(session_id, {})
    
    # 创建Agent
    agent = CodeAgent(
        tools=[],
        model=InferenceClientModel(config.model_name),
        max_steps=config.max_steps
    )
    
    # 恢复会话状态
    if "memory" in session_data:
        agent.memory = session_data["memory"]
    
    return agent


# 使用依赖注入的端点
@app.post("/agent/run/v2")
async def run_agent_v2(
    request: AgentRequest,
    agent: Annotated[CodeAgent, Depends(get_agent_with_deps)],
    db: Annotated[DatabaseConnection, Depends(get_database)]
):
    """使用依赖注入的Agent端点"""
    result = agent.run(request.query)
    
    # 保存会话状态
    db.get_session().save(agent.memory)
    
    return {"result": result}


# 自定义依赖：权限验证
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()


def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> dict:
    """验证访问令牌"""
    token = credentials.credentials
    # 验证逻辑
    if token != "expected_token":
        raise HTTPException(status_code=401, detail="无效的令牌")
    return {"user_id": "user123", "permissions": ["agent:run"]}


@app.post("/agent/secure-run")
async def secure_run(
    request: AgentRequest,
    user: Annotated[dict, Depends(verify_token)],
    agent: Annotated[CodeAgent, Depends(get_agent_with_deps)]
):
    """需要认证的Agent端点"""
    if "agent:run" not in user["permissions"]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    result = agent.run(request.query)
    return {"result": result, "user": user["user_id"]}
```

---

## 五、与数据库整合

### 5.1 对话历史存储

#### 5.1.1 SQL数据库存储

```python
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

Base = declarative_base()


class ConversationModel(Base):
    """对话记录模型"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), index=True, nullable=False)
    user_message = Column(Text, nullable=False)
    assistant_message = Column(Text)
    tool_calls = Column(JSON)
    step_logs = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    execution_time = Column(Integer)  # 毫秒
    status = Column(String(20), default="success")  # success, error
    error_message = Column(Text)


class SessionModel(Base):
    """会话模型"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), index=True)
    title = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0)
    metadata = Column(JSON)


class SQLConversationStore:
    """SQL数据库对话存储"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str = None,
        tool_calls: list = None,
        step_logs: list = None,
        execution_time: int = None,
        status: str = "success",
        error_message: str = None
    ) -> str:
        """保存对话记录"""
        session = self.Session()
        try:
            conversation = ConversationModel(
                id=str(uuid.uuid4()),
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                tool_calls=tool_calls,
                step_logs=step_logs,
                execution_time=execution_time,
                status=status,
                error_message=error_message
            )
            session.add(conversation)
            session.commit()
            
            # 更新会话统计
            self._update_session_stats(session, session_id)
            
            return conversation.id
        finally:
            session.close()
    
    def _update_session_stats(self, session, session_id: str):
        """更新会话统计信息"""
        sess = session.query(SessionModel).filter_by(id=session_id).first()
        if sess:
            sess.message_count += 1
            sess.updated_at = datetime.utcnow()
            session.commit()
    
    def get_conversation_history(
        self, 
        session_id: str, 
        limit: int = 50
    ) -> list:
        """获取对话历史"""
        session = self.Session()
        try:
            conversations = session.query(ConversationModel)\
                .filter_by(session_id=session_id)\
                .order_by(ConversationModel.created_at.desc())\
                .limit(limit)\
                .all()
            
            return [
                {
                    "id": c.id,
                    "user": c.user_message,
                    "assistant": c.assistant_message,
                    "tool_calls": c.tool_calls,
                    "created_at": c.created_at.isoformat()
                }
                for c in reversed(conversations)
            ]
        finally:
            session.close()
    
    def create_session(self, user_id: str = None, title: str = None) -> str:
        """创建新会话"""
        session = self.Session()
        try:
            sess = SessionModel(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=title or f"会话 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            session.add(sess)
            session.commit()
            return sess.id
        finally:
            session.close()


# 使用示例
store = SQLConversationStore("postgresql://user:pass@localhost/smolagents")

# 在Agent中集成
class PersistentAgent:
    def __init__(self, store: SQLConversationStore, session_id: str = None):
        self.store = store
        self.session_id = session_id or store.create_session()
        self.agent = CodeAgent(tools=[], model=InferenceClientModel())
    
    def run(self, query: str) -> str:
        import time
        start_time = time.time()
        
        try:
            result = self.agent.run(query)
            execution_time = int((time.time() - start_time) * 1000)
            
            # 保存成功记录
            self.store.save_conversation(
                session_id=self.session_id,
                user_message=query,
                assistant_message=result,
                tool_calls=self._extract_tool_calls(),
                step_logs=self._extract_step_logs(),
                execution_time=execution_time
            )
            
            return result
        
        except Exception as e:
            # 保存错误记录
            self.store.save_conversation(
                session_id=self.session_id,
                user_message=query,
                status="error",
                error_message=str(e)
            )
            raise
    
    def _extract_tool_calls(self):
        if hasattr(self.agent, "logs"):
            return [
                {"tool": log.tool_calls[0].name, "args": log.tool_calls[0].arguments}
                for log in self.agent.logs
                if hasattr(log, "tool_calls") and log.tool_calls
            ]
        return []
    
    def _extract_step_logs(self):
        if hasattr(self.agent, "logs"):
            return [str(log) for log in self.agent.logs]
        return []
```

#### 5.1.2 NoSQL存储

```python
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId


class MongoConversationStore:
    """MongoDB对话存储"""
    
    def __init__(self, connection_string: str, database: str = "smolagents"):
        self.client = MongoClient(connection_string)
        self.db = self.client[database]
        self.conversations = self.db.conversations
        self.sessions = self.db.sessions
        
        # 创建索引
        self.conversations.create_index("session_id")
        self.conversations.create_index("created_at")
        self.sessions.create_index("user_id")
    
    def save_conversation(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str = None,
        **kwargs
    ) -> str:
        """保存对话"""
        doc = {
            "_id": ObjectId(),
            "session_id": session_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "created_at": datetime.utcnow(),
            **kwargs
        }
        
        result = self.conversations.insert_one(doc)
        
        # 更新会话
        self.sessions.update_one(
            {"_id": session_id},
            {
                "$inc": {"message_count": 1},
                "$set": {"updated_at": datetime.utcnow()},
                "$setOnInsert": {"created_at": datetime.utcnow()}
            },
            upsert=True
        )
        
        return str(result.inserted_id)
    
    def get_conversation_history(
        self, 
        session_id: str, 
        limit: int = 50
    ) -> list:
        """获取对话历史"""
        cursor = self.conversations.find(
            {"session_id": session_id}
        ).sort("created_at", -1).limit(limit)
        
        return [
            {
                "id": str(doc["_id"]),
                "user": doc["user_message"],
                "assistant": doc.get("assistant_message"),
                "created_at": doc["created_at"].isoformat()
            }
            for doc in reversed(list(cursor))
        ]
    
    def search_conversations(self, query: str, user_id: str = None) -> list:
        """搜索对话历史"""
        search_filter = {
            "$text": {"$search": query}
        }
        if user_id:
            search_filter["user_id"] = user_id
        
        cursor = self.conversations.find(search_filter).limit(20)
        return list(cursor)
    
    def get_session_stats(self, session_id: str) -> dict:
        """获取会话统计"""
        pipeline = [
            {"$match": {"session_id": session_id}},
            {
                "$group": {
                    "_id": "$session_id",
                    "message_count": {"$sum": 1},
                    "avg_execution_time": {"$avg": "$execution_time"},
                    "first_message": {"$min": "$created_at"},
                    "last_message": {"$max": "$created_at"}
                }
            }
        ]
        
        result = list(self.conversations.aggregate(pipeline))
        return result[0] if result else {}


# Redis缓存层
import redis
import pickle


class RedisCache:
    """Redis缓存层"""
    
    def __init__(self, host='localhost', port=6379, db=0):
        self.client = redis.Redis(host=host, port=port, db=db)
        self.ttl = 3600  # 1小时过期
    
    def cache_agent_state(self, session_id: str, state: dict):
        """缓存Agent状态"""
        key = f"agent:state:{session_id}"
        self.client.setex(key, self.ttl, pickle.dumps(state))
    
    def get_agent_state(self, session_id: str) -> dict:
        """获取缓存的Agent状态"""
        key = f"agent:state:{session_id}"
        data = self.client.get(key)
        return pickle.loads(data) if data else None
    
    def cache_conversation(self, session_id: str, conversations: list):
        """缓存对话历史"""
        key = f"conversation:{session_id}"
        self.client.setex(key, self.ttl, pickle.dumps(conversations))
    
    def get_cached_conversation(self, session_id: str) -> list:
        """获取缓存的对话"""
        key = f"conversation:{session_id}"
        data = self.client.get(key)
        return pickle.loads(data) if data else None
```

### 5.2 状态持久化

#### 5.2.1 Checkpoint存储

```python
from dataclasses import dataclass, asdict
from typing import Any, Dict
import json
import hashlib


@dataclass
class AgentCheckpoint:
    """Agent检查点"""
    checkpoint_id: str
    session_id: str
    step_number: int
    agent_state: Dict[str, Any]
    memory_state: Dict[str, Any]
    tool_states: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any]


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, storage_backend):
        self.storage = storage_backend
        self.checkpoint_interval = 5  # 每5步保存
    
    def save_checkpoint(self, agent: CodeAgent, step_number: int) -> str:
        """保存检查点"""
        session_id = agent.session_id if hasattr(agent, "session_id") else "default"
        
        checkpoint = AgentCheckpoint(
            checkpoint_id=self._generate_id(session_id, step_number),
            session_id=session_id,
            step_number=step_number,
            agent_state=self._serialize_agent_state(agent),
            memory_state=self._serialize_memory(agent.memory),
            tool_states=self._serialize_tools(agent.tools),
            timestamp=datetime.utcnow(),
            metadata={
                "max_steps": agent.max_steps,
                "tools_count": len(agent.tools)
            }
        )
        
        self.storage.save(checkpoint)
        return checkpoint.checkpoint_id
    
    def restore_checkpoint(self, checkpoint_id: str) -> AgentCheckpoint:
        """恢复检查点"""
        return self.storage.load(checkpoint_id)
    
    def _serialize_agent_state(self, agent: CodeAgent) -> dict:
        """序列化Agent状态"""
        return {
            "logs": [self._serialize_log(log) for log in agent.logs] if hasattr(agent, "logs") else [],
            "system_prompt": agent.system_prompt if hasattr(agent, "system_prompt") else None,
            "tool_calls": agent.tool_calls if hasattr(agent, "tool_calls") else []
        }
    
    def _serialize_memory(self, memory) -> dict:
        """序列化内存"""
        if memory is None:
            return {}
        return {
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in memory.messages
            ] if hasattr(memory, "messages") else []
        }
    
    def _serialize_tools(self, tools: list) -> dict:
        """序列化工具状态"""
        return {
            tool.name: tool.to_dict() if hasattr(tool, "to_dict") else {"name": tool.name}
            for tool in tools
        }
    
    def _serialize_log(self, log) -> dict:
        """序列化日志"""
        return {
            "role": log.role if hasattr(log, "role") else "unknown",
            "content": str(log.content) if hasattr(log, "content") else str(log)
        }
    
    def _generate_id(self, session_id: str, step_number: int) -> str:
        """生成检查点ID"""
        content = f"{session_id}:{step_number}:{datetime.utcnow().timestamp()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


# 文件存储后端
import os


class FileCheckpointStorage:
    """文件系统检查点存储"""
    
    def __init__(self, base_path: str = "./checkpoints"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def save(self, checkpoint: AgentCheckpoint):
        """保存检查点"""
        session_dir = os.path.join(self.base_path, checkpoint.session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        filepath = os.path.join(session_dir, f"{checkpoint.checkpoint_id}.json")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(checkpoint), f, default=str, indent=2)
    
    def load(self, checkpoint_id: str) -> AgentCheckpoint:
        """加载检查点"""
        # 遍历查找
        for session_id in os.listdir(self.base_path):
            filepath = os.path.join(self.base_path, session_id, f"{checkpoint_id}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return AgentCheckpoint(**data)
        
        raise FileNotFoundError(f"检查点不存在: {checkpoint_id}")
    
    def list_checkpoints(self, session_id: str) -> list:
        """列出会话的所有检查点"""
        session_dir = os.path.join(self.base_path, session_id)
        if not os.path.exists(session_dir):
            return []
        
        checkpoints = []
        for filename in os.listdir(session_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(session_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    checkpoints.append({
                        "checkpoint_id": data["checkpoint_id"],
                        "step_number": data["step_number"],
                        "timestamp": data["timestamp"]
                    })
        
        return sorted(checkpoints, key=lambda x: x["step_number"])
```

### 5.3 配置管理

#### 5.3.1 动态配置

```python
from pydantic import BaseSettings, Field
from typing import Optional, List
import yaml
import os


class AgentSettings(BaseSettings):
    """Agent配置"""
    model_name: str = Field(default="Qwen/Qwen2.5-Coder-32B-Instruct")
    max_steps: int = Field(default=10)
    timeout: int = Field(default=60)
    add_base_tools: bool = Field(default=True)
    planning_interval: Optional[int] = Field(default=None)
    
    class Config:
        env_prefix = "SMOLAGENTS_"


class DatabaseSettings(BaseSettings):
    """数据库配置"""
    url: str = Field(default="postgresql://localhost/smolagents")
    pool_size: int = Field(default=10)
    max_overflow: int = Field(default=20)
    
    class Config:
        env_prefix = "DB_"


class ConfigManager:
    """动态配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.agent_settings = AgentSettings()
        self.db_settings = DatabaseSettings()
        self._watchers = []
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
                if 'agent' in config:
                    for key, value in config['agent'].items():
                        if hasattr(self.agent_settings, key):
                            setattr(self.agent_settings, key, value)
                
                if 'database' in config:
                    for key, value in config['database'].items():
                        if hasattr(self.db_settings, key):
                            setattr(self.db_settings, key, value)
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
        # 通知观察者
        for watcher in self._watchers:
            watcher(self)
    
    def add_watcher(self, callback):
        """添加配置变更监听器"""
        self._watchers.append(callback)
    
    def get_agent_config(self) -> dict:
        """获取Agent配置"""
        return {
            "model_name": self.agent_settings.model_name,
            "max_steps": self.agent_settings.max_steps,
            "timeout": self.agent_settings.timeout,
            "add_base_tools": self.agent_settings.add_base_tools,
            "planning_interval": self.agent_settings.planning_interval
        }
    
    def update_config(self, section: str, key: str, value: any):
        """运行时更新配置"""
        if section == "agent" and hasattr(self.agent_settings, key):
            setattr(self.agent_settings, key, value)
        elif section == "database" and hasattr(self.db_settings, key):
            setattr(self.db_settings, key, value)
        
        # 持久化到文件
        self._save_config()
    
    def _save_config(self):
        """保存配置到文件"""
        config = {
            "agent": self.agent_settings.dict(),
            "database": self.db_settings.dict()
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False)


# 在Agent中使用动态配置
config_manager = ConfigManager()

class ConfigurableAgent:
    """支持动态配置的Agent"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.agent = self._create_agent()
        
        # 监听配置变更
        self.config_manager.add_watcher(self._on_config_change)
    
    def _create_agent(self) -> CodeAgent:
        """根据配置创建Agent"""
        config = self.config_manager.get_agent_config()
        
        return CodeAgent(
            tools=[],
            model=InferenceClientModel(config["model_name"]),
            max_steps=config["max_steps"],
            add_base_tools=config["add_base_tools"],
            planning_interval=config["planning_interval"]
        )
    
    def _on_config_change(self, config_manager: ConfigManager):
        """配置变更回调"""
        # 重新创建Agent以应用新配置
        self.agent = self._create_agent()
        print("配置已更新，Agent已重新初始化")
    
    def run(self, query: str) -> str:
        return self.agent.run(query)
```

---

## 六、与消息队列整合

### 6.1 异步任务

#### 6.1.1 Celery集成

```python
from celery import Celery, chain, group, chord
from celery.result import AsyncResult
from smolagents import CodeAgent, Tool
import json

# Celery应用配置
celery_app = Celery(
    'smolagents_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['smolagents_integration.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10分钟超时
    worker_prefetch_multiplier=1,  # 公平调度
)


@celery_app.task(bind=True, max_retries=3)
def execute_single_task(self, query: str, tools: list, session_id: str):
    """执行单个Agent任务"""
    try:
        self.update_state(state='STARTED', meta={'progress': 0})
        
        # 初始化Agent
        agent = create_agent(tools)
        
        self.update_state(state='PROGRESS', meta={'progress': 30, 'status': '执行中'})
        
        # 执行
        result = agent.run(query)
        
        self.update_state(state='SUCCESS', meta={
            'progress': 100,
            'result': result,
            'steps': len(agent.logs) if hasattr(agent, 'logs') else 0
        })
        
        return {
            'session_id': session_id,
            'result': result,
            'status': 'success'
        }
    
    except Exception as exc:
        # 重试逻辑
        if self.request.retries < self.max_retries:
            self.retry(countdown=60, exc=exc)
        
        self.update_state(state='FAILURE', meta={'error': str(exc)})
        raise


@celery_app.task
def process_batch_tasks(tasks: list):
    """批量处理任务"""
    job = group(
        execute_single_task.s(task['query'], task['tools'], task['session_id'])
        for task in tasks
    )
    result = job.apply_async()
    return result.id


@celery_app.task
def analyze_results(results: list):
    """分析批量任务结果"""
    successful = [r for r in results if r.get('status') == 'success']
    failed = [r for r in results if r.get('status') != 'success']
    
    return {
        'total': len(results),
        'successful': len(successful),
        'failed': len(failed),
        'success_rate': len(successful) / len(results) if results else 0
    }


# 复杂工作流示例
def create_analysis_workflow(data_sources: list, final_query: str):
    """创建分析工作流"""
    # 并行处理多个数据源
    parallel_tasks = group(
        execute_single_task.s(
            f"分析数据源: {source}",
            ['data_analysis'],
            f"workflow_{source}"
        )
        for source in data_sources
    )
    
    # 汇总分析
    summary_task = execute_single_task.s(
        final_query,
        ['synthesis'],
        "workflow_summary"
    )
    
    # 创建工作流：并行任务 -> 汇总
    workflow = chain(parallel_tasks, summary_task)
    
    return workflow.apply_async()


# 任务监控
class TaskMonitor:
    """任务监控器"""
    
    def __init__(self):
        self.celery_app = celery_app
    
    def get_task_info(self, task_id: str) -> dict:
        """获取任务信息"""
        result = AsyncResult(task_id, app=self.celery_app)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'date_done': result.date_done.isoformat() if result.date_done else None,
            'traceback': result.traceback if result.failed() else None
        }
    
    def get_queue_stats(self) -> dict:
        """获取队列统计"""
        inspector = self.celery_app.control.inspect()
        
        return {
            'active': inspector.active(),
            'scheduled': inspector.scheduled(),
            'reserved': inspector.reserved(),
            'stats': inspector.stats()
        }
    
    def revoke_task(self, task_id: str, terminate: bool = False):
        """取消任务"""
        self.celery_app.control.revoke(task_id, terminate=terminate)


# 使用示例
"""
# 提交单个任务
task = execute_single_task.delay(
    query="分析销售数据",
    tools=["data_analysis", "visualization"],
    session_id="session_001"
)

# 查询任务状态
monitor = TaskMonitor()
info = monitor.get_task_info(task.id)

# 提交批量任务
batch_job = process_batch_tasks.delay([
    {'query': '任务1', 'tools': [], 'session_id': 's1'},
    {'query': '任务2', 'tools': [], 'session_id': 's2'},
])

# 创建工作流
workflow = create_analysis_workflow(
    data_sources=['sales', 'marketing', 'support'],
    final_query='综合分析所有部门数据'
)
"""
```

#### 6.1.2 任务队列管理

```python
from queue import Queue, PriorityQueue
from threading import Thread, Lock
from dataclasses import dataclass, field
from typing import Callable
import time
import uuid


@dataclass(order=True)
class PrioritizedTask:
    """优先级任务"""
    priority: int
    created_at: float = field(compare=False)
    task_id: str = field(compare=False)
    query: str = field(compare=False)
    callback: Callable = field(compare=False, default=None)


class LocalTaskQueue:
    """本地任务队列"""
    
    def __init__(self, max_workers: int = 3):
        self.task_queue = PriorityQueue()
        self.results = {}
        self.workers = []
        self.max_workers = max_workers
        self.running = False
        self.lock = Lock()
        
        # Agent实例池
        self.agent_pool = AgentPool()
    
    def start(self):
        """启动工作线程"""
        self.running = True
        for i in range(self.max_workers):
            worker = Thread(target=self._worker_loop, name=f"Worker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
    
    def stop(self):
        """停止队列"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)
    
    def submit(self, query: str, priority: int = 5, callback: Callable = None) -> str:
        """提交任务"""
        task_id = str(uuid.uuid4())
        task = PrioritizedTask(
            priority=priority,
            created_at=time.time(),
            task_id=task_id,
            query=query,
            callback=callback
        )
        
        self.task_queue.put(task)
        
        with self.lock:
            self.results[task_id] = {
                'status': 'pending',
                'result': None,
                'submitted_at': time.time()
            }
        
        return task_id
    
    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1)
                self._process_task(task)
            except:
                continue
    
    def _process_task(self, task: PrioritizedTask):
        """处理单个任务"""
        # 更新状态
        with self.lock:
            self.results[task.task_id]['status'] = 'running'
            self.results[task.task_id]['started_at'] = time.time()
        
        try:
            # 获取Agent
            agent = self.agent_pool.get_agent()
            
            # 执行
            result = agent.run(task.query)
            
            # 保存结果
            with self.lock:
                self.results[task.task_id].update({
                    'status': 'completed',
                    'result': result,
                    'completed_at': time.time()
                })
            
            # 执行回调
            if task.callback:
                task.callback(task.task_id, result)
        
        except Exception as e:
            with self.lock:
                self.results[task.task_id].update({
                    'status': 'failed',
                    'error': str(e),
                    'completed_at': time.time()
                })
        
        finally:
            self.agent_pool.release_agent(agent)
    
    def get_result(self, task_id: str) -> dict:
        """获取任务结果"""
        with self.lock:
            return self.results.get(task_id, {}).copy()
    
    def get_queue_status(self) -> dict:
        """获取队列状态"""
        return {
            'queue_size': self.task_queue.qsize(),
            'active_workers': len([w for w in self.workers if w.is_alive()]),
            'completed_tasks': len([r for r in self.results.values() if r['status'] == 'completed']),
            'pending_tasks': len([r for r in self.results.values() if r['status'] == 'pending'])
        }


class AgentPool:
    """Agent实例池"""
    
    def __init__(self, pool_size: int = 5):
        self.available = Queue()
        self.in_use = set()
        self.lock = Lock()
        
        # 预创建Agent
        for _ in range(pool_size):
            agent = CodeAgent(
                tools=[],
                model=InferenceClientModel()
            )
            self.available.put(agent)
    
    def get_agent(self) -> CodeAgent:
        """获取可用Agent"""
        agent = self.available.get(timeout=30)
        with self.lock:
            self.in_use.add(id(agent))
        return agent
    
    def release_agent(self, agent: CodeAgent):
        """释放Agent"""
        with self.lock:
            self.in_use.discard(id(agent))
        self.available.put(agent)
```

### 6.2 分布式执行

#### 6.2.1 跨节点Agent调用

```python
import grpc
from concurrent import futures
import protobuf.agent_pb2 as agent_pb2
import protobuf.agent_pb2_grpc as agent_pb2_grpc


class AgentService(agent_pb2_grpc.AgentServiceServicer):
    """gRPC Agent服务"""
    
    def __init__(self):
        self.agent_pool = AgentPool()
    
    def Execute(self, request, context):
        """执行Agent任务"""
        try:
            agent = self.agent_pool.get_agent()
            
            result = agent.run(request.query)
            
            return agent_pb2.ExecuteResponse(
                task_id=request.task_id,
                result=result,
                status='success',
                steps=len(agent.logs) if hasattr(agent, 'logs') else 0
            )
        except Exception as e:
            return agent_pb2.ExecuteResponse(
                task_id=request.task_id,
                error=str(e),
                status='error'
            )
    
    def StreamExecute(self, request, context):
        """流式执行"""
        agent = self.agent_pool.get_agent()
        
        # 模拟流式输出
        for i, log in enumerate(agent.logs if hasattr(agent, 'logs') else []):
            yield agent_pb2.StreamChunk(
                chunk_type='step',
                content=str(log),
                step_number=i
            )


def serve_grpc(port=50051):
    """启动gRPC服务"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    agent_pb2_grpc.add_AgentServiceServicer_to_server(AgentService(), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    return server


# gRPC客户端
class RemoteAgentClient:
    """远程Agent客户端"""
    
    def __init__(self, host: str, port: int):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = agent_pb2_grpc.AgentServiceStub(self.channel)
    
    def execute(self, query: str, task_id: str = None) -> dict:
        """远程执行"""
        task_id = task_id or str(uuid.uuid4())
        
        request = agent_pb2.ExecuteRequest(
            task_id=task_id,
            query=query
        )
        
        response = self.stub.Execute(request)
        
        return {
            'task_id': response.task_id,
            'result': response.result,
            'status': response.status,
            'error': response.error if response.error else None,
            'steps': response.steps
        }
    
    def stream_execute(self, query: str):
        """流式远程执行"""
        request = agent_pb2.ExecuteRequest(
            task_id=str(uuid.uuid4()),
            query=query
        )
        
        for chunk in self.stub.StreamExecute(request):
            yield {
                'type': chunk.chunk_type,
                'content': chunk.content,
                'step': chunk.step_number
            }


# 负载均衡器
class LoadBalancer:
    """Agent服务负载均衡器"""
    
    def __init__(self, nodes: list):
        """
        nodes: [{'host': 'localhost', 'port': 50051, 'weight': 1}]
        """
        self.nodes = nodes
        self.clients = {}
        self.current_index = 0
        self.lock = Lock()
        
        # 初始化连接
        for node in nodes:
            key = f"{node['host']}:{node['port']}"
            self.clients[key] = RemoteAgentClient(node['host'], node['port'])
    
    def get_client(self) -> RemoteAgentClient:
        """获取下一个客户端（轮询）"""
        with self.lock:
            node = self.nodes[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.nodes)
        
        key = f"{node['host']}:{node['port']}"
        return self.clients[key]
    
    def execute(self, query: str) -> dict:
        """负载均衡执行"""
        client = self.get_client()
        return client.execute(query)
    
    def health_check(self) -> dict:
        """健康检查"""
        status = {}
        for key, client in self.clients.items():
            try:
                # 简单健康检查
                result = client.execute("test", task_id="health_check")
                status[key] = 'healthy' if result['status'] != 'error' else 'unhealthy'
            except:
                status[key] = 'unreachable'
        
        return status
```

### 6.3 结果回调

#### 6.3.1 Webhook

```python
import requests
import hmac
import hashlib
from typing import Callable


class WebhookCallback:
    """Webhook回调处理器"""
    
    def __init__(self, webhook_url: str, secret: str = None):
        self.webhook_url = webhook_url
        self.secret = secret
    
    def __call__(self, task_id: str, result: any):
        """发送Webhook回调"""
        payload = {
            'task_id': task_id,
            'result': result,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # 签名验证
        if self.secret:
            signature = self._generate_signature(payload)
            headers['X-Webhook-Signature'] = signature
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Webhook发送失败: {e}")
            return False
    
    def _generate_signature(self, payload: dict) -> str:
        """生成HMAC签名"""
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.secret.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"


# 使用
webhook_callback = WebhookCallback(
    webhook_url="https://example.com/webhook",
    secret="your-secret-key"
)

# 提交带回调的任务
task_id = task_queue.submit(
    query="分析数据",
    priority=1,
    callback=webhook_callback
)
```

#### 6.3.2 消息通知

```python
from abc import ABC, abstractmethod


class NotificationProvider(ABC):
    """通知提供者基类"""
    
    @abstractmethod
    def send(self, message: str, **kwargs) -> bool:
        pass


class SlackNotifier(NotificationProvider):
    """Slack通知"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send(self, message: str, channel: str = None, **kwargs) -> bool:
        payload = {
            'text': message,
            'channel': channel
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload)
            return response.status_code == 200
        except:
            return False


class EmailNotifier(NotificationProvider):
    """邮件通知"""
    
    def __init__(self, smtp_host: str, smtp_port: int, 
                 username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send(self, message: str, to_email: str, subject: str = None, **kwargs) -> bool:
        import smtplib
        from email.mime.text import MIMEText
        
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject or 'Agent任务完成'
            msg['From'] = self.username
            msg['To'] = to_email
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return True
        except:
            return False


class NotificationManager:
    """通知管理器"""
    
    def __init__(self):
        self.providers: list[NotificationProvider] = []
    
    def add_provider(self, provider: NotificationProvider):
        self.providers.append(provider)
    
    def notify_all(self, message: str, **kwargs):
        """发送所有通知"""
        results = []
        for provider in self.providers:
            result = provider.send(message, **kwargs)
            results.append((provider.__class__.__name__, result))
        return results
    
    def create_task_callback(self, task_description: str):
        """创建任务完成回调"""
        def callback(task_id: str, result: any):
            message = f"任务完成\n任务ID: {task_id}\n描述: {task_description}\n结果: {str(result)[:500]}"
            self.notify_all(message)
        return callback


# 使用
notifier = NotificationManager()
notifier.add_provider(SlackNotifier("https://hooks.slack.com/..."))
notifier.add_provider(EmailNotifier("smtp.gmail.com", 587, "user", "pass"))

# 作为任务回调
task_id = task_queue.submit(
    query="复杂分析任务",
    callback=notifier.create_task_callback("销售数据分析")
)
```

---

## 七、整合最佳实践

### 7.1 性能优化

| 优化策略 | 适用场景 | 实施方法 |
|----------|----------|----------|
| Agent池化 | 高并发请求 | 预创建Agent实例，复用连接 |
| 异步执行 | 耗时任务 | 使用Celery或后台线程 |
| 结果缓存 | 重复查询 | Redis缓存常见查询结果 |
| 流式输出 | 长任务 | WebSocket或SSE实时返回 |
| 连接池 | 数据库操作 | SQLAlchemy连接池配置 |

### 7.2 错误处理

```python
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
def execute_with_retry(agent: CodeAgent, query: str) -> str:
    """带重试的执行"""
    return agent.run(query)


class ErrorHandler:
    """错误处理器"""
    
    ERROR_CODES = {
        'AGENT_TIMEOUT': '执行超时，请简化查询或增加超时时间',
        'TOOL_ERROR': '工具调用失败，请检查工具配置',
        'MODEL_ERROR': '模型调用失败，请检查模型配置',
        'MEMORY_ERROR': '内存不足，请清理历史会话',
        'NETWORK_ERROR': '网络错误，请检查连接'
    }
    
    @classmethod
    def handle(cls, error: Exception) -> dict:
        """处理错误"""
        error_type = type(error).__name__
        
        return {
            'error_code': error_type,
            'message': str(error),
            'user_message': cls.ERROR_CODES.get(error_type, '未知错误，请联系管理员'),
            'retryable': error_type in ['NETWORK_ERROR', 'MODEL_ERROR']
        }
```

### 7.3 监控指标

```python
from prometheus_client import Counter, Histogram, Gauge

# 定义指标
agent_requests = Counter('agent_requests_total', 'Agent请求总数', ['status'])
agent_duration = Histogram('agent_duration_seconds', 'Agent执行耗时')
active_sessions = Gauge('agent_active_sessions', '活跃会话数')
tool_calls = Counter('tool_calls_total', '工具调用次数', ['tool_name'])


class MetricsCollector:
    """指标收集器"""
    
    @staticmethod
    def record_request(duration: float, success: bool):
        status = 'success' if success else 'failure'
        agent_requests.labels(status=status).inc()
        agent_duration.observe(duration)
    
    @staticmethod
    def record_tool_call(tool_name: str):
        tool_calls.labels(tool_name=tool_name).inc()
    
    @staticmethod
    def update_session_count(delta: int):
        active_sessions.set(active_sessions._value.get() + delta)
```

---

## 八、参考文档

- [[19-smolagents-MCP与扩展机制]] - MCP协议与扩展机制分析
- [[20-smolagents-Agent架构解析]] - Agent内部架构详解
- [[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/agents.py|agents.py 源码]]
- [[Projects/AI数据分析系统/参考项目/smolagents/src/smolagents/tools.py|tools.py 源码]]
- FastAPI文档: https://fastapi.tiangolo.com/
- Celery文档: https://docs.celeryq.dev/
- LlamaIndex文档: https://docs.llamaindex.ai/
- LangChain文档: https://python.langchain.com/

---

## 版本记录

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 1.0 | 2026-02-06 | 初始版本，包含完整的生态整合方案 |
