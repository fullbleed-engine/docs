# The numbered report

A fictional, two-page project outline with editable HTML and print CSS. Chapters,
subsections, table rows, and page footers receive their numbers from the stylesheet.

Use Python 3.10 or newer in a virtual environment:

```sh
python -m pip install -r requirements.txt
python render.py --out output
```

Open `output/numbered-report.pdf` and both `page-*.png` previews. The command also
saves input/font hashes, a glyph report, and a deterministic replay result in
`render.json`. It requires a fresh output directory so old pages cannot remain.

Edit `report.html` to change the content. Keep chapter and section headings as
siblings inside `main`: `.chapter` resets the section counter, and `.section`
increments it. Insert another section without typing a number yourself.
Edit `report.css` for colors, typography, page size, margins, and page breaks.
The second chapter explicitly starts a new page; longer content can add pages.

The pinned wheel supplies the registered Inter font. Rendering does not fetch
remote fonts or require a browser. After editing, run with another output path:

```sh
python render.py --out output-edited
```

Inspect every page before sharing. The glyph check stops the script before it
writes a PDF when the registered font cannot cover the text. This example does
not claim PDF/UA, PDF/A, or complete CSS counter conformance. The sample content
and Northstar project are fictional. Source code is MIT licensed.
