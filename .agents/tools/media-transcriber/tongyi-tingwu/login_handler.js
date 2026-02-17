/**
 * 通义听悟自动登录与 Cookie 抓取工具 (login_handler.js)
 * 
 * 功能：
 * 1. 自动启动浏览器并打开通义官网
 * 2. 监听登录状态（支持扫码登录）
 * 3. 登录成功后自动保存 Cookie 到 datas/cookies.json
 * 
 * 用法:
 *   node login_handler.js
 * 
 * 说明:
 *   运行后会弹出浏览器窗口，请在 5 分钟内完成登录。
 *   登录成功后，Cookie 将自动保存，供其他脚本使用。
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const COOKIE_FILE = path.join(__dirname, 'datas', 'cookies.json');
const LOGIN_TIMEOUT = 300000; // 5分钟超时

async function run() {
  console.log('🚀 正在启动浏览器...');
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext();
  const page = await context.newPage();

  // 确保 datas 目录存在
  const datasDir = path.dirname(COOKIE_FILE);
  if (!fs.existsSync(datasDir)) {
    fs.mkdirSync(datasDir, { recursive: true });
  }

  console.log('🔗 正在打开通义官网...');
  try {
    await page.goto('https://www.qianwen.com/', { 
      timeout: 60000, 
      waitUntil: 'domcontentloaded' 
    });
  } catch (e) {
    console.log('⚠️  页面加载超时，但如果扫码界面已出现，请直接操作。');
  }

  console.log('\n------------------------------------------------');
  console.log('请在浏览器窗口中完成登录 (建议扫码)。');
  console.log('脚本正在监听重定向或登录状态...');
  console.log('------------------------------------------------\n');

  return new Promise((resolve, reject) => {
    let isFinished = false;

    const saveAndExit = async (reason) => {
      if (isFinished) return;
      isFinished = true;
      
      console.log(`\n✅ 检测到登录成功 (${reason})！正在保存 Cookie...`);
      const cookies = await context.cookies();
      fs.writeFileSync(COOKIE_FILE, JSON.stringify(cookies, null, 2));
      console.log(`✨ Cookie 已保存至: ${COOKIE_FILE}`);
      
      await browser.close();
      resolve();
    };

    // 逻辑 A: 监听 URL 重定向
    page.on('framenavigated', async (frame) => {
      if (frame !== page.mainFrame()) return;
      const url = page.url();
      // 如果跳转到了个人空间或创作页
      if (url.includes('/creations') || url.includes('/assistant') || (url.includes('qianwen.com') && !url.includes('login'))) {
        // 简单延迟确保 cookie 写入
        await new Promise(r => setTimeout(r, 2000));
        await saveAndExit('检测到页面重定向');
      }
    });

    // 逻辑 B: 定时轮询关键 Cookie
    const timer = setInterval(async () => {
      if (isFinished) {
        clearInterval(timer);
        return;
      }
      const cookies = await context.cookies();
      const hasTicket = cookies.some(c => c.name === 'tongyi_sso_ticket');
      if (hasTicket) {
        clearInterval(timer);
        await saveAndExit('检测到关键认证 Cookie');
      }
    }, 3000);

    // 逻辑 C: 超时保护
    setTimeout(async () => {
      if (!isFinished) {
        clearInterval(timer);
        console.log('\n❌ 登录超时 (5分钟)，脚本退出。');
        await browser.close();
        reject(new Error('Timeout'));
      }
    }, LOGIN_TIMEOUT);
  });
}

run().catch(err => {
  if (err.message !== 'Timeout') {
    console.error('💥 脚本运行出错:', err.message);
  }
  process.exit(1);
});
