#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render the saved playground source with the bundled fonts."""
from importlib import metadata
import hashlib
import json
from pathlib import Path

import fullbleed

ROOT = Path(__file__).resolve().parent
FONTS = ["Inter-Variable.ttf", "DMSerifDisplay-Regular.ttf",
         "DMSerifDisplay-Italic.ttf", "BebasNeue-Regular.ttf"]


def main():
    html = (ROOT / "input.html").read_text(encoding="utf-8")
    css = (ROOT / "style.css").read_text(encoding="utf-8")
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    engine = fullbleed.PdfEngine(font_files=[str(ROOT / "fonts" / name) for name in FONTS])
    pdf = output / "document.pdf"
    engine.render_pdf_to_file(html, css, str(pdf))
    previews = engine.render_finalized_pdf_image_pages_to_dir(str(pdf), str(output / "preview"), 96, "page")
    report = dict(engine=metadata.version("fullbleed"), pdf=str(pdf), pages=len(previews),
                  previews=list(previews), sha256=hashlib.sha256(pdf.read_bytes()).hexdigest())
    (output / "render.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
