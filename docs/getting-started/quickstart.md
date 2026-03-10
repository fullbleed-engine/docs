# Quick Start

Generate your first PDF in under a minute.

## Option 1: CLI Scaffold

The fastest way to see Fullbleed in action:

```bash
mkdir my-first-fullbleed
cd my-first-fullbleed
fullbleed init .
python report.py
```

This creates a scaffold project with a sample `report.py` and outputs `output/report.pdf`.

## Option 2: Python Script

Create a file called `hello.py`:

```python
import fullbleed

engine = fullbleed.PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.75in",
)

html = """
<h1>Invoice #1042</h1>
<p>Date: March 9, 2026</p>

<table>
  <thead>
    <tr>
      <th>Item</th>
      <th>Qty</th>
      <th>Price</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>Widget A</td><td>10</td><td>$25.00</td></tr>
    <tr><td>Widget B</td><td>5</td><td>$42.00</td></tr>
    <tr><td>Consulting</td><td>8 hrs</td><td>$150.00</td></tr>
  </tbody>
</table>

<p><strong>Total: $1,660.00</strong></p>
"""

css = """
body { font-family: Helvetica, sans-serif; color: #1a202c; }
h1 { color: #2d3748; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
table { width: 100%; border-collapse: collapse; margin-top: 20px; }
th { background: #edf2f7; text-align: left; padding: 8px; border-bottom: 2px solid #cbd5e0; }
td { padding: 8px; border-bottom: 1px solid #e2e8f0; }
"""

pdf_bytes = engine.render_pdf(html, css)

with open("invoice.pdf", "wb") as f:
    f.write(pdf_bytes)

print(f"Generated invoice.pdf ({len(pdf_bytes):,} bytes)")
```

Run it:

```bash
python hello.py
```

Open `invoice.pdf` — you've just generated a PDF with zero browser dependencies.

## Option 3: CLI Render

If you have separate HTML and CSS files:

```bash
fullbleed render --html invoice.html --css style.css --out invoice.pdf
```

## What's Different?

If you've used wkhtmltopdf, Puppeteer, or WeasyPrint before, here's what you'll notice:

1. **No browser process.** Fullbleed renders natively — there's no Chromium download, no headless browser startup time.
2. **Deterministic output.** Run it twice with the same input, get the same bytes. Every time.
3. **Page-aware features.** Headers, footers, per-page running totals, and page margins are built into the engine, not CSS hacks.

## Next Steps

- [Your First PDF (detailed walkthrough) →](first-pdf.md)
- [PdfEngine API →](../engine/pdf-engine.md)
- [Headers & Footers →](../engine/headers-footers.md)
- [Comparison with other tools →](../guides/comparison.md)
