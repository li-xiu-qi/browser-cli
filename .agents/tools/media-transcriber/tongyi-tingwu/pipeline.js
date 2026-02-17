/**
 * 通义听悟批量上传管道 (pipeline.js)
 * 
 * 完整工作流程：
 * 1. 上传本地音视频文件到 OSS
 * 2. 提交转写任务
 * 
 * 用法:
 *   node pipeline.js <文件或文件夹路径> [输出目录]
 * 
 * 示例:
 *   node pipeline.js ./audio.ogg                  # 上传单个文件，输出到 outputs/
 *   node pipeline.js ./audio_folder ./exports     # 批量上传，输出到 exports/
 * 
 * 限制 (来自通义听悟官方):
 * - 单次最多上传 50 个文件
 * - 视频: mp4/wmv/m4v/flv/rmvb/dat/mov/mkv/webm/avi/mpeg/3gp/ogg，最大 6GB
 * - 音频: mp3/wav/m4a/wma/aac/ogg/amr/flac/aiff，最大 500MB
 * - 单个文件最长 6 小时
 */

const fs = require('fs');
const fsp = require('fs/promises');
const path = require('path');
const common = require('./common');
const { uploadFileTask } = require('./pipeline_core_wrapper');

// ============ 配置 ============
const AUTO_DELETE_MODE = true;      // 超过限制时自动清理
const AUTO_CONVERT_TO_OGG = true;   // 是否自动转换非 ogg 文件以提高上传速度
const UPLOAD_DELAY_MIN = 3000;      // 文件间上传间隔最小值(ms)
const UPLOAD_DELAY_MAX = 4000;      // 文件间上传间隔最大值(ms)

// ============ 配额检查与清理 ============

/**
 * 检查配额并在需要时执行自动清理
 * @param {string} outputDir - 导出目录
 */
async function checkQuotaAndCleanup(outputDir) {
  console.log('📊 检查远程配额...');
  const { total } = await common.getRecordList({ pageSize: 1 });
  console.log(`   当前远程记录数: ${total}/${common.MAX_BATCH_FILES}`);

  if (total >= common.MAX_BATCH_FILES) {
    console.log('\n⚠️  已达到上传限制 (50个文件)！');
    
    if (!AUTO_DELETE_MODE) {
      console.log('❌ AUTO_DELETE_MODE 未开启，请手动运行:');
      console.log('   1. node bin/export.js  (导出已完成的记录)');
      console.log('   2. node bin/delete.js  (清理远程记录)');
      process.exit(1);
    }

    console.log('🔄 AUTO_DELETE_MODE 已开启，开始自动清理...');
    
    const completedRecords = await common.getCompletedRecords();
    if (completedRecords.length === 0) {
      console.log('⚠️  没有已完成的记录可以清理，可能还在转写中');
      console.log('   请稍后再试，或手动在网页端处理');
      process.exit(1);
    }

    console.log(`📝 找到 ${completedRecords.length} 条已完成的记录`);
    console.log('⚡ 开始自动导出并删除这些记录...');
    
    let processedCount = 0;
    for (const record of completedRecords) {
      const title = record.recordTitle || '无标题';
      
      // 1. 先导出
      try {
        process.stdout.write(`[处理] ${title} ... \n`);
        process.stdout.write(`       -> 导出中... `);
        const exportResult = await common.exportRecordToFile(record, outputDir);
        
        if (exportResult.skipped) {
          console.log(`[跳过] (已存在)`);
        } else {
          console.log(`✅ ${path.basename(exportResult.path)}`);
        }

        // 2. 导出成功(或已存在)后删除
        process.stdout.write(`       -> 删除中... `);
        const deleteResult = await common.deleteRecord(record.recordId);
        if (deleteResult.success) {
          console.log('✅');
          processedCount++;
        } else {
          console.log(`❌ 删除失败: ${deleteResult.message || '未知错误'}`);
        }

      } catch (err) {
        console.log(`\n❌ 处理失败: ${err.message}`);
        console.log('       (保留该记录以防丢失)');
      }
      
      await common.sleep(1000);
    }

    if (processedCount === 0) {
        console.log('\n❌ 未能清理任何记录 (可能导出失败或删除失败)');
        process.exit(1);
    }

    console.log(`\n✅ 已成功转存并清理 ${processedCount} 条记录，现在可以继续上传`);
    await common.sleep(2000);
  }
}

// ============ 主流程 ============

/**
 * 处理输入路径
 */
