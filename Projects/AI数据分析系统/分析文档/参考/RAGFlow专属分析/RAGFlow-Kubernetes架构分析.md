# RAGFlow Kubernetes 架构深度分析

**分析日期**: 2026-02-05  
**项目版本**: RAGFlow v0.23.1  
**Helm Charts路径**: `helm/`  
**分析范围**: Helm配置、K8s资源定义、部署架构设计

---

## 一、Kubernetes架构概览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAGFlow Kubernetes 架构                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  【Namespace: ragflow】                                                      │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Ingress (可选)                                │   │
│  │                  nginx-ingress / traefik                            │   │
│  │                           ↓                                          │   │
│  │                     ragflow.local                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ↓                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Service: ragflow                                 │   │
│  │                     Type: ClusterIP/LoadBalancer                     │   │
│  │                           ↓                                          │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │              Deployment: ragflow                             │   │   │
│  │  │              Replicas: 1                                     │   │   │
│  │  │                                                             │   │   │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │   │
│  │  │  │   Nginx      │  │  RAGFlow     │  │  Task        │    │   │   │
│  │  │  │  (Web UI)    │  │  API Server  │  │  Executor    │    │   │   │
│  │  │  │  Port: 80    │  │  Port: 9380  │  │  (Celery)    │    │   │   │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘    │   │   │
│  │  │                                                             │   │   │
│  │  │  ConfigMap: nginx-config, ragflow-service-config           │   │   │
│  │  │  Secret: ragflow-env-config (DB密码等)                      │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────┼─────────────────────────────────────┐  │
│  │              依赖服务层          │                                      │  │
│  │                                  ↓                                      │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │   MySQL      │  │   Redis      │  │   MinIO      │                │  │
│  │  │  StatefulSet │  │  StatefulSet │  │  Deployment  │                │  │
│  │  │  PVC: 5Gi    │  │  PVC: 5Gi    │  │  PVC: 5Gi    │                │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                │  │
│  │        │                │                │                            │  │
│  │        └────────────────┼────────────────┘                            │  │
│  │                         ↓                                             │  │
│  │              ┌──────────────────────┐                                 │  │
│  │              │   向量数据库(三选一)  │                                 │  │
│  │              │                      │                                 │  │
│  │              │  • Elasticsearch     │                                 │  │
│  │              │    StatefulSet       │                                 │  │
│  │              │    PVC: 20Gi         │                                 │  │
│  │              │    Resources: 4C/16G │                                 │  │
│  │              │                      │                                 │  │
│  │              │  • Infinity          │                                 │  │
│  │              │  • OpenSearch        │                                 │  │
│  │              └──────────────────────┘                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 组件清单

| 组件 | K8s资源类型 | 存储 | 用途 |
|------|-------------|------|------|
| **ragflow** | Deployment | - | 主应用（Nginx + API） |
| **mysql** | StatefulSet | PVC 5Gi | 关系数据库 |
| **redis** | StatefulSet | PVC 5Gi | 缓存/队列 |
| **minio** | Deployment | PVC 5Gi | 对象存储 |
| **elasticsearch** | StatefulSet | PVC 20Gi | 向量/全文检索（可选） |
| **infinity** | StatefulSet | PVC 5Gi | 向量数据库（可选） |
| **opensearch** | StatefulSet | PVC 20Gi | 向量/全文检索（可选） |

---

## 二、Helm Charts结构

### 2.1 目录结构

```
helm/
├── Chart.yaml              # Chart元数据
├── values.yaml             # 默认配置值
├── README.md               # 部署文档
├── .helmignore             # Helm忽略文件
│
└── templates/              # K8s资源模板
    ├── _helpers.tpl        # 辅助函数
    │
    ├── env.yaml            # 环境变量Secret
    ├── ragflow.yaml        # 主应用Deployment/Service
    ├── ragflow_config.yaml # RAGFlow配置ConfigMap
    │
    ├── mysql.yaml          # MySQL StatefulSet
    ├── mysql-config.yaml   # MySQL初始化脚本
    │
    ├── redis.yaml          # Redis StatefulSet
    ├── minio.yaml          # MinIO Deployment
    │
    ├── elasticsearch.yaml  # Elasticsearch StatefulSet
    ├── elasticsearch-config.yaml
    │
    ├── infinity.yaml       # Infinity向量数据库
    ├── opensearch.yaml     # OpenSearch StatefulSet
    ├── opensearch-config.yaml
    │
    ├── ingress.yaml        # Ingress规则
    └── tests/              # Helm测试
```

