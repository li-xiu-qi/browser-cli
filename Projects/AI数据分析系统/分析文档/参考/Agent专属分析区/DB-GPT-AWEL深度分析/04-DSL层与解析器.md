# 04-DSL 层与解析器

**分析对象**: AWEL DSL (声明式工作流语言)  
**分析日期**: 2026-02-08

---

## TL;DR

AWEL DSL 是一个 **SQL-like 的声明式语言**，用于定义 LLM 工作流。核心组件：**词法分析器** → **语法分析器** → **AST** → **代码生成** → **Python 执行**。

---

## 1. 为什么需要 DSL?

### 1.1 目标用户

```
Python 开发者 → AgentFream 层
数据分析师 → DSL 层
业务人员 → 可视化工具 (基于 DSL)
```

### 1.2 DSL 的优势

| 优势 | 说明 |
|------|------|
| **声明式** | 描述"做什么"而非"怎么做" |
| **可读性** | SQL-like 语法，降低学习成本 |
| **可验证** | 语法检查提前发现错误 |
| **可优化** | 编译期进行执行计划优化 |
| **可视化** | 容易转换为流程图 |

---

## 2. DSL 语法设计

### 2.1 完整语法规范 (EBNF)

```ebnf
(* 工作流定义 *)
workflow_definition ::= 
    "CREATE" "WORKFLOW" identifier "AS"
    "BEGIN"
        statement_list
    "END" ";"

(* 语句列表 *)
statement_list ::= 
    statement { statement }

(* 语句类型 *)
statement ::=
    data_declaration
    | data_transformation
    | data_retrieval
    | llm_application
    | conditional_branch
    | error_handling
    | response_statement

(* 数据声明：数据源 *)
data_declaration ::=
    "DATA" identifier "=" 
    ( receive_request | load_from_source ) ";"

receive_request ::=
    "RECEIVE" "REQUEST" "FROM" source_definition

source_definition ::=
    http_source
    | kafka_source
    | db_source
    | file_source

http_source ::=
    "http_source" "(" 
        string_literal 
        ["," "method" "=" string_literal]
        ["," "auth" "=" auth_config]
    ")"

(* 数据转换 *)
data_transformation ::=
    "DATA" identifier "=" 
    "TRANSFORM" identifier 
    "USING" operator_call 
    [error_clause] ";"

operator_call ::=
    identifier "(" [parameter_list] ")"

parameter_list ::=
    parameter {"," parameter}

parameter ::=
    identifier "=" literal

(* 数据检索 *)
data_retrieval ::=
    "DATA" identifier "=" 
    "RETRIEVE" "DATA" "FROM" storage_definition
    ["ON" "KEY" expression]
    [error_clause] ";"

storage_definition ::=
    vector_store
    | database
    | cache

vector_store ::=
    "vstore" "(" 
        "database" "=" string_literal
        ["," "collection" "=" string_literal]
        ["," "top_k" "=" integer]
    ")"

(* LLM 应用 *)
llm_application ::=
    "DATA" identifier "=" 
    "APPLY" "LLM" string_literal
    "WITH" "DATA" identifier
    ["AND" "PARAMETERS" "(" parameter_list ")"]
    [error_clause] ";"

(* 条件分支 *)
conditional_branch ::=
    "IF" boolean_expression "THEN"
        statement_list
    ["ELSE" statement_list]
    "END" "IF" ";"

boolean_expression ::=
    expression comparison_operator expression
    | identifier

comparison_operator ::=
    "=" | "!=" | "<" | ">" | "<=" | ">="

(* 错误处理 *)
error_clause ::=
    "ON" "ERROR" error_action

error_action ::=
    "FAIL"
    | "RETRY" integer ["TIMES"]
    | "LOG" string_literal
    | "FALLBACK" "TO" identifier

(* 响应 *)
response_statement ::=
    "RESPOND" "TO" identifier "WITH" identifier
    [error_clause] ";"

(* 基本元素 *)
identifier ::= letter {letter | digit | "_"}
string_literal ::= "'" {character} "'" | """ {character} """
integer ::= digit {digit}
float ::= digit {digit} "." digit {digit}
boolean ::= "TRUE" | "FALSE"
literal ::= string_literal | integer | float | boolean | null
```

