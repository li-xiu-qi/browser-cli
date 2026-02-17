# RAGFlow 多租户隔离架构深度分析

**分析日期**: 2026-02-05  
**项目版本**: RAGFlow v0.23.1  
**核心结论**: **逻辑隔离为主（数据层tenant_id字段），结合物理索引隔离，权限控制到行级别**

---

## 一、多租户架构概览

### 1.1 架构设计图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        RAGFlow 多租户架构                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  【租户模型】                                                                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Tenant（租户）                                                      │   │
│  │  ├─ id: 租户唯一标识                                                 │   │
│  │  ├─ name: 租户名称                                                   │   │
│  │  ├─ llm_id: 默认LLM模型                                              │   │
│  │  ├─ embd_id: 默认Embedding模型                                       │   │
│  │  ├─ rerank_id: 默认Rerank模型                                        │   │
│  │  ├─ asr_id: 默认语音识别模型                                          │   │
│  │  ├─ img2txt_id: 默认图像理解模型                                      │   │
│  │  └─ tts_id: 默认语音合成模型                                          │   │
│  │                                                                     │   │
│  │  UserTenant（用户-租户关联）                                         │   │
│  │  ├─ user_id: 用户ID                                                  │   │
│  │  ├─ tenant_id: 租户ID                                                │   │
│  │  └─ role: OWNER（拥有者）/ NORMAL（成员）                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  【数据隔离层级】                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  L1: 逻辑隔离（数据层）                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  所有业务表包含 tenant_id 字段                                 │   │   │
│  │  │  查询时自动添加 tenant_id = ? 条件                            │   │   │
│  │  │                                                              │   │   │
│  │  │  示例：SELECT * FROM knowledgebase                           │   │   │
│  │  │          WHERE tenant_id = 'tenant_123'                      │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  L2: 索引隔离（ES/Infinity层）                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  ES索引名：ragflow_{tenant_id}                                │   │   │
│  │  │  或：ragflow_{tenant_id}_{kb_id}（Infinity多表模式）          │   │   │
│  │  │                                                              │   │   │
│  │  │  物理上：一个租户一个索引                                     │   │   │
│  │  │  查询时：指定索引名，自动过滤                                 │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  L3: 权限控制（应用层）                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  • 拥有者(OWNER)：完整CRUD权限                                │   │   │
│  │  │  • 成员(NORMAL)：只读或受限访问                               │   │   │
│  │  │  • 团队共享：permission = 'team' 的数据可被成员访问           │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、租户模型设计

### 2.1 核心模型定义

```python
# api/db/db_models.py

class Tenant(DataBaseModel):
    """
    租户表 - 每个用户注册时自动创建
    """
    id = CharField(max_length=32, primary_key=True)  # 租户ID（等于创建者user_id）
    name = CharField(max_length=100, null=True, index=True)  # 租户名称
    
    # 各类型默认模型配置
    llm_id = CharField(max_length=128, null=False, default="gpt-4o", help_text="默认对话模型")
    embd_id = CharField(max_length=128, null=False, default="BAAI/bge-large-zh-v1.5", help_text="默认嵌入模型")
    rerank_id = CharField(max_length=128, null=False, default="BAAI/bge-reranker-v2-m3", help_text="默认重排序模型")
    asr_id = CharField(max_length=128, null=True, help_text="默认语音识别模型")
    img2txt_id = CharField(max_length=128, null=True, help_text="默认图像理解模型")
    tts_id = CharField(max_length=256, null=True, help_text="默认语音合成模型")
    
    class Meta:
        db_table = "tenant"


class UserTenant(DataBaseModel):
    """
    用户-租户关联表 - 支持多租户成员关系
    """
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=255, null=False, index=True)      # 用户ID
    tenant_id = CharField(max_length=32, null=False, index=True)     # 租户ID
    role = CharField(max_length=32, null=False, help_text="UserTenantRole", index=True)
    # role: OWNER（拥有者）/ NORMAL（普通成员）
    status = CharField(max_length=32, null=False, default=StatusEnum.VALID.value)
    
    class Meta:
        db_table = "user_tenant"


class TenantLLM(DataBaseModel):
    """
    租户LLM配置表 - 每个租户独立的模型配置
    """
    tenant_id = CharField(max_length=32, null=False, index=True)
    llm_factory = CharField(max_length=32, null=False, help_text="厂商")  # OpenAI/Azure等
    llm_name = CharField(max_length=128, null=False, help_text="模型名")  # gpt-4o等
    model_type = CharField(max_length=32, null=False, help_text="模型类型")  # CHAT/EMBEDDING/RERANK
    api_key = CharField(max_length=2048, null=True, help_text="API KEY")
    base_url = CharField(max_length=255, null=True, help_text="自定义Base URL")
    max_tokens = IntegerField(default=8192, help_text="最大Token数")
    used_tokens = IntegerField(default=0, help_text="已使用Token数（计费）")
    
    class Meta:
        db_table = "tenant_llm"
        primary_key = CompositeKey("tenant_id", "llm_factory", "llm_name")


class TenantLangfuse(DataBaseModel):
    """
    租户Langfuse配置（可观测性）
    """
    tenant_id = CharField(max_length=32, null=False, primary_key=True)
    host = CharField(max_length=255, null=False, help_text="Langfuse服务器地址")
    public_key = CharField(max_length=255, null=False)
    secret_key = CharField(max_length=255, null=False)
    
    class Meta:
        db_table = "tenant_langfuse"
```

