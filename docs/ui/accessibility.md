# Accessibility Components

`fullbleed.ui.accessibility` provides ARIA-aware components that emit semantic HTML with proper roles, labels, and structure. Use these when generating documents that must meet WCAG/PDF/UA requirements.

## Available Components

### Structural

| Component | HTML Output | Purpose |
|-----------|-------------|---------|
| `Region` | `<div role="...">` | Landmark regions (banner, main, contentinfo) |
| `Section` | `<section>` | Logical document sections |
| `Heading` | `<h1>`–`<h6>` | Hierarchical headings |

### Tables

| Component | HTML Output | Purpose |
|-----------|-------------|---------|
| `SemanticTable` | `<table>` with scope attrs | Accessible data table |
| `ColumnHeader` | `<th scope="col">` | Column header cell |
| `RowHeader` | `<th scope="row">` | Row header cell |
| `DataCell` | `<td>` | Data cell |

### Content

| Component | HTML Output | Purpose |
|-----------|-------------|---------|
| `Alert` | `<div role="alert">` | Important notices |
| `FieldGrid` | Labeled key-value layout | Form-like data display |
| `FieldItem` | Label + value pair | Single field in a FieldGrid |

## Usage

```python
from fullbleed.ui.accessibility import (
    Region, Section, Heading, SemanticTable,
    ColumnHeader, RowHeader, DataCell, Alert, FieldGrid, FieldItem
)

doc = Region(role="main",
    Heading("Annual Financial Report", level=1),

    Alert("This report contains unaudited figures.", severity="warning"),

    Section(
        Heading("Company Overview", level=2),
        FieldGrid(
            FieldItem("Company", "Acme Corporation"),
            FieldItem("Fiscal Year", "2025"),
            FieldItem("Report Date", "March 9, 2026"),
        ),
    ),

    Section(
        Heading("Revenue by Region", level=2),
        SemanticTable(
            ColumnHeader("Region"),
            ColumnHeader("Revenue"),
            ColumnHeader("YoY Growth"),
            RowHeader("North America"), DataCell("$4.2M"), DataCell("+15%"),
            RowHeader("Europe"), DataCell("$2.8M"), DataCell("+8%"),
            RowHeader("Asia Pacific"), DataCell("$1.9M"), DataCell("+22%"),
            caption="Q4 2025 Revenue by Region",
        ),
    ),
)
```

## Region

Landmark regions help screen readers navigate the document:

```python
Region(role="banner",     # Page header / title area
    Heading("Report Title", level=1),
)

Region(role="main",       # Primary content
    Section(...),
    Section(...),
)

Region(role="contentinfo", # Footer / metadata
    "© 2026 Acme Corporation",
)
```

## SemanticTable

The key difference from `fullbleed.ui.Table`: explicit `scope` attributes on headers, which PDF/UA requires.

```python
# Headers and data cells are positional — the table infers columns
# from the number of ColumnHeaders

table = SemanticTable(
    # First, declare column headers
    ColumnHeader("Date"),
    ColumnHeader("Description"),
    ColumnHeader("Amount"),

    # Then data rows — each RowHeader starts a new row
    RowHeader("03/01"), DataCell("Deposit"), DataCell("$1,200.00"),
    RowHeader("03/05"), DataCell("Payment"), DataCell("-$450.00"),
    RowHeader("03/12"), DataCell("Transfer"), DataCell("$300.00"),

    caption="March 2026 Transactions",
)
```

## A11yContract Validation

Validate component trees before rendering:

```python
from fullbleed.ui.accessibility import A11yContract

contract = A11yContract()
result = contract.validate(doc, mode="warn")
# mode="warn" — logs warnings, continues
# mode="raise" — raises on first violation

print(f"Valid: {result.valid}")
for issue in result.issues:
    print(f"  {issue.severity}: {issue.message}")
```

The contract checks:
- Headings are in order (no skipping levels)
- Tables have proper headers
- Images have alt text
- Regions have roles
- Required attributes are present

## Combining with Raw HTML

Components emit HTML, so you can mix them with raw HTML strings:

```python
from fullbleed.ui import Stack
from fullbleed.ui.accessibility import Section, Heading

doc = Stack(
    Section(
        Heading("Overview", level=1),
        "<p>This is raw HTML mixed with components.</p>",
        "<ul><li>Item one</li><li>Item two</li></ul>",
    ),
)

html = doc.to_html()  # or use @Document decorator
```

## Next Steps

- [Accessibility Engine →](../accessibility/engine.md) — Rendering with evidence bundles
- [Coverage Report →](../accessibility/coverage.md) — WCAG/508 coverage details
- [Component Overview →](overview.md) — Non-accessibility components
