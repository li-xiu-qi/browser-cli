# RAGFlow SSO 改造方案

**文档版本**: 1.0  
**日期**: 2026-02-05  
**目标**: 将 RAGFlow 从本地账号体系改造为企业级 SSO 支持

---

## 一、现状分析

### 1.1 当前认证架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAGFlow 当前认证流程                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  用户 ──► 登录页 ──► 输入账号密码 ──► User表验证 ──► JWT Token   │
│            │                           (MySQL)                   │
│            ▼                                                     │
│    ┌───────────────┐                                             │
│    │  可选: OAuth  │  用GitHub/Google账号登录RAGFlow              │
│    │  (作为Client) │                                             │
│    └───────────────┘                                             │
│                                                                  │
│  核心问题：                                                       │
│  • 用户必须在RAGFlow中注册账号                                   │
│  • 不支持企业已有的统一身份认证接入                              │
│  • 无法实现"企业微信/钉钉一键登录"                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 数据库模型

```python
# 当前 User 表结构（api/db/db_models.py）

class User(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    email = CharField(max_length=255, unique=True, index=True)  # 登录账号
    password = CharField(max_length=255)                         # 加密密码
    nickname = CharField(max_length=255)                        # 昵称
    avatar = TextField(null=True)                               # 头像
    
    # 当前缺失字段：
    # - 外部身份源标识 (idp_id)
    # - 外部用户唯一标识 (external_user_id)
    # - 单点登录会话信息 (sso_session)
```

---

## 二、改造目标

### 2.1 目标架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    SSO改造后架构                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                   企业身份中心 (IdP)                      │   │
│   │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │   │
│   │  │企业微信  │  │  钉钉   │  │  LDAP   │  │ SAML IdP│    │   │
│   │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘    │   │
│   │       └─────────────┴─────────────┴─────────────┘       │   │
│   │                         │                               │   │
│   │              统一认证网关 (SSO Gateway)                  │   │
│   └─────────────────────────┬───────────────────────────────┘   │
│                             │ SAML/OIDC/LDAP                   │
│                             ▼                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │              RAGFlow (作为 Service Provider)             │   │
│   │                                                         │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │   │
│   │  │SAML Handler │  │OIDC Handler │  │  LDAP Handler   │ │   │
│   │  │(saml.py)    │  │(oidc_sp.py) │  │  (ldap_auth.py) │ │   │
│   │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘ │   │
│   │         └─────────────────┴──────────────────┘          │   │
│   │                           │                             │   │
│   │                    ┌──────┴──────┐                      │   │
│   │                    │ Auth Router │                      │   │
│   │                    │  (统一入口) │                      │   │
│   │                    └──────┬──────┘                      │   │
│   │                           ▼                             │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │   │
│   │  │  User表改造  │  │SSO Session  │  │  Tenant绑定    │ │   │
│   │  │(关联外部ID) │  │  (Redis)    │  │ (自动创建租户) │ │   │
│   │  └─────────────┘  └─────────────┘  └─────────────────┘ │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 支持的协议

| 协议 | 优先级 | 适用场景 | 实现难度 |
|------|--------|----------|----------|
| **SAML 2.0** | P0 | 传统企业（用AD/LDAP的企业） | 中 |
| **OIDC** | P0 | 现代云原生企业 | 低 |
| **LDAP/AD** | P1 | 内网直接对接AD域控 | 中 |
| **OAuth 2.0** | P2 | 第三方登录（已有） | - |

---

## 三、改造方案

### 3.1 数据库改造

#### 3.1.1 User 表扩展

