# RAGFlow RAG架构深度分析

**分析日期**: 2026-02-05  
**项目版本**: RAGFlow v0.23.1  
**核心定位**: 企业级多模态RAG引擎，支持GraphRAG、RAPTOR等高级检索技术

---

## 一、RAG架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAGFlow RAG 架构全景图                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  【文档处理 Pipeline】                                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Parser  │ │ Splitter │ │ Extractor│ │ Hierarch │ │ Embedder │        │
│  │  文档解析 │ │  分块    │ │ 信息提取 │ │ 合并优化 │ │ 向量化   │        │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘        │
│       │            │            │            │            │               │
│       ▼            ▼            ▼            ▼            ▼               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                     DeepDoc 深度文档理解                             │  │
│  │  • PDF/DOCX/Excel/Markdown/PPT 解析                                 │  │
│  │  • OCR（文字识别）                                                   │  │
│  │  • 版面分析（Layout Analysis）                                       │  │
│  │  • 表格提取（结构化）                                                │  │
│  │  • 图片理解（Vision LLM）                                            │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│       │                                                                   │
│       ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                     存储层                                           │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │  │
│  │  │ Elasticsearch   │  │    MySQL        │  │      Redis          │  │  │
│  │  │ • 向量索引      │  │ • 元数据        │  │ • 缓存              │  │  │
│  │  │ • 全文索引      │  │ • 文档信息      │  │ • 任务队列          │  │  │
│  │  │ • 混合检索      │  │ • 知识库配置    │  │ • 实时状态          │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│       ▲                                                                   │
│       │                                                                   │
│  【检索 Pipeline】                                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │  Query   │ │  Hybrid  │ │  Rerank  │ │  Citation│ │  Answer  │       │
│  │ Analysis │ │  Search  │ │          │ │ Insert   │ │ Gen      │       │
│  │ 查询分析 │ │ 混合检索 │ │ 重排序   │ │ 引用插入 │ │ 答案生成 │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                                              │
│  【高级RAG技术】                                                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐   │
│  │   GraphRAG      │  │    RAPTOR       │  │  Advanced RAG           │   │
│  │   知识图谱检索  │  │  递归摘要树     │  │  • Query分解            │   │
│  │   • 实体抽取    │  │  检索           │  │  • Multi-Query          │   │
│  │   • 关系构建    │  │  • 层级摘要     │  │  • Step-back            │   │
│  │   • 社区摘要    │  │  • 树形检索     │  │  • HyDE                 │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、文档处理 Pipeline（rag/flow/）

### 2.1 分阶段处理架构

```python
# rag/flow/pipeline.py 简化分析

class RAGFlowPipeline:
    """
    RAG文档处理Pipeline
    
    阶段：
    1. Parser - 文档解析
    2. Splitter - 智能分块
    3. Extractor - 信息提取
    4. Hierarchical Merger - 层级合并
    5. Embedder - 向量化
    """
    
    def __init__(self, parser_config: dict):
        self.parser = get_parser(parser_config)
        self.splitter = get_splitter(parser_config)
        self.extractor = get_extractor(parser_config)
        self.merger = HierarchicalMerger(parser_config)
        self.embedder = get_embedder(parser_config)
    
    async def process(self, document: bytes, callback=None) -> List[Chunk]:
        """处理文档"""
        
        # Step 1: 解析文档
        sections, tables = self.parser.parse(document, callback=callback)
        # sections: [{"text": "...", "page": 1, "bbox": {...}}, ...]
        # tables: [{"cells": [...], "page": 1}, ...]
        
        # Step 2: 智能分块
        chunks = self.splitter.split(sections, tables)
        # 策略：语义完整段落 + 重叠窗口
        
        # Step 3: 信息提取
        metadata = self.extractor.extract(chunks)
        # 提取：关键词、摘要、标题、实体等
        
        # Step 4: 层级合并（小chunk合并为大chunk）
        chunks = self.merger.merge(chunks)
        # 父子层级关系，支持不同粒度的检索
        
        # Step 5: 向量化
        embeddings = await self.embedder.embed([c.text for c in chunks])
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb
        
        return chunks
```

