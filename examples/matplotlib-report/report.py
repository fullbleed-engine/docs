"""Compose a two-page PDF from Matplotlib SVG charts and editable HTML/CSS."""
from hashlib import sha256
from html import escape
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
import argparse
import json

import fullbleed
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.text import Text
from matplotlib.ticker import FuncFormatter, MaxNLocator

ROOT = Path(__file__).resolve().parent
INK, TEAL, MUTED, GRID = "#162838", "#236a67", "#61727c", "#d4dfe2"


def load_data(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("organization", "period", "title"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"{key} must be nonempty text")
    for key, minimum, maximum, amounts in (
        ("months", 2, 12, ("delivered", "planned")),
        ("regions", 1, 6, ("delivered",)),
    ):
        rows = data.get(key)
        if not isinstance(rows, list) or not minimum <= len(rows) <= maximum:
            raise ValueError(f"{key} must contain {minimum} to {maximum} records")
        labels = set()
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("label"), str) or not row["label"].strip():
                raise ValueError(f"Each {key} record needs a nonempty label")
            if row["label"] in labels:
                raise ValueError(f"Duplicate {key} label: {row['label']}")
            labels.add(row["label"])
            for amount in amounts:
                if type(row.get(amount)) is not int or row[amount] < 0:
                    raise ValueError(f"{key}.{amount} must be a nonnegative integer")
    if sum(row["delivered"] for row in data["regions"]) != data["months"][-1]["delivered"]:
        raise ValueError("Regional deliveries must sum to the final month's delivered count")
    return data


def save_chart(fig, name, out, font_path):
    # Explicit font file: Matplotlib does not need a machine-installed font.
    for text in fig.findobj(Text):
        text.set_fontproperties(FontProperties(fname=str(font_path), size=text.get_fontsize()))
        text.set_parse_math(False)
        text.set_usetex(False)
    with matplotlib.rc_context({"svg.fonttype": "path", "svg.hashsalt": "fullbleed-matplotlib-report"}):
        fig.savefig(out / (name + ".svg"), format="svg", metadata={"Date": None, "Creator": "Fullbleed Matplotlib example"})
        # Reference image for visual review, never embedded in the PDF.
        fig.savefig(out / (name + "-reference.png"), dpi=144)
    fig.clear()


def style_axes(ax, direction="y"):
    ax.set_axisbelow(True)
    ax.grid(axis=direction, color=GRID, linewidth=.6)
    ax.tick_params(axis="both", length=0, labelsize=9, colors=MUTED, pad=8)
    for spine in ax.spines.values():
        spine.set_visible(False)


def charts(data, out, font_path):
    months, regions = data["months"], data["regions"]
    fig = Figure(figsize=(7, 2.6), layout="constrained")
    ax = fig.subplots()
    x = list(range(len(months)))
    ax.plot(x, [r["planned"] for r in months], color=MUTED, linewidth=1.4, linestyle=(0, (4, 3)), label="Planned")
    ax.plot(x, [r["delivered"] for r in months], color=TEAL, linewidth=2.3, marker="o", markersize=5, label="Delivered")
    ax.set_xticks(x, [r["label"] for r in months])
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=True))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:g}k"))
    style_axes(ax)
    ax.legend(loc="upper left", frameon=False, ncols=2, fontsize=8,
              prop=FontProperties(fname=str(font_path), size=8), labelcolor=INK)
    save_chart(fig, "volume", out, font_path)

    fig = Figure(figsize=(7, 2.1), layout="constrained")
    ax = fig.subplots()
    values = [r["delivered"] for r in regions]
    y = list(range(len(regions)))
    ax.barh(y, values, color=[TEAL if v == max(values) else "#b8ced0" for v in values], height=.52)
    ax.set_yticks(y, [r["label"] for r in regions])
    ax.invert_yaxis()
    ax.set_xlim(0, max(max(values) * 1.18, 1))
    ax.xaxis.set_major_locator(MaxNLocator(nbins=5, integer=True))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value / 1000:g}k"))
    style_axes(ax, "x")
    for index, value in enumerate(values):
        ax.annotate(f"{value:,}", (value, index), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=INK)
    save_chart(fig, "regions", out, font_path)


def percent(numerator, denominator):
    return f"{100 * numerator / denominator:+.1f}%" if denominator else "n/a"


