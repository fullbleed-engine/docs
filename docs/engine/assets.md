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

## Images, SVG, and asset bundles

The [AssetBundle API](pdf-engine.md#assetbundle) provides explicit CSS, font, SVG, and raster asset registration. Use the [canonical reference project](https://github.com/fullbleed-engine/fullbleed-official/tree/v2.4.0/examples/canonical_reference) for complete examples of inline SVG, data URIs, vendored files, and image previews.

For Bootstrap icons, use the bundled SVG assets as demonstrated by the scaffold. An arbitrary web icon font or JavaScript icon loader is not automatically available to the document renderer.

## Inspect what was rendered

Check glyph reports and structured diagnostics, then inspect the finalized PDF preview. The [CLI reference](../cli/commands.md) covers asset installation and render diagnostics.
