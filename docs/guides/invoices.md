---
description: Generate PDF invoices from JSON or CSV in Python with Fullbleed. Download a sample PDF and run its complete source.
---
# Generate PDF invoices from Python data

Choose the smallest example that matches your application.

## A compact JSON invoice

The [agent-workflow invoice](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/agent_workflows) loads JSON, escapes text, builds an HTML table, embeds Inter, writes a PDF, and checks that the invoice ID, customer, and total survived rendering.

[Open the PDF](../assets/examples/invoice.pdf) · [View its HTML](../assets/examples/invoice.html) · [View its CSS](../assets/examples/invoice.css)

To run the complete example suite:

```bash
git clone https://github.com/fullbleed-engine/fullbleed-official.git
cd fullbleed-official
python -m pip install fullbleed
python examples/agent_workflows/run_examples.py --out output/examples --json
```

The invoice is written to `output/examples/invoice/document.pdf`. Change the sample data in `examples/agent_workflows/data/invoice.json` and rerun.

## A styled CSV invoice

The [Acme invoice project](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/acme_invoice) separates the header, body, footer, CSS, and CSV input. Its application code calculates line amounts and totals using Python `Decimal`.

![Generated Acme invoice with four line items and a total.](../assets/examples/acme-invoice.png){ width="440" }

[Download the PDF](../assets/examples/acme-invoice.pdf) · [Read the data contract](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.4.0/examples/acme_invoice/README.md)

From the repository checkout:

```bash
cd examples/acme_invoice
python report.py
```

Open `output/acme_sample_invoice.pdf`. Edit `data/invoice.csv`, then inspect the regenerated PNG and component diagnostics before delivery.

## Scale to multiple invoices

Use ordinary rendering when document structure changes substantially. Use [compiled bindings](bank-statements.md) when you have a family of documents with repeatable structure. Choose the reflow API if text or table length can change pagination.
