# Fullbleed browser playground

An optional static website adapter for the unchanged published `fullbleed = 2.5.50`
Rust crate with the `svg_raster` feature. It compiles to `wasm32-wasip1` and runs inside a Web Worker using
`@bjorn3/browser_wasi_shim` 0.4.2. It adds no dependencies to the Python wheel or
the core Rust crate. The engine produces the PDF, then renders PNG page previews
from that finalized file. Downloaded Python and Node.js projects use the same preview path.

The editable invoice uses `docs/assets/playground/invoice.html` and `invoice.css`
for automatic table pagination, page-margin counters, and grouped totals/payment
details. `examples.js` supplies source paths to the browser and verification tools;
the report and notice sources live in `docs/assets/showcase`.

The browser fetches fixed engine/font/example assets from the docs site. User
HTML/CSS is passed to a worker and an in-memory filesystem; it is never inserted
into the page DOM or submitted to a server. Bundled fonts and explicitly selected
local assets are exposed to WASI in memory. No host file-system, network, process, or system-font capabilities are passed
through to the host machine. Sources are kept in tab memory, without localStorage.

A native `beforeunload` prompt guards unsaved source and asset changes. It is
attached only while the tab contains unsaved work, including edits in other examples.
Saving one source file or example does not mark other edits as saved; an export
that finishes after newer edits only marks its captured snapshot as saved.
Reset explicitly discards source edits. Browser prompts are not reliable backups,
particularly on mobile; users must keep their downloaded project ZIPs.

The local file picker accepts one HTML and one CSS file per selection, plus PNG,
JPEG, SVG, TTF, OTF, and optional TXT license files. Assets use `assets/filename`
paths, with 16 assets, 8 MiB per file, and 20 MiB total as the demo limits. File
validation completes before source or asset state changes. Importing HTML starts
the Your document entry; existing example edits remain available. Assets stay in
the tab when switching documents and are copied into downloaded projects.

**Open saved project** restores an unchanged playground ZIP's source, custom
assets, and language in a new tab. It replaces the current document and assets
only after validating the entire archive. The importer accepts the exporter's
stored ZIP format, up to 24 MiB and 64 entries, with matching local/directory
records, CRCs, manifest hashes, and the usual source/asset limits. It does not
execute archived runners or use archived engine binaries. Previewing uses the
current engine and bundled fonts; a different saved engine version is reported
before rendering. These integrity checks do not authenticate a ZIP's author.

## Reproduce

Install Rust with the `wasm32-wasip1` target, Node 22 or newer, Python, and the
root documentation requirements. Then from the repository root:

```sh
rustup target add wasm32-wasip1
python tools/build_playground.py
node tools/verify_playground.mjs
python -m pip install -r tools/browser-requirements.txt fullbleed==2.5.50
node tools/verify_project_export.mjs
python -I tools/verify_project_export.py
python -I tools/verify_node_project_export.py
python tools/verify_playground_pagination.py
python tools/verify_playground_quotes.py
python tools/verify_playground_decorations.py
python tools/verify_playground_preformatted.py
python tools/verify_playground_radial_gradients.py
python tools/verify_playground_fonts.py
python -m mkdocs build --strict
python tools/check_site.py site
python -m playwright install chrome
python tools/check_playground_ui.py --site site --out output/playground-ui
python tools/check_playground_invoice.py --site site --out output/playground-invoice
python tools/check_playground_recovery.py --site site --out output/playground-recovery
python tools/check_playground_unsaved.py --site site --out output/playground-unsaved/chrome --browser chrome
python tools/check_playground_unsaved.py --site site --out output/playground-unsaved/firefox --browser firefox
```

