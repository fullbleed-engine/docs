#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render the saved playground source with the bundled fonts."""
from importlib import metadata
import hashlib
import json
import os
from pathlib import Path
import re

import fullbleed

ROOT = Path(__file__).resolve().parent
FONTS = ["Inter-Variable.ttf", "DMSerifDisplay-Regular.ttf",
         "DMSerifDisplay-Italic.ttf", "BebasNeue-Regular.ttf"]


def main():
    html = (ROOT / "input.html").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    manifest = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
    local = manifest.get("localAssets", [])
    for asset in local:
        name = asset["path"]
        if not re.fullmatch(r"assets/[^/\\:\x00-\x1f]+", name) or name[7:] in (".", ".."):
            raise ValueError("Invalid local asset path in project.json")
    fonts = [str(ROOT / "fonts" / name) for name in FONTS]
    engine = fullbleed.PdfEngine(font_files=fonts)
    if any(asset.get("font") for asset in local):
        bundle = fullbleed.AssetBundle()
        for asset in local:
            if asset.get("font"):
                bundle.add_file(str(ROOT / asset["path"]), "font", name=asset["path"], trusted=True)
        engine.register_bundle(bundle)
    pdf = output / "document.pdf"
    previous = Path.cwd()
    try:
        os.chdir(ROOT)
        engine.render_pdf_to_file(html, css, str(pdf))
    finally:
        os.chdir(previous)
    previews = engine.render_finalized_pdf_image_pages_to_dir(str(pdf), str(output / "preview"), 96, "page")
    report = dict(engine=metadata.version("fullbleed"), pdf=str(pdf), pages=len(previews),
                  previews=list(previews), sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())
    (output / "render.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
