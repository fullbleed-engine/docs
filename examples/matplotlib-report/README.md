# Matplotlib charts in a styled PDF report

This MIT-licensed example combines two Matplotlib SVG figures with HTML/CSS,
summary metrics, a data table and page numbers. The supplied fictional dataset
produces a two-page A4 report. No browser, GUI, TeX installation or system font
is needed.

Use Python 3.11 or newer. From this extracted `matplotlib-report` directory:

```sh
python -m venv .venv
```

Activate it with `.venv\Scripts\activate` on Windows, or
`source .venv/bin/activate` on macOS/Linux. Then:

```sh
python -m pip install -r requirements.txt
python report.py --out output
```

Open `output/report.pdf` and the two PNGs in `output/preview/`. The output also
includes the generated HTML, SVG figures, Matplotlib reference PNGs, a glyph
report and a JSON record of package versions, totals and asset hashes. Reference
PNGs are for review; the renderer receives only the SVG figures.

## Customize

Edit `data.json` for labels and nonnegative integer delivery counts. Regional
counts must add up to the final month's delivery count. The loader rejects
duplicate labels, invalid counts and inconsistent regional totals. Zero plans
produce `n/a` instead of a divided-by-zero percentage.

```sh
python report.py --data my-data.json --out my-report
```

Change `report.css` for typography, spacing, colors and page layout. Change
`charts()` in `report.py` for figure types and chart colors, and `document()` for
the report's structure and wording. Keep SVG dimensions and CSS image dimensions
at the same aspect ratio. Review pagination after changing content or record
counts; the two-page specimen uses six months and four regions.

The data is escaped before entering HTML. Chart strings are passed as text to
Matplotlib. The example reads local JSON and CSS; it does not fetch remote data.

## Fonts and SVG

Both renderers use the Inter font bundled with the pinned Fullbleed wheel.
Matplotlib converts chart labels to paths with `svg.fonttype = 'path'`. This
preserves their shape without asking an SVG consumer to find a system font,
but those labels are not searchable PDF text. The HTML table and captions repeat
the values as selectable text. This is not a PDF accessibility conformance claim.

The SVG export removes its date and fixes `svg.hashsalt`. The verification checks
that repeated inputs produce identical SVGs and PDFs in the tested environment.
Different Matplotlib, font, FreeType or Fullbleed versions can change output.

SVG rendering here uses `svg_raster_fallback=False` and `svg_form_xobjects=True`.
The two sample figures contain no embedded raster images. Other Matplotlib
features, such as `imshow()` or explicitly rasterized artists, can produce image
content inside an SVG. Review and verify each new figure type.

Matplotlib and its pinned dependencies belong to this example. Fullbleed's base
Python package retains its dependency-free runtime. Matplotlib's own `savefig`
and `PdfPages` can export figures directly when a composed report is unnecessary.
