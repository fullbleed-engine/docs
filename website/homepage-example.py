from importlib.resources import files
from pathlib import Path
import fullbleed
from fullbleed.ui import Document, Heading, Paragraph, Stack, Strong

@Document(title="Order summary", styles={
    "@page": {"size": "A4", "margin": "18mm"},
    "body": {"font_family": "Inter", "color": "#18372e"},
    "h1": {"font_size": "32pt", "margin": 0},
    "p": {"margin": 0},
})
def OrderSummary(customer):
    return Stack(
        Heading("Made for you", level=1),
        Paragraph("Prepared for ", Strong(customer)),
        gap="12pt",
    )

font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
engine = fullbleed.PdfEngine(font_files=[str(font)])
order = OrderSummary("Moss & Fern")
Path("order.pdf").write_bytes(order.render_pdf(engine))