def document(data):
    months = data["months"]
    first, last = months[0], months[-1]
    total = sum(row["delivered"] for row in months)
    change = percent(last["delivered"] - first["delivered"], first["delivered"])
    variance = percent(last["delivered"] - last["planned"], last["planned"])
    header = f'<header class="masthead"><span>{escape(data["organization"])}</span><span class="edition">OPERATIONS / 026</span></header>'
    title = "<br>".join(escape(data["title"]).splitlines())
    rows = "".join(f'<tr><td>{escape(r["label"])}</td><td class="number">{r["planned"]:,}</td><td class="number">{r["delivered"]:,}</td><td class="number">{percent(r["delivered"]-r["planned"],r["planned"])}</td></tr>' for r in months)
    region_text = "; ".join(f'{escape(r["label"])}: {r["delivered"]:,}' for r in data["regions"])
    html = f'''<!doctype html><html lang="en"><body>
    <section class="sheet">{header}<p class="eyebrow">{escape(data['period'])} / PERFORMANCE BRIEF</p>
    <h1>{title}</h1><p class="intro">A compact view of volume, planning and regional distribution.<br>Fictional data, presented for a repeatable reporting workflow.</p>
    <div class="metrics"><div class="metric"><p class="metric-label">DELIVERIES / PERIOD</p><p class="metric-value">{total:,}</p><p class="metric-detail">Across {len(months)} reporting months</p></div>
    <div class="metric"><p class="metric-label">FIRST TO FINAL MONTH</p><p class="metric-value">{change}</p><p class="metric-detail">{escape(first['label'])} to {escape(last['label'])} delivery count</p></div>
    <div class="metric"><p class="metric-label">FINAL MONTH VS PLAN</p><p class="metric-value">{variance}</p><p class="metric-detail">{last['delivered']:,} delivered / {last['planned']:,} planned</p></div></div>
    <figure><div class="figure-header"><h2>01 / Volume over time</h2><span>DELIVERIES / THOUSANDS</span></div>
    <img class="chart volume" src="volume.svg" alt="Monthly planned and delivered counts; exact values appear in the table on page 2.">
    <figcaption>The solid line shows completed deliveries; the dashed line shows the plan. Both series use a zero-based vertical axis.</figcaption></figure>
    <div class="callout"><p><strong>{escape(last['label'])}: {last['delivered']:,} deliveries.</strong> The final month differs from plan by {last['delivered']-last['planned']:+,} deliveries. Read the exact monthly values and regional breakdown on the next page.</p></div>
    </section>
    <section>{header}<p class="eyebrow">THE DETAIL / DATA &amp; METHOD</p><h1 class="section-title">The numbers behind the view.</h1>
    <figure><div class="figure-header"><h2>02 / Regional distribution</h2><span>{escape(last['label']).upper()} / COMPLETED DELIVERIES</span></div>
    <img class="chart regions" src="regions.svg" alt="Regional delivery counts, repeated as selectable text below.">
    <figcaption>{region_text}. Total: {last['delivered']:,}.</figcaption></figure>
    <h2 class="subhead">Monthly ledger</h2><table><thead><tr><th>MONTH</th><th class="number">PLANNED</th><th class="number">DELIVERED</th><th class="number">VS PLAN</th></tr></thead><tbody>{rows}</tbody></table>
    <p class="method"><strong>Source &amp; method.</strong> All organizations and counts are fictional. Variance is (delivered - planned) / planned; a zero plan is shown as n/a. The regional total equals the final month's delivery count. Chart lettering is vector artwork; values and explanations are also provided as selectable document text.</p>
    </section></body></html>'''
    return html, total


def render(data_path, out):
    data = load_data(data_path)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
    charts(data, out, font)
    bundle = fullbleed.AssetBundle()
    for name in ("volume", "regions"):
        bundle.add_file(str(out / (name + ".svg")), "svg", name=name + ".svg")
    engine = fullbleed.PdfEngine(font_files=[str(font)], svg_form_xobjects=True, svg_raster_fallback=False,
        document_title=data["organization"] + " / " + data["period"], document_lang="en",
        footer_each="FIELDNOTE / FICTIONAL EXAMPLE                                      {page} / {pages}",
        footer_font_name="Inter", footer_font_size=7, footer_y_from_bottom=24, footer_x=51,
        footer_color="#61727c")
    engine.register_bundle(bundle)
    html, total = document(data)
    css = (ROOT / "report.css").read_text(encoding="utf-8")
    pdf, missing = engine.render_pdf_with_glyph_report(html, css)
    (out / "glyph-report.json").write_text(json.dumps(missing, indent=2) + "\n", encoding="utf-8")
    if missing:
        raise ValueError("The document font lacks required characters; see glyph-report.json")
    (out / "report.html").write_text(html, encoding="utf-8")
    (out / "report.pdf").write_bytes(pdf)
    engine.render_finalized_pdf_image_pages_to_dir(str(out / "report.pdf"), str(out / "preview"), 110, "report")
    result = {"fullbleed": version("fullbleed"), "matplotlib": version("matplotlib"),
              "total_deliveries": total, "pdf_bytes": len(pdf), "pdf_sha256": sha256(pdf).hexdigest(),
              "font_sha256": sha256(Path(str(font)).read_bytes()).hexdigest(),
              "svg_sha256": {name:sha256((out / (name + ".svg")).read_bytes()).hexdigest() for name in ("volume", "regions")}}
    (out / "render.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data.json")
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    print(json.dumps(render(args.data, args.out)))
