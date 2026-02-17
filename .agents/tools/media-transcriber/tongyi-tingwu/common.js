/**
 * 通义听悟 API 公共模块
 * 提供各脚本共用的常量、工具函数和 API 调用封装
 */

const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');
const { spawnSync } = require('child_process');
const { HEADERS, BASE_URL } = require('./config');

// ============ API 端点 ============
const EXPORT_API_URL = "https://audio-api.qianwen.com/api/export/request";

// ============ 文件限制常量 ============
const MAX_VIDEO_SIZE = 6 * 1024 * 1024 * 1024;  // 6GB
const MAX_AUDIO_SIZE = 500 * 1024 * 1024;        // 500MB
const MAX_BATCH_FILES = 50;                       // 单次最多上传文件数

// 支持的格式分类
const VIDEO_EXTENSIONS = ['.mp4', '.wmv', '.m4v', '.flv', '.rmvb', '.dat', '.mov', '.mkv', '.webm', '.avi', '.mpeg', '.3gp'];
const AUDIO_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.wma', '.aac', '.ogg', '.amr', '.flac', '.aiff'];
const SUPPORTED_EXTENSIONS = [...VIDEO_EXTENSIONS, ...AUDIO_EXTENSIONS];

// ============ 工具函数 ============

/**
 * 延迟函数
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * 获取文件的 MIME 类型
 */
function getMimeType(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  const mimeTypes = {
    // 视频格式
    '.mp4': 'video/mp4',
    '.wmv': 'video/x-ms-wmv',
    '.m4v': 'video/x-m4v',
    '.flv': 'video/x-flv',
    '.rmvb': 'application/vnd.rn-realmedia-vbr',
    '.dat': 'video/mpeg',
    '.mov': 'video/quicktime',
    '.mkv': 'video/x-matroska',
    '.webm': 'video/webm',
    '.avi': 'video/x-msvideo',
    '.mpeg': 'video/mpeg',
    '.3gp': 'video/3gpp',
    // 音频格式
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.m4a': 'audio/mp4',
    '.wma': 'audio/x-ms-wma',
    '.aac': 'audio/aac',
    '.ogg': 'audio/ogg',
    '.amr': 'audio/amr',
    '.flac': 'audio/flac',
    '.aiff': 'audio/aiff'
  };
  return mimeTypes[ext] || 'application/octet-stream';
}

/**
 * 检查 FFmpeg 是否可用
 */
function checkFFmpeg() {
  try {
    const result = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' });
    return result.status === 0;
  } catch (error) {
    return false;
  }
}

/**
 * 检查文件是否符合上传限制
 */
function validateFile(filePath) {
  const stat = fs.statSync(filePath);
  const ext = path.extname(filePath).toLowerCase();
  
  if (!SUPPORTED_EXTENSIONS.includes(ext)) {
    return { valid: false, reason: `不支持的格式: ${ext}` };
  }
  
  const isVideo = VIDEO_EXTENSIONS.includes(ext);
  const maxSize = isVideo ? MAX_VIDEO_SIZE : MAX_AUDIO_SIZE;
  const maxSizeLabel = isVideo ? '6GB' : '500MB';
  
  if (stat.size > maxSize) {
    const actualSize = (stat.size / (1024 * 1024)).toFixed(2);
    return { valid: false, reason: `文件过大 (${actualSize}MB)，${isVideo ? '视频' : '音频'}最大支持 ${maxSizeLabel}` };
  }
  
  return { valid: true };
}

/**
 * 清理文件名中的非法字符
 */
