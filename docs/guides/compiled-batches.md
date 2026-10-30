---
title: Generate batch PDFs from one template in Python
description: Compile one document template, render records into a combined PDF, and check missing characters and per-record page ranges before saving it.
---

# Generate batch PDFs from one template

Use compiled batches when many records share a document design: account notices,
letters, invoices, or statements. Supply columns of values, then render one PDF
in input order. Reflowing bindings let each record take as many pages as its text
needs.

The optional report API requires **Fullbleed 2.5.46 or later**. It returns page
ranges and registered-font character checks alongside the PDF, so your application
can inspect the result before saving or delivering it.

For a JavaScript application, use the [Node.js batch guide](node-pdf-batches.md).

Install the version used by this example with `python -m pip install fullbleed==2.5.46`.
Save the code below as `notices.py`, then run `python notices.py`.

## Render and check a batch

This example registers a bundled font explicitly. The two account notices use the
same template; the longer notice flows onto additional pages.

```python
from importlib.resources import files
from pathlib import Path

import fullbleed

bundle = fullbleed.AssetBundle()
bundle.add_file(
    str(files("fullbleed_assets").joinpath("fonts", "NotoSans-Regular.ttf")),
    fullbleed.AssetKind.Font,
    name="Body",
    trusted=True,
)
engine = fullbleed.PdfEngine()
engine.register_bundle(bundle)

template = engine.compile_pdf(
    """<!doctype html><html lang="en"><body>
    <p class="label">ACCOUNT NOTICE</p>
    <h1>Account {{account}}</h1>
    <p class="message">{{message}}</p>
    </body></html>""",
    """@page { size: A5; margin: 18mm; }
    body { font-family: Body; font-size: 11pt; color: #23342f; }
    .label { color: #47745d; font-size: 8pt; letter-spacing: 1pt; }
    h1 { font-size: 25pt; margin: 8pt 0 18pt; }
    .message { line-height: 1.5; }""",
)

records = {
    "account": ["1042", "1043"],
    "message": [
        "Your account is up to date. Thank you.",
        "Your scheduled account review includes the following information. " * 90,
    ],
}
pdf, report = template.render_pdf_reflow_bindings_with_report(records)

bad_rows = [row for row in report["records"] if row["missing_glyphs"]]
if bad_rows:
    indexes = [row["record_index"] for row in bad_rows]
    raise ValueError(f"Registered-font coverage failed for records: {indexes}")

Path("notices.pdf").write_bytes(pdf)
for row in report["records"]:
    account = records["account"][row["record_index"]]
    first = row["page_offset"] + 1
    last = row["page_offset"] + row["page_count"]
    print(f"Account {account}: pages {first}–{last}")
```

The example saves `notices.pdf` and prints the page range for each account:
account 1042 occupies page 1; account 1043 occupies pages 2–5.

Every binding column must have the same nonzero length. Keep the compiled template
and call it again when only the values change. Treat records as plain text; changes
to attributes, images, selectors, metadata, or document structure need a different
template or the ordinary rendering API.

## Use the report in your delivery workflow

`report["records"]` follows input order. Each entry has:

| Field | Meaning |
| --- | --- |
| <code style="white-space: nowrap">record_index</code> | Zero-based index into the input columns. |
| <code style="white-space: nowrap">page_offset</code> | Zero-based first page in the combined PDF. |
| <code style="white-space: nowrap">page_count</code> | Number of pages produced for this record. |
| <code style="white-space: nowrap">missing_glyphs</code> | Characters absent from the registered fonts selected for its final text. |

`report["page_count"]` is the combined PDF's page count. Missing-character entries
include `codepoint`, `char`, `count`, and `fonts_tried`. The last field identifies
the first selected font where that character was absent.

The report covers the same render as the returned bytes; requesting it preserves
the PDF output. Missing characters do not raise automatically. Choose your own
acceptance policy before writing, emailing, archiving, or queueing the PDF for
delivery. A failed font check should lead to a font or input correction followed
by a new render. No email or delivery service is part of this example.

## Choose fixed or reflowing bindings

Use `render_pdf_reflow_bindings_with_report()` when replacement text may wrap,
change font selection, or change a record's page count. For fixed geometry,
`render_pdf_bindings_with_report()` returns the same report shape while retaining
the compiled layout and fonts. A registered fallback cannot cover a fixed binding
unless the output actually selects that font.

Existing `render_pdf_reflow_bindings()` and `render_pdf_bindings()` still return
PDF bytes alone. The report methods hold the PDF and diagnostics in memory; split
large jobs into batches sized for your worker's memory budget.

## What the character check does not establish

Register fonts explicitly when using these checks. Base-14 fonts and text already
converted to images are outside the report's coverage. An empty `missing_glyphs`
list does not establish correct shaping, layout, accessibility, or PDF conformance.
Unembedded Base-14 fonts can also look different across PDF readers, even when
the PDF bytes are identical.

See [font registration](../engine/font-registration.md) for font setup and the
[2.5.46 Python API](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.5.46/docs/python-api.md#check-a-compiled-batch-before-accepting-it)
for the compiled binding contract.
