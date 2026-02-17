# RATH connector：数据源连接服务详解

**服务定位**: 统一多数据源连接与查询网关  
**技术栈**: Python + Flask + SQLAlchemy  
**默认端口**: 5001  
**所属项目**: [RATH](https://github.com/Kanaries/RATH)

---

## 一、服务概述

### 1.1 什么是 connector？

connector 是 RATH 的数据基础设施层，提供**统一的数据源接入能力**：

```
┌─────────────────────────────────────────────────────────────┐
│                        connector :5001                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   前端/UI                                                    │
│      ↓ "连接MySQL数据库"                                     │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              connector 统一接口                      │   │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │   │
│   │  │  MySQL   │ │PostgreSQL│ │BigQuery  │ │ 更多   │  │   │
│   │  │Connector │ │Connector │ │Connector │ │ 20+   │  │   │
│   │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘  │   │
│   │       └─────────────┴─────────────┴──────────┘       │   │
│   │                      ↓                                │   │
│   │              统一的查询接口                            │   │
│   │              query(sql) → DataFrame                   │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心能力

| 能力 | 说明 | 支持数量 |
|------|------|---------|
| **多数据源** | 支持20+种数据库/数据仓库 | MySQL、PostgreSQL、BigQuery、ClickHouse等 |
| **统一接口** | 不同数据源相同API | query()、get_schema()、test_connection() |
| **连接池** | 复用数据库连接 | 减少连接开销 |
| **Schema发现** | 自动获取表结构 | 用于前端展示和SQL提示 |
| **SQL执行** | 安全执行查询 | 只读查询，防止误操作 |

---

## 二、技术架构

### 2.1 项目结构

```
connector/
├── app.py                  # Flask 入口
├── database.py            # SQLAlchemy 模型
├── bp_database.py         # 数据库蓝图（API路由）
├── connection.py          # 连接管理核心
├── requirements.txt       # 依赖
├── Dockerfile            # 容器定义
├── connectors/           # 连接器实现
│   ├── __init__.py
│   ├── base.py           # 连接器基类
│   ├── mysql.py          # MySQL
│   ├── postgres.py       # PostgreSQL
│   ├── bigquery.py       # Google BigQuery
│   ├── clickhouse.py     # ClickHouse
│   ├── snowflake.py      # Snowflake
│   ├── athena.py         # AWS Athena
│   └── ...               # 更多数据源
└── utils/                # 工具函数
    ├── sql_parser.py     # SQL解析
    └── data_converter.py # 数据格式转换
```

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     connector :5001                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Flask API Layer                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ POST /connections        # 创建连接                 │   │
│  │ GET  /connections        # 列出连接                 │   │
│  │ POST /query              # 执行SQL                  │   │
│  │ GET  /schema             # 获取表结构               │   │
│  │ POST /test               # 测试连接                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Connection Manager                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ - 连接池管理                                         │   │
│  │ - 连接生命周期（创建、复用、关闭）                    │   │
│  │ - 配置加密存储                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                           ↓                                  │
│  Connector Registry                                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │  MySQL   │ │PostgreSQL│ │BigQuery  │ │ClickHouse│      │
│  │Connector │ │Connector │ │Connector │ │Connector │      │
│  │          │ │          │ │          │ │          │      │
│  │pymysql   │ │psycopg2  │ │google    │ │clickhouse│      │
│  │          │ │          │ │cloud     │ │driver    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、连接器设计模式

### 3.1 抽象基类

```python
# connectors/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd

class ConnectionConfig:
    """连接配置"""
    def __init__(self, 
                 source_type: str,    # 数据源类型
                 host: str = None,
                 port: int = None,
                 database: str = None,
                 username: str = None,
                 password: str = None,
                 **kwargs):
        self.source_type = source_type
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.extra = kwargs

class TableSchema:
    """表结构定义"""
    def __init__(self, name: str, columns: List[Dict]):
        self.name = name
        self.columns = columns  # [{"name": "id", "type": "INTEGER"}, ...]

class BaseConnector(ABC):
    """数据源连接器基类"""
    
    # 连接器元信息
    source_type: str = None  # 如 "mysql", "postgres"
    display_name: str = None  # 如 "MySQL"
    icon: str = None  # 前端图标
    
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self._connection = None
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        建立数据库连接
        Returns: 是否连接成功
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """关闭连接"""
        pass
    
    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接是否可用
        Returns: {"success": bool, "message": str}
        """
        pass
    
    @abstractmethod
    def query(self, sql: str, limit: int = 10000) -> pd.DataFrame:
        """
        执行SQL查询
        Args:
            sql: SQL语句
            limit: 最大返回行数
        Returns: pandas DataFrame
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> List[TableSchema]:
        """
        获取数据库结构
        Returns: 表结构列表
        """
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        pass
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected
```

### 3.2 MySQL连接器实现

```python
# connectors/mysql.py
import pymysql
import pandas as pd
from .base import BaseConnector, ConnectionConfig, TableSchema

class MySQLConnector(BaseConnector):
    """MySQL连接器"""
    
    source_type = "mysql"
    display_name = "MySQL"
    icon = "mysql-icon.svg"
    
    def connect(self) -> bool:
        try:
            self._connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port or 3306,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"MySQL连接失败: {str(e)}")
    
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connected = False
    
    def test_connection(self) -> Dict:
        try:
            with self._connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return {"success": True, "message": "连接成功"}
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def query(self, sql: str, limit: int = 10000) -> pd.DataFrame:
        """执行查询"""
        # 安全检查：只允许SELECT语句
        if not self._is_safe_sql(sql):
            raise ValueError("只允许执行SELECT查询")
        
        # 添加LIMIT限制
        sql = self._add_limit(sql, limit)
        
        try:
            df = pd.read_sql(sql, self._connection)
            return df
        except Exception as e:
            raise QueryError(f"查询执行失败: {str(e)}")
    
    def get_schema(self) -> List[TableSchema]:
        """获取数据库结构"""
        schema = []
        
        with self._connection.cursor() as cursor:
            # 获取所有表
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            for table_row in tables:
                table_name = list(table_row.values())[0]
                
                # 获取表结构
                cursor.execute(f"DESCRIBE `{table_name}`")
                columns = cursor.fetchall()
                
                column_list = [
                    {
                        "name": col["Field"],
                        "type": col["Type"],
                        "nullable": col["Null"] == "YES",
                        "key": col["Key"],
                        "default": col["Default"]
                    }
                    for col in columns
                ]
                
                schema.append(TableSchema(
                    name=table_name,
                    columns=column_list
                ))
        
        return schema
    
    def get_tables(self) -> List[str]:
        """获取所有表名"""
        with self._connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            return [list(row.values())[0] for row in tables]
    
    def _is_safe_sql(self, sql: str) -> bool:
        """检查SQL是否安全（只允许SELECT）"""
        dangerous_keywords = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER']
        sql_upper = sql.upper().strip()
        return sql_upper.startswith('SELECT') and not any(kw in sql_upper for kw in dangerous_keywords)
    
    def _add_limit(self, sql: str, limit: int) -> str:
        """智能添加LIMIT"""
        sql_upper = sql.upper()
        if 'LIMIT' not in sql_upper:
            sql = f"{sql} LIMIT {limit}"
        return sql
