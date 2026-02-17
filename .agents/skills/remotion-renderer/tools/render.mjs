import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import path from 'path';
import fs from 'fs';

// 自动查找浏览器路径
const findBrowser = () => {
  const paths = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  ];
  for (const p of paths) {
    if (fs.existsSync(p)) return p;
  }
  return null;
};

const start = async () => {
  try {
    const browserExecutable = findBrowser();
    if (!browserExecutable) {
      throw new Error('No Chrome or Edge installation found.');
    }
    console.log(`Using browser: ${browserExecutable}`);

    const outputArg = process.argv[2];
    const outputPath = outputArg ? path.resolve(outputArg) : path.resolve('output.mp4');

    console.log('Bundling...');
    const bundleLocation = await bundle({
      entryPoint: path.resolve('src/index.ts'),
      webpackOverride: (config) => config,
    });

    console.log('Selecting composition...');
    const composition = await selectComposition({
      serveUrl: bundleLocation,
      id: 'UserComposition',
      browserExecutable,
      chromiumOptions: { headless: false },
    });

    console.log(`Rendering to ${outputPath}...`);
    await renderMedia({
      composition,
      serveUrl: bundleLocation,
      codec: 'h264',
      outputLocation: outputPath,
      browserExecutable,
      chromiumOptions: {
        headless: false,
        gl: 'angle',
      },
    });

    console.log('Render complete!');
    process.exit(0);
  } catch (err) {
    console.error('Render failed:', err);
    process.exit(1);
  }
};

start();
