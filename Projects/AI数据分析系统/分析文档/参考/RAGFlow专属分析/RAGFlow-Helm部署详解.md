# RAGFlow Helm 部署详解

**版本**: Helm Chart v0.1.0  
**应用版本**: RAGFlow v0.23.1  
**文档日期**: 2026-02-05

---

## 一、Helm 是什么？

**Helm** 是 Kubernetes 的包管理工具，类似于 Ubuntu 的 apt 或 macOS 的 Homebrew。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Helm 在 K8s 中的角色                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   传统部署（手动）              Helm 部署（自动化）                           │
│   ─────────────────             ────────────────                             │
│                                                                              │
│   1. 写 Deployment.yaml         1. helm install ragflow ./helm              │
│   2. 写 Service.yaml                ↓                                       │
│   3. 写 ConfigMap.yaml          Chart（模板 + 配置）                         │
│   4. 写 Secret.yaml                 ↓                                       │
│   5. kubectl apply -f .           helm template（渲染）                      │
│                                     ↓                                       │
│                                   K8s 资源清单                                │
│                                     ↓                                       │
│                                   kubectl apply                             │
│                                                                              │
│   优势：                                                                     │
│   • 参数化配置（values.yaml）                                                │
│   • 版本管理（helm upgrade/rollback）                                        │
│   • 依赖管理（Chart.yaml dependencies）                                      │
│   • 模板复用（_helpers.tpl）                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、RAGFlow Helm Chart 结构

### 2.1 目录结构

```
helm/                                   # Helm Chart 根目录
├── Chart.yaml                          # Chart 元数据
├── values.yaml                         # 默认配置值
├── README.md                           # 使用说明
├── .helmignore                         # 打包忽略文件
│
└── templates/                          # K8s 模板文件
    ├── _helpers.tpl                    # 通用模板函数
    │
    ├── ragflow.yaml                    # RAGFlow 主应用
    ├── ragflow_config.yaml             # RAGFlow 配置文件
    │
    ├── mysql.yaml                      # MySQL 数据库
    ├── mysql-config.yaml               # MySQL 初始化脚本
    │
    ├── redis.yaml                      # Redis 缓存
    ├── minio.yaml                      # MinIO 对象存储
    │
    ├── infinity.yaml                   # Infinity 向量数据库
    ├── elasticsearch.yaml              # Elasticsearch
    ├── opensearch.yaml                 # OpenSearch
    │
    ├── env.yaml                        # 环境变量 Secret
    ├── ingress.yaml                    # 入口网关
    │
    └── tests/                          # 测试模板
        └── test-connection.yaml
```

### 2.2 核心文件详解

#### Chart.yaml - Chart 元数据

```yaml
apiVersion: v2          # Helm 3 版本
name: ragflow           # Chart 名称
description: A Helm chart for deploying RAGFlow on Kubernetes
type: application       # 应用类型（非库）
version: 0.1.0          # Chart 版本
appVersion: "dev"       # 应用版本

# 注意：RAGFlow 当前 Chart 没有定义依赖（dependencies）
# 所有组件（MySQL/Redis/MinIO）都在同一个 Chart 中管理
```

#### values.yaml - 配置中心

