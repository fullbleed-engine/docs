---
title: Compose styled PDF and HTML with Python components
description: Use Python functions, reusable styles and explicit class names to author PDF and HTML. Try the Fullbleed 2.6.0a12 component namespace and complete migration kit.
---

# Compose documents with Python components

Use Python functions for reusable document sections, pass data as arguments,
and keep each component's default styles with its definition. Export the same
tree as a PDF, styled HTML or unstyled HTML without writing HTML strings.

**2.6.0a12** introduces `fullbleed.components` as the intended public namespace.
It preserves both earlier import paths and adds a complete document migration
example: two implementations produce the same A5 and Letter landscape reports.

The current opt-in release is **2.6.0a14**, which adds native PDF navigation
and fixes inline opacity and table-cell alignment. This guide and its downloadable
kit stay pinned to alpha 12. See the [release status](component-status.md) for
the latest install command, the [PDF links guide](pdf-links.md) for a working
report, and the [alpha 14 release notes](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.6.0a14)
for the rendering changes.

[Download the migration source kit](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.6.0a12/fullbleed-component-migration-2.6.0a12.zip){ .md-button .md-button--primary }
[Read the migration reference](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.6.0a12/docs/component-namespace.md){ .md-button }

!!! info "The API remains alpha"
    Use Python 3.10 or later in a virtual environment and install
    `python -m pip install --pre "fullbleed==2.6.0a12"`.
    Ordinary `pip install fullbleed` selects the stable channel.
    The existing `fullbleed.ui` API remains supported. A public namespace does
    not itself make the new API stable; the [release status](component-status.md)
    records the remaining decisions.

## Write a component with its own styles

`Summary` below is an ordinary reusable function. `Title` carries its default
appearance, while `.muted` is an explicit stylesheet rule:

```python
from importlib.resources import files
from pathlib import Path
from fullbleed.components import (
    Document, Flow, Heading, Page, Paragraph, Renderer, Theme,
    component, mm, pt, style, styled,
)

Title = styled(Heading, font_size=pt(24), color="#183e36")

@component
def Summary(title, description):
    return Flow(
        Title(title, level=1),
        Paragraph(description, class_name="muted"),
        gap=pt(12),
    )

document = Document(
    Summary("Project summary", "Prepared by Northstar Studio."),
    title="Project summary",
    lang="en-US",
    page=Page("A5", margin=mm(16)),
    theme=Theme(text=style(font_family="Inter", font_size=pt(11))),
    styles={".muted": style(color="#50665f")},
)
font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
renderer = Renderer(font_files=[str(font)])
Path("summary.pdf").write_bytes(document.render_pdf(renderer))
Path("summary.html").write_text(document.to_html(include_styles=True), encoding="utf-8")
Path("summary.unstyled.html").write_text(
    document.to_html(include_styles=False), encoding="utf-8"
)
```

`class_name="muted"` writes the literal class `muted`. The matching `.muted`
rule in `Document(styles=...)` supplies its appearance. The dot belongs in the
selector. A function name or class name does not load a stylesheet automatically.

| Change you want | Where to put it |
| --- | --- |
| Reusable defaults for a heading, box or paragraph | `styled(...)` |
| One component instance | `style=style(...)` or `.with_style(...)` |
| A component's named internal part | `.with_parts(...)` |
| Shared typography and theme values | `Theme(...)` on `Document` |
| A literal CSS class | `class_name="..."` and a matching rule in `Document(styles=...)` |
| Paper size, orientation and margins | `Page(...)` on `Document` |

The [styling notebook](../getting-started/component-styling.md) lets you edit
these style mechanisms in a complete Common Ground report. It keeps its
explicit alpha 11 pin; the earlier import path continues to work in alpha 12.
The [component reference](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.6.0a12/docs/component-bootstrap.md)
covers style precedence, named parts and static Bootstrap 5.0.0 helpers.

When combining reusable kits, [try the two-kit report](component-kits.md).
It demonstrates concrete palette defaults, documented theme dependencies and
local overrides with the current alpha 14 package.

## Export with or without styles

