---
title: Variable-data PDF generation
description: Compile a Fullbleed document template and bind fixed or reflowing records for statements, invoices, and letters.
---
# One template, many documents

Fullbleed offers ordinary batch rendering and compiled document APIs. Choose based on how the content changes.

| Record changes | Start with |
| --- | --- |
| Each document has unrelated HTML/CSS | `PdfEngine` batch APIs |
| Text changes inside stable geometry | `CompiledDocument.render_pdf_bindings` |
| Text or table length changes pagination | `CompiledDocument.render_pdf_reflow_bindings` |

## Fixed fields

```python
import fullbleed

engine = fullbleed.PdfEngine()
template = engine.compile_pdf(
    "<h1>Statement {{statement_id}}</h1><p>{{customer}}</p>",
    "body { font-family: Helvetica; }",
)
template.render_pdf_bindings_to_file(
    {"statement_id": ["ST-001", "ST-002"], "customer": ["Ada", "Grace"]},
    "statements.pdf",
)
```

Use equal-length, nonempty columns. Keep replacement values within the geometry your template reserves. The [100-record example](../assets/examples/compiled-vdp.pdf) comes from the checked [workflow suite](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/agent_workflows).

## Content that changes length

The reflow lane retains the template tree and compiles encountered flow variants. It can paginate records of different lengths. The [20-record example](../assets/examples/compiled-reflow.pdf) produces 41 pages from the current sample data.

Read the [CompiledDocument reference](../engine/pdf-engine.md#compileddocument) for the binding contract, trusted structural slots, compression modes, and examples. The larger [compiled reflow project](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/compiled_reflow) includes table rows, running strings, and per-record page distributions.

## Measure your own workload

The [performance report](performance.md) retains timings and correctness checks for specified historical fixtures. Compile time, first-seen structures, font shaping, compression, I/O, and record length affect your results. Compare complete, equivalent jobs with output verification enabled.

## Print production

For PDF/VT job, record, document, and page hierarchies, use the [print-output contract](print-output.md). The variable-data examples above are ordinary PDF examples and do not claim PDF/VT conformance.