---

## 3. DSL 示例

### 3.1 简单 RAG 工作流

```sql
-- RAG 聊天工作流
CREATE WORKFLOW rag_chat AS
BEGIN
    -- 1. 接收 HTTP 请求
    DATA request = RECEIVE REQUEST FROM 
        http_source('/api/chat', method = 'POST');
    
    -- 2. 提取查询内容
    DATA query = EXTRACT query FROM request;
    
    -- 3. 向量化查询
    DATA query_embedding = TRANSFORM query 
        USING embedding(model = 'text2vec');
    
    -- 4. 检索相关文档
    DATA docs = RETRIEVE DATA 
        FROM vstore(
            database = 'chromadb',
            collection = 'knowledge_base',
            top_k = 5
        )
        ON KEY query_embedding
        ON ERROR RETRY 3 TIMES;
    
    -- 5. 构建提示词
    DATA prompt = CONSTRUCT PROMPT 
        TEMPLATE 'rag_v2'
        WITH query, docs;
    
    -- 6. 调用 LLM 生成回复
    DATA response = APPLY LLM 'gpt-4'
        WITH DATA prompt
        AND PARAMETERS (
            temperature = 0.7,
            max_tokens = 2000,
            stream = TRUE
        )
        ON ERROR FALLBACK TO default_response;
    
    -- 7. 返回 HTTP 响应
    RESPOND TO request WITH response
        ON ERROR LOG 'Failed to send response';
END;
```

### 3.2 数据分析工作流

```sql
-- 销售数据分析
CREATE WORKFLOW sales_analysis AS
BEGIN
    -- 1. 从数据库加载数据
    DATA raw_data = LOAD FROM db_source(
        connection = 'sales_db',
        query = 'SELECT * FROM orders WHERE date >= CURRENT_DATE - 30'
    );
    
    -- 2. 数据清洗
    DATA clean_data = TRANSFORM raw_data
        USING pipeline(
            filter(amount > 0),
            drop_duplicates(),
            fillna(strategy = 'mean')
        );
    
    -- 3. 分组聚合
    DATA daily_stats = TRANSFORM clean_data
        USING aggregate(
            group_by = 'date',
            metrics = {
                total_revenue: sum(amount),
                order_count: count(*),
                avg_order_value: mean(amount)
            }
        );
    
    -- 4. 异常检测
    DATA anomalies = TRANSFORM daily_stats
        USING detect_anomalies(
            column = 'total_revenue',
            method = 'zscore',
            threshold = 3.0
        );
    
    -- 5. 生成分析报告
    DATA report_prompt = CONSTRUCT PROMPT
        TEMPLATE 'sales_report'
        WITH daily_stats, anomalies;
    
    DATA report = APPLY LLM 'gpt-4'
        WITH DATA report_prompt
        AND PARAMETERS (temperature = 0.3);
    
    -- 6. 保存报告
    WRITE report TO file_sink(
        path = '/reports/daily_sales.md',
        format = 'markdown'
    );
    
    -- 7. 发送邮件通知
    SEND EMAIL TO 'manager@company.com'
        WITH ATTACHMENT report
        ON ERROR LOG 'Email send failed';
END;
```

### 3.3 条件分支工作流