### 2.2 多Parser策略（rag/app/）

```python
# 根据文档类型选择不同Parser

FACTORY = {
    "general": naive,              # 通用文档
    ParserType.PAPER.value: paper, # 学术论文（保留引用、公式）
    ParserType.BOOK.value: book,   # 图书（目录结构）
    ParserType.PRESENTATION.value: presentation,  # PPT
    ParserType.MANUAL.value: manual,              # 产品手册
    ParserType.LAWS.value: laws,   # 法律法规（条款结构）
    ParserType.QA.value: qa,       # QA对格式
    ParserType.TABLE.value: table, # 表格密集型
    ParserType.RESUME.value: resume,# 简历
    ParserType.PICTURE.value: picture,  # 图片（OCR）
    ParserType.AUDIO.value: audio,     # 音频（ASR）
    ParserType.EMAIL.value: email,     # 邮件
}

# 示例：学术论文Parser（rag/app/paper.py）
class PaperParser:
    """学术论文专用解析器"""
    
    def parse(self, file_bytes):
        # 1. 识别论文结构
        # - 标题、作者、摘要
        # - 引言、方法、实验、结论
        # - 参考文献
        
        # 2. 特殊处理
        # - LaTeX公式转换
        # - 表格转为结构化数据
        # - 图表OCR识别
        
        # 3. 保留引用关系
        # - 引用标注 [1], [2]
        # - 参考文献列表对应
        
        return sections


# 示例：法律文档Parser（rag/app/laws.py）
class LawsParser:
    """法律法规专用解析器"""
    
    def parse(self, file_bytes):
        # 识别法律结构
        # 第一章 → 第一节 → 第一条 → （一）→ 1.
        
        sections = []
        for match in re.finditer(r'(第[一二三四五六七八九十]+章)', text):
            sections.append({
                "type": "chapter",
                "title": match.group(),
                "content": extract_chapter_content(match)
            })
        
        return sections
```

### 2.3 智能分块策略（rag/flow/splitter/）

```python
# rag/flow/splitter/splitter.py

class SmartSplitter:
    """
    智能分块器
    
    策略：
    1. 语义完整性：按段落、句子边界分块
    2. 长度控制：chunk_size（默认512 tokens）
    3. 重叠窗口：overlap（保证上下文连续性）
    4. 特殊结构：表格、列表整体保留
    """
    
    def split(self, sections: list, chunk_size: int = 512, overlap: int = 50):
        chunks = []
        
        for section in sections:
            text = section["text"]
            
            # 如果文本较短，直接作为一个chunk
            if len(text) < chunk_size:
                chunks.append(Chunk(
                    text=text,
                    page=section["page"],
                    bbox=section["bbox"]
                ))
                continue
            
            # 长文本分块
            sentences = self.split_to_sentences(text)
            current_chunk = []
            current_size = 0
            
            for sentence in sentences:
                sentence_size = len(sentence)
                
                if current_size + sentence_size > chunk_size and current_chunk:
                    # 保存当前chunk
                    chunks.append(self.create_chunk(current_chunk, section))
                    
                    # 重叠窗口：保留最后一部分
                    overlap_text = self.get_overlap_text(current_chunk, overlap)
                    current_chunk = [overlap_text, sentence]
                    current_size = len(overlap_text) + sentence_size
                else:
                    current_chunk.append(sentence)
                    current_size += sentence_size
            
            # 保存最后一个chunk
            if current_chunk:
                chunks.append(self.create_chunk(current_chunk, section))
        
        return chunks
```

---

## 三、存储层设计

### 3.1 Elasticsearch 索引结构