### 2.2 业务表的租户字段

```python
# 所有业务表都包含 tenant_id 字段

class KnowledgeBase(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    tenant_id = CharField(max_length=32, null=False, index=True)  # ★ 租户隔离字段
    name = CharField(max_length=128, null=False, help_text="知识库名称")
    description = TextField(null=True, help_text="描述")
    embd_id = CharField(max_length=128, null=False, help_text="使用的嵌入模型")
    permission = CharField(max_length=32, null=False, default="me", help_text="me|team")
    # permission: 'me'私有, 'team'团队共享
    
    class Meta:
        db_table = "knowledgebase"


class Document(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    kb_id = CharField(max_length=32, null=False, index=True)  # 关联知识库
    # 通过kb_id -> Knowledgebase.tenant_id 间接关联租户
    name = CharField(max_length=255, null=False, help_text="文档名")
    location = CharField(max_length=512, null=True, help_text="存储路径")
    size = IntegerField(default=0, help_text="文件大小")
    type = CharField(max_length=32, null=False, help_text="文档类型")
    status = CharField(max_length=16, default=StatusEnum.VALID.value)
    
    class Meta:
        db_table = "document"


class UserCanvas(DataBaseModel):
    """Agent/工作流"""
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=255, null=False, index=True)  # 创建者（即tenant_id）
    title = CharField(max_length=255, null=True, help_text="标题")
    permission = CharField(max_length=16, null=False, default="me", help_text="me|team")
    canvas_type = CharField(max_length=32, null=True)
    dsl = JSONField(null=True, default={})  # 工作流定义
    
    class Meta:
        db_table = "user_canvas"


class File(DataBaseModel):
    """文件管理"""
    id = CharField(max_length=32, primary_key=True)
    parent_id = CharField(max_length=32, null=False, index=True)
    tenant_id = CharField(max_length=32, null=False, index=True)  # ★ 租户隔离
    created_by = CharField(max_length=32, null=False, index=True)
    name = CharField(max_length=255, null=False, help_text="文件名")
    location = CharField(max_length=255, null=False, help_text="存储路径")
    size = IntegerField(default=0, help_text="文件大小")
    type = CharField(max_length=32, null=False, help_text="文件类型")
    
    class Meta:
        db_table = "file"
```

---

## 三、数据隔离实现机制

### 3.1 逻辑隔离（数据层）

