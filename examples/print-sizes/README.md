# Custom paper sizes with print CSS

This fictional shelf card keeps its paper size and margins in HTML/CSS.
Python selects the bundled Inter font and writes the PDFs and previews.

Use standard-GIL CPython 3.10–3.15 in a virtual environment:

```sh
python -m pip install -r requirements.txt
python render.py
```

Open `output/metric-card.pdf` (100 × 150 mm) or `output/inch-card.pdf`
(4 × 6 inches). Each file contains one card. The second output overrides the
embedded `@page` rule with a separate CSS argument; no page dimensions are
passed to the engine constructor. The two paper sizes are different.

Edit `shelf-card.html` to change the copy, typography, vector cup or page rule.
Its screen-only preview instruction is excluded from PDFs. Its 20 mm scale
line appears in print output. The HTML does not fetch fonts, images or scripts.

When printing, select matching stock and Actual size / 100% in the PDF viewer.
Fit-to-page changes physical dimensions. Measure the 20 mm line on a sample;
printer drivers and hardware margins are separate from the PDF page geometry.

The product, store and price are fictional. This example verifies ordinary PDF
page dimensions and print-style behavior, not printer output or PDF/X conformance.
The Inter font and its notices come from the installed Fullbleed package.
