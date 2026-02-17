const { chromium } = require('playwright');
const TurndownService = require('turndown');
const Defuddle = require('defuddle');
const { JSDOM } = require('jsdom');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// 统一使用项目级浏览器用户数据目录（共享登录状态）
const SHARED_DATA_DIR = path.resolve(__dirname, '..', '..', '..', '..', '..', '.agents', 'browser_user_data');
console.log(`使用共享 user-data-dir: ${SHARED_DATA_DIR}`);

/**
 * 从微信公众号图片元素中提取真实图片URL
 * 微信使用懒加载，真实URL通常在 data-src 属性中
 */
function extractWechatImageUrl(img) {
    // 尝试各种可能的属性
    const possibleAttrs = ['data-src', 'data-original', 'src', 'data-url', 'data-link'];
    
    for (const attr of possibleAttrs) {
        const value = img.getAttribute(attr);
        if (value && !value.includes('data:image/svg+xml') && value.length > 10) {
            // 如果是相对路径，转换为绝对路径
            if (value.startsWith('//')) {
                return 'https:' + value;
            }
            return value;
        }
    }
    
    return null;
}

/**
 * 检查是否是占位图
 */
function isPlaceholderImage(src) {
    if (!src) return true;
    return src.includes('data:image/svg+xml') || 
           src.includes('data:image/gif;base64') ||
           src.includes('placeholder') ||
           src.length < 50;
}

