# Generating Invoices

Generate professional, paginated invoices from HTML with automatic running totals, page-aware subtotals, and proper headers/footers — all from a single render call.

## Why Fullbleed for Invoices?

Most PDF libraries treat invoices as flat documents. Fullbleed handles the hard parts natively:

- **Per-page running totals** via paginated context — no manual pagination math
- **Consistent headers/footers** with `{page}` / `{pages}` placeholders
- **Deterministic output** — same invoice data produces byte-identical PDFs
- **Tagged PDF/UA** — accessible invoices out of the box

## Quick Example

```python
from fullbleed import PdfEngine

html = """
<style>
  body { font-family: sans-serif; font-size: 10pt; margin: 0; }
  .invoice-header { margin-bottom: 24pt; }
  .company { font-size: 18pt; font-weight: bold; color: #1a365d; }
  .meta { display: flex; justify-content: space-between; margin-top: 12pt; }
  table { width: 100%; border-collapse: collapse; margin-top: 12pt; }
  th { background: #1a365d; color: white; padding: 6pt 8pt; text-align: left; }
  td { padding: 6pt 8pt; border-bottom: 1px solid #e2e8f0; }
  .amount { text-align: right; }
  .total-row { font-weight: bold; background: #f7fafc; }
</style>

<div class="invoice-header">
  <div class="company">Acme Corp</div>
  <div class="meta">
    <div>
      <div><strong>Bill To:</strong></div>
      <div>Jane Smith</div>
      <div>456 Oak Avenue</div>
      <div>Portland, OR 97201</div>
    </div>
    <div>
      <div><strong>Invoice #:</strong> INV-2026-0042</div>
      <div><strong>Date:</strong> March 9, 2026</div>
      <div><strong>Due:</strong> April 8, 2026</div>
    </div>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th>Description</th>
      <th>Qty</th>
      <th>Rate</th>
      <th class="amount">Amount</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Web Development — Homepage Redesign</td>
      <td>40</td>
      <td>$150.00</td>
      <td class="amount" data-amount="6000">$6,000.00</td>
    </tr>
    <tr>
      <td>UI/UX Design — Wireframes</td>
      <td>20</td>
      <td>$125.00</td>
      <td class="amount" data-amount="2500">$2,500.00</td>
    </tr>
    <tr>
      <td>Backend API Development</td>
      <td>60</td>
      <td>$175.00</td>
      <td class="amount" data-amount="10500">$10,500.00</td>
    </tr>
    <tr>
      <td>Database Migration</td>
      <td>15</td>
      <td>$200.00</td>
      <td class="amount" data-amount="3000">$3,000.00</td>
    </tr>
    <tr>
      <td>QA Testing</td>
      <td>25</td>
      <td>$100.00</td>
      <td class="amount" data-amount="2500">$2,500.00</td>
    </tr>
  </tbody>
</table>
"""

engine = PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.75in",
    document_title="Invoice INV-2026-0042",
    document_lang="en",
    pdf_profile="tagged",

    # Headers
    header_each="Invoice INV-2026-0042 — Page {page} of {pages}",
    header_font_size=8,
    header_color="#666666",
    header_y_from_top="0.35in",

    # Footers with running totals
    footer_each="Page Subtotal: ${sum:amount} | Running Total: ${total:amount}",
    footer_font_size=8,
    footer_color="#333333",
    footer_y_from_bottom="0.35in",

    # Paginated context — sum the data-amount values per page
    paginated_context={"amount": "sum"},
)

pdf_bytes = engine.render(html)
with open("invoice.pdf", "wb") as f:
    f.write(pdf_bytes)
```

## Per-Page Running Totals

The `paginated_context` parameter lets you aggregate data across pages automatically. Fullbleed scans for `data-*` attributes matching your context keys and computes per-page and document-wide aggregates.

### Available Operations

| Operation | Syntax | Description |
|-----------|--------|-------------|
| `sum` | `{"key": "sum"}` | Sum values per page (default 2 decimal places) |
| `sum:<scale>` | `{"key": "sum:4"}` | Sum with custom decimal precision |
| `count` | `{"key": "count"}` | Count occurrences per page |
| `every` | `{"key": "every"}` | Collect all values per page |

### Footer Placeholders

| Placeholder | Description |
|-------------|-------------|
| `{sum:key}` | Sum of values on current page |
| `{total:key}` | Running total across all pages so far |
| `{count:key}` | Count of items on current page |
| `{total_count:key}` | Running count across all pages |
| `{every:key}` | All values on current page |
| `{total_every:key}` | All values across all pages |
| `{page}` | Current page number |
| `{pages}` | Total page count |

## Multi-Page Invoices

For invoices with many line items that span multiple pages, Fullbleed handles page breaks automatically. Each page gets its own subtotal via `{sum:amount}`, and the running total via `{total:amount}` carries forward.

```python
# Generate 50 line items that will span multiple pages
items = []
for i in range(50):
    amount = (i + 1) * 100
    items.append(f"""
    <tr>
      <td>Service Line Item #{i+1}</td>
      <td>1</td>
      <td>${amount:,.2f}</td>
      <td class="amount" data-amount="{amount}">${amount:,.2f}</td>
    </tr>
    """)

html = f"""
<style>
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #1a365d; color: white; padding: 6pt; text-align: left; }}
  td {{ padding: 6pt; border-bottom: 1px solid #eee; }}
  .amount {{ text-align: right; }}
</style>
<h1>Invoice INV-2026-0099</h1>
<table>
  <thead><tr><th>Description</th><th>Qty</th><th>Rate</th><th class="amount">Amount</th></tr></thead>
  <tbody>{"".join(items)}</tbody>
</table>
"""

engine = PdfEngine(
    margin="0.85in",
    footer_each="Page {page}/{pages} — Page Total: ${sum:amount} — Invoice Total: ${total:amount}",
    paginated_context={"amount": "sum"},
)
pdf_bytes = engine.render(html)
```

Each page's footer will show:
- **Page 1/3 — Page Total: $2,100.00 — Invoice Total: $2,100.00**
- **Page 2/3 — Page Total: $5,500.00 — Invoice Total: $7,600.00**
- **Page 3/3 — Page Total: $5,400.00 — Invoice Total: $13,000.00**

## Accessible Invoices

For WCAG-compliant invoices (required for government vendors), use the `AccessibilityEngine`:

```python
from fullbleed import AccessibilityEngine

engine = AccessibilityEngine(
    strict=False,
    document_title="Invoice INV-2026-0042",
    document_lang="en",
    footer_each="Page {page} of {pages}",
    paginated_context={"amount": "sum"},
)

results = engine.render_bundle(html)
# results["pdf"] — Tagged PDF/UA
# results["a11y_report"] — Accessibility verification
# results["pmr_score"] — Pagination/Markup/Readability score
```

## Template Overlay

Need to render onto a pre-designed invoice template (letterhead, watermark, branding)?

```python
engine = PdfEngine(
    template_pdf="company-letterhead.pdf",
    margin="1.25in",  # Larger margins to avoid template artwork
)
pdf_bytes = engine.render(html)
```

The rendered HTML content is overlaid onto each page of the template PDF.

## Next Steps

- [Paginated Context →](../engine/paginated-context.md) — Deep dive on per-page data aggregation
- [Headers & Footers →](../engine/headers-footers.md) — All header/footer options
- [Bank Statements →](bank-statements.md) — Similar pattern for financial documents
- [Template Composition →](../engine/template-composition.md) — Overlay onto existing PDFs
