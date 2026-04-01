/**
 * 通义听悟全自动转录工具 (core_transcribe.js)
 * 
 * 功能：
 * 1. 自动上传文件到通义听悟
 * 2. 自动等待转写完成
 * 3. 自动导出 Markdown 文件
 * 4. 自动清理远程记录
 * 
 * 用法:
 *   node core_transcribe.js <文件路径> [输出目录]
 */

const fs = require('fs');
const path = require('path');
const common = require('./common');
const { uploadFileTask } = require('./pipeline_core_wrapper');
const { ensureQianwenSession } = require('./ensure_session');

/**
 * 轮询等待任务完成
 */
async function waitForRecordCompletion(genRecordId, maxWaitMinutes = 30) {
  const startTime = Date.now();
  console.log(`[等待] 正在等待任务完成 (genRecordId: ${genRecordId})...\n`);
  
  while (Date.now() - startTime < maxWaitMinutes * 60 * 1000) {
    try {
      const { records } = await common.getRecordList({ pageSize: 50 });
      const record = records.find(r => r.genRecordId === genRecordId);
      
      if (!record) {
        console.warn('   ! 找不到记录，可能还在初始化或已被删除');
      } else {
        const status = record.recordStatus ?? record.status;
        const statusText = record.statusText || status;
        process.stdout.write(`\r   > 当前状态: ${statusText} ... `);

        if (status === 30) {
          console.log('\n✅ 任务已完成！');
          return record;
        } else if (status === 40 || status === 41 || status === 43) {
          console.log('\n❌ 任务失败！');
          throw new Error(`任务失败，状态码: ${status}`);
        }
      }
    } catch (e) {
      console.warn(`\n   ! 轮询出错 (将重试): ${e.message}`);
    }

    await common.sleep(15000); // 15 秒检查一次
  }
  
  throw new Error('等待超时');
}

/**
 * 主流程
 */
async function main(filePath, outputDir = 'resources/transcript_outputs') {
  if (!fs.existsSync(filePath)) {
    throw new Error(`文件不存在: ${filePath}`);
  }

  // 检查本地是否已存在结果
  const fileNameNoExt = path.basename(filePath, path.extname(filePath));
  const expectedMdName = common.sanitizeFilename(fileNameNoExt) + '.md';
  const expectedMdPath = path.join(outputDir, expectedMdName);

  if (fs.existsSync(expectedMdPath)) {
    console.log(`⏩ 本地已存在转写结果: ${expectedMdPath}`);
    console.log('   如需重新转写，请先删除该文件。');
    return {
      skipped: true,
      path: expectedMdPath
    };
  }

  console.log(`\n==== 通义听悟 ASR 全自动流程 ====\n`);
  console.log(`📄 文件: ${path.basename(filePath)}`);

  const sessionResult = await ensureQianwenSession({ refreshIfNeeded: true });
  if (!sessionResult.ok) {
    throw new Error('通义听悟登录态不可用，且从 browser-cli 刷新后仍未通过校验');
  }

  // 1. 上传与启动
  console.log('\n[1/4] 上传文件并启动转写任务...');
  const result = await uploadFileTask(filePath, outputDir, true);
  const genRecordId = result.genRecordId;

  // 2. 等待完成
  console.log('\n[2/4] 等待转写完成...');
  const completedRecord = await waitForRecordCompletion(genRecordId);

  // 3. 导出结果
  console.log('\n[3/4] 正在导出 Markdown...');
  const exportResult = await common.exportRecordToFile(completedRecord, outputDir);
  
  if (exportResult.skipped) {
    console.log(`⏩ ${exportResult.reason}: ${path.basename(exportResult.path)}`);
  } else {
    console.log(`✅ 已导出: ${exportResult.path}`);
  }

  // 4. 清理远程记录
  console.log('\n[4/4] 正在删除远程记录以节省空间...');
  const deleteResult = await common.deleteRecord(completedRecord.recordId);
  if (deleteResult.success) {
    console.log('✅ 清理完成');
  } else {
    console.log(`⚠️  清理失败: ${deleteResult.message || '未知错误'}`);
  }

  console.log(`\n🎉 全部完成！转写结果: ${exportResult.path}`);
  return {
    skipped: Boolean(exportResult.skipped),
    path: exportResult.path,
    genRecordId,
    recordId: completedRecord.recordId,
    deleted: Boolean(deleteResult.success)
  };
}

// 命令行入口
if (require.main === module) {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.log('通义听悟全自动转录工具');
    console.log('======================');
    console.log('用法: node core_transcribe.js <文件路径> [输出目录]');
    console.log('');
    console.log('示例:');
    console.log('  node core_transcribe.js ./会议录音.mp3');
    console.log('  node core_transcribe.js ./课程视频.mp4 ./笔记');
    process.exit(1);
  }

  const inputPath = args[0];
  const outputDir = args[1] || 'resources/transcript_outputs';

  main(inputPath, outputDir).catch((err) => {
    console.error(`\n❌ 执行失败: ${err.message}`);
    if (err.cause) console.error(`   原因: ${err.cause.message || err.cause}`);
    process.exit(1);
  });
}

module.exports = {
  main,
  waitForRecordCompletion
};
