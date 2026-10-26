# Frequently asked questions

## Is Fullbleed free for commercial use?

The current Fullbleed release is [MIT licensed](https://github.com/fullbleed-engine/fullbleed-official/blob/master/LICENSE), including commercial use under the license terms. Older references to AGPL or required commercial licensing do not describe the current release.

## What do I need to install?

Standard-GIL CPython 3.10–3.15 and a Fullbleed wheel for your platform. The core has no required third-party Python runtime dependencies. See [installation](getting-started/installation.md) for the published platform list and Python 3.15 qualification.

## Can I use my existing HTML and CSS?

Fullbleed uses static HTML/CSS as a document layout language. Check the [CSS coverage](css-coverage.md) and test representative templates. JavaScript and a live browser DOM are outside the engine's document-rendering model.

## How do I generate PDFs from application data?

Start with the [JSON or CSV invoice examples](guides/invoices.md). Escape text before inserting it into HTML. For repeated templates, see [compiled variable-data rendering](guides/bank-statements.md).

## Why is Chinese text missing or garbled?

Register a font file that contains the required characters and select its family
in CSS. Fullbleed does not search system fonts. Also check that the source text
is decoded as UTF-8. The [Chinese-font recipe](guides/chinese-pdf.md) provides a
verified bilingual invoice, font preparation, and missing-character diagnostics.

## Why are table rows or column text cut off? {#tables-cut-off}

**Stable 2.5.35 fixes clipped auto-height pagination in Python and Rust.**
Tables can continue across PDF pages while explicitly sized clipping viewports
keep their existing behavior. See the [release and retained verification evidence](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.5.35).
For JavaScript, **npm 0.8.1** includes the same engine fix in its Node and browser
entries; see the [JavaScript pagination checks](https://github.com/fullbleed-engine/fullbleed-node/blob/v0.8.1/docs/pagination.md).

In **2.5.34** and **2.6.0a14**, clipping an auto-height table or its container can
keep rows below the physical page instead of continuing them onto another page.
On those versions, remove fixed `height`/`max-height` constraints and clipping
from long tables and their wrappers. Keep a `<thead>` for repeated column headings:

```css
.report-table {
  table-layout: auto;
  overflow: visible;
}
```

In **2.6.0a14**, percentage column widths can also push neighboring text past the
table edge when a label needs more than its assigned share. Remove percentage
`width` declarations from the affected `th`, `td`, and `<col>` elements so the
automatic layout can allocate space from the content. Remove widths from
`style` attributes too; a normal stylesheet rule does not override inline CSS.

The combined workaround was checked with an 80-row table on both versions:
every row appears once, headings repeat, and glyphs stay within the page and
table bounds. Review the final PDF with your actual fonts and data. Complete
text extraction alone does not prove the text is visible on the page.

Follow the fixes for [clipped-container pagination](https://github.com/fullbleed-engine/fullbleed-official/pull/127)
and [percentage column sizing](https://github.com/fullbleed-engine/fullbleed-official/pull/128).

## Does choosing a PDF profile prove conformance?

No. Profile selection configures output. Verify the final artifact and retain the validator reports. The [accessibility workflow](accessibility/overview.md) and [print-output reference](guides/print-output.md) describe the available checks and current limits.

## Does Fullbleed edit arbitrary existing PDF content?

Fullbleed supports document generation and PDF-template composition. For general changes to existing page content, choose a tool designed for that operation. See the [tool selection guide](guides/comparison.md).

## How can I help?

Try a real document, share a minimal reproducible issue, contribute an example, or improve the docs. Include the installed Fullbleed version, input HTML/CSS, explicit assets, expected result, and diagnostics in [bug reports](https://github.com/fullbleed-engine/fullbleed-official/issues). Remove private customer data from shared examples.
