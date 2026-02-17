/**
 * Pipeline 核心逻辑封装 (用于被其他脚本引用)
 * 专注于单任务上传，提供文件转码、分片上传、转写启动功能。
 */

const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');
const crypto = require('crypto');
const { HEADERS, BASE_URL } = require('./config');
const common = require('./common');

// 配置
const PART_SIZE = 30 * 1024 * 1024; // 30MB 分片
const CONCURRENCY = 1;              // 单并发稳定性优先

/**
 * 生成 OSS 签名
 */
function signRequest(method, bucket, objectKey, headers, accessKeyId, accessKeySecret, securityToken) {
  const contentType = headers['content-type'] || '';
  const date = headers['x-oss-date'];
  const ossHeaders = Object.entries(headers)
    .filter(([k]) => k.toLowerCase().startsWith('x-oss-'))
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([k, v]) => `${k.toLowerCase()}:${v}`)
    .join('\n');
  const resource = `/${bucket}/${objectKey}`;
  const stringToSign = `${method}\n\n${contentType}\n${date}\n${ossHeaders}\n${resource}`;
  const signature = crypto.createHmac('sha1', accessKeySecret).update(stringToSign).digest('base64');
  return `OSS ${accessKeyId}:${signature}`;
}

/**
 * 获取 OSS Token (带重试)
 */
async function getOssToken(filePath) {
  const stat = fs.statSync(filePath);
  const fileName = path.basename(filePath);
  const ext = path.extname(filePath).slice(1);
  const payload = {
    taskType: 'local', useSts: 1, fileSize: stat.size, dirIdStr: '0',
    fileContentType: common.getMimeType(filePath), bizTerminal: 'web',
    tag: {
      showName: fileName.replace(/\.[^.]+$/, ''), fileFormat: ext, fileType: 'local',
      lang: 'cn', roleSplitNum: -1, translateSwitch: 0, transTargetValue: 0,
      originalTag: '{"isVideo":0}', client: 'web'
    }
  };

  let lastError;
  for (let i = 1; i <= 3; i++) {
    try {
      const resp = await fetch(`${BASE_URL}/record/oss/token/get?c=tongyi-web`, {
        method: 'POST', headers: { ...HEADERS, 'x-platform': 'pc_tongyi' }, body: JSON.stringify(payload),
        signal: AbortSignal.timeout(60000)
      });
      const data = await resp.json();
      if (!data.success) throw new Error(`API错误: ${data.message}`);
      return {
        ...data.data.sts, 
        recordId: data.data.recordId, 
        genRecordId: data.data.genRecordId, 
        getLink: data.data.getLink, 
        fileSize: stat.size 
      };
    } catch (e) {
      lastError = e;
      if (i < 3) await common.sleep(2000 * i);
    }
  }
  throw new Error(`获取上传凭证最终失败: ${lastError.message}`);
}

/**
 * 初始化分片上传
 */
async function initMultipartUpload(ossInfo) {
  const { bucket, fileKey, accessKeyId, accessKeySecret, securityToken } = ossInfo;
  const date = new Date().toUTCString();
  const headers = { 'content-type': common.getMimeType(fileKey), 'x-oss-date': date, 'x-oss-security-token': securityToken, 'x-oss-user-agent': 'aliyun-sdk-js/6.23.0' };
  headers['authorization'] = signRequest('POST', bucket, fileKey + '?uploads', headers, accessKeyId, accessKeySecret, securityToken);
  const encodedFileKey = fileKey.split('/').map(encodeURIComponent).join('/');
  const resp = await fetch(`https://${bucket}.oss-accelerate.aliyuncs.com/${encodedFileKey}?uploads=`, { method: 'POST', headers });
  const text = await resp.text();
  const match = text.match(/<UploadId>(.+?)<\/UploadId>/);
  if (!match) throw new Error(`初始化失败: ${text}`);
  return match[1];
}

/**
 * 上传分片 (带重试，长超时)
 */