```

### 3.3 BigQuery连接器实现

```python
# connectors/bigquery.py
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
from .base import BaseConnector, ConnectionConfig, TableSchema

class BigQueryConnector(BaseConnector):
    """Google BigQuery连接器"""
    
    source_type = "bigquery"
    display_name = "Google BigQuery"
    icon = "bigquery-icon.svg"
    
    def connect(self) -> bool:
        try:
            # 使用服务账号认证
            if self.config.extra.get('credentials'):
                credentials = service_account.Credentials.from_service_account_info(
                    self.config.extra['credentials']
                )
                self._client = bigquery.Client(
                    project=self.config.extra.get('project_id'),
                    credentials=credentials
                )
            else:
                # 使用默认认证（如GCP环境）
                self._client = bigquery.Client(project=self.config.extra.get('project_id'))
            
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"BigQuery连接失败: {str(e)}")
    
    def disconnect(self):
        # BigQuery客户端无需显式关闭
        self._connected = False
    
    def query(self, sql: str, limit: int = 10000) -> pd.DataFrame:
        """执行BigQuery SQL"""
        # 添加LIMIT
        if "LIMIT" not in sql.upper():
            sql = f"{sql} LIMIT {limit}"
        
        query_job = self._client.query(sql)
        results = query_job.result()
        
        # 转换为DataFrame
        df = results.to_dataframe()
        return df
    
    def get_schema(self) -> List[TableSchema]:
        """获取数据集结构"""
        dataset_id = self.config.extra.get('dataset_id')
        dataset_ref = self._client.dataset(dataset_id)
        
        schema = []
        tables = list(self._client.list_tables(dataset_ref))
        
        for table in tables:
            table_ref = dataset_ref.table(table.table_id)
            table_obj = self._client.get_table(table_ref)
            
            columns = [
                {
                    "name": field.name,
                    "type": field.field_type,
                    "nullable": field.is_nullable,
                    "description": field.description
                }
                for field in table_obj.schema
            ]
            
            schema.append(TableSchema(
                name=table.table_id,
                columns=columns
            ))
        
        return schema
