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

For automatic PDF previews while editing, run:

```sh
python examples/design_showcase/preview.py
```

Open the local URL printed in the terminal, then save a Python component, CSS,
or JSON data edit. The page refreshes automatically and provides PDF plus HTML
downloads. Use `--document report` for Common Ground or `--authoring html` for
the original template path. Errors retain a clearly labeled last good preview;
saving a correction retries. Ctrl-C stops the server. Download anything you
want to keep before stopping it.

This optional development helper uses only the pinned Fullbleed wheel and the
Python standard library. It executes the local source and binds to 127.0.0.1.
The comparison command above remains the explicit matching-output check.

Guide: https://docs.fullbleed.dev/guides/showcase-authoring/
