# Yew components to PDF and HTML

Write a document as Rust components, then export a PDF, styled browser HTML,
or HTML without a stylesheet. The sample is a fictional event schedule with
levels and break rows. It is useful for learning the rendering path; supply
your own event data and rules for an actual structure sheet.

The example pins Fullbleed 2.5.34, Yew 0.23.0 and Tokio 1.54.1. Its fonts and
their license notices are included. PDF rendering does not launch a browser
or use system fonts. Yew is a dependency of this example, not of Fullbleed.

## Run

With a native Rust toolchain installed, run from this directory:

```sh
cargo run --release --locked -- data.json output
```

The first build needs internet access to download Cargo dependencies. Open:

- `output/document.pdf`: the print document.
- `output/document.html`: the styled browser document.
- `output/unstyled.html`: the same content and classes without a stylesheet.
- `output/page-1.png`: a preview of the finalized PDF; longer documents have
  one PNG per page.

Keep `style.css` and the `fonts` directory beside the styled HTML when copying
the export. Keep font license notices when redistributing the fonts. Choose a
new output directory for each run; the program refuses to overwrite one.

## Change the content and design

Edit `data.json` to change the title, event settings, levels, breaks and notes.
`SheetData` and `ScheduleRow` in `src/document.rs` define the input types. Text is
passed through Yew's ordinary text nodes, which escape HTML markup.

`StructureSheet` is the reusable component. For example, its
`class="masthead"` attribute selects `.masthead` in `style.css`. Edit that
rule to change the title panel, or add your own classes and CSS rules. The
stylesheet is read at run time, so design edits do not require recompiling
the Rust component. Screen rules provide a responsive page and a horizontally
scrollable table on narrow displays; print rules supply the paper layout.

The `to_html(data, styled)` function renders `SheetDocument` through
`yew::ServerRenderer`, with hydration disabled. `styled = true` includes a link
to `style.css`; `false` leaves that link out while preserving the content and
classes. Fullbleed receives the unstyled HTML and the CSS separately to create
the PDF. The browser HTML works without Fullbleed or JavaScript after export.

When adding a font, register its bytes in the `AssetBundle`, add the matching
browser `@font-face` rule, and include its license notice. This example checks
the renderer's missing-glyph report before writing its outputs.

## Reuse in an application

The public `StructureSheet` component and native `to_html` function live in
`src/document.rs`, which depends on Yew and Serde, independently of Fullbleed.
`src/main.rs` handles files, fonts and PDF rendering. The document component
can be shared with an existing Yew application when
it can render from props without browser-only APIs. The PDF path needs the
resulting static HTML; it does not execute a client-side Yew application or
load a live webpage. In a web service, run synchronous PDF rendering outside
the asynchronous request executor and apply the service's own input limits.

The `to_html` helper is excluded from browser WASM builds. The shared document
module can therefore use Yew's `csr` feature in a browser project and its `ssr`
feature in the native renderer. Yew currently describes SSR as experimental;
the checks for this sample cover its pinned versions and fixtures.

See [Yew's server-rendering guide](https://yew.rs/docs/advanced-topics/server-side-rendering)
and [Fullbleed's Rust guide](https://docs.fullbleed.dev/getting-started/rust/)
for the two APIs involved. Browser layout and paginated PDF layout should be
reviewed independently when changing a design.

This example was authored and checked by an AI coding agent for the Fullbleed
project. Its data is synthetic; it is not an integration with a third-party
application.
