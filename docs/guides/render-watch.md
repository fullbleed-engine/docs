---
title: Rebuild PDFs automatically while editing HTML and CSS
description: Use Fullbleed render --watch to rebuild a PDF and PNG previews after saving HTML, CSS, or assets. Includes a runnable invoice, JSON results, and recovery behavior.
---
# Rebuild PDFs as you edit

Save your HTML or CSS and let Fullbleed rebuild the document. Watch mode writes
an initial PDF, then keeps running and rebuilds after input changes. It uses
Python's standard library and adds no extra runtime package.

**Requires Fullbleed 2.5.0 or newer.** Check your version with
`python -m fullbleed --version`.

## Try the invoice example

Use a Python 3.10–3.14 virtual environment:

```bash
python -m pip install --upgrade "fullbleed>=2.5.0,<3"
git clone https://github.com/fullbleed-engine/fullbleed-official.git
cd fullbleed-official/examples/render_watch
python -m fullbleed render --html invoice.html --css styles.css --asset "@noto-sans" --out invoice.pdf --emit-image preview --watch
```

Open `invoice.pdf` or the PNG in `preview/`. Change the heading color in
`styles.css`, save, and inspect the regenerated file. The font is bundled in
the wheel. Press **Ctrl-C** to stop; omit `--watch` to render once.

[Get the complete example](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.5.0/examples/render_watch){ .md-button .md-button--primary }

Fullbleed writes the PDF and preview files. Your viewer handles opening and
refreshing them; use a viewer that reloads changed files if you want a live
view. On Windows, close a PDF viewer that locks the output file, or inspect
the PNG instead.

The sample uses fictional data and static amounts. Update the total if you
change its line items; rendering does not calculate invoice arithmetic.

## Choose what to watch

Explicit HTML, CSS, and `--asset` files are watched automatically. So are local
file-backed page margins, PDF/VT jobs, template bindings and template maps,
output-intent ICC files, watermark images, and reproducibility-check inputs.

Add any other dependency with `--watch-path`. Repeat it for multiple files or
directories; directories are scanned recursively, including newly created files:

```bash
python -m fullbleed render --html invoice.html --css styles.css --asset "@noto-sans" --out invoice.pdf --emit-image preview --watch --watch-path assets --watch-path templates
```

Paths referenced *inside* HTML, CSS, or a JSON file are not automatically
discovered. For example, add a PDF referenced by a template map as a watch path.
An extra path triggers rendering but does not make its contents an asset or
template input: configure those inputs with the ordinary render options.

If Python generates your HTML from data, keep that generation step in your
application and let Fullbleed watch the resulting HTML file. Watch mode does
not rerun Python scripts or transform a watched JSON file into HTML.

## Saving and recovering from errors

The default polling interval is **0.5 seconds**, with a **0.2-second debounce**
after the last observed change. Set `--watch-interval` and `--watch-debounce`
to adjust them. A burst of saves becomes one rebuild; an edit made during a
render triggers another pass.

If an editor temporarily removes an input during a save, the error is reported
and the process keeps watching. Restore or fix the file, and the next change
triggers another render. Failed quality gates also leave the watcher running.
A quality-gate failure can already have written a PDF, so use the latest result
to decide whether the output passed.

When a successful render shrinks the document, old PNG previews from that watch
session are removed only if they are still unmodified. Unrelated or manually
edited files are left alone.

## Read results from another tool

```bash
python -m fullbleed --json-only render --html invoice.html --css styles.css --asset "@noto-sans" --out invoice.pdf --watch
```

Stdout contains newline-delimited JSON with the existing
`fullbleed.render_result.v1` and `fullbleed.error.v1` schemas. Successful results
include the PDF SHA-256 at `outputs.sha256`. `--emit-manifest manifest.json`
refreshes a manifest on each cycle. JSON-only mode emits no watch status lines.

## Keep the loop predictable

- Use local file dependencies and a file for `--out`; HTML/CSS stdin and PDF stdout are unsupported. Inline HTML needs another local input or an explicit watch path.
- CLI output files and the preview directory are excluded from scans. Common cache/build directories are skipped beneath recursive roots, and nested directory symlinks are not followed.
- Put redirected stdout and application logs outside recursive watch paths. Fullbleed cannot identify arbitrary logs as its own outputs.
- Run one watcher per output path.
- Use a one-shot `render` or `verify` command for a delivery or CI gate. A watch process continues after failures and exits when interrupted.

For pull requests, use the [PDF regression starter](pdf-regression-ci.md) to
compare a one-shot render with a reviewed baseline and retain previews on failure.

See the [CLI reference](../cli/commands.md) for render flags and the
[source guide](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.5.0/docs/render-watch.md)
for the full contract. [Report an issue](https://github.com/fullbleed-engine/fullbleed-official/issues)
with the command, installed version, and a small input that reproduces it.
