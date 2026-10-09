---
title: Generate PDFs in Vue with reactive previews
description: Build a Vue 3 and TypeScript PDF editor with HTML/CSS templates, automatic previews, cancellation, and downloads. Reuse the composable or edit the complete starter online.
---

# Generate PDFs in Vue

Connect a Vue form to a PDF preview with `fullbleed/browser`. Change a field
or an HTML/CSS template and the actual PDF updates after a short pause. This
starter renders in a browser worker and needs no PDF server or account.

[Open the Vue demo](../assets/vue-demo/index.html){ .md-button .md-button--primary }
[Edit source online](../assets/vue-starter/edit-online.html){ .md-button }
[Download the Vue project](../assets/vue-starter/project.zip){ .md-button }

The project includes a designed invoice, a three-page report, a Vue form and
template editor, and a reusable TypeScript composable. Sample names, records,
and amounts are fictional. The code is MIT licensed, including commercial use.

## Edit the project online

Choose **Edit source online**, then **Open in StackBlitz** to load the complete
project without a local Node.js installation. Wait for **Ready** in the preview,
change the customer, and choose **Download PDF** after the preview updates.

Open `src/DocumentEditor.vue` in the **Files** panel to change the Vue form.
Edit `src/invoice.html` and `src/invoice.css` to change the print layout.
Saving a print-template file reloads the document component and resets its
form values and temporary editor changes.
The online launcher submits the same source files and lockfile as the ZIP.
It opens a temporary project; save or export changes in StackBlitz to keep them.

<span id="run-the-project"></span>

## Run the project locally

Extract the ZIP. With Node.js 22.12 or newer, open a terminal in
`fullbleed-vue-starter` and run:

```sh
npm ci
npm run dev
```

Open the localhost URL printed by Vite. Edit the customer, reference, or ink
color and wait for **Ready**, then choose **Download PDF**. Turn off **Update
automatically** to generate on demand. **Cancel** stops a pending preview or
active render. **Close editor** releases its resources; reopening starts fresh.

The lockfile pins Fullbleed npm **0.4.1** / engine **2.5.22**, Vue **3.5.43**,
TypeScript **6.0.3**, and Vite **8.3.2**. The build downloads the published
dependencies and copies their verified runtime. TypeScript 6 is pinned for
compatibility with the project's `vue-tsc` type checker.

## Customize the document

Expand **Edit the HTML & CSS** to paste a print template. These edits stay in
the tab until reload or closing the editor. Keep a layout in the source files:

| File | Purpose |
| --- | --- |
| `src/DocumentEditor.vue` | Form fields, template state, validation, and preview UI |
| `src/usePdfPreview.ts` | Reactive rendering, cancellation, stale-result protection, and URL cleanup |
| `src/App.vue` | Application shell and editor mount/unmount |
| `src/invoice.html` / `src/invoice.css` | Invoice print layout |
| `src/report.html` / `src/report.css` | Three-page report print layout |
| `src/style.css` | Application interface |

The invoice fills `{{customer}}` and `{{reference}}` in HTML and `{{ink}}` in CSS.
The app escapes customer text before inserting it and validates the hex color.
Line items, totals, addresses, and dates are fixed samples: replace them with
your data and calculations.

Print templates are separate from Vue component templates. Fullbleed consumes
static HTML/CSS and does not capture the Vue page. Use
[supported print CSS](../css-coverage.md). Document scripts do not execute, and
document URLs do not fetch remote resources. Pass extra font or image bytes
through the SDK's `fonts` and `assets` options.

## Reuse the composable in an existing Vue app

Install the package and copy its runtime into your static directory:

```sh
npm install --save-exact fullbleed@0.4.1
npx fullbleed-browser-assets public/fullbleed
```

Copy `src/usePdfPreview.ts` from the project. Call it during component setup
with a computed input or a getter that reads reactive values:

```vue
<script setup lang="ts">
import { computed } from 'vue';
import { usePdfPreview } from './usePdfPreview';

const props = defineProps<{ html: string; css: string }>();
const input = computed(() => ({
  html: props.html, css: props.css,
  previewDpi: 96, maxPages: 20, timeoutMs: 30_000,
}));
const { status, result, error, generate, cancel } = usePdfPreview(input, '/fullbleed/');
</script>

<template>
  <section>
    <button @click="generate">Generate PDF</button>
    <button @click="cancel">Cancel</button>
    <p role="status">{{ error?.message ?? status }}</p>
    <template v-if="result">
      <a :href="result.url" download="document.pdf">Download PDF</a>
      <img v-for="(url, index) in result.previews" :key="url"
        :src="url" :alt="`PDF page ${index + 1}`" />
    </template>
  </section>
</template>
```

The returned values are refs and can be destructured. For a ref containing an
input object, replace the object when changing it; the composable does not
deeply watch font or asset arrays.

Its default delay is 450 ms. Set `{ auto: false }` to generate only on demand,
or pass a boolean ref as `auto` to switch modes. `{ delayMs: 800 }` waits longer
after edits. Cancel stops work until the next input change or `generate()` call.
Changing preview mode also resets output.

The watcher invalidates downloads synchronously, aborts superseded work, and
ignores obsolete results. Replaced PDF/PNG Blob URLs are revoked. Rendering
starts after mount; scope disposal stops the watcher and releases its resources.
See Vue's [composable lifecycle guidance](https://vuejs.org/guide/reusability/composables.html).
Use it in a browser component. This example does not handle server rendering
or `KeepAlive` deactivation.

## Build and deploy

```sh
npm run build
npm run preview
```

Upload the entire `dist/` directory to a static HTTPS host. Relative paths
support nested deployment URLs. In another app, set the composable's asset URL
to your same-origin runtime directory, ending in `/`. Deploy the client, worker,
engine, fonts, manifest, and notices together.

The deployed app needs no Node process. Its first render loads the engine and
fonts; document inputs stay in that browser. It needs HTTPS or localhost,
Web Workers, WebAssembly, and Web Crypto. The [browser SDK guide](browser-pdf.md)
covers hosting, custom assets, and API limits.

## What is checked

The [source workflow](https://github.com/fullbleed-engine/fullbleed-node/actions/workflows/vue-starter.yml)
builds and checks the project in Chrome, Firefox, and Playwright WebKit.
It downloads real PDFs, independently checks their text and page sizes, and
compares default PDF and preview bytes with the installed Node package. It
exercises fast edits, both preview modes, cancellation, runtime-outage recovery,
template editing, unmount/remount, URL cleanup, and 1440/390/320px layouts.
The docs build installs and checks the exact downloadable ZIP.
An edited-template check verifies unembedded Helvetica faces in the PDF and
visible text in its browser preview.

These fixtures do not establish compatibility with every device or hosting
policy. WebKit testing is not branded Safari certification. Worker counts
observe browser API handles, not native thread-exit events. Bound concurrent
instances for the devices you support.

This browser entry provides ordinary PDFs and previews. It does not expose
PDF/A, PDF/UA, PDF/X, or VDP options. For React, use the
[React PDF starter](react-pdf.md).

The editor checks also paste templates for sibling counter resets, nested clipping,
SVG border-image centers, and decorated floated initials. They inspect downloaded
PDF text and independently specified colors in both the PDF and its preview.
