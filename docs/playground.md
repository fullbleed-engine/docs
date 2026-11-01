---
title: HTML/CSS to PDF playground
description: Generate a PDF from local HTML, CSS, images, and fonts. Save and reopen Python or Node.js projects in your browser. Free, no account, and no document upload.
hide:
  - navigation
  - toc
search:
  boost: 2
---

<link rel="stylesheet" href="../assets/playground/playground.css?v=contents-counters-2550">

<div class="fb-playground" id="playground">
  <div class="pg-intro">
    <p class="pg-eyebrow">A little code. A finished page.</p>
    <h1>Make it your own.</h1>
    <p>Edit an example or open your own HTML, CSS, images, and fonts. Everything runs on your device.</p>
  </div>
  <div class="pg-toolbar">
    <div class="pg-picker"><label for="pg-example">Start with</label><select id="pg-example" disabled><option value="invoice">Northstar invoice</option><option value="report">Common Ground report</option><option value="notice">Riverton notice</option></select></div>
    <div class="pg-actions"><button id="pg-render" class="pg-primary" disabled>Render PDF <span aria-hidden="true">↗</span></button><button id="pg-cancel" hidden>Cancel</button><a id="pg-download" aria-disabled="true">Download PDF</a></div>
  </div>
  <p id="pg-status" class="pg-status" role="status" aria-live="polite">Loading the examples…</p>
  <details class="pg-tools" id="pg-tools" open>
  <summary>Files and projects <span class="pg-tools-marker" aria-hidden="true">+</span></summary>
  <div class="pg-local-files">
    <div class="pg-local-top"><button id="pg-open-files" disabled>Open local files</button><span id="pg-asset-count">0 local assets</span></div>
    <input id="pg-files" class="pg-sr" type="file" multiple accept=".html,.htm,.css,.png,.jpg,.jpeg,.svg,.ttf,.otf,.txt" tabindex="-1" aria-label="Choose local document files">
    <p>Choose HTML/CSS, PNG, JPEG, SVG, TTF, or OTF files. Opening HTML starts a new document. Your files stay in this tab.</p>
    <p id="pg-asset-help" hidden>Use the paths below in your HTML or CSS. Assets stay available when switching examples and are included in Download project. Optional TXT license files are included too.</p>
    <ul id="pg-assets" aria-label="Local document assets"></ul>
  </div>
  <div class="pg-export">
    <div class="pg-picker"><label for="pg-project-language">Project language</label><select id="pg-project-language" disabled><option value="python">Python</option><option value="node">Node.js</option></select></div>
    <button id="pg-project" disabled>Download project</button>
    <button id="pg-open-project" aria-describedby="pg-project-help" disabled>Open saved project</button>
    <input id="pg-project-file" class="pg-sr" type="file" accept=".zip" tabindex="-1" aria-label="Choose a saved playground project ZIP">
  </div>
  <p id="pg-project-status" class="pg-project-status" role="status" aria-live="polite" hidden></p>
  </details>
  <div class="pg-view" id="pg-view" role="group" aria-label="Workspace view" hidden>
    <button id="pg-view-source" aria-controls="pg-editor" aria-pressed="false">Edit source</button>
    <button id="pg-view-preview" aria-controls="pg-output" aria-pressed="true">PDF preview</button>
  </div>
  <div class="pg-workspace">
    <section class="pg-editor" id="pg-editor" aria-label="Document source" tabindex="-1">
      <div class="pg-pane-top"><div role="tablist" aria-label="Source language"><button role="tab" id="pg-html-tab" aria-controls="pg-html-panel" aria-selected="true">HTML</button><button role="tab" id="pg-css-tab" aria-controls="pg-css-panel" aria-selected="false" tabindex="-1">CSS</button></div><button id="pg-reset" disabled>Reset example</button></div>
      <div id="pg-html-panel" role="tabpanel" aria-labelledby="pg-html-tab"><label class="pg-sr" for="pg-html">HTML source</label><textarea id="pg-html" spellcheck="false" autocapitalize="off" autocomplete="off" aria-describedby="pg-editor-tip" disabled></textarea></div>
      <div id="pg-css-panel" role="tabpanel" aria-labelledby="pg-css-tab" hidden><label class="pg-sr" for="pg-css">CSS source</label><textarea id="pg-css" spellcheck="false" autocapitalize="off" autocomplete="off" aria-describedby="pg-editor-tip" disabled></textarea></div>
      <div class="pg-editor-foot"><span id="pg-editor-tip">Change a heading or color, then render. Ctrl/⌘ + Enter also works.</span><div><a id="pg-save-html" aria-disabled="true">Save HTML</a><a id="pg-save-css" aria-disabled="true">Save CSS</a></div></div>
    </section>
    <section class="pg-output" id="pg-output" aria-label="PDF preview" aria-busy="true" tabindex="-1">
      <div class="pg-pane-top"><span class="pg-output-label">THE PRINTED PAGE</span><div class="pg-pagination"><button id="pg-previous" aria-label="Previous PDF page" disabled>←</button><span id="pg-page-count">—</span><button id="pg-next" aria-label="Next PDF page" disabled>→</button></div></div>
      <div class="pg-canvas"><p id="pg-placeholder">Preparing your first PDF…</p><img id="pg-preview" alt="" hidden></div>
      <div class="pg-output-foot"><span id="pg-result">Fullbleed 2.5.50</span><a href="../examples/">Explore the full gallery ↗</a></div>
    </section>
  </div>
  <p id="pg-project-help" class="pg-footnote">Download project saves your source and assets in a ZIP you can reopen here. Opening a saved project replaces the current document and local assets.</p>
  <p class="pg-footnote">Free. No account. Your source stays in this tab and is not uploaded. Download your project before leaving. The first render downloads the engine and bundled fonts.</p>
  <p id="pg-feedback" class="pg-footnote"><a id="pg-report" href="https://github.com/fullbleed-engine/fullbleed-official/issues/new?template=bug_report.yml&amp;title=%5BBug%5D%3A+Playground+rendering&amp;version=2.5.50+%28browser+playground%29&amp;environment=WebAssembly+playground%3B+browser+and+operating+system%3A+%5Badd+yours%5D" target="_blank" rel="noopener noreferrer">Report a rendering problem</a>. Opens a public GitHub form in a new tab. Use sample data; your document is not attached.</p>