```python
# api/db/db_models.py

class User(DataBaseModel):
    # ===== 已有字段 =====
    id = CharField(max_length=32, primary_key=True)
    email = CharField(max_length=255, index=True)  # 改为非唯一，允许不同IdP相同email
    password = CharField(max_length=255, null=True)  # 改为nullable，SSO用户无密码
    nickname = CharField(max_length=255)
    avatar = TextField(null=True)
    
    # ===== SSO新增字段 =====
    # 身份源标识
    idp_id = CharField(max_length=64, null=True, index=True, help_text="身份源ID: oidc/google/saml/ldap")
    
    # 外部用户唯一标识
    external_user_id = CharField(max_length=255, null=True, index=True, help_text="IdP返回的用户唯一标识")
    
    # 用户来源类型
    auth_type = CharField(max_length=32, default="local", help_text="local/oauth/saml/oidc/ldap")
    
    # SSO专属属性（JSON存储）
    sso_attributes = JSONField(null=True, help_text="IdP返回的用户属性")
    
    # 最后登录的SSO会话标识
    sso_session_index = CharField(max_length=255, null=True, help_text="SAML SessionIndex")
    
    # 用户状态
    status = CharField(max_length=32, default="active", help_text="active/disabled")
    
    class Meta:
        db_table = "user"
        indexes = (
            # 联合唯一索引：同一IdP下external_user_id唯一
            (('idp_id', 'external_user_id'), True),
        )


# 新增：身份源配置表（管理员配置）
class IdentityProvider(DataBaseModel):
    """企业身份源配置"""
    id = CharField(max_length=32, primary_key=True)
    name = CharField(max_length=128, help_text="显示名称：企业微信/钉钉")
    
    # 协议类型
    protocol = CharField(max_length=32, help_text="saml/oidc/ldap/oauth")
    
    # 是否启用
    enabled = BooleanField(default=True)
    
    # 协议特定配置（JSON）
    config = JSONField(help_text="协议配置参数")
    
    # 属性映射配置
    attribute_mapping = JSONField(help_text="字段映射：email->user_email, name->user_name")
    
    # 自动创建租户
    auto_create_tenant = BooleanField(default=True)
    
    # 默认租户角色
    default_role = CharField(max_length=32, default="owner", help_text="owner/admin/user")
    
    class Meta:
        db_table = "identity_provider"


# 新增：SSO会话表（用于单点登出SLO）
class SSOSession(DataBaseModel):
    """SSO会话跟踪（支持SLO）"""
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, index=True)
    idp_id = CharField(max_length=32, index=True)
    
    # SAML特定
    saml_session_index = CharField(max_length=255, index=True, null=True)
    saml_name_id = CharField(max_length=255, null=True)
    
    # OIDC特定
    oidc_sid = CharField(max_length=255, null=True)
    
    # 会话状态
    status = CharField(max_length=32, default="active")  # active/logged_out
    
    # 过期时间
    expires_at = DateTimeField()
    
    class Meta:
        db_table = "sso_session"
```

#### 3.1.2 配置表示例