### 2.2 values.yaml核心配置

```yaml
# values.yaml 核心配置解析

# 全局配置
global:
  repo: ""                 # 镜像仓库前缀（支持私有镜像仓库）
  imagePullSecrets: []     # 镜像拉取密钥

# 环境变量（传递给所有组件）
env:
  # 文档引擎选择（三选一）
  DOC_ENGINE: infinity     # elasticsearch / infinity / opensearch
  
  # 各组件密码配置
  MYSQL_PASSWORD: infini_rag_flow_helm
  REDIS_PASSWORD: infini_rag_flow_helm
  MINIO_PASSWORD: infini_rag_flow_helm
  ELASTIC_PASSWORD: infini_rag_flow_helm
  
  # 时区
  TZ: "Asia/Shanghai"
  
  # 批处理配置
  DOC_BULK_SIZE: 4                    # 文档解析批量大小
  EMBEDDING_BATCH_SIZE: 16            # 嵌入批量大小

# RAGFlow主应用配置
ragflow:
  image:
    repository: infiniflow/ragflow
    tag: v0.23.1
    pullPolicy: IfNotPresent
  
  # 资源限制
  deployment:
    resources:
      limits:
        cpu: "2000m"
        memory: "4Gi"
      requests:
        cpu: "1000m"
        memory: "2Gi"
  
  service:
    type: ClusterIP          # 或LoadBalancer暴露公网
  
  api:
    service:
      enabled: true
      type: ClusterIP

# MySQL配置
mysql:
  enabled: true              # 可禁用使用外部MySQL
  image:
    repository: mysql
    tag: 8.0.39
  storage:
    className: ""            # StorageClass（空为默认）
    capacity: 5Gi            # 存储容量
  deployment:
    resources:
      requests:
        cpu: "500m"
        memory: "1Gi"

# Elasticsearch配置
elasticsearch:
  image:
    repository: elasticsearch
    tag: "8.11.3"
  storage:
    capacity: 20Gi           # ES需要较大存储
  deployment:
    resources:
      requests:
        cpu: "4000m"         # ES需要较高CPU
        memory: "16Gi"       # ES需要较大内存
```

---

## 三、核心K8s资源设计

### 3.1 RAGFlow主应用（Deployment）

```yaml
# templates/ragflow.yaml

apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "ragflow.fullname" . }}
  labels:
    app.kubernetes.io/component: ragflow
spec:
  replicas: 1                # 默认单副本，可水平扩展
  selector:
    matchLabels:
      app.kubernetes.io/component: ragflow
  
  # 更新策略
  strategy:
    type: RollingUpdate      # 滚动更新
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  
  template:
    metadata:
      labels:
        app.kubernetes.io/component: ragflow
      annotations:
        # 配置变更检测 - 配置更新时自动重启Pod
        checksum/config-env: {{ include (print $.Template.BasePath "/env.yaml") . | sha256sum }}
        checksum/config-ragflow: {{ include (print $.Template.BasePath "/ragflow_config.yaml") . | sha256sum }}
    
    spec:
      # 镜像拉取密钥
      imagePullSecrets:
        - name: {{ .Values.ragflow.image.pullSecrets }}
      
      containers:
      - name: ragflow
        image: infiniflow/ragflow:v0.23.1
        imagePullPolicy: IfNotPresent
        
        ports:
          - containerPort: 80
            name: http           # Nginx Web UI
          - containerPort: 9380
            name: http-api       # API服务
        
        # 配置挂载
        volumeMounts:
          # Nginx配置
          - mountPath: /etc/nginx/conf.d/ragflow.conf
            subPath: ragflow.conf
            name: nginx-config-volume
          
          # 服务配置（可选自定义）
          - mountPath: /ragflow/conf/local.service_conf.yaml
            subPath: local.service_conf.yaml
            name: service-conf-volume
        
        # 环境变量（从Secret加载）
        envFrom:
          - secretRef:
              name: ragflow-env-config
        
        # 资源限制
        resources:
          limits:
            cpu: "2000m"
            memory: "4Gi"
          requests:
            cpu: "1000m"
            memory: "2Gi"
        
        # 健康检查（待完善）
        # livenessProbe:
        #   httpGet:
        #     path: /health
        #     port: 9380
        # readinessProbe:
        #   httpGet:
        #     path: /ready
        #     port: 9380
      
      volumes:
        - name: nginx-config-volume
          configMap:
            name: nginx-config
        - name: service-conf-volume
          configMap:
            name: ragflow-service-config

---
# Service定义
apiVersion: v1
kind: Service
metadata:
  name: ragflow
spec:
  selector:
    app.kubernetes.io/component: ragflow
  ports:
    - port: 80
      targetPort: http
      name: http
    - port: 9380
      targetPort: http-api
      name: http-api
  type: ClusterIP    # 内部访问，Ingress暴露外部
```

