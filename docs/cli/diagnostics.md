# CLI Diagnostics

Fullbleed can output structured diagnostic information during rendering, useful for debugging layout issues, font problems, and accessibility verification.

## Diagnostic Flags

```bash
# Enable verbose logging
FULLBLEED_LOG=debug fullbleed render input.html -o output.pdf

# Output diagnostics as JSON
fullbleed render input.html -o output.pdf --diagnostics

# Generate preview PNGs alongside the PDF
fullbleed render input.html -o output.pdf --preview --preview-dpi 150

# Full accessibility bundle
fullbleed render input.html -o output.pdf --a11y-bundle --bundle-dir ./evidence/
```

## Log Levels

Set via the `FULLBLEED_LOG` environment variable:

| Level | Description |
|-------|-------------|
| `error` | Only errors (default) |
| `warn` | Errors + warnings |
| `info` | General progress information |
| `debug` | Detailed render pipeline information |
| `trace` | Everything, including CSS resolution details |

## Diagnostic Output

The `--diagnostics` flag outputs a JSON object to stdout with:

```json
{
  "render_time_ms": 142,
  "pages": 3,
  "output_size_bytes": 245832,
  "fonts_used": ["Noto Sans", "Noto Sans Bold"],
  "images_embedded": 2,
  "css_properties_used": 47,
  "warnings": []
}
```

## Accessibility Bundle Output

The `--a11y-bundle` flag creates a directory with the full evidence bundle:

```
evidence/
├── output.pdf           # Tagged PDF/UA
├── a11y-report.json     # Accessibility verification
├── pmr-score.json       # PMR score breakdown
├── pdfua-verify.json    # PDF/UA structural checks
├── reading-order.json   # Reading order trace
├── structure-trace.json # Tag tree
├── cross-check.json     # Render vs. extraction comparison
├── preview-1.png        # Page 1 preview
├── preview-2.png        # Page 2 preview
├── preview-3.png        # Page 3 preview
└── run-report.json      # Overall status
```

This is the CLI equivalent of `AccessibilityEngine.render_bundle()`.

## Debugging Common Issues

### Fonts Not Rendering

```bash
FULLBLEED_LOG=debug fullbleed render input.html -o output.pdf 2>&1 | grep -i font
```

Look for font resolution messages showing which fonts were requested vs. what was resolved.

### Unexpected Page Breaks

```bash
fullbleed render input.html -o output.pdf --diagnostics
```

Check the `pages` count and use `--preview` to visually inspect where breaks occurred.

### CSS Not Applied

```bash
FULLBLEED_LOG=trace fullbleed render input.html -o output.pdf
```

The trace level shows every CSS property resolution, including which selectors matched and what values were computed.

## Next Steps

- [CLI Commands →](commands.md) — Full CLI reference
- [Evidence Bundles →](../accessibility/evidence-bundles.md) — Understanding bundle artifacts
- [CSS Coverage →](../css-coverage.md) — Supported CSS properties