```

---

## 四、连接管理

### 4.1 连接池设计

```python
# connection.py
import threading
import time
from typing import Dict, Optional
from .connectors.base import BaseConnector, ConnectionConfig

class PooledConnection:
    """连接池中的连接包装"""
    def __init__(self, connector: BaseConnector, created_at: float):
        self.connector = connector
        self.created_at = created_at
        self.last_used = created_at
        self.use_count = 0
    
    def is_expired(self, max_age: int = 3600) -> bool:
        """检查连接是否过期"""
        return time.time() - self.created_at > max_age
    
    def touch(self):
        """更新最后使用时间"""
        self.last_used = time.time()
        self.use_count += 1

class ConnectionPool:
    """连接池管理"""
    
    def __init__(self, 
                 max_size: int = 10,
                 max_age: int = 3600,  # 连接最大存活时间
                 max_idle: int = 300):  # 连接最大空闲时间
        self.max_size = max_size
        self.max_age = max_age
        self.max_idle = max_idle
        
        self._pools: Dict[str, list] = {}  # connection_id -> [PooledConnection]
        self._lock = threading.RLock()
    
    def get_connection(self, connection_id: str) -> Optional[BaseConnector]:
        """从池中获取连接"""
        with self._lock:
            if connection_id not in self._pools:
                return None
            
            pool = self._pools[connection_id]
            
            # 清理过期连接
            pool = [c for c in pool if not c.is_expired(self.max_age)]
            self._pools[connection_id] = pool
            
            # 返回可用连接
            for pooled in pool:
                if pooled.connector.is_connected():
                    pooled.touch()
                    return pooled.connector
            
            return None
    
    def return_connection(self, connection_id: str, connector: BaseConnector):
        """归还连接到池中"""
        with self._lock:
            if connection_id not in self._pools:
                self._pools[connection_id] = []
            
            pool = self._pools[connection_id]
            
            if len(pool) < self.max_size:
                pooled = PooledConnection(connector, time.time())
                pool.append(pooled)
            else:
                # 池已满，关闭连接
                connector.disconnect()
    
    def close_all(self, connection_id: str = None):
        """关闭连接（全部或指定ID）"""
        with self._lock:
            if connection_id:
                pools = {connection_id: self._pools.get(connection_id, [])}
            else:
                pools = self._pools
            
            for cid, pool in pools.items():
                for pooled in pool:
                    try:
                        pooled.connector.disconnect()
                    except:
                        pass
                self._pools[cid] = []