```python
# IdentityProvider 配置示例

# 1. SAML配置（对接企业ADFS/Azure AD）
{
    "id": "saml_adfs",
    "name": "企业ADFS",
    "protocol": "saml",
    "config": {
        # IdP元数据URL或XML
        "idp_metadata_url": "https://adfs.company.com/FederationMetadata/2007-06/FederationMetadata.xml",
        
        # SP配置
        "sp_entity_id": "ragflow.company.com",
        "sp_acs_url": "https://ragflow.company.com/api/v1/auth/saml/acs",
        "sp_sls_url": "https://ragflow.company.com/api/v1/auth/saml/sls",
        
        # 签名/加密
        "want_assertions_signed": True,
        "want_name_id_encrypted": False,
        
        # 证书（SP私钥和公钥）
        "sp_private_key": "-----BEGIN PRIVATE KEY-----\n...",
        "sp_certificate": "-----BEGIN CERTIFICATE-----\n..."
    },
    "attribute_mapping": {
        "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "nickname": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/displayname",
        "department": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/department"
    },
    "auto_create_tenant": True,
    "default_role": "owner"
}

# 2. OIDC配置（对接企业微信/钉钉/Azure AD）
{
    "id": "oidc_wecom",
    "name": "企业微信",
    "protocol": "oidc",
    "config": {
        "issuer": "https://login.work.weixin.qq.com",
        "client_id": "wxxxxxxxxxxxxxxxx",
        "client_secret": "xxxxxxxxxxxxxxxxxxxxxxxx",
        "redirect_uri": "https://ragflow.company.com/api/v1/auth/oidc/callback",
        "scope": "openid profile email userid",
        
        # 端点（可从.well-known自动发现）
        "authorization_endpoint": "https://login.work.weixin.qq.com/wwlogin/sso/authorize",
        "token_endpoint": "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        "userinfo_endpoint": "https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo"
    },
    "attribute_mapping": {
        "email": "email",
        "nickname": "name",
        "external_user_id": "userid"
    }
}

# 3. LDAP配置（直接对接AD域控）
{
    "id": "ldap_ad",
    "name": "Active Directory",
    "protocol": "ldap",
    "config": {
        "server_uri": "ldap://dc.company.com:389",
        "bind_dn": "CN=ragflow,OU=ServiceAccounts,DC=company,DC=com",
        "bind_password": "xxxxxxxx",
        
        # 用户搜索配置
        "user_search_base": "OU=Users,DC=company,DC=com",
        "user_search_filter": "(sAMAccountName=%(user)s)",
        
        # 属性映射
        "user_attr_map": {
            "username": "sAMAccountName",
            "email": "mail",
            "nickname": "displayName"
        },
        
        # 组/角色同步
        "group_search_base": "OU=Groups,DC=company,DC=com",
        "group_search_filter": "(member=%(userdn)s)"
    }
}
```

---

### 3.2 服务端代码改造

#### 3.2.1 目录结构扩展

```
api/apps/auth/
├── __init__.py
├── base.py                  # 认证基类
├── README.md
├── oauth.py                 # OAuth 客户端（已有）
├── oidc.py                  # OIDC 客户端（已有）
├── github.py                # GitHub登录（已有）
│
# ===== 新增 SSO Service Provider 支持 =====
├── saml.py                  # SAML SP处理器
├── oidc_sp.py               # OIDC SP处理器（服务端）
├── ldap_auth.py             # LDAP认证处理器
├── sso_router.py            # SSO统一路由
└── utils.py                 # SSO工具函数
```

#### 3.2.2 SAML SP 实现

