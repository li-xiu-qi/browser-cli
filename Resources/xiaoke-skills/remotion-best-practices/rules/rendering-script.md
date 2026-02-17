# Custom Rendering Script

For stable local rendering, especially on Windows, it is recommended to use a Node.js script instead of the CLI. This allows for better control over browser paths and launch arguments.

## Setup a Persistent Render Tool

Instead of installing dependencies every time, set up a local tool at `.gemini/tools/remotion-renderer`.

### Template `render.mjs`

This script automatically finds Chrome/Edge and renders the video.

```javascript
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import path from 'path';
import fs from 'fs';

const findBrowser = () => {
  const paths = [
    'C:\\ Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\ Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
  ];
  for (const p of paths) {
    if (fs.existsSync(p)) return p;
  }
  return null;
};

const start = async () => {
  const browserExecutable = findBrowser();
  if (!browserExecutable) throw new Error('Browser not found');

  const bundleLocation = await bundle({
    entryPoint: path.resolve('src/index.ts'),
    webpackOverride: (config) => config,
  });

  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: 'UserComposition',
    browserExecutable,
    chromiumOptions: { headless: false },
  });

  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: 'h264',
    outputLocation: path.resolve('output.mp4'),
    browserExecutable,
    chromiumOptions: { headless: false, gl: 'angle' },
  });
};

start();
```

## Usage

1. Write your component code to `src/UserComposition.tsx`.
2. Run `node render.mjs <output-path>`.
