# Vanna 数据源集成能力分析

**分析日期**: 2026-02-05  
**项目路径**: `Projects/AI数据分析系统/参考项目/vanna/`  
**版本**: 基于最新主干代码

---

## 1. 数据源支持总览

### 1.1 新版本 (v2.x) 支持的数据库

Vanna 在新架构中通过 `SqlRunner` 接口支持以下数据库：

| 数据库 | 实现类 | 依赖包 | 连接方式 |
|--------|--------|--------|----------|
| **PostgreSQL** | `PostgresRunner` | psycopg2 | 连接字符串或参数 |
| **MySQL** | `MySQLRunner` | PyMySQL | 主机/端口/用户名/密码 |
| **SQLite** | `SqliteRunner` | sqlite3 (内置) | 文件路径 |
| **DuckDB** | `DuckDBRunner` | duckdb | 文件路径或内存 |
| **BigQuery** | `BigQueryRunner` | google-cloud-bigquery | 项目ID + 凭证 |
| **Snowflake** | `SnowflakeRunner` | snowflake-connector-python | 账号/用户/密码或密钥 |
| **Microsoft SQL Server** | `MSSQLRunner` | pyodbc + sqlalchemy | ODBC 连接字符串 |
| **Oracle** | `OracleRunner` | oracledb | DSN (host:port/sid) |
| **ClickHouse** | `ClickHouseRunner` | clickhouse-connect | HTTP 接口 |
| **Hive** | `HiveRunner` | pyhive | HiveServer2 |
| **Presto** | `PrestoRunner` | pyhive | HTTP/HTTPS 接口 |

### 1.2 遗留版本支持的数据库

遗留版本 (`vanna.legacy.base.VannaBase`) 提供类似支持：

```python
# 遗留版本的连接方法
vn.connect_to_postgres(host, dbname, user, password, port)
vn.connect_to_mysql(host, dbname, user, password, port)
vn.connect_to_sqlite(url)
vn.connect_to_snowflake(account, username, password, database)
vn.connect_to_bigquery(cred_file_path, project_id)
vn.connect_to_duckdb(url)
vn.connect_to_mssql(odbc_conn_str)
vn.connect_to_oracle(user, password, dsn)
vn.connect_to_clickhouse(host, dbname, user, password, port)
vn.connect_to_presto(host, catalog, schema, user, password, port)
vn.connect_to_hive(host, dbname, user, password, port, auth)
```

### 1.3 数据源特点分析

**关系型数据库全覆盖**: 支持主流商业和开源关系型数据库
- PostgreSQL / MySQL / SQLite (开源三剑客)
- Oracle / SQL Server (商业数据库)
- DuckDB (嵌入式分析型数据库)

**云数据仓库支持**: 原生支持主流云数据仓库
- Snowflake (云原生数据仓库)
- BigQuery (Google 云数据仓库)
- ClickHouse (列式 OLAP 数据库)

**大数据生态集成**: 支持 Hadoop 生态
- Hive (数据仓库)
- Presto/Trino (分布式 SQL 查询引擎)

---

## 2. 数据库连接器架构

### 2.1 核心抽象层

```
┌─────────────────────────────────────────────────────────────────┐
│                      SqlRunner (抽象基类)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  @abstractmethod                                         │   │
│  │  async def run_sql(args: RunSqlToolArgs, context) -> df │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 实现
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
   ┌────┴────┐          ┌────┴────┐          ┌────┴────┐
   │Postgres │          │  MySQL  │          │ DuckDB  │
   │ Runner  │          │ Runner  │          │ Runner  │
   └─────────┘          └─────────┘          └─────────┘
```

### 2.2 抽象接口定义

```python
# src/vanna/capabilities/sql_runner/base.py
class SqlRunner(ABC):
    """Interface for SQL execution with different implementations."""

    @abstractmethod
    async def run_sql(
        self, args: RunSqlToolArgs, context: "ToolContext"
    ) -> pd.DataFrame:
        """Execute SQL query and return results as a DataFrame."""
        pass

# 参数模型
class RunSqlToolArgs(BaseModel):
    """Arguments for run_sql tool."""
    sql: str = Field(description="SQL query to execute")
```

