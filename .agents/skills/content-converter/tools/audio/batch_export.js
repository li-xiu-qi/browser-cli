/**
 * 通义听悟批量导出工具 (batch_export.js)
 * 能够导出完整的 Markdown 转写稿（带说话人、时间戳）
 * 
 * 用法:
 *   node batch_export.js [数量] [输出目录]
 * 
 * 示例:
 *   node batch_export.js              # 导出最近50条，保存到 resources/transcript_outputs/
 *   node batch_export.js 20           # 导出最近20条
 *   node batch_export.js 20 ./exports # 导出最近20条，保存到 exports/
 */

const fs = require('fs/promises');
const path = require('path');
const common = require('./common');

/**
 * 批量导出主函数
 */
async function batchExport(limit = 50, outputDir = 'resources/transcript_outputs') {
  // 确保目录存在
  try {
    await fs.mkdir(outputDir, { recursive: true });
  } catch (e) {}

  console.log(`正在获取最近 ${limit} 条已完成记录...`);
  let records;
  try {
    records = await common.getCompletedRecords(limit);
  } catch (err) {
    console.error('请求失败，请检查 Cookie。详细信息:', err.message);
    return;
  }

  if (records.length === 0) {
    console.log('没有找到已完成的记录。');
    return;
  }

  console.log(`找到 ${records.length} 条已完成记录，开始逐个导出...`);
  let successCount = 0;
  let skipCount = 0;

  for (const item of records) {
    try {
      const result = await common.exportRecordToFile(item, outputDir);
      
      if (result.skipped) {
        console.log(`[跳过] ${path.basename(result.path)} (${result.reason})`);
        skipCount++;
      } else {
        console.log(`[成功] -> ${result.path}`);
        successCount++;
      }
    } catch (err) {
      console.error(`[失败] ${item.recordTitle}:`, err.message);
    }

    // 增加动态延迟（2-3s），防止请求过快
    await common.sleep(2000 + Math.random() * 1000);
  }

  console.log(`\n全部处理完毕！成功: ${successCount}, 跳过: ${skipCount}`);
}

// 执行
const args = process.argv.slice(2);
const limit = parseInt(args[0]) || 50;
const outputDir = args[1] || 'resources/transcript_outputs';

batchExport(limit, outputDir).catch(console.error);