```sql
-- 智能客服路由
CREATE WORKFLOW customer_support AS
BEGIN
    DATA ticket = RECEIVE REQUEST FROM 
        http_source('/api/tickets', method = 'POST');
    
    DATA intent = CLASSIFY intent OF ticket
        USING classifier(model = 'intent-v2');
    
    -- 根据意图路由到不同处理流程
    IF intent.category = 'technical' THEN
        DATA solution = APPLY LLM 'tech-support-gpt'
            WITH DATA ticket
            AND PARAMETERS (temperature = 0.2);
        
        DATA response = FORMAT solution 
            USING template('technical_response');
            
    ELSE IF intent.category = 'billing' THEN
        DATA account_info = RETRIEVE DATA 
            FROM db_source(
                query = 'SELECT * FROM accounts WHERE id = {ticket.user_id}'
            );
        
        DATA solution = APPLY LLM 'billing-gpt'
            WITH DATA ticket, account_info;
            
        DATA response = FORMAT solution 
            USING template('billing_response');
            
    ELSE
        DATA solution = APPLY LLM 'general-gpt'
            WITH DATA ticket;
            
        DATA response = FORMAT solution 
            USING template('general_response');
    END IF;
    
    -- 记录处理日志
    LOG processing_result(
        ticket_id = ticket.id,
        intent = intent.category,
        response_type = 'automated'
    );
    
    RESPOND TO ticket WITH response;
END;
```

---

## 4. 解析器实现

### 4.1 词法分析器 (Lexer)

