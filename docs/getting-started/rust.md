---
title: Generate PDFs from Rust with HTML and CSS
description: Use the published Fullbleed Rust crate to render HTML/CSS into a PDF, register explicit fonts, and generate PNG previews. Includes runnable invoice and report examples.
---
# Generate PDFs from Rust with HTML and CSS

Use the [`fullbleed` crate](https://crates.io/crates/fullbleed) directly in a
Rust application. The engine renders static HTML and CSS into print documents;
you do not need Python or a browser to render them.

## Create your first PDF

With Rust 1.85 or newer and a working native Rust toolchain:

```bash
cargo new invoice-demo
cd invoice-demo
cargo add fullbleed@=2.5.11
```

Replace `src/main.rs` with:

```rust
use fullbleed::FullBleed;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let html = "<h1>Invoice INV-1042</h1><p>Consulting: USD 1,200.00</p>";
    let css = "@page { size: A4; margin: 20mm; } h1 { color: #175c52; }";
    let engine = FullBleed::builder().build()?;
    let pdf = engine.render_to_buffer(html, css)?;
    std::fs::write("invoice.pdf", pdf)?;
    Ok(())
}
```

Run it:

```bash
cargo run --release
```

Open `invoice.pdf` in the project directory. `render_to_buffer` returns PDF
bytes, which you can also return from an HTTP handler or write to your own
storage. For a file directly, use
`engine.render_to_file(html, css, "invoice.pdf")?`.

This first example uses standard PDF fonts. For explicit typography and
broader character coverage, register the font files your document uses.
The Python wheel's bundled fonts are not included in the Rust crate.

## Render a designed invoice or report

The runnable example includes font registration, missing-glyph checking, and
PNG previews. It uses the same source and fonts as the
[editable browser playground](../playground.md).

[![Northstar invoice rendered with Fullbleed, with cream paper, serif typography, and a forest-green total panel.](../assets/showcase/invoice-1.png)](../assets/showcase/invoice.pdf)

Clone the documentation repository and run the example from its root:

```bash
git clone https://github.com/fullbleed-engine/docs.git fullbleed-docs
cd fullbleed-docs
cargo run --release --locked --manifest-path examples/rust/Cargo.toml --bin from-files -- docs/assets/showcase/invoice.html docs/assets/showcase/invoice.css docs/assets/playground/fonts output/rust-invoice
```

Open `output/rust-invoice/document.pdf` or `page-1.png` in the same directory.
Replace both `invoice` input filenames with `report` for the report design,
and choose a new output directory. The report produces three
pages. These examples pin Fullbleed 2.5.11 and include a Cargo lockfile.

For the service notice or your own edits, choose **Download project** in the
playground. Extract the ZIP into `my-project` in this repository, then run:

```bash
cargo run --release --locked --manifest-path examples/rust/Cargo.toml --bin from-files -- my-project/input.html my-project/style.css my-project/fonts output/my-project
```

The Rust example reads the exported HTML, CSS, and fonts directly. The individual
**Save HTML** and **Save CSS** links also work with an existing fonts directory.

## Register fonts and create previews

Font registration is explicit. For example, with the downloaded `fonts`
directory beside your application:

```rust
let engine = FullBleed::builder()
    .register_font_file("fonts/Inter-Variable.ttf")
    .build()?;
let css = "body { font-family: 'Inter'; font-size: 11pt; }";
let (pdf, glyphs) = engine.render_with_glyph_report(html, css)?;
if !glyphs.missing().is_empty() {
    return Err("A character is not covered by the supplied fonts.".into());
}
std::fs::write("invoice.pdf", pdf)?;
```

Keep font license notices with redistributed assets. Register the additional
families and styles used by your CSS; the designed example registers all four
playground font files.

For one PNG per page, preview the PDF you just wrote at your chosen DPI:

```rust
for (index, png) in engine.render_finalized_pdf_image_pages("invoice.pdf", 96)?.iter().enumerate() {
    std::fs::write(format!("page-{}.png", index + 1), png)?;
}
```

This previews the finalized PDF, including its supported gradient fills. The
designed example and downloaded playground projects use the same path.

## Keep building

Use [the latest hosted Rust API reference](https://docs.rs/fullbleed/latest/fullbleed/)
for `FullBleed`, its builder, compiled templates, and document types. The
[2.5.11 source](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.5.11/src/lib.rs)
matches the version pinned by these examples. Check
[CSS coverage](../css-coverage.md) before adapting a web layout, and inspect
your actual output when changing fonts or content. These examples use trusted
local inputs; file and HTML handling should follow your application's trust
boundary.

[Runnable Rust source](https://github.com/fullbleed-engine/docs/tree/main/examples/rust)
· [More document designs](../examples.md)
· [Python quickstart](quickstart.md)
· [Ask a usage question](https://github.com/fullbleed-engine/fullbleed-official/discussions)

## Authorship and checks

This walkthrough was written by an AI coding agent for the Fullbleed project.
The [runnable Rust examples are compiled and rendered in documentation CI](https://github.com/fullbleed-engine/docs/actions/workflows/docs.yml),
where their fixture PDFs and PNG previews are compared with the playground's
output. See the [verification source](https://github.com/fullbleed-engine/docs/blob/main/tools/verify_rust_examples.py)
for the checks and their scope.
