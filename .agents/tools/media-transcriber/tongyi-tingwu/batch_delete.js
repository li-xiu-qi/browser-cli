/**
 * 通义听悟远程记录清空工具 (batch_delete.js)
 * 用于批量删除远程已完成或不需要的记录
 * 
 * 用法:
 *   node batch_delete.js [数量]
 * 
 * 示例:
 *   node batch_delete.js       # 删除最多50条记录
 *   node batch_delete.js 10    # 删除最多10条记录
 */

const common = require('./common');

/**
 * 批量删除主函数
 */
async function batchDelete(limit = 50) {
  console.log(`正在获取待删除记录 (上限 ${limit} 条)...`);
  
  let records;
  try {
    const result = await common.getRecordList({ pageSize: limit });
    records = result.records;
  } catch (err) {
    console.error('无法获取列表:', err.message);
    return;
  }

  if (records.length === 0) {
    console.log('没有发现可删除的记录。');
    return;
  }

  console.log(`找到 ${records.length} 条记录，准备开始删除...`);
  let successCount = 0;

  for (const item of records) {
    const title = item.recordTitle || '无标题';
    const recordId = item.recordId;
    
    if (!recordId) continue;

    try {
      process.stdout.write(`[删除中] ${title} ... `);
      const result = await common.deleteRecord(recordId);
      
      if (result.success) {
        console.log('✅ 成功');
        successCount++;
      } else {
        console.log(`❌ 失败: ${result.message || '未知原因'}`);
      }
    } catch (err) {
      console.log(`💥 报错: ${err.message}`);
    }

    // 1-2秒动态延时
    await common.sleep(1000 + Math.random() * 1000);
  }

  console.log(`\n清理完成！共成功删除 ${successCount} 条记录。`);
}

// 执行
const args = process.argv.slice(2);
const limit = parseInt(args[0]) || 50;

batchDelete(limit).catch(console.error);