```

### 4.2 连接管理器

```python
# connection.py (continued)
class ConnectionManager:
    """连接管理器 - 统一管理所有数据源连接"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        # 单例模式
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._pool = ConnectionPool()
        self._connectors: Dict[str, BaseConnector] = {}  # 非池化连接
        self._registry = ConnectorRegistry()
        self._initialized = True
    
    def register_connector(self, connector_class):
        """注册新的连接器类型"""
        self._registry.register(connector_class)
    
    def create_connection(self, config: ConnectionConfig, use_pool: bool = True) -> str:
        """
        创建新连接
        Returns: connection_id
        """
        # 生成连接ID
        connection_id = f"{config.source_type}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # 获取连接器类
        connector_class = self._registry.get(config.source_type)
        if not connector_class:
            raise ValueError(f"不支持的数据源类型: {config.source_type}")
        
        # 创建连接器实例
        connector = connector_class(config)
        
        # 建立连接
        if connector.connect():
            if use_pool:
                self._pool.return_connection(connection_id, connector)
            else:
                self._connectors[connection_id] = connector
            return connection_id
        else:
            raise ConnectionError("连接建立失败")
    
    def execute_query(self, connection_id: str, sql: str, limit: int = 10000) -> pd.DataFrame:
        """执行查询"""
        # 尝试从连接池获取
        connector = self._pool.get_connection(connection_id)
        
        if not connector:
            # 从非池化连接获取
            connector = self._connectors.get(connection_id)
        
        if not connector or not connector.is_connected():
            raise ConnectionError("连接不存在或已断开")
        
        try:
            result = connector.query(sql, limit)
            return result
        finally:
            # 归还到连接池
            if connection_id in self._connectors:
                self._pool.return_connection(connection_id, connector)
    
    def get_schema(self, connection_id: str) -> List[TableSchema]:
        """获取数据库结构"""
        connector = self._get_connector(connection_id)
        return connector.get_schema()
    
    def close_connection(self, connection_id: str):
        """关闭连接"""
        self._pool.close_all(connection_id)
        if connection_id in self._connectors:
            self._connectors[connection_id].disconnect()
            del self._connectors[connection_id]
    
    def _get_connector(self, connection_id: str) -> BaseConnector:
        """获取连接器实例"""
        connector = self._pool.get_connection(connection_id)
        if not connector:
            connector = self._connectors.get(connection_id)
        if not connector:
            raise ConnectionError(f"连接不存在: {connection_id}")
        return connector


class ConnectorRegistry:
    """连接器注册中心"""
    
    def __init__(self):
        self._connectors: Dict[str, type] = {}
    
    def register(self, connector_class: type):
        """注册连接器"""
        self._connectors[connector_class.source_type] = connector_class
    
    def get(self, source_type: str) -> Optional[type]:
        """获取连接器类"""
        return self._connectors.get(source_type)
    
    def list(self) -> Dict[str, str]:
        """列出所有可用连接器"""
        return {
            source_type: cls.display_name 
            for source_type, cls in self._connectors.items()
        }

# 自动注册内置连接器
_connection_manager = None

def get_connection_manager() -> ConnectionManager:
    """获取连接管理器实例（单例）"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
        
        # 注册所有内置连接器
        from .connectors.mysql import MySQLConnector
        from .connectors.postgres import PostgresConnector
        from .connectors.bigquery import BigQueryConnector
        from .connectors.clickhouse import ClickHouseConnector
        # ... 更多
        
        _connection_manager.register_connector(MySQLConnector)
        _connection_manager.register_connector(PostgresConnector)
        _connection_manager.register_connector(BigQueryConnector)
        _connection_manager.register_connector(ClickHouseConnector)
    
    return _connection_manager
```

---

## 五、API 设计

### 5.1 Flask 路由

```python
# bp_database.py
from flask import Blueprint, request, jsonify
from .connection import get_connection_manager, ConnectionConfig

bp = Blueprint('database', __name__, url_prefix='/api')
manager = get_connection_manager()

@bp.route('/connections', methods=['POST'])
def create_connection():
    """创建数据源连接"""
    data = request.json
    
    config = ConnectionConfig(
        source_type=data['sourceType'],
        host=data.get('host'),
        port=data.get('port'),
        database=data.get('database'),
        username=data.get('username'),
        password=data.get('password'),
        **data.get('extra', {})
    )
    
    try:
        connection_id = manager.create_connection(config)
        return jsonify({
            "success": True,
            "connectionId": connection_id,
            "message": "连接创建成功"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

@bp.route('/connections/<connection_id>', methods=['DELETE'])
def close_connection(connection_id):
    """关闭连接"""
    manager.close_connection(connection_id)
    return jsonify({"success": True})

@bp.route('/query', methods=['POST'])
def execute_query():
    """执行SQL查询"""
    data = request.json
    connection_id = data['connectionId']
    sql = data['sql']
    limit = data.get('limit', 10000)
    
    try:
        df = manager.execute_query(connection_id, sql, limit)
        
        return jsonify({
            "success": True,
            "columns": df.columns.tolist(),
            "data": df.to_dict('records'),
            "rowCount": len(df),
            "preview": df.head(10).to_dict('records')
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

@bp.route('/schema', methods=['GET'])
def get_schema():
    """获取数据库结构"""
    connection_id = request.args.get('connectionId')
    
    try:
        schema = manager.get_schema(connection_id)
        
        return jsonify({
            "success": True,
            "tables": [
                {
                    "name": table.name,
                    "columns": table.columns
                }
                for table in schema
            ]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

@bp.route('/connections', methods=['GET'])
def list_supported_connections():
    """列出支持的数据源类型"""
    connectors = manager._registry.list()
    return jsonify({
        "success": True,
        "connectors": connectors
    })

@bp.route('/test', methods=['POST'])
def test_connection():
    """测试连接配置"""
    data = request.json
    
    config = ConnectionConfig(**data)
    
    try:
        # 创建临时连接测试
        connection_id = manager.create_connection(config, use_pool=False)
        connector = manager._connectors[connection_id]
        result = connector.test_connection()
        manager.close_connection(connection_id)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400
```

### 5.2 API 端点汇总

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/connections` | POST | 创建连接 |
| `/api/connections` | GET | 列出支持的连接器 |
| `/api/connections/<id>` | DELETE | 关闭连接 |
| `/api/query` | POST | 执行SQL查询 |
| `/api/schema` | GET | 获取数据库结构 |
| `/api/test` | POST | 测试连接配置 |

---

## 六、前端集成示例

```typescript
// 前端 connector API 客户端
class ConnectorAPI {
    baseURL = '/api';
    
    // 创建MySQL连接
    async createMySQLConnection(config: {
        host: string;
        port: number;
        database: string;
        username: string;
        password: string;
    }) {
        const response = await fetch(`${this.baseURL}/connections`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sourceType: 'mysql',
                ...config
            })
        });
        return response.json();
    }
    
    // 执行SQL查询
    async query(connectionId: string, sql: string, limit = 1000) {
        const response = await fetch(`${this.baseURL}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ connectionId, sql, limit })
        });
        return response.json();
    }
    
    // 获取表结构（用于SQL提示）
    async getSchema(connectionId: string) {
        const response = await fetch(
            `${this.baseURL}/schema?connectionId=${connectionId}`
        );
        return response.json();
    }
}

