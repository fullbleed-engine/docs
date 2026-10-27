# Personalize an existing PDF with Python

Keep a designed PDF as the background and place a transparent text overlay on
top of it for each JSON record. The supplied Common Ground certificate is a
fictional example with an editable HTML/CSS source and an already-built PDF.

Use Python 3.10 or newer in a virtual environment:

```sh
python -m pip install -r requirements.txt
python render.py --out output
```

Open `output/certificates.pdf` and the three `page-*.png` previews. These are
previews of the final composed PDF. The directory also contains the overlay,
the page-composition plan, a repeated output, and hashes/checks in `render.json`.
Rendering uses the engine and Inter font bundled in the pinned Fullbleed wheel.

Edit `data.json` to change recipients, the workshop, completion dates, and IDs.
Use `python render.py --out output-edited` for a new output folder. Dates use
`YYYY-MM-DD`; IDs accept ASCII letters, digits, periods, underscores, and
hyphens. Names allow 48 characters, workshop names 80, and IDs 20. The script
escapes text, checks required glyphs, and reduces the type size for long values.
Review the final pages whenever you change the data or layout.

## Change the design

- `template.pdf`: the one-page background used by the renderer.
- `template.html` and `template.css`: editable source for that background.
- `overlay.css`: positions, fonts, and colors of the variable fields.
- `render.py`: input validation, overlay authoring, and PDF composition.

The page is 792 × 612 points (US Letter landscape). Overlay coordinates are
measured from the top-left, with 72 points per inch. The overlay has no opaque
page background. Keep its page size aligned with the PDF template.

After editing the background artwork, rebuild it to a new path:

```sh
python build_template.py --out revised-template.pdf
python render.py --template revised-template.pdf --out output-revised
```

You can supply another readable, unencrypted, one-page PDF with `--template`.
Use an unrotated page and adjust the page size and field positions in
`overlay.css` to fit it. The script checks readability, encryption, and page
count; it does not automatically check your template's dimensions or rotation.
The original PDF is not overwritten.

## Scope

This places static content over existing artwork. It does not discover/fill
AcroForm fields, replace existing text, preserve digital signatures, or make
the resulting document tagged or accessible. It carries no source annotations
(`annotation_mode="none"`). Use an unsigned template without interactive
content. The input and output files stay on your machine.

The repeat check compares bytes within the installed runtime. It is not a
promise of identical PDF bytes across engine versions. The example's code and
artwork are MIT licensed; the embedded Inter font retains its SIL Open Font
License, included here as `Inter-OFL.txt`.