```json
// RAGFlow ES索引设计（多模态支持）
{
  "mappings": {
    "properties": {
      // 基础字段
      "id": {"type": "keyword"},
      "kb_id": {"type": "keyword"},
      "doc_id": {"type": "keyword"},
      "docnm_kwd": {"type": "keyword"},  // 文档名
      
      // 文本内容（全文检索）
      "content_with_weight": {"type": "text", "analyzer": "standard"},
      "content_ltks": {"type": "text", "analyzer": "whitespace"},  // 分词后
      "title_tks": {"type": "text"},
      
      // 向量字段（多维度支持）
      "q_768_vec": {  // 768维向量
        "type": "dense_vector",
        "dims": 768,
        "index": true,
        "similarity": "cosine"
      },
      "q_1024_vec": {  // 1024维向量（不同模型）
        "type": "dense_vector",
        "dims": 1024,
        "index": true,
        "similarity": "cosine"
      },
      
      // 元数据
      "page_num_int": {"type": "integer"},
      "position_int": {"type": "integer"},  // 文档内位置
      "top_int": {"type": "integer"},       // 排序权重
      "create_timestamp_flt": {"type": "float"},
      
      // 标签系统
      "important_kwd": {"type": "keyword"},  // 关键词
      "tag_kwd": {"type": "keyword"},        // 标签
      "knowledge_graph_kwd": {"type": "keyword"},  // 知识图谱类型
      
      // RAPTOR层级
      "level_int": {"type": "integer"},      // 摘要层级
      "parent_id": {"type": "keyword"},      // 父节点ID
      
      // 图片（多模态）
      "img_id": {"type": "keyword"},         // 图片ID
      "content_with_weight_sm": {"type": "text"},  // 图片描述（视觉模型生成）
      
      // GraphRAG
      "entity_kwd": {"type": "keyword"},     // 实体
      "from_entity_kwd": {"type": "keyword"},
      "to_entity_kwd": {"type": "keyword"},
      
      // PageRank权重
      "pagerank_flt": {"type": "float"}
    }
  }
}
```

### 3.2 混合检索实现

```python
# rag/nlp/search.py

class Dealer:
    """
    RAG检索核心
    
    支持：
    1. 全文检索（BM25）
    2. 向量检索（Cosine Similarity）
    3. 混合检索（RRF融合）
    """
    
    async def search(self, req, idx_names, kb_ids, emb_mdl=None):
        """
        混合检索
        
        Args:
            req: 查询请求
            idx_names: 索引名
            kb_ids: 知识库ID列表
            emb_mdl: Embedding模型
        """
        qst = req.get("question", "")
        topk = int(req.get("topk", 1024))
        
        # 1. 全文检索（关键词匹配）
        matchText, keywords = self.qryr.question(qst, min_match=0.3)
        # qryr.question: 查询分析 + 关键词提取
        
        if emb_mdl is None:
            # 仅全文检索
            matchExprs = [matchText]
            res = self.dataStore.search(
                src, highlightFields, filters, matchExprs, 
                orderBy, offset, limit, idx_names, kb_ids
            )
        else:
            # 2. 向量检索
            matchDense = await self.get_vector(
                qst, emb_mdl, topk, req.get("similarity", 0.1)
            )
            # matchDense: 查询向量 + 相似度计算
            
            # 3. RRF混合融合
            # RRF (Reciprocal Rank Fusion)
            # score = Σ(1 / (k + rank)) 
            # k=60 经验值
            fusionExpr = FusionExpr(
                "weighted_sum", 
                topk, 
                {"weights": "0.05,0.95"}  # 文本:向量 = 5%:95%
            )
            
            matchExprs = [matchText, matchDense, fusionExpr]
            res = self.dataStore.search(
                src, highlightFields, filters, matchExprs,
                orderBy, offset, limit, idx_names, kb_ids
            )
        
        return self.SearchResult(
            total=self.dataStore.get_total(res),
            ids=self.dataStore.get_doc_ids(res),
            keywords=keywords,
            highlight=self.dataStore.get_highlight(res, keywords),
            field=self.dataStore.get_fields(res)
        )
```

