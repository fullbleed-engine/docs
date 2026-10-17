---
title: An accessible document, authored with components
description: A designed two-page Common Ground guide with Python component source, PDF/UA-1 validation evidence, and styled or unstyled HTML exports.
---

# An accessible document, authored with components

Common Ground is a fictional community-program guide: an illustrated cover,
reusable program cards, a captioned schedule and practical visitor information.
Its Python source carries headings, table headers, lists and an image description
through to the final PDF.

[Read the component source](https://github.com/fullbleed-engine/fullbleed-official/blob/1dade16aa2131cb7c1d683bd8cb18b366ede2d0e/examples/accessible_showcase/guide.py).

[Read the PDF](../assets/accessible-showcase/common-ground-guide.pdf){ .md-button .md-button--primary }
[Download the source kit](../assets/accessible-showcase/project.zip){ .md-button }
[Open the responsive HTML](../assets/accessible-showcase/guide.html){ .md-button }

![Common Ground cover with forest-green serif typography, an illustrated shared garden, three program cards and a welcoming callout.](../assets/accessible-showcase/page-1.png)

[View the schedule and visitor-information page](../assets/accessible-showcase/page-2.png).

!!! info "Pinned component alpha"
    The kit uses `fullbleed.ui.experimental` from **2.6.0a4**. Its API may change
    before stabilization. The PDF and all verification receipts below refer to
    this specific published specimen.

## Build it and make it yours

Unzip the source kit, open its folder and run:

```sh
python -m pip install -r requirements.txt
python render.py
```

The PDF appears at `output/common-ground-guide.pdf`. Edit the `SCHEDULE` records
or compose another card:

```python
from guide import ProgramCard

card = ProgramCard(
    "Grow something",
    "A few seeds. A pair of hands. A garden we tend together.",
)
```

`ProgramCard` owns its section and H3. `ProgramSchedule` uses `DataTable` and
`Column` to turn records into a table with a caption and scoped column headers.
`BulletList` preserves list semantics; the illustration uses `Image(alt=...)`.
The source needs no raw HTML strings.

## Styling and HTML export

`class_name="program-card"` emits the authored CSS class. Its appearance comes
from `.program-card` in `guide.css`, loaded with `Document(styles=...)`.
The class name does not load a stylesheet automatically.

`guide.css` owns the print design. `browser.css` adds the responsive presentation
only to browser exports; `Page(size="A4", margin=mm(0))` owns the PDF geometry.

```python
from guide import build_document

document = build_document(browser=True)
styled = document.to_html(include_styles=True, a11y_mode="raise")
unstyled = document.to_html(include_styles=False, a11y_mode="raise")
```

[Open the unstyled HTML](../assets/accessible-showcase/guide-unstyled.html) to see
the semantic document without CSS. It retains authored class names, text, alt
text and the link, so another application can supply its own presentation.
The render command copies the local fonts and illustration beside both exports.

## What was checked

The final two-page PDF passed **veraPDF 1.30.3's PDF/UA-1 validation profile:
106 passed rules, 5,326 passed checks, zero failures and no diagnostic warnings**. The receipt identifies
the exact PDF by SHA-256.

| Check | Result |
| --- | --- |
| Actual PDF structure and marked-content text | One H1, continuous H2/H3 hierarchy, expected logical reading order |
| Image | One tagged figure with the authored description |
| Schedule | One table, three column headers with `/Scope /Column`, nine data cells |
| Lists | Two lists containing six items |
| Fonts, metadata and geometry | Embedded fonts, English language, document title, two A4 pages; no overflow or missing-glyph/font-substitution gate failures |
| Reproduction | Identical PDF bytes on repeat rendering and through the exported HTML/CSS path |
| Visual review | Both pages inspected in native and independent PDFium previews |
| Styled HTML | Checked at 1440, 390 and 320 pixels; no horizontal overflow; keyboard link focus verified |
| Unstyled HTML | Semantic elements and authored classes retained; no CSS or inline style declarations |
| Authored text colors | Minimum contrast ratio 7.45:1 across the design's text/background pairs |

[Validation receipt](../assets/accessible-showcase/validation.json) ·
[veraPDF report](../assets/accessible-showcase/pdfua1.verapdf.json) ·
[PDF tag and reading-order report](../assets/accessible-showcase/structure.json) ·
[Browser checks](../assets/accessible-showcase/browser-verification.json) ·
[Source manifest](../assets/accessible-showcase/source.json)

These checks are **not a screen-reader user test or blanket WCAG certification**.
The kit includes `verify.py` to inspect the actual output again after edits.
For an external check, run [veraPDF's UA-1 profile](https://docs.verapdf.org/cli/validation/)
on the final PDF:

```sh
verapdf --format json -f ua1 output/common-ground-guide.pdf
```

The pinned runtime exports HTML links as plain PDF text, so this document also
writes out its destination URL. Redundant decorative folios and card numbers
are omitted because paragraph ARIA attributes do not reliably remove that text
from the PDF's tags in this alpha. The browser export has a descriptively named
link. The two-page print layout should be rechecked after content changes.

For another way to author the same design, see the
[paired Northstar and Common Ground examples](showcase-authoring.md).
