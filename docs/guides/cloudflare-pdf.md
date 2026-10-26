---
title: Generate PDFs in Cloudflare Workers with HTML and CSS
description: Render PDF invoices inside a Cloudflare Worker with Fullbleed's bundled WebAssembly engine and fonts. Download an editable invoice endpoint with local workerd tests.
---
# Generate PDFs in Cloudflare Workers

Import `renderPdf` from `fullbleed/cloudflare` to turn static HTML/CSS into PDF
bytes inside a Worker. Wrangler bundles the engine and fonts with your code.
The renderer uses an in-memory filesystem; document content does not need to
leave the Worker for a PDF service.

The adapter is verified in **local workerd on Windows and Linux**. A
[hosted Playground smoke test](#hosted-playground-smoke-test) also reproduces the
starter's PDFs. Production CPU, memory, startup behavior and Free-plan suitability
remain unqualified. Measure representative documents in your deployment before
choosing a plan or workload limits.
[Cloudflare's platform limits](https://developers.cloudflare.com/workers/platform/limits/)
apply to the entire isolate, including WebAssembly memory.

## Run a complete invoice endpoint

[Download the Workers invoice starter](../assets/cloudflare-starter/project.zip){ .md-button .md-button--primary }
[Open the generated PDF](../assets/cloudflare-starter/invoice.pdf){ .md-button }
[See a five-page invoice](../assets/cloudflare-starter/long-invoice.pdf){ .md-button }

[![Northstar Studio invoice with forest-green typography, project progress bars and a dark-green total panel.](../assets/cloudflare-starter/invoice.png)](../assets/cloudflare-starter/invoice.pdf)

The project uses **npm package 0.8.1**, **engine 2.5.35**, and **Wrangler 4.151.3**.
It accepts structured invoice JSON, applies an editable template, and returns a
PDF attachment. The sample organization and customer are fictional.

Extract the ZIP and, with Node.js 22 or newer, run:

```sh
npm ci --ignore-scripts
npm test
npm run build
npm run dev
```

`build` produces a local bundle without deploying. `dev` starts the local Worker
at `http://127.0.0.1:8787`; no Cloudflare account is needed. In a second terminal:

```sh
curl --fail-with-body http://127.0.0.1:8787/invoice \
  -H "Content-Type: application/json" \
  --data-binary @sample.json --output invoice.pdf
```

Open `invoice.pdf`. On Windows PowerShell, use `curl.exe` and put that command on
one line. Run `npm run test:worker` while the server is running to check sample,
zero-total, maximum-total, long, escaped-text and invalid invoices. The test uses
synthetic data and saves its PDFs in `output/`.

## Use your own HTML and CSS

The adapter accepts the same static document sources as the Node renderer:

```js
import { renderPdf } from 'fullbleed/cloudflare';

export default {
  async fetch() {
    const result = await renderPdf({
      html: '<h1>Invoice NS-1042</h1><p>Design and delivery: $1,870.00</p>',
      css: '@page { size: A4; margin: 20mm } h1 { color: #173b35 }',
      maxPages: 5,
    });
    return new Response(result.pdf, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="invoice.pdf"',
        'Cache-Control': 'no-store',
      },
    });
  },
};
```

This is a complete Worker entry file. Keep document input behind your
application's authorization and workload limits. HTML scripts do not
run, and document URLs do not fetch remote resources. Supply images and custom
fonts as byte arrays through `assets` and `fonts`.

Add this rule to an existing Wrangler configuration so the bundled TrueType
fonts become data modules:

```json
{
  "rules": [{ "type": "Data", "globs": ["**/*.ttf"], "fallthrough": false }]
}
```

Wrangler already recognizes the engine's compiled `.wasm` import. The download
includes the complete configuration; see Cloudflare's
[WebAssembly module documentation](https://developers.cloudflare.com/workers/runtime-apis/webassembly/javascript/)
for the runtime mechanism.

## Edit the starter's design

| File | What to change |
| --- | --- |
| `sample.json` | Customer, reference, dates, paid status, and line items. |
| `src/document.mjs` | Headings, labels, document sections, and table rows. |
| `src/styles.mjs` | Page geometry, fonts, colors, spacing, and class rules. |
| `src/handler.mjs` | Input schema, limits, and download headers. |
| `src/index.mjs` | The platform renderer import. |

This template uses [JavaScript function components](javascript-components.md).
`className` adds an HTML class, and a matching rule in the document's
`StyleSheet` supplies its styling. `Invoice({ data }).renderPdf(renderPdf)` passes
the generated HTML and CSS to the Workers renderer. You can replace that call
with your own HTML/CSS template.

For standalone HTML, use `Invoice({ data }).toHtml({ includeStyles: true })`.
The embedded stylesheet also renders to PDF with `css: ''` and
`defaultStyles: false`. `includeStyles: false` exports HTML without styles.

The sample accepts 1–30 rows and at most 32 KiB of JSON. Rates are nonnegative
integer cents, quantities are integers, dates use `YYYY-MM-DD`, and the total is
limited to $999,999.99. It uses USD and does not calculate tax. Tables flow across
pages, with a ten-page render limit. Change these bounds together with layout
tests for your own documents.

## Connect it to your application

The starter disables `workers_dev` and `preview_urls` and defines no public
route. Its local endpoint has no authentication. Configure an authenticated
application route or private service binding before deployment, apply rate and
concurrency limits, and keep invoice data out of logs. The handler stores no
invoices or PDFs and returns `Cache-Control: no-store`.

Rendering is synchronous inside the isolate and returns a settled Promise.
Each call gets a fresh engine instance, but that does not guarantee that previous
allocations have already been garbage-collected. `timeoutMs`, `signal`, and
`isolation` are rejected on this entry. Cloudflare enforces CPU and memory limits;
page and input limits are not guarantees about either resource.

The adapter defaults to 20 pages, caps HTML/CSS at 1,000,000 UTF-8 bytes, and
caps caller-provided fonts and assets at 8 MiB combined. Optional previews use
additional memory. These are ordinary PDFs; this entry does not expose PDF/A,
PDF/UA, PDF/X, or VDP profiles.

## Verification and source

The release checks the installed npm tarball in real local workerd, compares
PDF and preview bytes with Node, and exercises custom fonts, SVG assets,
components, embedded styles, input limits, missing glyphs and failure recovery.
The downloadable project is also installed from its lockfile and exercised over
local HTTP. Independent readers check the retained PDF contents, and the
sample and long-invoice layouts are visually reviewed.

### Hosted Playground smoke test

The earlier 0.8.0 starter was exercised in Cloudflare's
[account-free Workers Playground](https://developers.cloudflare.com/workers/playground/)
on October 21, 2026 (UTC). Six invoices, including a five-page invoice and recovery
after invalid requests, matched the local PDF bytes exactly. An independent
reader checked the ten output pages and expected text. Ten invalid inputs,
method restrictions and unknown routes returned the expected responses. The
temporary preview was replaced with a `410` response after the checks.

This establishes hosted sandbox behavior for those fixtures. CPU and memory were
not measured, and this was not a load test or a production account deployment.
The Playground's
[service source at the checked revision](https://github.com/cloudflare/workers-sdk/blob/f43e2e61093b3218a48691dc76ce7f463a2123ce/packages/playground-preview-worker/src/user.do.ts#L169)
selects an `unbound` usage model, so this result does not establish Free-plan
suitability. The [hosted verification record](../assets/cloudflare-playground-verification.json)
retains the module and PDF hashes and source references.

[Download source manifest](../assets/cloudflare-starter/source.json) ·
[Local verification record](../assets/cloudflare-starter/verification.json) ·
[SDK guide](https://github.com/fullbleed-engine/fullbleed-node/blob/v0.8.1/docs/cloudflare.md) ·
[Release evidence](https://github.com/fullbleed-engine/fullbleed-node/releases/tag/v0.8.1)