```yaml
# ═══════════════════════════════════════════════════════════════
# RAGFlow Helm Chart 配置详解
# ═══════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────
# 1. 全局配置
# ─────────────────────────────────────────────────────────────
global:
  # 镜像仓库前缀（用于私有镜像仓库）
  # 例："registry.cn-hangzhou.aliyuncs.com/mycompany"
  repo: ""
  
  # 镜像拉取密钥（私有仓库需要）
  imagePullSecrets: []
  # - name: regcred

# ─────────────────────────────────────────────────────────────
# 2. 环境变量配置（核心）
# ─────────────────────────────────────────────────────────────
env:
  # 文档引擎选择：infinity / elasticsearch / opensearch
  DOC_ENGINE: infinity
  
  # ES 配置（当 DOC_ENGINE=elasticsearch）
  STACK_VERSION: "8.11.3"
  ELASTIC_PASSWORD: infini_rag_flow_helm
  
  # OpenSearch 配置（当 DOC_ENGINE=opensearch）
  OPENSEARCH_PASSWORD: infini_rag_flow_OS_01
  
  # MySQL 配置
  MYSQL_PASSWORD: infini_rag_flow_helm
  MYSQL_DBNAME: rag_flow
  
  # MinIO 配置
  MINIO_ROOT_USER: rag_flow
  MINIO_PASSWORD: infini_rag_flow_helm
  
  # Redis 配置
  REDIS_PASSWORD: infini_rag_flow_helm
  
  # 时区
  TZ: "Asia/Shanghai"
  
  # 文档处理批量大小
  DOC_BULK_SIZE: 4          # 文档解析批量
  EMBEDDING_BATCH_SIZE: 16  # 向量化批量

# ─────────────────────────────────────────────────────────────
# 3. RAGFlow 主应用配置
# ─────────────────────────────────────────────────────────────
ragflow:
  image:
    repository: infiniflow/ragflow    # 镜像地址
    tag: v0.23.1                       # 版本标签
    pullPolicy: IfNotPresent          # 拉取策略
    pullSecrets: []                   # 私有仓库密钥
  
  # RAGFlow 服务配置（注入到容器）
  service_conf:
    # 会生成 local.service_conf.yaml
    # 参考：https://ragflow.io/docs/dev/configurations
  
  # LLM 厂商配置（注入到容器）
  llm_factories:
    # 会生成 llm_factories.json
  
  # K8s 部署配置
  deployment:
    strategy: {}        # 更新策略
    resources: {}       # 资源限制/请求
  
  service:
    type: ClusterIP     # 服务类型
  
  api:
    service:
      enabled: true     # 是否暴露 API Service
      type: ClusterIP

# ─────────────────────────────────────────────────────────────
# 4. 依赖服务配置
# ─────────────────────────────────────────────────────────────

# 4.1 Infinity 向量数据库（默认）
infinity:
  enabled: true         # 是否部署（与 elasticsearch/opensearch 互斥）
  image:
    repository: infiniflow/infinity
    tag: v0.7.0-dev2
  storage:
    className: ""       # StorageClass（空为默认）
    capacity: 5Gi       # 存储容量
  deployment:
    resources: {}

# 4.2 Elasticsearch（可选）
elasticsearch:
  enabled: false
  image:
    repository: elasticsearch
    tag: "8.11.3"
  storage:
    capacity: 20Gi
  deployment:
    resources:
      requests:
        cpu: "4"        # ES 需要较多资源
        memory: "16Gi"

# 4.3 OpenSearch（可选）
opensearch:
  enabled: false
  image:
    repository: opensearchproject/opensearch
    tag: 2.19.1
  storage:
    capacity: 20Gi

# 4.4 MinIO 对象存储
minio:
  enabled: true
  image:
    repository: quay.io/minio/minio
    tag: RELEASE.2023-12-20T01-00-02Z
  storage:
    capacity: 5Gi

# 4.5 MySQL 数据库
mysql:
  enabled: true
  image:
    repository: mysql
    tag: 8.0.39
  storage:
    capacity: 5Gi

# 4.6 Redis 缓存（使用 Valkey 替代）
redis:
  enabled: true
  image:
    repository: valkey/valkey    # Redis 的开源替代
    tag: "8"
  storage:
    capacity: 5Gi
  persistence:
    enabled: true

# ─────────────────────────────────────────────────────────────
# 5. 入口配置
# ─────────────────────────────────────────────────────────────
ingress:
  enabled: false
  className: ""       # ingress-controller 类名
  annotations: {}     # 额外注解
  hosts:
    - host: ragflow.example.com
      paths:
        - path: /
          pathType: Prefix
  tls: []             # HTTPS 证书
```

---

## 三、部署实战

### 3.1 基础部署