```python
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, Optional

class TokenType(Enum):
    # 关键字
    CREATE = auto()
    WORKFLOW = auto()
    AS = auto()
    BEGIN = auto()
    END = auto()
    DATA = auto()
    RECEIVE = auto()
    REQUEST = auto()
    FROM = auto()
    USING = auto()
    TRANSFORM = auto()
    RETRIEVE = auto()
    APPLY = auto()
    LLM = auto()
    WITH = auto()
    AND = auto()
    PARAMETERS = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    RESPOND = auto()
    TO = auto()
    ON = auto()
    ERROR = auto()
    FAIL = auto()
    RETRY = auto()
    TIMES = auto()
    LOG = auto()
    FALLBACK = auto()
    
    # 标识符和字面量
    IDENTIFIER = auto()
    STRING = auto()
    INTEGER = auto()
    FLOAT = auto()
    BOOLEAN = auto()
    NULL = auto()
    
    # 运算符
    EQUALS = auto()           # =
    NOT_EQUALS = auto()       # !=
    LESS_THAN = auto()        # <
    GREATER_THAN = auto()     # >
    LESS_EQ = auto()          # <=
    GREATER_EQ = auto()       # >=
    
    # 分隔符
    LPAREN = auto()           # (
    RPAREN = auto()           # )
    LBRACE = auto()           # {
    RBRACE = auto()           # }
    COMMA = auto()            # ,
    SEMICOLON = auto()        # ;
    DOT = auto()              # .
    
    EOF = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class Lexer:
    """AWEL DSL 词法分析器"""
    
    KEYWORDS = {
        'CREATE': TokenType.CREATE,
        'WORKFLOW': TokenType.WORKFLOW,
        'AS': TokenType.AS,
        'BEGIN': TokenType.BEGIN,
        'END': TokenType.END,
        'DATA': TokenType.DATA,
        'RECEIVE': TokenType.RECEIVE,
        'REQUEST': TokenType.REQUEST,
        'FROM': TokenType.FROM,
        'USING': TokenType.USING,
        'TRANSFORM': TokenType.TRANSFORM,
        'RETRIEVE': TokenType.RETRIEVE,
        'APPLY': TokenType.APPLY,
        'LLM': TokenType.LLM,
        'WITH': TokenType.WITH,
        'AND': TokenType.AND,
        'PARAMETERS': TokenType.PARAMETERS,
        'IF': TokenType.IF,
        'THEN': TokenType.THEN,
        'ELSE': TokenType.ELSE,
        'RESPOND': TokenType.RESPOND,
        'TO': TokenType.TO,
        'ON': TokenType.ON,
        'ERROR': TokenType.ERROR,
        'FAIL': TokenType.FAIL,
        'RETRY': TokenType.RETRY,
        'TIMES': TokenType.TIMES,
        'LOG': TokenType.LOG,
        'FALLBACK': TokenType.FALLBACK,
        'TRUE': TokenType.BOOLEAN,
        'FALSE': TokenType.BOOLEAN,
        'NULL': TokenType.NULL,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def error(self, msg: str):
        raise SyntaxError(
            f"{msg} at line {self.line}, column {self.column}"
        )
    
    def peek(self, offset: int = 0) -> str:
        pos = self.pos + offset
        if pos >= len(self.source):
            return '\0'
        return self.source[pos]
    
    def advance(self) -> str:
        char = self.peek()
        self.pos += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
    
    def skip_whitespace(self):
        while self.peek() in ' \t\n\r':
            self.advance()
    
    def skip_comment(self):
        if self.peek() == '-' and self.peek(1) == '-':
            while self.peek() != '\n' and self.peek() != '\0':
                self.advance()
    
    def read_string(self) -> str:
        quote = self.advance()  # ' or "
        value = []
        while self.peek() != quote:
            if self.peek() == '\0':
                self.error("Unterminated string")
            if self.peek() == '\\':
                self.advance()
                escape = self.advance()
                value.append(self._escape_char(escape))
            else:
                value.append(self.advance())
        self.advance()  # closing quote
        return ''.join(value)
    
    def _escape_char(self, char: str) -> str:
        escapes = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', '"': '"', "'": "'"}
        return escapes.get(char, char)
    
    def read_number(self) -> Token:
        start_line, start_col = self.line, self.column
        value = []
        
        while self.peek().isdigit():
            value.append(self.advance())
        
        if self.peek() == '.' and self.peek(1).isdigit():
            value.append(self.advance())  # .
            while self.peek().isdigit():
                value.append(self.advance())
            return Token(
                TokenType.FLOAT, 
                ''.join(value), 
                start_line, 
                start_col
            )
        
        return Token(
            TokenType.INTEGER, 
            ''.join(value), 
            start_line, 
            start_col
        )
    
    def read_identifier(self) -> Token:
        start_line, start_col = self.line, self.column
        value = []
        
        while (self.peek().isalnum() or self.peek() == '_'):
            value.append(self.advance())
        
        text = ''.join(value)
        token_type = self.KEYWORDS.get(text.upper(), TokenType.IDENTIFIER)
        
        return Token(token_type, text, start_line, start_col)
    
    def tokenize(self) -> List[Token]:
        """词法分析主入口"""
        while self.peek() != '\0':
            self.skip_whitespace()
            self.skip_comment()
            
            if self.peek() == '\0':
                break
            
            start_line, start_col = self.line, self.column
            char = self.peek()
            
            # 字符串
            if char in '"\'':
                value = self.read_string()
                self.tokens.append(Token(
                    TokenType.STRING, value, start_line, start_col
                ))
            
            # 数字
            elif char.isdigit():
                self.tokens.append(self.read_number())
            
            # 标识符/关键字
            elif char.isalpha() or char == '_':
                self.tokens.append(self.read_identifier())
            
            # 运算符和分隔符
            elif char == '(':
                self.advance()
                self.tokens.append(Token(TokenType.LPAREN, '(', start_line, start_col))
            elif char == ')':
                self.advance()
                self.tokens.append(Token(TokenType.RPAREN, ')', start_line, start_col))
            elif char == '{':
                self.advance()
                self.tokens.append(Token(TokenType.LBRACE, '{', start_line, start_col))
            elif char == '}':
                self.advance()
                self.tokens.append(Token(TokenType.RBRACE, '}', start_line, start_col))
            elif char == ',':
                self.advance()
                self.tokens.append(Token(TokenType.COMMA, ',', start_line, start_col))
            elif char == ';':
                self.advance()
                self.tokens.append(Token(TokenType.SEMICOLON, ';', start_line, start_col))
            elif char == '.':
                self.advance()
                self.tokens.append(Token(TokenType.DOT, '.', start_line, start_col))
            elif char == '=':
                self.advance()
                self.tokens.append(Token(TokenType.EQUALS, '=', start_line, start_col))
            elif char == '<':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.LESS_EQ, '<=', start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.LESS_THAN, '<', start_line, start_col))
            elif char == '>':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.GREATER_EQ, '>=', start_line, start_col))
                else:
                    self.tokens.append(Token(TokenType.GREATER_THAN, '>', start_line, start_col))
            elif char == '!':
                self.advance()
                if self.peek() == '=':
                    self.advance()
                    self.tokens.append(Token(TokenType.NOT_EQUALS, '!=', start_line, start_col))
                else:
                    self.error("Unexpected character: !")
            else:
                self.error(f"Unexpected character: {char}")
        
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens
```

