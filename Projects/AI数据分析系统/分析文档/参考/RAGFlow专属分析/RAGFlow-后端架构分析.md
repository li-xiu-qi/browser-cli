# RAGFlow 后端架构深度分析

**分析日期**: 2026-02-05  
**项目版本**: RAGFlow v0.23.1  
**技术栈**: Python 3.12 + Flask + SQLAlchemy + Elasticsearch + Redis  
**分析路径**: `api/`, `rag/`, `deepdoc/`

---

## 一、整体架构概览

### 1.1 技术栈选型

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAGFlow 后端技术栈                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  【Web框架】                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Flask + Flask-RESTX                                               │   │
│  │  - RESTful API                                                     │   │
│  │  - 自动Swagger文档生成                                              │   │
│  │  - 请求验证                                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  【数据库】                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  MySQL/PostgreSQL (主数据库)                                        │   │
│  │  - SQLAlchemy ORM                                                  │   │
│  │  - Alembic 数据库迁移                                               │   │
│  │                                                                     │   │
│  │  Elasticsearch (向量检索)                                           │   │
│  │  - 文档索引                                                         │   │
│  │  - 全文检索                                                         │   │
│  │  - 向量相似度搜索                                                    │   │
│  │                                                                     │   │
│  │  Redis (缓存 + 消息队列)                                            │   │
│  │  - 缓存                                                            │   │
│  │  - Celery任务队列                                                   │   │
│  │  - 会话存储                                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  【异步任务】                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Celery + Redis/RabbitMQ                                           │   │
│  │  - 文档解析（耗时操作）                                              │   │
│  │  - 索引构建                                                         │   │
│  │  - 定时任务                                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  【LLM集成】                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  多模型支持：                                                        │   │
│  │  - OpenAI (GPT-4/3.5)                                              │   │
│  │  - Azure OpenAI                                                    │   │
│  │  - 本地模型 (Ollama, Xinference)                                    │   │
│  │  - 国内模型 (文心一言、通义千问、智谱)                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  【文档解析】                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  DeepDoc (自研深度文档理解)                                         │   │
│  │  - OCR (文字识别)                                                   │   │
│  │  - 版面分析 (Layout Analysis)                                       │   │
│  │  - 表格提取                                                         │   │
│  │  - 图片理解                                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 与RATH后端的对比

| 维度 | RATH | RAGFlow | 评价 |
|------|------|---------|------|
| **Web框架** | FastAPI/Flask | Flask | 持平，FastAPI更现代但Flask更成熟 |
| **数据库** | PostgreSQL | MySQL/PostgreSQL + ES |  RAGFlow多了ES向量检索 |
| **向量存储** |  无 |  Elasticsearch |  RAGFlow支持语义搜索 |
| **缓存** |  无 |  Redis |  RAGFlow有缓存层 |
| **异步任务** |  无 |  Celery |  RAGFlow支持异步处理 |
| **LLM集成** |  无 |  多模型支持 |  RAGFlow原生LLM |
| **文档解析** | 基础 |  DeepDoc深度理解 |  RAGFlow核心差异化能力 |

---

## 二、目录结构分析

### 2.1 整体结构

```
ragflow/
├──  api/                    # REST API层
│   ├──  apps/              # 业务应用（按模块组织）
│   │   ├──  conversation/  # 对话管理
│   │   ├──  document/      # 文档管理
│   │   ├──  knowledgebase/ # 知识库管理
│   │   ├──  user/          # 用户管理
│   │   └──  file/          # 文件管理
│   ├──  common/            # 公共工具
│   ├──  db/                # 数据库模型
│   │   ├──  database.py    # 数据库连接
│   │   ├──  models.py      # SQLAlchemy模型
│   │   └──  session.py     # 会话管理
│   ├──  ragflow_server.py  # 服务入口
│   └──  settings.py        # 配置文件
│
├──  rag/                    # RAG引擎核心
│   ├──  app.py             # RAG应用封装
│   ├──  nlp/               # NLP处理
│   ├──  prompt/            # Prompt模板
│   ├──  search/            # 检索逻辑
│   └──  utils/             # RAG工具
│
├──  deepdoc/                # 深度文档理解（核心差异化）
│   ├──  parser/            # 文档解析器
│   │   ├──  pdf_parser.py
│   │   ├──  docx_parser.py
│   │   └──  excel_parser.py
│   ├──  vision/            # 视觉/OCR
│   │   ├──  table_recognition.py  # 表格识别
│   │   ├──  layout_analysis.py    # 版面分析
│   │   └──  ocr.py                # OCR识别
│   └──  chunk/             # 文档分块
│
├──  agent/                  # Agent编排（见单独分析文档）
│
├──  graph/                  # 知识图谱
│
├──  tools/                  # 外部工具集成
│   ├──  search/            # 搜索引擎
│   └──  database/          # 数据库查询
│
└──  conf/                   # 配置文件
```