```bash
# 1. 克隆仓库
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/helm

# 2. 基础安装（使用默认配置）
helm upgrade --install ragflow ./ \
  --namespace ragflow \
  --create-namespace

# 3. 查看部署状态
kubectl get pods -n ragflow

# 预期输出：
# NAME                                    READY   STATUS
# ragflow-0                               1/1     Running
# ragflow-infinity-0                      1/1     Running
# ragflow-mysql-0                         1/1     Running
# ragflow-minio-6c9b8f7d5-x2v9p          1/1     Running
# ragflow-redis-0                         1/1     Running
```

### 3.2 自定义配置部署

```bash
# 创建自定义配置文件
cat > my-values.yaml << 'EOF'
# 使用外部 MySQL
global:
  repo: "registry.cn-hangzhou.aliyuncs.com/infiniflow"

env:
  TZ: "Asia/Shanghai"
  # 使用外部 MySQL
  MYSQL_HOST: "mydb.example.com"
  MYSQL_PORT: "3306"
  MYSQL_PASSWORD: "my-secret-password"

mysql:
  enabled: false    # 不部署内置 MySQL

ragflow:
  image:
    tag: "v0.23.1-gpu"   # 使用 GPU 版本
  deployment:
    resources:
      limits:
        nvidia.com/gpu: 1    # 分配 GPU

infinity:
  storage:
    capacity: 50Gi    # 增加向量库存储

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: ragflow.mycompany.com
      paths:
        - path: /
          pathType: Prefix
EOF

# 使用自定义配置部署
helm upgrade --install ragflow ./ \
  --namespace ragflow \
  --create-namespace \
  -f my-values.yaml
```

### 3.3 生产级部署配置

```yaml
# production-values.yaml

ragflow:
  replicas: 3              # 多副本
  
  deployment:
    strategy:
      type: RollingUpdate
      rollingUpdate:
        maxSurge: 1
        maxUnavailable: 0
    resources:
      requests:
        cpu: "2"
        memory: "4Gi"
      limits:
        cpu: "4"
        memory: "8Gi"
  
  service:
    type: LoadBalancer     # 使用云厂商负载均衡

mysql:
  enabled: false           # 使用 RDS

redis:
  enabled: false           # 使用云 Redis

minio:
  enabled: false           # 使用 S3

env:
  # 外部服务配置
  MYSQL_HOST: "ragflow-mysql.rds.aliyuncs.com"
  MYSQL_PASSWORD: "${MYSQL_PASSWORD}"  # 从 Secret 注入
  
  REDIS_HOST: "ragflow-redis.redis.rds.aliyuncs.com"
  REDIS_PASSWORD: "${REDIS_PASSWORD}"
  
  MINIO_HOST: "oss-cn-beijing.aliyuncs.com"
  MINIO_ROOT_USER: "${OSS_ACCESS_KEY}"
  MINIO_PASSWORD: "${OSS_SECRET_KEY}"
```

---

## 四、关键模板解析

### 4.1 RAGFlow 主应用模板