</div>

<noscript>This playground needs JavaScript to run Fullbleed on your device. You can also <a href="../examples/">download the examples</a> or <a href="../getting-started/quickstart/">render with Python</a>.</noscript>

## Try your own document

On smaller screens, use **Edit source** and **PDF preview** to switch views.
**Render PDF** opens the preview; **Ctrl/⌘ + Enter** renders while keeping you in
the editor. Switching views preserves your edits.

Expand **Files and projects**, then choose **Open local files** to select HTML,
CSS, images, and fonts from your device.
Opening HTML starts **Your document** and clears the separate stylesheet unless
you select a CSS file at the same time. Opening CSS alone keeps the current HTML.
Your edited examples remain in the **Start with** menu.

Use the displayed asset paths in your source. For example:

```html
<img src="assets/logo.png" alt="Company logo" width="120">
```

Give an imported font a convenient CSS family name:

```css
@font-face { font-family: Brand; src: url("assets/brand.ttf"); }
html, body { font-family: Brand; }
@page {
  @bottom-center { content: "Page " counter(page) " of " counter(pages); }
}
```

Page headers and footers inherit their font from `html`. Set a different family
on `@page` or an individual margin box to override it. A font set only on `body`
does not set the page font. These aliases also work in the Python and Node.js
projects you download. See [font registration](engine/font-registration.md#fonts-in-page-headers-and-footers)
for fallback families and weight selection.

Assets stay available when switching examples. Remove an asset before adding a
replacement with the same filename. The demo accepts up to **16 assets**, **8 MiB
per asset**, and **20 MiB combined**, plus **200 KB of HTML/CSS**. Use filenames
without folders; update references such as `images/logo.png` to the displayed
`assets/logo.png`. Remote files and linked external stylesheets are not fetched.

**Download project** includes the source, selected assets, and their hashes for
Python or Node.js. Optional TXT license files are included as assets. Files stay
in this tab until you download them; closing the tab clears them.

## Let an invoice grow

The Northstar invoice flows onto additional pages when you add line items.
Its table headings repeat, the footer shows the actual page count, and the total
stays with the payment details. Edit the rows inside `<tbody>` in the HTML panel.
The sample amounts are plain text, so update the subtotal and total when you change
the rows. For calculated amounts from application data, use the
[Python invoice starter](guides/web-frameworks.md).

Page size, margins, and footer text are in the stylesheet's `@page` rule.
The `.closing` block groups the totals and payment details. These same HTML/CSS
files are included when you download a Python or Node.js project.

## Save a project and come back later

Choose Python or Node.js, then **Download project**. Keep the ZIP unchanged.
On your next visit, choose **Open saved project** and select that ZIP to restore
your HTML, CSS, custom assets, and project language. Choose **Render PDF** to
preview it, or keep editing. This works without an account or document upload.

Opening a project replaces the current document and assets; download your current
project first if you want to keep it. Invalid projects leave your current work
intact. The browser accepts project ZIPs up to **24 MiB**, with the same source and
asset limits listed above. Larger exports remain usable with their local renderer.

The preview uses this playground’s engine and bundled fonts. If the saved engine
version differs, the editor tells you before you render. To use the project’s
original pinned version, follow the README inside its ZIP. Archived Python and
JavaScript files are never run by the playground. For source edited after
extraction, use **Open local files** instead of repackaging the ZIP.

## Wrap long code lines

To keep indentation and authored line breaks while fitting long tokens on the
page, add this to the CSS editor:

```css
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
```

Use `white-space: pre-line` when you want to keep line breaks but collapse extra
spaces. A plain `<pre>` preserves its whitespace without wrapping. Wrapped code
can continue onto another page; this playground accepts up to six pages.

## Keep building

Choose **Python** or **Node.js** under **Project language**, then **Download
project** to keep your current HTML/CSS, bundled fonts and licenses, pinned
dependencies, and a renderer in one ZIP. Extract it into a folder, open a
terminal there, and run:

=== "Python"

    Use a Python 3.10 or newer virtual environment.

    ```bash
    python -m pip install -r requirements.txt
    python render.py
    ```

=== "Node.js"

    Use Node.js 22 or newer. The lockfile pins Fullbleed 0.9.3 and its dependency.

    ```bash
    npm ci --ignore-scripts
    npm run render
    ```

Open `output/document.pdf`; PNG previews are in `output/preview/`. Edit
`input.html` or `style.css`, then run the script again. The project uses Fullbleed
engine 2.5.50 to match this demo. The Node renderer preserves your CSS with
`defaultStyles: false`. The ZIP
is assembled on your device, using the source present when you click the button.
It does not upload your document.

The individual **Save HTML** and **Save CSS** links remain useful for an existing
project. [Download the bundled fonts](assets/playground/fonts.zip) and extract
them beside those files; for the invoice example, run:

```bash
python -m pip install fullbleed
python -m fullbleed render --html fullbleed-invoice.html --css fullbleed-invoice.css --out invoice.pdf --asset fonts/Inter-Variable.ttf --asset fonts/DMSerifDisplay-Regular.ttf --asset fonts/DMSerifDisplay-Italic.ttf --asset fonts/BebasNeue-Regular.ttf
```

For the other examples, replace `invoice` in the input filenames with `report`
or `notice`. You can keep editing and add `--watch` to rebuild after each save.

[Use Fullbleed in Python](getting-started/quickstart.md){ .md-button .md-button--primary }
[Use Fullbleed in Node.js](getting-started/node.md){ .md-button }
[Use Fullbleed in Rust](getting-started/rust.md){ .md-button }
[Run the Python notebook](getting-started/notebook.md){ .md-button }
[CSS support](css-coverage.md){ .md-button }

The playground uses the released **Fullbleed 2.5.50** Rust engine, compiled to
WebAssembly. Page previews are rendered from the same PDF you download, including
the report's gradient chart fills. It accepts static
HTML/CSS, with Inter, DM Serif Display, and Bebas Neue embedded fonts. JavaScript
inside your document is not executed, and remote assets are not loaded. Open local
images and fonts or use inline SVG for artwork.

Unembedded Helvetica, Times, and Courier variants also produce visible previews.
The [font-preview guide](engine/assets.md#standard-14-native-previews) explains
the bundled substitute fonts used for those faces.

This demo handles up to **6 pages and 200 KB of HTML/CSS**, with a 30-second render
limit. These are playground limits; the local
Python, Node.js, and Rust packages support larger jobs. Sample organizations and data are
fictional.

[Playground source and verification](https://github.com/fullbleed-engine/docs/tree/main/playground)
· [Build record](assets/playground/build.json)
· [Native/WASI fixture checks](assets/playground/verification.json)
· [Project download checks](assets/playground/project-verification.json)
· [Node project checks](assets/playground/node-project-verification.json)
· [Radial-gradient checks](assets/playground/radial-gradient-verification.json)
· [Release upgrade checks](assets/playground/upgrade-verification-084.json)
· [Third-party licenses](assets/playground/LICENSES.txt)

<script type="module" src="../assets/playground/app.js?v=contents-counters-2550"></script>

Build this into your own web app: [download the browser SDK starter](guides/browser-pdf.md),
with editable templates and local PDF downloads.
