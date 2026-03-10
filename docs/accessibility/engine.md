# Accessibility Engine

The `AccessibilityEngine` is Fullbleed's primary interface for generating accessible PDFs. It wraps `PdfEngine` with accessibility-first defaults and produces a complete evidence bundle — not just a PDF, but proof that it's compliant.

## Why a Separate Engine?

You *can* make accessible PDFs with `PdfEngine` by setting `pdf_profile="tagged"`. But the `AccessibilityEngine` does more:

1. **Forces PDF/UA targeting** — tagged structure is mandatory, not optional
2. **Runs accessibility verification** — checks the output against WCAG/PDF/UA rules
3. **Generates evidence bundles** — 15+ artifacts proving compliance
4. **Computes PMR scores** — quantified accessibility scoring
5. **Cross-checks reading order** — validates render-time vs. PDF extraction

This matters because compliance isn't just about output — it's about *proving* output is compliant. Auditors want evidence, not assertions.

## Basic Usage

```python
from fullbleed import AccessibilityEngine

html = """
<h1>Quarterly Report</h1>
<p>Revenue increased 12% year-over-year.</p>

<table>
  <caption>Q4 2025 Revenue by Region</caption>
  <thead>
    <tr>
      <th scope="col">Region</th>
      <th scope="col">Revenue</th>
      <th scope="col">Growth</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th scope="row">North America</th>
      <td>$4.2M</td>
      <td>+15%</td>
    </tr>
    <tr>
      <th scope="row">Europe</th>
      <td>$2.8M</td>
      <td>+8%</td>
    </tr>
    <tr>
      <th scope="row">Asia Pacific</th>
      <td>$1.9M</td>
      <td>+22%</td>
    </tr>
  </tbody>
</table>
"""

engine = AccessibilityEngine(
    strict=False,  # Recommended unless you have full CSS metadata configured
    document_title="Q4 2025 Quarterly Report",
    document_lang="en",
    footer_each="Page {page} of {pages}",
)

results = engine.render_bundle(html)
```

## The Evidence Bundle

A single `render_bundle()` call produces **15 artifacts**:

| Artifact | Type | Description |
|----------|------|-------------|
| `pdf` | bytes | Tagged PDF/UA document |
| `html` | str | The input HTML |
| `css` | str | The resolved CSS |
| `a11y_report` | dict | Accessibility verification (pass/fail per rule) |
| `pmr_score` | dict | Pagination/Markup/Readability score (0–100) |
| `pdfua_seed_verify` | dict | PDF/UA structural tag checks |
| `reading_order_trace` | dict | Every text block in reading order with coordinates |
| `pdf_structure_trace` | dict | Tag tree with MCID mapping |
| `asset_resolution_trace` | dict | How assets (fonts, images) were resolved |
| `font_resolution_trace` | dict | Font matching and embedding details |
| `pagination_trace` | dict | Page break decisions |
| `preview_pngs` | list | Per-page PNG previews |
| `run_report` | dict | Overall render status and timing |
| `cross_check` | dict | Render-time vs PDF extraction comparison |
| `diagnostics` | dict | Engine-level diagnostic information |

### PMR Score

The PMR (Pagination/Markup/Readability) score quantifies accessibility on a 0–100 scale:

```python
pmr = results["pmr_score"]
print(f"Score: {pmr['score']}/100")
print(f"Band: {pmr['band']}")         # "excellent", "good", "fair", "poor"
print(f"Confidence: {pmr['confidence']}")  # e.g., 97.5%
```

With well-structured semantic HTML, scores of 100/100 are achievable.

### PDF/UA Seed Verification

```python
verify = results["pdfua_seed_verify"]
for check in verify["checks"]:
    print(f"  {check['rule']}: {'✅' if check['pass'] else '❌'}")
# All 14 structural checks should pass
```

### Reading Order Trace

The reading order trace cross-checks two independent sources:

1. **Render-time order** — the sequence Fullbleed wrote content to the PDF
2. **PDF extraction order** — what a reader (lopdf) extracts from the finished PDF

If these match, the reading order is correct. If they diverge, something went wrong.

```python
trace = results["reading_order_trace"]
for block in trace["blocks"][:5]:
    print(f"  [{block['page']}] ({block['x']:.0f}, {block['y']:.0f}) {block['text'][:50]}")
```

## Constructor Parameters

The `AccessibilityEngine` accepts all `PdfEngine` parameters as keyword arguments (they pass through as `**engine_kwargs`):

```python
engine = AccessibilityEngine(
    strict=False,
    document_title="My Document",
    document_lang="en",

    # All PdfEngine params work here
    page_width="8.5in",
    page_height="11in",
    margin="0.85in",
    footer_each="Page {page} of {pages}",
    paginated_context={"amount": "sum"},

    # Accessibility profile
    # profile="cav",  # Default — Compliant Alternative Version
)
```

### The `strict` Parameter

- `strict=True` — Requires CSS metadata to be fully configured. Use for production pipelines where you control the CSS.
- `strict=False` — Skips CSS metadata validation. **Recommended for most users.** The engine still produces tagged PDF/UA; it just doesn't require metadata in the stylesheet.

### Profiles

- `"cav"` (default) — Compliant Alternative Version. Full tagged output with evidence.

## Writing Accessible HTML

The engine can only tag what it can understand. Write semantic HTML:

```html
<!-- ✅ Good — clear structure -->
<h1>Report Title</h1>
<p>Introduction paragraph.</p>
<table>
  <caption>Data Table</caption>
  <thead><tr><th scope="col">Header</th></tr></thead>
  <tbody><tr><td>Data</td></tr></tbody>
</table>

<!-- ❌ Bad — no semantic meaning -->
<div style="font-size: 24px; font-weight: bold">Report Title</div>
<div>Introduction paragraph.</div>
<div class="grid">
  <div class="row"><div class="cell">Data</div></div>
</div>
```

Key rules:

1. Use `<h1>`–`<h6>` for headings (in order, no skipping levels)
2. Use `<table>` with `<caption>`, `<thead>`, `<th scope="col|row">`
3. Use `<p>` for paragraphs
4. Use `<ul>`, `<ol>`, `<li>` for lists
5. Use `<img alt="description">` for images
6. Set `document_lang` on the engine

## Next Steps

- [Evidence Bundles →](evidence-bundles.md) — Deep dive on each artifact
- [Coverage Report →](coverage.md) — WCAG 2.0 AA and Section 508 coverage
- [AI Agent Integration →](../guides/ai-agents.md) — Using evidence bundles in agent workflows
