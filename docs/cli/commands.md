# CLI Commands

Fullbleed includes a command-line interface for rendering PDFs, scaffolding projects, and managing assets.

## `fullbleed render`

Render an HTML file to PDF.

```bash
fullbleed render input.html -o output.pdf
```

### Options

| Flag | Description |
|------|-------------|
| `-o`, `--output` | Output PDF file path |
| `--width` | Page width (e.g., `8.5in`) |
| `--height` | Page height (e.g., `11in`) |
| `--margin` | Page margin (single value, e.g., `0.85in`) |
| `--profile` | PDF profile: `none`, `tagged`, `pdfa2b`, `pdfx4` |
| `--title` | Document title |
| `--lang` | Document language (e.g., `en`) |
| `--header-each` | Header text for each page |
| `--footer-each` | Footer text for each page |

### Examples

```bash
# Basic render
fullbleed render report.html -o report.pdf

# Tagged PDF with headers
fullbleed render report.html -o report.pdf \
  --profile tagged \
  --title "Annual Report" \
  --lang en \
  --header-each "Annual Report — Page {page}/{pages}"

# Custom page size (A4)
fullbleed render report.html -o report.pdf \
  --width 210mm --height 297mm --margin 20mm
```

## `fullbleed init`

Scaffold a new Fullbleed project with example files and vendored assets.

```bash
fullbleed init my-project
cd my-project
```

This creates:
```
my-project/
├── components/       # Python component files
├── styles/           # CSS stylesheets
├── vendor/           # Vendored assets (Bootstrap, fonts, icons)
├── output/           # Rendered PDF output directory
├── fullbleed.yaml    # Project configuration
└── render.py         # Entry point script
```

### Running the Scaffold

```bash
cd my-project
python render.py
# → output/report.pdf
```

## `fullbleed assets`

Manage vendored assets.

```bash
# List installed assets
fullbleed assets list

# Show asset details
fullbleed assets info bootstrap-css
```

## `fullbleed render` with Agent Flags

For AI agent integration, additional flags provide machine-readable output:

```bash
# Render with full diagnostics (JSON to stdout)
fullbleed render input.html -o output.pdf --diagnostics

# Render with preview PNGs
fullbleed render input.html -o output.pdf --preview --preview-dpi 150

# Render with accessibility bundle
fullbleed render input.html -o output.pdf --a11y-bundle --bundle-dir ./evidence/
```

The `--a11y-bundle` flag produces the same 15 artifacts as `AccessibilityEngine.render_bundle()`, saved to the specified directory.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `FULLBLEED_LOG` | Log level: `error`, `warn`, `info`, `debug`, `trace` |
| `FULLBLEED_THREADS` | Max render threads (default: CPU count) |

## Next Steps

- [Scaffolding →](scaffolding.md) — Deep dive on project scaffolding
- [Diagnostics →](diagnostics.md) — CLI diagnostic output
- [Quick Start →](../getting-started/quickstart.md) — Getting started guide
