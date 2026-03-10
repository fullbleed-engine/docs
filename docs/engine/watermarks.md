# Watermarks

Fullbleed supports text watermarks rendered on every page. Useful for draft stamps, confidentiality notices, and document status indicators.

## Text Watermarks

```python
from fullbleed import PdfEngine

engine = PdfEngine(
    margin="0.85in",
    watermark_text="DRAFT",
    watermark_font_size=72,
    watermark_color="#cccccc",
    watermark_opacity=0.3,
    watermark_angle=45,
)

pdf_bytes = engine.render(html)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `watermark_text` | `str` | `None` | Text to render as watermark |
| `watermark_font_name` | `str` | `"Helvetica"` | Font for watermark text |
| `watermark_font_size` | `int` | `48` | Font size in points |
| `watermark_color` | `str` | `"#999999"` | Color (hex) |
| `watermark_opacity` | `float` | `0.5` | Opacity (0.0–1.0) |
| `watermark_angle` | `int` | `45` | Rotation angle in degrees |

### Common Patterns

```python
# Confidential stamp
engine = PdfEngine(
    watermark_text="CONFIDENTIAL",
    watermark_font_size=60,
    watermark_color="#ff0000",
    watermark_opacity=0.15,
    watermark_angle=45,
)

# Approved stamp
engine = PdfEngine(
    watermark_text="APPROVED",
    watermark_font_size=80,
    watermark_color="#00aa00",
    watermark_opacity=0.2,
    watermark_angle=-30,
)

# Sample / Preview
engine = PdfEngine(
    watermark_text="SAMPLE — NOT FOR DISTRIBUTION",
    watermark_font_size=36,
    watermark_color="#666666",
    watermark_opacity=0.25,
    watermark_angle=45,
)
```

## Watermarks with Paginated Context

Watermark text supports the same placeholder tokens as headers and footers:

```python
engine = PdfEngine(
    watermark_text="Page {page} of {pages}",
    watermark_font_size=24,
    watermark_opacity=0.1,
)
```

## With Accessibility Engine

Watermarks pass through to `AccessibilityEngine` as `**engine_kwargs`:

```python
from fullbleed import AccessibilityEngine

engine = AccessibilityEngine(
    strict=False,
    document_title="Draft Report",
    document_lang="en",
    watermark_text="DRAFT",
    watermark_opacity=0.2,
)

results = engine.render_bundle(html)
```

!!! note
    Watermarks are decorative/presentational and should not convey essential information. The engine treats them as artifacts in the tag structure, meaning screen readers will skip them — which is the correct behavior for accessibility.

## Next Steps

- [Template Composition →](template-composition.md) — Overlay onto existing PDFs
- [Page Margins →](page-margins.md) — Per-page margin control
- [Headers & Footers →](headers-footers.md) — Page-aware headers and footers
