# Arabic and English invoice

A fictional A4 invoice using Fullbleed, local Noto Sans Arabic regular/bold
faces, and the Inter font bundled with Fullbleed. All names and amounts are
sample data. The template code is MIT-licensed; keep `fonts/OFL.txt` with the
bundled Arabic fonts.

Use a Python 3.11 or newer virtual environment:

```sh
python -m pip install -r requirements.txt
python render.py
```

Open `output/invoice.pdf` and `output/preview/invoice_page1.png`. Font files
are already in the ZIP. Rendering needs no network access or system fonts.

Edit `data.json` for the studio, customer, reference, dates and services.
Amounts use integer USD cents; quantities are positive integers. The script
calculates line totals and escapes inserted HTML text. Edit `invoice.css`
for colors, type, spacing and layout, or `render.py` for the HTML structure.

```sh
python render.py --data data.json --out output/custom
```

Keep Arabic strings in logical Unicode order. Do not reverse them manually.
Use `direction: rtl` for Arabic blocks and `<bdi dir="ltr">` around dates,
references and other fields that must retain their LTR order. Keep an Arabic
word together when styling its text; this sample does not test styling
individual connected letters as separate spans.

The renderer verifies pinned font bytes, writes a glyph report and refuses to
write a new PDF if a registered font lacks a character. If you intentionally
replace a font, update its manifest hash and CSS family name. Inspect every
page after changing the content or styling. Readers can reconstruct mixed RTL
and LTR text differently on copy/paste even when the page looks correct.

`render.json` records the engine version, calculated total, PDF size and hash.
The guide and independent output checks are at
https://docs.fullbleed.dev/guides/arabic-pdf/ .
