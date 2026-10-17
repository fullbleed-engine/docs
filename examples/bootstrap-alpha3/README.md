# Static Bootstrap components for Python

This kit uses the opt-in **Fullbleed 2.6.0a3** Python alpha, from source
`a5c66e5d6cc890a04b9373c3bfc2b41ccc868405`. It includes the 23 Bootstrap 5.0.0
component families, forms, layout, content, helpers and checked utility classes.
The API remains experimental under `fullbleed.ui.experimental`; names and
behavior may change. Normal stable installations do not select this alpha.

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
python -m pip install --pre -r requirements.txt
python first_document.py
python examples/component_bootstrap/main.py --out output --catalog-pdfs
```

The exact alpha version is in `requirements.txt`. pip downloads a compatible
wheel from PyPI on supported Windows, macOS and Linux platforms. Other platforms
may build the source distribution and require Rust/Cargo and native build tools.
You can also install it with `python -m pip install --pre "fullbleed==2.6.0a3"`.

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

Custom components can declare required `parts=(...)` and conditional
`optional_parts=(...)`. Use `.forward_parts(heading="label")` to expose a
selected child part deliberately. Missing required targets fail at construction;
private child parts remain private. See the
[authoring guide](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.6.0a3/examples/component_recipes/README.md#customize-a-root-or-an-exposed-part).

Alpha 2 includes the stable 2.5.27 inline SVG styling fixes. Document selectors,
inherited color and named-part opacity apply to supported SVG descendants in
PDFs and styled HTML. Unstyled HTML keeps classes for a host stylesheet.

Alpha 3 also includes the stable 2.5.28 inset-shadow corrections, including
negative spread, translated holes and clear edges. PDF and HTML remain static.

Explicit theme and component font choices also replace Bootstrap's variable-based
font default. Register font files with Renderer for PDF output; browser hosts
provide their own fonts. Typography can reflow when the intended font is used.

## Scope

The catalog demonstrates 23 component families plus layout, forms, content and
utilities. It is a bounded set of specimens, not exhaustive testing of every
Bootstrap combination. Tabs do not switch, carousels do not advance, and spinners
do not animate. Modals and other overlays appear in document flow. No browser
pixel parity, accessibility conformance, Sass compiler or standalone HTML-only
package is claimed.

Read the [API guide](https://github.com/fullbleed-engine/fullbleed-official/blob/a5c66e5d6cc890a04b9373c3bfc2b41ccc868405/docs/component-bootstrap.md)
and [implementation review](https://github.com/fullbleed-engine/fullbleed-official/blob/a5c66e5d6cc890a04b9373c3bfc2b41ccc868405/docs/component-authoring-next-iteration.md).
If you try an editing task, share where the API helped or required generated
HTML/internal selectors in the existing
[design discussion](https://github.com/fullbleed-engine/fullbleed-official/discussions/86).
Use small synthetic examples without customer data.
