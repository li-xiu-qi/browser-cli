# RAGFlow 架构改造 Roadmap

**目标**: 将 RAGFlow 从「模块化单体」改造为「可水平扩展的企业级架构」
**当前上限**: ~5000用户  
**目标上限**: ~100万用户  
**预计周期**: 6-12个月（分4个阶段）

---

## 一、改造总览

### 1.1 架构演进路线

```
当前（模块化单体）           Phase 1（数据库优化）         Phase 2（服务拆分）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────┐              ┌─────────────┐              ┌─────────────┐
│  Web Server │              │  Web Server │              │   API GW    │
│  (单体)     │              │  (单体)     │              │   (Kong/    │
└──────┬──────┘              └──────┬──────┘              │   Nginx)    │
       │                            │                    └──────┬──────┘
       │                            │                           │
       │                            │              ┌────────────┼────────────┐
       │                            │              ▼            ▼            ▼
       ▼                            ▼           ┌────┐     ┌────┐     ┌────┐
┌─────────────┐              ┌─────────────┐   │用户│     │知识库│    │对话│
│   MySQL     │              │   MySQL     │   │服务│     │服务│    │服务│
│  (单库单表) │      →       │ (读写分离)  │   └────┘     └────┘    └────┘
└─────────────┘              └─────────────┘
                                    │
                                    ▼
                              ┌─────────────┐
                              │  Redis集群  │
                              │  (缓存层)   │
                              └─────────────┘

Phase 3（数据分片）              Phase 4（云原生）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────┐              ┌─────────────────────────────────────────┐
│   API GW    │              │            Service Mesh (Istio)         │
└──────┬──────┘              │  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐   │
       │                     │  │用户│ │知识库│ │对话│ │检索│ │解析│   │
       │                     │  │服务│ │服务│ │服务│ │服务│ │服务│   │
  ┌────┴────┐                │  └────┘ └────┘ └────┘ └────┘ └────┘   │
  ▼         ▼                └─────────────────────────────────────────┘
┌────────┐ ┌────────┐                        │
│User DB │ │KB DB   │                        ▼
│(分片1) │ │(分片2) │              ┌─────────────────────┐
└────────┘ └────────┘              │  Kubernetes + Istio │
                                   │  • 自动扩缩容         │
                                   │  • 服务网格           │
                                   │  • 灰度发布           │
                                   └─────────────────────┘
```

### 1.2 改造阶段总览

| 阶段 | 目标 | 核心改动 | 预计工时 | 风险 |
|------|------|----------|----------|------|
| **Phase 1** | 数据库优化 | 读写分离 + 缓存层 + 连接池 | 2周 | 低 |
| **Phase 2** | 服务拆分 | Web层拆分为独立服务 | 6周 | 中 |
| **Phase 3** | 数据分片 | 分库分表 + 分布式ID | 8周 | 高 |
| **Phase 4** | 云原生 | Service Mesh + 自动化 | 4周 | 中 |
| **总计** | 企业级架构 | - | 20周(5个月) | - |

---

## 二、Phase 1: 数据库优化（第1-2周）

**目标**: 在不改动代码架构的前提下，将数据库能力提升5-10倍

### 2.1 读写分离

```python
# 改造前：单数据库连接
# api/db/db_models.py

database = PooledMySQLDatabase(
    'ragflow',
    host='mysql',
    user='root',
    password='password',
    max_connections=20
)


# 改造后：读写分离
# api/db/db_models.py

from common.db_router import DBRouter

# 主库（写）
master_db = PooledMySQLDatabase(
    'ragflow',
    host='mysql-master',
    max_connections=50
)

# 从库（读）- 多从库
slave_dbs = [
    PooledMySQLDatabase('ragflow', host='mysql-slave-1'),
    PooledMySQLDatabase('ragflow', host='mysql-slave-2'),
    PooledMySQLDatabase('ragflow', host='mysql-slave-3'),
]

class DBRouter:
    """数据库路由"""
    
    @staticmethod
    def get_db(operation='read'):
        if operation in ['write', 'insert', 'update', 'delete']:
            return master_db
        
        # 读操作负载均衡
        return random.choice(slave_dbs)


# Service层使用
class DocumentService:
    @classmethod
    def get_by_id(cls, doc_id):
        # 自动路由到从库
        db = DBRouter.get_db('read')
        return cls.model.select().where(cls.model.id == doc_id).switch(db).first()
    
    @classmethod
    def create(cls, **kwargs):
        # 自动路由到主库
        db = DBRouter.get_db('write')
        return cls.model.create(**kwargs)
```