```python
# api/db/services/knowledgebase_service.py

class KnowledgebaseService(CommonService):
    model = Knowledgebase
    
    @classmethod
    def get_list(cls, joined_tenant_ids, user_id, page_number, items_per_page, 
                 orderby, desc, keywords, parser_id=None):
        """
        获取知识库列表 - 带租户隔离
        
        Args:
            joined_tenant_ids: 用户已加入的租户ID列表
            user_id: 当前用户ID
        """
        fields = [
            cls.model.id,
            cls.model.name,
            cls.model.tenant_id,  # 返回租户ID用于前端显示
            cls.model.permission,
            User.avatar.alias('tenant_avatar'),  # 关联用户表获取头像
        ]
        
        # ★ 核心查询条件：租户隔离 + 权限控制
        kbs = cls.model.select(*fields).join(User, on=(cls.model.tenant_id == User.id)).where(
            # 条件1：用户是租户成员且知识库是团队共享
            ((cls.model.tenant_id.in_(joined_tenant_ids) & 
              (cls.model.permission == TenantPermission.TEAM.value)) | 
             # 条件2：知识库属于用户自己（私人）
             (cls.model.tenant_id == user_id))
            & (cls.model.status == StatusEnum.VALID.value)
        )
        
        # 分页
        kbs = kbs.order_by(cls.model.create_time.desc()).paginate(
            page_number, items_per_page
        )
        
        return kbs
    
    @classmethod
    def get_by_id(cls, kb_id, tenant_id):
        """
        根据ID获取知识库 - 严格租户隔离
        
        防止越权：确保只能访问自己租户的知识库
        """
        return cls.model.select().where(
            (cls.model.id == kb_id) & 
            (cls.model.tenant_id == tenant_id) &  # ★ 租户隔离
            (cls.model.status == StatusEnum.VALID.value)
        ).first()
```

### 3.2 物理索引隔离（检索层）

```python
# rag/nlp/search.py

def index_name(tenant_id: str) -> str:
    """
    生成ES索引名 - 租户隔离
    
    格式: ragflow_{tenant_id}
    示例: ragflow_tenant_abc123
    """
    return f"ragflow_{tenant_id}"


class Dealer:
    """检索核心类"""
    
    async def search(self, req, idx_names: str | list[str], 
                     kb_ids: list[str], emb_mdl=None):
        """
        混合检索
        
        Args:
            req: 查询请求
            idx_names: 索引名（通常是ragflow_{tenant_id}）
            kb_ids: 知识库ID列表（进一步过滤）
        """
        qst = req.get("question", "")
        
        # 构建过滤器
        filters = self.get_filters(req)
        # filters示例: {"kb_id": ["kb_1", "kb_2"], "tenant_id": "tenant_123"}
        
        # 全文检索
        matchText, keywords = self.qryr.question(qst, min_match=0.3)
        
        # 向量检索
        matchDense = await self.get_vector(qst, emb_mdl, topk=1024)
        
        # RRF融合
        fusionExpr = FusionExpr("weighted_sum", topk, {"weights": "0.05,0.95"})
        
        # 执行搜索 - 指定租户索引
        res = self.dataStore.search(
            src_fields,           # 返回字段
            highlightFields,      # 高亮字段
            filters,              # 过滤条件（包含tenant_id）
            [matchText, matchDense, fusionExpr],  # 匹配表达式
            orderBy, offset, limit,
            idx_names,            # ★ 租户隔离的索引名
            kb_ids                # 知识库过滤
        )
        
        return self.SearchResult(
            total=self.dataStore.get_total(res),
            ids=self.dataStore.get_doc_ids(res),
            keywords=keywords
        )


# 使用示例
# 租户A搜索自己的文档
dealer = Dealer(es_client)
result = await dealer.search(
    req={"question": "什么是RAG?"},
    idx_names="ragflow_tenant_a",  # ★ 租户A的专属索引
    kb_ids=["kb_a1", "kb_a2"],
    emb_mdl=embedding_model
)
```

### 3.3 文件存储隔离

```python
# 文件存储路径设计

# MinIO对象存储路径结构
# {bucket}/{tenant_id}/{file_type}/{date}/{file_id}

# 示例：
# ragflow-bucket/tenant_123/documents/2024-11-15/doc_abc123.pdf
# ragflow-bucket/tenant_123/images/2024-11-15/img_def456.png
# ragflow-bucket/tenant_456/documents/2024-11-15/doc_xyz789.pdf

# 代码实现
class FileService:
    @classmethod
    def get_storage_path(cls, tenant_id: str, file_id: str, file_type: str) -> str:
        """生成存储路径 - 租户隔离"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        return f"{tenant_id}/{file_type}/{date_str}/{file_id}"
    
    @classmethod
    def upload_file(cls, tenant_id: str, file_bytes: bytes, 
                    filename: str, file_type: str) -> str:
        """上传文件"""
        file_id = get_uuid()
        path = cls.get_storage_path(tenant_id, file_id, file_type)
        
        # 上传到MinIO
        minio_client.put_object(
            bucket_name="ragflow",
            object_name=path,
            data=file_bytes,
            length=len(file_bytes)
        )
        
        return file_id
```

