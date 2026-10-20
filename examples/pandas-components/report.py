#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render a pandas report with the experimental Fullbleed 2.6.0a9 components."""
from __future__ import annotations

import argparse
from hashlib import sha256
from importlib import metadata, resources
import json
from pathlib import Path
import shutil

import fullbleed
from fullbleed.ui.experimental import (
    Document, Flow, Grid, Heading, Page, PageBand, PageNumbers,
    Paragraph, Renderer, Strong, mm, pt, style, token,
)
from components import Brand, Kicker, Ledger, Metric, Small, THEME
from data import dollars, load_products, totals


def build_report(frame, *, title="The product edit.", period="September 2026"):
    """Convert a validated frame to a frozen document without mutating the frame."""
    summary = totals(frame)
    return Document(
        Flow(
            Kicker(f"Monthly inventory / {period}"),
            Heading(title, level=1, style=style(font_size=pt(34), line_height=1.08, letter_spacing=pt(-1))),
            Paragraph("A clear view of the collection: product activity, net sales, and the latest restock dates."),
            Grid(
                Metric(f'{summary["products"]:,}', "products in the collection"),
                Metric(f'{summary["units"]:,}', "units sold"),
                Metric(dollars(summary["cents"]), "net sales · USD").with_parts(value=style(color=token("accent"))),
                columns=3, gap=pt(10),
            ),
            Small(f'{summary["categories"]} categories · Input order is preserved · Fictional sample data'),
            Ledger(frame.to_dict(orient="records")),
            Small(Strong("Reading this report. "), "Net sales may include signed adjustments. Blank restock dates appear as “Not recorded”. Figures describe this input file, not a live inventory system."),
            gap=pt(12),
        ),
        title=f"Gridline — {title} — {period}", lang="en-US", theme=THEME,
        page=Page("A4", landscape=True, margin=(mm(20), mm(16), mm(19), mm(16)),
                  header=PageBand(left=Brand(), right=Small(period)),
                  footer=PageBand(left=Small("GRIDLINE / FICTIONAL DATA"),
                                  right=PageNumbers(total=True, prefix="", separator=" / ", class_name="folio"))),
        styles={
            ".ledger tbody tr:nth-child(even)": style(background="#f5f7f2"),
            ".folio": style(font_size=pt(8), color=token("muted")),
        },
    )


def render(frame, out: Path, *, title="The product edit.", period="September 2026", previews=False):
    out.mkdir(parents=True, exist_ok=True)
    font = Path(str(resources.files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")))
    document = build_report(frame, title=title, period=period)
    renderer = Renderer(font_files=[str(font)], pdf_profile="tagged", document_timestamp="2026-10-20T00:00:00Z")
    source = document.compile(a11y_mode="raise", target="pdf")
    prepared = document.prepare(renderer, a11y_mode="raise")
    pdf = prepared.render_pdf()
    path = out / "report.pdf"
    path.write_bytes(pdf)
    for styled, filename in ((True, "report.html"), (False, "report-unstyled.html")):
        html = document.to_html(include_styles=styled, a11y_mode="raise")
        if styled:
            # Font loading and screen framing belong to the export boundary.
            # The document itself is authored entirely with Python components.
            html = html.replace("</head>", '''<style>
@font-face {font-family:Inter;src:url("fonts/Inter-Variable.ttf");font-weight:100 900}
@media screen {
  body {max-width:1060px;margin:auto;padding:24px}
  [data-fb-flow] > * + * {margin-top:16px}
  [data-fb-page-band] {margin:12px 0 28px}
  footer[data-fb-page-band] {margin-top:28px}
}
</style></head>''', 1)
        (out / filename).write_text(html, encoding="utf-8", newline="\n")
    (out / "fonts").mkdir(exist_ok=True)
    shutil.copyfile(font, out / "fonts" / font.name)
    shutil.copyfile(Path(__file__).with_name("Inter-OFL.txt"), out / "fonts/Inter-OFL.txt")
    inspection = fullbleed.inspect_pdf(str(path))
    if previews:
        renderer.engine_for(document).render_finalized_pdf_image_pages_to_dir(
            str(path), str(out / "previews"), dpi=110)
    report = {
        "schema": "fullbleed.pandas_components_example.v1",
        "fullbleed": metadata.version("fullbleed"), "pandas": metadata.version("pandas"),
        "rows": len(frame), "totals": totals(frame), "page_count": inspection["page_count"],
        "pdf_sha256": sha256(pdf).hexdigest(), "font_sha256": sha256(font.read_bytes()).hexdigest(),
        "profile": "tagged", "timestamp": "2026-10-20T00:00:00Z",
        "validation_scope": "Source structural checks and native layout checks; no PDF/UA conformance claim.",
    }
    for name, value in (("render-report.json", report), ("a11y-source.json", source.a11y_report),
                        ("pagination.json", prepared.export_render_time_pagination_trace()), ("inspection.json", inspection)):
        (out / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=Path(__file__).with_name("products.csv"))
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("output"))
    parser.add_argument("--title", default="The product edit.")
    parser.add_argument("--period", default="September 2026")
    parser.add_argument("--previews", action="store_true")
    args = parser.parse_args()
    print(json.dumps(render(load_products(args.csv), args.out.resolve(), title=args.title,
                            period=args.period, previews=args.previews)), flush=True)


if __name__ == "__main__":
    main()
