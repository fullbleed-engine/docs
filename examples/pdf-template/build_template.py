"""Rebuild the supplied blank PDF from its editable HTML/CSS artwork."""
import argparse
from importlib.resources import files
from pathlib import Path
import fullbleed


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="New PDF path")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Choose a new output path; the source template will not be overwritten.")
    engine = fullbleed.PdfEngine(font_files=[str(files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf"))])
    pdf, missing = engine.render_pdf_with_glyph_report((root / "template.html").read_text(encoding="utf-8"), (root / "template.css").read_text(encoding="utf-8"))
    if missing:
        raise ValueError("The template font is missing required glyphs.")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(bytes(pdf))
    print(args.out)


if __name__ == "__main__":
    main()