---

## 四、高级RAG技术

### 4.1 GraphRAG（rag/graphrag/）

```python
# GraphRAG 实现流程

class GraphRAG:
    """
    基于知识图谱的RAG
    
    流程：
    1. 实体抽取（Entity Extraction）
    2. 关系构建（Relation Building）
    3. 社区摘要（Community Summarization）
    4. 图谱检索（Graph-based Retrieval）
    """
    
    async def build_knowledge_graph(self, chunks: list):
        """构建知识图谱"""
        
        # Step 1: 实体抽取
        entities = []
        for chunk in chunks:
            # 使用LLM抽取实体
            prompt = f"""
            从以下文本中抽取实体（人名、地名、组织、概念等）：
            {chunk.text}
            
            输出格式JSON：
            {{"entities": [{{"name": "...", "type": "...", "description": "..."}}]}}
            """
            result = await self.llm.generate(prompt)
            chunk_entities = json.loads(result)
            entities.extend(chunk_entities["entities"])
        
        # Step 2: 实体消歧（Entity Resolution）
        # 合并相同实体（不同名字指代同一实体）
        resolved_entities = self.entity_resolution(entities)
        
        # Step 3: 关系抽取
        relations = []
        for chunk in chunks:
            prompt = f"""
            识别文本中的实体关系：
            {chunk.text}
            
            已知实体：{[e.name for e in resolved_entities]}
            
            输出关系三元组：(实体1, 关系, 实体2)
            """
            result = await self.llm.generate(prompt)
            relations.extend(parse_relations(result))
        
        # Step 4: 构建图
        graph = nx.Graph()
        for entity in resolved_entities:
            graph.add_node(entity.name, **entity.dict())
        for rel in relations:
            graph.add_edge(rel.from_entity, rel.to_entity, relation=rel.type)
        
        # Step 5: 社区摘要（Leiden算法）
        communities = detect_communities(graph)
        for community in communities:
            summary = await self.summarize_community(community)
            community.summary = summary
        
        return graph, communities
    
    async def search(self, query: str, graph, communities):
        """图谱检索"""
        
        # 1. 识别查询中的实体
        query_entities = extract_entities(query)
        
        # 2. 图谱遍历（多跳推理）
        relevant_nodes = set()
        for entity in query_entities:
            # 单跳邻居
            neighbors = graph.neighbors(entity)
            relevant_nodes.update(neighbors)
            
            # 两跳邻居
            for neighbor in neighbors:
                relevant_nodes.update(graph.neighbors(neighbor))
        
        # 3. 社区匹配
        relevant_communities = [
            c for c in communities
            if any(e in c.nodes for e in query_entities)
        ]
        
        # 4. 生成回答（结合社区摘要）
        context = {
            "entities": [graph.nodes[n] for n in relevant_nodes],
            "communities": [c.summary for c in relevant_communities]
        }
        
        answer = await self.generate_answer(query, context)
        return answer
```

### 4.2 RAPTOR（rag/raptor.py）