### 2.2 引入缓存层

```python
# common/cache.py - 统一缓存接口

import redis
import json
from functools import wraps

class CacheManager:
    """多级缓存管理"""
    
    def __init__(self):
        # L1: 本地缓存 (Caffeine/similar)
        self.local_cache = {}
        
        # L2: Redis集群
        self.redis_cluster = redis.RedisCluster(
            startup_nodes=[
                {'host': 'redis-1', 'port': 6379},
                {'host': 'redis-2', 'port': 6379},
                {'host': 'redis-3', 'port': 6379},
            ]
        )
    
    def get(self, key, level='all'):
        """获取缓存"""
        # L1: 本地缓存
        if level in ['all', 'local']:
            if key in self.local_cache:
                return self.local_cache[key]
        
        # L2: Redis
        if level in ['all', 'redis']:
            value = self.redis_cluster.get(key)
            if value:
                data = json.loads(value)
                # 回填本地缓存
                self.local_cache[key] = data
                return data
        
        return None
    
    def set(self, key, value, ttl=300, level='all'):
        """设置缓存"""
        if level in ['all', 'local']:
            self.local_cache[key] = value
        
        if level in ['all', 'redis']:
            self.redis_cluster.setex(
                key, ttl, json.dumps(value)
            )
    
    def delete(self, key):
        """删除缓存"""
        self.local_cache.pop(key, None)
        self.redis_cluster.delete(key)


# 装饰器自动缓存
from common.cache import cache_manager

def cached(ttl=300, key_prefix=''):
    """自动缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试读取缓存
            result = cache_manager.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


# Service层使用缓存
class KnowledgebaseService:
    @classmethod
    @cached(ttl=600, key_prefix='kb')
    def get_by_id(cls, kb_id):
        """获取知识库 - 自动缓存10分钟"""
        return cls.model.select().where(cls.model.id == kb_id).first()
    
    @classmethod
    def update(cls, kb_id, **kwargs):
        """更新时清除缓存"""
        result = cls.model.update(**kwargs).where(cls.model.id == kb_id).execute()
        
        # 清除相关缓存
        cache_manager.delete(f'kb:get_by_id:{kb_id}')
        cache_manager.delete(f'kb:get_list:*')
        
        return result
```

### 2.3 数据库连接池优化

```yaml
# docker/service_conf.yaml.template

database:
  master:
    host: ${MYSQL_HOST}
    port: ${MYSQL_PORT}
    user: ${MYSQL_USER}
    password: ${MYSQL_PASSWORD}
    database: ${MYSQL_DATABASE}
    
    # 连接池配置（关键优化）
    pool:
      max_connections: 100        # 最大连接数
      max_idle: 20                # 最大空闲连接
      connection_timeout: 30      # 连接超时
      idle_timeout: 600           # 空闲超时
      max_lifetime: 1800          # 连接最大生命周期
      
  slaves:
    - host: mysql-slave-1
      weight: 1                   # 负载均衡权重
    - host: mysql-slave-2
      weight: 1
    - host: mysql-slave-3
      weight: 1
```

### 2.4 Phase 1 效果预期

| 指标 | 改造前 | 改造后 | 提升 |
|------|--------|--------|------|
| 数据库并发连接 | 20 | 150+ | 7.5x |
| 读QPS | ~1000 | ~5000 | 5x |
| 热点数据延迟 | ~50ms | ~5ms | 10x |
| 支持用户数 | ~1000 | ~5000 | 5x |

