const { chromium } = require('playwright');
const { PDFDocument } = require('pdf-lib');
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const { spawn } = require('child_process');

// 使用项目统一的浏览器数据目录
const USER_DATA_DIR = path.join(__dirname, '..', '..', 'user_data');
const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

async function run() {
  if (process.argv.includes('-bg')) {
    const args = process.argv.slice(1).filter(arg => arg !== '-bg');
    const logFile = path.join(__dirname, 'crawl.log');
    const out = fs.openSync(logFile, 'w');
    const err = fs.openSync(logFile, 'w');

    console.log('🚀 任务已转入后台运行！');
    console.log(`📄 实时日志: ${logFile}`);
    console.log('您可以关闭此终端，任务将持续进行。');

    const subprocess = spawn(process.argv[0], args, {
      detached: true,
      stdio: ['ignore', out, err]
    });

    subprocess.unref();
    process.exit(0);
  }

  const mode = process.argv[2];

  if (mode === 'login') {
    await runLoginMode();
  } else if (mode === 'crawl') {
    const bookUrl = process.argv[3];
    const saveLong = process.argv.includes('--save-long');
    const keepImages = process.argv.includes('--keep-images');
    if (!bookUrl) {
      console.log('请提供书籍 URL');
      process.exit(1);
    }
    await runCrawlMode(bookUrl, saveLong, keepImages);
  } else {
    console.log('请选择模式:');
    console.log('  node index.js login');
    console.log('  node index.js crawl [URL] [--save-long] [--keep-images]');
  }
}

async function runLoginMode() {
  console.log('正在启动登录模式...');
  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    viewport: null,
    userAgent: USER_AGENT,
    args: ['--disable-blink-features=AutomationControlled', '--start-maximized'],
  });

  const page = await context.newPage();
  await page.goto('https://weread.qq.com/');
  console.log('请扫码登录，完成后回车退出...');
  await new Promise(resolve => process.stdin.once('data', resolve));
  await context.close();
}