async function uploadPart(ossInfo, uploadId, partNumber, data) {
  const { bucket, fileKey, accessKeyId, accessKeySecret, securityToken } = ossInfo;
  const date = new Date().toUTCString();
  const resource = `${fileKey}?partNumber=${partNumber}&uploadId=${uploadId}`;
  const headers = { 'content-type': 'application/octet-stream', 'x-oss-date': date, 'x-oss-security-token': securityToken, 'x-oss-user-agent': 'aliyun-sdk-js/6.23.0' };
  headers['authorization'] = signRequest('PUT', bucket, resource, headers, accessKeyId, accessKeySecret, securityToken);
  const encodedFileKey = fileKey.split('/').map(encodeURIComponent).join('/');
  const url = `https://${bucket}.oss-accelerate.aliyuncs.com/${encodedFileKey}?partNumber=${partNumber}&uploadId=${uploadId}`;
  
  for (let i = 1; i <= 3; i++) {
    try {
      const resp = await fetch(url, { 
        method: 'PUT', headers, body: data, 
        signal: AbortSignal.timeout(600000) // 10 分钟超时
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      return resp.headers.get('etag');
    } catch (e) {
      if (i === 3) throw e;
      console.warn(`     ! 分片 ${partNumber} 重试 ${i}/3...`);
      await common.sleep(3000 * i);
    }
  }
}

/**
 * 合并并启动转写任务
 */
async function completeAndStart(ossInfo, uploadId, etags) {
  const { bucket, fileKey, accessKeyId, accessKeySecret, securityToken, genRecordId, getLink, fileSize } = ossInfo;
  const date = new Date().toUTCString();
  const xmlParts = etags.map((etag, i) => `<Part><PartNumber>${i + 1}</PartNumber><ETag>${etag}</ETag></Part>`).join('');
  const body = `<?xml version="1.0" encoding="UTF-8"?><CompleteMultipartUpload>${xmlParts}</CompleteMultipartUpload>`;
  const headers = { 'content-type': 'application/xml', 'x-oss-date': date, 'x-oss-security-token': securityToken, 'x-oss-user-agent': 'aliyun-sdk-js/6.23.0' };
  headers['authorization'] = signRequest('POST', bucket, `${fileKey}?uploadId=${uploadId}`, headers, accessKeyId, accessKeySecret, securityToken);
  const encodedFileKey = fileKey.split('/').map(encodeURIComponent).join('/');
  
  await fetch(`https://${bucket}.oss-accelerate.aliyuncs.com/${encodedFileKey}?uploadId=${uploadId}`, { method: 'POST', headers, body });
  
  const startResp = await fetch(`${BASE_URL}/record/start?c=tongyi-web`, {
    method: 'POST', headers: { ...HEADERS, 'x-platform': 'pc_tongyi' },
    body: JSON.stringify({ taskType: 'local', tingwuRequest: { fileLink: getLink, transId: genRecordId, fileSize }, bizTerminal: 'web', dirIdStr: '0' })
  });
  return await startResp.json();
}

/**
 * 执行完整的上传任务流程
 * @param {string} filePath - 要上传的文件路径
 * @param {string} outputDir - 输出目录（用于临时文件存放）
 * @param {boolean} autoConvert - 是否自动转换为 OGG
 */
async function uploadFileTask(filePath, outputDir, autoConvert = true) {
  // 使用 common.js 中的 ensureOgg
  const oggResult = await common.ensureOgg(filePath, outputDir, autoConvert);
  const uploadPath = oggResult.path;
  const isTemp = oggResult.isTemp;

  console.log(`[上传] 正在上传: ${path.basename(uploadPath)}`);
  const ossInfo = await getOssToken(uploadPath);
  const uploadId = await initMultipartUpload(ossInfo);
  
  const fileBuffer = fs.readFileSync(uploadPath);
  const totalParts = Math.ceil(fileBuffer.length / PART_SIZE);
  const etags = new Array(totalParts);

  for (let i = 0; i < totalParts; i++) {
    const chunk = fileBuffer.slice(i * PART_SIZE, Math.min((i + 1) * PART_SIZE, fileBuffer.length));
    process.stdout.write(`\r   > 进度: ${(((i + 1) / totalParts) * 100).toFixed(1)}% `);
    etags[i] = await uploadPart(ossInfo, uploadId, i + 1, chunk);
  }
  console.log('\n[上传] 完成，正在启动转写...');
  await completeAndStart(ossInfo, uploadId, etags);

  if (isTemp) try { await fsp.unlink(uploadPath); } catch(e){}
  
  return { genRecordId: ossInfo.genRecordId };
}

module.exports = { uploadFileTask };