### 3.2 有状态服务：MySQL（StatefulSet）

```yaml
# templates/mysql.yaml

# PVC定义
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ragflow-mysql
  annotations:
    "helm.sh/resource-policy": keep    # Helm删除时保留PVC（防止误删数据）
spec:
  storageClassName: ""                  # 使用默认StorageClass
  accessModes:
    - ReadWriteOnce                     # 单节点读写
  resources:
    requests:
      storage: 5Gi

---
# StatefulSet定义
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ragflow-mysql
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: mysql
  
  serviceName: ragflow-mysql    # Headless Service名称
  
  template:
    metadata:
      labels:
        app.kubernetes.io/component: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0.39
        
        # MySQL启动参数
        args:
          - --max_connections=1000          # 最大连接数
          - --character-set-server=utf8mb4   # UTF-8编码
          - --collation-server=utf8mb4_general_ci
          - --default-authentication-plugin=mysql_native_password
          - --tls_version=TLSv1.2,TLSv1.3   # TLS版本
          - --init-file=/data/application/init.sql  # 初始化脚本
          - --disable-log-bin               # 禁用binlog（减少IO）
        
        ports:
          - containerPort: 3306
            name: mysql
        
        envFrom:
          - secretRef:
              name: ragflow-env-config
        
        volumeMounts:
          # 数据持久化
          - mountPath: /var/lib/mysql
            name: mysql-data
          
          # 初始化脚本
          - mountPath: /data/application/init.sql
            subPath: init.sql
            name: init-script-volume
      
      volumes:
        - name: mysql-data
          persistentVolumeClaim:
            claimName: ragflow-mysql
        - name: init-script-volume
          configMap:
            name: mysql-init-script

---
# Headless Service（StatefulSet必需）
apiVersion: v1
kind: Service
metadata:
  name: ragflow-mysql
spec:
  selector:
    app.kubernetes.io/component: mysql
  ports:
    - port: 3306
      targetPort: mysql
  type: ClusterIP
  clusterIP: None    # Headless Service，Pod直接暴露
```

### 3.3 向量数据库：Elasticsearch（StatefulSet + InitContainer）

```yaml
# templates/elasticsearch.yaml

apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: ragflow-es-data
  annotations:
    "helm.sh/resource-policy": keep
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi      # ES需要较大存储

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: ragflow-es
spec:
  replicas: 1
  selector:
    matchLabels:
      app.kubernetes.io/component: elasticsearch
  template:
    spec:
      # InitContainer：初始化操作
      initContainers:
        # 1. 修复数据目录权限
        - name: fix-data-volume-permissions
          image: alpine:latest
          command:
            - sh
            - -c
            - "chown -R 1000:0 /usr/share/elasticsearch/data"
          volumeMounts:
            - mountPath: /usr/share/elasticsearch/data
              name: es-data
        
        # 2. 设置内核参数（vm.max_map_count）
        - name: sysctl
          image: busybox:latest
          securityContext:
            privileged: true        # 特权模式修改内核参数
            runAsUser: 0
          command: ["sysctl", "-w", "vm.max_map_count=262144"]
      
      containers:
      - name: elasticsearch
        image: elasticsearch:8.11.3
        
        envFrom:
          - secretRef:
              name: ragflow-env-config
          - configMapRef:
              name: ragflow-es-config
        
        ports:
          - containerPort: 9200
            name: http
          - containerPort: 9300
            name: transport
        
        volumeMounts:
          - mountPath: /usr/share/elasticsearch/data
            name: es-data
        
        resources:
          requests:
            cpu: "4000m"      # ES需要高CPU
            memory: "16Gi"    # ES需要大内存
          limits:
            cpu: "8000m"
            memory: "32Gi"
        
        securityContext:
          capabilities:
            add:
              - "IPC_LOCK"    # 内存锁定能力
          runAsUser: 1000      # ES用户ID
          allowPrivilegeEscalation: false
      
      volumes:
        - name: es-data
          persistentVolumeClaim:
            claimName: ragflow-es-data
```