async function runCrawlMode(bookUrl, saveLong, keepImages) {
  console.log(`正在启动抓取模式: ${bookUrl}`);
  
  const bookIdMatch = bookUrl.match(/\/reader\/([^?\/]+)/);
  const bookId = bookIdMatch ? bookIdMatch[1] : `unknown_${Date.now()}`;
  const outputDir = path.join(__dirname, 'output', `book_${bookId}`);
  
  // 分层目录结构
  const imagesDir = path.join(outputDir, 'images');
  const longDir = path.join(imagesDir, 'long');
  const pagesDir = path.join(imagesDir, 'pages');

  if (!fs.existsSync(longDir)) fs.mkdirSync(longDir, { recursive: true });
  if (!fs.existsSync(pagesDir)) fs.mkdirSync(pagesDir, { recursive: true });

  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    headless: false,
    viewport: null,
    userAgent: USER_AGENT,
    args: ['--disable-blink-features=AutomationControlled', '--start-maximized'],
  });

  const page = await context.newPage();
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
  });

  await page.goto(bookUrl, { timeout: 60000, waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(5000);

  try {
    await captureBook(page, outputDir, longDir, pagesDir, saveLong, keepImages);
  } catch (err) {
    console.error('抓取中发生错误:', err);
  } finally {
    await context.close();
  }
}

async function captureBook(page, outputDir, longDir, pagesDir, saveLong, keepImages) {
  const finalPagePaths = [];
  let partIndex = 1;

  while (true) {
    console.log(`\n--- 正在处理第 ${partIndex} 批次 ---`);
    await cleanUI(page);
    
    await page.waitForSelector('.wr_canvasContainer', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(2000);

    const readerSelector = '.wr_canvasContainer'; 
    const readerElement = await page.$(readerSelector);

    if (readerElement) {
      const { totalHeight, viewHeight } = await page.evaluate((sel) => {
        const el = document.querySelector(sel);
        return { totalHeight: el ? el.scrollHeight : 0, viewHeight: window.innerHeight };
      }, readerSelector);

      console.log(`  内容高度: ${totalHeight}px，执行步进滚动...`);
      const steps = Math.max(2, Math.ceil(totalHeight / (viewHeight * 0.8)));
      for (let i = 1; i <= steps; i++) {
        await page.evaluate(({ step, vh }) => window.scrollTo(0, step * vh * 0.8), { step: i, vh: viewHeight });
        await page.waitForTimeout(800 + Math.random() * 800);
        if ((await page.evaluate(() => window.scrollY + window.innerHeight)) >= totalHeight) break;
      }

      console.log('  正在截图并保存长图原稿...');
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(1500);

      const longImgPath = path.join(longDir, `chapter_${partIndex.toString().padStart(3, '0')}.png`);
      
      await readerElement.screenshot({ path: longImgPath });

      console.log('  正在进行 A4 智能切分...');
      const splitPaths = await splitLongImage(longImgPath, pagesDir, partIndex);
      finalPagePaths.push(...splitPaths);

      // 根据参数决定是否保留长图原稿
      if (!saveLong && fs.existsSync(longImgPath)) {
        fs.unlinkSync(longImgPath);
      } else {
        console.log(`  已保留长图原稿: chapter_${partIndex.toString().padStart(3, '0')}.png`);
      }
    }

    const nextBtnSelector = 'button.readerFooter_button[title="下一页"], button.readerFooter_button[title="下一章"]';
    let nextBtn = await page.$(nextBtnSelector);

    if (!nextBtn) {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(3000);
      nextBtn = await page.$(nextBtnSelector);
    }

    if (nextBtn) {
      const title = await nextBtn.getAttribute('title');
      console.log(`  跳转至“${title}”...`);
      await page.waitForTimeout(2000 + Math.random() * 2000);

      await page.evaluate((sel) => {
        const footer = document.querySelector('.readerFooter');
        if (footer) {
          footer.style.setProperty('visibility', 'visible', 'important');
          footer.style.setProperty('display', 'block', 'important');
        }
        const btn = document.querySelector(sel);
        if (btn) {
          btn.style.setProperty('display', 'block', 'important');
          btn.style.setProperty('visibility', 'visible', 'important');
          btn.scrollIntoView();
        }
      }, nextBtnSelector);
      
      await page.waitForTimeout(1000);
      await nextBtn.click();
      partIndex++;
      await page.waitForTimeout(4000 + Math.random() * 3000); 
    } else {
      console.log('  抓取结束。');
      break;
    }

    if (partIndex > 1000) break;
  }

  if (finalPagePaths.length > 0) {
    console.log(`\n正在合并 ${finalPagePaths.length} 张分页图片为 PDF...`);
    const pdfPath = path.join(outputDir, 'book_result.pdf');
    await createPdf(finalPagePaths, pdfPath);
    
    // 清理逻辑
    if (!keepImages) {
      console.log('  正在清理中间图片目录...');
      const imagesDir = path.dirname(longDir);
      fs.rmSync(imagesDir, { recursive: true, force: true });
    }

    console.log(`\n====================================`);
    console.log(`完成！`);
    if (keepImages) {
      console.log(`长图目录: ${longDir}`);
      console.log(`分页目录: ${pagesDir}`);
    }
    console.log(`PDF 路径: ${pdfPath}`);
    console.log(`====================================`);
  }
}

async function splitLongImage(imgPath, pagesDir, batchIdx) {
  const image = sharp(imgPath);
  const metadata = await image.metadata();
  const width = metadata.width;
  const height = metadata.height;
  
  const targetHeight = Math.floor(width * 1.414);
  const splitPaths = [];
  const { data } = await image.raw().grayscale().toBuffer({ resolveWithObject: true });

  let currentY = 0;
  let subIdx = 1;

  while (currentY < height) {
    let nextY = currentY + targetHeight;
    
    if (nextY >= height) {
      nextY = height;
    } else {
      let bestY = nextY;
      let maxBrightness = -1;
      const searchStart = Math.max(currentY + 500, nextY - 300);
      const searchEnd = Math.min(height - 1, nextY + 300);

      for (let y = searchStart; y < searchEnd; y++) {
        let rowBrightness = 0;
        for (let x = 0; x < width; x++) {
          rowBrightness += data[y * width + x];
        }
        if (rowBrightness >= maxBrightness) {
          maxBrightness = rowBrightness;
          bestY = y;
        }
      }
      nextY = bestY;
    }

    const subImgPath = path.join(pagesDir, `page_${batchIdx.toString().padStart(3, '0')}_${subIdx.toString().padStart(2, '0')}.png`);
    const extractHeight = nextY - currentY;
    
    if (extractHeight > 20) {
      await sharp(imgPath).extract({ left: 0, top: currentY, width: width, height: extractHeight }).toFile(subImgPath);
      splitPaths.push(subImgPath);
    }
    currentY = nextY;
    subIdx++;
  }
  return splitPaths;
}

async function cleanUI(page) {
  await page.evaluate(() => {
    const selectors = [
      '.readerTopBar', '.readerControls', '.extra_reader_controls',
      '.readerApp_download_guide', '.readerNotePanel',
      '.readerCatalogSideBar', '.reader_dialog_wrapper'
    ];
    selectors.forEach(s => document.querySelectorAll(s).forEach(el => el.style.setProperty('display', 'none', 'important')));
    
    const footer = document.querySelector('.readerFooter');
    if (footer) {
      footer.style.setProperty('visibility', 'hidden', 'important');
      footer.style.setProperty('display', 'block', 'important');
    }

    const content = document.querySelector('.readerContent');
    if (content) {
      content.style.setProperty('padding', '0', 'important');
      content.style.setProperty('margin', '0 auto', 'important');
    }
    document.body.style.overflow = 'auto';
  });
}

async function createPdf(imagePaths, outputPath) {
  const pdfDoc = await PDFDocument.create();
  for (const imgPath of imagePaths) {
    const imgBytes = fs.readFileSync(imgPath);
    const img = await pdfDoc.embedPng(imgBytes);
    const page = pdfDoc.addPage([img.width, img.height]);
    page.drawImage(img, { x: 0, y: 0, width: img.width, height: img.height });
  }
  const pdfBytes = await pdfDoc.save();
  fs.writeFileSync(outputPath, pdfBytes);
}

run();