### 2.3 连接器实现模式

各数据库连接器遵循统一的实现模式：

```python
class PostgresRunner(SqlRunner):
    def __init__(self, connection_string=None, host=None, port=5432, ...):
        # 1. 延迟导入依赖（可选安装）
        try:
            import psycopg2
            self.psycopg2 = psycopg2
        except ImportError as e:
            raise ImportError("psycopg2 package is required...") from e
        
        # 2. 保存连接参数
        self.connection_params = {...}
    
    async def run_sql(self, args: RunSqlToolArgs, context: ToolContext) -> pd.DataFrame:
        # 3. 建立连接
        conn = self.psycopg2.connect(**self.connection_params)
        cursor = conn.cursor(cursor_factory=self.psycopg2.extras.RealDictCursor)
        
        try:
            # 4. 执行查询
            cursor.execute(args.sql)
            
            # 5. 区分查询类型（SELECT vs DML）
            query_type = args.sql.strip().upper().split()[0]
            
            if query_type == "SELECT":
                rows = cursor.fetchall()
                return pd.DataFrame([dict(row) for row in rows])
            else:
                conn.commit()
                return pd.DataFrame({"rows_affected": [cursor.rowcount]})
        finally:
            # 6. 清理资源
            cursor.close()
            conn.close()
```

### 2.4 架构设计特点

| 特性 | 实现方式 | 优势 |
|------|----------|------|
| **依赖延迟加载** | `__init__` 中动态导入 | 减少不必要的依赖安装 |
| **连接参数抽象** | 构造函数接收标准参数 | 统一配置方式 |
| **异步接口** | `async def run_sql` | 支持高并发场景 |
| **结果统一** | 返回 `pd.DataFrame` | 便于后续处理和可视化 |
| **资源自动清理** | `try/finally` 模式 | 防止连接泄漏 |

---

## 3. 查询执行机制

### 3.1 查询执行流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   LLM 生成  │────▶│  RunSqlTool │────▶│ SqlRunner   │────▶│   数据库    │
│   SQL 语句  │     │   工具调用   │     │  连接器实现  │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ 结果处理    │
                                        │ - DataFrame │
                                        │ - CSV 导出  │
                                        │ - 元数据    │
                                        └─────────────┘
```

### 3.2 连接管理方式

#### 方式一：每查询新建连接（PostgreSQL/MySQL/Oracle）

```python
async def run_sql(self, args, context):
    conn = self.psycopg2.connect(...)  # 新建连接
    cursor = conn.cursor()
    try:
        cursor.execute(args.sql)
        results = cursor.fetchall()
        return pd.DataFrame(results)
    finally:
        cursor.close()
        conn.close()  # 立即关闭
```

**特点**: 简单可靠，无连接池管理，适合低频查询场景

#### 方式二：连接复用（DuckDB/BigQuery）

```python
class DuckDBRunner(SqlRunner):
    def __init__(self, database_path):
        self._conn = None
    
    def _get_connection(self):
        if self._conn is None:
            self._conn = self.duckdb.connect(self.database_path)
        return self._conn
    
    async def run_sql(self, args, context):
        conn = self._get_connection()  # 复用连接
        return conn.query(args.sql).to_df()
```

**特点**: 减少连接开销，适合分析型数据库

#### 方式三：SQLAlchemy 引擎（MSSQL）

```python
class MSSQLRunner(SqlRunner):
    def __init__(self, odbc_conn_str):
        # 创建 SQLAlchemy 引擎（内部维护连接池）
        self.engine = create_engine(connection_url)
    
    async def run_sql(self, args, context):
        with self.engine.begin() as conn:  # 自动管理连接
            df = pd.read_sql_query(self.sa.text(args.sql), conn)
            return df
