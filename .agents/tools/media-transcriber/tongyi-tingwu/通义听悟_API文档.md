# 通义听悟 API 完整工作流文档

本文档基于 `0_Inbox` 目录下的请求记录整理，详细描述了从文件上传到结果导出的完整 API 流程。

## 基础信息
- **音频 API 地址**: `https://audio-api.qianwen.com`
- **助手 API 地址**: `https://api.qianwen.com`
- **公共查询参数**: `c=tongyi-web`

---

## 一、 上传与转写流程

### 1. 获取 OSS 上传 Token
在上传文件前，需先向服务端申请 OSS 临时凭证及记录 ID。
- **URL**: `/assistant/api/record/oss/token/get`
- **Method**: `POST`
- **关键请求参数**: `fileSize`, `fileContentType`, `tag` (包含文件名、语言等)。
- **核心响应**:
  - `data.recordId`: 业务记录 ID。
  - `data.genRecordId`: 全局唯一记录 ID (用于后续所有关联操作)。
  - `data.sts`: 包含 `accessKeyId`, `accessKeySecret`, `securityToken` 及 `fileKey`。

### 2. 初始化 OSS 分片上传
使用上一步获取的 STS 凭证，直接向阿里云 OSS 发起请求。
- **URL**: `https://{bucket}.oss-accelerate.aliyuncs.com/{fileKey}?uploads=`
- **Method**: `POST`
- **响应**: 返回 `UploadId`，用于后续分片上传。

### 3. 上传心跳维持
在上传过程中，需定期发送心跳以维持 session。
- **URL**: `/assistant/api/record/upload_heartbeat`
- **Method**: `POST`
- **Payload**: `{"genRecordId": "..."}`

### 4. 启动转写任务
文件上传完成后，调用此接口通知服务端开始转写。
- **URL**: `/assistant/api/record/start`
- **Method**: `POST`
- **Payload**:
  ```json
  {
    "taskType": "local",
    "tingwuRequest": {
      "fileLink": "OSS_FILE_URL",
      "transId": "genRecordId",
      "fileSize": 12345
    }
  }
  ```

---

## 二、 记录管理与查询

### 5. 获取记录列表
分页查询听悟记录，可获取记录的 `genRecordId`, `recordId` 及转写状态 (`recordStatus`)。

- **URL**: `/assistant/api/record/list`
- **Method**: `POST`
- **Payload 示例**:
  ```json
  {
    "status": [10, 20, 30, 33, 40, 41, 43], // 状态筛选
    "pageNo": 1,
    "pageSize": 10,
    "taskTypes": ["local"], // 筛选本地上传的任务
    "orderType": 0,
    "orderDesc": true
  }
  ```
- **核心响应字段**:
  - `data.batchRecord[].recordList[]`: 记录列表
    - `recordId`: 记录唯一标识
    - `genRecordId`: 通用记录 ID (重要，后续操作多用此 ID)
    - `recordTitle`: 标题 (通常是文件名)
    - `recordStatus`: 状态码 (10=转写中/处理中?, 20=完成?)
    - `transId`: 转写 ID (类似于 genRecordId)

### 6. 导出结果查询
查询导出任务状态并获取 Markdown/Word 下载链接。
- **URL**: `/api/export/request` (Audio API)
- **Method**: `POST`
- **请求体**:
  ```json
  {
    "action": "getExportStatus",
    "exportTaskId": "..." 
  }
  ```
- **说明**: 导出成功后 `exportStatus` 为 1，`exportUrls` 中包含临时下载链接。

### 7. 删除记录
- **URL**: `/assistant/api/record/task/delete`
- **Method**: `POST`
- **Payload**: `{"recordIds": ["recordId"]}`

---

## 常用请求头 (Headers)
所有请求通常需携带以下认证信息：
- `cookie`: 包含 `tongyi_sso_ticket`。
- `x-xsrf-token`: 校验 Token。
- `x-platform`: 值为 `pc_tongyi`。