---

## 四、配置管理设计

### 4.1 环境变量管理（Secret）

```yaml
# templates/env.yaml

apiVersion: v1
kind: Secret
metadata:
  name: ragflow-env-config
type: Opaque
stringData:
  # 从values.yaml注入的环境变量
  TZ: "Asia/Shanghai"
  DOC_ENGINE: "infinity"
  MYSQL_PASSWORD: "infini_rag_flow_helm"
  REDIS_PASSWORD: "infini_rag_flow_helm"
  
  # 内部服务DNS地址（自动构建）
  # 格式: <service-name>.<namespace>.svc
  REDIS_HOST: "ragflow-redis.ragflow.svc"
  REDIS_PORT: "6379"
  MYSQL_HOST: "ragflow-mysql.ragflow.svc"
  MYSQL_PORT: "3306"
  MINIO_HOST: "ragflow-minio.ragflow.svc"
  MINIO_PORT: "9000"
  
  # 文档引擎地址
  {{- if eq .Values.env.DOC_ENGINE "elasticsearch" }}
  ES_HOST: "ragflow-es.ragflow.svc"
  ELASTIC_PASSWORD: "xxx"
  {{- else if eq .Values.env.DOC_ENGINE "infinity" }}
  INFINITY_HOST: "ragflow-infinity.ragflow.svc"
  {{- end }}
```

**设计亮点**：
-  所有密码集中管理在Secret中
-  内部服务使用K8s DNS自动发现
-  支持外部依赖（设置`enabled: false`使用外部服务）

### 4.2 ConfigMap配置

```yaml
# templates/ragflow_config.yaml

apiVersion: v1
kind: ConfigMap
metadata:
  name: ragflow-service-config
data:
  # 本地服务配置覆盖
  local.service_conf.yaml: |
    # 可以覆盖默认配置
    
  # LLM工厂配置（自定义模型）
  llm_factories.json: |
    {
      "factory_llm_infos": [
        {
          "name": "OpenAI-API-Compatible",
          "llm": [
            {"llm_name": "gpt-4", "tags": "LLM,CHAT"}
          ]
        }
      ]
    }

---
# MySQL初始化脚本
apiVersion: v1
kind: ConfigMap
metadata:
  name: mysql-init-script
data:
  init.sql: |
    CREATE DATABASE IF NOT EXISTS rag_flow CHARACTER SET utf8mb4;
    -- 其他初始化SQL
```

---

## 五、部署架构特点

