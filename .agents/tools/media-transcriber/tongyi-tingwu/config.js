/**
 * 通义听悟配置文件 (config.js)
 * 
 * 优先级：
 * 1. datas/cookies.json - 推荐来自 browser-cli 或其他浏览器会话导出，或 login_handler.js
 * 2. DEFAULT_COOKIE - 手动配置的备用 Cookie
 * 
 * 提示：
 *   当前更推荐直接复用已经登录的浏览器会话，把 qianwen cookies 写入 datas/cookies.json。
 *   如果当前会话不可用，再运行 `node login_handler.js` 打开独立浏览器完成登录。
 *   XSRF-TOKEN 现在会优先从 cookies.json 自动提取。
 */

const fs = require('fs');
const path = require('path');

// 优先从 datas/cookies.json 读取
// 该文件属于本地登录态，不应提交真实内容到版本库
const COOKIE_FILE = path.join(__dirname, 'datas', 'cookies.json');
let COOKIE = '';
let COOKIE_DATA = null;
let COOKIE_XSRF_TOKEN = '';

try {
  if (fs.existsSync(COOKIE_FILE)) {
    const cookieData = JSON.parse(fs.readFileSync(COOKIE_FILE, 'utf-8'));
    COOKIE_DATA = cookieData;
    // 兼容数组格式(Playwright)和字符串格式
    if (Array.isArray(cookieData)) {
      COOKIE = cookieData.map(c => `${c.name}=${c.value}`).join('; ');
      const preferredXsrf =
        cookieData.find(c => c.name === 'XSRF-TOKEN' && c.domain === 'api.qianwen.com') ||
        cookieData.find(c => c.name === 'XSRF-TOKEN' && String(c.domain || '').includes('qianwen.com'));
      if (preferredXsrf && preferredXsrf.value) {
        COOKIE_XSRF_TOKEN = preferredXsrf.value;
      }
    } else if (cookieData.cookie) {
      COOKIE = cookieData.cookie;
      if (cookieData.xsrfToken) {
        COOKIE_XSRF_TOKEN = cookieData.xsrfToken;
      }
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
    'x-xsrf-token': COOKIE_XSRF_TOKEN || XSRF_TOKEN || '9e54d3f4-106e-4155-adb9-da11e986e018',
    'x-tw-canary': '',
    'x-tw-from': 'tongyi',
    'Referer': 'https://www.qianwen.com/',
    'Origin': 'https://www.qianwen.com',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
  },
  BASE_URL: 'https://api.qianwen.com/assistant/api'
};