```

**特点**: 利用 SQLAlchemy 的连接池管理能力

### 3.3 查询类型处理

```python
# 查询类型识别
query_type = args.sql.strip().upper().split()[0]

if query_type == "SELECT":
    # SELECT 查询：返回完整结果集
    rows = cursor.fetchall()
    return pd.DataFrame([dict(row) for row in rows])
else:
    # DML 查询（INSERT/UPDATE/DELETE）：返回影响行数
    conn.commit()
    return pd.DataFrame({"rows_affected": [cursor.rowcount]})
```

### 3.4 结果处理机制

RunSqlTool 对查询结果进行统一处理：

```python
async def execute(self, context: ToolContext, args: RunSqlToolArgs) -> ToolResult:
    df = await self.sql_runner.run_sql(args, context)
    
    if query_type == "SELECT":
        # 1. 转换为字典列表
        results_data = df.to_dict("records")
        
        # 2. 保存为 CSV 供下游工具使用
        csv_content = df.to_csv(index=False)
        await self.file_system.write_file(filename, csv_content, context)
        
        # 3. 截断大结果（>1000字符）
        if len(results_preview) > 1000:
            results_preview = results_preview[:1000] + "\n(Results truncated...)"
        
        # 4. 返回结构化结果
        return ToolResult(
            success=True,
            result_for_llm=results_preview,
            ui_component=DataFrameComponent(...),
            metadata={"row_count": row_count, "columns": columns}
        )
```

---

## 4. 安全机制

### 4.1 SQL 注入防护分析

**现状**: Vanna **没有内置 SQL 注入防护机制**

```python
# 当前实现：直接执行 LLM 生成的 SQL
cursor.execute(args.sql)  # 原始 SQL 直接执行，无参数化查询
```

**风险**:
- LLM 生成的 SQL 可能包含恶意代码
- 无法阻止 `DROP TABLE`、`DELETE FROM` 等危险操作
- 无输入验证或查询白名单机制

**建议**: 
- 在生产环境使用只读数据库用户
- 通过数据库层面的权限控制限制操作
- 考虑添加 SQL 语法检查和白名单机制

### 4.2 权限控制系统

Vanna 提供了基于用户组的工具级权限控制：

```python
# 用户模型
class User(BaseModel):
    id: str
    username: Optional[str]
    group_memberships: List[str]  # 用户所属组

# 工具注册时指定访问组
registry.register_local_tool(
    tool=sql_tool,
    access_groups=["admin", "analyst"]  # 仅 admin 和 analyst 组可访问
)
```

**权限检查流程**:

```python
async def _validate_tool_permissions(self, tool: Tool, user: User) -> bool:
    tool_access_groups = tool.access_groups
    if not tool_access_groups:
        return True  # 无限制，允许所有用户
    
    user_groups = set(user.group_memberships)
    tool_groups = set(tool_access_groups)
    
    # 交集检查：用户属于任一允许组即可
    return bool(user_groups & tool_groups)
```

**权限测试用例**:

| 用户组 | 工具访问组 | 结果 |
|--------|------------|------|
| ["user"] | [] |  允许 |
| ["admin"] | ["admin"] |  允许 |
| ["user"] | ["admin"] |  拒绝 |
| ["analyst", "user"] | ["admin", "analyst"] |  允许 |
| [] | ["user"] |  拒绝 |

### 4.3 审计日志机制

Vanna 提供了完整的审计日志框架：

```python
class AuditLogger(ABC):
    """审计日志基类，支持多种后端实现"""
    
    async def log_tool_access_check(...)
    async def log_tool_invocation(...)
    async def log_tool_result(...)
    async def log_ai_response(...)