### 4.2 语法分析器 (Parser)

```python
from typing import Optional

# AST 节点定义
@dataclass
class ASTNode:
    """AST 基类"""
    line: int
    column: int

@dataclass
class WorkflowNode(ASTNode):
    """工作流定义节点"""
    name: str
    statements: List[ASTNode]

@dataclass
class DataDeclarationNode(ASTNode):
    """数据声明节点"""
    var_name: str
    source: ASTNode

@dataclass
class HttpSourceNode(ASTNode):
    """HTTP 源节点"""
    path: str
    method: str
    auth: Optional[dict]

@dataclass
class TransformNode(ASTNode):
    """转换节点"""
    input_var: str
    output_var: str
    operator: str
    params: dict
    error_handler: Optional[ASTNode]

@dataclass
class RetrieveNode(ASTNode):
    """检索节点"""
    output_var: str
    storage: str
    storage_params: dict
    key: str
    error_handler: Optional[ASTNode]

@dataclass
class LLMApplyNode(ASTNode):
    """LLM 应用节点"""
    output_var: str
    model: str
    input_var: str
    params: dict
    error_handler: Optional[ASTNode]

@dataclass
class IfNode(ASTNode):
    """条件分支节点"""
    condition: ASTNode
    then_branch: List[ASTNode]
    else_branch: Optional[List[ASTNode]]

@dataclass
class RespondNode(ASTNode):
    """响应节点"""
    target: str
    data: str
    error_handler: Optional[ASTNode]

@dataclass
class ErrorHandlerNode(ASTNode):
    """错误处理节点"""
    action: str  # FAIL, RETRY, LOG, FALLBACK
    params: dict

class Parser:
    """AWEL DSL 语法分析器"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def peek(self, offset: int = 0) -> Token:
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]  # EOF
        return self.tokens[pos]
    
    def advance(self) -> Token:
        token = self.peek()
        self.pos += 1
        return token
    
    def expect(self, token_type: TokenType) -> Token:
        """期望特定类型的 token"""
        token = self.peek()
        if token.type != token_type:
            raise SyntaxError(
                f"Expected {token_type.name}, got {token.type.name} "
                f"at line {token.line}"
            )
        return self.advance()
    
    def match(self, *token_types: TokenType) -> bool:
        """检查当前 token 是否匹配任一类型"""
        return self.peek().type in token_types
    
    def parse(self) -> WorkflowNode:
        """语法分析入口"""
        return self.parse_workflow()
    
    def parse_workflow(self) -> WorkflowNode:
        """解析工作流定义"""
        start_token = self.expect(TokenType.CREATE)
        self.expect(TokenType.WORKFLOW)
        name_token = self.expect(TokenType.IDENTIFIER)
        self.expect(TokenType.AS)
        self.expect(TokenType.BEGIN)
        
        statements = []
        while not self.match(TokenType.END):
            statements.append(self.parse_statement())
        
        self.expect(TokenType.END)
        self.expect(TokenType.SEMICOLON)
        
        return WorkflowNode(
            line=start_token.line,
            column=start_token.column,
            name=name_token.value,
            statements=statements
        )
    
    def parse_statement(self) -> ASTNode:
        """解析语句"""
        if self.match(TokenType.DATA):
            return self.parse_data_statement()
        elif self.match(TokenType.IF):
            return self.parse_if_statement()
        elif self.match(TokenType.RESPOND):
            return self.parse_respond_statement()
        else:
            raise SyntaxError(
                f"Unexpected token {self.peek().type.name} at line {self.peek().line}"
            )
    
    def parse_data_statement(self) -> ASTNode:
        """解析数据声明/转换语句"""
        start_token = self.advance()  # DATA
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.EQUALS)
        
        if self.match(TokenType.RECEIVE):
            return self.parse_receive_statement(start_token, var_name)
        elif self.match(TokenType.TRANSFORM):
            return self.parse_transform_statement(start_token, var_name)
        elif self.match(TokenType.RETRIEVE):
            return self.parse_retrieve_statement(start_token, var_name)
        elif self.match(TokenType.APPLY):
            return self.parse_apply_statement(start_token, var_name)
        else:
            raise SyntaxError(
                f"Expected RECEIVE, TRANSFORM, RETRIEVE, or APPLY, "
                f"got {self.peek().type.name}"
            )
    
    def parse_receive_statement(
        self, 
        start_token: Token, 
        var_name: str
    ) -> DataDeclarationNode:
        """解析 RECEIVE 语句"""
        self.advance()  # RECEIVE
        self.expect(TokenType.REQUEST)
        self.expect(TokenType.FROM)
        
        source = self.parse_source()
        error_handler = self.parse_error_clause()
        self.expect(TokenType.SEMICOLON)
        
        return DataDeclarationNode(
            line=start_token.line,
            column=start_token.column,
            var_name=var_name,
            source=source
        )
    
    def parse_source(self) -> ASTNode:
        """解析数据源定义"""
        if self.match(TokenType.IDENTIFIER):
            func_name = self.advance().value
            if func_name == 'http_source':
                return self.parse_http_source()
            # ... 其他源类型
        raise SyntaxError(f"Unknown source type at line {self.peek().line}")
    
    def parse_http_source(self) -> HttpSourceNode:
        """解析 http_source 调用"""
        start_token = self.peek()
        self.expect(TokenType.LPAREN)
        path = self.expect(TokenType.STRING).value
        
        method = 'GET'
        auth = None
        
        if self.match(TokenType.COMMA):
            self.advance()
            params = self.parse_parameter_list()
            method = params.get('method', 'GET')
            auth = params.get('auth')
        
        self.expect(TokenType.RPAREN)
        
        return HttpSourceNode(
            line=start_token.line,
            column=start_token.column,
            path=path,
            method=method,
            auth=auth
        )
    
    def parse_parameter_list(self) -> dict:
        """解析参数列表"""
        params = {}
        while True:
            key = self.expect(TokenType.IDENTIFIER).value
            self.expect(TokenType.EQUALS)
            value = self.parse_value()
            params[key] = value
            
            if self.match(TokenType.COMMA):
                self.advance()
            else:
                break
        return params
    
    def parse_value(self):
        """解析值（字符串、数字、布尔等）"""
        if self.match(TokenType.STRING):
            return self.advance().value
        elif self.match(TokenType.INTEGER):
            return int(self.advance().value)
        elif self.match(TokenType.FLOAT):
            return float(self.advance().value)
        elif self.match(TokenType.BOOLEAN):
            return self.advance().value.upper() == 'TRUE'
        elif self.match(TokenType.NULL):
            self.advance()
            return None
        else:
            raise SyntaxError(f"Expected value, got {self.peek().type.name}")
    
    def parse_error_clause(self) -> Optional[ErrorHandlerNode]:
        """解析错误处理子句"""
        if not self.match(TokenType.ON):
            return None
        
        self.advance()  # ON
        self.expect(TokenType.ERROR)
        
        if self.match(TokenType.FAIL):
            self.advance()
            return ErrorHandlerNode(
                line=self.peek().line,
                column=self.peek().column,
                action='FAIL',
                params={}
            )
        elif self.match(TokenType.RETRY):
            self.advance()
            count = int(self.expect(TokenType.INTEGER).value)
            if self.match(TokenType.TIMES):
                self.advance()
            return ErrorHandlerNode(
                line=self.peek().line,
                column=self.peek().column,
                action='RETRY',
                params={'count': count}
            )
        elif self.match(TokenType.LOG):
            self.advance()
            message = self.expect(TokenType.STRING).value
            return ErrorHandlerNode(
                line=self.peek().line,
                column=self.peek().column,
                action='LOG',
                params={'message': message}
            )
        # ... 其他错误处理
        
        return None
```

