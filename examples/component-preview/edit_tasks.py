"""Five small component-editing tasks. Change the functions and rerun this file."""
from importlib.resources import files
import argparse
import json
from pathlib import Path
import sys

from fullbleed.ui.experimental import (
    Box, Column, DataTable, Document, Flow, Heading, LayoutError, Page, Paragraph,
    Renderer, component, mm, pt, style, styled, token,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "examples/component_recipes"))
from documents import Invoice
from kit import Field, STUDIO_THEME, Total, WorkCell, money


def shared_components(data):
    theme = STUDIO_THEME.with_values(accent="#9a462e")
    customer = Field("Prepared for", data["customer"]).with_parts(label=style(color="#9a462e"))
    return Document(
        Flow(Heading("Made for your next project", level=1), customer, Total(data["items"]), gap=pt(20)),
        title="Shared components, new brand", theme=theme, page=Page("A5", margin=mm(16)),
    )


def extra_column(data):
    return Document(
        DataTable(data["items"], caption="Cost per project", columns=[
            Column("Project", WorkCell),
            Column("Hours", lambda item: item["quantity"], align="right", width=mm(20)),
            Column("Amount", lambda item: money(item["quantity"] * item["rate_cents"]), align="right", width=mm(30)),
        ]),
        title="A column owns its header and cells", theme=STUDIO_THEME,
    )


def paper_change(data):
    return Invoice(data, page=Page("LETTER", margin=mm(18)))


def selector_styles():
    Notice = styled(Paragraph, font_size=pt(16), color="#a0442e")
    shared = Notice("Shared class: blue", class_name="notice")
    custom = Notice("One instance: rust", class_name="notice").with_style(color="#a0442e")
    return Document(
        Flow(shared, custom, gap=pt(16)),
        title="Classes and instance overrides", theme=STUDIO_THEME,
        page=Page("A5", margin=mm(16)),
        styles={".notice": style(color=token("accent"))},
    )


@component
def Notice():
    return Box(Paragraph("A long notice can continue when its container permits it.")).with_style(
        height=pt(900), overflow="hidden", background="#f2f5f8", padding=pt(14),
    )


def layout_repair(renderer, output):
    notice = Notice()
    broken = Document(notice, title="A clipping constraint", theme=STUDIO_THEME)
    try:
        broken.render_pdf(renderer)
    except LayoutError as error:
        # Keep useful authored paths; omit machine-specific definition filenames.
        report = {"code": error.code, "reason": error.reason, "path": list(error.path),
                  "message": error.message,
                  "failure_sources": [list(source.path) for source in error.failure_sources]}
        (output / "expected-layout-error.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("Expected layout error:", error.code, error.reason, "/".join(error.path))
    else:
        raise AssertionError("The oversized clipped notice should be rejected")
    return Document(notice.with_style(height="auto", overflow="visible"),
                    title="Clipping constraint repaired", theme=STUDIO_THEME)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "output/edits")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    data = json.loads((HERE / "examples/components/data.json").read_text(encoding="utf-8"))
    renderer = Renderer(font_files=[str(files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf"))],
                        document_timestamp="2026-10-15T00:00:00Z")
    documents = [("shared-components", shared_components(data)), ("extra-column", extra_column(data)),
                 ("letter-invoice", paper_change(data)), ("selector-styles", selector_styles()),
                 ("repaired-notice", layout_repair(renderer, args.output))]
    for name, document in documents:
        prepared = document.prepare(renderer)
        (args.output / f"{name}.pdf").write_bytes(prepared.render_pdf())
        for number, png in enumerate(prepared.render_image_pages(dpi=96), 1):
            (args.output / f"{name}-{number}.png").write_bytes(png)
        print(name, "theme tokens:", document.required_tokens)


if __name__ == "__main__":
    main()
