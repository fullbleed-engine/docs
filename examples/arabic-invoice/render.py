"""Render a fictional bilingual invoice from local, explicitly registered fonts."""
from hashlib import sha256
from html import escape
from importlib.metadata import version
from importlib.resources import files
from pathlib import Path
import argparse
import json

import fullbleed

ROOT = Path(__file__).resolve().parent


def money(cents):
    return f"{cents // 100:,}.{cents % 100:02}"


def render(data_path, out):
    data = json.loads(Path(data_path).read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "font-source.json").read_text(encoding="utf-8"))
    for asset in manifest["files"]:
        path = ROOT / asset["file"]
        if not path.is_file() or sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise ValueError("Missing or changed project font asset: " + asset["file"])
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    e = lambda key: escape(str(data[key]))
    rows = []
    total = 0
    for item in data["items"]:
        quantity, unit = item["quantity"], item["unit_cents"]
        if type(quantity) is not int or quantity <= 0 or type(unit) is not int or unit < 0:
            raise ValueError("Use positive integer quantities and nonnegative integer USD cents")
        amount = quantity * unit
        total += amount
        rows.append(f'''<tr><td class="money">{money(amount)}</td><td class="money">{money(unit)}</td>
        <td class="money qty">{quantity}</td><td class="rtl"><p class="service">{escape(item['ar'])}</p>
        <p class="latin service-en">{escape(item['en'])}</p></td></tr>''')
    html = f'''<!doctype html><html lang="ar"><body>
    <header class="masthead"><p class="latin edition">DESIGN / DOCUMENTS<br>EST. 2026</p>
    <div class="rtl"><p class="brand-ar">{e('studio_ar')}</p><p class="latin brand-en">{e('studio_en')}</p></div></header>
    <section class="hero"><div><p class="latin ref-label">REFERENCE</p><p class="latin reference">{e('reference')}</p></div>
    <div class="rtl"><h1>فاتورة</h1><p class="latin subtitle">INVOICE</p></div></section>
    <section class="parties"><div class="project rtl"><p class="eyebrow">المشروع <bdi dir="ltr" class="latin">/ PROJECT</bdi></p>
    <p class="project-name">{e('project_ar')}</p><p class="latin secondary">{e('project_en')}</p></div>
    <div class="customer rtl"><p class="eyebrow">فاتورة إلى <bdi dir="ltr" class="latin">/ BILL TO</bdi></p><h2>{e('customer_ar')}</h2><p class="latin secondary">{e('customer_en')}</p></div></section>
    <section class="dates"><p class="rtl">تاريخ الاستحقاق <bdi dir="ltr">{e('due')}</bdi></p>
    <p class="rtl">تاريخ الإصدار <bdi dir="ltr">{e('issued')}</bdi></p></section>
    <table><colgroup><col style="width:22%"><col style="width:20%"><col style="width:12%"><col style="width:46%"></colgroup>
    <thead><tr><th class="rtl"><p>المبلغ</p><span class="latin">AMOUNT / USD</span></th><th class="rtl"><p>السعر</p><span class="latin">RATE / USD</span></th>
    <th class="rtl qty"><p>العدد</p><span class="latin">QTY</span></th><th class="rtl"><p>الخدمة</p><span class="latin">SERVICE</span></th></tr></thead>
    <tbody>{''.join(rows)}</tbody></table>
    <section class="summary"><div class="total"><div class="total-label"><span class="latin">TOTAL DUE</span><span class="rtl">الإجمالي</span></div>
    <p class="latin total-value"><span class="currency">USD</span>{money(total)}</p></div>
    <div class="note rtl"><p class="thanks">شكراً لثقتكم</p><p>يُرجى استخدام رقم الفاتورة <bdi dir="ltr" class="latin">{e('reference')}</bdi> عند التواصل معنا.</p>
    <p class="latin secondary">Please include the invoice reference in your correspondence.</p></div></section>
    <footer class="footer"><p class="latin">FICTIONAL EXAMPLE · FULLBLEED</p><p class="rtl">نموذج توضيحي — جميع الأسماء والمبالغ خيالية</p></footer>
    </body></html>'''
    font_paths = [ROOT / "fonts/NotoSansArabic-Regular.ttf", ROOT / "fonts/NotoSansArabic-Bold.ttf"]
    engine = fullbleed.PdfEngine(font_files=[str(p) for p in font_paths] + [str(files("fullbleed_assets").joinpath("fonts/Inter-Variable.ttf"))],
                                document_title=data["reference"] + " / Bilingual invoice", document_lang="ar")
    css = (ROOT / "invoice.css").read_text(encoding="utf-8")
    pdf, missing = engine.render_pdf_with_glyph_report(html, css)
    (out / "glyph-report.json").write_text(json.dumps(missing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if missing:
        raise RuntimeError("A project font lacks required characters; see glyph-report.json")
    (out / "invoice.html").write_text(html, encoding="utf-8")
    (out / "invoice.pdf").write_bytes(pdf)
    engine.render_finalized_pdf_image_pages_to_dir(str(out / "invoice.pdf"), str(out / "preview"), 110, "invoice")
    result = {"engine": version("fullbleed"), "reference": data["reference"], "total_cents": total,
              "bytes": len(pdf), "pdf_sha256": sha256(pdf).hexdigest(), "missing_glyphs": missing}
    (out / "render.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data.json")
    parser.add_argument("--out", type=Path, default=ROOT / "output")
    args = parser.parse_args()
    print(json.dumps(render(args.data, args.out)))
