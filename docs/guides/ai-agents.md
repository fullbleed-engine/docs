# AI Agent Integration

Fullbleed was designed for deterministic, observable document rendering — which accidentally makes it the ideal PDF engine for AI agents.

## Why Agents Love Fullbleed

Most PDF tools are black boxes: HTML in, PDF out, good luck debugging. Fullbleed produces **15+ machine-readable artifacts per render**, giving agents the structured feedback they need to iterate autonomously.

| What agents need | What Fullbleed provides |
|---|---|
| Visual feedback | Preview PNGs per page at configurable DPI |
| Structured errors | JSON diagnostic reports (glyph misses, CSS selector misses, layout warnings) |
| Accessibility validation | PMR scores, PDF/UA verification, reading order traces |
| Determinism | Same input = same output, every time (SHA256 verified) |
| Machine-parseable everything | `--json-only`, `--schema` flags; all reports in JSON |
| Fast iteration | No browser startup, no Chromium binary, sub-second renders |

## Quick Start for Agents

```python
import fullbleed
from fullbleed.accessibility import AccessibilityEngine

# Create an accessibility-aware engine
engine = AccessibilityEngine(
    page_size="letter",
    document_lang="en",
    document_title="Sales Report Q4 2025",
    footer_each="Page {page} of {pages} | Confidential",
    footer_x="0.75in",
    footer_y_from_bottom="0.3in",
    footer_font_size=8.0,
    footer_color="#888888",
    margin="0.75in",
)

# Agent generates semantic HTML from data
html = """
<main role="main" aria-label="Sales Report">
  <h1>Q4 2025 Sales Report</h1>
  <section role="region" aria-label="Summary">
    <h2>Summary</h2>
    <p>Revenue exceeded targets by 12%.</p>
  </section>
  <section role="region" aria-label="Revenue">
    <h2>Revenue by Segment</h2>
    <table>
      <caption>Q3 vs Q4 revenue comparison</caption>
      <thead>
        <tr>
          <th scope="col">Segment</th>
          <th scope="col">Q3</th>
          <th scope="col">Q4</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Enterprise</th>
          <td>$1.2M</td>
          <td>$1.45M</td>
        </tr>
        <tr>
          <th scope="row">SMB</th>
          <td>$680K</td>
          <td>$720K</td>
        </tr>
      </tbody>
    </table>
  </section>
</main>
"""

css = """
body { font-family: 'Noto Sans', sans-serif; font-size: 10pt; color: #1a202c; }
h1 { font-size: 20pt; color: #1a365d; border-bottom: 2pt solid #2b6cb0; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 6pt 8pt; border-bottom: 1pt solid #e2e8f0; }
thead th { background: #edf2f7; }
"""

# One call produces everything the agent needs
result = engine.render_bundle(
    body_html=html,
    css_text=css,
    out_dir="./output",
    stem="report",
    run_verifier=True,        # Accessibility verification
    run_pmr=True,             # PMR quality score
    render_preview_png=True,  # Visual preview per page
    emit_reading_order_trace=True,
    emit_pdf_structure_trace=True,
)
```

## What `render_bundle` Produces

A single call generates up to **15 artifacts**:

```
output/
├── report.pdf                              # Tagged PDF (PDF/UA targeted)
├── report.html                             # HTML artifact
├── report.css                              # CSS artifact
├── report_page1.png                        # Preview image (page 1)
├── report_a11y_verify_engine.json          # Accessibility verifier report
├── report_pmr_engine.json                  # PMR quality score
├── report_pdf_ua_seed_verify.json          # PDF/UA structural checks
├── report_reading_order_trace.json         # Reading order (lopdf extraction)
├── report_reading_order_trace_render.json  # Reading order (render-time)
├── report_pdf_structure_trace.json         # Tag tree (lopdf extraction)
├── report_pdf_structure_trace_render.json  # Tag tree (render-time)
├── report_asset_resolution_trace.json      # Image/asset resolution
├── report_font_resolution_trace.json       # Font resolution
├── report_pagination_trace.json            # Page layout trace
└── report_run_report.json                  # Overall status
```

## The Agent Feedback Loop

Each artifact gives agents specific, actionable feedback:

### 1. Visual Preview (PNGs)

