---
title: PDF examples and downloads
description: Download generated Fullbleed invoices, reports, tagged notices, and compiled variable-data PDFs, with runnable Python source and verification details.
---

# See the output. Run the source.

These PDFs were generated with the public Fullbleed 2.4.0 wheel. The five compact workflows passed their expected-content and internal inspection checks. Their [verification manifest](assets/examples/verification.json) records page counts, hashes, and the scope of the checks.

[Try the editable invoice notebook](getting-started/notebook.md) to generate and
download your own PDF before setting up a local project.

[Serve an invoice in FastAPI, Flask, or Django](guides/web-frameworks.md) with the
runnable web app examples.

## Styled invoice

![An Acme invoice with itemized services and a total.](assets/examples/acme-invoice.png){ width="400" }

A component-based invoice from CSV, with bundled assets and application-side decimal calculations.

[Download PDF](assets/examples/acme-invoice.pdf) · [Source and data contract](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/acme_invoice) · [Invoice guide](guides/invoices.md)

## Invoice from JSON

A compact one-page example with an embedded font, item table, and content checks.

[PDF](assets/examples/invoice.pdf) · [HTML](assets/examples/invoice.html) · [CSS](assets/examples/invoice.css) · [Preview](assets/examples/invoice.png)

## Business report

A five-page report with headings and content-driven pagination.

[PDF](assets/examples/business-report.pdf) · [HTML](assets/examples/business-report.html) · [CSS](assets/examples/business-report.css) · [First-page preview](assets/examples/business-report.png)

## Tagged service notice

A one-page semantic notice using the `pdfua1` profile. The example checks profile markers and expected text; see the [accessibility workflow](accessibility/overview.md) for validation scope.

[PDF](assets/examples/accessible.pdf) · [HTML](assets/examples/accessible.html) · [CSS](assets/examples/accessible.css) · [Preview](assets/examples/accessible.png)

## Compiled variable-data documents

| Example | Output | What changes |
| --- | --- | --- |
| [Fixed bindings PDF](assets/examples/compiled-vdp.pdf) | 100 records, 100 pages | Statement IDs, customer names, balances |
| [Reflow bindings PDF](assets/examples/compiled-reflow.pdf) | 20 records, 41 pages | Record content and page count |

[Read the variable-data guide](guides/bank-statements.md) for choosing a rendering lane.

## Run all five compact workflows

```bash
git clone https://github.com/fullbleed-engine/fullbleed-official.git
cd fullbleed-official
python -m pip install fullbleed
python examples/agent_workflows/run_examples.py --out output/examples --json
```

[Browse the full source](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/agent_workflows). Sample data is fictional. These outputs demonstrate the stated workflows; standards conformance requires the applicable checks on the exact delivered artifact.
