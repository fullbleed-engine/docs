# Fonts and assets

Keep document assets explicit and local so each render uses the same inputs. The project scaffold vendors Inter, Bootstrap CSS, and Bootstrap SVG icons, together with their license notices and an asset lockfile.

```bash
python -m fullbleed init my-report
python -m fullbleed assets list --json
```

## Register a font

```python
from importlib.resources import files
import fullbleed

font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
engine = fullbleed.PdfEngine(font_files=[str(font)])
pdf = engine.render_pdf(
    "<h1>Quarterly statement</h1>",
    "body { font-family: Inter; }",
)
```

Register your own font files or directories through the [Python API](pdf-engine.md#pdfengine). Check that the selected font contains the characters you use. The engine does not require a system-font installation.

Regular and italic faces can share a family name. For exact face mappings and
upgrade guidance, see [Font face selection](font-registration.md).

## Standard 14 native previews

Starting with engine 2.5.11, Fullbleed bundles fixed, OFL-licensed outline
substitutes for the unembedded PDF Standard 14 fonts: Helvetica, Times, Courier,
Symbol, and ZapfDingbats. Native previews can render these fonts without a system
font installation. Explicitly registered and embedded fonts retain precedence.

Check the installed Python runtime before relying on this behavior:

```python
import fullbleed

features = fullbleed.build_features()
print(features.get(
    "bundled_standard_font_previews",
    False,
))
```

The substitutes affect native preview pixels; they preserve the input PDF's font
resources, text, and advances. Review saved preview baselines when upgrading.
For a specific branded appearance in both the PDF and its preview, register your
chosen font files explicitly as shown above. Font-resolution traces report
`bundled_substitute` when the native renderer selects a bundled face.

The [2.5.11 verification evidence](https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.5.11)
includes 68 cases with identical preview pixels and PDF bytes on Windows, Linux,
and Linux with system fonts hidden. The [font manifest and coverage limits](https://github.com/fullbleed-engine/fullbleed-official/blob/v2.5.11/src/preview_fonts/README.md)
describe the substitute designs and the unsupported, unencoded Symbol `/apple`
glyph. [Node package 0.3.2](../getting-started/node.md) ships engine 2.5.11 and
includes these substitutes in both its Node and browser entries. Bindings have
separate engine version pins; check the version shipped with your binding.

## Images, SVG, and asset bundles

The [AssetBundle API](pdf-engine.md#assetbundle) provides explicit CSS, font, SVG, and raster asset registration. Use the [canonical reference project](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/canonical_reference) for complete examples of inline SVG, data URIs, vendored files, and image previews.

For Bootstrap icons, use the bundled SVG assets as demonstrated by the scaffold. An arbitrary web icon font or JavaScript icon loader is not automatically available to the document renderer.

## Inspect what was rendered

Check glyph reports and structured diagnostics, then inspect the finalized PDF preview. The [CLI reference](../cli/commands.md) covers asset installation and render diagnostics.
