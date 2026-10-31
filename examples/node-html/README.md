# Static HTML to PDF in Node.js

Render the supplied order documents with Fullbleed, then optionally compare the
same HTML, font and logo with Puppeteer. All businesses, orders and addresses
are fictional. This example targets ordinary PDFs; it is not an accessibility,
archival or print-profile certification.

## Render with Fullbleed

Use Node.js 22.12 or newer. From this project's directory:

```sh
npm ci --ignore-scripts
npm run render
```

Open `output/fullbleed/short/document.pdf` and
`output/fullbleed/long/document.pdf`. Each folder also contains native PNG
previews and the complete HTML passed to the renderer. `render.json` records
the actual engine version, page counts and output hashes.

The root package installs Fullbleed 0.9.0, with engine 2.5.46. It does not
install or launch a browser. Puppeteer is confined to the optional `reference`
folder.

## Make it your document

- Edit `records.json` to change customers, line items and integer-cent prices.
  `document.mjs` escapes text and computes totals before rendering.
- Edit `template.html` for markup and `print.css` for typography and layout.
  The loader places the stylesheet in a `<style>` element in the final HTML.
- Replace `assets/logo.svg` or the regular/bold Source Sans 3 files in `fonts`
  with assets you may distribute. The fonts' OFL license and pinned source
  manifest are included. Both renderers use those exact local bytes.
- The HTML references `assets/logo.svg`; the Fullbleed asset map calls it
  `logo.svg`. The CSS aliases use `Brand-Regular.ttf` and `Brand-Bold.ttf`;
  the supplied named-font objects use the same filenames. The separate
  `@font-face` rules map weights 400 and 700. Neither relies on system fonts.

Render just one record set or choose an output directory:

```sh
node render.mjs short
node render.mjs long "output/my order"
```

Keep the stylesheet's page margins, flowing table and `break-inside: avoid`
closing section when adding rows. Review every output page after changing
content. A single row or closing section taller than a page needs its own
layout decision.

## Optional Puppeteer reference

This separate package installs Puppeteer and its compatible Chrome download.
It is only needed to evaluate a migration:

```sh
cd reference
npm ci
npm run render
```

Open `../output/chromium/short/document.pdf` and
`../output/chromium/long/document.pdf`. The reference serves only the document
and supplied assets on a temporary loopback HTTP server, waits for the local
font/images, and prints with `printBackground` and `preferCSSPageSize` enabled.
It records the actual Chromium version and asset requests in `render.json`.
The server and temporary browser close when rendering finishes.

If a Chrome build compatible with the pinned Puppeteer is already provisioned
by your CI environment, the reference accepts its executable path in
`FULLBLEED_CHROME_PATH`. Its installation can then use
`PUPPETEER_SKIP_DOWNLOAD=true` to skip Puppeteer's separate browser download.
Normal use needs neither setting. Consult Puppeteer's installation guide for
your operating system's browser dependencies.

Compare the pages and content, not just the file sizes. Fullbleed and Chromium
have different layout engines; this project does not promise equal pagination
or identical pixels. Keep a browser when your document depends on page
JavaScript, live application state, or browser-specific behavior.

[Migration guide](https://docs.fullbleed.dev/guides/node-html-to-pdf/) ·
[Puppeteer PDF guide](https://pptr.dev/guides/pdf-generation) ·
[Fullbleed CSS coverage](https://docs.fullbleed.dev/css-coverage/)