async function scrapeWithRetry(url, outputDir, maxRetries = 3) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        console.log(`\n[Attempt ${attempt}/${maxRetries}] Navigating to ${url}...`);
        
        const context = await chromium.launchPersistentContext(SHARED_DATA_DIR, {
            headless: false,
            viewport: { width: 1920, height: 1080 },
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
            args: [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--window-size=1920,1080',
                '--no-startup-focus',
                '--window-position=200,200'
            ]
        });
        
        const page = await context.newPage();
        
        try {
            // 访问页面 - 延长超时时间
            console.log('正在加载页面（最多等待2分钟）...');
            await page.goto(url, { waitUntil: 'networkidle', timeout: 120000 });
            
            // 等待页面稳定 - 增加到15秒确保懒加载触发
            console.log('等待页面稳定...');
            await page.waitForTimeout(15000);
            
            // 在浏览器中处理图片懒加载 - 改进版
            console.log('处理图片懒加载（完整滚动）...');
            await page.evaluate(async () => {
                // 预加载所有可能的图片
                const preloadImages = () => {
                    document.querySelectorAll('img').forEach(img => {
                        const realSrc = img.getAttribute('data-src') || 
                                       img.getAttribute('data-original') || 
                                       img.getAttribute('data-url') ||
                                       img.getAttribute('data-link') ||
                                       img.getAttribute('data-ratio');
                        
                        if (realSrc && !realSrc.includes('data:image/svg+xml')) {
                            img.setAttribute('data-real-src', realSrc);
                            img.src = realSrc;
                        }
                    });
                };
                
                // 先预加载一次
                preloadImages();
                
                // 分阶段滚动，确保所有懒加载触发
                const scrollSteps = [
                    { distance: 500, wait: 1000 },   // 快速滚动上半部分
                    { distance: 800, wait: 1500 },   // 中等速度滚动中间
                    { distance: 1000, wait: 2000 },  // 慢速滚动底部
                ];
                
                let currentScroll = 0;
                const maxScroll = document.body.scrollHeight - window.innerHeight;
                
                for (const step of scrollSteps) {
                    while (currentScroll < maxScroll) {
                        currentScroll = Math.min(currentScroll + step.distance, maxScroll);
                        window.scrollTo(0, currentScroll);
                        await new Promise(r => setTimeout(r, step.wait));
                        
                        // 每滚动一次就预加载新出现的图片
                        preloadImages();
                    }
                    
                    // 重置到底部再往上滚
                    if (currentScroll >= maxScroll) {
                        await new Promise(r => setTimeout(r, 2000));
                        // 往上滚动一点，有时微信会反向加载
                        window.scrollTo(0, maxScroll * 0.8);
                        await new Promise(r => setTimeout(r, 1000));
                        currentScroll = maxScroll * 0.8;
                    }
                }
                
                // 最终滚动到底
                window.scrollTo(0, maxScroll);
                await new Promise(r => setTimeout(r, 3000));
                
                // 最后预加载一次
                preloadImages();
                
                // 滚动回顶部
                window.scrollTo(0, 0);
            });
            
            // 增加等待时间确保图片加载
            console.log('等待图片加载完成...');
            await page.waitForTimeout(5000);
            
            const fullHtml = await page.content();
            
            // 检查是否需要人工干预（微信验证）
            if (fullHtml.includes("环境异常") || fullHtml.includes("访问频繁") || 
                fullHtml.includes("请完成验证") || fullHtml.includes("为了你的账号安全")) {
                console.log('\n========================================');
                console.log('⚠️  检测到微信安全验证');
                console.log('请在浏览器窗口中完成验证操作');
                console.log('========================================\n');
                
                // 暂停等待用户完成验证
                const rl = readline.createInterface({
                    input: process.stdin,
                    output: process.stdout
                });
                
                await new Promise(resolve => {
                    rl.question('验证完成后请按回车键继续...', () => {
                        rl.close();
                        resolve();
                    });
                });
                
                // 重新获取页面内容
                console.log('重新获取页面内容...');
                await page.waitForTimeout(5000);
                fullHtml = await page.content();
            }
            
            // 处理图片：使用 JSDOM 替换占位图
            const dom = new JSDOM(fullHtml, { url });
            const document = dom.window.document;
            
            // 处理所有图片
            let fixedCount = 0;
            let placeholderCount = 0;
            
            document.querySelectorAll('img').forEach(img => {
                // 首先检查我们之前标记的 data-real-src
                const realSrc = img.getAttribute('data-real-src');
                
                if (realSrc && !realSrc.includes('data:image/svg+xml')) {
                    img.src = realSrc;
                    fixedCount++;
                    console.log(`修复图片: ${realSrc.substring(0, 80)}...`);
                } else {
                    // 尝试其他属性
                    const extractedUrl = extractWechatImageUrl(img);
                    if (extractedUrl) {
                        img.src = extractedUrl;
                        fixedCount++;
                        console.log(`提取图片: ${extractedUrl.substring(0, 80)}...`);
                    } else if (isPlaceholderImage(img.src)) {
                        placeholderCount++;
                        // 标记占位图
                        img.setAttribute('data-is-placeholder', 'true');
                    }
                }
            });
            
            console.log(`图片处理完成: ${fixedCount} 张已修复, ${placeholderCount} 张仍为占位图`);
            
            // 使用 Defuddle 提取内容
            const defuddled = new Defuddle(document, { url }).parse();
            
            const turndownService = new TurndownService({
                headingStyle: 'atx',
                hr: '---',
                bulletListMarker: '-',
                codeBlockStyle: 'fenced',
                emDelimiter: '*', 
                preformattedCode: true,
            });
            
            // 自定义图片处理规则
            turndownService.addRule('wechatImages', {
                filter: 'img',
                replacement: function(content, node) {
                    const src = node.getAttribute('src');
                    const alt = node.getAttribute('alt') || '图片';
                    
                    // 跳过占位图
                    if (!src || isPlaceholderImage(src) || node.getAttribute('data-is-placeholder') === 'true') {
                        return '';
                    }
                    
                    return `\n![${alt}](${src})\n`;
                }
            });
            
            let markdown = turndownService.turndown(defuddled.content);
            
            // 提取标题
            let title = defuddled.title || '未命名文章';
            
            // 清理
            markdown = markdown.replace(/\n{3,}/g, '\n\n');
            
            // 添加 frontmatter
            const now = new Date().toISOString().split('T')[0];
            const frontmatter = `---\ntitle: "${title}"\nsource: "${url}"\nclipped: ${now}\ntags:\n  - clippings\n---\n\n`;
            markdown = frontmatter + markdown;
            
            // 确保输出目录存在
            if (!fs.existsSync(outputDir)) {
                fs.mkdirSync(outputDir, { recursive: true });
            }
            
            // 安全文件名
            const safeTitle = title.replace(/[\\/:*?"<>|]/g, '_').substring(0, 50);
            const outputPath = path.join(outputDir, `${safeTitle}.md`);
            
            fs.writeFileSync(outputPath, markdown, 'utf-8');
            console.log(`✓ 文章已保存: ${outputPath}`);
            
            await context.close();
            return outputPath;
            
        } catch (error) {
            console.error(`✗ Error: ${error.message}`);
            await context.close();
            
            if (attempt === maxRetries) {
                throw new Error(`Failed after ${maxRetries} attempts`);
            }
            
            console.log(`Retrying in 5 seconds...`);
            await new Promise(r => setTimeout(r, 5000));
        }
    }
}

// 主程序
const url = process.argv[2];
// 默认输出到 0_Inbox/image-staging/cliper_datas/ 便于在 Obsidian 中查看
const DEFAULT_OUTPUT_DIR = path.resolve(__dirname, '..', '..', '..', '..', '..', '0_Inbox', 'image-staging', 'cliper_datas');
const outputDir = process.argv[3] || DEFAULT_OUTPUT_DIR;

if (!url) {
    console.error('Usage: node web_clipper.js <URL> [outputDir]');
    process.exit(1);
}

scrapeWithRetry(url, outputDir)
    .then(() => process.exit(0))
    .catch(err => {
        console.error(`Failed: ${err.message}`);
        process.exit(1);
    });