```python
# RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval
# 递归摘要树检索

class Raptor:
    """
    RAPTOR实现
    
    思想：
    1. 将文本分块向量化
    2. 聚类相似的chunk
    3. 为每个聚类生成摘要
    4. 递归向上摘要，形成树形结构
    5. 检索时从树的不同层级获取信息
    """
    
    async def build_tree(self, chunks: list, embedding_model, llm):
        """构建RAPTOR树"""
        
        # Level 0: 原始chunks（叶子节点）
        level_0 = chunks
        
        # 向上递归摘要
        current_level = level_0
        tree_levels = [current_level]
        
        while len(current_level) > 1:
            # 1. 向量化
            embeddings = await embedding_model.embed([c.text for c in current_level])
            
            # 2. 聚类（GMM - Gaussian Mixture Model）
            clusters = self.cluster_embeddings(embeddings, n_clusters=len(current_level)//2)
            
            # 3. 为每个聚类生成摘要
            next_level = []
            for cluster in clusters:
                cluster_texts = [current_level[i].text for i in cluster]
                
                # 摘要生成
                prompt = f"""
                总结以下文本的主要内容：
                {'\n'.join(cluster_texts)}
                
                生成简洁的摘要，保留关键信息。
                """
                summary = await llm.generate(prompt)
                
                next_level.append(Chunk(
                    text=summary,
                    level=len(tree_levels),
                    children=[current_level[i] for i in cluster]
                ))
            
            tree_levels.append(next_level)
            current_level = next_level
        
        return tree_levels
    
    def retrieve(self, query: str, tree_levels: list, embedding_model, top_k=5):
        """树形检索"""
        
        query_embedding = embedding_model.embed(query)
        
        # 从每一层检索最相关的节点
        results = []
        for level in tree_levels:
            level_embeddings = [c.embedding for c in level]
            similarities = cosine_similarity([query_embedding], level_embeddings)[0]
            
            # 取每层top-k
            top_indices = np.argsort(similarities)[-top_k:]
            results.extend([level[i] for i in top_indices])
        
        return results
```

---

## 五、与RATH RAG对比

| 特性 | RAGFlow RAG | RATH |
|------|-------------|------|
| **多Parser** |  12+文档类型专用解析器 | ⚠️ 基础通用解析 |
| **深度文档理解** |  DeepDoc（OCR+版面） |  基础文本提取 |
| **分块策略** |  智能语义分块+层级合并 | ⚠️ 基础分块 |
| **向量存储** |  Elasticsearch（混合检索） |  无向量检索 |
| **全文检索** |  ES全文索引 |  无 |
| **混合检索** |  文本+向量融合 |  不支持 |
| **GraphRAG** |  知识图谱检索 |  无 |
| **RAPTOR** |  递归摘要树 |  无 |
| **多模态** |  图片OCR+理解 |  不支持 |
| **引用溯源** |  自动生成引用 |  无 |

---

## 六、总结

### 核心优势

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      RAGFlow RAG核心优势                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. 文档理解深度最强                                                      │
│     - 12+专用Parser（论文/法律/简历等）                                   │
│     - DeepDoc：OCR + 版面分析 + 表格结构化                                │
│                                                                          │
│  2. 检索技术最先进                                                        │
│     - 混合检索（BM25 + 向量 + RRF融合）                                   │
│     - GraphRAG：知识图谱增强                                              │
│     - RAPTOR：层级摘要树                                                  │
│                                                                          │
│  3. 多模态支持                                                            │
│     - 文本 + 图片 + 表格统一处理                                          │
│     - 视觉模型理解图片内容                                                │
│                                                                          │
│  4. 工程化完善                                                            │
│     - 异步Pipeline（Celery）                                              │
│     - 可扩展架构（组件化）                                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 一句话总结

> **RAGFlow的RAG架构是当前开源领域最先进的实现之一，其DeepDoc文档理解、混合检索、GraphRAG、RAPTOR等技术组合，使其在企业级知识库场景具有极强的竞争力。**

### 适用场景

| 场景 | 推荐度 | 理由 |
|------|--------|------|
| 多格式文档知识库 | ⭐⭐⭐⭐⭐ | 12+文档类型专用解析 |
| 学术论文检索 | ⭐⭐⭐⭐⭐ | Paper Parser保留公式引用 |
| 法律法规查询 | ⭐⭐⭐⭐⭐ | Laws Parser识别条款结构 |
| 需要引用溯源 | ⭐⭐⭐⭐⭐ | 自动生成引用标注 |
| 图片密集型文档 | ⭐⭐⭐⭐⭐ | 视觉模型理解图片 |
| 复杂多跳推理 | ⭐⭐⭐⭐⭐ | GraphRAG支持 |
| 简单文本检索 | ⭐⭐⭐ | 功能过剩，配置复杂 |
