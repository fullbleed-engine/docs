# Accessibility Overview

Fullbleed treats accessibility as a first-class engineering constraint, not an afterthought. The engine produces tagged PDF/UA output with built-in verification, scoring, and evidence bundles.

## Why This Matters

The ADA Title II deadline (April 24, 2026) requires state and local government web content — including PDFs — to meet WCAG 2.0 AA. Most organizations are scrambling to remediate existing PDFs. Fullbleed takes a different approach: **author accessible documents correctly from the start.**

## The Fullbleed Accessibility Stack

```
┌──────────────────────────────────────────────────┐
│              UI Component System                  │
│  SemanticTable · Region · FieldGrid · Alert       │
│  (Accessibility by construction)                  │
├──────────────────────────────────────────────────┤
│            A11y Contract Validation               │
│  Validate component tree BEFORE rendering         │
│  (Catch issues early, not in PDF output)          │
├──────────────────────────────────────────────────┤
│           AccessibilityEngine                     │
│  Wraps PdfEngine with PDF/UA-targeted output      │
│  Tagged structure, reading order, metadata        │
├──────────────────────────────────────────────────┤
│              Evidence Bundles                      │
│  PMR scores · Verifier reports · Reading order    │
│  Structure traces · PDF/UA checks · Previews      │
│  (15+ artifacts per render)                       │
└──────────────────────────────────────────────────┘
```

## Three Levels of Accessibility

### Level 1: Semantic HTML → Tagged PDF

Write clean, semantic HTML and Fullbleed handles the rest:

```html
<main role="main" aria-label="Report">
  <h1>Annual Report</h1>
  <section role="region" aria-label="Revenue">
    <h2>Revenue</h2>
    <table>
      <caption>Revenue by quarter</caption>
      <thead>
        <tr><th scope="col">Quarter</th><th scope="col">Amount</th></tr>
      </thead>
      <tbody>
        <tr><th scope="row">Q1</th><td>$1.2M</td></tr>
      </tbody>
    </table>
  </section>
</main>
```

This produces a tagged PDF with:
- Document structure tags (H1, H2, Table, TH, TD, etc.)
- Reading order that matches visual order
- Language metadata
- Document title

### Level 2: UI Components (Accessibility by Construction)

Use Fullbleed's component system to make inaccessible output structurally impossible:

```python
from fullbleed.ui import *
from fullbleed.ui.accessibility import *

# These components ALWAYS emit correct ARIA and semantic HTML
SemanticTable(
    caption="Revenue by quarter",
    head=SemanticTableHead(
        SemanticTableRow(ColumnHeader("Quarter"), ColumnHeader("Amount"))
    ),
    body=SemanticTableBody(
        SemanticTableRow(RowHeader("Q1"), DataCell("$1.2M"))
    ),
)
```

Available accessibility components:
- `Region`, `Section`, `Main`, `Nav`, `Aside` — landmark regions
- `Heading` — properly leveled headings
- `SemanticTable`, `SemanticTableHead/Body/Foot/Row`, `ColumnHeader`, `RowHeader`, `DataCell` — fully accessible tables
- `Alert`, `Status`, `LiveRegion` — dynamic content roles
- `FieldGrid`, `FieldItem`, `FieldSet`, `Legend` — form-like data display
- `Figure`, `FigCaption` — captioned images
- `DefinitionList`, `DefinitionTerm`, `DefinitionDescription` — definition lists
- `ScreenReaderText`, `Decorative` — screen reader hints

### Level 3: Evidence Bundles (Prove Compliance)

The `AccessibilityEngine.render_bundle()` produces verifiable evidence:

```python
from fullbleed.accessibility import AccessibilityEngine

engine = AccessibilityEngine(
    page_size="letter",
    document_lang="en",
    document_title="Annual Report 2025",
    margin="0.75in",
)

result = engine.render_bundle(
    body_html=html,
    css_text=css,
    out_dir="./output",
    stem="annual-report",
    run_verifier=True,
    run_pmr=True,
    render_preview_png=True,
    emit_reading_order_trace=True,
    emit_pdf_structure_trace=True,
)

# result.ok == True
# result.pmr_report["score"]["score"] == 100.0
# result.pdf_ua_seed_report["ok"] == True (14/14 checks pass)
# result.verifier_report["gate"]["error_count"] == 0
```

This isn't just a PDF — it's a PDF with a complete evidence trail that proves it meets accessibility standards. Every artifact is JSON, machine-parseable, and auditable.

## Coverage

| Standard | Coverage |
|----------|----------|
| WCAG 2.0 AA | 100% of applicable success criteria |
| Section 508 E205 | 100% |
| PDF/UA-1 (ISO 14289-1) | Targeted (seed verification) |

See [WCAG & Section 508 Coverage →](coverage.md) for detailed per-criterion mapping.

## Key Concepts

- **PMR Score**: Pagination/Markup/Readability quality score (0-100) with confidence bands. Quantifies how well a document meets accessibility standards.
- **Evidence Bundle**: The collection of artifacts produced by `render_bundle()` — verifier reports, PMR scores, traces, previews.
- **CAV Profile**: Compliant Alternative Version — the default accessibility profile that targets full WCAG 2.0 AA + Section 508 compliance.
- **Reading Order Trace**: A record of every text block in the order a screen reader would encounter it, cross-checked between render-time and PDF extraction.
- **Cross-Checking**: Fullbleed verifies its own output from two independent paths. If the render-time reading order doesn't match the lopdf-extracted reading order, a warning is raised.

## Next Steps

- [AccessibilityEngine API →](engine.md)
- [Evidence Bundles →](evidence-bundles.md)
- [WCAG & Section 508 Coverage →](coverage.md)