```python
# api/apps/auth/saml.py

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from api.db.db_models import IdentityProvider, User, SSOSession
from api.db.services.user_service import UserService
from api.utils.api_utils import generate_access_token
import json


class SAMLServiceProvider:
    """SAML 2.0 Service Provider 实现"""
    
    def __init__(self, idp_config: IdentityProvider):
        self.idp = idp_config
        self.saml_settings = self._build_saml_settings()
    
    def _build_saml_settings(self) -> dict:
        """构建SAML配置"""
        config = self.idp.config
        
        return {
            "sp": {
                "entityId": config["sp_entity_id"],
                "assertionConsumerService": {
                    "url": config["sp_acs_url"],
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                },
                "singleLogoutService": {
                    "url": config["sp_sls_url"],
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": config.get("sp_certificate", ""),
                "privateKey": config.get("sp_private_key", ""),
            },
            "idp": {
                # 从metadata解析或使用配置
                "entityId": config.get("idp_entity_id"),
                "singleSignOnService": {
                    "url": config.get("idp_sso_url"),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "singleLogoutService": {
                    "url": config.get("idp_slo_url"),
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
                },
                "x509cert": config.get("idp_certificate"),
            },
            "security": {
                "nameIdEncrypted": config.get("want_name_id_encrypted", False),
                "authnRequestsSigned": config.get("sign_authn_request", True),
                "logoutRequestSigned": config.get("sign_logout_request", True),
                "wantAssertionsSigned": config.get("want_assertions_signed", True),
            }
        }
    
    def initiate_login(self, return_to: str = None) -> dict:
        """
        发起SAML登录请求（生成AuthnRequest）
        
        Returns:
            {
                "redirect_url": "https://adfs.company.com/...",
                "saml_request": "base64encoded...",
                "relay_state": "random_state_123"
            }
        """
        auth = OneLogin_Saml2_Auth({}, self.saml_settings)
        
        # 生成RelayState用于回调时验证
        relay_state = self._generate_relay_state(return_to)
        
        # 生成SAML Request
        saml_request = auth.login(return_to=relay_state)
        
        return {
            "redirect_url": saml_request,
            "relay_state": relay_state
        }
    
    def process_acs(self, saml_response: str, relay_state: str) -> dict:
        """
        处理SAML断言消费服务（Assertion Consumer Service）
        
        Args:
            saml_response: Base64编码的SAML Response
            relay_state: 用于防止CSRF的随机状态
            
        Returns:
            {
                "user": User对象,
                "token": JWT Token,
                "attributes": 用户属性
            }
        """
        # 验证RelayState
        if not self._validate_relay_state(relay_state):
            raise ValueError("Invalid relay state")
        
        # 解析SAML Response
        auth = OneLogin_Saml2_Auth({}, self.saml_settings)
        auth.process_response(saml_response)
        
        # 验证响应
        errors = auth.get_errors()
        if errors:
            raise ValueError(f"SAML Error: {', '.join(errors)}")
        
        if not auth.is_authenticated():
            raise ValueError("SAML authentication failed")
        
        # 提取用户信息
        attributes = auth.get_attributes()
        name_id = auth.get_nameid()
        session_index = auth.get_session_index()
        
        # 映射属性
        user_info = self._map_attributes(attributes, name_id)
        
        # 查找或创建用户
        user = self._find_or_create_user(user_info)
        
        # 创建SSO会话（用于SLO）
        self._create_sso_session(user, session_index, name_id)
        
        # 生成RAGFlow JWT Token
        token = generate_access_token(user)
        
        return {
            "user": user,
            "token": token,
            "attributes": user_info
        }
    
    def _map_attributes(self, saml_attrs: dict, name_id: str) -> dict:
        """映射SAML属性到RAGFlow用户字段"""
        mapping = self.idp.attribute_mapping
        
        result = {
            "external_user_id": name_id,
            "idp_id": self.idp.id
        }
        
        for local_field, saml_attr in mapping.items():
            if saml_attr in saml_attrs:
                result[local_field] = saml_attrs[saml_attr][0]  # SAML属性通常是列表
            elif saml_attr == "NameID":
                result[local_field] = name_id
        
        return result
    
    def _find_or_create_user(self, user_info: dict) -> User:
        """查找或创建SSO用户"""
        # 1. 尝试查找已有用户
        user = User.select().where(
            (User.idp_id == user_info["idp_id"]) &
            (User.external_user_id == user_info["external_user_id"])
        ).first()
        
        if user:
            # 更新用户信息
            User.update(
                email=user_info.get("email", user.email),
                nickname=user_info.get("nickname", user.nickname),
                sso_attributes=user_info,
                last_login_time=datetime.now()
            ).where(User.id == user.id).execute()
            return user
        
        # 2. 创建新用户
        user_id = get_uuid()
        
        # 检查email是否已被本地账号使用
        existing = User.select().where(
            (User.email == user_info["email"]) &
            (User.auth_type == "local")
        ).first()
        
        if existing:
            # 策略1：禁止绑定，报错
            # raise ValueError("Email already registered with local account")
            
            # 策略2：自动关联（企业场景推荐）
            User.update(
                idp_id=user_info["idp_id"],
                external_user_id=user_info["external_user_id"],
                auth_type="saml",
                sso_attributes=user_info
            ).where(User.id == existing.id).execute()
            return existing
        
        # 3. 创建全新用户
        user = User.create(
            id=user_id,
            email=user_info["email"],
            nickname=user_info.get("nickname", user_info["email"].split("@")[0]),
            idp_id=user_info["idp_id"],
            external_user_id=user_info["external_user_id"],
            auth_type="saml",
            sso_attributes=user_info,
            status="active"
        )
        
        # 4. 自动创建租户（企业场景）
        if self.idp.auto_create_tenant:
            self._create_tenant_for_user(user)
        
        return user
    
    def process_slo(self, slo_request: str = None) -> dict:
        """
        处理单点登出（Single Logout）
        
        IdP通知SP用户已登出，SP需要清除本地会话
        """
        auth = OneLogin_Saml2_Auth({}, self.saml_settings)
        
        # 处理LogoutRequest（IdP发起的SLO）
        if slo_request:
            auth.process_slo(request_data={"SAMLRequest": slo_request})
            
            # 获取要登出的用户
            name_id = auth.get_nameid()
            session_index = auth.get_session_index()
            
            # 清除用户所有SSO会话
            self._invalidate_user_sessions(name_id, session_index)
        
        return {
            "logout_url": auth.get_slo_url(),
            "success": len(auth.get_errors()) == 0
        }
    
    def initiate_logout(self, user: User, return_to: str = None) -> str:
        """
        发起SP登出请求（用户从RAGFlow登出，通知IdP）
        """
        # 获取用户SSO会话
        session = SSOSession.select().where(
            (SSOSession.user_id == user.id) &
            (SSOSession.status == "active")
        ).first()
        
        if not session:
            return None
        
        auth = OneLogin_Saml2_Auth({}, self.saml_settings)
        
        # 生成LogoutRequest
        logout_url = auth.logout(
            return_to=return_to,
            name_id=session.saml_name_id,
            session_index=session.saml_session_index
        )
        
        return logout_url
    
    def _create_sso_session(self, user: User, session_index: str, name_id: str):
        """创建SSO会话记录（用于SLO）"""
        SSOSession.create(
            id=get_uuid(),
            user_id=user.id,
            idp_id=self.idp.id,
            saml_session_index=session_index,
            saml_name_id=name_id,
            status="active",
            expires_at=datetime.now() + timedelta(hours=8)
        )
    
    def _generate_relay_state(self, return_to: str) -> str:
        """生成并缓存RelayState（防止CSRF）"""
        state = generate_secure_random(32)
        # 存入Redis，5分钟过期
        REDIS_CONN.setex(f"saml:relay_state:{state}", 300, return_to or "/")
        return state
    
    def _validate_relay_state(self, state: str) -> bool:
        """验证RelayState"""
        return REDIS_CONN.exists(f"saml:relay_state:{state}")
```