```python
# Agent can "see" the output without opening the PDF
pages = engine._engine.render_image_pages(html, css, dpi=150)
# Returns list of PNG bytes, one per page
```

### 2. PMR Score

```json
{
  "score": {"score": 100.0, "confidence": 97.5, "band": "excellent"},
  "profile": "cav"
}
```

PMR (Pagination/Markup/Readability) quantifies accessibility quality on a 0-100 scale with confidence bands. Not just pass/fail — agents can optimize toward a target score.

### 3. PDF/UA Seed Verification

```json
{
  "ok": true,
  "checks": [
    {"id": "pdf.mark_info.present", "verdict": "pass"},
    {"id": "pdf.structure_root.present", "verdict": "pass"},
    {"id": "pdf.catalog.lang.present_seed", "verdict": "pass"},
    {"id": "pdf.trace.reading_order.cross_check_seed", "verdict": "pass"}
  ]
}
```

14 structural checks verify the PDF's tag tree, reading order, and metadata. Cross-checks compare render-time output against post-hoc PDF extraction — if they disagree, you know something went wrong.

### 4. Reading Order Trace

```json
{
  "pages": [{
    "page": 1,
    "blocks": [
      {"index": 0, "text": "Q4 2025 Sales Report"},
      {"index": 1, "text": "Summary"},
      {"index": 2, "text": "Revenue exceeded targets by 12%."}
    ]
  }]
}
```

The reading order trace shows exactly what a screen reader would encounter, in order. Agents can verify logical reading flow without running a screen reader.

### 5. Accessibility Verifier

```json
{
  "gate": {"ok": true, "error_count": 0, "warn_count": 3},
  "summary": {"pass_count": 11, "fail_count": 0, "warn_count": 3, "manual_needed_count": 4}
}
```

Rule-level pass/fail with severity, mapped to WCAG 2.0 AA and Section 508 criteria.

## CLI for Agent Pipelines

```bash
# Render with all diagnostics as JSON
fullbleed render \
    --html doc.html \
    --css style.css \
    --out output.pdf \
    --emit-image \
    --json-only

# Get schema for tool definitions
fullbleed render --schema
fullbleed capabilities --json
```

`--json-only` ensures all output is machine-parseable. `--schema` produces JSON schemas suitable for agent tool definitions (function calling).

## The IRS Tax Forms Story

Fullbleed was used to autonomously generate IRS tax form layouts from Publications 1141, 1167, and 1179. An AI agent:

1. Parsed the IRS specification documents
2. Generated semantic HTML + CSS for each form
3. Rendered with `render_bundle()` and inspected the artifacts
4. Iterated on layout based on PMR scores and visual preview feedback
5. Achieved specification compliance without human intervention

This is the workflow Fullbleed was built for: agents that can render, inspect, and iterate on documents autonomously.

## Component System for Agents

For agents that prefer structured document building over raw HTML, Fullbleed's UI component system provides accessibility-by-construction:

```python
from fullbleed.ui import *
from fullbleed.ui.accessibility import *

@Document(page="letter", margin="0.75in", title="Report", bootstrap=True)
def report():
    return Stack(
        Heading("Quarterly Report", level=1),
        Region(
            FieldGrid(
                FieldItem("Revenue", "$2.8M"),
                FieldItem("Target", "$2.5M"),
            ),
            label="Summary",
        ),
        Section(
            SemanticTable(
                caption="Revenue by segment",
                head=SemanticTableHead(
                    SemanticTableRow(
                        ColumnHeader("Segment"),
                        ColumnHeader("Amount"),
                    )
                ),
                body=SemanticTableBody(
                    SemanticTableRow(
                        RowHeader("Enterprise"),
                        DataCell("$1.45M"),
                    ),
                ),
            ),
            label="Revenue",
        ),
        Alert("Board review March 15."),
    )

# Validate accessibility contract before render
artifact = report()
contract = A11yContract()
issues = contract.validate(artifact, mode="warn")
# issues["ok"] == True, issues["error_count"] == 0
```

Components like `SemanticTable`, `ColumnHeader`, `RowHeader`, `Region`, and `Alert` emit correct ARIA attributes and semantic HTML automatically. It's impossible to produce inaccessible output if you use the component system correctly.
