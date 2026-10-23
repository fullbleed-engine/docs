"""Compose two separately defined kits without reaching into their selectors."""
import argparse
from hashlib import sha256
from importlib.metadata import version
from importlib.resources import files
import json
from pathlib import Path

from fullbleed.components import (
    Column, DataTable, Document, Flow, Grid, Heading, Page, Paragraph,
    Renderer, Theme, mm, pct, pt, style, styled,
)

from billing import BillingPalette, billing_kit
from impact import IMPACT_DEFAULTS, Impact

PIN = "2.6.0a14"
VARIANTS = ("default", "billing-brand", "impact-brand", "local-override")
INK = "#233a37"
MUTED = "#5a6a66"


def report(variant="default"):
    if variant not in VARIANTS:
        raise ValueError(f"Unknown variant: {variant}")
    palette = (BillingPalette(accent="#7047a1", surface="#f3eef8", ink="#483461")
               if variant == "billing-brand" else BillingPalette())
    Balance = billing_kit(palette)
    theme = Theme(IMPACT_DEFAULTS, text=style(
        font_family="Inter, sans-serif", font_size=pt(10), line_height=1.5, color=INK))
    if variant == "impact-brand":
        theme = theme.with_values({"impact.accent": "#a34e21",
                                   "impact.surface": "#faf0e8", "impact.ink": "#673d29"})
    impact = Impact("COMMUNITY REACH", "128", "people joined a workshop this month")
    if variant == "local-override":
        impact = impact.with_parts(value=style(color="#9b3d64"))

    Kicker = styled(Paragraph, font_size=pt(8), letter_spacing=pt(1.2),
                    font_weight=700, color=MUTED, margin=pt(0))
    Title = styled(Heading, font_size=pt(32), line_height=1.08,
                   letter_spacing=pt(-0.8), margin=pt(0))
    Section = styled(Heading, font_size=pt(14), margin=pt(0))
    Body = styled(Paragraph, margin=pt(0))
    Metrics = styled(Grid, grid_template_columns="1fr 1fr", gap=mm(5))
    rows = (
        {"area": "Member workshops", "next": "Open the November calendar", "owner": "Program team"},
        {"area": "Community grants", "next": "Review the next four applications", "owner": "Finance team"},
        {"area": "Studio access", "next": "Add two evening sessions", "owner": "Operations"},
    )
    return Document(
        Flow(
            Kicker("CEDAR COOPERATIVE / OCTOBER 2026"),
            Title("A shared view.\nRoom for every team.", level=1),
            Body("Our monthly briefing brings finance and community programs together. "
                 "Each team keeps its own visual identity inside one consistent document."),
            Metrics(
                Balance("COMMUNITY FUND", "$24,600", "available for the next funding round"),
                impact, class_name="report-metrics",
            ),
            Section("The next month, at a glance", level=2),
            DataTable(rows, caption="November action plan", columns=(
                Column("Focus", lambda row: row["area"], width=pct(25)),
                Column("Next step", lambda row: row["next"]),
                Column("Owner", lambda row: row["owner"], width=pct(20)),
            )).with_parts(
                header=style(background="#233a37", color="#ffffff", font_size=pt(8)),
                cell=style(font_size=pt(9), padding=(pt(11), pt(9))),
                caption=style(font_size=pt(8), color=MUTED),
            ),
            Flow(
                Section("One report. Two reusable kits.", level=2),
                Body("The finance card receives a palette when its kit is created. "
                     "The community card declares three document theme values. "
                     "Neither needs the other kit's implementation details."),
                Body("SYNTHETIC EXAMPLE / No real financial or participant data.",
                     style=style(font_size=pt(7), color=MUTED)),
                gap=pt(7),
            ),
            gap=pt(18),
        ),
        title="Cedar Cooperative — October briefing", lang="en-US",
        page=Page("A4", margin=mm(18)), theme=theme,
        styles="""
            @media print {
                body { margin: 0; padding: 0; }
            }
            @media screen {
                body { max-width: 174mm; margin: 24px auto; padding: 16px; }
            }
            @media screen and (max-width: 600px) {
                .report-metrics { grid-template-columns: 1fr; }
            }
        """,
    )


def renderer():
    font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
    return Renderer(font_files=[str(font)], document_timestamp="2026-10-23T00:00:00Z")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "output")
    args = parser.parse_args()
    installed = version("fullbleed")
    if installed != PIN:
        raise RuntimeError(f"This example is qualified with fullbleed=={PIN}; found {installed}.")
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for variant in VARIANTS:
        document = report(variant)
        prepared = document.prepare(renderer())
        pdf = prepared.render_pdf()
        (args.output / f"{variant}.pdf").write_bytes(pdf)
        images = prepared.render_image_pages(dpi=108)
        for index, image in enumerate(images, start=1):
            (args.output / f"{variant}.native-{index}.png").write_bytes(image)
        trace = prepared.export_render_time_pagination_trace()
        (args.output / f"{variant}.pagination.json").write_text(
            json.dumps(trace, indent=2) + "\n", encoding="utf-8")
        for suffix, with_styles in (("html", True), ("unstyled.html", False)):
            (args.output / f"{variant}.{suffix}").write_text(
                document.to_html(include_styles=with_styles), encoding="utf-8")
        # Keep native print source separate from continuous browser HTML.
        document.emit_artifacts(html_path=args.output / f"{variant}.print.html",
                                css_path=args.output / f"{variant}.print.css", target="pdf")
        records.append({"variant": variant, "pdf_sha256": sha256(pdf).hexdigest(),
                        "pages": len(images),
                        "required_tokens": list(document.required_tokens)})
    result = {"version": installed, "documents": records}
    (args.output / "render.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
