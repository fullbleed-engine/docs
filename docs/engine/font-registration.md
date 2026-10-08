# Registering regular and italic fonts

Reference imported from [v2.5.16](https://github.com/fullbleed-engine/fullbleed-official/blob/1813df2150cbad6213dff78963df77a1c3e1c096/docs/font-registration.md). Check the installed runtime for your exact version.

Register the font files your document uses with `PdfEngine(font_files=[...])`,
`font_dirs=[...]`, or an `AssetBundle`. Fullbleed reads these assets directly;
it does not search system fonts.

The [Chinese-text guide](../guides/chinese-pdf.md) includes a runnable bilingual
invoice, pinned font preparation, and the current variable-font weight and
glyph-report limitations.
The [Arabic and English invoice](../guides/arabic-pdf.md) includes static regular
and bold Noto Sans Arabic files with a font manifest and glyph checks.

When regular and italic faces share a family name, normal text selects the
regular face even if the italic file was registered first. The default family
face prefers upright fonts, then the CSS weight-400 fallback order: 400 through
500, lighter weights descending, and heavier weights ascending. Both legacy
and typographic family names are recognized.

For example, after registering `DMSerifDisplay-Regular.ttf` and
`DMSerifDisplay-Italic.ttf` from this repository's
[`design_showcase/fonts`](https://github.com/fullbleed-engine/fullbleed-official/tree/1813df2150cbad6213dff78963df77a1c3e1c096/examples/design_showcase/fonts):

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

The installed-wheel [family smoke check](https://github.com/fullbleed-engine/fullbleed-official/blob/1813df2150cbad6213dff78963df77a1c3e1c096/tools/smoke_font_families.py)
compares embedded face names, extracted text, and native/PDFium previews against
explicit-face controls for file, directory, bundle, fixed-template, and reflow
rendering. This is a focused regression check, not a claim of complete CSS font
matching conformance.

## Controlling synthetic styles

Starting with Fullbleed 2.5.16, weight and style synthesis can be controlled
independently. When the selected registered face lacks a requested bold or
slanted style, `font-synthesis` controls which approximations Fullbleed may draw:

```css
/* Allow synthetic italics only. */
.label {
  font-weight: 700;
  font-style: italic;
  font-synthesis: style;
}

/* Allow synthetic bold only. */
.total {
  font-weight: 700;
  font-style: italic;
  font-synthesis: weight;
}

/* Disable all synthetic variants. */
.exact { font-synthesis: none; }

/* Disable artificial slant alone. */
.upright { font-synthesis-style: none; }
```

The shorthand independently sets `weight`, `style`, `small-caps`, and `position`;
omitted controls become `none`. The longhands `font-synthesis-weight`,
`font-synthesis-style`, `font-synthesis-small-caps`, and `font-synthesis-position`
accept `auto` or `none`. The style longhand also accepts `oblique-only`, which
permits a synthetic `font-style: oblique` but does not synthesize an italic
request. These properties inherit. `initial` restores all synthesis controls;
`auto` is a longhand value, not a valid shorthand value.

The controls do not suppress a real bold or italic face already selected by
font matching. SVG text inherits the document's weight/style controls and
supports overrides in its own inline and embedded CSS. Small-cap controls govern
HTML's existing synthetic small caps; position controls govern the default
footnote-call superscript fallback. They do not add general OpenType small-cap
or positional-substitution support.

Synthetic small caps with fixed binding slots remain unsupported; use compiled
reflow for those templates. The finalized-PDF preview reader can also omit the
synthetic-bold stroke on fixed binding slots; inspect the emitted PDF in an
independent viewer when using that combination.

The [synthesis smoke check](https://github.com/fullbleed-engine/fullbleed-official/blob/1813df2150cbad6213dff78963df77a1c3e1c096/tools/smoke_font_synthesis.py)
registers a known regular font and compares each combination with explicit style
controls in ordinary, fixed, and reflow output. It retains 130 cases / 221 pages,
with PDFs, extracted text, and native, finalized, and PDFium previews; small-cap
positive controls cover ordinary and reflow output. All 130 PDFs and preview
case sets match across Windows and Linux in the release-preparation CI.

[Download the executable evidence bundle](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.5.16/fullbleed-2.5.16-font-synthesis-evidence.zip),
inspect the [verification record](https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.5.16/fullbleed-2.5.16-verification.json),
or read the [2.5.16 release notes](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.5.16).
The comparisons verify the named controls, not complete CSS Fonts conformance.
