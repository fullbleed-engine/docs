# Fullbleed from Rust

These examples use the published `fullbleed` 2.5.0 crate. They require Rust
1.85 or newer and a working native Rust toolchain; they do not require Python.

From the root of this documentation repository:

```bash
cargo run --release --locked --manifest-path examples/rust/Cargo.toml --bin hello
cargo run --release --locked --manifest-path examples/rust/Cargo.toml --bin from-files -- docs/assets/showcase/invoice.html docs/assets/showcase/invoice.css docs/assets/playground/fonts output/rust-invoice
```

The first command writes `invoice.pdf`. The second writes the designed
Northstar invoice to `output/rust-invoice/document.pdf`, plus a 96-DPI PNG for
each page. Replace both `invoice` input filenames with `report` or `notice`
to render the other playground designs. Use a new output directory for each
document so previews from an earlier, longer document do not remain there.

`from-files` also accepts HTML/CSS exported from the browser playground and
its extracted fonts folder. Font files and licenses are in
`docs/assets/playground/fonts`; keep the license notices when redistributing them.

The [Rust quickstart](https://docs.fullbleed.dev/getting-started/rust/) explains
the API and how to start a new Cargo project. These are document-generation
examples, not a sandbox for untrusted HTML or file paths.
