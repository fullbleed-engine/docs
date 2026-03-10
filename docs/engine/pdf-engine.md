# PdfEngine API

The `PdfEngine` is the primary interface for rendering HTML/CSS to PDF.

## Constructor

```python
import fullbleed

engine = fullbleed.PdfEngine(
    # Page geometry
    page_width="8.5in",
    page_height="11in",
    margin="0.75in",

    # Optional: per-page margin overrides
    page_margins={
        1: {"top": "0.5in", "right": "0.75in", "bottom": "0.75in", "left": "0.75in"},
        "n": {"top": "1in", "right": "0.75in", "bottom": "0.75in", "left": "0.75in"},
    },

    # Fonts
    font_dirs=["./fonts"],
    font_files=["./fonts/Inter-Regular.ttf"],

    # PDF output
    pdf_version="1.7",          # "1.7" or "2.0"
    pdf_profile="none",         # "none", "pdfa2b", "pdfx4", "tagged"
    color_space="rgb",          # "rgb" or "cmyk"

    # Rendering
    reuse_xobjects=True,        # Deduplicate repeated images
    unicode_support=True,
    shape_text=True,

    # Document metadata
    document_title="My Document",
    document_lang="en",
)
```

## Page Geometry Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page_width` | `str` | Page width as length string (e.g., `"8.5in"`, `"210mm"`) |
| `page_height` | `str` | Page height as length string |
| `margin` | `str \| int` | **Single value** margin applied to all sides. Does not accept shorthand. |
| `page_margins` | `dict` | Per-page margin overrides. Keys: page number (int) or `"n"` for default. Values: dict with `top`, `right`, `bottom`, `left`. |

!!! warning "Margin is a single value"
    `margin="0.75in"` ✅  
    `margin="0.75in 1in"` ❌ — shorthand is not supported.  
    Use `page_margins` for per-side control.

## Render Methods

### `render_pdf(html, css, deterministic_hash=None) → bytes`

Renders HTML/CSS to PDF bytes.

```python
pdf_bytes = engine.render_pdf(html_string, css_string)

with open("output.pdf", "wb") as f:
    f.write(pdf_bytes)
```

### `render_pdf_to_file(html, css, path, deterministic_hash=None) → int`

Renders directly to a file. Returns page count.

```python
pages = engine.render_pdf_to_file(html, css, "output.pdf")
print(f"Rendered {pages} pages")
```

### `render_pdf_with_page_data(html, css) → (bytes, dict | None)`

Renders PDF and returns paginated context data (running totals, counts, etc.).

```python
pdf_bytes, page_data = engine.render_pdf_with_page_data(html, css)
# page_data contains per-page aggregated values from paginated_context
```

### `render_image_pages(html, css, dpi=150) → list[bytes]`

Renders each page as a PNG image. Useful for previews and AI agent workflows.

```python
pages = engine.render_image_pages(html, css, dpi=150)
for i, png_bytes in enumerate(pages):
    with open(f"page_{i+1}.png", "wb") as f:
        f.write(png_bytes)
```

### `render_image_pages_to_dir(html, css, out_dir, dpi=150, stem=None) → list[str]`

Renders page images directly to a directory. Returns file paths.

```python
paths = engine.render_image_pages_to_dir(html, css, "./previews", dpi=200, stem="invoice")
# paths = ["./previews/invoice_1.png", "./previews/invoice_2.png", ...]
```

## Batch Rendering

For high-volume rendering, use the parallel batch methods:

### `render_pdf_batch_parallel(...)`

Renders multiple documents in parallel using Rayon threads:

```python
results = engine.render_pdf_batch_parallel(
    items=[
        {"html": html1, "css": css1},
        {"html": html2, "css": css2},
        # ...
    ]
)
# results = [bytes, bytes, ...]
```

### `render_pdf_batch_to_file_parallel(...)`

Same as above but writes directly to files.

## PDF Output Options

| Parameter | Default | Description |
|-----------|---------|-------------|
| `pdf_version` | `"1.7"` | PDF version. `"2.0"` enables newer features. |
| `pdf_profile` | `"none"` | Output profile: `"none"`, `"pdfa2b"`, `"pdfx4"`, `"tagged"` |
| `color_space` | `"rgb"` | Color space: `"rgb"` or `"cmyk"` |
| `reuse_xobjects` | `False` | Deduplicate repeated images across pages |

## Font Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `font_dirs` | `list[str]` | Directories to scan for font files |
| `font_files` | `list[str]` | Specific font file paths to register |
| `unicode_support` | `bool` | Enable Unicode text support |
| `shape_text` | `bool` | Enable text shaping (for complex scripts) |
| `unicode_metrics` | `bool` | Use Unicode metrics for text measurement |

## Rendering Options

| Parameter | Type | Description |
|-----------|------|-------------|
| `svg_form_xobjects` | `bool` | Render SVGs as PDF form XObjects |
| `svg_raster_fallback` | `bool` | Rasterize SVGs that can't be vectorized |
| `jit_mode` | `bool` | Enable JIT compiler diagnostics |
| `debug` | `bool` | Enable debug output |
| `debug_out` | `str` | Debug output file path |
| `perf` | `bool` | Enable performance profiling |
| `perf_out` | `str` | Performance output file path |
| `layout_strategy` | `str` | Layout strategy selection |

## Deterministic Hash

Pass a `deterministic_hash` to any render method to get byte-identical output:

```python
pdf1 = engine.render_pdf(html, css, deterministic_hash="abc123")
pdf2 = engine.render_pdf(html, css, deterministic_hash="abc123")
assert pdf1 == pdf2  # Always true
```

## See Also

- [Headers & Footers →](headers-footers.md)
- [Paginated Context →](paginated-context.md)
- [Page Margins →](page-margins.md)
- [Watermarks →](watermarks.md)
- [Asset Bundles →](assets.md)
