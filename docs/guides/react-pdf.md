---
title: React PDF components with live previews
description: Build PDFs with typed components in React. Edit invoice data, preview and download locally, or customize the JSX document and styles in the complete online project.
---

# Build PDFs with components in React

Write a PDF template with typed function components and connect it to a React
form. Change line items, mark an invoice paid, or choose a color and watch the
actual PDF update. Fullbleed renders the document in a browser worker; the
starter needs no PDF server or account.

[Open the component demo](../assets/react-demo/index.html){ .md-button .md-button--primary }
[Edit source online](../assets/react-starter/edit-online.html){ .md-button }
[Download the React project](../assets/react-starter/project.zip){ .md-button }

The project uses **fullbleed 0.8.4** with engine **2.5.40**. Its default invoice
uses typed props, mapped rows, conditional paid text and composed style maps.
Text is escaped by the authoring layer; amounts are calculated in integer cents.
The form accepts up to 20 rows and whole hours, including negative rates for
credits. All records and amounts are fictional. The source is MIT licensed.

## Edit the component online

Choose **Edit source online**, then **Open in StackBlitz** to load the complete
project without a local Node.js installation. Wait for **Ready** in the preview,
change a row or the customer, and choose **Download PDF** after it updates.

The source editor opens `src/documents/Invoice.tsx`. Change a heading or compose
another print component there. Edit `src/documents/invoiceStyles.ts` for layout
and typography, `src/documents/data.ts` for the data model, or `src/App.tsx` for
the React form. TSX and stylesheet edits update the preview while preserving
the current form values. The launcher sends the same source files and lockfile
as the ZIP. Save or export your changes in StackBlitz to keep them.

The design selector also offers the existing **HTML/CSS invoice** and
**Community report**. Their **Edit the HTML & CSS** panel accepts templates,
with source in `src/invoice.html`, `src/invoice.css`, `src/report.html` and
`src/report.css`. Use **Reset this template** after editing one of those files
to load it into a preview that already has local edits.

## React for the app, components for the document

`src/App.tsx` uses React's JSX runtime. The print file begins with
`/** @jsxImportSource fullbleed/ui */`, selecting Fullbleed for that file.
Call `Invoice({ data })` to compose the document, then pass it to the preview
hook. The document functions are synchronous; fetch data and use React hooks
in the surrounding application.

The Vite config excludes print modules from React Fast Refresh boundaries:

```javascript
plugins: [react({ exclude: [/node_modules/, /[\\/]src[\\/]documents[\\/]/] })]
```

This lets edits to imported print styles propagate to the form and regenerate
the PDF. See the React plugin's [exclude option](https://github.com/vitejs/vite-plugin-react/tree/main/packages/plugin-react#exclude).
The complete project includes this configuration. The
[JavaScript component guide](javascript-components.md) explains the authoring
API, props, children and reusable styles in more detail.

<span id="run-the-project"></span>

## Run the project locally

Extract the ZIP. With Node.js 22.13+ on the 22.x line, or Node.js 23.5+
(including 24.x), open a terminal in
`fullbleed-react-starter` and run:

```sh
npm ci
npm run dev
```

Keep the supplied `package-lock.json` and `overrides` in `package.json`. They
pin Vite's WebAssembly bundler runtime so the same project also starts in
StackBlitz.

Open the localhost URL printed by Vite. Edit the customer, reference, or ink
color and wait for **Ready**. **Download PDF** saves the generated document.
Turn off **Update automatically** to generate only when you choose **Generate PDF**.
**Cancel** stops a pending preview or active render.

The lockfile pins Fullbleed npm **0.8.4** / engine **2.5.40**, React **19.3.0**,
TypeScript **7.0.2**, and Vite **8.3.2**. The ZIP includes its source and lockfile;
the build downloads the published dependencies and copies their verified runtime.

## Customize the document

