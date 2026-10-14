"""Bounded sales data and a print report, independent of Streamlit state."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
from html import escape
from importlib.resources import files
from io import StringIO
from pathlib import Path
from string import Template
import argparse
import csv
import json
import re

import fullbleed

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 65536
MAX_ROWS = 250
COLUMNS = ["date", "region", "channel", "orders", "revenue_usd"]


@dataclass(frozen=True)
class Sale:
    row: int
    day: date
    region: str
    channel: str
    orders: int
    cents: int


def label(value, name, limit=24):
    value = value.strip()
    if not value or len(value) > limit or any(ord(c) < 32 or 127 <= ord(c) < 160 for c in value):
        raise ValueError(f"{name} must contain 1–{limit} characters without control characters.")
    return value


def load_sales(data: bytes) -> list[Sale]:
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Choose a nonempty CSV no larger than 64 KiB.")
    try:
        reader = csv.DictReader(StringIO(data.decode("utf-8-sig"), newline=""), strict=True)
        if reader.fieldnames != COLUMNS:
            raise ValueError("CSV columns must be: " + ",".join(COLUMNS))
        rows = []
        for number, item in enumerate(reader, 1):
            if number > MAX_ROWS:
                raise ValueError("The example accepts at most 250 records.")
            if None in item or any(value is None for value in item.values()):
                raise ValueError(f"CSV record {number} has an incorrect number of fields.")
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["date"]):
                raise ValueError(f"CSV record {number} needs a YYYY-MM-DD date.")
            day = date.fromisoformat(item["date"])
            if not re.fullmatch(r"[0-9]{1,6}", item["orders"]) or int(item["orders"]) > 100000:
                raise ValueError(f"CSV record {number} needs an order count from 0 to 100000.")
            if not re.fullmatch(r"[0-9]{1,7}(?:\.[0-9]{1,2})?", item["revenue_usd"]):
                raise ValueError(f"CSV record {number} needs nonnegative USD revenue with at most two decimals.")
            amount = Decimal(item["revenue_usd"])
            if amount > 1000000:
                raise ValueError(f"CSV record {number} exceeds the USD 1,000,000 revenue limit.")
            rows.append(Sale(number, day, label(item["region"], "Region"),
                             label(item["channel"], "Channel"), int(item["orders"]), int(amount * 100)))
    except (UnicodeError, csv.Error) as exc:
        raise ValueError("Choose a valid UTF-8 CSV with the sample's five columns.") from exc
    if not rows:
        raise ValueError("The CSV needs at least one data record.")
    if any(len({getattr(row, field) for row in rows}) > 6 for field in ("region", "channel")):
        raise ValueError("The example accepts at most six regions and six channels.")
    return rows


def select_sales(rows, start, end, regions, channel):
    if start > end:
        raise ValueError("The start date must not follow the end date.")
    return sorted((row for row in rows if start <= row.day <= end and row.region in regions
                   and (channel is None or row.channel == channel)),
                  key=lambda row: (row.day, row.region, row.channel, row.row))


def money(cents):
    return f"USD {cents // 100:,}.{cents % 100:02d}"


def compact(number):
    for size, suffix in ((1000000, "m"), (1000, "k")):
        if number >= size:
            return f"{Decimal(number) / size:.1f}{suffix}"
    return f"{number:,}"


def totals(rows):
    return sum(row.orders for row in rows), sum(row.cents for row in rows)


def bars(rows, field):
    amounts = defaultdict(int)
    for row in rows:
        amounts[getattr(row, field)] += row.cents
    maximum = max(amounts.values(), default=0)
    parts = []
    for name, amount in sorted(amounts.items(), key=lambda pair: (-pair[1], pair[0])):
        width = 0 if not maximum else amount * 100 / maximum
        parts.append(f'<div class="bar-row"><table class="bar-label"><tr><td>{escape(name)}</td>'
                     f'<td class="number">{money(amount)}</td></tr></table>'
                     f'<div class="bar-track"><div class="bar-fill" style="width:{width:.6f}%"></div></div></div>')
    return "".join(parts)


def document(rows, name, start, end, regions, channel):
    if not rows:
        raise ValueError("No records match these filters. Change the selection before preparing a PDF.")
    name = label(name, "Report name", 48)
    orders, revenue = totals(rows)
    table = "".join(f'<tr><td>R{r.row:03}</td><td>{r.day.isoformat()}</td><td>{escape(r.region)}</td>'
                    f'<td>{escape(r.channel)}</td><td class="number">{r.orders:,}</td>'
                    f'<td class="number">{money(r.cents).removeprefix("USD ")}</td></tr>' for r in rows)
    values = dict(name=escape(name), start=start.isoformat(), end=end.isoformat(),
                  regions=escape(", ".join(sorted(regions))), channel=escape(channel or "All channels"),
                  count=str(len(rows)), orders=f"{orders:,}", order_short=compact(orders),
                  revenue=money(revenue), revenue_short=compact(revenue // 100),
                  region_bars=bars(rows, "region"), channel_bars=bars(rows, "channel"), rows=table)
    html = Template((ROOT / "report.html").read_text(encoding="utf-8")).substitute(values)
    css = (ROOT / "report.css").read_text(encoding="utf-8")
    return html, css


def fingerprint(html, css):
    return sha256((html + "\0" + css).encode("utf-8")).hexdigest()


def render_report(html, css):
    font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
    engine = fullbleed.PdfEngine(font_files=[str(font), str(ROOT / "fonts/DMSerifDisplay-Regular.ttf")],
        document_title="Sales brief", document_lang="en",
        footer_each="SALES BRIEF / {page} OF {pages}",
        footer_font_name="Inter", footer_font_size=7, footer_x=42, footer_y_from_bottom=22,
        footer_color="#596f67")
    pdf, missing = engine.render_pdf_with_glyph_report(html, css)
    if missing:
        raise ValueError("A character is missing from the report fonts. Add a suitable font before exporting this data.")
    if len(pdf) > 8 * 1024 * 1024:
        raise ValueError("This example limits a prepared PDF to 8 MiB. Reduce embedded assets or the data.")
    return {"pdf": pdf, "signature": fingerprint(html, css)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=ROOT / "sales.csv")
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    rows = load_sales(args.csv.read_bytes())
    start, end = min(r.day for r in rows), max(r.day for r in rows)
    regions = sorted({r.region for r in rows})
    html, css = document(select_sales(rows, start, end, regions, None), "Northstar Supply / Quarterly review",
                         start, end, regions, None)
    report = render_report(html, css)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.pdf").write_bytes(report["pdf"])
    (args.out / "report.html").write_text(html, encoding="utf-8")
    print(json.dumps({"pdf_sha256": sha256(report["pdf"]).hexdigest(),
                      "records": len(rows), "orders": totals(rows)[0], "revenue_cents": totals(rows)[1]}))


if __name__ == "__main__":
    main()