---

## 三、Phase 2: 服务拆分（第3-8周）

**目标**: 将单体Web Server拆分为独立微服务

### 3.1 服务拆分策略

```
拆分原则：按业务领域拆分（DDD）

当前单体：
┌─────────────────────────────────────────────────────────┐
│                    api/apps/                             │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┐   │
│  │ canvas  │   kb    │document │   user  │   file  │   │
│  │  _app   │  _app   │  _app   │  _app   │  _app   │   │
│  └─────────┴─────────┴─────────┴─────────┴─────────┘   │
└─────────────────────────────────────────────────────────┘

拆分为5个服务：
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  用户服务   │ │  知识库服务 │ │  文档服务   │ │  Agent服务  │ │  文件服务   │
│  user-svc   │ │    kb-svc   │ │  doc-svc    │ │  agent-svc  │ │  file-svc   │
│   :8001     │ │    :8002    │ │   :8003     │ │   :8004     │ │   :8005     │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │               │               │
       └───────────────┴───────────────┴───────────────┴───────────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │    API Gateway    │
                         │   (Kong/Nginx)    │
                         └───────────────────┘
```

### 3.2 服务拆分实施

#### 3.2.1 用户服务（user-service）

```python
# services/user-service/main.py

from fastapi import FastAPI
from user_api import router as user_router
from auth_api import router as auth_router

app = FastAPI(title="RAGFlow User Service")

# 注册路由
app.include_router(user_router, prefix="/api/v1/users")
app.include_router(auth_router, prefix="/api/v1/auth")

# 健康检查
@app.get("/health")
def health():
    return {"status": "ok", "service": "user-service"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

```python
# services/user-service/user_api.py

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from user_service import UserService
from auth import verify_token

router = APIRouter()

class CreateUserRequest(BaseModel):
    email: str
    password: str
    nickname: str

@router.post("/")
async def create_user(
    req: CreateUserRequest,
    current_user: dict = Depends(verify_token)
):
    """创建用户"""
    user = await UserService.create_user(**req.dict())
    return {"id": user.id, "email": user.email}

@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user: dict = Depends(verify_token)
):
    """获取用户信息"""
    user = await UserService.get_by_id(user_id)
    return user.to_dict()
```

#### 3.2.2 知识库服务（kb-service）

```python
# services/kb-service/main.py

from fastapi import FastAPI
from kb_api import router as kb_router

app = FastAPI(title="RAGFlow KB Service")
app.include_router(kb_router, prefix="/api/v1/knowledgebases")

# 与其他服务的gRPC客户端
from grpc_clients import UserServiceClient, DocServiceClient

user_client = UserServiceClient("user-service:8001")
doc_client = DocServiceClient("doc-service:8003")