For class-based styling, read [how `className`, selectors and document styles connect](javascript-components.md#class-names-and-styles).
In this starter, `className="total"` in `src/documents/Invoice.tsx` matches
the `'.total'` rule in `src/documents/invoiceStyles.ts`. `Invoice` imports that
sheet, composes the chosen ink color overrides, and attaches it through
`<Document styles={...}>`. `src/style.css`
styles the React interface; print rules belong to the document's stylesheet.

The invoice reference has its own `className="invoice-reference"` rule with
`letterSpacing: "0pt"` and `textTransform: "none"`. Keep those overrides when
styling the surrounding label so references remain searchable and retain their
original case in the PDF.

Use **See the document component** to inspect the source while trying the form.
Keep your layout and data changes in these project files:

| File | Purpose |
| --- | --- |
| `src/App.tsx` | React fields, structured data, template selection, and preview UI |
| `src/usePdfPreview.ts` | Rendering, cancellation, stale-result protection, and URL cleanup |
| `src/documents/Invoice.tsx` | Typed print components, rows, totals and conditional content |
| `src/documents/invoiceStyles.ts` | Attached print style maps and layout rules |
| `src/documents/data.ts` | Sample records, integer-cents formatting and form validation |
| `src/invoice.html` / `src/invoice.css` | Optional HTML/CSS invoice design |
| `src/report.html` / `src/report.css` | Optional three-page report design |
| `src/style.css` | The application interface |

The component invoice accepts a typed data object and an ink color. Its rows,
totals and payment text respond to the form. Supply your own dates and records
when building an application. The optional HTML invoice fills `{{customer}}`
and `{{reference}}` in HTML and `{{ink}}` in CSS, with escaped customer text.

Use [supported Fullbleed print CSS](../css-coverage.md). The SDK consumes static
HTML/CSS rather than capturing the React page. Document scripts do not execute,
and document URLs do not fetch remote resources. Pass extra font or image bytes
through the SDK's `fonts` and `assets` options.

## Reuse the hook in an existing React app

For a smaller runnable example, use
[the focused preview and download recipe](react-pdf-preview-lifecycle.md).
It includes a complete form, invalid-input handling, manual mode, cancellation,
and editor cleanup, with the same styled component invoice.

Install the package and copy its runtime into your app's static directory:

```sh
npm install --save-exact fullbleed@0.8.4
npx fullbleed-browser-assets public/fullbleed
```

Copy `src/usePdfPreview.ts` and the `src/documents/` directory into your client app,
or replace `Invoice` with your own document factory. Memoize the
input so unrelated component updates do not schedule a new render:

```tsx
import { useMemo } from 'react';
import { usePdfPreview } from './usePdfPreview';
import { Invoice } from './documents/Invoice';
import type { InvoiceData } from './documents/data';

export function PdfDownload({ data }: { data: InvoiceData }) {
  const input = useMemo(() => ({
    document: Invoice({ data }), previewDpi: 96, maxPages: 20, timeoutMs: 30_000,
  }), [data]);
  const pdf = usePdfPreview(input, '/fullbleed/');

  return <section>
    <p role="status">{pdf.error?.message ?? pdf.status}</p>
    <button onClick={pdf.cancel}>Cancel</button>
    {pdf.result && <>
      <a href={pdf.result.url} download="document.pdf">Download PDF</a>
      {pdf.result.previews.map((url, index) =>
        <img key={url} src={url} alt={`PDF page ${index + 1}`} />)}
    </>}
  </section>;
}
```

The default delay is 450 ms. Use the third argument `{ auto: false }` and call
`pdf.generate()` from a button for on-demand rendering. `{ delayMs: 800 }` waits
longer between edits. A new input immediately hides the old download, cancels
the preceding job, and schedules the next preview. Cancel stops work until the
next edit or explicit `generate()` call. Changing preview mode resets output. Pass `null` while inputs are invalid to
clear old output without starting a worker. The hook also accepts
`{ html, css, ...options }` for existing templates.

The hook releases old PDF/PNG Blob URLs and aborts active work on unmount. It
ignores obsolete results even when requests settle out of order. The starter
uses React `StrictMode`, including the extra setup/cleanup cycle in development;
see React's [Effect cleanup guidance](https://react.dev/reference/react/useEffect#connecting-to-an-external-system).
Use it in a client component with browser APIs available.

## Build and deploy

```sh
npm run build
npm run preview
```

Upload the complete `dist/` directory to a static HTTPS host. The example uses
relative paths and is checked under a nested URL prefix. In another app, set
the hook's asset URL to your same-origin runtime directory, ending in `/`.
Keep the client, worker, engine, fonts, manifest, and notices together.

The deployed app needs no Node process. Its first render loads the engine and
fonts from the static host; document inputs stay in the same browser. It needs
HTTPS or localhost, Web Workers, WebAssembly, and Web Crypto. The
[browser SDK guide](browser-pdf.md) covers hosting, custom assets, and API limits.

## What is checked

The [source workflow](https://github.com/fullbleed-engine/fullbleed-node/actions/workflows/react-starter.yml)
checks the built project in Chrome, Firefox, and Playwright WebKit, and checks a
React development build with StrictMode enabled. It downloads real PDFs,
independently checks their text and page sizes, and compares six component
cases with the installed Node package: default, paid, edited, empty, credit,
and a twenty-row invoice across three pages. Every component preview matches
the Node output too. Default and mixed-case references must also survive exact
text extraction and case-sensitive PDF search without whitespace normalization.
The existing HTML invoice and report keep their byte checks. It also checks automatic and
on-demand modes, fast edits, cancellation, recovery, unmount/remount, URL cleanup,
and 1440/390/320px layouts. The docs build installs and checks the exact ZIP.
A real Vite development-server check edits TSX and stylesheet source, verifies
the resulting PDFs and preserves the React form values.
An edited-template check verifies unembedded Helvetica faces in the PDF and
visible text in its browser preview.

These fixtures do not establish compatibility with every browser, device, or
hosting policy. WebKit testing is not branded Safari certification. Worker
observations count browser API handles; browsers expose no native thread-exit
promise. Bound concurrently mounted renderers for the devices you support.

This browser entry provides ordinary PDFs and previews, not PDF/A, PDF/UA,
PDF/X, or VDP options. For a server-side React framework route, use the
[Next.js PDF download starter](nextjs-pdf.md).

The editor checks also paste templates for sibling counter resets, nested clipping,
SVG border-image centers, and decorated floated initials. They inspect downloaded
PDF text and independently specified colors in both the PDF and its preview.

Nested quotation checks cover inline, block, and contents layouts through the
actual editor. They check both PDF readers, page size, and visible preview output.
The [retained starter verification](../assets/browser-starters-084-verification.json)
records these cases and the unchanged invoice and report downloads.
