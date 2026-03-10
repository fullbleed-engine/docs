# Template Composition

Fullbleed can overlay rendered HTML content onto existing PDF templates — letterheads, branded forms, pre-printed backgrounds. No separate composition library needed.

## How It Works

Pass a `template_pdf` parameter to `PdfEngine`. The engine renders your HTML content and overlays it onto each page of the template. The template becomes the background; your HTML becomes the foreground.

```python
from fullbleed import PdfEngine

html = """
<div style="margin-top: 120pt;">
  <h2>Dear Valued Customer,</h2>
  <p>Thank you for your continued partnership. Enclosed is your
  quarterly account summary for Q4 2025.</p>

  <table>
    <tr><td>Account Balance:</td><td>$12,450.00</td></tr>
    <tr><td>Transactions:</td><td>47</td></tr>
    <tr><td>Statement Period:</td><td>Oct 1 – Dec 31, 2025</td></tr>
  </table>

  <p>If you have any questions, please contact us at support@example.com.</p>
</div>
"""

engine = PdfEngine(
    template_pdf="company-letterhead.pdf",
    margin="1.25in",  # Wider margins to avoid overlapping letterhead artwork
    document_title="Q4 Statement",
)

pdf_bytes = engine.render(html)
```

## Common Use Cases

### Corporate Letterhead

Your design team provides a branded PDF with logo, address block, and footer art. You render content into the body area:

```python
engine = PdfEngine(
    template_pdf="letterhead.pdf",
    margin="1.5in",  # Top margin clears the logo
    page_margins={1: {"top": "2in"}},  # Extra top margin on first page for logo
)
```

### Government Forms

Overlay data onto pre-designed form layouts:

```python
# Position content precisely within form fields
html = """
<style>
  .field { position: absolute; font-family: monospace; font-size: 10pt; }
  .name { top: 142pt; left: 180pt; }
  .date { top: 142pt; left: 450pt; }
  .address { top: 172pt; left: 180pt; }
</style>
<div class="field name">John Smith</div>
<div class="field date">03/09/2026</div>
<div class="field address">123 Main St, Portland OR 97201</div>
"""

engine = PdfEngine(
    template_pdf="government-form.pdf",
    margin="0in",  # No margins — position everything absolutely
)
```

### Branded Reports

Monthly reports that need consistent branding without rebuilding the template in HTML:

```python
engine = PdfEngine(
    template_pdf="report-template.pdf",
    margin="1in",
    header_each="Monthly Report — {page}/{pages}",
    footer_each="Confidential — © 2026 Acme Corp",
)
```

## Multi-Page Templates

If your template PDF has multiple pages, Fullbleed maps rendered pages to template pages:

- **Page 1** of content → overlaid on **page 1** of template
- **Page 2** of content → overlaid on **page 2** of template (if it exists)
- **Page N** of content → overlaid on the **last page** of template (if template has fewer pages)

This means a 2-page template (cover + body) works naturally: page 1 gets the cover background, all subsequent pages get the body background.

## With Accessibility

Template composition works with `AccessibilityEngine` too:

```python
from fullbleed import AccessibilityEngine

engine = AccessibilityEngine(
    strict=False,
    template_pdf="branded-template.pdf",
    document_title="Accessible Report",
    document_lang="en",
    margin="1.25in",
)

results = engine.render_bundle(html)
# Tagged PDF overlaid on template, with full evidence bundle
```

!!! note
    The template PDF itself should be untagged or have minimal tagging — Fullbleed generates the tag structure from your HTML content. Complex pre-tagged templates may cause tag conflicts.

## Next Steps

- [Watermarks →](watermarks.md) — Text and image watermarks
- [Page Margins →](page-margins.md) — Per-page margin control
- [PdfEngine API →](pdf-engine.md) — Full constructor reference
