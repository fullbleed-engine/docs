# Frequently asked questions

## Is Fullbleed free for commercial use?

The current Fullbleed release is [MIT licensed](https://github.com/fullbleed-engine/fullbleed-official/blob/master/LICENSE), including commercial use under the license terms. Older references to AGPL or required commercial licensing do not describe the current release.

## What do I need to install?

Python 3.10–3.14 and a Fullbleed wheel for your platform. The core has no required third-party Python runtime dependencies. See [installation](getting-started/installation.md) for the published platform list.

## Can I use my existing HTML and CSS?

Fullbleed uses static HTML/CSS as a document layout language. Check the [CSS coverage](css-coverage.md) and test representative templates. JavaScript and a live browser DOM are outside the engine's document-rendering model.

## How do I generate PDFs from application data?

Start with the [JSON or CSV invoice examples](guides/invoices.md). Escape text before inserting it into HTML. For repeated templates, see [compiled variable-data rendering](guides/bank-statements.md).

## Why is Chinese text missing or garbled?

Register a font file that contains the required characters and select its family
in CSS. Fullbleed does not search system fonts. Also check that the source text
is decoded as UTF-8. The [Chinese-font recipe](guides/chinese-pdf.md) provides a
verified bilingual invoice, font preparation, and missing-character diagnostics.

## Does choosing a PDF profile prove conformance?

No. Profile selection configures output. Verify the final artifact and retain the validator reports. The [accessibility workflow](accessibility/overview.md) and [print-output reference](guides/print-output.md) describe the available checks and current limits.

## Does Fullbleed edit arbitrary existing PDF content?

Fullbleed supports document generation and PDF-template composition. For general changes to existing page content, choose a tool designed for that operation. See the [tool selection guide](guides/comparison.md).

## How can I help?

Try a real document, share a minimal reproducible issue, contribute an example, or improve the docs. Include the installed Fullbleed version, input HTML/CSS, explicit assets, expected result, and diagnostics in [bug reports](https://github.com/fullbleed-engine/fullbleed-official/issues). Remove private customer data from shared examples.
