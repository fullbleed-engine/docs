---
title: Community projects using Fullbleed
description: Explore independent Ruby bindings, workflow automation, binary-analysis reports, and dataset documentation built around Fullbleed's Rust engine.
---

# Community projects

Read how other projects connect Fullbleed to their own applications. The links
below point to public source inspected on **November 1, 2026**, including each
project's dependency declaration and rendering code.

These projects are maintained by their respective authors. Source integration
does not establish production deployment, an endorsement, or compatibility with
the latest Fullbleed release. Follow each project's own setup, license, and
support information; these integrations are not part of Fullbleed's release tests.

## PDF generation in Betty Blocks

[Betty Blocks' native WebAssembly components](https://github.com/bettyblocks/native-wasm-components)
include a **Generate PDF** action. It applies variables to a Liquid template,
renders the resulting HTML inside the component, and stores the PDF in a model's
file property.

The integration prepares linked stylesheets, images, and fonts before calling
Fullbleed. Resource fetching belongs to that application layer; the rendering
engine itself does not fetch those URLs.

- [Action documentation](https://github.com/bettyblocks/native-wasm-components/blob/3b575d15adc7077122a913210105dfbbcf536bfc/functions/generate-pdf/1.0/README.md)
- [HTML preparation and PDF rendering](https://github.com/bettyblocks/native-wasm-components/blob/3b575d15adc7077122a913210105dfbbcf536bfc/functions/generate-pdf/1.0/src/pdf/mod.rs)
- [Fullbleed dependency](https://github.com/bettyblocks/native-wasm-components/blob/3b575d15adc7077122a913210105dfbbcf536bfc/functions/generate-pdf/1.0/Cargo.toml)

## Binary-analysis reports in RBAT

[RBAT](https://github.com/Heritage-XioN/rbat) is a binary-analysis tool with a
PDF report exporter. Its report module puts analysis results into an Askama HTML
template and passes the HTML and report CSS to Fullbleed. It also preserves an
HTML fallback when PDF rendering fails.

- [Report exporter](https://github.com/Heritage-XioN/rbat/blob/a3c84608bf65fc63f8c2c6e62ae3995f31204463/crates/rbat-cli/src/report/pdf.rs)
- [CLI dependencies](https://github.com/Heritage-XioN/rbat/blob/a3c84608bf65fc63f8c2c6e62ae3995f31204463/crates/rbat-cli/Cargo.toml)

## Dataset documentation in Davis

[Davis](https://github.com/bin-utokyo/davis) uses Fullbleed for English and
Japanese schema-document PDFs. Its document crate registers bundled Inter and
Japanese fonts, shares an engine through `OnceLock`, and writes PDF files only
when their bytes change. The source includes a repeated-output test.

- [Schema-document generator](https://github.com/bin-utokyo/davis/blob/343d4d27537b7809638140df082901a1d9c7dab9/crates/davis-document/src/lib.rs)
- [Workspace dependency declaration](https://github.com/bin-utokyo/davis/blob/343d4d27537b7809638140df082901a1d9c7dab9/Cargo.toml)

## Ruby bindings

[mitsuru/fullbleed-ruby](https://github.com/mitsuru/fullbleed-ruby) wraps the
Rust engine as a Ruby native extension using Magnus. Its rendering methods call
Fullbleed to produce PDF bytes or write a PDF file.

This is an independent binding, separate from the packages maintained in the
Fullbleed organization. Its RubyGems installation instructions have an
[open clarification request](https://github.com/mitsuru/fullbleed-ruby/issues/1).
Check that issue for installation status before following the wrapper's README.

- [Ruby API documentation](https://github.com/mitsuru/fullbleed-ruby/blob/3c57bb9d6b83e80ec98f17d246ff565431e74a8b/README.md)
- [Native rendering bridge](https://github.com/mitsuru/fullbleed-ruby/blob/3c57bb9d6b83e80ec98f17d246ff565431e74a8b/ext/fullbleed/src/engine.rs)
- [Engine dependency](https://github.com/mitsuru/fullbleed-ruby/blob/3c57bb9d6b83e80ec98f17d246ff565431e74a8b/ext/fullbleed/Cargo.toml)

## Build your integration

Start with a tested [Rust example](../getting-started/rust.md),
[web-framework starter](web-frameworks.md), or
[n8n invoice workflow](n8n-pdf.md). Keep template processing, resource retrieval,
and application storage in your application; provide the engine with explicit
HTML, CSS, and assets.

To share a public integration or correct a listing, use
[Fullbleed Discussions](https://github.com/fullbleed-engine/fullbleed-official/discussions).
Include its repository and the document workflow it supports.