#### 3.2.3 SSO 路由层

```python
# api/apps/auth/sso_router.py

from quart import Blueprint, request, redirect, jsonify
from api.apps.auth.saml import SAMLServiceProvider
from api.apps.auth.oidc_sp import OIDCServiceProvider
from api.db.db_models import IdentityProvider

sso_manager = Blueprint("sso", __name__)


@sso_manager.route("/login/<idp_id>", methods=["GET"])
async def sso_login(idp_id: str):
    """
    统一SSO登录入口
    
    GET /api/v1/auth/login/saml_adfs
    GET /api/v1/auth/login/oidc_wecom
    """
    # 查找IdP配置
    idp = IdentityProvider.select().where(
        (IdentityProvider.id == idp_id) &
        (IdentityProvider.enabled == True)
    ).first()
    
    if not idp:
        return jsonify({"error": "Identity provider not found"}), 404
    
    # 获取回调后跳转地址
    return_to = request.args.get("return_to", "/")
    
    # 根据协议类型处理
    if idp.protocol == "saml":
        sp = SAMLServiceProvider(idp)
        result = sp.initiate_login(return_to=return_to)
        
        # 重定向到IdP
        return redirect(result["redirect_url"])
    
    elif idp.protocol == "oidc":
        sp = OIDCServiceProvider(idp)
        result = sp.initiate_login(return_to=return_to)
        
        return redirect(result["redirect_url"])
    
    elif idp.protocol == "ldap":
        # LDAP不走重定向，返回配置让前端渲染登录框
        return jsonify({
            "type": "ldap",
            "name": idp.name,
            "fields": ["username", "password"]
        })
    
    else:
        return jsonify({"error": "Unsupported protocol"}), 400


@sso_manager.route("/saml/acs/<idp_id>", methods=["POST"])
async def saml_acs(idp_id: str):
    """
    SAML断言消费服务
    IdP POST SAML Response到这里
    """
    idp = IdentityProvider.select().where(IdentityProvider.id == idp_id).first()
    if not idp:
        return jsonify({"error": "IdP not found"}), 404
    
    form = await request.form
    saml_response = form.get("SAMLResponse")
    relay_state = form.get("RelayState")
    
    if not saml_response:
        return jsonify({"error": "Missing SAMLResponse"}), 400
    
    try:
        sp = SAMLServiceProvider(idp)
        result = sp.process_acs(saml_response, relay_state)
        
        # 生成登录Cookie/Token
        resp = redirect(result.get("relay_state_destination", "/"))
        resp.set_cookie("access_token", result["token"], httponly=True, secure=True)
        
        return resp
        
    except Exception as e:
        logging.exception("SAML ACS error")
        return jsonify({"error": str(e)}), 401


@sso_manager.route("/saml/sls/<idp_id>", methods=["GET", "POST"])
async def saml_sls(idp_id: str):
    """
    SAML单点登出端点
    处理IdP发起的登出请求
    """
    idp = IdentityProvider.select().where(IdentityProvider.id == idp_id).first()
    
    form = await request.form
    get_params = request.args
    
    slo_request = form.get("SAMLRequest") or get_params.get("SAMLRequest")
    
    sp = SAMLServiceProvider(idp)
    result = sp.process_slo(slo_request)
    
    return redirect("/login?logged_out=1")


@sso_manager.route("/oidc/callback/<idp_id>", methods=["GET"])
async def oidc_callback(idp_id: str):
    """
    OIDC回调处理
    
    GET /api/v1/auth/oidc/callback/oidc_wecom?code=xxx&state=xxx
    """
    idp = IdentityProvider.select().where(IdentityProvider.id == idp_id).first()
    
    code = request.args.get("code")
    state = request.args.get("state")
    
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400
    
    sp = OIDCServiceProvider(idp)
    result = sp.process_callback(code, state)
    
    resp = redirect("/")
    resp.set_cookie("access_token", result["token"])
    return resp


@sso_manager.route("/logout", methods=["POST"])
@login_required
async def sso_logout():
    """
    SSO登出
    
    1. 如果用户是SSO登录，需要通知IdP
    2. 清除本地会话
    """
    user = current_user
    
    if user.auth_type in ["saml", "oidc"] and user.idp_id:
        idp = IdentityProvider.select().where(IdentityProvider.id == user.idp_id).first()
        
        if idp.protocol == "saml":
            sp = SAMLServiceProvider(idp)
            logout_url = sp.initiate_logout(user, return_to="/login")
            
            if logout_url:
                # 需要重定向到IdP完成SLO
                return jsonify({"redirect_url": logout_url})
    
    # 本地登出
    logout_user()
    return jsonify({"message": "Logged out"})
```

