# Fullbleed browser playground

An optional static website adapter for the unchanged published `fullbleed = 2.5.40`
Rust crate with the `svg_raster` feature. It compiles to `wasm32-wasip1` and runs inside a Web Worker using
`@bjorn3/browser_wasi_shim` 0.4.2. It adds no dependencies to the Python wheel or
the core Rust crate. The engine produces the PDF, then renders PNG page previews
from that finalized file. Downloaded Python and Node.js projects use the same preview path.

The browser fetches fixed engine/font/example assets from the docs site. User
HTML/CSS is passed to a worker and an in-memory filesystem; it is never inserted
into the page DOM or submitted to a server. Only the sample fonts are exposed
to WASI. No file-system, network, process, or system-font capabilities are passed
through to the host machine. Sources are kept in tab memory, without localStorage.

## Reproduce

Install Rust with the `wasm32-wasip1` target, Node 22 or newer, Python, and the
root documentation requirements. Then from the repository root:

```sh
rustup target add wasm32-wasip1
python tools/build_playground.py
node tools/verify_playground.mjs
python -m mkdocs build --strict
python tools/check_site.py site
python -m pip install -r tools/browser-requirements.txt
python -m playwright install chrome
python tools/check_playground_ui.py --site site --out output/playground-ui
```

The build uses both lockfiles, publishes a toolchain/hash record, and retains
the generated verification report next to the browser assets. The verification
script compares native and WASI PDF and PNG bytes for the invoice, report, and
notice, an edited invoice, three gradient cases, and all 12 unembedded Latin
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
`tools/check_playground_ui.py` exercises the built page, checks the four
layout cases against independent PDF text and color probes, downloads edited
PDFs and both project ZIPs, and verifies pagination, source/page limits, cancellation,
recovery, and 1440/390/320px layouts. CI retains the PDFs, previews, and screenshots.
The page-flow checks inspect downloaded PDF text and glyph positions with
independent readers and compare every displayed page with the native preview.
These checks establish the recorded fixtures only, not universal platform parity
or ISO conformance.

## Continue locally

**Download project** captures the current editor values into a ZIP with the
fonts and their licenses, dependencies pinned to the built engine version, a
Python or Node.js runner, and a file-hash manifest. The Node project locks
`fullbleed@0.8.4` (engine 2.5.40), uses `defaultStyles: false` to retain the
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
python -m pip install fullbleed==2.5.40 pypdf==6.19.0 pypdfium2==5.14.0 Pillow==12.3.0
node tools/verify_project_export.mjs
python -I tools/verify_project_export.py
python -I tools/verify_node_project_export.py
python tools/verify_playground_pagination.py
python tools/verify_playground_quotes.py
python tools/verify_playground_decorations.py
```

The verifier checks ZIP integrity, exact source and font/license bytes, export
replay, failure recovery, and Python/Node/WASI PDF and PNG equality for the invoice,
report, notice, an edited invoice, three gradient cases, and the standard-font
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