```yaml
# templates/ragflow.yaml

---
# 1. Deployment - 部署应用
apiVersion: apps/v1
kind: Deployment
metadata:
  # 使用 helper 模板生成名称
  name: {{ include "ragflow.fullname" . }}
  labels:
    {{- include "ragflow.labels" . | nindent 4 }}
    app.kubernetes.io/component: ragflow
spec:
  replicas: 1    # 当前是单副本，可扩展
  selector:
    matchLabels:
      {{- include "ragflow.selectorLabels" . | nindent 6 }}
      app.kubernetes.io/component: ragflow
  
  # 更新策略
  {{- with .Values.ragflow.deployment.strategy }}
  strategy:
    {{- . | toYaml | nindent 4 }}
  {{- end }}
  
  template:
    metadata:
      labels:
        {{- include "ragflow.labels" . | nindent 8 }}
        app.kubernetes.io/component: ragflow
      annotations:
        # 配置变更时自动滚动更新
        checksum/config-env: {{ include (print $.Template.BasePath "/env.yaml") . | sha256sum }}
        checksum/config-ragflow: {{ include (print $.Template.BasePath "/ragflow_config.yaml") . | sha256sum }}
    
    spec:
      # 镜像拉取密钥
      {{- if or .Values.global.imagePullSecrets .Values.ragflow.image.pullSecrets }}
      imagePullSecrets:
        {{- with .Values.global.imagePullSecrets }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
        {{- with .Values.ragflow.image.pullSecrets }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- end }}
      
      containers:
      - name: ragflow
        # 动态生成镜像地址（支持 global.repo 前缀）
        image: {{ include "ragflow.imageRepo" (dict "root" . "repo" .Values.ragflow.image.repository) }}:{{ .Values.ragflow.image.tag }}
        imagePullPolicy: {{ .Values.ragflow.image.pullPolicy }}
        
        ports:
          - containerPort: 80      # Web UI
            name: http
          - containerPort: 9380    # API
            name: http-api
        
        # 配置挂载
        volumeMounts:
          - mountPath: /etc/nginx/conf.d/ragflow.conf
            subPath: ragflow.conf
            name: nginx-config-volume
          # ... 其他配置
        
        # 环境变量（从 Secret 加载）
        envFrom:
          - secretRef:
              name: {{ include "ragflow.fullname" . }}-env-config
        
        # 资源限制
        resources:
          {{- .Values.ragflow.deployment.resources | toYaml | nindent 10 }}
      
      volumes:
        - name: nginx-config-volume
          configMap:
            name: nginx-config

---
# 2. Service - 暴露服务
apiVersion: v1
kind: Service
metadata:
  name: {{ include "ragflow.fullname" . }}
spec:
  selector:
    app.kubernetes.io/component: ragflow
  ports:
    - port: 80
      targetPort: http
      name: http
  type: {{ .Values.ragflow.service.type }}    # ClusterIP/LoadBalancer
```

### 4.2 MySQL StatefulSet 模板

```yaml
# templates/mysql.yaml

{{- if .Values.mysql.enabled }}    # 条件渲染
---
# 1. PVC - 数据持久化
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "ragflow.fullname" . }}-mysql
  annotations:
    "helm.sh/resource-policy": keep    # 删除 Chart 时保留数据
spec:
  {{- with .Values.mysql.storage.className }}
  storageClassName: {{ . }}
  {{- end }}
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: {{ .Values.mysql.storage.capacity }}

---
# 2. StatefulSet - 有状态应用
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: {{ include "ragflow.fullname" . }}-mysql
spec:
  replicas: 1
  serviceName: {{ include "ragflow.fullname" . }}-mysql
  selector:
    matchLabels:
      app.kubernetes.io/component: mysql
  template:
    spec:
      containers:
      - name: mysql
        image: {{ include "ragflow.imageRepo" (dict "root" . "repo" .Values.mysql.image.repository) }}:{{ .Values.mysql.image.tag }}
        
        args:
          - --max_connections=1000
          - --character-set-server=utf8mb4
          - --init-file=/data/application/init.sql    # 初始化脚本
        
        envFrom:
          - secretRef:
              name: {{ include "ragflow.fullname" . }}-env-config
        
        volumeMounts:
          - name: mysql-data
            mountPath: /var/lib/mysql
  
  # 3. VolumeClaimTemplate - 每个 Pod 独立存储
  volumeClaimTemplates:
    - metadata:
        name: mysql-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: {{ .Values.mysql.storage.capacity }}
{{- end }}
```

### 4.3 Helper 模板函数

```yaml
# templates/_helpers.tpl

{{/* 生成完整应用名称 */}}
{{- define "ragflow.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/* 通用标签 */}}
{{- define "ragflow.labels" -}}
helm.sh/chart: {{ include "ragflow.chart" . }}
{{ include "ragflow.selectorLabels" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* 选择器标签 */}}
{{- define "ragflow.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ragflow.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* 处理镜像仓库（支持 global.repo 前缀） */}}
{{- define "ragflow.imageRepo" -}}
{{- $root := .root -}}
{{- $repo := .repo -}}
{{- $global := $root.Values.global -}}
{{- if and $global $global.repo }}
  # 如果设置了 global.repo，替换镜像前缀
  {{- $parts := splitList "/" $repo -}}
  {{- $first := index $parts 0 -}}
  {{- $hasRegistry := or (regexMatch "\\." $first) (regexMatch ":" $first) -}}
  {{- if $hasRegistry -}}
    {{- $path := join "/" (rest $parts) -}}
    {{- printf "%s/%s" $global.repo $path -}}
  {{- else -}}
    {{- printf "%s/%s" $global.repo $repo -}}
  {{- end -}}
{{- else -}}
  {{- $repo -}}
{{- end -}}
{{- end }}
```