#### 3.2.4 前端改造

```typescript
// web/src/pages/login/index.tsx 改造

interface LoginProps {
  // ... 已有props
}

const Login: React.FC<LoginProps> = () => {
  const [idpList, setIdpList] = useState<IdentityProvider[]>([]);
  
  useEffect(() => {
    // 获取启用的身份源列表
    fetch('/api/v1/auth/idp-list')
      .then(res => res.json())
      .then(data => setIdpList(data.data));
  }, []);
  
  const handleSSOLogin = (idp: IdentityProvider) => {
    // 跳转到SSO登录入口
    const returnTo = encodeURIComponent(window.location.origin + '/chat');
    window.location.href = `/api/v1/auth/login/${idp.id}?return_to=${returnTo}`;
  };
  
  return (
    <div className="login-container">
      {/* 原有本地登录表单 */}
      <LocalLoginForm />
      
      {/* 分隔线 */}
      {idpList.length > 0 && <Divider>或使用企业账号登录</Divider>}
      
      {/* SSO登录按钮列表 */}
      <div className="sso-buttons">
        {idpList.map(idp => (
          <Button
            key={idp.id}
            icon={getIdpIcon(idp.protocol)}
            onClick={() => handleSSOLogin(idp)}
            block
          >
            使用 {idp.name} 登录
          </Button>
        ))}
      </div>
    </div>
  );
};
```

