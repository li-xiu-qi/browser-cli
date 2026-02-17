# Fluent UI Icon Fonts

This directory contains the icon font files from `@fluentui/font-icons-mdl2` package.

## Purpose

These fonts are hosted locally to avoid CORS issues when loading from Microsoft's CDN. The fonts are automatically loaded when the application initializes icons via `initializeIcons('/fonts/')` in `src/index.tsx`.

## Maintenance

If you update the `@fluentui/font-icons-mdl2` package version, you may need to update these font files:

```bash
cp node_modules/@fluentui/font-icons-mdl2/fonts/*.woff packages/rath-client/public/fonts/
```

## Files

The directory contains multiple font files (fabric-icons-*.woff) that are split by icon set to optimize loading performance.