### 5.1 设计亮点

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RAGFlow K8s 设计亮点                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  【1】模块化依赖管理                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  values.yaml中每个依赖都有enabled开关                            │   │
│  │                                                                  │   │
│  │  mysql:                                                         │   │
│  │    enabled: true    → 部署内置MySQL                              │   │
│  │                      → 自动生成内部DNS地址                        │   │
│  │                                                                  │   │
│  │    enabled: false   → 使用外部MySQL                              │   │
│  │                      → 需要配置MYSQL_HOST等环境变量              │   │
│  │                                                                  │   │
│  │  优势：灵活选择内置/外部依赖，生产环境可用云厂商托管服务            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  【2】向量数据库三选一                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  env.DOC_ENGINE:                                                │   │
│  │    • elasticsearch  - 功能最全，资源占用高                        │   │
│  │    • infinity       - 专用向量DB，性能优（默认）                  │   │
│  │    • opensearch     - 开源ES替代品                               │   │
│  │                                                                  │   │
│  │  优势：根据场景选择，Infinity适合纯向量场景                       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  【3】数据持久化保护                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  annotations:                                                    │   │
│  │    "helm.sh/resource-policy": keep                               │   │
│  │                                                                  │   │
│  │  作用：helm uninstall时保留PVC，防止误删数据                      │   │
│  │  手动清理：kubectl delete pvc ...                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  【4】配置变更自动重启                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Pod annotations:                                                │   │
│  │    checksum/config-env: {{ sha256sum }}                          │   │
│  │                                                                  │   │
│  │  作用：ConfigMap/Secret变更时，Pod自动滚动更新                     │   │
│  │  原理：annotation变化 → Pod template变化 → Deployment滚动更新    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  【5】镜像仓库镜像支持                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  global.repo: "registry.company.com/mirror"                      │   │
│  │                                                                  │   │
│  │  自动替换镜像前缀：                                                │   │
│  │    elasticsearch:8.11.3                                          │   │
│  │    → registry.company.com/mirror/elasticsearch:8.11.3           │   │
│  │                                                                  │   │
│  │  优势：内网/私有云环境可配置镜像仓库镜像                            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 生产部署建议

```bash
# 1. 创建命名空间
kubectl create namespace ragflow

# 2. 使用自定义values生产部署
helm install ragflow ./helm \
  --namespace ragflow \
  --values values-production.yaml

# values-production.yaml 示例
---
global:
  repo: "registry.company.com/dockerhub"  # 镜像仓库镜像

ragflow:
  replicas: 3                              # 多副本高可用
  deployment:
    resources:
      limits:
        cpu: "4000m"
        memory: "8Gi"
  service:
    type: LoadBalancer                     # 暴露公网访问

# 使用外部托管数据库（推荐生产环境）
mysql:
  enabled: false                           # 禁用内置MySQL
env:
  MYSQL_HOST: "rm-xxx.mysql.rds.aliyuncs.com"  # 阿里云RDS
  MYSQL_PORT: "3306"
  MYSQL_PASSWORD: "<from-secret>"

redis:
  enabled: false
env:
  REDIS_HOST: "r-xxx.redis.rds.aliyuncs.com"   # 阿里云Redis
  REDIS_PORT: "6379"

# 保留MinIO（或改用OSS）
minio:
  enabled: true
  storage:
    className: "alicloud-disk-ssd"         # 高性能存储
```

---

## 六、与RATH部署对比

| 维度 | RAGFlow | RATH |
|------|---------|------|
| **部署方式** | Helm Charts（K8s原生） | Docker Compose |
| **编排能力** |  自动扩缩容、滚动更新 |  手动管理 |
| **高可用** |  StatefulSet + PVC |  单节点 |
| **配置管理** |  ConfigMap/Secret | ⚠️ 环境变量 |
| **服务发现** |  K8s DNS | ⚠️ 硬编码主机名 |
| **监控集成** |  可对接Prometheus |  无 |
| **生产就绪度** |  企业级K8s部署 | ⚠️ 开发/测试级 |

---

## 七、总结

### 一句话评价

> **RAGFlow的Kubernetes架构设计专业且生产就绪，采用Helm Charts标准化部署，支持水平扩展、配置分离、数据持久化，是企业级K8s部署的典范。**

### 核心优势

1. **模块化依赖** - 内置/外部服务灵活选择
2. **多向量DB支持** - ES/Infinity/OpenSearch三选一
3. **数据保护** - PVC保留策略防止误删
4. **配置管理** - ConfigMap/Secret分离敏感信息
5. **镜像仓库支持** - 适配私有云环境

### 生产部署 checklist

- [ ] 配置StorageClass（高性能SSD）
- [ ] 使用外部托管数据库（RDS/Redis）
- [ ] 配置Ingress暴露服务
- [ ] 设置资源限制（resources）
- [ ] 配置HPA自动扩缩容
- [ ] 对接Prometheus监控
- [ ] 定期备份PVC数据