---

### 3.3 管理员配置界面

```python
# api/apps/idp_app.py - 身份源管理API

from quart import Blueprint, request
from api.db.db_models import IdentityProvider
from api.utils.api_utils import login_required, admin_required

idp_blueprint = Blueprint("idp", __name__)


@idp_blueprint.route("/idp", methods=["GET"])
@login_required
async def list_idp():
    """获取身份源列表（普通用户可见启用的）"""
    idps = IdentityProvider.select().where(IdentityProvider.enabled == True)
    return jsonify({
        "data": [{"id": i.id, "name": i.name, "protocol": i.protocol} for i in idps]
    })


@idp_blueprint.route("/idp", methods=["POST"])
@admin_required
async def create_idp():
    """创建身份源（管理员）"""
    data = await request.json
    
    # 验证配置
    if data["protocol"] == "saml":
        validate_saml_config(data["config"])
    elif data["protocol"] == "oidc":
        validate_oidc_config(data["config"])
    
    idp = IdentityProvider.create(
        id=get_uuid(),
        name=data["name"],
        protocol=data["protocol"],
        config=data["config"],
        attribute_mapping=data.get("attribute_mapping", {}),
        auto_create_tenant=data.get("auto_create_tenant", True),
        enabled=data.get("enabled", True)
    )
    
    return jsonify({"id": idp.id, "message": "Identity provider created"})


@idp_blueprint.route("/idp/<idp_id>/test", methods=["POST"])
@admin_required
async def test_idp(idp_id: str):
    """测试身份源连接"""
    idp = IdentityProvider.select().where(IdentityProvider.id == idp_id).first()
    
    try:
        if idp.protocol == "saml":
            sp = SAMLServiceProvider(idp)
            # 测试解析metadata
            sp.validate_metadata()
        elif idp.protocol == "ldap":
            test_ldap_connection(idp.config)
        
        return jsonify({"status": "ok", "message": "Connection successful"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
```

---

## 四、实施计划

### 4.1 开发阶段

| 阶段 | 任务 | 工时 | 依赖 |
|------|------|------|------|
| **Phase 1** | 数据库改造 | 2天 | - |
| | - User表扩展 | | |
| | - IdentityProvider表 | | |
| | - SSOSession表 | | |
| **Phase 2** | OIDC SP实现 | 3天 | Phase 1 |
| | - OIDC认证流程 | | |
| | - 企业微信/钉钉对接 | | |
| | - 前端登录页改造 | | |
| **Phase 3** | SAML SP实现 | 5天 | Phase 1 |
| | - SAML库集成 | | |
| | - AuthnRequest生成 | | |
| | - ACS回调处理 | | |
| | - 元数据解析 | | |
| **Phase 4** | LDAP实现 | 2天 | Phase 1 |
| | - LDAP绑定认证 | | |
| | - AD域控对接 | | |
| **Phase 5** | SLO单点登出 | 2天 | Phase 2-3 |
| | - 登出回调处理 | | |
| | - 会话同步 | | |
| **Phase 6** | 管理后台 | 3天 | Phase 2-4 |
| | - IdP配置CRUD | | |
| | - 配置测试功能 | | |
| **Phase 7** | 测试&文档 | 3天 | 全部 |
| **总计** | | **20天** | |

### 4.2 技术依赖

```txt
# requirements.txt 新增

# SAML 2.0 支持
python3-saml>=1.16.0
xmlsec>=1.3.13

# LDAP 支持
python-ldap>=3.4.3

# OIDC 客户端（已有，补充服务端）
authlib>=1.2.0

# JWT验证（已有）
PyJWT>=2.8.0
cryptography>=41.0.0
```

### 4.3 配置示例

