---
title: Reusable PDF headers, footers and page numbers in Python
description: Build a complete report from Python components, including styled headers and finalized page counts. Download the Fullbleed 2.6.0a9 source kit and export PDF or HTML.
---

# Reuse your design on every page

!!! info "Current component preview: 2.6.0a10"
    [Get the current components, styling guide and source kit](component-preview-10.md).
    This page retains the alpha 9 package and its verification record.

A document's header can use the same brand component as its body. Its footer can
carry a styled page count that updates after pagination. Fullbleed **2.6.0a9**
adds `PageBand` and `PageNumbers` to the experimental Python component API.

The Common Ground field-notes example combines a shared theme, reusable brand
and metric components, a table, and three numbered pages. Edit its Python
functions and data to make it your own.

[Download the complete source kit](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.6.0a9/fullbleed-component-showcases-2.6.0a9.zip){ .md-button .md-button--primary }
[Open the field-notes PDF](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.6.0a9/common-ground-field-notes-pdfua2-2.6.0a9.pdf){ .md-button }
[Try the page-band notebook](../getting-started/page-band-notebook.md){ .md-button }

![Common Ground field notes: a seasonal report with reusable brand header, editorial typography, summary metrics and a finalized page count.](../assets/component-preview-9/field-notes-1.png)

!!! info "Install the preview explicitly"
    Use Python 3.10 or later in a virtual environment. The kit pins
    `fullbleed==2.6.0a9`; ordinary `pip install fullbleed` selects the stable
    channel. Components under `fullbleed.ui.experimental` may change.

## Run the report

Extract the ZIP, open its `fullbleed-component-showcases-2.6.0a9` folder, and run:

```sh
python -m pip install -r requirements.txt
python component_page_bands/render.py --out output/field-notes --pdf-profile pdfua2
```

Open `output/field-notes/field-notes.pdf`, `field-notes.html`, or
`field-notes-unstyled.html`. The PDF has repeating bands and page values such as
`1 / 3`. HTML has one semantic header, main and footer, with explicit
`[page] / [pages]` placeholders. It does not paginate the browser.

The content is fictional. Fonts come from the pinned package or the source kit;
PDF generation does not need a browser or system fonts. Choose `--pdf-profile
tagged` for ordinary tagged PDF, or `pdfua1` for the other accessible profile.

## Give the margins reusable components

This complete example creates a PDF with a branded header and a numbered footer:

```python
from importlib.resources import files
from pathlib import Path
from fullbleed.ui.experimental import (
    Document, Heading, Page, PageBand, PageNumbers, Paragraph, Renderer,
    Theme, component, mm, pt, style,
)

@component
def Brand(name):
    return Paragraph(name, style=style(font_size=pt(8), font_weight=700))

document = Document(
    Heading("Project summary", level=1),
    Paragraph("Prepared by Northstar Studio."),
    title="Project summary",
    lang="en-US",
    theme=Theme(text=style(font_family="Inter", font_size=pt(10))),
    page=Page(
        "A4", margin=mm(20),
        header=PageBand(left=Brand("NORTHSTAR STUDIO")),
        footer=PageBand(right=PageNumbers(total=True, class_name="folio")),
    ),
    styles={".folio": style(font_size=pt(8), color="#53665c")},
)
font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
renderer = Renderer(font_files=[str(font)])
Path("summary.pdf").write_bytes(document.render_pdf(renderer))
Path("summary.html").write_text(document.to_html(include_styles=True), encoding="utf-8")
Path("summary.unstyled.html").write_text(document.to_html(include_styles=False), encoding="utf-8")
```

`class_name="folio"` adds the literal class. The matching `.folio` rule in
`Document(styles=...)` supplies its appearance. Components also accept `style=`;
`.with_style(...)` customizes their root and `.with_parts(...)` customizes named
internal elements. In the complete report, `Brand`, `Metric` and `NextStep`
expose parts, and `styled(...)` defines reusable typography.

`Page` reserves the margins. A band does not enlarge them automatically. It
accepts `left`, `center` and `right` slots, with `first_page` and `blank_pages`
policies. A `PageNumbers` value occupies its own slot. Managed bands report
layout or conservative paint-bound failures with the page, slot and authoring
source. Register fonts explicitly so those checks can use the actual glyphs.

See the [page-band API and limits](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.6.0a9/docs/component-page-bands.md)
for per-record numbering, fit diagnostics, styling precedence and export behavior.

## Keep both authoring paths

The same kit also includes the existing Northstar invoice, Common Ground
report and authored accessible community guide:

```sh
python design_showcase/compare_authoring.py --out output/paired
python accessible_showcase/render.py --out output/accessible-ua1
python accessible_showcase/render.py --pdf-profile pdfua2 --out output/accessible-ua2
```

Northstar and the report each include component and HTML/CSS sources for the
same design. The paired command compares the rendered pages and writes styled
and unstyled HTML. The guide demonstrates headings, captioned tables, column
headers, lists and image descriptions. Bootstrap components remain static,
including HTML export; no Bootstrap JavaScript is included.

The [paired-authoring walkthrough](showcase-authoring.md),
[accessible-guide walkthrough](accessible-showcase.md), and
[Bootstrap catalog](bootstrap-components-preview.md) retain their versioned
examples. The [alpha 8 guide](component-preview-8.md) documents the earlier package,
which does not include `PageBand` or `PageNumbers`.

## Verification and scope

The [release evidence](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.6.0a9)
links source provenance, checksums, saved-output comparisons and independent
PDF/UA validator reports. The source ZIP is tested after extraction using a
fresh public package installation.

The component source retains 1,480 native tests, 11 doctests and 970 Python
tests. Its 33-case page-band matrix includes per-record numbering, styled
number comparisons, first/blank-page policies and rejected inputs. Earlier
saved-PDF fixtures and the designed showcases retain their reviewed output.
The complete CSS comparison retains its 25 failed cases and 18 disputed references.

Repeated bands are artifacts outside the PDF body reading order. Keep essential
identity and report details in the body as well. Profile selection and passing
specimens do not establish accessibility for arbitrary documents or human
assistive-technology usability. Fit checks are conservative; named/facing-page
band variants are outside this API. Native streaming output is not atomic.
