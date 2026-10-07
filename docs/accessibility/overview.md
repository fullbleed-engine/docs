---
description: Author semantic documents, generate tagged PDF output, and retain accessibility checks with Fullbleed.
---
# Tagged PDFs and accessibility checks

Fullbleed provides semantic Python components, tagged PDF output profiles, inspection, and accessibility verification tools. Start with clear headings, logical reading order, meaningful table headers, document language, and appropriate alternative text.

For .NET, use the [editable C# tagged-notice starter](../guides/csharp-tagged-pdf.md).
It includes styled HTML/CSS, explicit fonts, a scoped table and a captioned
illustration, with PDF/UA-1 and PDF/UA-2 output and retained verification.

## Try the checked example

[Open the service-notice PDF](../assets/examples/accessible.pdf) · [View HTML](../assets/examples/accessible.html) · [View CSS](../assets/examples/accessible.css)

The [workflow suite](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/agent_workflows) creates this notice with the `pdfua1` profile and an embedded Inter font. Its checks cover expected text, profile markers, structure-tree and language presence, and reported seed blockers.

```bash
python examples/agent_workflows/run_examples.py --out output/examples --json
python -m fullbleed inspect pdf output/examples/accessible/document.pdf --json
```

## Author, inspect, and verify

1. Create semantic content with the [component and accessibility API](../ui/overview.md).
2. Choose the output profile and register embeddable fonts.
3. Render and inspect the finalized PDF and every page preview.
4. Run the applicable validation tools and retain their reports alongside the exact PDF.
5. Review content-dependent requirements such as reading order, alternative text, and contrast.

Selecting a profile or receiving a passing structural check does not establish full PDF/UA, WCAG, or legal compliance for every document. Validate your final artifact against the requirements that apply to your use case.

## Evidence and current scope

The [2.4.0 validation report](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.4.0/docs/release/2.4.0-validation-report.md) records the release's profile checks. Download the retained evidence from the [release assets](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.4.0).

Use `python -m fullbleed agent-contract --format json` to discover the profiles and verification commands supported by your installed version.