@app.get("/health")
def health():
    return {"status": "ok", "service": "kb-service"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
```

```python
# services/kb-service/kb_api.py

from fastapi import APIRouter, HTTPException
from kb_service import KnowledgebaseService
from grpc_clients import doc_client

router = APIRouter()

@router.post("/{kb_id}/documents")
async def add_document(kb_id: str, doc_request: dict):
    """向知识库添加文档"""
    
    # 1. 调用文档服务创建文档
    doc = await doc_client.create_document(
        name=doc_request['name'],
        content=doc_request['content']
    )
    
    # 2. 本地关联知识库和文档
    await KnowledgebaseService.add_document(kb_id, doc.id)
    
    return {"kb_id": kb_id, "doc_id": doc.id}


@router.get("/{kb_id}/search")
async def search_kb(kb_id: str, query: str):
    """搜索知识库"""
    # 调用RAG检索服务（可以是本地或另一个服务）
    results = await KnowledgebaseService.search(kb_id, query)
    return {"results": results}
```

#### 3.2.3 服务间通信（gRPC）

```protobuf
# services/proto/user.proto

syntax = "proto3";

package user;

service UserService {
    rpc GetUser(GetUserRequest) returns (User);
    rpc ValidateToken(ValidateTokenRequest) returns (TokenResponse);
}

message GetUserRequest {
    string user_id = 1;
}

message User {
    string id = 1;
    string email = 2;
    string nickname = 3;
    string tenant_id = 4;
}

message ValidateTokenRequest {
    string token = 1;
}

message TokenResponse {
    bool valid = 1;
    User user = 2;
}
```

```python
# services/common/grpc_clients.py

import grpc
from proto import user_pb2, user_pb2_grpc

class UserServiceClient:
    """用户服务gRPC客户端"""
    
    def __init__(self, target):
        self.channel = grpc.insecure_channel(target)
        self.stub = user_pb2_grpc.UserServiceStub(self.channel)
    
    async def get_user(self, user_id: str):
        request = user_pb2.GetUserRequest(user_id=user_id)
        response = await self.stub.GetUser(request)
        return {
            "id": response.id,
            "email": response.email,
            "nickname": response.nickname
        }
    
    async def validate_token(self, token: str):
        request = user_pb2.ValidateTokenRequest(token=token)
        response = await self.stub.ValidateToken(request)
        return response.valid, response.user
```

### 3.3 API Gateway

```yaml
# kong/kong.yaml

services:
  - name: user-service
    url: http://user-service:8001
    routes:
      - name: user-routes
        paths:
          - /api/v1/users
          - /api/v1/auth
        strip_path: false
    
  - name: kb-service
    url: http://kb-service:8002
    routes:
      - name: kb-routes
        paths:
          - /api/v1/knowledgebases
        strip_path: false
    
  - name: doc-service
    url: http://doc-service:8003
    routes:
      - name: doc-routes
        paths:
          - /api/v1/documents
        strip_path: false

plugins:
  - name: rate-limiting
    config:
      minute: 100
      
  - name: jwt
    service: user-service
    config:
      uri_param_names: []
      cookie_names: []
      key_claim_name: iss
      secret_is_base64: false
      claims_to_verify:
        - exp
```

### 3.4 Phase 2 效果预期

| 指标 | 改造前 | 改造后 | 提升 |
|------|--------|--------|------|
| 部署粒度 | 整体 | 独立服务 | 可精准扩容 |
| 故障隔离 | 无 | 服务级 | 单服务故障不影响全局 |
| 团队并行 | 困难 | 容易 | 各团队维护独立服务 |
| 技术栈 | 统一 | 可异构 | 各服务可用不同语言 |
| 支持用户数 | ~5000 | ~5万 | 10x |

---

## 四、Phase 3: 数据分片（第9-16周）

**目标**: 解决数据库单表瓶颈，支持百万级租户

### 4.1 分库分表策略

```
分片策略：按租户ID（tenant_id）水平分片

┌─────────────────────────────────────────────────────────────────────────────┐
│                        分片架构                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   应用层                    分片中间件              数据库集群                 │
│   ──────                   ────────────            ────────────               │
│                                                                              │
│   ┌─────────┐              ┌─────────────┐        ┌─────────────────────┐   │
│   │ User    │─────────────►│ ShardingSphere│─────►│ DB-Shard-0 (0-99)   │   │
│   │ Service │   SQL        │   (Proxy)   │        │ DB-Shard-1 (100-199)│   │
│   └─────────┘              └─────────────┘        │ DB-Shard-2 (200-299)│   │
│        │                     │                    │ ...                 │   │
│        │                     │ 路由规则            │ DB-Shard-N          │   │
│        │                     │ tenant_id % 100    └─────────────────────┘   │
│        │                     │                                              │
│        │                     ▼                                              │
│        │              ┌─────────────┐                                       │
│        └─────────────►│  Config Center│                                       │
│                       │  (Nacos/etcd)│                                       │
│                       │  分片规则配置 │                                       │
│                       └─────────────┘                                       │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 ShardingSphere 配置

```yaml
# sharding-proxy/conf/config-sharding.yaml

schemaName: ragflow

dataSources:
  ds_0:
    url: jdbc:mysql://mysql-shard-0:3306/ragflow?serverTimezone=UTC
    username: root
    password: password
    connectionTimeoutMilliseconds: 30000
    idleTimeoutMilliseconds: 60000
    maxLifetimeMilliseconds: 1800000
    maxPoolSize: 50
    
  ds_1:
    url: jdbc:mysql://mysql-shard-1:3306/ragflow?serverTimezone=UTC
    username: root
    password: password
    maxPoolSize: 50
    
  ds_2:
    url: jdbc:mysql://mysql-shard-2:3306/ragflow?serverTimezone=UTC
    username: root
    password: password
    maxPoolSize: 50

rules:
  - !SHARDING
    tables:
      # 用户表分片
      user:
        actualDataNodes: ds_${0..2}.user
        tableStrategy:
          standard:
            shardingColumn: id
            shardingAlgorithmName: user_inline
        keyGenerateStrategy:
          column: id
          keyGeneratorName: snowflake
      
      # 知识库表分片（按tenant_id）
      knowledgebase:
        actualDataNodes: ds_${0..2}.knowledgebase
        databaseStrategy:
          standard:
            shardingColumn: tenant_id
            shardingAlgorithmName: tenant_hash
      
      # 文档表分片（按tenant_id）
      document:
        actualDataNodes: ds_${0..2}.document
        databaseStrategy:
          standard:
            shardingColumn: tenant_id
            shardingAlgorithmName: tenant_hash
    
    shardingAlgorithms:
      user_inline:
        type: INLINE
        props:
          algorithm-expression: ds_${id % 3}
      
      tenant_hash:
        type: INLINE
        props:
          algorithm-expression: ds_${Math.abs(tenant_id.hashCode()) % 3}
    
    keyGenerators:
      snowflake:
        type: SNOWFLAKE
        props:
          worker-id: ${WORKER_ID}
```

### 4.3 分布式ID生成

```python
# common/id_generator.py

from snowflake import SnowflakeGenerator

class DistributedIDGenerator:
    """分布式ID生成器（Snowflake）"""
    
    def __init__(self, datacenter_id, worker_id):
        """
        Args:
            datacenter_id: 数据中心ID (0-31)
            worker_id: 机器ID (0-31)
        """
        self.gen = SnowflakeGenerator(
            datacenter_id=datacenter_id,
            worker_id=worker_id
        )
    
    def generate(self):
        """生成全局唯一ID"""
        return next(self.gen)
    
    def generate_bulk(self, count):
        """批量生成"""
        return [next(self.gen) for _ in range(count)]


# 使用
id_gen = DistributedIDGenerator(
    datacenter_id=int(os.getenv('DC_ID', 0)),
    worker_id=int(os.getenv('WORKER_ID', 0))
)

# Service层
class DocumentService:
    @classmethod
    def create(cls, **kwargs):
        # 使用分布式ID，不再依赖数据库自增
        doc_id = id_gen.generate()
        
        return Document.create(
            id=doc_id,
            **kwargs
        )
```

### 4.4 跨分片查询处理

```python
# 聚合查询处理（跨分片）

class CrossShardQueryHandler:
    """跨分片查询处理器"""
    
    @staticmethod
    async def aggregate_user_stats():
        """统计所有分片的用户数量"""
        
        # 并行查询所有分片
        tasks = []
        for shard_id in range(SHARD_COUNT):
            tasks.append(query_shard(shard_id, "SELECT COUNT(*) FROM user"))
        
        results = await asyncio.gather(*tasks)
        
        # 聚合结果
        total = sum(r[0] for r in results)
        return {"total_users": total}
    
    @staticmethod
    async def search_across_shards(tenant_ids, query):
        """跨分片搜索（已知tenant_id列表）"""
        
        # 按分片分组tenant_id
        shard_groups = {}
        for tid in tenant_ids:
            shard_id = get_shard_id(tid)
            shard_groups.setdefault(shard_id, []).append(tid)
        
        # 并行查询
        tasks = []
        for shard_id, tids in shard_groups.items():
            tasks.append(search_shard(shard_id, tids, query))
        
        results = await asyncio.gather(*tasks)
        
        # 合并排序
        all_docs = []
        for r in results:
            all_docs.extend(r)
        
        return sorted(all_docs, key=lambda x: x.score, reverse=True)
```

### 4.5 Phase 3 效果预期

| 指标 | 改造前 | 改造后 | 提升 |
|------|--------|--------|------|
| 单表数据量 | 1000万+ | <500万 | 分片后 |
| 租户容量 | ~5000 | ~100万 | 200x |
| 单库连接数 | 150 | 150 x 分片数 | 线性扩展 |
| 查询延迟P99 | ~500ms | ~100ms | 5x |

---

## 五、Phase 4: 云原生化（第17-20周）

**目标**: 全面云原生化，实现自动扩缩容、服务网格

### 5.1 Kubernetes 部署

```yaml
# k8s/user-service.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: user-service
  labels:
    app: user-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: user-service
  template:
    metadata:
      labels:
        app: user-service
    spec:
      containers:
        - name: user-service
          image: ragflow/user-service:latest
          ports:
            - containerPort: 8001
          env:
            - name: DB_HOST
              value: "sharding-proxy"
            - name: REDIS_HOST
              value: "redis-cluster"
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8001
            initialDelaySeconds: 5
            periodSeconds: 5
---
# HPA 自动扩缩容
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: user-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user-service
  minReplicas: 3
  maxReplicas: 50
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

### 5.2 Service Mesh (Istio)

```yaml
# istio/virtual-service.yaml

apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: kb-service
spec:
  hosts:
    - kb-service
  http:
    - route:
        - destination:
            host: kb-service
            subset: v1
          weight: 90
        - destination:
            host: kb-service
            subset: v2
          weight: 10
      timeout: 10s
      retries:
        attempts: 3
        perTryTimeout: 2s
        retryOn: 5xx,gateway-error
      fault:
        delay:
          percentage:
            value: 0.1
          fixedDelay: 5s
---
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: kb-service
spec:
  host: kb-service
  trafficPolicy:
    connectionPool:
      tcp:
        maxConnections: 100
      http:
        http1MaxPendingRequests: 50
        maxRequestsPerConnection: 10
    outlierDetection:
      consecutiveErrors: 5
      interval: 30s
      baseEjectionTime: 30s
  subsets:
    - name: v1
      labels:
        version: v1
    - name: v2
      labels:
        version: v2
```

### 5.3 可观测性

```yaml
# prometheus/service-monitor.yaml

apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: ragflow-services
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: ragflow
  endpoints:
    - port: metrics
      interval: 15s
      path: /metrics
---
# grafana/dashboards/ragflow.json

{
  "dashboard": {
    "title": "RAGFlow 服务监控",
    "panels": [
      {
        "title": "QPS by Service",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (service)"
          }
        ]
      },
      {
        "title": "Latency P99",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (service)"
          }
        ]
      }
    ]
  }
}
```

---

## 六、改造风险与回滚策略

### 6.1 风险分析

| 阶段 | 风险 | 影响 | 缓解措施 |
|------|------|------|----------|
| Phase 1 | 读写分离延迟 | 数据不一致 | 强制读主库策略 |
| Phase 2 | 服务间网络故障 | 级联失败 | 熔断降级机制 |
| Phase 3 | 分片数据迁移 | 数据丢失 | 双写验证+逐步切流 |
| Phase 4 | K8s复杂度 | 运维困难 | 保留裸机部署能力 |

### 6.2 双写迁移策略

```python
# Phase 3 数据迁移方案

