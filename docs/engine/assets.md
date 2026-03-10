# Asset Management

Fullbleed includes a built-in asset management system for fonts, CSS frameworks, and icon sets. Assets are vendored locally so your documents render consistently regardless of network availability.

## Listing Available Assets

```bash
fullbleed assets list
```

This shows installed asset packages with their versions and types.

## Built-in Assets

When you scaffold a project with `fullbleed init`, these assets are vendored automatically:

| Asset | Type | Description |
|-------|------|-------------|
| Bootstrap CSS | Stylesheet | Utility classes and grid system |
| Noto Sans | Font | Google's multi-language font family |
| Bootstrap Icons | Icon Font | 2,000+ SVG icons as a web font |

## Using Assets in HTML

### Fonts

Reference vendored fonts in your CSS:

```html
<style>
  body {
    font-family: 'Noto Sans', sans-serif;
  }
</style>
```

Fullbleed resolves font references during rendering and embeds them in the PDF. No system font installation required.

### CSS Frameworks

Include vendored CSS files:

```html
<link rel="stylesheet" href="vendor/bootstrap.min.css">
```

Or reference them in the scaffold structure created by `fullbleed init`.

### Icons

Use Bootstrap Icons via their CSS classes:

```html
<i class="bi bi-check-circle" style="color: green;"></i> Approved
<i class="bi bi-x-circle" style="color: red;"></i> Rejected
```

## Font Resolution

Fullbleed resolves fonts in this order:

1. **Vendored fonts** — local copies in your project
2. **System fonts** — installed on the host machine
3. **Fallback** — built-in default font

The `font_resolution_trace` in the evidence bundle (from `AccessibilityEngine.render_bundle()`) shows exactly how each font reference was resolved:

```python
results = engine.render_bundle(html)
trace = results["font_resolution_trace"]
for entry in trace["resolutions"]:
    print(f"  {entry['requested']} → {entry['resolved']} ({entry['source']})")
```

## Custom Fonts

To use custom fonts, place them in your project directory and reference them in CSS:

```html
<style>
  @font-face {
    font-family: 'MyBrandFont';
    src: url('fonts/MyBrandFont-Regular.woff2') format('woff2');
  }
  body { font-family: 'MyBrandFont', sans-serif; }
</style>
```

Fullbleed embeds the font data directly into the PDF — no external font server needed.

## Image Resolution

Images referenced in HTML are resolved similarly:

```html
<img src="images/logo.png" alt="Company Logo" width="200">
```

Fullbleed supports:

- **Local files** — relative or absolute paths
- **Data URIs** — `data:image/png;base64,...`
- **SVG** — inline `<svg>` elements or referenced `.svg` files

The `asset_resolution_trace` documents how each asset was found and embedded.

## Next Steps

- [Scaffolding →](../cli/scaffolding.md) — Generate a project with vendored assets
- [PdfEngine API →](pdf-engine.md) — Full constructor reference
- [CSS Coverage →](../css-coverage.md) — Supported CSS properties
