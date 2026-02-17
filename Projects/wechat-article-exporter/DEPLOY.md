# wechat-article-exporter 部署指南

## 快速开始

### 1. 进入项目目录

```powershell
cd Projects/wechat-article-exporter
```

### 2. 构建 Docker 镜像

```powershell
docker build -t wechat-article-exporter:latest .
```

> 注意：构建时间约 10-15 分钟，取决于网络速度

### 3. 运行容器

```powershell
docker run -d -p 3000:3000 --name wechat-exporter wechat-article-exporter:latest
```

### 4. 访问应用

打开浏览器访问：http://localhost:3000

---

## 使用 docker-compose（推荐）

### 构建并启动

```powershell
docker-compose up -d --build
```

### 查看日志

```powershell
docker-compose logs -f
```

### 停止服务

```powershell
docker-compose down
```

---

## 数据持久化（可选）

如果想保留数据，使用以下命令：

```powershell
# 创建数据目录
mkdir data

# 运行并挂载数据卷
docker run -d -p 3000:3000 -v ${PWD}/data:/app/.data --name wechat-exporter wechat-article-exporter:latest
```

---

## 常见问题

### 构建失败/超时

网络较慢时，可以尝试多执行几次构建命令，Docker 会缓存已下载的层。

### 端口被占用

如果 3000 端口被占用，修改映射端口：

```powershell
docker run -d -p 8080:3000 --name wechat-exporter wechat-article-exporter:latest
```

然后访问 http://localhost:8080

---

## 使用流程

1. 访问 http://localhost:3000
2. 点击登录，扫码授权公众号
3. 搜索目标公众号
4. 如需获取阅读量，需配置 credentials（抓包获取）
5. 选择文章，批量导出
