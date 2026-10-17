from pathlib import Path
from fullbleed.ui.experimental import Document, style
from fullbleed.ui.experimental import bootstrap as bs

rows = [{"item": "Studio notebook", "quantity": 24, "amount": "$360.00"}]
card = bs.Card(
    bs.DataTable(
        rows,
        columns=[
            bs.Column("Item", lambda row: row["item"]),
            bs.Column("Quantity", lambda row: row["quantity"], align="right"),
            bs.Column("Amount", lambda row: row["amount"], align="right"),
        ],
        striped=True,
    ),
    title="Ready to ship",
    header="ORDER / 1048",
    footer=bs.Badge("Approved", variant="success"),
    class_name="mb-3",
).with_parts(title=style(color="#205b47"))

document = Document(card, title="Order summary")
Path("order.html").write_text(document.to_html(include_styles=True), encoding="utf-8", newline="\n")
Path("order.unstyled.html").write_text(document.to_html(include_styles=False), encoding="utf-8", newline="\n")

from importlib.resources import files
from fullbleed.ui.experimental import Renderer, Theme, pt

document = Document(card, title="Order summary", theme=Theme(text=style(font_family="Inter", font_size=pt(11))))
font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
renderer = Renderer(font_files=[str(font)], document_timestamp="2026-04-30T00:00:00Z")
Path("order.pdf").write_bytes(document.render_pdf(renderer))
