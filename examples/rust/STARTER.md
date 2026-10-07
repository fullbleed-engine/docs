# Rust PDF starter

Generate a designed invoice and a three-page report from editable HTML/CSS.
This project includes the Rust source, a Cargo lockfile, four font faces, and
their license notices. The sample data is fictional.

## Run the invoice

Install a native Rust toolchain with a linker. The project declares Rust 1.85
as its minimum; the downloadable project is checked with Rust 1.97.0 on Windows
and Linux. No Python installation or browser is needed to render the documents.
Cargo downloads the pinned dependencies on the first build, so that build needs
internet access.

Extract the ZIP, open a terminal in `fullbleed-rust-starter`, and run:

```sh
cargo run --release --locked --bin from-files -- templates/invoice.html templates/invoice.css fonts output/invoice
```

Open `output/invoice/document.pdf` and `output/invoice/page-1.png`. The PNG is
rendered from the finalized PDF at 96 DPI. For the report:

```sh
cargo run --release --locked --bin from-files -- templates/report.html templates/report.css fonts output/report
```

Open `output/report/document.pdf` and its three page previews.

## Make it yours

Edit the HTML for the content and the CSS for typography, colors, tables, and
page layout. Then render to a new output directory:

```sh
cargo run --release --locked --bin from-files -- templates/invoice.html templates/invoice.css fonts output/edited-invoice
```

Use a new output directory when changing page counts: this small example does
not remove old preview files from an existing directory. Review every page
after changing content or styles. See the engine's
[supported CSS](https://docs.fullbleed.dev/css-coverage/) when adapting a web layout.

`src/from_files.rs` registers the four fonts explicitly and rejects characters
that the engine reports as missing. For another font, keep its license notice,
add its filename to the registration list, and use its family name in CSS.
Keep the font files beside the project when moving it.

The renderer takes trusted local paths and static HTML/CSS; it is not an HTTP
server or a sandbox. It does not execute document JavaScript. These examples
produce ordinary PDFs and do not select an accessibility or archival profile.

## Reuse the Rust API

`src/hello.rs` contains the smaller `FullBleed::builder()` and
`render_to_buffer()` example. Run it with:

```sh
cargo run --release --locked --bin hello
```

It writes `invoice.pdf` in the current directory. In an application, return the
PDF bytes from your handler or write them to your storage. Use the full
[Rust walkthrough](https://docs.fullbleed.dev/getting-started/rust/) for font
registration and preview details.

The project pins the published `fullbleed` crate to 2.5.11. `Cargo.lock` records
the resolved dependency versions. No local Fullbleed checkout is required.
The code and templates are MIT licensed; the fonts are SIL OFL 1.1.

This starter was assembled by an AI coding agent for Fullbleed from the
[checked Rust examples](https://github.com/fullbleed-engine/docs/tree/main/examples/rust).
The download is extracted, compiled, and rendered in documentation CI; its
checks cover the included fixtures and edited synthetic input.
