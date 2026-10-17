# One design, two authoring paths

Recreate Northstar Studio and Common Ground with HTML/CSS or Python components.
The component API is an opt-in alpha. Python 3.10+ is required.

From this extracted directory, preferably in a fresh virtual environment:

```sh
python -m pip install -r requirements.txt
python examples/design_showcase/compare_authoring.py --out output
```

Open `output/html/invoice/invoice.pdf` and
`output/components/invoice/invoice.pdf`, then the corresponding `report` PDFs.
`output/comparison.json` records four identical page PNGs, page counts, PDF hashes,
replay checks, font diagnostics, and styled/unstyled HTML export checks.

The invoice PDFs are byte-identical on the pinned runtime. Common Ground's SVG
nodes introduce extra graphics-state scopes, so its PDF bytes differ while all
three pages have identical pixels in the native preview and independent PDFium
checks. The historical website PDFs were made on 2.4.0; this comparison renders
both source paths on 2.6.0a4.

Read `examples/design_showcase/README.md` for components, styling, direct PDF and
HTML export, fixed page limits, font licenses, and the four original HTML projects.
The direct component example is run from `examples/design_showcase/`.

Guide: https://docs.fullbleed.dev/guides/showcase-authoring/
