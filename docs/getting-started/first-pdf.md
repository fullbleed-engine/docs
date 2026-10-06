# Add fonts and a PDF preview

Use the font bundled in the installed wheel to make font selection explicit. This example writes a PDF and renders a preview from that finalized file.

```python
from importlib.resources import files
from pathlib import Path
import fullbleed

font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
engine = fullbleed.PdfEngine(
    font_files=[str(font)],
    document_title="Service invoice",
    document_lang="en-US",
)
html = "<main><h1>Service invoice</h1><p>INV-1042 · USD 1,200.00</p></main>"
css = """
@page { size: A4; margin: 20mm; }
body { font-family: Inter; font-size: 11pt; color: #203a36; }
h1 { font-size: 28pt; color: #175c52; }
"""
Path("output").mkdir(exist_ok=True)
engine.render_pdf_to_file(html, css, "output/invoice.pdf")
engine.render_finalized_pdf_image_pages_to_dir(
    "output/invoice.pdf", "output/preview", 120, "invoice"
)
print(fullbleed.inspect_pdf("output/invoice.pdf"))
```

Open `output/invoice.pdf` and the images under `output/preview`. Inspect every page when you change the layout, particularly table breaks, long text, and fonts containing non-ASCII characters.

For Simplified Chinese, use the [Chinese-font invoice recipe](../guides/chinese-pdf.md).
It registers Noto Sans SC explicitly and includes a missing-character check.

## Repeatable output

Keep the engine version, HTML/CSS, fonts, images, and explicit metadata fixed. Compare output bytes or SHA-256 hashes in your own workflow. The CLI's `--repro-record` and `--repro-check` options support retained reproducibility records. Use **Fullbleed 2.5.3 or newer** for this gate; earlier versions could accept a record with missing hashes. Follow the [PDF regression starter](../guides/pdf-regression-ci.md) or consult [the render reference](../cli/commands.md#reproducibility-checks).

## Structured data

Escape text inserted into HTML with Python's `html.escape`. Keep numeric calculations in your application; the [invoice example](../guides/invoices.md) shows data separated from layout.

[Fonts and assets](../engine/assets.md) · [Python API](../engine/pdf-engine.md)
