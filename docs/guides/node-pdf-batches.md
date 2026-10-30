---
title: Generate batch PDFs from one template in Node.js
description: Generate a combined PDF from JavaScript records, let longer notices reflow, and use per-record page ranges and character reports in your application.
---

# Generate batch PDFs in Node.js

Use `renderPdfBatch()` when many records share a design: account notices, letters,
invoices, or statements. The engine compiles the template once per request and
returns one PDF in record order. Longer records can wrap onto additional pages.

This guide uses **Node package 0.9.0**, powered by **Fullbleed 2.5.46**. With
Node.js 22 or newer, install the pinned version:

```sh
npm install --save-exact fullbleed@0.9.0
```

For a Python application, use the [Python compiled-batch guide](compiled-batches.md).

## Generate account notices

Save this as `notices.mjs`, then run `node notices.mjs`. The first account has a
short notice; the second has a longer message. All data is fictional.

```javascript
import { writeFile } from 'node:fs/promises';
import { renderPdfBatch } from 'fullbleed';

const records = [
  { account: '1042', message: 'Your account is up to date. Thank you.' },
  {
    account: '1043',
    message: 'Your scheduled account review includes the following information. '.repeat(90),
  },
];

const result = await renderPdfBatch({
  html: `<!doctype html><html lang="en"><body>
    <p class="label">ACCOUNT NOTICE</p>
    <h1>Account {{account}}</h1>
    <p class="message">{{message}}</p>
    </body></html>`,
  css: `@page { size: A5; margin: 18mm }
    body { font-family: Inter; font-size: 11pt; color: #23342f }
    .label { color: #47745d; font-size: 8pt; letter-spacing: 1pt }
    h1 { font-size: 25pt; margin: 8pt 0 18pt }
    .message { line-height: 1.5 }`,
  records,
  maxPages: 20,
  timeoutMs: 30_000,
});

await writeFile('notices.pdf', result.pdf);
await writeFile('record-pages.json', JSON.stringify(result.records, null, 2));
for (const row of result.records) {
  const first = row.pageOffset + 1;
  const last = row.pageOffset + row.pageCount;
  console.log(`Account ${records[row.recordIndex].account}: pages ${first}–${last}`);
}
```

Open `notices.pdf`. The console and `record-pages.json` identify each account's
page range: account 1042 occupies page 1, and account 1043 occupies pages 2–5.
`recordIndex` and `pageOffset` are zero-based; the printed ranges above are one-based.

Records contain plain strings. Format numbers and dates in your application;
characters such as `<`, `>` and `&` remain literal text. Every record must have
the same own enumerable fields, exactly matching the template's text bindings.
Changes to image sources, attributes, CSS, or document structure use the ordinary
rendering API or a different template.

## Choose how each record flows

The default `layout: 'reflow'` lays out each record with its values, so a long
notice can take more pages than a short one. Each returned `pageCount` describes
the actual result.

Use `layout: 'fixed'` when values fit a reviewed template's geometry. Fixed mode
retains the compiled layout and selected fonts. Review the PDF with realistic
data before using that mode for a delivery workflow.

Compilation is scoped to one call. A later `renderPdfBatch()` call compiles its
template again; JavaScript does not expose a persistent compiled-template handle.

## Use the reports in your application

The result contains `pdf`, `pages`, and `records`. Each record reports its
`recordIndex`, `pageOffset`, `pageCount`, and `missingGlyphs`.

Missing characters reject the batch by default with `MISSING_GLYPHS`. With
`allowMissingGlyphs: true`, a PDF is returned and each affected record identifies
the character's `codepoint`, `char`, occurrence `count`, and `fontsTried`. That
last field identifies the first selected registered font where the character was
absent. The top-level `missingGlyphs` count is the number of distinct missing
code points across the entire batch.

These diagnostics cover the selected registered font chain. They exclude
unembedded Standard 14 fonts and text inside images, and do not establish correct
shaping, line fit, accessibility, or PDF conformance. Keep visual checks alongside
the reports when adapting a design.

For order events or scheduled statements, let your application's durable job
system collect and format the records. Render the batch, inspect the result, then
store its PDF and page map together. A failed call does not deliver a partial PDF.

## Bound work across requests

Use one [render queue](node-render-queue.md) per application process and call its
`renderPdfBatch()` method with the same options. A whole batch occupies one queue
slot. Queue deadlines include waiting time, and cancellation waits for the worker
or child process to stop. The queue controls concurrent jobs; your application
owns scheduling, retries, authentication, and delivery.

Up to 10,000 records are accepted. HTML, CSS, and all record keys and values share
a 4,000,000-byte UTF-8 budget. `maxPages` applies to the combined PDF. Records are
copied when the request is accepted, before asynchronous rendering begins.

The PDF, reports, and optional previews stay in memory. Split larger workloads
into batches that fit your host's memory and CPU budget. Use `timeoutMs` and an
`AbortSignal` to bound work; use the existing `isolation: 'process'` option when
your Node host permits child processes and that isolation suits the application.

## Other JavaScript authoring paths

[Component-authored templates](javascript-components.md) can use
`document.renderPdf(renderPdfBatch, { records })`; component authoring remains
alpha. The same batch method is available on the
[browser renderer](browser-pdf.md), and `fullbleed/cloudflare` exports
`renderPdfBatch` for [Workers](cloudflare-pdf.md). Workers have a smaller
1,000,000-byte combined source budget. The package's Workers verification covers
local workerd, so qualify deployment against your actual hosting limits.

[Node.js quickstart](../getting-started/node.md) ·
[Batch API reference](https://github.com/fullbleed-engine/fullbleed-node/tree/v0.9.0#generate-a-batch-from-one-template)
