---
title: Python components — current preview and source showcases
description: Recreate the Northstar invoice, Common Ground report and accessible community guide with Fullbleed 2.6.0a8. Download the verified source and export PDF or styled and unstyled HTML.
---

# Python components: make the design your own

Start with a complete invoice, report or community guide. Edit Python functions,
data and styles, then generate a PDF and HTML from the same component tree.
The **2.6.0a8 preview** includes the page-furniture and running-header fixes from
stable 2.5.34, with the preview's improved page-margin sizing.

[Download the source kit](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.6.0a8/fullbleed-component-showcases-2.6.0a8.zip){ .md-button .md-button--primary }
[Release and verification evidence](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.6.0a8){ .md-button }

!!! info "An explicit preview installation"
    The API lives under `fullbleed.ui.experimental` and may change. The source kit
    pins `fullbleed==2.6.0a8`; ordinary `pip install fullbleed` selects the stable
    channel. Use Python 3.10 or later in a virtual environment.

## Choose a starting point

| Document | PDF | Source in the kit |
| --- | --- | --- |
| Northstar invoice | [One-page invoice](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.6.0a8/northstar-invoice-2.6.0a8.pdf) | `design_showcase/invoice_components.py` and `invoice.html` |
| Common Ground report | [Three-page report](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.6.0a8/common-ground-report-2.6.0a8.pdf) | `design_showcase/report_components.py` and `report.html` |
| Common Ground accessible guide | [PDF/UA-1](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.6.0a8/common-ground-guide-pdfua1-2.6.0a8.pdf) · [PDF/UA-2](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.6.0a8/common-ground-guide-pdfua2-2.6.0a8.pdf) | `accessible_showcase/guide.py` and `guide.css` |

The content is fictional. Northstar and the report each include HTML/CSS and
component source for the same design. The guide shows headings, a captioned table,
column headers, lists and an image description authored through components.

## Recreate the documents

Unzip the kit, open its `fullbleed-component-showcases-2.6.0a8` folder, activate
your virtual environment and run:

```sh
python -m pip install -r requirements.txt
python design_showcase/compare_authoring.py --out output/paired
python accessible_showcase/render.py --out output/accessible-ua1
python accessible_showcase/render.py --pdf-profile pdfua2 --out output/accessible-ua2
```

The paired command renders both designs through both authoring paths and compares
their PDF pages. It also writes styled and unstyled HTML. Edit the records in
`design_showcase/data.json`, reuse a component such as `InvoiceField` or
`AmountDue`, or compose another `ProgramCard` in the guide.

Fonts, illustrations and font licenses are included or supplied by the pinned
Fullbleed package. PDF generation needs no browser or system fonts.

## Give a component its appearance

Components can carry defaults and expose named styling parts. `class_name`
adds a literal CSS class; a matching rule supplies its appearance. For example:

```python
from pathlib import Path
from fullbleed.ui.experimental import Document, style
from fullbleed.ui.experimental import bootstrap as bs

note = bs.Alert("Please retain this copy.", class_name="order-note")
document = Document(
    note,
    styles={".order-note": style(color="#205b47", border_color="#b8cec4")},
)
Path("note.html").write_text(document.to_html(include_styles=True), encoding="utf-8")
Path("note.unstyled.html").write_text(document.to_html(include_styles=False), encoding="utf-8")
```

Bootstrap components carry their default stylesheet. `.with_style(...)` changes
a component root; `.with_parts(title=style(...))` targets an exposed internal
part. Unstyled HTML retains content, semantic elements and authored classes so
the host application can provide CSS. All Bootstrap components and exports are
static; no Bootstrap JavaScript is included.

See the [current styling API](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.6.0a8/docs/component-bootstrap.md#how-styling-works)
and [reusable component recipes](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.6.0a8/examples/component_recipes/README.md).
The [paired-authoring guide](showcase-authoring.md),
[accessible-guide walkthrough](accessible-showcase.md) and
[Bootstrap catalog](bootstrap-components-preview.md) retain their earlier,
versioned examples and verification records.

## What was verified

The release's source ZIP was extracted and executed using a fresh public PyPI
installation. It reproduced the checked PDFs. Northstar's two authoring paths
produce identical PDF bytes; Common Ground's report pages have identical pixels.
Each accessible-guide profile produces identical PDF bytes through components
and exported HTML/CSS, and passes independent veraPDF validation.

The release retains 943 Python tests, 1,451 native tests, 489 saved-PDF regression
cases and validation evidence for 326 PDF/UA matrix fixtures. The complete CSS
corpus remains failing, with 25 failed cases and 18 disputed references. Reports,
checksums, limits and reproduction details are linked from the release.

These fixture checks do not establish accessibility for arbitrary documents or
human assistive-technology usability. Running-box measurements do not establish
complete painted-ink fit; transformed content and oversized descendants can
clip. `PageBand` and `PageNumbers` remain design proposals. The preview preserves
the deterministic print-document engine and static HTML export boundaries.