```

**审计事件类型**:

| 事件类型 | 记录内容 | 用途 |
|----------|----------|------|
| `TOOL_ACCESS_CHECK` | 用户、工具名、访问结果、所需组 | 权限审计 |
| `TOOL_INVOCATION` | 工具调用参数（可脱敏）、用户上下文 | 操作追溯 |
| `TOOL_RESULT` | 执行结果、错误信息、执行时间 | 性能监控 |
| `AI_RESPONSE_GENERATED` | 响应长度、工具调用数、模型信息 | LLM 审计 |

**敏感信息脱敏**:

```python
def _sanitize_parameters(self, parameters: Dict) -> tuple[Dict, bool]:
    """自动脱敏敏感字段"""
    sensitive_patterns = [
        "password", "secret", "token", "api_key", 
        "credential", "private_key", "access_key"
    ]
    
    for key in list(sanitized.keys()):
        if any(pattern in key.lower() for pattern in sensitive_patterns):
            sanitized[key] = "[REDACTED]"
```

### 4.4 行级安全（RLS）支持

通过 `transform_args` 钩子实现行级安全：

```python
class RowLevelSecurityRegistry(ToolRegistry):
    async def transform_args(self, tool, args, user, context):
        """根据用户组修改 SQL 查询"""
        if "SELECT" in args.sql.upper():
            if "admin" in user.group_memberships:
                return args  # Admin 看到所有数据
            elif "analyst" in user.group_memberships:
                # Analyst 添加部门过滤
                modified_sql = args.sql + " WHERE department='analytics'"
                return RunSqlToolArgs(sql=modified_sql)
            else:
                # 普通用户只能看自己的数据
                modified_sql = args.sql + f" WHERE user_id='{user.id}'"
                return RunSqlToolArgs(sql=modified_sql)
        return args
```

---

## 5. 扩展性分析

### 5.1 添加新数据源的步骤

**步骤 1**: 创建新的 Runner 类

```python
# src/vanna/integrations/newdb/sql_runner.py
from vanna.capabilities.sql_runner import SqlRunner, RunSqlToolArgs

class NewDBRunner(SqlRunner):
    def __init__(self, host: str, port: int, username: str, password: str):
        try:
            import newdb_driver
            self.driver = newdb_driver
        except ImportError:
            raise ImportError("newdb package is required. Install with: pip install newdb")
        
        self.connection_params = {
            "host": host, "port": port,
            "user": username, "password": password
        }
    
    async def run_sql(self, args: RunSqlToolArgs, context: ToolContext) -> pd.DataFrame:
        conn = self.driver.connect(**self.connection_params)
        try:
            cursor = conn.cursor()
            cursor.execute(args.sql)
            results = cursor.fetchall()
            return pd.DataFrame(results, columns=[desc[0] for desc in cursor.description])
        finally:
            conn.close()
```

**步骤 2**: 导出模块

```python
# src/vanna/integrations/newdb/__init__.py
from .sql_runner import NewDBRunner

__all__ = ["NewDBRunner"]
```

**步骤 3**: 注册到工具注册表

```python
from vanna.tools.run_sql import RunSqlTool
from vanna.integrations.newdb import NewDBRunner

# 创建 Runner
runner = NewDBRunner(host="localhost", port=1234, username="user", password="pass")

# 创建工具
sql_tool = RunSqlTool(sql_runner=runner)

# 注册到 Agent
registry.register_local_tool(sql_tool, access_groups=["analyst"])
```

### 5.2 扩展示例：添加 Redis 支持

```python
class RedisRunner(SqlRunner):
    """Redis 连接器（使用 RediSearch 模块支持 SQL-like 查询）"""
    
    def __init__(self, host: str, port: int = 6379):
        import redis
        self.client = redis.Redis(host=host, port=port)
    
    async def run_sql(self, args: RunSqlToolArgs, context: ToolContext) -> pd.DataFrame:
        # 将类 SQL 查询转换为 Redis 命令
        # 或使用 RediSearch 的 FT.AGGREGATE
        ...