---

## 四、权限控制系统

### 4.1 角色权限模型

```python
# api/db/db_models.py

class UserTenantRole(Enum):
    """用户-租户角色"""
    OWNER = "owner"    # 拥有者：完整CRUD权限
    NORMAL = "normal"  # 普通成员：只读或受限访问


class TenantPermission(Enum):
    """数据权限"""
    ME = "me"      # 私有：只有创建者可访问
    TEAM = "team"  # 团队：租户成员可访问
```

### 4.2 权限检查实现

```python
# api/db/services/canvas_service.py

class UserCanvasService(CommonService):
    model = UserCanvas
    
    @classmethod
    def accessible(cls, canvas_id, tenant_id):
        """
        检查用户是否有权访问Agent/工作流
        
        逻辑：
        1. 创建者本人有权限
        2. 如果是team权限，租户成员有权限
        3. 如果是me权限，只有创建者有权限
        """
        from api.db.services.user_service import UserTenantService
        
        # 获取用户加入的所有租户
        user_tenants = UserTenantService.query(user_id=tenant_id)
        joined_tenant_ids = [t.tenant_id for t in user_tenants]
        
        # 查询Agent
        cvs = cls.model.select().where(
            (cls.model.id == canvas_id) &
            (
                # 条件1：用户是创建者
                (cls.model.user_id == tenant_id) |
                # 条件2：Agent是团队共享且用户在租户中
                ((cls.model.user_id.in_(joined_tenant_ids)) & 
                 (cls.model.permission == TenantPermission.TEAM.value))
            )
        ).first()
        
        return cvs is not None


# API层权限检查示例
@canvas_blueprint.route('/<canvas_id>', methods=['GET'])
def get_canvas(canvas_id):
    """获取Agent详情"""
    current_user = get_current_user()
    
    # 权限检查
    if not UserCanvasService.accessible(canvas_id, current_user.id):
        return jsonify({"error": "Access denied"}), 403
    
    canvas = UserCanvasService.get_by_id(canvas_id)
    return jsonify(canvas.to_dict())
```

### 4.3 API鉴权中间件

```python
# api/utils/api_utils.py

def token_required(func):
    """JWT Token鉴权装饰器"""
    @wraps(func)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"error": "Token required"}), 401
        
        try:
            # 解码Token
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            user_id = payload['user_id']
            tenant_id = payload.get('tenant_id', user_id)  # 默认租户
            
            # 设置当前用户
            g.current_user = UserService.get_by_id(user_id)
            g.tenant_id = tenant_id
            
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        
        return func(*args, **kwargs)
    return decorated_function


# 使用示例
@chat_blueprint.route('/completion', methods=['POST'])
@token_required
def chat_completion():
    """对话接口 - 自动鉴权"""
    data = request.json
    tenant_id = g.tenant_id  # 从Token获取当前租户
    
    # 所有后续操作都基于tenant_id进行隔离
    result = DialogService.completion(
        tenant_id=tenant_id,
        dialog_id=data['dialog_id'],
        question=data['question']
    )
    
    return jsonify(result)
```

---

## 五、租户资源限制

### 5.1 资源配额控制

```python
# api/db/db_models.py

class Tenant(DataBaseModel):
    # ... 基础字段 ...
    
    # 资源配额限制
    max_knowledgebases = IntegerField(default=10, help_text="最大知识库数量")
    max_documents = IntegerField(default=1000, help_text="最大文档数量")
    max_users = IntegerField(default=5, help_text="最大成员数量")
    max_storage_bytes = BigIntegerField(default=10*1024*1024*1024, help_text="最大存储空间(10GB)")
    
    # 用量统计
    used_storage_bytes = BigIntegerField(default=0, help_text="已用存储空间")
    used_tokens = IntegerField(default=0, help_text="已用LLM Token数")


# 资源检查服务
class TenantQuotaService:
    @classmethod
    def check_knowledgebase_quota(cls, tenant_id: str) -> Tuple[bool, str]:
        """检查知识库配额"""
        tenant = TenantService.get_by_id(tenant_id)
        current_count = KnowledgebaseService.count_by_tenant(tenant_id)
        
        if current_count >= tenant.max_knowledgebases:
            return False, f"Knowledgebase quota exceeded: {current_count}/{tenant.max_knowledgebases}"
        return True, "OK"
    
    @classmethod
    def check_storage_quota(cls, tenant_id: str, file_size: int) -> Tuple[bool, str]:
        """检查存储配额"""
        tenant = TenantService.get_by_id(tenant_id)
        
        if tenant.used_storage_bytes + file_size > tenant.max_storage_bytes:
            return False, f"Storage quota exceeded"
        return True, "OK"
    
    @classmethod
    def update_storage_usage(cls, tenant_id: str, delta_bytes: int):
        """更新存储用量"""
        Tenant.update(
            used_storage_bytes=Tenant.used_storage_bytes + delta_bytes
        ).where(Tenant.id == tenant_id).execute()
```