### 4.3 代码生成器

```python
class CodeGenerator:
    """将 AST 转换为 Python/AgentFream 代码"""
    
    def __init__(self):
        self.indent_level = 0
        self.code_lines = []
    
    def indent(self) -> str:
        """返回当前缩进"""
        return "    " * self.indent_level
    
    def emit(self, line: str):
        """添加代码行"""
        self.code_lines.append(self.indent() + line)
    
    def generate(self, node: ASTNode) -> str:
        """代码生成入口"""
        self.visit(node)
        return '\n'.join(self.code_lines)
    
    def visit(self, node: ASTNode):
        """访问者模式分发"""
        method_name = f'visit_{node.__class__.__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node: ASTNode):
        raise NotImplementedError(f"No visitor for {type(node)}")
    
    def visit_WorkflowNode(self, node: WorkflowNode):
        """生成工作流代码"""
        self.emit("from dbgpt.awel import *")
        self.emit("")
        self.emit(f"# Auto-generated from DSL: {node.name}")
        self.emit(f"def create_{node.name}_workflow():")
        self.indent_level += 1
        
        # 生成语句
        for stmt in node.statements:
            self.visit(stmt)
        
        self.emit("return dag")
        self.indent_level -= 1
    
    def visit_DataDeclarationNode(self, node: DataDeclarationNode):
        """生成数据声明代码"""
        source_code = self.visit(node.source)
        self.emit(f"# Data: {node.var_name}")
        self.emit(f"{node.var_name} = {source_code}")
    
    def visit_HttpSourceNode(self, node: HttpSourceNode):
        """生成 HTTP Source 代码"""
        return f"HttpTrigger(path='{node.path}', method='{node.method}')"
    
    def visit_TransformNode(self, node: TransformNode):
        """生成转换代码"""
        params_str = ', '.join(f"{k}={repr(v)}" for k, v in node.params.items())
        self.emit(f"# Transform: {node.output_var}")
        self.emit(f"{node.output_var} = {node.input_var}")
        self.indent_level += 1
        self.emit(f".transform('{node.operator}', {params_str})")
        self.indent_level -= 1
    
    def visit_LLMApplyNode(self, node: LLMApplyNode):
        """生成 LLM 应用代码"""
        params_str = ', '.join(f"{k}={repr(v)}" for k, v in node.params.items())
        self.emit(f"# LLM Application: {node.output_var}")
        self.emit(f"{node.output_var} = AgentFream({node.input_var})")
        self.indent_level += 1
        self.emit(f".llm(model='{node.model}', {params_str})")
        self.indent_level -= 1
```

