# Fullbleed vs Other PDF Generators

A practical comparison for developers evaluating HTML-to-PDF tools.

## Quick Comparison

| | Fullbleed | wkhtmltopdf | Puppeteer / Playwright | WeasyPrint | Prince |
|---|---|---|---|---|---|
| **Engine** | Native Rust | Qt WebKit | Chromium | Custom Python | Custom C++ |
| **Browser required** | No | Yes (bundled) | Yes (downloads) | No | No |
| **Install** | `pip install` | System package | npm + browser binary | `pip install` | Paid installer |
| **Deterministic** | ✅ SHA256 | ❌ | ❌ | ❌ | ❌ |
| **Python GIL release** | ✅ | N/A | N/A | ❌ | N/A |
| **Parallel rendering** | ✅ Native Rayon | ❌ | Process pool | ❌ | ❌ |
| **Headers/footers** | Built-in engine | `--header-html` flag | JS injection | CSS `@page` | CSS `@page` |
| **Per-page running totals** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **PDF template overlay** | ✅ Native | ❌ | ❌ | ❌ | ❌ |
| **Tagged PDF/UA** | ✅ | ❌ | ❌ | Partial | ✅ |
| **CSS coverage** | Broad subset | WebKit full | Chromium full | Good subset | Excellent |
| **JavaScript** | None (by design) | Yes | Yes | None | Yes |
| **License** | AGPL + Commercial | LGPL | Apache-2.0 | BSD | Commercial ($3,800) |
| **Maintenance** | Active | Deprecated | Active | Active | Active |

## Fullbleed vs wkhtmltopdf

**wkhtmltopdf** was the go-to for years but is now **deprecated and unmaintained**. It uses an old Qt WebKit build with known security vulnerabilities.

**Choose Fullbleed when:**

- You need a maintained, actively developed solution
- You want deterministic output for CI/testing
- You need per-page data aggregation (running totals)
- You want a pure Python install with no system dependencies
- You need tagged PDF output for accessibility

**wkhtmltopdf still wins if:**

- You need full browser-grade CSS/JS rendering of arbitrary web pages (but consider Puppeteer instead)

## Fullbleed vs Puppeteer / Playwright

**Puppeteer/Playwright** use a real Chromium browser for rendering. They produce pixel-perfect web-to-print output but carry significant overhead.

**Choose Fullbleed when:**

- You're generating **documents** (invoices, statements, reports), not printing web pages
- You need deterministic output (Chromium rendering varies across versions)
- You don't want to manage browser binary downloads in CI/Docker
- You need parallel rendering without spawning multiple browser processes
- You need built-in headers/footers with page data, not JS injection hacks
- Container/serverless size matters (Chromium adds ~300MB)

**Puppeteer/Playwright still win if:**

- You need full web rendering (JavaScript execution, complex CSS animations, web fonts via `@import`)
- You're literally printing a web page as-is
- CSS coverage is more important than determinism

## Fullbleed vs WeasyPrint

**WeasyPrint** is the closest alternative — also a Python library that doesn't need a browser. It's well-maintained and has good CSS support.

**Choose Fullbleed when:**

- You need **speed**. Fullbleed's Rust core is significantly faster, especially for batch rendering.
- You need parallel rendering. WeasyPrint holds the GIL during rendering; Fullbleed releases it.
- You need per-page running totals, subtotals, or data aggregation
- You need PDF template composition (overlay onto existing PDFs)
- You need tagged PDF/UA output for accessibility compliance
- You need deterministic, reproducible output

**WeasyPrint still wins if:**

- You need better CSS `@page` margin-box support (Fullbleed doesn't implement `@bottom-center` etc.)
- You prefer a pure Python dependency chain
- You need `position: sticky` or multi-column layout

## Fullbleed vs Prince

**Prince** is the gold standard for CSS-to-PDF quality. It has the best CSS Paged Media support of any tool. It's also $3,800 per server.

**Choose Fullbleed when:**

- Budget matters. Fullbleed is free for open source (AGPL) and commercial licenses are far cheaper.
- You need an API-first workflow (Python bindings, batch APIs) rather than CLI-only
- You need per-page data aggregation
- You need PDF template composition
- You need AI/agent-ready JSON diagnostics

**Prince still wins if:**

- You need the absolute best CSS Paged Media spec compliance
- You need advanced CSS features like `@footnote`, named strings, cross-references
- Budget is not a concern and CSS quality is paramount

## Migration Guides

### From wkhtmltopdf

```python
# Before (wkhtmltopdf via subprocess)
import subprocess
subprocess.run(["wkhtmltopdf", "--header-right", "Page [page] of [toPage]",
                "input.html", "output.pdf"])

# After (Fullbleed)
import fullbleed
engine = fullbleed.PdfEngine(
    page_width="8.5in", page_height="11in", margin="0.75in",
    header_each="Page {page} of {pages}",
    header_x="6in", header_y_from_top="0.3in",
)
with open("input.html") as f:
    html = f.read()
engine.render_pdf_to_file(html, "", "output.pdf")
```

### From WeasyPrint

```python
# Before (WeasyPrint)
from weasyprint import HTML
HTML(string=html_string).write_pdf("output.pdf")

# After (Fullbleed)
import fullbleed
engine = fullbleed.PdfEngine(page_width="8.5in", page_height="11in", margin="0.75in")
engine.render_pdf_to_file(html_string, css_string, "output.pdf")
```

### From Puppeteer

```javascript
// Before (Puppeteer)
const browser = await puppeteer.launch();
const page = await browser.newPage();
await page.setContent(html);
await page.pdf({ path: 'output.pdf', format: 'Letter' });
await browser.close();
```

```python
# After (Fullbleed) — no browser, no Node.js
import fullbleed
engine = fullbleed.PdfEngine(page_width="8.5in", page_height="11in", margin="0.75in")
engine.render_pdf_to_file(html, css, "output.pdf")
```