class MigrationService:
    """双写迁移服务"""
    
    async def migrate_tenant(self, tenant_id):
        """
        单个租户数据迁移流程
        """
        # 1. 开启双写（写旧库+新分片库）
        await self.enable_dual_write(tenant_id)
        
        # 2. 全量数据迁移
        await self.full_migration(tenant_id)
        
        # 3. 增量同步（追平数据）
        await self.catch_up(tenant_id)
        
        # 4. 验证数据一致性
        consistent = await self.verify_consistency(tenant_id)
        if not consistent:
            raise MigrationError("数据不一致")
        
        # 5. 切换读流量到新库
        await self.switch_read(tenant_id)
        
        # 6. 观察一段时间
        await asyncio.sleep(86400)  # 观察1天
        
        # 7. 关闭双写，只写新库
        await self.disable_dual_write(tenant_id)
        
        # 8. 删除旧库数据（可选）
        await self.cleanup_old_data(tenant_id)
```

### 6.3 回滚方案

```yaml
# 每个阶段都有回滚方案

Phase 1 回滚:
  操作: 移除读写分离配置，切回单库
  时间: 5分钟
  数据风险: 无

Phase 2 回滚:
  操作: 流量切回单体服务
  时间: 10分钟
  数据风险: 无（数据仍在原库）

