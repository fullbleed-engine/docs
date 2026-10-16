# Static Bootstrap components for Python

An experimental Fullbleed authoring kit pinned to source commit
`41a2cee2e96b085429d2b9518f4c7d7cfab99817`. This includes the 23 Bootstrap 5.0.0
component families, forms, layout, content, helpers and checked utility classes.
It is not included in the stable Fullbleed 2.5.26 package on PyPI or the earlier
`component-preview-f88cced`. Names and behavior may change.

All Bootstrap components are static, including HTML export. No Bootstrap
JavaScript is included. PDFs use explicit print representations for controls:
values and selections are printed, with no fillable fields.

## Install and run

Use CPython 3.10+ and an isolated virtual environment:

```console
python -m venv .venv
```

Activate with `.venv\Scripts\Activate.ps1` on Windows PowerShell, or
`source .venv/bin/activate` on macOS/Linux. From this folder:

```console
python -m pip install --force-reinstall -r requirements-preview.txt
python first_document.py
python examples/component_bootstrap/main.py --out output --catalog-pdfs
```

The installer selects a matching Windows, macOS or Linux wheel from the pinned
GitHub preview and checks its hash. No Rust build is needed for those platforms.
The preview retains package version metadata 2.5.26; `--force-reinstall` replaces
any same-version package inside this environment. Its commit and hashes identify
the preview, not the version number alone.

If no wheel matches your platform, the explicit fallback
`python -m pip install --force-reinstall -r requirements-source.txt` builds the
same commit and requires Rust/Cargo and your platform's native build tools.

Open `order.pdf`, `order.html` and `order.unstyled.html` for the first example.
Then open `output/report.pdf`, `output/report.styled.html`, and
`output/catalog.html`. The catalog also writes 27 static specimen PDFs.
All data and organizations are fictional.

## Edit content, structure and appearance

| Task | Start here |
| --- | --- |
| Add a formatted column | `columns` in `first_document.py`; each `Column` owns its header and cell function |
| Change a card title's color | `.with_parts(title=style(...))`; no internal selector required |
| Reuse a component | Return a node from an ordinary Python function; use `@component` for named diagnostics |
| Apply Bootstrap styling | Named options such as `variant="success"` or literal `class_name="mb-3"` |
| Apply a custom CSS class | `class_name="order-note"` plus `Document(styles={".order-note": style(...)})` |
| Choose a static state | `active`, `open`, `checked`, `value`, and selected options in `catalog.py` |
| Export complete HTML with CSS | `document.to_html(include_styles=True)` |
| Export unstyled HTML | `document.to_html(include_styles=False)`; class names and content remain |
| Export a component fragment | The same `to_html` calls on a node |
| Change the report | `examples/component_bootstrap/main.py` |
| Explore all component families | `examples/component_bootstrap/catalog.py` |

`class_name` is a literal CSS label. Bootstrap components carry Bootstrap CSS
automatically; your custom classes need explicit rules. Normal CSS specificity
applies, including Bootstrap utilities that use `!important`. An inline style
does not override an important utility declaration.

Styled HTML embeds collected CSS, not fonts or images. HTML export does not
create a PDF renderer, but still requires the installed Fullbleed distribution.
The PDF examples explicitly select Fullbleed's bundled Inter font.

Bootstrap CSS includes global reset and typography rules. When inserting a
fragment into an application that already loads Bootstrap, use
`include_styles=False` so the existing stylesheet styles its class names.

## Scope

The catalog demonstrates 23 component families plus layout, forms, content and
utilities. It is a bounded set of specimens, not exhaustive testing of every
Bootstrap combination. Tabs do not switch, carousels do not advance, and spinners
do not animate. Modals and other overlays appear in document flow. No browser
pixel parity, accessibility conformance, Sass compiler or standalone HTML-only
package is claimed.

Read the [API guide](https://github.com/fullbleed-engine/fullbleed-official/blob/41a2cee2e96b085429d2b9518f4c7d7cfab99817/docs/component-bootstrap.md)
and [implementation review](https://github.com/fullbleed-engine/fullbleed-official/blob/41a2cee2e96b085429d2b9518f4c7d7cfab99817/docs/component-authoring-next-iteration.md).
If you try an editing task, share where the API helped or required generated
HTML/internal selectors in the existing
[design discussion](https://github.com/fullbleed-engine/fullbleed-official/discussions/86).
Use small synthetic examples without customer data.