// 使用示例
const connector = new ConnectorAPI();

// 1. 创建连接
const conn = await connector.createMySQLConnection({
    host: 'localhost',
    port: 3306,
    database: 'sales_db',
    username: 'admin',
    password: 'password'
});

// 2. 获取表结构
const schema = await connector.getSchema(conn.connectionId);
console.log(schema.tables);
// [{name: 'orders', columns: [...]}, {name: 'customers', columns: [...]}]

// 3. 执行查询
const result = await connector.query(
    conn.connectionId,
    'SELECT * FROM orders WHERE amount > 1000'
);
console.log(result.data);
```

---

## 七、部署与配置

### 7.1 Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖（某些数据库驱动需要）
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# requirements.txt:
# flask==3.0.0
# pymysql==1.1.0
# psycopg2-binary==2.9.9
# google-cloud-bigquery==3.13.0
# clickhouse-driver==0.2.6
# pandas==2.0.3
# sqlalchemy==2.0.23

COPY . .

EXPOSE 5001

CMD ["python", "app.py"]
```

### 7.2 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `POOL_MAX_SIZE` | 连接池最大连接数 | 10 |
| `POOL_MAX_AGE` | 连接最大存活时间（秒） | 3600 |
| `QUERY_MAX_LIMIT` | 查询最大返回行数 | 10000 |
| `ENABLE_SSL` | 是否强制SSL | false |

---

## 八、最佳实践

### 8.1 安全性

- **SQL注入防护**: 使用参数化查询（pandas.read_sql自动处理）
- **只读限制**: 只允许SELECT语句
- **连接加密**: 密码使用环境变量或密钥管理服务
- **连接超时**: 设置合理的超时时间

### 8.2 性能优化

- **连接池**: 复用连接减少开销
- **查询限制**: 强制LIMIT防止大数据查询
- **分页**: 大数据集使用分页查询
- **异步**: 考虑使用异步数据库驱动

### 8.3 错误处理

```python
# 连接错误分类
try:
    df = connector.query(sql)
except ConnectionError as e:
    # 连接问题（网络、认证等）
    logger.error(f"连接失败: {e}")
    return {"error": "DATABASE_CONNECTION_ERROR", "message": str(e)}
except QueryError as e:
    # SQL问题（语法错误、权限等）
    logger.error(f"查询失败: {e}")
    return {"error": "QUERY_EXECUTION_ERROR", "message": str(e)}
except TimeoutError as e:
    # 查询超时
    logger.error(f"查询超时: {e}")
    return {"error": "QUERY_TIMEOUT", "message": "查询执行时间过长"}
```

---

## 九、总结

connector 服务是 RATH 的数据基础设施：

| 亮点 | 说明 |
|------|------|
| **统一抽象** | 20+数据源相同接口 |
| **连接池** | 高效复用连接 |
| **类型安全** | Schema自动发现 |
| **安全** | 只读查询，防止误操作 |

**借鉴价值**: ⭐⭐⭐⭐⭐
- 学习多数据源抽象设计
- 连接池实现模式
- Schema发现机制