### 2.2 分层架构设计

```
┌───────────────────────────────────────────────────────────────────────────┐
│                        RAGFlow 后端分层架构                                 │
├───────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  【API层】api/                                                              │
│  - RESTful API路由定义                                                      │
│  - 请求参数验证（validation）                                               │
│  - 响应序列化                                                                │
│  - 认证授权（JWT/OAuth2）                                                    │
│                                                                            │
│  【服务层】apps/ + services/                                                │
│  - 业务逻辑封装                                                              │
│  - 事务管理                                                                  │
│  - 数据转换（DTO）                                                           │
│                                                                            │
│  【数据访问层】db/ + DAO/                                                   │
│  - SQLAlchemy模型定义                                                        │
│  - 数据库操作                                                                │
│  - 缓存管理                                                                  │
│                                                                            │
│  【引擎层】rag/ + deepdoc/                                                  │
│  - RAG检索引擎                                                               │
│  - 文档解析引擎                                                              │
│  - LLM调用封装                                                               │
│                                                                            │
│  【基础设施层】                                                             │
│  - MySQL/PostgreSQL                                                         │
│  - Elasticsearch                                                            │
│  - Redis                                                                    │
│  - MinIO/S3（对象存储）                                                      │
│                                                                            │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详解

### 3.1 API层设计 (api/apps/)

```python
# api/apps/knowledgebase/__init__.py 简化分析
from flask import Blueprint
from flask_restx import Api, Resource, fields

kb_blueprint = Blueprint('knowledgebase', __name__)
api = Api(kb_blueprint, doc='/doc/')  # Swagger文档

# 定义数据模型
knowledgebase_model = api.model('KnowledgeBase', {
    'id': fields.String(readonly=True, description='知识库ID'),
    'name': fields.String(required=True, description='知识库名称'),
    'description': fields.String(description='描述'),
    'created_at': fields.DateTime(readonly=True),
})

# API路由
@api.route('/')
class KnowledgeBaseList(Resource):
    @api.marshal_list_with(knowledgebase_model)
    def get(self):
        """获取知识库列表"""
        return KnowledgebaseService.get_list()
    
    @api.expect(knowledgebase_model)
    @api.marshal_with(knowledgebase_model, code=201)
    def post(self):
        """创建知识库"""
        return KnowledgebaseService.create(api.payload), 201

@api.route('/<string:id>')
class KnowledgeBase(Resource):
    def get(self, id):
        """获取知识库详情"""
        return KnowledgebaseService.get_by_id(id)
    
    def delete(self, id):
        """删除知识库"""
        KnowledgebaseService.delete(id)
        return '', 204

# 特点：
#  Flask-RESTX自动生成Swagger文档
#  请求/响应模型定义清晰
#  RESTful设计规范
```

### 3.2 数据库层 (api/db/)

```python
# api/db/models.py 简化分析
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from api.db.database import Base

