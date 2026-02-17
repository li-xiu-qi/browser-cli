/**
 * 通义听悟配置文件 (config.js)
 * 
 * 优先级：
 * 1. datas/cookies.json - 通过 login_handler.js 自动获取
 * 2. DEFAULT_COOKIE - 手动配置的备用 Cookie
 * 
 * 提示：
 *   推荐先运行 `node login_handler.js` 完成登录，Cookie 会自动保存。
 *   如果自动登录不可用，可以手动填写 DEFAULT_COOKIE。
 */

const fs = require('fs');
const path = require('path');

// 优先从 datas/cookies.json 读取
const COOKIE_FILE = path.join(__dirname, 'datas', 'cookies.json');
let COOKIE = '';

try {
  if (fs.existsSync(COOKIE_FILE)) {
    const cookieData = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf-8'));
    // 兼容数组格式(Playwright)和字符串格式
    if (Array.isArray(cookieData)) {
      COOKIE = cookieData.map(c => `${c.name}=${c.value}`).join('; ');
    } else if (cookieData.cookie) {
      COOKIE = cookieData.cookie;
    }
  }
} catch (e) {
  console.error('读取 cookies.json 失败，将使用默认配置');
}

// 备用 Cookie（手动配置）
// 格式: "name1=value1; name2=value2; ..."
const DEFAULT_COOKIE = '';

// XSRF Token（需要从浏览器开发者工具获取）
// 在通义听悟网页按 F12 -> Network -> 任意请求 -> Headers -> x-xsrf-token
const XSRF_TOKEN = '';

module.exports = {
  HEADERS: {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json',
    'cookie': COOKIE || DEFAULT_COOKIE,
    'priority': 'u=1, i',
    'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'x-platform': 'pc_tongyi',
    'x-xsrf-token': XSRF_TOKEN || '9e54d3f4-106e-4155-adb9-da11e986e018',
    'x-tw-canary': '',
    'x-tw-from': 'tongyi',
    'Referer': 'https://www.qianwen.com/',
    'Origin': 'https://www.qianwen.com',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
  },
  BASE_URL: 'https://api.qianwen.com/assistant/api'
};
