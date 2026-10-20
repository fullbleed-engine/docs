"""Build the focused styling tutorial from the preserved field-notes notebook."""
from argparse import ArgumentParser
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/page-band-notebook-alpha9/component_page_bands.ipynb"
DESTINATIONS = (
    ROOT / "examples/styling-notebook-alpha10/component_styling.ipynb",
    ROOT / "docs/assets/styling-notebook-alpha10/component_styling.ipynb",
)


def build(channel="alpha10"):
    assert channel in ("alpha10", "alpha11")
    notebook = deepcopy(json.loads(SOURCE.read_text(encoding="utf-8")))
    cells = {cell["id"]: cell for cell in notebook["cells"]}

    def get(name):
        return "".join(cells[name]["source"])

    def put(name, text):
        cells[name]["source"] = text.strip().splitlines(keepends=True)

    def replace(name, before, after):
        source = get(name)
        assert source.count(before) == 1, (name, before)
        put(name, source.replace(before, after, 1))

    for name in cells:
        put(name, get(name).replace("2.6.0a9", "2.6.0a10"))
    put("intro", """# Make the components your own

Change five styling controls in a complete Common Ground report, then compare
the PDF, styled HTML and unstyled HTML. The document uses Python functions and
component values; its content does not need authored HTML strings.

| Control | What it demonstrates |
| --- | --- |
| `ACCENT` | A shared color in `Theme`, read with `token("accent")` |
| `TITLE_SIZE` | A reusable `styled(Heading, ...)` primitive |
| `PANEL_BACKGROUND` | `.with_style(...)` on the metrics panel's root |
| `METRIC_COLOR` | `.with_parts(value=...)` on each `Metric` |
| `FOLIO_COLOR` | A `.folio` rule matched by `class_name="folio"` |

Run all cells, edit one control in step 2, and rerun from there through the
download cell. Change one value at a time to see which elements it affects.
The PDF includes repeating headers and finalized page totals.

This notebook explicitly installs **Fullbleed 2.6.0a10**. Its component API is
experimental. All content is fictional. Fullbleed and this notebook are MIT
licensed. Use a standard CPU runtime in Colab or local Jupyter and download
your work before leaving the hosted session.""")
    replace(
        "report-controls",
        'ACCENT = "#755122"',
        '''# Five independent styling paths; try changing one at a time.
ACCENT = "#755122"             # Theme token: the small uppercase labels.
TITLE_SIZE = 31                # styled(): all large report headings, in points.
PANEL_BACKGROUND = "#edf2e6"    # with_style(): the first-page metrics panel.
METRIC_COLOR = "#183e34"        # with_parts(): only the large metric values.
FOLIO_COLOR = "#53665c"         # class_name + selector: the page numbers.''',
    )
    replace("shared-styles", "font_size=pt(31)", "font_size=pt(TITLE_SIZE)")
    replace(
        "compose-document",
        'Row(Metric("126", "neighbors took part"), Metric("21", "open sessions"), gap=pt(18))',
        '''Row(
                    Metric("126", "neighbors took part").with_parts(value=style(color=METRIC_COLOR)),
                    Metric("21", "open sessions").with_parts(value=style(color=METRIC_COLOR)),
                    gap=pt(18),
                )''',
    )
    replace(
        "compose-document",
        'style=style(background=token("paper"), padding=pt(18)),\n            ),',
        'style=style(background=token("paper"), padding=pt(18)),\n            ).with_style(background=PANEL_BACKGROUND),',
    )
    replace(
        "compose-document",
        'styles={".folio": style(font_size=pt(8), color=token("muted"))}',
        'styles={".folio": style(font_size=pt(8), color=FOLIO_COLOR)}',
    )
    replace(
        "render-export",
        "for include_styles, filename in (",
        '''# Reuse the same content with browser-only presentation rules.
# Native Flow spacing needs flex-column layout in a browser. Keep those
# host rules out of the PDF document; no HTML string rewriting is needed.
browser_document = Document(
    *document.children,
    title=document.title, lang=document.lang, page=document.page, theme=document.theme,
    styles=document.styles + """
@media screen {
    body, [data-fb-band-slot] { font-family: Inter, sans-serif; }
    body { max-width: 680px; margin: 0 auto; padding: 24px; }
    [data-fb-flow] { display: flex; flex-direction: column; }
    main > [data-fb-flow] { margin-bottom: 40px; }
    [data-fb-page-band] { margin: 12px 0 28px; }
    footer[data-fb-page-band] { margin-top: 28px; }
}
""",
)
for include_styles, filename in (''',
    )
    replace(
        "render-export",
        '''    (output / filename).write_text(
        document.to_html(include_styles=include_styles, a11y_mode="raise"),''',
        '''    export_document = browser_document if include_styles else document
    (output / filename).write_text(
        export_document.to_html(include_styles=include_styles, a11y_mode="raise"),''',
    )
    # Put the selector explanation beside the code it describes, not just in
    # the landing page. Existing markdown cell IDs remain deterministic.
    compose_index = notebook["cells"].index(cells["compose-document"])
    notebook["cells"].insert(compose_index, {
        "cell_type": "markdown", "id": "style-connections", "metadata": {},
        "source": """### Follow a style to its target

`class_name="folio"` on `PageNumbers` emits the class. The matching
`Document(styles={".folio": style(...)})` supplies its appearance. The dot
belongs in the selector; omit it from `class_name`. A class name does not
automatically load Bootstrap or any other stylesheet.

`Metric` explicitly declares the `value` and `label` parts. Its
`.with_parts(value=style(...))` call changes the value without changing the
label. `.with_style(...)` changes a component's root. These calls return new
values, so one instance can be customized without changing its siblings.

Try `METRIC_COLOR = "#8c2f6b"` first. Then restore it and try
`FOLIO_COLOR = "#206b7a"`. The named part affects the first page's two numbers;
the selector affects the footer on every page.
""".splitlines(keepends=True),
    })
    notebook["cells"].append({
        "cell_type": "markdown", "id": "export-styling-scope", "metadata": {},
        "source": """## Use the HTML in another application

Both HTML files contain the same authored content. Styled HTML includes the
component and document CSS. Unstyled HTML retains semantic structure and
classes, including `folio`, but contains no style declarations; your host can
provide its own CSS. Both exports are static, without Bootstrap JavaScript.

The PDF uses explicitly registered, bundled Inter. Registering that font with
`Renderer` does not embed it in browser HTML; the browser host must provide
Inter or use a fallback. HTML has one header/main/footer sequence and
`[page] / [pages]` placeholders. It does not paginate like the PDF.
The included `@media screen` stylesheet frames the browser document, provides
a sans-serif fallback, and maps native `Flow` spacing to browser flex columns.
It belongs to `browser_document`, which shares the same component content.
The PDF document does not receive these host rules.

For a longer report, put 72 rows in `ACTIVITY` and rerun. Use `ACTIVITY = []`
afterwards to check the empty state. The ZIP includes only the current PDF,
HTML files and previews, even after a longer run.

The PDF/UA-2 profile and source checks express authoring intent. Validate your
own output and perform human assistive-technology review when needed. Repeated
PDF bands sit outside body reading order; essential information also belongs
in the body.
""".splitlines(keepends=True),
    })
    if channel == "alpha11":
        for cell in notebook["cells"]:
            cell["source"] = "".join(cell["source"]).replace(
                "2.6.0a10", "2.6.0a11").splitlines(keepends=True)
        replace(
            "render-export",
            "# Native Flow spacing needs flex-column layout in a browser. Keep those\n"
            "# host rules out of the PDF document; no HTML string rewriting is needed.",
            "# Flow already exports its browser layout and gaps. Keep font fallbacks\n"
            "# and screen framing out of the PDF document.",
        )
        replace(
            "render-export",
            "    [data-fb-flow] { display: flex; flex-direction: column; }\n",
            "",
        )
        scope = next(cell for cell in notebook["cells"] if cell["id"] == "export-styling-scope")
        old = ("The included `@media screen` stylesheet frames the browser document, provides\n"
               "a sans-serif fallback, and maps native `Flow` spacing to browser flex columns.\n"
               "It belongs to `browser_document`, which shares the same component content.\n"
               "The PDF document does not receive these host rules.")
        new = ("The included `@media screen` stylesheet supplies a sans-serif fallback and\n"
               "screen framing. `Flow` exports its own browser layout and gaps; no host\n"
               "layout rule is needed. PDF-only page breaks are hidden in styled HTML.\n"
               "The host stylesheet belongs to `browser_document`, which shares the same\n"
               "component content. The PDF document does not receive those host rules.")
        text = "".join(scope["source"])
        assert text.count(old) == 1
        scope["source"] = text.replace(old, new).splitlines(keepends=True)
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            assert cell["outputs"] == [] and cell["execution_count"] is None
    return (json.dumps(notebook, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--channel", choices=("alpha10", "alpha11"), default="alpha10")
    args = parser.parse_args()
    data = build(args.channel)
    for original in DESTINATIONS:
        destination = Path(str(original).replace("styling-notebook-alpha10", "styling-notebook-" + args.channel))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    print(f"Built the styling notebook and identical download ({len(data)} bytes).")
