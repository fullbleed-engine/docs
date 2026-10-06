# Markdown to PDF with Fullbleed

Turn a Markdown file into a styled PDF, with local images, an editable print
stylesheet, and PNG previews. Includes a fictional engineering brief. MIT
licensed; the included IBM Plex Mono font uses the SIL Open Font License.

## Run

Use Python 3.10 or newer in a virtual environment:

```sh
python -m pip install -r requirements.txt
python render.py brief.md --out output --title "Release notes that travel"
```

Open `output/document.pdf`. The command prints the current preview paths and
writes `output/render.json` with input, font, image, stylesheet, and PDF hashes.
The PNGs come from the finalized PDF. Each PDF has its own preview subdirectory,
so a shorter rerender does not mix new pages with an older document's previews.

`markdown-it-py` parses the content and Fullbleed renders the resulting HTML/CSS.
These dependencies are pinned in `requirements.txt`; the Markdown parser is
optional and is not a dependency of the core `fullbleed` package. Rendering
uses the installed engine and local assets. No browser or PDF service is needed.

## Use your own document

```sh
python render.py /path/to/notes.md --out output/notes --title "Project notes"
python render.py brief.md --css my-print.css --out output/custom
python render.py brief.md --out output/pdf-only --no-preview
```

Relative input paths and `--out` are relative to the working directory. The
default stylesheet and included font are found beside `render.py`. The `--css`
option replaces the stylesheet; start by copying `print.css`.

The parser supports headings, paragraphs, ordered and unordered lists, emphasis,
inline and fenced code, block quotes, links, pipe tables, and strikethrough.
Code fences are printed as text without syntax highlighting. Raw HTML is
escaped. This preset does not add task lists, footnotes, front matter, math,
Mermaid execution, or full GitHub Markdown compatibility.

## Images and fonts

Use PNG, JPEG, or SVG files beneath the Markdown file's own directory:

```markdown
![Publishing workflow](images/publishing.svg)
```

The script registers these files explicitly, including paths with URL-encoded
spaces. It rejects remote image URLs, missing files, absolute paths, and paths
that resolve outside that directory. Images are limited to 16 MiB combined;
each Markdown or CSS input is limited to 4,000,000 bytes. This is a local
publishing example, not a sandbox for hosting arbitrary uploaded documents.

Body text uses Inter from the Fullbleed wheel. Code uses the included static
IBM Plex Mono face. To use another script or typeface, pass a local TTF with
`--font` and select its actual family name in your stylesheet:

```sh
python render.py brief.md --font fonts/MyFont.ttf --css my-print.css --out output/custom
```

Missing glyphs produce a nonzero exit and `glyph-report.json`; no new PDF is
written. A previous PDF in that output directory may still exist. The report
does not establish that every requested CSS font family was used, so inspect
the actual previews when changing fonts or styles.

The intermediate `document.html` contains engine asset aliases; use the PDF or
PNG previews for review. To reproduce it separately, register the images listed
in `render.json` under those aliases.

## Review and reuse

Review all pages for wrapping, wide tables, long code lines, and page breaks.
Fullbleed uses static print CSS; see its [CSS coverage](https://docs.fullbleed.dev/css-coverage/).
This starter produces ordinary PDFs and makes no PDF/A or PDF/UA conformance claim.

- [Markdown guide](https://docs.fullbleed.dev/guides/markdown-pdf/)
- [Fullbleed source](https://github.com/fullbleed-engine/fullbleed-official)
- [markdown-it-py options](https://markdown-it-py.readthedocs.io/en/latest/using.html)
- [IBM Plex Mono license and source](fonts/source.json): unmodified font and `OFL.txt` included.

The accompanying verification checks the actual ZIP in an isolated directory,
renders and independently reads the PDFs, checks image and font handling,
exercises input failures, and compares repeated output bytes. Those checks cover
the retained fixtures; they do not validate every possible Markdown document.