class KnowledgeBase(Base):
    """知识库模型"""
    __tablename__ = 'knowledgebase'
    
    id = Column(String(32), primary_key=True)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    tenant_id = Column(String(32), ForeignKey('tenant.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    # 关系
    tenant = relationship('Tenant', back_populates='knowledgebases')
    documents = relationship('Document', back_populates='knowledgebase', cascade='all, delete-orphan')

class Document(Base):
    """文档模型"""
    __tablename__ = 'document'
    
    id = Column(String(32), primary_key=True)
    kb_id = Column(String(32), ForeignKey('knowledgebase.id'))
    name = Column(String(255), nullable=False)
    location = Column(String(512))  # 存储路径
    size = Column(Integer)  # 文件大小
    type = Column(String(32))  # 文件类型
    status = Column(String(16), default='PENDING')  # 处理状态
    
    # RAG相关
    chunk_num = Column(Integer, default=0)  # 分块数量
    token_num = Column(Integer, default=0)  # Token数量
    
    knowledgebase = relationship('KnowledgeBase', back_populates='documents')

# 特点：
#  SQLAlchemy ORM定义清晰
#  关系定义完整（一对多）
#  字段注释完善
```

### 3.3 RAG引擎核心 (rag/)

```python
# rag/app.py 简化分析 - RAG应用封装

class RAGApplication:
    """RAG应用主类"""
    
    def __init__(self, config):
        self.llm = LLMService(config.llm_config)
        self.retriever = RetrieverService(config.retriever_config)
        self.prompt = PromptTemplate()
    
    def chat(self, query: str, kb_ids: List[str], history: List[dict] = None) -> str:
        """
        RAG对话
        
        Args:
            query: 用户查询
            kb_ids: 知识库ID列表
            history: 对话历史
        
        Returns:
            生成的回答
        """
        # 1. 检索相关文档
        retrieved_docs = self.retriever.search(query, kb_ids, top_k=10)
        
        # 2. 构建Prompt
        context = '\n'.join([doc.content for doc in retrieved_docs])
        prompt = self.prompt.build(query, context, history)
        
        # 3. 调用LLM生成
        response = self.llm.generate(prompt)
        
        # 4. 返回结果（带引用）
        return {
            'answer': response,
            'references': [
                {'doc_id': doc.id, 'content': doc.content[:200]}
                for doc in retrieved_docs
            ]
        }

# rag/search/search.py
class RetrieverService:
    """检索服务"""
    
    def __init__(self):
        self.es = ElasticsearchService()  # ES全文检索
        self.vector_store = VectorStore()  # 向量检索
    
    def search(self, query: str, kb_ids: List[str], top_k: int = 10):
        """混合检索"""
        # 1. 全文检索
        text_results = self.es.search(query, kb_ids, top_k)
        
        # 2. 向量检索（语义相似）
        query_embedding = self.embed(query)
        vector_results = self.vector_store.similarity_search(
            query_embedding, kb_ids, top_k
        )
        
        # 3. 结果融合（RRF算法）
        return self.reciprocal_rank_fusion(text_results, vector_results)
```

### 3.4 深度文档理解 (deepdoc/) - 核心差异化

```python
# deepdoc/parser/pdf_parser.py 简化分析

class PDFParser:
    """PDF解析器 - 深度理解PDF结构"""
    
    def __init__(self):
        self.ocr = OCRService()  # OCR服务
        self.layout = LayoutAnalyzer()  # 版面分析
        self.table = TableRecognizer()  # 表格识别
    
    def parse(self, file_path: str) -> List[DocumentSegment]:
        """
        解析PDF文档
        
        Returns:
            文档片段列表（保留结构信息）
        """
        segments = []
        
        # 1. 逐页处理
        for page_num, page in enumerate(self.read_pages(file_path)):
            # 2. 版面分析 - 识别文本块、图片、表格区域
            layout_result = self.layout.analyze(page)
            
            for region in layout_result.regions:
                if region.type == 'text':
                    # 文字区域
                    text = self.extract_text(region)
                    segments.append(DocumentSegment(
                        type='text',
                        content=text,
                        page=page_num,
                        bbox=region.bbox
                    ))
                
                elif region.type == 'table':
                    # 表格区域 - 结构化提取
                    table_data = self.table.recognize(region)
                    segments.append(DocumentSegment(
                        type='table',
                        content=table_data.to_markdown(),
                        page=page_num,
                        bbox=region.bbox
                    ))
                
                elif region.type == 'image':
                    # 图片区域 - OCR提取
                    image_text = self.ocr.recognize(region)
                    segments.append(DocumentSegment(
                        type='image',
                        content=image_text,
                        page=page_num,
                        bbox=region.bbox
                    ))
        
        return segments

# deepdoc/vision/table_recognition.py

class TableRecognizer:
    """表格识别 - 将图片表格转为结构化数据"""
    
    def recognize(self, image_region) -> TableData:
        """
        识别表格结构
        
        输出：
        {
            'headers': ['列1', '列2', '列3'],
            'rows': [
                ['数据1', '数据2', '数据3'],
                ['数据4', '数据5', '数据6']
            ]
        }
        """
        # 1. 检测表格线
        lines = self.detect_lines(image_region)
        
        # 2. 识别单元格
        cells = self.extract_cells(image_region, lines)
        
        # 3. OCR识别每个单元格内容
        for cell in cells:
            cell.text = self.ocr.recognize(cell.image)
        
        # 4. 构建结构化表格
        return self.build_table_structure(cells)

# 特点：
#  不仅提取文本，还理解文档结构
#  表格保留结构化（不只是文字堆砌）
#  图片OCR提取
#  版面分析（标题、段落、列表识别）
```

---

## 四、异步任务处理 (Celery)

### 4.1 文档处理流程

```python
# api/tasks/document_tasks.py

from celery import shared_task

@shared_task(bind=True, max_retries=3)
def process_document(self, doc_id: str):
    """
    异步处理文档任务
    
    流程：
    1. 下载/读取文档
    2. 解析文档（DeepDoc）
    3. 分块
    4. 生成向量
    5. 索引到ES
    """
    try:
        # 更新状态为处理中
        DocumentService.update_status(doc_id, 'PROCESSING')
        
        # 1. 获取文档
        doc = DocumentService.get_by_id(doc_id)
        
        # 2. 解析（根据类型选择解析器）
        parser = get_parser(doc.type)
        segments = parser.parse(doc.location)
        
        # 3. 分块
        chunks = chunk_segments(segments)
        
        # 4. 生成向量
        for chunk in chunks:
            chunk.embedding = embed(chunk.content)
        
        # 5. 索引到ES
        index_to_elasticsearch(doc.kb_id, chunks)
        
        # 更新状态完成
        DocumentService.update_status(doc_id, 'COMPLETED', chunk_num=len(chunks))
        
    except Exception as exc:
        # 失败重试
        DocumentService.update_status(doc_id, 'FAILED', error=str(exc))
        self.retry(exc=exc, countdown=60)

# 使用示例
# 上传文档后异步处理
document_tasks.process_document.delay(new_doc.id)
```

---

## 五、LLM集成设计

### 5.1 多模型支持

```python
# rag/llm/base.py

class BaseLLM(ABC):
    """LLM基类"""
    
    @abstractmethod
    def chat(self, messages: List[Message], **kwargs) -> str:
        """对话接口"""
        pass
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embedding接口"""
        pass

# rag/llm/openai.py

class OpenAILLM(BaseLLM):
    """OpenAI集成"""
    
    def __init__(self, api_key: str, model: str = 'gpt-4'):
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def chat(self, messages: List[Message], **kwargs) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[m.dict() for m in messages],
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 2000)
        )
        return response.choices[0].message.content
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            model='text-embedding-3-small',
            input=texts
        )
        return [item.embedding for item in response.data]

# rag/llm/ollama.py

class OllamaLLM(BaseLLM):
    """本地Ollama集成"""
    
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model
    
    def chat(self, messages: List[Message], **kwargs) -> str:
        # 调用本地Ollama服务
        response = requests.post(
            f'{self.base_url}/api/chat',
            json={
                'model': self.model,
                'messages': [m.dict() for m in messages]
            }
        )
        return response.json()['message']['content']

# LLM工厂
class LLMFactory:
    """LLM工厂 - 根据配置创建对应实例"""
    
    @staticmethod
    def create(config: LLMConfig) -> BaseLLM:
        if config.provider == 'openai':
            return OpenAILLM(config.api_key, config.model)
        elif config.provider == 'ollama':
            return OllamaLLM(config.base_url, config.model)
        elif config.provider == 'azure':
            return AzureOpenAILLM(config)
        # ... 其他提供商
```

---

## 六、与RATH后端对比总结

### 6.1 RAGFlow的优势

| 能力 | RAGFlow | RATH | 评价 |
|------|---------|------|------|
| **LLM原生** |  多模型支持 |  无 | RAGFlow为LLM时代设计 |
| **向量检索** |  ES向量搜索 |  无 | RAGFlow支持语义搜索 |
| **文档理解** |  DeepDoc深度解析 | ⚠️ 基础 | RAGFlow核心优势 |
| **异步处理** |  Celery |  同步 | RAGFlow支持大文件处理 |
| **缓存层** |  Redis |  无 | RAGFlow性能更好 |
| **多租户** |  内置 |  无 | RAGFlow企业级 |

### 6.2 可借鉴的设计

| 模块 | 可借鉴内容 | 适用场景 |
|------|-----------|---------|
| **DeepDoc** | 文档解析Pipeline | 任何需要文档理解的项目 |
| **RAG引擎** | 检索+生成流程 | 知识问答系统 |
| **LLM封装** | 多模型统一接口 | 需要支持多LLM的项目 |
| **异步任务** | Celery任务队列 | 耗时操作处理 |
| **向量检索** | ES向量搜索 | 语义搜索功能 |

---

## 七、总结

### 核心评价

RAGFlow的后端架构体现了**生产级LLM应用的最佳实践**：

1. **完整的技术栈**：Flask + SQLAlchemy + ES + Redis + Celery
2. **核心差异化能力**：DeepDoc深度文档理解
3. **LLM原生设计**：多模型支持，RAG流程完善
4. **企业级特性**：多租户、权限、审计

### 一句话总结

> **RAGFlow的后端比RATH成熟一个时代，特别是DeepDoc的文档理解能力和完整的RAG引擎，是现代化AI应用架构的典范。**

### 最值得学习的部分

```
1. deepdoc/ - 文档解析Pipeline设计
2. rag/ - RAG引擎实现
3. api/db/ - 数据库模型设计
4. celery任务 - 异步处理模式
```
