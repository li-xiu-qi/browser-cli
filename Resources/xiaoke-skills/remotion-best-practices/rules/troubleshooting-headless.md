# Troubleshooting: Headless Mode Issues on Windows

When rendering videos locally on Windows, you might encounter issues with the default headless mode of Chrome/Edge, especially with recent browser updates that removed the old headless implementation.

## Common Error

```
Error: Failed to launch the browser process!
Old Headless mode has been removed from the Chrome binary.
```

## Solution 1: Use `headless: 'new'` (If supported)

In your `remotion.config.ts` or render script, try setting the mode to "new".

```ts
// render.mjs
chromiumOptions: {
  headless: 'new',
}
```

## Solution 2: Disable Headless Mode (Most Reliable)

If `new` headless mode fails or hangs (common in some environments), forcing a visible browser window is often the most reliable workaround for local rendering.

```ts
// render.mjs
chromiumOptions: {
  headless: false, // Browser window will pop up briefly
  gl: 'angle',     // Recommended for Windows to fix WebGL issues
}
```

## Solution 3: Use a Custom Render Script

Avoid relying solely on the CLI (`npx remotion render`). Use a Node.js script to have full control over Puppeteer launch arguments. See `rendering-script.md` for a template.