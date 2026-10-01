---
title: Choose a Python PDF library
description: Match your PDF task to Fullbleed, WeasyPrint, Playwright, ReportLab, or pypdf using each project's documented scope.
---
# Choose a PDF library for your task

Start with the job: authoring a new document, printing browser content, and modifying an existing PDF need different APIs. This guide is maintained by Fullbleed and describes selection considerations, not a measured performance ranking.

| Your main task | Tools to evaluate | What to check |
| --- | --- | --- |
| Generate structured documents from Python and static HTML/CSS | Fullbleed, WeasyPrint | Template coverage, pagination, font handling, installation, and output validation |
| Print content whose JavaScript and browser layout matter | Playwright | Browser environment, print CSS, asset loading, and page readiness |
| Build documents through Python drawing and layout primitives | ReportLab | Canvas/Platypus APIs and the amount of layout code your team wants to own |
| Merge, split, crop, or extract text from existing PDFs | pypdf | The existing files' structures and the operations you need |

## When Fullbleed is a useful fit

Fullbleed combines a Rust document engine with a Python API, self-contained wheels, explicit assets, deterministic rendering, PNG previews, and structured diagnostics. Its compiled fixed and reflowing binding APIs support repeated document families. The current release is [MIT licensed](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.4.0/LICENSE).

Try your own HTML/CSS against the [coverage report](../css-coverage.md). Include long content, page breaks, glyph coverage, and every required output profile in the evaluation. Use the [complete examples](../examples.md) to establish a working baseline.

## Other projects' documented scope

- [WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/) is a Python HTML/CSS rendering engine designed for paginated documents and distributed under a BSD license. It is another browser-independent option to evaluate for static print content.
- [Playwright's PDF API](https://playwright.dev/python/docs/api/class-page#page-pdf) exposes PDF generation from a browser page, including print settings. It is relevant when browser behavior forms part of the required output.
- [ReportLab's documentation](https://docs.reportlab.com/reportlab/userguide/ch1_intro/) describes its Python PDF generation and document-layout APIs.
- [pypdf](https://pypdf.readthedocs.io/en/stable/) focuses on operations on existing PDFs, including page transformations, merging, splitting, text, and metadata extraction.

Check each project's current documentation for detailed capability and license terms. These descriptions were reviewed on October 1, 2026.

## A practical migration check

1. Collect representative documents and their input data.
2. Pin versions and font/image assets for both implementations.
3. Match page size, margins, headers, footers, and required metadata.
4. Compare page images and extracted content, including the longest records.
5. Run the relevant standards validators on the final files.
6. Measure complete jobs, including startup, compilation, and file writes.

Fullbleed's [retained performance evidence](performance.md) covers specified Fullbleed versions and fixtures. It does not establish speed or quality superiority over the tools listed here.