---

## 五、常用操作

### 5.1 生命周期管理

```bash
# ─────────────────────────────────────────
# 安装
# ─────────────────────────────────────────
helm install ragflow ./helm -n ragflow --create-namespace

# ─────────────────────────────────────────
# 升级
# ─────────────────────────────────────────
# 修改 values.yaml 后
helm upgrade ragflow ./helm -n ragflow

# 强制重启（更新 ConfigMap）
helm upgrade ragflow ./helm -n ragflow --force

# ─────────────────────────────────────────
# 回滚
# ─────────────────────────────────────────
# 查看历史版本
helm history ragflow -n ragflow

# 回滚到上一版本
helm rollback ragflow -n ragflow

# 回滚到指定版本
helm rollback ragflow 2 -n ragflow

# ─────────────────────────────────────────
# 卸载
# ─────────────────────────────────────────
# 保留数据（PVC）
helm uninstall ragflow -n ragflow

# 清理所有资源（包括 PVC）
helm uninstall ragflow -n ragflow
cubectl delete pvc -n ragflow --all

# ─────────────────────────────────────────
# 调试
# ─────────────────────────────────────────
# 渲染模板（不部署）
helm template ragflow ./helm -n ragflow > rendered.yaml

# 检查配置
helm lint ./helm

# 获取已部署的 values
helm get values ragflow -n ragflow

# 查看资源状态
helm status ragflow -n ragflow
```

### 5.2 扩缩容

```bash
# 方式1：修改 values.yaml 后升级
helm upgrade ragflow ./helm -n ragflow -f values.yaml

# 方式2：直接 kubectl 扩容（临时）
kubectl scale deployment ragflow --replicas=3 -n ragflow

# 方式3：使用 HPA（自动扩缩容）
kubectl autoscale deployment ragflow \
  --min=2 --max=10 --cpu-percent=70 \
  -n ragflow
```

### 5.3 配置更新

```bash
# 更新环境变量（如修改密码）
kubectl create secret generic ragflow-env-config \
  --from-literal=MYSQL_PASSWORD=newpassword \
  --dry-run=client -o yaml | kubectl apply -f -

# 触发滚动更新
kubectl rollout restart deployment/ragflow -n ragflow

# 查看更新进度
kubectl rollout status deployment/ragflow -n ragflow
```

---

## 六、架构对比

### 6.1 Helm vs Docker Compose

| 对比项 | Docker Compose | Helm (K8s) |
|--------|---------------|------------|
| **适用场景** | 单机/开发测试 | 生产环境/集群 |
| **编排能力** | 容器级别 | Pod/Service/Ingress |
| **扩展性** | 垂直扩展 | 水平自动扩缩容 |
| **高可用** | 依赖外部 | 原生支持多副本 |
| **配置管理** | .env 文件 | values.yaml + Secret |
| **版本管理** | 手动 | helm upgrade/rollback |
| **服务发现** | 容器名DNS | K8s Service/DNS |

### 6.2 部署架构对比

