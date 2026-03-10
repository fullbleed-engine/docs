# Page Margins

Fullbleed supports both uniform margins and per-page margin control. This is essential for documents where the first page has a different layout (cover pages, letterheads, forms with different header areas).

## Uniform Margins

The `margin` parameter sets the same margin on all sides of every page:

```python
from fullbleed import PdfEngine

engine = PdfEngine(
    margin="0.85in",  # Single value only — not shorthand
)
```

!!! warning "Single value only"
    The `margin` parameter accepts a **single length value** (e.g., `"0.85in"`, `"2cm"`, `"72pt"`). CSS-style shorthand like `"0.75in 1in"` is **not supported**. Use `page_margins` for per-side control.

## Per-Page Margins

The `page_margins` dict lets you set different margins for specific pages:

```python
engine = PdfEngine(
    margin="0.85in",  # Default for all pages
    page_margins={
        1: {                    # First page — extra top for letterhead
            "top": "2in",
            "right": "0.85in",
            "bottom": "0.85in",
            "left": "0.85in",
        },
        "n": {                  # Last page — extra bottom for signature block
            "bottom": "3in",
        },
    },
)
```

### Keys

| Key | Meaning |
|-----|---------|
| `1`, `2`, `3`, ... | Specific page number |
| `"n"` | Last page (whatever page ends up being last) |

### Margin Sides

Each page entry is a dict with these optional keys:

| Key | Description |
|-----|-------------|
| `"top"` | Top margin |
| `"right"` | Right margin |
| `"bottom"` | Bottom margin |
| `"left"` | Left margin |

Any side not specified falls back to the global `margin` value.

## Common Patterns

### Cover Page + Body

```python
engine = PdfEngine(
    margin="0.85in",
    page_margins={
        1: {"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"},
        # Pages 2+ use the default 0.85in
    },
)
```

### Letterhead First Page

```python
engine = PdfEngine(
    margin="0.75in",
    page_margins={
        1: {"top": "2.5in"},  # Clear the logo/address block
    },
)
```

### Binding Margin (Left-Heavy)

```python
engine = PdfEngine(
    margin="0.75in",
    page_margins={
        # All pages get extra left margin for binding
        # (You'd need to set this per-page or use the global margin)
    },
)
```

## Supported Length Units

All margin values accept standard CSS length units:

| Unit | Example | Description |
|------|---------|-------------|
| `in` | `"0.85in"` | Inches |
| `cm` | `"2.54cm"` | Centimeters |
| `mm` | `"25.4mm"` | Millimeters |
| `pt` | `"72pt"` | Points (1/72 inch) |
| `px` | `"96px"` | Pixels (at 96 DPI) |

## Next Steps

- [Headers & Footers →](headers-footers.md) — Content within margin areas
- [Template Composition →](template-composition.md) — Overlay onto existing PDFs
- [PdfEngine API →](pdf-engine.md) — Full constructor reference