function sanitizeFilename(name) {
  return name.replace(/[\\/:*?"<>|]/g, '').trim() || '未命名';
}

/**
 * 确保文件是 OGG 格式（如果不是视频且开启了自动转换，则调用 ffmpeg 转换）
 * @param {string} filePath - 输入文件路径
 * @param {string} outputDir - 输出目录（用于存放临时文件）
 * @param {boolean} autoConvert - 是否自动转换
 * @returns {Promise<{path: string, isTemp: boolean}>}
 */
async function ensureOgg(filePath, outputDir, autoConvert = true) {
  const ext = path.extname(filePath).toLowerCase();
  const isVideo = VIDEO_EXTENSIONS.includes(ext);
  
  // 如果不是视频，或者是 ogg，或者未开启自动转换，则直接返回原始路径
  if (!autoConvert || !isVideo || ext === '.ogg') {
    return { path: filePath, isTemp: false };
  }

  if (!checkFFmpeg()) {
    console.warn('⚠️  警告: 未检测到 FFmpeg，将直接上传原始文件。');
    return { path: filePath, isTemp: false };
  }

  const fileName = path.basename(filePath, ext);
  const tempDir = path.join(outputDir, '.temp_ogg');
  await fsp.mkdir(tempDir, { recursive: true });
  
  const outputPath = path.join(tempDir, `${fileName}.ogg`);

  // 如果临时文件已存在，直接使用
  if (fs.existsSync(outputPath)) {
    console.log(`   [转换] 发现已转换的临时文件: ${path.basename(outputPath)}`);
    return { path: outputPath, isTemp: true };
  }

  console.log(`   [转换] 正在将 ${path.basename(filePath)} 转换为 OGG 以提高上传速度...`);
  
  const args = [
    '-i', filePath,
    '-vn',
    '-c:a', 'libvorbis',
    '-q:a', '4',
    '-y',
    '-loglevel', 'error',
    outputPath
  ];

  const result = spawnSync('ffmpeg', args);

  if (result.status === 0) {
    const srcSize = fs.statSync(filePath).size;
    const dstSize = fs.statSync(outputPath).size;
    const ratio = ((dstSize / srcSize) * 100).toFixed(1);
    
    if (dstSize > srcSize) {
      console.log(`   [转换] 转换后的文件体积变大 (${(dstSize / 1024 / 1024).toFixed(2)}MB)，放弃转换结果，使用原始文件。`);
      try { await fsp.unlink(outputPath); } catch (e) {}
      return { path: filePath, isTemp: false };
    }

    console.log(`   └─ 完成! ${(srcSize / 1024 / 1024).toFixed(2)}MB -> ${(dstSize / 1024 / 1024).toFixed(2)}MB (压缩率: ${ratio}%)`);
    return { path: outputPath, isTemp: true };
  } else {
    console.error(`   ❌ 转换失败，将回退到原始文件上传。`);
    return { path: filePath, isTemp: false };
  }
}

/**
 * 批量转换视频文件为 OGG 音频（独立工具函数）
 * @param {string} inputPath - 输入文件或目录
 * @param {string} outputDir - 输出目录
 */
async function batchConvertToOgg(inputPath, outputDir) {
  if (!checkFFmpeg()) {
    console.error('❌ 错误: 未检测到 FFmpeg，请先安装 FFmpeg 并将其添加到系统环境变量中。');
    process.exit(1);
  }

  // 确保输出目录存在
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
    console.log(`创建输出目录: ${outputDir}`);
  }

  // 扫描文件
  const filesToProcess = [];
  const stat = fs.statSync(inputPath);
  
  if (stat.isFile()) {
    if (VIDEO_EXTENSIONS.includes(path.extname(inputPath).toLowerCase())) {
      filesToProcess.push(inputPath);
    }
  } else {
    const scan = (dir) => {
      const items = fs.readdirSync(dir);
      for (const item of items) {
        const fullPath = path.join(dir, item);
        const itemStat = fs.statSync(fullPath);
        if (itemStat.isDirectory()) {
          scan(fullPath);
        } else if (VIDEO_EXTENSIONS.includes(path.extname(item).toLowerCase())) {
          filesToProcess.push(fullPath);
        }
      }
    };
    scan(inputPath);
  }

  if (filesToProcess.length === 0) {
    console.log('没有找到支持的视频文件。');
    return;
  }

  console.log(`共找到 ${filesToProcess.length} 个文件，开始转换...\n`);

  for (let i = 0; i < filesToProcess.length; i++) {
    const file = filesToProcess[i];
    const fileName = path.basename(file);
    const baseName = path.basename(file, path.extname(file));
    const outputPath = path.join(outputDir, `${baseName}.ogg`);

    process.stdout.write(`[${i + 1}/${filesToProcess.length}] 正在转换: ${fileName} ... `);

    if (fs.existsSync(outputPath)) {
      console.log(`[跳过] 目标已存在`);
      continue;
    }

    const args = [
      '-i', file,
      '-vn',
      '-c:a', 'libvorbis',
      '-q:a', '4',
      '-y',
      '-loglevel', 'error',
      outputPath
    ];

    const result = spawnSync('ffmpeg', args);

    if (result.status === 0) {
      const srcSize = fs.statSync(file).size;
      const dstSize = fs.statSync(outputPath).size;
      const ratio = ((dstSize / srcSize) * 100).toFixed(1);
      console.log(`✅ ${(srcSize / 1024 / 1024).toFixed(2)}MB -> ${(dstSize / 1024 / 1024).toFixed(2)}MB (${ratio}%)`);
    } else {
      console.error(`❌ 转换失败`);
    }
  }

  console.log('\n✅ 所有任务完成。');
}

// ============ 记录管理 API ============

/**
 * 获取记录列表
 * @param {object} options - 查询选项
 * @param {number} options.pageSize - 每页数量，默认 50
 * @param {number[]} options.status - 状态筛选，默认所有状态
 * @param {string[]} options.taskTypes - 任务类型，默认 ["local"]
 */
async function getRecordList(options = {}) {
  const {
    pageSize = 50,
    status = [10, 20, 30, 33, 40, 41, 43],
    taskTypes = ["local"]
  } = options;

  const url = `${BASE_URL}/record/list?c=tongyi-web`;
  const payload = {
    pageNo: 1,
    pageSize,
    status,
    taskTypes,
    dirIdStr: "0",
    orderType: 0,
    orderDesc: true
  };

  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: { ...HEADERS, 'x-platform': 'pc_tongyi' },
      body: JSON.stringify(payload)
    });

    if (!resp.ok) {
        throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
    }

    const data = await resp.json();
    if (!data.success) {
      throw new Error(`API错误: ${data.message || '未知错误'}`);
    }

    const batchRecord = data.data?.batchRecord || [];
    const records = batchRecord.flatMap(batch => batch.recordList || []);
    const total = data.data?.total || 0;

    return { records, total };
  } catch (err) {
    console.error(`[getRecordList] 请求失败:`, err.message);
    if (err.cause) {
        console.error('   底层错误(cause):', err.cause);
    }
    // 重新抛出以便上层处理
    throw err;
  }
}

