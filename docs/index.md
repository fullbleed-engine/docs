# Fullbleed

**Deterministic, dependency-free HTML/CSS-to-PDF generation in Rust, with Python-first bindings.**

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } **Get Started in 5 Minutes**

    ---

    Install Fullbleed and generate your first PDF with three commands.

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

- :material-code-braces:{ .lg .middle } **Python API**

    ---

    Full control over page geometry, headers, footers, pagination, and rendering.

    [:octicons-arrow-right-24: PdfEngine API](engine/pdf-engine.md)

- :material-file-document-check:{ .lg .middle } **Accessibility**

    ---

    Built-in tagged PDF/UA output, WCAG 2.0 AA coverage, and evidence bundles.

    [:octicons-arrow-right-24: Accessibility](accessibility/overview.md)

- :material-robot:{ .lg .middle } **Agent-Ready**

    ---

    JSON schemas, structured diagnostics, and image previews designed for AI agent workflows.

    [:octicons-arrow-right-24: AI Agent Guide](guides/ai-agents.md)

</div>

## What is Fullbleed?

Fullbleed is an HTML/CSS-to-PDF rendering engine built from scratch in Rust. It uses HTML and CSS as a familiar design language for document layout — but there's **no browser under the hood**. No Chrome, no WebKit, no Puppeteer, no headless anything.

```bash
pip install fullbleed
```

```python
import fullbleed

engine = fullbleed.PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.75in",
)

pdf_bytes = engine.render_pdf(
    html='<h1>Hello, Fullbleed</h1><p>Your first PDF.</p>',
    css='h1 { color: #2d3748; font-family: Inter; }',
)

with open("output.pdf", "wb") as f:
    f.write(pdf_bytes)
```

## Why Fullbleed?

| Feature | Fullbleed | wkhtmltopdf | Puppeteer/Playwright | WeasyPrint | Prince |
|---------|-----------|-------------|---------------------|------------|--------|
| No browser dependency | ✅ | ❌ Qt WebKit | ❌ Chromium | ✅ | ✅ |
| Deterministic output | ✅ SHA256 verified | ❌ | ❌ | ❌ | ❌ |
| Native Rust performance | ✅ | ❌ | ❌ | ❌ (Python) | ❌ (C++) |
| Python GIL release | ✅ | N/A | N/A | ❌ | N/A |
| Parallel batch rendering | ✅ Rayon | ❌ | Manual | ❌ | ❌ |
| Tagged PDF/UA | ✅ | ❌ | ❌ | Partial | ✅ |
| PDF template composition | ✅ Native | ❌ | ❌ | ❌ | ❌ |
| Headers/footers w/ page data | ✅ Built-in | Basic | JS injection | CSS @page | CSS @page |
| Per-page running totals | ✅ | ❌ | ❌ | ❌ | ❌ |
| AI/agent-safe JSON output | ✅ | ❌ | ❌ | ❌ | ❌ |
| Free / OSS | ✅ AGPL | ✅ | ✅ | ✅ | ❌ $3,800 |

## Key Features

- **No system dependencies.** `pip install fullbleed` and you're done. No browser binaries, no system font packages, no Docker workarounds.
- **Deterministic rendering.** Same input = same output, byte-for-byte. Verify with `--repro-record` / `--repro-check`.
- **Built for documents, not web pages.** Page geometry, margins, headers/footers, paginated context (running totals, subtotals per page), watermarks — all first-class.
- **PDF template composition.** Overlay rendered content onto existing PDF templates without a separate composition library.
- **Parallel batch rendering.** Rayon-backed concurrency. Python GIL released on every render call.
- **Accessibility built in.** Tagged PDF output, WCAG 2.0 AA coverage, Section 508 support, evidence bundles.
- **Agent-ready.** Structured JSON diagnostics, image preview rendering, schema output for CI and AI agents.

## License

Fullbleed is dual-licensed:

- **AGPL-3.0** for open source use
- **Commercial license** available for proprietary/closed-source production

[Contact us](https://fullbleed.dev/contact) for commercial licensing.
