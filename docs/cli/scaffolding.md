# Scaffolding

`fullbleed init` generates a complete project structure with example components, styles, vendored assets, and a render script. It's the fastest way to go from zero to rendered PDF.

## Usage

```bash
fullbleed init my-project
cd my-project
```

## Generated Structure

```
my-project/
├── components/
│   ├── __init__.py
│   ├── report.py          # Example document component
│   └── header.py          # Example header component
├── styles/
│   └── report.css         # Example stylesheet
├── vendor/
│   ├── bootstrap.min.css  # Bootstrap CSS framework
│   ├── noto-sans/         # Noto Sans font family
│   └── bootstrap-icons/   # Bootstrap Icons web font
├── output/                # Rendered PDFs land here
├── fullbleed.yaml         # Project configuration
└── render.py              # Entry point
```

## The Render Script

The generated `render.py` shows the recommended pattern:

```python
from fullbleed import PdfEngine
# or: from fullbleed import AccessibilityEngine

# Import your components
from components.report import build_report

# Build HTML from components
html = build_report(data={
    "title": "Quarterly Report",
    "period": "Q4 2025",
})

# Render
engine = PdfEngine(
    margin="0.85in",
    document_title="Quarterly Report",
    footer_each="Page {page} of {pages}",
    pdf_profile="tagged",
)

pdf_bytes = engine.render(html)

with open("output/report.pdf", "wb") as f:
    f.write(pdf_bytes)
    print(f"Wrote {len(pdf_bytes):,} bytes to output/report.pdf")
```

## Running It

```bash
python render.py
# → Wrote 880,891 bytes to output/report.pdf
```

## The Component System

Scaffolded projects use Fullbleed's UI component system (`fullbleed.ui`), which provides a React-like model for building document structures:

```python
from fullbleed.ui import Stack, Row, Card, Table
from fullbleed.ui.accessibility import (
    Region, Section, SemanticTable, ColumnHeader,
    RowHeader, DataCell, Heading
)

# Components are nested, not called
doc = Stack(
    Region(role="banner",
        Heading("Annual Report", level=1),
    ),
    Section(
        Heading("Revenue", level=2),
        SemanticTable(
            ColumnHeader("Region"), ColumnHeader("Revenue"),
            RowHeader("North America"), DataCell("$4.2M"),
            RowHeader("Europe"), DataCell("$2.8M"),
        ),
    ),
)
```

!!! note
    You don't have to use the component system. Raw semantic HTML works just as well — and is often simpler for straightforward documents. The component system shines when you need reusable, composable document building blocks across many templates.

## Customizing the Scaffold

After `fullbleed init`, the project is yours. Common modifications:

1. **Add your own CSS** in `styles/`
2. **Add custom fonts** in `vendor/` and reference them in CSS
3. **Create new components** in `components/`
4. **Modify `fullbleed.yaml`** for project-wide settings

## Next Steps

- [CLI Commands →](commands.md) — Full CLI reference
- [Your First PDF →](../getting-started/first-pdf.md) — Step-by-step tutorial
- [UI Components →](../ui/overview.md) — The component system in depth
