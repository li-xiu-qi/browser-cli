# 常见问题 (FAQ)

> 使用百度网盘 API 过程中可能遇到的问题及解决方案

---

## 🔑 Token 相关

### Q: Token 过期了怎么办？

**A**: 需要重新授权获取新的 Token。

```bash
# 1. 访问授权 URL（浏览器打开）
https://openapi.baidu.com/oauth/2.0/authorize?response_type=token&client_id=s4muIqE7Nv9sXk6IV841pQc7iUEQwZiP&redirect_uri=oob&scope=basic,netdisk

# 2. 登录并授权
# 3. 从 URL 中提取新的 access_token
# 4. 更新到 .token_info.json 和 .env 文件
```

### Q: Token 有什么权限？

**A**: 当前 Token 权限：
- ✅ 读取文件列表
- ✅ 搜索文件
- ✅ 获取文件信息
- ✅ 删除文件/文件夹
- ✅ 移动文件/文件夹
- ✅ 复制文件/文件夹

### Q: 如何检查 Token 是否有效？

**A**: 运行验证脚本：
```bash
python scripts/verify_token.py
```

---

## 🚀 API 调用相关

### Q: 返回 "Unsupported open api" 怎么办？

**A**: 这是 API 调用方式错误。

❌ 错误方式：
```python
method=delete  # 错误！
```

✅ 正确方式：
```python
method=filemanager&opera=delete  # 正确！
```

参考 [文件管理 API 文档](https://pan.baidu.com/union/doc/mksg0s9l4)。

### Q: 批量操作有数量限制吗？

**A**: 有，建议每次不超过 100 个文件。

### Q: API 调用频率有限制吗？

**A**: 官方限制约 100 次/分钟，建议添加适当延迟：
```python
import time
time.sleep(0.5)  # 每次调用后等待 0.5 秒
```

### Q: 大文件夹扫描超时怎么办？

**A**: 限制递归深度或分批处理：
```python
# 限制深度
def scan(dir_path, max_depth=2, current_depth=0):
    if current_depth >= max_depth:
        return
    # ...
```

---

## 📁 文件操作相关

### Q: 移动文件时提示"文件已存在"怎么办？

**A**: 使用 `ondup=newcopy` 参数：
```python
data = {
    'ondup': 'newcopy',  # 如果存在则重命名
    'filelist': filelist
}
```

### Q: 误删了文件能恢复吗？

**A**: 可以！删除的文件会进入回收站，保留 10 天：
1. 打开百度网盘网页版
2. 进入回收站
3. 找到文件并还原

### Q: 如何批量删除空文件夹？

**A**: 先检查文件夹是否为空，再删除：
```python
items = list_dir(folder_path)
if not items:  # 为空
    delete_file(folder_path)
```

---

## 🎙️ 音频转文稿相关

### Q: 如何触发音频转写？

**A**: SVIP 用户上传音频/视频后会自动触发。如需手动触发：
```python
# 提交转写任务
GET /apaas/1.0/bas/aitrans/video2doc/start?fsid={FSID}&md5={MD5}

# 轮询查询结果
GET /apaas/1.0/bas/aitrans/video2doc/get?fsid={FSID}&md5={MD5}&page=0
```

### Q: 转写需要多长时间？

**A**: 取决于文件大小，一般：
- 1 小时音频：5-10 分钟
- 4 小时音频：20-30 分钟

### Q: 如何获取转写结果？

**A**: 通过 MCP 的 `file_meta` 工具：
```
获取文件ID为 xxx 的详细信息，包含 content 字段
```

或调用 API：
```python
meta = get_file_meta([fsid])
content = meta['list'][0].get('content', '')  # 转写文本
```

---

## 📝 字幕获取相关

### Q: 为什么获取字幕返回空或失败？

**A**: 检查以下条件：
1. **SVIP 会员** - 字幕功能需要百度网盘 SVIP
2. **字幕已生成** - 视频需要先在网盘播放，等待 AI 字幕生成完成
3. **路径正确** - 确认 `BASE_DIR` 指向的是网盘中的正确路径
4. **Token 有效** - 运行 `verify_token.py` 检查

### Q: 字幕是什么格式？

**A**:
- **原始格式**: SRT (SubRip Subtitle)
- **转换后**: Markdown (智能分段，适合阅读)
- **包含内容**: 时间戳 + 文本内容

### Q: 如何批量获取多个课程的字幕？

**A**: 修改脚本中的 `BASE_DIR` 为课程根目录，脚本会自动处理所有子目录中的视频：
```python
BASE_DIR = "/我的资源/00-转存区域/课程文件夹"
```

### Q: 字幕质量如何？

**A**: 百度网盘 AI 字幕的准确率约 90-95%，可能存在：
- 人名识别错误
- 专业术语错误
- 语气词重复（"啊""呢"等）

建议转换后人工校对关键内容。

### Q: 转换后的 Markdown 可以自定义格式吗？

**A**: 可以，编辑 `convert_srt_to_md.py` 中的 `smart_paragraphs` 函数：
```python
# 修改分段长度（默认约 300 字）
if char_count >= 300:  # 调整这个值
    result.append(current_para.strip())
```

---

## 🔧 MCP 相关

### Q: MCP 无法连接怎么办？

**A**: 检查以下几点：
1. Token 是否过期
2. MCP 配置是否正确
3. 网络是否能访问 `mcp-pan.baidu.com`

### Q: MCP 和直接调用 API 有什么区别？

**A**: 
- **MCP**: 自然语言操作，适合对话式交互
- **直接 API**: 程序化操作，适合批量处理

---

## 🐛 错误排查

### Q: 遇到未知错误怎么办？

**A**: 排查步骤：
1. 检查错误码（参考 [错误码文档](./error-codes.md)）
2. 检查 Token 是否有效
3. 检查 API 参数是否正确
4. 查看官方文档
5. 联系百度网盘开放平台客服

### Q: 如何查看详细的 API 响应？

**A**: 打印响应内容：
```python
response = requests.post(url, params=params, data=data)
print(response.text)  # 查看完整响应
result = response.json()
print(result)  # 查看解析后的结果
```

---

## 💡 最佳实践

### Q: 如何避免误删重要文件？

**A**: 
1. 删除前先列出要删除的文件，人工确认
2. 先移动到临时文件夹，观察几天后再删除
3. 重要文件先在本地备份

### Q: 如何提高批量操作效率？

**A**:
1. 使用批量 API（一次最多 100 个）
2. 添加适当的延迟避免频率限制
3. 使用异步操作（async=2）处理大文件

### Q: 如何监控操作进度？

**A**: 添加进度打印：
```python
total = len(files)
for i, file in enumerate(files, 1):
    print(f"处理中... {i}/{total} ({i/total*100:.1f}%)")
    # 执行操作
```

---

## 📞 获取帮助

如果以上 FAQ 无法解决你的问题：

1. **查看文档**: [官方 API 文档](https://pan.baidu.com/union/doc)
2. **检查日志**: 查看 `scripts/` 目录下的执行日志
3. **联系客服**: 百度网盘开放平台反馈渠道

---

**最后更新**: 2026-02-17（新增字幕获取相关 FAQ）
