# FAQ

## General

### What is Fullbleed?

Fullbleed is a deterministic HTML/CSS-to-PDF rendering engine written in Rust with Python bindings. It generates tagged, accessible PDFs without browser dependencies.

### How is it different from wkhtmltopdf / Puppeteer / WeasyPrint?

| | Fullbleed | wkhtmltopdf | Puppeteer | WeasyPrint |
|-|-----------|-------------|-----------|------------|
| Browser needed | ❌ | Qt WebKit | Chromium | ❌ |
| Deterministic | ✅ SHA256 | ❌ | ❌ | ❌ |
| Tagged PDF/UA | ✅ | ❌ | ❌ | Partial |
| Parallel render | ✅ Rayon | ❌ | Manual | ❌ |
| Evidence bundles | ✅ | ❌ | ❌ | ❌ |
| Actively maintained | ✅ | ❌ Deprecated | ✅ | ✅ |

See the [full comparison guide →](guides/comparison.md)

### Is it free?

Yes. Fullbleed is dual-licensed under AGPL-3.0 (free/open source) and a commercial license for organizations that can't use AGPL.

### What Python versions are supported?

Python 3.8+.

### What platforms are supported?

- Linux (x86_64, aarch64)
- macOS (x86_64, Apple Silicon)
- Windows (x86_64)

Pre-built wheels are available on PyPI for all platforms. No compilation needed.

## Installation

### Do I need to install Rust?

No. `pip install fullbleed` installs pre-built binary wheels. Rust is only needed if you're building from source.

### Do I need system dependencies?

No. Unlike wkhtmltopdf (Qt) or Puppeteer (Chromium), Fullbleed has zero system dependencies. The entire engine is in the Python wheel.

### Can I use it in Docker?

Yes. A minimal `python:3.11-slim` image works:

```dockerfile
FROM python:3.11-slim
RUN pip install fullbleed
COPY . /app
WORKDIR /app
CMD ["python", "render.py"]
```

No `apt-get install` for browser dependencies.

## Rendering

### What CSS is supported?

Fullbleed supports the most common CSS properties for document layout: flexbox, positioning, typography, borders, tables, colors, and print-specific properties. See [CSS Coverage →](css-coverage.md) for the full list.

Notable gaps: no CSS Grid, no `calc()`, no CSS variables, no media queries.

### Can I render from a URL?

Not directly. Fullbleed renders HTML strings, not URLs. Fetch the HTML yourself and pass it to the engine:

```python
import requests
from fullbleed import PdfEngine

html = requests.get("https://example.com/report").text
engine = PdfEngine()
pdf = engine.render(html)
```

### How do I add page breaks?

Use CSS `page-break-before: always` or `break-before: page`:

```html
<div style="page-break-before: always;">
  This starts on a new page.
</div>
```

### Why doesn't `break-inside: avoid` work?

`break-inside: avoid` is a *hint* to the layout engine. In complex documents with large elements, it may not always be respected. For reliable page control, use explicit page breaks with `page-break-before: always`.

### How do I add headers and footers?

Use engine parameters, not CSS `@page`:

```python
engine = PdfEngine(
    header_each="Report — Page {page} of {pages}",
    footer_each="Confidential",
)
```

See [Headers & Footers →](engine/headers-footers.md)

### What about CSS `@page` margin boxes?

Not supported. Use `header_each`, `footer_each`, etc. These are more powerful (they support HTML content and paginated context placeholders) and work consistently.

## Accessibility

### What does "tagged PDF" mean?

A tagged PDF contains a structure tree that maps visual content to semantic elements (headings, paragraphs, tables, lists). Screen readers use this tree to read the document in the correct order with proper context.

### Do I need to do anything special for accessibility?

Write semantic HTML. That's it. Fullbleed converts HTML structure to PDF tags automatically.

```html
<!-- This HTML automatically produces accessible tags -->
<h1>Title</h1>
<p>Paragraph</p>
<table>
  <caption>Data</caption>
  <thead><tr><th scope="col">Header</th></tr></thead>
  <tbody><tr><td>Cell</td></tr></tbody>
</table>
```

### What's a PMR score?

PMR (Pagination/Markup/Readability) is Fullbleed's composite accessibility score on a 0–100 scale. It quantifies how well your document is structured for accessibility. A score of 90+ is "excellent."

### What's an evidence bundle?

The 15 artifacts produced by `AccessibilityEngine.render_bundle()` — the tagged PDF plus all verification reports, traces, and diagnostics. Used for audit trails and compliance documentation.

See [Evidence Bundles →](accessibility/evidence-bundles.md)

### Is Fullbleed compliant with the ADA Title II deadline?

Fullbleed generates PDFs that meet WCAG 2.0 AA and PDF/UA requirements. For the April 24, 2026 ADA Title II deadline, documents generated from semantic HTML with `AccessibilityEngine` should meet compliance requirements. The evidence bundle provides documentation for auditors.

## Performance

### How fast is it?

Typical render times are sub-second for single documents. In parallel batch mode with 8 threads, throughput scales near-linearly.

### Can I render in parallel?

Yes. Use Python's `ThreadPoolExecutor` — Fullbleed releases the GIL on every render call, so threads actually run in parallel.

```python
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(render_one, documents))
```

See [Batch Rendering →](engine/batch.md)

### Memory usage?

Proportional to document size. No browser processes, so no 200MB-per-tab overhead. A typical document render uses 10–50MB.

## Licensing

### Can I use AGPL in my company?

AGPL requires that if you modify Fullbleed and serve the modifications over a network, you must release your modifications under AGPL. If you use Fullbleed unmodified as a dependency, your own code doesn't need to be AGPL — but consult your legal team.

### What about the commercial license?

Contact [keenan@fullbleed.dev](mailto:keenan@fullbleed.dev) for commercial licensing terms. The commercial license removes AGPL obligations.
