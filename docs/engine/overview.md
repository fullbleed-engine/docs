# Engine Overview

Fullbleed's rendering engine is written in Rust and exposed to Python via PyO3 bindings. The engine handles:

- HTML parsing and CSS resolution
- Computed style generation
- Flowable layout and frame placement
- Page creation and content splitting
- Header/footer injection with page data
- PDF serialization (1.7 or 2.0)
- Optional tagged PDF/UA output

## Architecture

```
┌─────────────────────────────────────────────┐
│                 Python API                   │
│  PdfEngine · AssetBundle · AccessibilityEngine│
├─────────────────────────────────────────────┤
│              PyO3 Bindings                   │
│         (GIL released during render)         │
├─────────────────────────────────────────────┤
│               Rust Core                      │
│  HTML Parser → CSS Resolver → Layout Engine  │
│  → Page Template → PDF Serializer            │
│         (Rayon parallel batch)               │
└─────────────────────────────────────────────┘
```

## Key Design Decisions

### No Browser

Fullbleed does not embed or shell out to any browser engine. It implements its own HTML/CSS parser and layout engine purpose-built for paginated document output. This means:

- No Chromium/WebKit binary downloads
- No startup overhead for browser processes
- No non-determinism from browser version differences
- No JavaScript execution (by design — documents are data + template, not interactive)

### GIL Release

Every Python render call releases the Python GIL while Rust executes. This means you can render PDFs in Python threads without blocking other threads:

```python
from concurrent.futures import ThreadPoolExecutor
import fullbleed

engine = fullbleed.PdfEngine(page_width="8.5in", page_height="11in", margin="0.75in")

def render_one(data):
    html = f"<h1>Invoice #{data['id']}</h1>"
    return engine.render_pdf(html, "")

with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(render_one, invoices))
```

### Deterministic by Default

Same HTML + CSS + engine config = same PDF bytes. Always. This is enforced at the engine level, not as an afterthought. Use `--repro-record` / `--repro-check` to verify in CI.

## Core Objects

| Object | Purpose |
|--------|---------|
| [`PdfEngine`](pdf-engine.md) | Main rendering engine — configure pages, margins, headers, footers, render to PDF/images |
| [`AssetBundle`](assets.md) | Register fonts, images, CSS, and PDF templates |
| [`AccessibilityEngine`](../accessibility/engine.md) | Wraps PdfEngine with accessibility defaults and evidence bundle output |
| [`WatermarkSpec`](watermarks.md) | Configure text, HTML, or image watermarks |
