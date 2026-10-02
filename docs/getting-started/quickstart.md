---
description: Copy a small Python script to create your first PDF, then try a complete Fullbleed project with bundled fonts and previews.
---
# Create your first PDF

Prefer to try it before setting up Python? [Open the browser playground](../playground.md)
to edit HTML/CSS and download a PDF or runnable project. Use the
[invoice notebook](notebook.md) to work with Python data in Colab.

Install Fullbleed into your Python environment:

```bash
python -m pip install fullbleed
```

Save this as `hello.py`:

```python
from pathlib import Path
import fullbleed

html = "<h1>Invoice INV-1042</h1><p>Consulting: USD 1,200.00</p>"
css = "@page { size: A4; margin: 20mm; } h1 { color: #175c52; }"
pdf = fullbleed.PdfEngine().render_pdf(html, css)
Path("invoice.pdf").write_bytes(pdf)
```

Run it and open the resulting file:

```bash
python hello.py
python -m fullbleed inspect pdf invoice.pdf --json
```

The [font and preview walkthrough](first-pdf.md) shows how to embed the bundled Inter font and preview the finalized PDF.

## Start with a complete project

For a component-based report with vendored assets and verification output, run these commands in a new directory:

```bash
mkdir my-report
cd my-report
python -m fullbleed init .
python report.py
```

Open `output/report.pdf`. The project includes Python components, CSS, bundled Inter, Bootstrap assets, a PNG preview, and structured diagnostics. Read its `SCAFFOLDING.md` before reorganizing the project.

For a task-specific starter:

```bash
python -m fullbleed new local invoice my-invoice
python -m fullbleed new local accessible my-accessible-document
```

## Bring your own HTML and CSS

```bash
python -m fullbleed render --html invoice.html --css invoice.css --out invoice.pdf
```

Use explicit local assets. See [supported CSS and known gaps](../css-coverage.md) when adapting an existing template.

[Examples and generated PDFs](../examples.md) · [Web framework examples](../guides/web-frameworks.md) · [Python API](../engine/pdf-engine.md) · [CLI reference](../cli/commands.md)