```

### 5.3 扩展性评价

| 维度 | 评分 | 说明 |
|------|------|------|
| **接口简洁度** | ⭐⭐⭐⭐⭐ | 仅需实现一个抽象方法 |
| **依赖管理** | ⭐⭐⭐⭐ | 延迟导入设计，可选依赖 |
| **配置灵活性** | ⭐⭐⭐⭐ | 支持多种连接参数方式 |
| **结果标准化** | ⭐⭐⭐⭐⭐ | 统一返回 DataFrame |
| **文档示例** | ⭐⭐⭐ | 需要阅读源码学习 |

---

## 6. 与 DB-GPT 数据源集成的对比

### 6.1 支持数据源对比

| 数据源 | Vanna | DB-GPT | 说明 |
|--------|-------|--------|------|
| PostgreSQL |  |  | 两者均支持 |
| MySQL |  |  | 两者均支持 |
| SQLite |  |  | 两者均支持 |
| DuckDB |  |  | 两者均支持 |
| BigQuery |  |  | 两者均支持 |
| Snowflake |  | ⚠️ | Vanna 原生支持 |
| Oracle |  |  | 两者均支持 |
| SQL Server |  |  | 两者均支持 |
| ClickHouse |  |  | 两者均支持 |
| Hive |  |  | 两者均支持 |
| Presto |  | ⚠️ | Vanna 原生支持 |
| **Doris** |  |  | DB-GPT 特有 |
| **StarRocks** |  |  | DB-GPT 特有 |
| **GaussDB** |  |  | DB-GPT 特有（国产） |
| **Vertica** |  |  | DB-GPT 特有 |

**结论**: 
- Vanna 支持 11 种主流数据库
- DB-GPT 支持 14+ 种，包含更多国产和特定场景数据库

### 6.2 架构设计对比

| 特性 | Vanna | DB-GPT |
|------|-------|--------|
| **抽象层级** | `SqlRunner` 接口 | `RDBMSConnector` 基类 |
| **ORM 使用** | 部分使用 (MSSQL) | SQLAlchemy 2.x 全面使用 |
| **连接池** | 依赖底层驱动 | SQLAlchemy 连接池管理 |
| **异步支持** |  原生 async/await |  原生 async/await |
| **查询构建** | 原始 SQL 字符串 | 原始 SQL + SQLAlchemy Core |

### 6.3 安全机制对比

| 安全特性 | Vanna | DB-GPT |
|----------|-------|--------|
| **SQL 注入防护** |  无内置防护 | ⚠️ 参数化查询支持 |
| **权限控制** |  基于用户组 |  多租户 + RBAC |
| **审计日志** |  完整框架 |  内置审计 |
| **行级安全** |  通过 transform_args |  数据库 RLS + 应用层 |
| **SQL 校验** | ⚠️ 简单类型检查 |  SQL 解析和校验 |

### 6.4 连接管理对比

```python
# Vanna: 每查询新建连接（简单模式）
conn = psycopg2.connect(...)
cursor.execute(sql)
results = cursor.fetchall()
conn.close()

# DB-GPT: 连接池管理（生产模式）
from sqlalchemy import create_engine, text
engine = create_engine(url, pool_size=5, max_overflow=10)
with engine.connect() as conn:
    result = conn.execute(text(sql))
    return pd.DataFrame(result.fetchall())