### 5.2 用量计费追踪

```python
# api/db/services/tenant_llm_service.py

class TenantLLMService(CommonService):
    model = TenantLLM
    
    @classmethod
    def increase_usage(cls, tenant_id, llm_type, used_tokens, llm_name=None):
        """
        增加Token用量 - 用于计费
        
        每次LLM调用后更新用量
        """
        try:
            # 获取当前用量
            tenant_llm = cls.model.select().where(
                cls.model.tenant_id == tenant_id,
                cls.model.llm_name == llm_name,
                cls.model.model_type == llm_type
            ).first()
            
            if tenant_llm:
                # 更新用量
                cls.model.update(
                    used_tokens=cls.model.used_tokens + used_tokens
                ).where(
                    cls.model.tenant_id == tenant_id,
                    cls.model.llm_name == llm_name
                ).execute()
                return True
        except Exception as e:
            logging.error(f"Failed to update usage: {e}")
            return False


# LLM调用时自动计费
class LLMBundle:
    def __init__(self, tenant_id, llm_type, llm_name=None, lang="Chinese", **kwargs):
        self.tenant_id = tenant_id
        self.llm_type = llm_type
        self.mdl = TenantLLMService.model_instance(tenant_id, llm_type, llm_name, lang, **kwargs)
    
    async def chat(self, system, history, gen_conf):
        """对话 - 自动计费"""
        response = await self.mdl.chat(system, history, gen_conf)
        
        # 计算Token用量
        used_tokens = response.get("usage", {}).get("total_tokens", 0)
        
        # 更新用量（异步）
        if used_tokens:
            TenantLLMService.increase_usage(
                self.tenant_id, 
                self.llm_type, 
                used_tokens,
                self.llm_name
            )
        
        return response
```

---

## 六、与成熟SaaS多租户对比

| 特性 | RAGFlow | 成熟SaaS（如Salesforce） |
|------|---------|------------------------|
| **隔离级别** | 逻辑隔离（行级） | 物理隔离/Schema隔离 |
| **数据隔离** |  tenant_id字段 |  Schema/Database级 |
| **索引隔离** |  ES索引分离 |  完全物理分离 |
| **权限控制** |  角色+资源级 |  字段级ACL |
| **资源配额** | ⚠️ 基础配额 |  细粒度配额 |
| **计费系统** | ⚠️ Token计数 |  完整计费引擎 |
| **租户自定义** |  无 |  字段/流程自定义 |
| **数据导出** |  无 |  租户数据导出 |

---

## 七、总结

### 一句话结论

> **RAGFlow采用"逻辑隔离为主，物理隔离为辅"的多租户架构，通过tenant_id字段实现行级数据隔离，ES索引物理分离，结合角色权限控制，满足基础多租户需求，但相比企业级SaaS在细粒度控制和定制化方面仍有差距。**

### 适用场景

| 场景 | 适合度 | 说明 |
|------|--------|------|
| 企业内部多部门 | ⭐⭐⭐⭐⭐ | 同一公司不同团队 |
| 小企业SaaS | ⭐⭐⭐⭐ | 租户数量<1000 |
| 大规模SaaS | ⭐⭐⭐ | 需增强隔离和配额 |
| 强合规要求 | ⭐⭐ | 需物理完全隔离 |

### 生产建议

1. **数据备份**：按租户维度备份（tenant_id过滤）
2. **监控告警**：租户级用量监控
3. **性能优化**：tenant_id字段加索引
4. **安全审计**：记录租户操作日志