```yaml
# conf/service_conf.yaml 新增SSO配置

sso:
  enabled: true
  
  # 全局默认设置
  default:
    auto_create_user: true
    auto_create_tenant: true
    default_role: owner
    session_timeout: 8h
  
  # SAML特定配置
  saml:
    # SP证书（用于签名SAML请求）
    sp_private_key_path: /ragflow/conf/saml_sp.key
    sp_certificate_path: /ragflow/conf/saml_sp.crt
    
    # 安全性设置
    strict: true
    debug: false
    
  # OIDC特定配置
  oidc:
    # 状态Cookie设置
    state_cookie_name: oidc_state
    state_cookie_secure: true
    
  # LDAP特定配置
  ldap:
    # 连接池
    pool_size: 10
    pool_timeout: 30
    
  # 用户属性映射默认值
  default_attribute_mapping:
    email: email
    nickname: name
    department: department
    phone: phone_number
```

---

## 五、风险与注意事项

### 5.1 安全风险

| 风险 | 措施 |
|------|------|
| SAML Response伪造 | 严格验证IdP证书签名 |
| RelayState攻击 | 使用随机state并验证，Redis存储 |
| 会话劫持 | HTTPS强制，Secure Cookie |
| 用户冒充 | external_user_id + idp_id联合唯一索引 |
| SLO异步问题 | 实现全局会话注销回调 |

### 5.2 兼容性问题

```python
# 本地用户与SSO用户共存策略

# 策略1：完全分离（推荐）
# - SSO用户不能修改密码
# - SSO用户不能使用本地登录
# - 同一email可存在本地和SSO两个账号

# 策略2：自动关联
# - 本地账号自动绑定SSO身份
# - 登录方式选择：本地密码或SSO

# 实现代码示例
def migrate_local_to_sso(user: User, idp_id: str, external_id: str):
    """将本地用户迁移到SSO"""
    if user.auth_type != "local":
        raise ValueError("User is not local account")
    
    User.update(
        idp_id=idp_id,
        external_user_id=external_id,
        auth_type="saml",
        password=None  # 清空密码，禁止本地登录
    ).where(User.id == user.id).execute()
```

---

## 六、总结

### 改造核心点

1. **数据库**：新增`idp_id`、`external_user_id`、`auth_type`字段，分离本地和SSO用户
2. **协议实现**：新增SAML SP、OIDC SP、LDAP三种认证处理器
3. **路由层**：统一`/api/v1/auth/login/{idp_id}`入口，区分回调处理
4. **会话管理**：支持SLO单点登出，Redis存储SSO会话
5. **管理界面**：管理员可配置多个IdP，测试连接

### 预期效果

```
改造后：
┌─────────────────────────────────────────────────────────┐
│  用户打开RAGFlow                                          │
│      │                                                   │
│      ▼                                                   │
│  ┌─────────────────────────────────────┐                 │
│  │ 登录页显示：                         │                 │
│  │  ┌─────────────────────────────┐   │                 │
│  │  │  账号密码登录                │   │                 │
│  │  └─────────────────────────────┘   │                 │
│  │  ────────── 或 ──────────          │                 │
│  │  ┌─────────────────────────────┐   │                 │
│  │  │  使用企业微信登录   [按钮]   │   │                 │
│  │  │  使用钉钉登录       [按钮]   │   │                 │
│  │  │  使用AD域账号登录   [按钮]   │   │                 │
│  │  └─────────────────────────────┘   │                 │
│  └─────────────────────────────────────┘                 │
│      │                                                   │
│      ▼ 点击企业微信                                       │
│  ┌─────────────────────────────────────┐                 │
│  │  跳转企业微信扫码                        │                 │
│  │  扫码确认 ──► 回调RAGFlow ──► 登录成功   │                 │
│  │  自动创建租户，进入系统                   │                 │
│  └─────────────────────────────────────┘                 │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 工时估算

- **最短路径**（仅OIDC）：10天
- **标准实现**（OIDC + SAML）：17天
- **完整方案**（+ LDAP + SLO + 管理后台）：20天
