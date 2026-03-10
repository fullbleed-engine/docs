# Your First PDF

A step-by-step walkthrough of Fullbleed's core concepts.

## The Render Pipeline

Every Fullbleed render follows the same pipeline:

```
HTML + CSS → Parse → Compute Styles → Layout → Paginate → PDF
```

There are no network requests, no JavaScript execution, and no DOM. Fullbleed parses HTML/CSS as a document description language and renders directly to PDF.

## Creating an Engine

The `PdfEngine` is the central object. It holds your page configuration and rendering settings:

```python
import fullbleed

engine = fullbleed.PdfEngine(
    page_width="8.5in",    # US Letter width
    page_height="11in",    # US Letter height
    margin="0.75in",       # Single value applied to all sides
)
```

!!! warning "Margin takes a single value"
    The `margin` parameter accepts a **single value only** (e.g., `"0.75in"`), not CSS shorthand like `"0.75in 1in"`. For per-side or per-page margins, use the `page_margins` parameter.

### Common Page Sizes

| Size | Width | Height |
|------|-------|--------|
| US Letter | `"8.5in"` | `"11in"` |
| A4 | `"210mm"` | `"297mm"` |
| Legal | `"8.5in"` | `"14in"` |
| Tabloid | `"11in"` | `"17in"` |

## Rendering

### To bytes

```python
pdf_bytes = engine.render_pdf(html, css)
```

### To file

```python
page_count = engine.render_pdf_to_file(html, css, "output.pdf")
print(f"Rendered {page_count} pages")
```

### To images (preview)

```python
# Returns list of PNG bytes, one per page
pages = engine.render_image_pages(html, css, dpi=150)

for i, page_bytes in enumerate(pages):
    with open(f"page_{i+1}.png", "wb") as f:
        f.write(page_bytes)
```

## Using CSS

Fullbleed supports a broad subset of CSS for document layout. Use it like you would for a web page, with a few document-specific considerations:

```css
/* Standard CSS works as expected */
body {
    font-family: Inter, Helvetica, sans-serif;
    font-size: 10pt;
    color: #1a202c;
    line-height: 1.5;
}

h1 {
    font-size: 18pt;
    color: #2d3748;
    margin-bottom: 12pt;
}

/* Flexbox and Grid work */
.row {
    display: flex;
    justify-content: space-between;
}

/* Page breaks */
.page-break {
    page-break-before: always;
}

/* Tables with header repeat across pages */
thead { display: table-header-group; }
```

!!! tip "Page breaks"
    Use `page-break-before: always` on a div for explicit page breaks. Note that `break-inside: avoid` may not always be respected — explicit breaks are more reliable.

## Custom Fonts

```python
engine = fullbleed.PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.75in",
    font_dirs=["./fonts"],                    # Directories to scan
    font_files=["./fonts/CustomFont.ttf"],    # Specific files
)
```

Then reference them in CSS:

```css
body { font-family: "CustomFont", sans-serif; }
```

## Deterministic Output

Fullbleed's renders are deterministic — same input always produces the same output bytes. You can verify this:

```bash
# Record a reference render
fullbleed render --html doc.html --css style.css --out ref.pdf --repro-record ref.repro

# Later, verify nothing changed
fullbleed render --html doc.html --css style.css --out check.pdf --repro-check ref.repro
```

This is invaluable for CI pipelines, regression testing, and audit trails.

## Next Steps

- [PdfEngine API (full reference) →](../engine/pdf-engine.md)
- [Headers & Footers →](../engine/headers-footers.md)
- [Paginated Context (running totals) →](../engine/paginated-context.md)