`document.to_html(include_styles=True)` embeds component styles, the theme and attached selector
rules. `document.to_html(include_styles=False)` removes generated CSS and inline
styles while keeping semantic content and literal classes, ready for a host
stylesheet. `Flow` gaps work in styled browser HTML.

The default `document.to_html()` keeps the separate-CSS form used with
`document.to_css()`. Choose `include_styles=True` for a complete styled HTML
file, or `False` when another application owns the styles.

PDF uses the explicitly registered font. Browser HTML needs its own font loading
or fallback; registering a font with `Renderer` does not give a browser a font
URL. Continuous browser layout and native PDF pagination are separate outputs.
Bootstrap helpers are static in both: no Bootstrap JavaScript is included.

## Keep existing imports working

If you already use an earlier alpha, change the import prefix when convenient:

```python
# Earlier alpha: still supported.
from fullbleed.ui.experimental import Document, Paragraph

# Intended public namespace for the new API.
from fullbleed.components import Document, Paragraph
from fullbleed.components import bootstrap as bs
```

These two namespaces expose the same objects. Components, styles and Bootstrap
helpers can be composed across them without a second style registry. Both have
the same typed signatures and editor completions.

The older `fullbleed.ui` API is a different authoring model. Its `Document` is
a decorator; the new `Document` is a value that owns its page, theme and metadata.
Changing an import alone does not migrate an existing decorated document.

## Migrate a whole document

Extract the source kit and open its `fullbleed-component-migration` directory:

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -I examples/component_migration/render.py --out output
```

Compare `output/a5-legacy.pdf` with `output/a5-components.pdf`, then the two
`letter-landscape` PDFs. Each report has three pages. The kit includes the four
saved PDFs in `preview/` for inspection before installation.

Read `legacy_document` and `migrated_document` side by side in `render.py`:

| Existing document setting | New owner |
| --- | --- |
| Page CSS for paper, orientation and margins | `Page(...)` |
| Engine title and language options | `Document(title=..., lang=...)` |
| Body typography | `Theme(text=style(...))` |
| Repeated class-based defaults | `styled(...)`, with explicit selectors where useful |
| Font files and engine options | `Renderer(...)` |

Change `ROWS` for content, `INK` and `MUTED` for colors, or `REPORTS` for page
geometry. Both implementations retain explicit font registration and a fixed
document timestamp.

For gradual adoption, `to_legacy(node, theme=...)` adapts a new component into
an old tree. It does not move the old document's geometry, metadata, renderer
settings or resource-owning kits such as Bootstrap. The
[migration reference](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.6.0a12/docs/component-namespace.md)
explains those boundaries.

## Rich documents and earlier examples

The [alpha 11 showcase kit](component-preview-11.md) retains the Northstar
invoice, Common Ground reports and authored accessible community guide with
its original package pin. It also demonstrates page bands and styled HTML.
The [paired-authoring guide](showcase-authoring.md) shows the HTML/CSS and
component implementations with the same rendered output.

## Verification and scope

The [alpha 12 release evidence](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.6.0a12)
records package provenance, saved outputs and checks. Local qualification
passes 374 focused component tests and 980 full Python tests. Both import paths
are checked with mypy, Pyright and real language-server completions.

The migration kit renders with Fullbleed alone. Its optional verifier checks
page geometry, per-page text, title/language, resolved timestamp, missing glyphs,
repeat bytes and exact PDFium pixels for the two paired reports. These examples
demonstrate an explicit migration, not automatic conversion of arbitrary CSS.

The independent CSS corpus retains known failures. This release does not claim
complete CSS conformance, browser/PDF layout equivalence, independent kit
usability or human accessibility results. Existing accessible specimen results
remain scoped to their exact verified PDFs.

## Help shape the stable API

Try rebranding a report, reusing a component, or adding a table column. Share
a small synthetic example in the [component RFC](https://github.com/fullbleed-engine/fullbleed-official/discussions/86),
including your installed version, the change you wanted and any step that
required raw HTML or knowledge of generated selectors. Those editing experiences
help identify which authoring contracts still need work.