---

## 5. 完整转换示例

```python
# DSL 代码
dsl_code = """
CREATE WORKFLOW simple_rag AS
BEGIN
    DATA request = RECEIVE REQUEST FROM http_source('/api/chat');
    DATA query = EXTRACT query FROM request;
    DATA response = APPLY LLM 'gpt-4' WITH DATA query;
    RESPOND TO request WITH response;
END;
"""

# 转换过程
lexer = Lexer(dsl_code)
tokens = lexer.tokenize()

parser = Parser(tokens)
ast = parser.parse()

generator = CodeGenerator()
python_code = generator.generate(ast)

# 生成的 Python 代码
print(python_code)
"""
from dbgpt.awel import *

# Auto-generated from DSL: simple_rag
def create_simple_rag_workflow():
    # Data: request
    request = HttpTrigger(path='/api/chat', method='GET')
    # Data: query
    query = request
        .extract('query')
    # LLM Application: response
    response = AgentFream(query)
        .llm(model='gpt-4', temperature=0.7)
    # Response
    response.respond_to(request)
    return dag
"""
```

---

## 6. 总结

AWEL DSL 的核心设计：

1. **SQL-like 语法** - 降低学习门槛
2. **声明式编程** - 描述意图而非实现
3. **完整工具链** - Lexer → Parser → AST → CodeGen
4. **可扩展** - 容易添加新算子和语法

---

*分析完成于 2026-02-08*
