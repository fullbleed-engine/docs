# Main website source

`squarespace-home.html` is the maintained HTML code block for
[www.fullbleed.dev](https://www.fullbleed.dev/). Squarespace owns the surrounding
navigation, footer and page metadata. This directory is not deployed by MkDocs.

The homepage leads with the browser playground and Python quickstart, alongside
the HTML/CSS Northstar invoice. Farther down, it highlights component authoring
with a runnable stable Python example, an explicitly labeled alpha preview,
paired Northstar/Common Ground sources, and the accessible showcase with its
retained validation reports. An ordinary install still selects the stable API.

`homepage-example.py` is the exact copyable example. With Python 3.10–3.14:

```sh
python -m pip install fullbleed
python website/homepage-example.py
```

It writes `order.pdf` in the current directory and registers the bundled Inter
font explicitly. The example was verified with the published 2.5.31 wheel:
one page, the expected text, embedded fonts, and identical PDF bytes on repeat
rendering. It does not claim PDF/UA conformance.

To update Squarespace, back up the current homepage code block and global code
injection, review the candidate in the existing public page shell, and replace
only the homepage block. Verify the saved page anonymously at desktop and mobile
widths, including real clipboard contents and linked PDF downloads. Do not paste
this block into global code injection. Keep the copyable example synchronized
with `homepage-example.py`.

## Tagged-PDF landing page

`squarespace-accessibility.json` is the maintained source for
[www.fullbleed.dev/accessibility](https://www.fullbleed.dev/accessibility).
It records the SEO fields, page header styling, and four native text blocks by
their existing IDs. This page links the stable C# notice and the explicitly
experimental Common Ground Python kit to their source and retained validation
reports. Scanned-record transcription or OCR is a separate workflow.

Back up those four blocks and the page settings before editing. Apply each
`html` value through its corresponding text editor, and `headerCode` only to this
page's Advanced header injection. Set the SEO title and description separately.
Squarespace normalizes rich-text markup: it places `strong` inside links and
wraps list-item text in paragraphs. The saved source and scoped CSS account for
that form. Verify headings, list structure, all links, visible keyboard focus,
and layout after saving; do not rely on a draft preview alone.

The October 27, 2026 published page was checked at 1440, 390, and 320 CSS pixels,
with no block overlap or horizontal overflow. All eight distinct destinations
returned HTTP 200. The three linked PDFs matched the checked-in document assets
byte for byte and contained extractable text. These website checks do not add
an accessibility or conformance claim to the linked specimens.