Phase 3 回滚:
  操作: 切回单库读，双写继续
  时间: 30分钟
  数据风险: 中（需检查数据一致性）

Phase 4 回滚:
  操作: 切回Docker Compose部署
  时间: 1小时
  数据风险: 无
```

---

## 七、总结

### 7.1 改造路线图

```
时间线 →

Week 1-2:   [==========] Phase 1: 数据库优化
                    读写分离 + 缓存层
                    
Week 3-8:   [======================] Phase 2: 服务拆分
                                          拆分为5+微服务
                                          
Week 9-16:  [======================================] Phase 3: 数据分片
                                                              分库分表
                                                              
Week 17-20: [==========] Phase 4: 云原生化
                    K8s + Istio
                    
Total: 20周 (5个月)
```

### 7.2 最终架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    改造后 RAGFlow 架构（企业级）                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   接入层                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  CDN / WAF / DDoS防护                                               │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│   网关层                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Kong / Nginx (API Gateway)                                         │   │
│   │  • 路由 • 鉴权 • 限流 • 负载均衡                                     │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│   服务层（Service Mesh）                                                     │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│   │  用户服务   │ │  知识库服务 │ │  文档服务   │ │  Agent服务  │          │
│   │  (HPA)     │ │   (HPA)    │ │   (HPA)    │ │   (HPA)    │          │
│   │  3-50 Pod  │ │  3-30 Pod  │ │  3-100 Pod │ │  3-20 Pod  │          │
│   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                                              │
│   数据层                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  MySQL集群 (ShardingSphere)  Redis集群  Elasticsearch集群           │   │
│   │  • 分库分表  • 读写分离    • 多级缓存  • 向量检索                    │   │
│   │  • 100+ 分片                • 热点数据  • 租户隔离                   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   基础设施                                                                   │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │  Kubernetes + Istio + Prometheus + Grafana + ELK                   │   │
│   │  自动扩缩容 + 服务网格 + 监控告警 + 日志分析                         │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   支持规模: 100万+ 租户, 1000万+ 日活用户                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 关键指标对比

| 指标 | 改造前 | 改造后 | 提升 |
|------|--------|--------|------|
| 支持租户数 | 5,000 | 1,000,000 | 200x |
| 日活用户数 | 10,000 | 10,000,000 | 1000x |
| 文档处理量/日 | 10万 | 1000万 | 100x |
| 系统可用性 | 99.9% | 99.99% | 10x |
| 故障恢复时间 | 30分钟 | 5分钟 | 6x |
| 部署频率 | 周级 | 日级 | 7x |

---

**文档版本**: 1.0  
**作者**: AI助手  
**日期**: 2026-02-05