```
Docker Compose 部署                  Helm K8s 部署
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

单机部署                              集群部署
┌─────────────┐                      ┌─────────────────────┐
│   docker    │                      │    Kubernetes       │
│   compose   │                      │    Cluster          │
│             │                      │                     │
│ ┌─────────┐ │                      │ ┌─────┐ ┌─────┐    │
│ │ragflow  │ │                      │ │Node1│ │Node2│ ...│
│ │:80      │ │                      │ └─────┘ └─────┘    │
│ ├─────────┤ │       ─────►         │                     │
│ │mysql    │ │                      │  ┌───────────────┐  │
│ │:3306    │ │                      │  │   Ingress     │  │
│ ├─────────┤ │                      │  │  Controller   │  │
│ │redis    │ │                      │  └───────┬───────┘  │
│ │:6379    │ │                      │          │          │
│ ├─────────┤ │                      │  ┌───────┴───────┐  │
│ │es       │ │                      │  │  Service      │  │
│ │:9200    │ │                      │  │  (ClusterIP)  │  │
│ └─────────┘ │                      │  └───────┬───────┘  │
└─────────────┘                      │          │          │
                                     │  ┌───────┴───────┐  │
                                     │  │  Deployment   │  │
                                     │  │  (3 replicas) │  │
                                     │  └───────────────┘  │
                                     └─────────────────────┘
```

---

## 七、常见问题

### Q1: 如何修改配置后生效？

```bash
# 修改 values.yaml 后执行
helm upgrade ragflow ./helm -n ragflow -f values.yaml

# 注意：某些配置需要重启 Pod
kubectl rollout restart deployment/ragflow -n ragflow
```

### Q2: 如何查看日志？

```bash
# 查看 RAGFlow 日志
kubectl logs -f deployment/ragflow -n ragflow

# 查看所有 Pod 日志
kubectl logs -f -l app.kubernetes.io/name=ragflow -n ragflow

# 查看之前容器的日志（崩溃后）
kubectl logs -f deployment/ragflow --previous -n ragflow
```

### Q3: 数据如何持久化？

```bash
# 查看 PVC
kubectl get pvc -n ragflow

# 输出示例：
# NAME                    STATUS   VOLUME   CAPACITY
# ragflow-mysql          Bound    pv-xxx   5Gi
# ragflow-infinity       Bound    pv-yyy   5Gi
# ragflow-redis          Bound    pv-zzz   5Gi

# 删除 Chart 但保留数据
helm uninstall ragflow -n ragflow
# PVC 会保留（有 helm.sh/resource-policy: keep 注解）

# 重新安装时会自动挂载原有 PVC
helm install ragflow ./helm -n ragflow
```

### Q4: 如何使用外部数据库？

```yaml
# values.yaml
mysql:
  enabled: false    # 关闭内置 MySQL

env:
  MYSQL_HOST: "your-rds-host.mysql.rds.aliyuncs.com"
  MYSQL_PORT: "3306"
  MYSQL_PASSWORD: "your-password"
```

---

## 八、总结

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     RAGFlow Helm Chart 核心要点                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. 架构特点                                                                 │
│     • All-in-One：一个 Chart 包含所有依赖（MySQL/Redis/MinIO/Infinity）       │
│     • 条件渲染：通过 enabled 开关控制部署哪些组件                              │
│     • 灵活配置：支持内置服务或外部服务                                         │
│                                                                              │
│  2. 关键模板                                                                 │
│     • _helpers.tpl：通用函数（名称生成、镜像处理）                             │
│     • ragflow.yaml：主应用 Deployment + Service                               │
│     • mysql.yaml：StatefulSet + PVC（数据持久化）                             │
│     • env.yaml：Secret（敏感配置统一管理）                                     │
│                                                                              │
│  3. 生产建议                                                                 │
│     • 使用外部 RDS 替代内置 MySQL                                              │
│     • 使用 Ingress + HTTPS 暴露服务                                            │
│     • 配置 Resource Limit 避免资源耗尽                                         │
│     • 启用 HPA 自动扩缩容                                                      │
│     • 定期备份 PVC 数据                                                        │
│                                                                              │
│  4. 与 docker-compose 的关系                                                  │
│     • docker-compose：适合开发/单机部署                                         │
│     • helm：适合生产/K8s 集群                                                   │
│     • 配置逻辑相似，都使用环境变量传参                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

**参考文档**：
- [Helm 官方文档](https://helm.sh/docs/)
- [RAGFlow Helm README](https://github.com/infiniflow/ragflow/blob/main/helm/README.md)
- [values.yaml 完整配置](https://github.com/infiniflow/ragflow/blob/main/helm/values.yaml)
