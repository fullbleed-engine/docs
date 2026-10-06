# Registering regular and italic fonts

Reference imported from [v2.5.8](https://github.com/fullbleed-engine/fullbleed-official/blob/f9f1b56f550237c924254ccd7718cc852a06692d/docs/font-registration.md). Check the installed runtime for your exact version.

Register the font files your document uses with `PdfEngine(font_files=[...])`,
`font_dirs=[...]`, or an `AssetBundle`. Fullbleed reads these assets directly;
it does not search system fonts.

The [Chinese-text guide](../guides/chinese-pdf.md) includes a runnable bilingual
invoice, pinned font preparation, and the current variable-font weight and
glyph-report limitations.

When regular and italic faces share a family name, normal text selects the
regular face even if the italic file was registered first. The default family
face prefers upright fonts, then the CSS weight-400 fallback order: 400 through
500, lighter weights descending, and heavier weights ascending. Both legacy
and typographic family names are recognized.

For example, after registering `DMSerifDisplay-Regular.ttf` and
`DMSerifDisplay-Italic.ttf` from this repository's
[`design_showcase/fonts`](https://github.com/fullbleed-engine/fullbleed-official/blob/f9f1b56f550237c924254ccd7718cc852a06692d/examples/design_showcase/fonts):

```css
body { font-family: "DM Serif Display"; font-style: normal; }
em { font-style: italic; }
```

Use explicit `@font-face` mappings when a document needs to choose exact source
faces, including fonts whose variant names differ from the family name:

```css
@font-face {
  font-family: "Brand";
  src: local("DMSerifDisplay-Regular");
  font-style: normal;
  font-weight: 400;
}
@font-face {
  font-family: "Brand";
  src: local("DMSerifDisplay-Italic");
  font-style: italic;
  font-weight: 400;
}
body { font-family: "Brand"; }
```

Here, `local()` refers to a font already registered with the engine. PostScript
names, full face names, and supplied source aliases remain available for exact
selection. Duplicate explicit aliases and equally ranked family faces retain
the first registration. Directory entries are processed in sorted path order;
use an explicit file list when duplicate fonts need a particular priority.

Starting with 2.5.8, documents that accidentally used an italic or bold family
default can change appearance and line breaks when the regular face is also
registered. Review existing PDF baselines when upgrading. To intentionally use
italics, set `font-style: italic` or map the exact face with `@font-face`.

The installed-wheel [family smoke check](https://github.com/fullbleed-engine/fullbleed-official/blob/f9f1b56f550237c924254ccd7718cc852a06692d/tools/smoke_font_families.py)
compares embedded face names, extracted text, and native/PDFium previews against
explicit-face controls for file, directory, bundle, fixed-template, and reflow
rendering. This is a focused regression check, not a claim of complete CSS font
matching conformance.
