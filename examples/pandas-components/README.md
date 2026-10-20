# pandas reports with Python components

A runnable, MIT-licensed example for **Fullbleed 2.6.0a9** and **pandas 3.0.6**.
The component API is experimental; keep the exact version pin while evaluating it.
Python 3.11 or later is required by this pandas version. No browser, system font,
network asset, or Rust build is needed to generate the PDF from the published wheel.

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install --only-binary=:all: -r requirements.txt
python report.py --previews
python report.py --csv products.csv --title "The autumn edit." --period "Autumn 2026" --out output/autumn
```

Open `output/report.pdf`. The supplied fictional 40-row CSV renders as three
landscape A4 pages, with a repeated table header and finalized page totals.
`output/report.html` and `output/report-unstyled.html` demonstrate both HTML
export modes. Keep the `output/fonts/` folder beside the styled HTML. The browser
export is one continuous static document; it does not reproduce PDF pagination.
`--previews` also writes PNG previews of the finalized PDF.

## Make it yours

- Change the palette and shared typography in `components.py` (`THEME`).
- Reuse `Metric`, `Kicker`, and `Small` across documents. `styled()` makes a new
  component factory; it does not change the original one.
- Override one metric's value with `.with_parts(value=style(color=token("accent")))`.
  This public part is declared with `@component(parts=("value", "label"))` and
  attached to the appropriate child using `part="value"`.
- A `class_name="ledger"` attaches a CSS class. Its declarations live in
  `Document(styles={".ledger …": style(...)})`; a class name alone adds no styles.
- Change the `Column` callbacks in `Ledger` to format each record or return a
  component such as `Strong(...)`. `frame.to_dict(orient="records")` is the bridge
  between pandas and the table. The report does not modify the input frame.
- Use `document.to_html(include_styles=True)` to embed component CSS, or `False`
  to omit CSS and inline styles while retaining authored classes and semantics.
  Font loading and screen framing are added separately in `render()`.

## Input contract

`data.load_products()` validates these columns before authoring:

| Column | Contract |
| --- | --- |
| `sku` | Unique, nonblank text |
| `product`, `category` | Nonblank text; markup is treated as text |
| `units` | Nonnegative integer |
| `net_sales_cents` | Signed integer cents; formatted with `Decimal`, never floating point |
| `last_restock` | `YYYY-MM-DD`, or missing (shown as “Not recorded”) |

Extra columns are ignored. An empty CSV, duplicates, invalid dates, and missing
required values are rejected. Row order is preserved. Negative net sales represent
adjustments. All products, sales, and dates are fictional. For an existing
DataFrame, normalize it to this contract before calling `build_report(frame)`.

`Flow` allows the report to paginate. `Stack` is used only inside small metrics.
Rows stay together when they fit; content too large for the page can raise a
structured layout error. Adjust columns, type size, or the document design for
your own unusually long labels and large figures.

## Verification

```sh
python -m pip install --only-binary=:all: -r requirements-check.txt
python verify.py --out output/verification
```

This saves and independently reads/rasterizes the sample, a one-row report, mixed
long/Unicode/literal-markup/negative/missing-date values, and 120 rows. It checks
row order and completeness, repeated headers, page totals, glyph page bounds,
both HTML modes, input immutability, invalid input rejection, and exact PDF bytes
from a fresh Python process. The tagged profile and source checks do **not**
establish PDF/UA conformance or assistive-technology usability.

The fixed document timestamp makes the example reproducible; use the actual report
timestamp in a production application and keep it fixed when replaying a report.
The bundled Inter font is supplied by the installed Fullbleed wheel. Its SIL OFL
license is copied beside the exported font. The CSV is shared with the earlier
Fullbleed pandas HTML/CSS example, which remains available separately.