```

### 6.5 优劣分析

**Vanna 优势**:
1. **架构简洁**: 仅一个抽象方法，易于理解和实现
2. **轻量级**: 最小依赖，快速集成
3. **灵活性高**: 不对 SQL 做过多干预，保留原生能力

**Vanna 劣势**:
1. **无连接池**: 频繁查询场景性能不佳
2. **安全薄弱**: 缺乏 SQL 注入防护和查询白名单
3. **功能单一**: 仅支持查询执行，无元数据管理

**DB-GPT 优势**:
1. **企业级**: 完整的多租户、RBAC、审计
2. **SQLAlchemy**: 成熟的 ORM 和连接池管理
3. **元数据**: 自动获取表结构、索引等元数据

**DB-GPT 劣势**:
1. **架构复杂**: 需要理解 SQLAlchemy 和整个框架
2. **依赖较重**: 需要安装完整的 dbgpt 生态

### 6.6 技术选型建议

| 场景 | 推荐选择 |
|------|----------|
| 快速原型开发 | Vanna (简单直接) |
| 企业级生产环境 | DB-GPT (安全完整) |
| 需要连接池优化 | DB-GPT |
| 多数据源动态切换 | DB-GPT |
| 轻量级嵌入式分析 | Vanna + DuckDB |
| 严格的 SQL 安全控制 | DB-GPT |

---

## 7. 数据血缘追踪

### 7.1 Vanna 现状

**结论**: Vanna **不支持**数据血缘追踪功能

通过代码搜索确认：
- 无 `lineage`、`provenance`、`data flow` 相关实现
- 仅提供基础的审计日志（谁在什么时间执行了什么查询）
- 无列级/表级血缘关系追踪

### 7.2 建议实现方案

如需在 Vanna 中实现血缘追踪，可考虑以下方案：

```python
class LineageTracker:
    """SQL 血缘追踪器"""
    
    def extract_lineage(self, sql: str) -> LineageResult:
        """解析 SQL 提取血缘关系"""
        # 使用 sqlparse 或 sqlglot 解析 SQL
        # 提取 Source Tables -> Target Tables 关系
        pass
    
    def track_query(self, user: User, sql: str, result_df: pd.DataFrame):
        """记录查询血缘"""
        lineage = self.extract_lineage(sql)
        self.store_lineage(
            query_id=generate_id(),
            user_id=user.id,
            sources=lineage.source_tables,
            targets=lineage.target_tables,
            columns=lineage.column_mappings,
            timestamp=datetime.utcnow()
        )
```

### 7.3 与 DB-GPT 对比

DB-GPT 同样未在分析文档中提及数据血缘功能，两者在此方面都处于空白状态。

---

## 8. 总结与建议

### 8.1 核心发现

| 维度 | 评价 |
|------|------|
| **数据源覆盖** | ⭐⭐⭐⭐☆ 支持 11 种主流数据库 |
| **架构设计** | ⭐⭐⭐⭐⭐ 简洁优雅，易于扩展 |
| **连接管理** | ⭐⭐⭐☆☆ 无连接池，适合低频场景 |
| **安全防护** | ⭐⭐☆☆☆ 依赖外部权限控制 |
| **审计追溯** | ⭐⭐⭐⭐☆ 完善的审计框架 |
| **数据血缘** | ⭐☆☆☆☆ 无内置支持 |

### 8.2 使用建议

**适合场景**:
- 快速搭建 SQL 问答原型
- 内部工具/数据分析场景
- 配合只读数据库使用
- DuckDB 等嵌入式分析

**不适合场景**:
- 高并发生产环境
- 需要严格 SQL 安全控制的场景
- 多租户 SaaS 产品
- 需要数据血缘追踪的企业级数据平台

### 8.3 改进建议

1. **添加 SQL 注入防护**
   - 实现 SQL 语法白名单
   - 支持只读模式配置
   - 添加危险操作拦截

2. **增强连接管理**
   - 引入连接池支持
   - 添加连接健康检查
   - 支持连接复用配置

3. **完善元数据管理**
   - 自动获取表结构
   - 缓存元数据信息
   - 支持 Schema 版本管理

4. **数据血缘追踪**
   - 集成 SQL 解析器
   - 记录列级血缘关系
   - 提供血缘可视化

---

**参考文件**:
- `src/vanna/capabilities/sql_runner/base.py` - SQL Runner 抽象接口
- `src/vanna/integrations/*/sql_runner.py` - 各数据库实现
- `src/vanna/tools/run_sql.py` - SQL 执行工具
- `src/vanna/core/registry.py` - 工具注册和权限控制
- `src/vanna/core/audit/base.py` - 审计日志框架
