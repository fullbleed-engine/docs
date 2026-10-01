---
title: HTML/CSS to PDF playground
description: Edit HTML and CSS and generate a real Fullbleed PDF directly in your browser. Free, no sign-in, and no document upload. Start with a designed invoice or illustrated report.
hide:
  - navigation
  - toc
---

<link rel="stylesheet" href="../assets/playground/playground.css">

<div class="fb-playground" id="playground">
  <div class="pg-intro">
    <p class="pg-eyebrow">A little code. A finished page.</p>
    <h1>Make it your own.</h1>
    <p>Edit the HTML or CSS. Render a real PDF. Everything runs on your device.</p>
  </div>
  <div class="pg-toolbar">
    <div class="pg-picker"><label for="pg-example">Start with</label><select id="pg-example" disabled><option value="invoice">Northstar invoice</option><option value="report">Common Ground report</option><option value="notice">Riverton notice</option></select></div>
    <div class="pg-actions"><button id="pg-render" class="pg-primary" disabled>Render PDF <span aria-hidden="true">↗</span></button><button id="pg-cancel" hidden>Cancel</button><a id="pg-download" aria-disabled="true">Download PDF</a></div>
  </div>
  <div class="pg-workspace">
    <section class="pg-editor" aria-label="Document source">
      <div class="pg-pane-top"><div role="tablist" aria-label="Source language"><button role="tab" id="pg-html-tab" aria-controls="pg-html-panel" aria-selected="true">HTML</button><button role="tab" id="pg-css-tab" aria-controls="pg-css-panel" aria-selected="false" tabindex="-1">CSS</button></div><button id="pg-reset" disabled>Reset example</button></div>
      <div id="pg-html-panel" role="tabpanel" aria-labelledby="pg-html-tab"><label class="pg-sr" for="pg-html">HTML source</label><textarea id="pg-html" spellcheck="false" autocapitalize="off" autocomplete="off" aria-describedby="pg-editor-tip" disabled></textarea></div>
      <div id="pg-css-panel" role="tabpanel" aria-labelledby="pg-css-tab" hidden><label class="pg-sr" for="pg-css">CSS source</label><textarea id="pg-css" spellcheck="false" autocapitalize="off" autocomplete="off" aria-describedby="pg-editor-tip" disabled></textarea></div>
      <div class="pg-editor-foot"><span id="pg-editor-tip">Change a heading or color, then render. Ctrl/⌘ + Enter also works.</span><div><a id="pg-save-html" aria-disabled="true">Save HTML</a><a id="pg-save-css" aria-disabled="true">Save CSS</a></div></div>
    </section>
    <section class="pg-output" aria-label="PDF preview" aria-busy="true">
      <div class="pg-pane-top"><span class="pg-output-label">THE PRINTED PAGE</span><div class="pg-pagination"><button id="pg-previous" aria-label="Previous PDF page" disabled>←</button><span id="pg-page-count">—</span><button id="pg-next" aria-label="Next PDF page" disabled>→</button></div></div>
      <div class="pg-canvas"><p id="pg-placeholder">Preparing your first PDF…</p><img id="pg-preview" alt="" hidden></div>
      <div class="pg-output-foot"><span id="pg-result">Fullbleed 2.5.0</span><a href="../examples/">Explore the full gallery ↗</a></div>
    </section>
  </div>
  <p id="pg-status" class="pg-status" role="status" aria-live="polite">Loading the examples…</p>
  <p class="pg-footnote">Free. No account. Your source stays in this tab and is not uploaded. Download any files you want to keep before leaving. The first render downloads the engine and bundled fonts.</p>
</div>

<noscript>This playground needs JavaScript to run Fullbleed on your device. You can also <a href="../examples/">download the examples</a> or <a href="../getting-started/quickstart/">render with Python</a>.</noscript>

## Keep building

Save your HTML and CSS with the links in the editor. [Download the bundled fonts](assets/playground/fonts.zip)
and extract the ZIP beside those files; it creates a `fonts` folder with the font
files and their licenses. For the invoice example, run:

```bash
python -m pip install fullbleed
python -m fullbleed render --html fullbleed-invoice.html --css fullbleed-invoice.css --out invoice.pdf --asset fonts/Inter-Variable.ttf --asset fonts/DMSerifDisplay-Regular.ttf --asset fonts/DMSerifDisplay-Italic.ttf --asset fonts/BebasNeue-Regular.ttf
```

For the other examples, replace `invoice` in the input filenames with `report`
or `notice`. You can keep editing and add `--watch` to rebuild after each save.

[Use Fullbleed in Python](getting-started/quickstart.md){ .md-button .md-button--primary }
[Run the Python notebook](getting-started/notebook.md){ .md-button }
[CSS support](css-coverage.md){ .md-button }

The playground uses the released **Fullbleed 2.5.0** Rust engine, compiled to
WebAssembly. The PDF and page previews come from Fullbleed. It accepts static
HTML/CSS, with Inter, DM Serif Display, and Bebas Neue embedded fonts. JavaScript
inside your document is not executed, and remote assets are not loaded. Use inline SVG for artwork.

This demo handles up to **6 pages and 200 KB of HTML/CSS**, with a 30-second render
limit. These are playground limits; the local
Python and Rust packages support larger jobs. Sample organizations and data are
fictional.

[Playground source and verification](https://github.com/fullbleed-engine/docs/tree/main/playground)
· [Build record](assets/playground/build.json)
· [Native/WASI fixture checks](assets/playground/verification.json)
· [Third-party licenses](assets/playground/LICENSES.txt)

<script type="module" src="../assets/playground/app.js"></script>
