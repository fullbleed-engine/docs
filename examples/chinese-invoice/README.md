# Chinese text in a Fullbleed PDF

Example code: MIT license (`LICENSE`). Font: SIL OFL 1.1 (`fonts/OFL.txt`).

A fictional one-page Simplified Chinese/English invoice. Text and numbers are
editable in `data.json`; layout lives in `invoice.css` and `render.py`.

Use Python 3.11 or newer. From this directory:

```bash
python -m pip install -r requirements.txt -r requirements-fonts.txt
python prepare_font.py
python render.py
```

Open `output/invoice.pdf` and `output/preview/invoice_page1.png`.
The renderer also writes its HTML/CSS, glyph report, font hash and PDF hash.
Missing characters stop the render before a new PDF is written. The included
three-row data fits one A4 page; inspect every page after changing the content.
This is an ordinary PDF example, not a tax invoice or a compliance certificate.

To supply different data or an output directory:

```bash
python render.py --data data.json --out output/edited
```

Text is escaped before insertion into HTML. Currency uses integer CNY cents;
the renderer computes each row and the total before layout.

## Fonts are project assets

Fullbleed does not search system fonts or fetch a font named in CSS. This example
registers `fonts/NotoSansSC-Regular.ttf` explicitly and selects `Noto Sans SC` in
CSS. Save source text as UTF-8. Changing `document_lang` does not load a font.

`prepare_font.py` downloads a pinned 17.8 MB Google Fonts source file and checks
its size and SHA-256. It uses fontTools 4.65.0 to prepare a static regular-weight
(400) TrueType face, verifies that output, and retains the full character
repertoire of the source font. This step can take about a minute. It needs
network access once; subsequent renders use only local files and Fullbleed.
For offline deployment, prepare the font first and copy `fonts/`, the scripts,
data, CSS and manifest into the deployment. Install only `requirements.txt` there.

The pinned source is a variable font whose default weight is 100. Fullbleed
2.5.8 uses the default variable-font instance. Preparing the static 400 face
avoids accidentally rendering thin text. This design uses weight 400 throughout;
for other weights, supply their actual static faces and explicit CSS mappings.

Font provenance and checksums are in `font-source.json`. The source and prepared
font remain under SIL OFL 1.1; retain `fonts/OFL.txt`. Font preparation changes
the weight instance and its face names. It does not subset the font. Fullbleed
embeds the used glyphs when producing this PDF.

The example verifies horizontal Simplified Chinese mixed with English. It does
not establish support for every character, language, shaping rule or vertical
writing mode. A glyph report checks coverage, not encoding, reading order or
typographic quality. Also inspect the finished PDF and its extracted text.

Guide: https://docs.fullbleed.dev/guides/chinese-pdf/
