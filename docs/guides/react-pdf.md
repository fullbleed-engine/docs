---
title: Generate PDFs in React with live previews
description: Build a React and TypeScript PDF editor with HTML/CSS templates, automatic previews, cancellation, and downloads. Edit the complete project online or download its source.
---

# Generate PDFs in React

Connect a React form to a PDF preview with `fullbleed/browser`. Change a field
or an HTML/CSS template and the actual PDF updates after a short pause. The
engine renders in a browser worker; this starter needs no PDF server or account.

[Open the React demo](../assets/react-demo/index.html){ .md-button .md-button--primary }
[Edit source online](../assets/react-starter/edit-online.html){ .md-button }
[Download the React project](../assets/react-starter/project.zip){ .md-button }

The project includes a designed invoice, a three-page report, a React form and
template editor, and a reusable TypeScript hook. Its sample names, records, and
amounts are fictional. The code is MIT licensed, including commercial use.

## Edit the project online

Choose **Edit source online**, then **Open in StackBlitz** to load the complete
project without a local Node.js installation. Wait for **Ready** in the preview,
change the customer, and choose **Download PDF** after the preview updates.

Open `src/App.tsx` in the **Files** panel to change the React form, or edit
`src/invoice.html` and `src/invoice.css` to change the document. After editing a
template file, expand **Edit the HTML & CSS** in the preview and choose
**Reset this template** to load it. React preserves the preview's current edits
during development updates. The online launcher uses the same source files and
lockfile as the ZIP below. It opens a temporary project in StackBlitz;
save or export your changes there if you want to keep them.

<span id="run-the-project"></span>

## Run the project locally

Extract the ZIP. With Node.js 22.12 or newer, open a terminal in
`fullbleed-react-starter` and run:

```sh
npm ci
npm run dev
```

Open the localhost URL printed by Vite. Edit the customer, reference, or ink
color and wait for **Ready**. **Download PDF** saves the generated document.
Turn off **Update automatically** to generate only when you choose **Generate PDF**.
**Cancel** stops a pending preview or active render.

The lockfile pins Fullbleed npm **0.3.2** / engine **2.5.11**, React **19.3.0**,
TypeScript **7.0.2**, and Vite **8.3.2**. The ZIP includes its source and lockfile;
the build downloads the published dependencies and copies their verified runtime.

## Customize the document

Open **Edit the HTML & CSS** to paste a print template. Changes stay in the tab
until reload or closing the editor. Keep a design by editing these project files:

| File | Purpose |
| --- | --- |
| `src/App.tsx` | React fields, structured data, template selection, and preview UI |
| `src/usePdfPreview.ts` | Rendering, cancellation, stale-result protection, and URL cleanup |
| `src/invoice.html` / `src/invoice.css` | Invoice print layout |
| `src/report.html` / `src/report.css` | Three-page report print layout |
| `src/style.css` | The application interface |

The invoice fills `{{customer}}` and `{{reference}}` in HTML and `{{ink}}` in CSS.
The app escapes customer text before inserting it. Line items, amounts, dates,
and addresses are fixed samples: replace them with your data and calculations.

Use [supported Fullbleed print CSS](../css-coverage.md). The SDK consumes static
HTML/CSS rather than capturing the React page. Document scripts do not execute,
and document URLs do not fetch remote resources. Pass extra font or image bytes
through the SDK's `fonts` and `assets` options.

## Reuse the hook in an existing React app

Install the package and copy its runtime into your app's static directory:

```sh
npm install --save-exact fullbleed@0.3.2
npx fullbleed-browser-assets public/fullbleed
```

Copy `src/usePdfPreview.ts` from the project into your client app. Memoize its
input so unrelated component updates do not schedule a new render:

```tsx
import { useMemo } from 'react';
import { usePdfPreview } from './usePdfPreview';

export function PdfDownload({ html, css }: { html: string; css: string }) {
  const input = useMemo(() => ({
    html, css, previewDpi: 96, maxPages: 20, timeoutMs: 30_000,
  }), [html, css]);
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
next edit or explicit `generate()` call. Changing preview mode resets output.

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
independently checks their text and page sizes, and compares the default invoice
and report bytes with the installed Node package. It also checks automatic and
on-demand modes, fast edits, cancellation, recovery, unmount/remount, URL cleanup,
and 1440/390/320px layouts. The docs build installs and checks the exact ZIP.
An edited-template check verifies unembedded Helvetica faces in the PDF and
visible text in its browser preview.

These fixtures do not establish compatibility with every browser, device, or
hosting policy. WebKit testing is not branded Safari certification. Worker
observations count browser API handles; browsers expose no native thread-exit
promise. Bound concurrently mounted renderers for the devices you support.

This browser entry provides ordinary PDFs and previews, not PDF/A, PDF/UA,
PDF/X, or VDP options. For a server-side React framework route, use the
[Next.js PDF download starter](nextjs-pdf.md).
