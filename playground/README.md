# Fullbleed browser playground

An optional static website adapter for the unchanged published `fullbleed = 2.5.0`
Rust crate. It compiles to `wasm32-wasip1` and runs inside a Web Worker using
`@bjorn3/browser_wasi_shim` 0.4.2. It adds no dependencies to the Python wheel or
the core Rust crate. The engine produces both the PDF and PNG page previews.

The browser fetches fixed engine/font/example assets from the docs site. User
HTML/CSS is passed to a worker and an in-memory filesystem; it is never inserted
into the page DOM or submitted to a server. Only the sample fonts are exposed
to WASI. No file-system, network, process, or system-font capabilities are passed
through to the host machine. Sources are kept in tab memory, without localStorage.

## Reproduce

Install Rust with the `wasm32-wasip1` target, Node 20 or newer, Python, and the
root documentation requirements. Then from the repository root:

```sh
rustup target add wasm32-wasip1
python tools/build_playground.py
node tools/verify_playground.mjs
python -m mkdocs build --strict
python tools/check_site.py site
```

The build uses both lockfiles, publishes a toolchain/hash record, and retains
the generated verification report next to the browser assets. The verification
script compares native and WASI PDF and PNG bytes for the invoice, report, and
notice; checks an edit changes the output; and exercises source/page limits and
recovery. The browser UI is additionally reviewed with actual downloaded PDFs.
These checks establish the recorded fixtures only, not universal platform parity
or ISO conformance.

The adapter limits sources to 200,000 UTF-8 bytes, documents to six pages, WASM
linear memory to 256 MiB, and each render to 30 seconds. The browser terminates
the worker after completion, cancellation, timeout, or an error. Font downloads
and compilation have a separate 90-second allowance. Edit and render again to
recover; no server process is created.

`docs/assets/playground/fonts` contains the licensed fonts used by the showcase.
Their upstream attribution is retained in `LICENSES.txt` and `font-sources.json`.
The demo's limits and embedded assets are not the full local engine feature set.