/**
 * 获取已完成的记录列表 (status=30)
 */
async function getCompletedRecords(pageSize = 50) {
  const { records } = await getRecordList({ pageSize, status: [30] });
  return records;
}

/**
 * 删除单条记录
 */
async function deleteRecord(recordId) {
  const url = `${BASE_URL}/record/task/delete?c=tongyi-web`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { ...HEADERS, 'x-platform': 'pc_tongyi' },
    body: JSON.stringify({ recordIds: [recordId] })
  });
  return await resp.json();
}

// ============ 导出 API ============

/**
 * 发起导出请求
 */
async function exportTrans(genRecordId, options = {}) {
  const { withSpeaker = true, withTimestamp = true } = options;
  
  const payload = {
    action: "exportTrans",
    transIds: [genRecordId],
    exportDetails: [{
      docType: 1,
      fileType: 3, // Markdown
      withSpeaker,
      withTimeStamp: withTimestamp
    }]
  };

  const resp = await fetch(`${EXPORT_API_URL}?c=tongyi-web`, {
    method: 'POST',
    headers: HEADERS,
    body: JSON.stringify(payload)
  });

  const data = await resp.json();
  if (!data.success) {
    throw new Error(`发起导出失败: ${data.message || '未知错误'}`);
  }

  return data.data?.exportTaskId;
}

/**
 * 轮询导出状态
 */
async function waitForExport(exportTaskId, options = {}) {
  const { maxWait = 60000, interval = 2000 } = options;
  
  const payload = {
    action: "getExportStatus",
    exportTaskId
  };

  const startTime = Date.now();
  while (Date.now() - startTime < maxWait) {
    const resp = await fetch(`${EXPORT_API_URL}?c=tongyi-web`, {
      method: 'POST',
      headers: HEADERS,
      body: JSON.stringify(payload)
    });

    const data = await resp.json();
    if (!data.success) {
      throw new Error(`查询状态失败: ${data.message || '未知错误'}`);
    }

    if (data.data?.exportStatus === 1) {
      const urlInfo = data.data.exportUrls?.[0];
      if (urlInfo?.success) {
        return urlInfo.url;
      }
      throw new Error("导出完成但未获取到下载链接");
    }

    await sleep(interval);
  }

  throw new Error(`导出超时，已等待 ${maxWait / 1000} 秒`);
}

/**
 * 下载文件到指定路径
 */
async function downloadFile(url, outputPath) {
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`下载失败: ${resp.statusText}`);
  const buffer = await resp.arrayBuffer();
  await fsp.writeFile(outputPath, Buffer.from(buffer));
}

/**
 * 导出单条记录到文件
 */
async function exportRecordToFile(record, outputDir) {
  const title = record.recordTitle || '无标题';
  const genRecordId = record.genRecordId;
  
  if (!genRecordId) {
    throw new Error('缺少 genRecordId');
  }

  const safeTitle = sanitizeFilename(title);
  const outputPath = path.join(outputDir, `${safeTitle}.md`);

  // 检查是否已存在
  try {
    await fsp.access(outputPath);
    return { skipped: true, path: outputPath, reason: '已存在' };
  } catch (e) {
    // 文件不存在，继续
  }

  const taskId = await exportTrans(genRecordId);
  const downloadUrl = await waitForExport(taskId);
  await downloadFile(downloadUrl, outputPath);

  return { skipped: false, path: outputPath };
}

// ============ 导出模块 ============

module.exports = {
  // 常量
  HEADERS,
  BASE_URL,
  EXPORT_API_URL,
  MAX_VIDEO_SIZE,
  MAX_AUDIO_SIZE,
  MAX_BATCH_FILES,
  VIDEO_EXTENSIONS,
  AUDIO_EXTENSIONS,
  SUPPORTED_EXTENSIONS,
  
  // 工具函数
  sleep,
  getMimeType,
  checkFFmpeg,
  validateFile,
  sanitizeFilename,
  
  // 媒体转换
  ensureOgg,
  batchConvertToOgg,
  
  // 记录管理
  getRecordList,
  getCompletedRecords,
  deleteRecord,
  
  // 导出功能
  exportTrans,
  waitForExport,
  downloadFile,
  exportRecordToFile
};
