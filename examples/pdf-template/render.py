"""Personalize a one-page PDF template, once per JSON record."""
import argparse
from datetime import date
from hashlib import sha256
from html import escape
from importlib.metadata import version
from importlib.resources import files
import json
from pathlib import Path
import re
import unicodedata

import fullbleed

ROOT = Path(__file__).resolve().parent
MONTHS = ("", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
FIELDS = {"name", "workshop", "completed_on", "certificate_id"}


def load_records(path):
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list) or not records:
        raise ValueError("data.json must contain a nonempty list of certificate records.")
    normalized = []
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise ValueError(f"Record {index}: use exactly {', '.join(sorted(FIELDS))}.")
        item = {}
        for key, limit in [("name", 48), ("workshop", 80), ("certificate_id", 20)]:
            value = record[key]
            if not isinstance(value, str):
                raise ValueError(f"Record {index}: {key} must be text.")
            value = unicodedata.normalize("NFC", value.strip())
            if not 1 <= len(value) <= limit or not value.isprintable():
                raise ValueError(f"Record {index}: {key} must contain 1–{limit} printable characters on one line.")
            item[key] = value
        if not re.fullmatch(r"[A-Za-z0-9._-]+", item["certificate_id"]):
            raise ValueError(f"Record {index}: certificate_id accepts letters, digits, periods, underscores and hyphens.")
        if not isinstance(record["completed_on"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["completed_on"]):
            raise ValueError(f"Record {index}: completed_on must use YYYY-MM-DD.")
        completed = date.fromisoformat(record["completed_on"])
        item["completed_on"] = completed.isoformat()
        item["date_label"] = f"{completed.day} {MONTHS[completed.month]} {completed.year}"
        normalized.append(item)
    return normalized


def overlay_html(records):
    pages = []
    for record in records:
        name_class = "long" if len(record["name"]) > 28 else "medium" if len(record["name"]) > 19 else ""
        workshop_class = "long" if len(record["workshop"]) > 40 else ""
        id_class = "long" if len(record["certificate_id"]) > 16 else ""
        pages.append(
            '<section class="certificate">'
            f'<p class="name {name_class}">{escape(record["name"])}</p>'
            f'<p class="workshop {workshop_class}">{escape(record["workshop"])}</p>'
            f'<p class="date">{escape(record["date_label"])}</p>'
            f'<p class="id {id_class}">{escape(record["certificate_id"])}</p>'
            '</section>'
        )
    return '<!doctype html><html lang="en"><body>' + ''.join(pages) + '</body></html>'


def render(data_path, out, template_path=ROOT / "template.pdf"):
    records = load_records(data_path)
    template_path = Path(template_path)
    inspection = fullbleed.inspect_pdf(str(template_path))
    if not inspection.get("ok") or inspection.get("encrypted") or inspection.get("page_count") != 1:
        raise ValueError("Use a readable, unencrypted, one-page PDF template.")
    template_bytes = template_path.read_bytes()
    font = files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf")
    engine = fullbleed.PdfEngine(font_files=[str(font)], document_title="Common Ground certificates", document_lang="en-US")
    html = overlay_html(records)
    css = (ROOT / "overlay.css").read_text(encoding="utf-8")
    overlay, missing = engine.render_pdf_with_glyph_report(html, css)
    if missing:
        raise ValueError("Inter is missing required glyphs. Register a suitable font and update overlay.css before rendering.")
    overlay = bytes(overlay)
    if overlay != bytes(engine.render_pdf(html, css)):
        raise RuntimeError("The repeated overlay render changed.")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    overlay_path = out / "overlay.pdf"
    overlay_path.write_bytes(overlay)
    overlay_inspection = fullbleed.inspect_pdf(str(overlay_path))
    if overlay_inspection.get("page_count") != len(records):
        raise ValueError("The overlay must produce exactly one page per record. Review overlay.css.")
    (out / "overlay.html").write_text(html, encoding="utf-8")
    # Each tuple is (template ID, template page, overlay page, X offset, Y offset).
    # Page indexes are zero-based. Zero offsets align the two full-size pages.
    templates = [("certificate", str(template_path))]
    plan = [("certificate", 0, page, 0.0, 0.0) for page in range(len(records))]
    (out / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    destination = out / "certificates.pdf"
    result = fullbleed.finalize_compose_pdf(templates, plan, str(overlay_path), str(destination), annotation_mode="none")
    if result.get("pages_written") != len(records):
        raise RuntimeError("The composed page count does not match the records.")
    repeat_path = out / "certificates-repeat.pdf"
    fullbleed.finalize_compose_pdf(templates, plan, str(overlay_path), str(repeat_path), annotation_mode="none")
    final_bytes = destination.read_bytes()
    if final_bytes != repeat_path.read_bytes() or template_bytes != template_path.read_bytes():
        raise RuntimeError("Composition changed its repeated output or source template.")
    previews = engine.render_finalized_pdf_image_pages(str(destination), 110)
    if len(previews) != len(records):
        raise RuntimeError("The final PDF preview count does not match the records.")
    for index, png in enumerate(previews, 1):
        (out / f"page-{index}.png").write_bytes(bytes(png))
    record = dict(version=version("fullbleed"), records=len(records), pages=len(previews),
        template_sha256=sha256(template_bytes).hexdigest(), template_unchanged=True,
        overlay_sha256=sha256(overlay).hexdigest(), pdf_sha256=sha256(final_bytes).hexdigest(),
        css_sha256=sha256(css.encode()).hexdigest(), font_sha256=sha256(font.read_bytes()).hexdigest(),
        missing_glyphs=missing, deterministic_repeat=True, annotation_mode="none",
        scope="One static template page plus one transparent text overlay per record. These are ordinary, noninteractive PDFs; no AcroForm, signature, tagging, or PDF conformance claim.")
    (out / "render.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data.json")
    parser.add_argument("--template", type=Path, default=ROOT / "template.pdf")
    parser.add_argument("--out", type=Path, default=ROOT / "output", help="New output directory")
    args = parser.parse_args()
    try:
        result = render(args.data, args.out, args.template)
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
