# API 速查表

> 常用百度网盘 API 快速参考

---

## 🔑 认证

### Token 验证
```python
GET https://pan.baidu.com/rest/2.0/xpan/nas?method=uinfo&access_token={TOKEN}
```

---

## 📁 文件操作

### 列出目录
```python
GET https://pan.baidu.com/rest/2.0/xpan/file?method=list&access_token={TOKEN}&dir={DIR}&num=1000
```

### 搜索文件
```python
GET https://pan.baidu.com/rest/2.0/xpan/file?method=search&access_token={TOKEN}&key={KEYWORD}
```

### 获取文件详情
```python
GET https://pan.baidu.com/rest/2.0/xpan/multimedia?method=filemetas&access_token={TOKEN}&fsids=[{FSID1},{FSID2}]
```

---

## ✏️ 文件管理 (filemanager)

### 删除文件/文件夹
```python
POST https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={TOKEN}&opera=delete

Body:
async=0
filelist=["/path/to/file"]
```

### 移动文件/文件夹
```python
POST https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={TOKEN}&opera=move

Body:
async=0
ondup=newcopy
filelist=[{"path": "/src/file", "dest": "/dest/", "newname": "file"}]
```

### 复制文件/文件夹
```python
POST https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={TOKEN}&opera=copy

Body:
async=0
ondup=newcopy
filelist=[{"path": "/src/file", "dest": "/dest/", "newname": "file"}]
```

### 重命名
```python
POST https://pan.baidu.com/rest/2.0/xpan/file?method=filemanager&access_token={TOKEN}&opera=rename

Body:
async=0
filelist=[{"path": "/old/name", "newname": "newname"}]
```

---

## 👤 用户信息

### 获取用户信息
```python
GET https://pan.baidu.com/rest/2.0/xpan/nas?method=uinfo&access_token={TOKEN}
```

### 获取容量信息
```python
GET https://pan.baidu.com/rest/2.0/xpan/quota?method=info&access_token={TOKEN}
```

---

## 🎙️ 音频转文稿

### 提交转写任务
```python
GET https://pan.baidu.com/apaas/1.0/bas/aitrans/video2doc/start?access_token={TOKEN}&appid={APPID}&fsid={FSID}&md5={MD5}
```

### 查询转写结果
```python
GET https://pan.baidu.com/apaas/1.0/bas/aitrans/video2doc/get?access_token={TOKEN}&appid={APPID}&fsid={FSID}&md5={MD5}&page=0
```

---

## 📝 视频字幕获取

### 获取字幕流（M3U8格式）
```python
GET https://pan.baidu.com/rest/2.0/xpan/file?method=streaming&access_token={TOKEN}&path={VIDEO_PATH}&type=M3U8_SUBTITLE_SRT
```

**Headers**:
```python
{"User-Agent": "xpanvideo;netdisk;iPhone13;ios-iphone;15.1;ts"}
```

**返回**: M3U8 播放列表，包含 SRT 字幕的真实下载链接

**示例响应**:
```
#EXTM3U
#EXT-X-TARGETDURATION:0
#EXTINF:0,
https://vdsubtitle.bdstatic.com/.../subtitle.srt
```

**使用流程**:
1. 调用 API 获取 M3U8 列表
2. 解析 M3U8 获取 SRT 下载链接
3. 下载 SRT 文件

> 💡 **提示**: 需要先开通百度网盘 SVIP 才能获取字幕

---

## 🐛 错误码速查

| 错误码 | 含义 | 解决 |
|--------|------|------|
| 0 | 成功 | - |
| -6, 31034 | Token 过期 | 重新授权 |
| 3 | 不支持的 API | 检查 method 参数 |
| 5 | 文件不存在 | 检查路径 |
| 9 | 空间不足 | 清理空间 |
| 111 | 有异步任务在执行 | 等待后重试 |

---

## 💡 常用代码片段

### 初始化
```python
import requests
import json

ACCESS_TOKEN = "your_token"
BASE_URL = "https://pan.baidu.com/rest/2.0/xpan"

def api_request(endpoint, method='GET', params=None, data=None):
    url = f"{BASE_URL}/{endpoint}"
    params = params or {}
    params['access_token'] = ACCESS_TOKEN
    
    if method == 'GET':
        response = requests.get(url, params=params, timeout=30)
    else:
        response = requests.post(url, params=params, data=data, timeout=30)
    
    return response.json()
```

### 递归获取所有文件
```python
def get_all_files(dir_path):
    files = {}
    items = list_dir(dir_path)
    for item in items:
        if item.get('isdir') == 1:
            sub_files = get_all_files(item['path'])
            files.update(sub_files)
        else:
            files[item['server_filename']] = item
    return files
```

### 批量删除
```python
def batch_delete(paths):
    if isinstance(paths, str):
        paths = [paths]
    
    url = f"{BASE_URL}/file"
    params = {
        'method': 'filemanager',
        'access_token': ACCESS_TOKEN,
        'opera': 'delete'
    }
    data = {
        'async': '0',
        'filelist': json.dumps(paths)
    }
    
    response = requests.post(url, params=params, data=data)
    return response.json()
```

### 批量移动
```python
def batch_move(file_list):
    # file_list: [{"path": "/src", "dest": "/dest", "newname": "name"}]
    url = f"{BASE_URL}/file"
    params = {
        'method': 'filemanager',
        'access_token': ACCESS_TOKEN,
        'opera': 'move'
    }
    data = {
        'async': '0',
        'ondup': 'newcopy',
        'filelist': json.dumps(file_list)
    }
    
    response = requests.post(url, params=params, data=data)
    return response.json()
```

---

## 📚 参考文档

- [官方 API 文档](https://pan.baidu.com/union/doc)
- [文件管理 API](https://pan.baidu.com/union/doc/mksg0s9l4)
- [音频转写 API](https://pan.baidu.com/union/doc/7lie62en8)

---

**最后更新**: 2026-02-14
