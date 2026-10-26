# PDFs from JavaScript components and TSX

This fictional invoice uses reusable fields, work rows, payment notes and totals.
Both authoring styles share the records in `data.json` and the JavaScript
`StyleSheet` in `styles.mjs`. Neither template constructs HTML strings.

With Node.js 22 or newer:

```sh
npm ci
npm run check
npm run pdf
npm run pdf:tsx
```

Open `output/functions/invoice.pdf` and `output/tsx/invoice.pdf`. Each command
also writes native PNG previews, HTML/CSS exports and a repeat-render receipt.
The two PDF outputs are checked to be identical in the downloadable-project
verification. Change `data.json` to try another customer, paid status or work rows.
Amounts use safe integer cents, including negative credit adjustments.

`document.mjs` uses ordinary functions and needs no compiler. `invoice.tsx` is
the same template written with JSX and typed props. `render-tsx.mjs` compiles the
dedicated document with esbuild before rendering it. The renderer has no React
runtime dependency; esbuild and TypeScript are development tools.

The package is pinned to `fullbleed@0.8.2`, which wraps engine 2.5.37. The
`upstream.json` file records the source commit and exact source-file hashes.

Read the guide: https://docs.fullbleed.dev/guides/javascript-components/