async function processInput(inputPath, outputDir) {
  if (!fs.existsSync(inputPath)) {
    console.error(`路径不存在: ${inputPath}`);
    process.exit(1);
  }

  // 确保输出目录存在
  await fsp.mkdir(outputDir, { recursive: true });
  console.log(`📁 输出目录: ${path.resolve(outputDir)}`);

  const stat = fs.statSync(inputPath);

  if (stat.isDirectory()) {
    console.log(`📂 检测到文件夹: ${inputPath}`);
    
    const allFiles = fs.readdirSync(inputPath)
      .filter(file => common.SUPPORTED_EXTENSIONS.includes(path.extname(file).toLowerCase()))
      .map(file => path.join(inputPath, file));

    console.log(`📝 找到 ${allFiles.length} 个支持的文件`);

    const validFiles = [];
    for (const file of allFiles) {
      const validation = common.validateFile(file);
      if (validation.valid) {
        validFiles.push(file);
      } else {
        console.log(`⚠️  跳过 ${path.basename(file)}: ${validation.reason}`);
      }
    }

    if (validFiles.length === 0) {
      console.log('❌ 没有符合条件的文件可上传');
      return;
    }

    console.log(`✅ ${validFiles.length} 个文件通过验证`);
    
    // 初次检查配额
    await checkQuotaAndCleanup(outputDir);

    for (let i = 0; i < validFiles.length; i++) {
      const file = validFiles[i];
      
      // 检查本地是否已存在结果
      const fileNameNoExt = path.basename(file, path.extname(file));
      const expectedMdName = common.sanitizeFilename(fileNameNoExt) + '.md';
      const expectedMdPath = path.join(outputDir, expectedMdName);

      if (fs.existsSync(expectedMdPath)) {
        console.log(`⏩ [${i + 1}/${validFiles.length}] 跳过已存在: ${path.basename(file)}`);
        continue;
      }

      // 每次上传前都检查配额 (防止长任务中途满了)
      if (i > 0 && i % 5 === 0) {
          await checkQuotaAndCleanup(outputDir);
      }

      console.log(`\n----------------------------------------`);
      console.log(`🚀 [${i + 1}/${validFiles.length}] 正在处理: ${path.basename(file)}`);
      
      try {
        // 使用 pipeline_core_wrapper 的上传函数
        await uploadFileTask(file, outputDir, AUTO_CONVERT_TO_OGG);
        console.log(`✅ 上传成功`);
      } catch (err) {
        console.error(`❌ 文件 ${path.basename(file)} 上传失败:`, err.message);
        if (err.cause) {
          console.error(`   详细原因:`, err.cause.message || err.cause);
        }
      }
      
      if (i < validFiles.length - 1) {
        const delay = UPLOAD_DELAY_MIN + Math.floor(Math.random() * (UPLOAD_DELAY_MAX - UPLOAD_DELAY_MIN));
        console.log(`⏳ 随机等待 ${delay}ms 后继续...`);
        await common.sleep(delay);
      }
    }

    console.log('\n========================================');
    console.log(`🎉 批量上传完成！共处理 ${validFiles.length} 个文件`);
    console.log(`📁 转写完成后请运行 bin/export.js 导出剩余结果到 ${outputDir}`);

  } else {
    const validation = common.validateFile(inputPath);
    if (!validation.valid) {
      console.error(`❌ 文件验证失败: ${validation.reason}`);
      process.exit(1);
    }

    await checkQuotaAndCleanup(outputDir);
    
    try {
      await uploadFileTask(inputPath, outputDir, AUTO_CONVERT_TO_OGG);
      console.log(`✅ 上传成功`);
    } catch (err) {
      console.error(`❌ 上传失败:`, err.message);
      if (err.cause) {
        console.error(`   详细原因:`, err.cause.message || err.cause);
      }
    }
    
    console.log(`📁 转写完成后请运行 bin/export.js 导出结果到 ${outputDir}`);
  }
}

// ============ 命令行入口 ============

const args = process.argv.slice(2);
if (args.length === 0) {
  console.log('通义听悟文件转写管道');
  console.log('====================');
  console.log('用法: node pipeline.js <文件或文件夹路径> [输出目录]');
  console.log('');
  console.log('示例:');
  console.log('  node pipeline.js ./audio.ogg');
  console.log('  node pipeline.js ./audio_folder ./exports');
  console.log('');
  console.log('限制:');
  console.log('  - 视频最大 6GB，音频最大 500MB');
  console.log('  - 远程最多保存 50 个记录');
  console.log(`  - AUTO_DELETE_MODE: ${AUTO_DELETE_MODE ? '开启' : '关闭'}`);
  console.log(`  - AUTO_CONVERT_TO_OGG: ${AUTO_CONVERT_TO_OGG ? '开启' : '关闭'}`);
  process.exit(1);
}

const inputPath = args[0];
const outputDir = args[1] || 'outputs';

processInput(inputPath, outputDir).catch(err => {
  console.error('程序执行异常:', err.message);
  process.exit(1);
});