The build uses both lockfiles, publishes a toolchain/hash record, and retains
the generated verification report next to the browser assets. The verification
script compares native and WASI PDF and PNG bytes for the invoice, report, and
notice, an edited invoice, fifteen gradient cases, and all 12 unembedded Latin
standard font faces, plus sibling counter resets, nested clipping, SVG border-image
centers, and a decorated floated initial; checks expected gradient colors and visible text in every
standard-font row; and exercises source/page limits and
recovery. Nine page-flow cases cover long tables with six overflow settings,
forced page breaks, and footnotes that move with their text.
Forty-one quotation cases cover nested generated quotes, silent depth changes,
hidden content and replaced elements. Independent PDF readers check the exact
text in the browser download and both exported language projects.
Sixteen decoration cases check continuous lines through spaces, inherited and
raised spans, wrapping, atomic isolation, and shadows. Independent PDFium
geometry and pixels must match the retained public 2.5.40 reference.
Seventeen preformatted-block cases use an imported, licensed Noto Sans font:
seven wrapping policies, four no-wrap controls, and six whitespace policies.
Independent PDF readers inspect all authored text, font embedding, page bounds,
indentation, and newline placement in WASI, Python, Node, and browser downloads.
The test font is not added to the playground's runtime bundle.
Twelve radial endpoint cases include coincident final stops, transparency,
ellipses, offset centers, and three controls. Their PDFs must match retained
public 2.5.43 outputs, with valid stitching-function bounds and checked outer
colors in both native previews and independent PDFium rendering. The actual
browser editor downloads and both exported language projects run these cases.
Eight page-font alias/control pairs cover local and imported sources, inherited
weight selection, fallback lists, quoted family names, `size-adjust`, and named
pages. The alias must reproduce the explicit face's PDF and native preview bytes;
independent readers verify embedded footer faces, sizes, text, and pixels. The
real browser editor runs the same pairs and replays its actual Python and Node
project downloads for the two-page named-page case.
`tools/check_playground_ui.py` exercises the built page, checks the four
layout cases against independent PDF text and color probes, downloads edited
PDFs and both project ZIPs, and verifies pagination, source/page limits, cancellation,
recovery, and 1440/390/320px layouts. CI retains the PDFs, previews, and screenshots.
The recovery check returns HTTP 503 for the worker script, renderer module,
engine, and a bundled font. It checks the retry guidance, preserves edited
HTML/CSS and imported assets, and retries on the same page. Every recovered
PDF and displayed preview must match the successful baseline, and the final
project ZIP must retain the edited source and original asset bytes.
The page-flow checks inspect downloaded PDF text and glyph positions with
independent readers and compare every displayed page with the native preview.
These checks establish the recorded fixtures only, not universal platform parity
or ISO conformance.

The invoice browser check covers the short design, 24 line items, wrapped
descriptions, an empty table, and four pagination boundaries. Independent readers
check item order, repeated headings, final page counters, totals/payment grouping,
and every visible glyph box. The long and wrapped invoices are downloaded as real
Python and Node.js projects; their PDF and preview bytes must match the browser.
The long project is also reopened through the file picker. CI compares the short
and long documents in Firefox and Playwright WebKit with the full Chrome run.

## Continue locally

**Download project** captures the current editor values into a ZIP with the
fonts and their licenses, dependencies pinned to the built engine version, a
Python or Node.js runner, and a file-hash manifest. The Node project locks
`fullbleed@0.9.3` (engine 2.5.50), uses `defaultStyles: false` to retain the
template's CSS cascade, and runs with `npm ci --ignore-scripts` followed by
`npm run render`. Exporting uses only static GET requests
for bundled assets; the document stays in the browser. It captures source at the
click, including edits that have not been rendered. Later edits do not change an
export already in progress, including its selected language. A separate download status leaves rendering usable
when a project asset fails to load.

The ZIP uses stored entries and requires no extra browser library. Font bytes
are checked against the existing attribution manifest before export. After
building the playground, verify the complete handoff with:

```sh
python -m pip install fullbleed==2.5.50 pypdf==6.19.0 pypdfium2==5.14.0 Pillow==12.3.0
node tools/verify_project_export.mjs
python -I tools/verify_project_export.py
python -I tools/verify_node_project_export.py
python tools/verify_playground_pagination.py
python tools/verify_playground_quotes.py
python tools/verify_playground_decorations.py
python tools/verify_playground_preformatted.py
python tools/verify_playground_radial_gradients.py
python tools/verify_playground_fonts.py
node tools/test_playground_local_files.mjs
node tools/test_playground_project_import.mjs
python tools/check_playground_local_files.py --site site --out output/playground-local-files
python tools/check_playground_fonts.py --site site --out output/playground-fonts
python -m playwright install chromium
python tools/check_playground_preformatted.py --site site --out output/playground-preformatted
python -m playwright install --with-deps chrome firefox webkit
python tools/check_playground_project_import.py --site site --out output/project-import/chrome --browser chrome
python tools/check_playground_project_import.py --site site --out output/project-import/firefox --browser firefox
python tools/check_playground_project_import.py --site site --out output/project-import/webkit --browser webkit
```

The verifier checks ZIP integrity, exact source and font/license bytes, export
replay, failure recovery, and Python/Node/WASI PDF and PNG equality for the invoice,
report, notice, an edited invoice, fifteen gradient cases, and the standard-font
fixture, plus the four layout cases above and six font-cascade cases covering
defaults, inheritance, specificity, and layers. An independent PDF reader verifies that all 12 font faces remain
unembedded and their text is intact. Extracted projects run from paths with
spaces and a different current working directory. Node dependencies are installed
from the public registry once, then from a local npm cache with the unchanged
lockfile for the other projects. The UI check holds an actual asset response while
changing the source and selected language, then verifies that the downloaded ZIP
retains the original snapshot. It also simulates an asset failure and recovers.
Results are retained in
`playground/project-verification`.

The local-file browser check imports a licensed IBM Plex Mono font, its license,
and synthetic PNG, JPEG, and SVG images. It checks UTF-8 filenames and sources,
font embedding and image pixels with independent PDF readers, then replays both
actual project downloads from directories with spaces and another working directory.
It also checks rejected imports, asset removal, document switching, mobile layouts,
and the absence of document uploads. The JavaScript checks cover limits before file
reads, equivalent duplicate filenames, and byte snapshots during project export.

The saved-project browser check closes the original context, reopens each actual
Python/Node download through the file picker, and requires byte-identical PDFs
and reexported ZIPs. It also checks damaged archives, edits during import, older
engine notices, keyboard activation, 1440/390/320px layouts, and no document
uploads. CI runs this check in Chromium, Firefox, and Playwright WebKit; the latter
is not a Safari certification. Unit checks reject unsupported ZIP features and
malformed manifests before the editor can change.

The preformatted browser check uses a fresh anonymous headless Chromium context,
the real file picker and editor, two PDF downloads for every case, every displayed
page preview, and six actual Python/Node project downloads. Those six projects
run from paths with spaces and must reproduce the browser PDF and PNG bytes.
The exported-project gate also repeats all seventeen cases in each runtime.
The separate Rust quickstart retains its bundled-font fixture scope; its report
lists the imported-asset cases excluded from that quickstart replay.

The adapter limits sources to 200,000 UTF-8 bytes, documents to six pages, WASM
linear memory to 256 MiB, and each render to 30 seconds. The browser terminates
the worker after completion, cancellation, timeout, or an error. Font downloads
and compilation have a separate 90-second allowance. Edit and render again to
recover; no server process is created.

`docs/assets/playground/fonts` contains the licensed fonts used by the showcase.
Their upstream attribution is retained in `LICENSES.txt` and `font-sources.json`.
`LICENSES.txt` also includes the licenses for substitute fonts compiled into the
engine's standard-font preview renderer.
The demo's limits and embedded assets are not the full local engine feature set.
