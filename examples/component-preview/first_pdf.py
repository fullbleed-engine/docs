from importlib.resources import files
from pathlib import Path
from fullbleed.ui.experimental import (
    Document, Flow, Heading, Page, Paragraph, Renderer, Stack, component, mm, pt,
)

@component
def Field(label: str, value: str):
    return Stack(
        Paragraph(label).with_style(font_size=pt(8), color="#667580"),
        Paragraph(value),
        gap=pt(4),
    )

body = Flow(
    Heading("Project summary", level=1),
    Field("Prepared for", "Maple & Finch"),
    Field("Status", "Ready for review"),
    gap=pt(14),
).with_style(font_family="Inter", font_size=pt(11), color="#263b46")
document = Document(body, title="Project summary", page=Page("A5", margin=mm(16)))
font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
renderer = Renderer(font_files=[str(font)])
Path("summary.pdf").write_bytes(document.render_pdf(renderer))
