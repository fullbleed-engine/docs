from importlib.resources import files
from pathlib import Path
import fullbleed

here = Path(__file__).resolve().parent
output = here / "output"
output.mkdir(exist_ok=True)
html = (here / "shelf-card.html").read_text(encoding="utf-8")
font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
engine = fullbleed.PdfEngine(font_files=[str(font)])

for name, extra_css in (
    ("metric-card", ""),
    ("inch-card", "@page { size: 4in 6in; margin: 8mm; }"),
):
    pdf = output / f"{name}.pdf"
    pdf.write_bytes(engine.render_pdf(html, extra_css))
    engine.render_finalized_pdf_image_pages_to_dir(
        str(pdf), str(output / name), 144, name
    )
    print(pdf)
