"""Render a fictional bilingual invoice using one explicit static font file."""
from hashlib import sha256
from html import escape
from importlib.metadata import version
from pathlib import Path
import argparse
import json

import fullbleed

ROOT = Path(__file__).resolve().parent


def money(cents):
    return f'¥{cents // 100:,}.{cents % 100:02d}'


def document_html(data):
    text = lambda value: escape(str(value), quote=True)
    rows = []
    total = 0
    for item in data['items']:
        quantity, unit = item['quantity'], item['unit_cents']
        if type(quantity) is not int or type(unit) is not int or quantity < 1 or unit < 0:
            raise ValueError('Use positive integer quantities and nonnegative integer currency cents.')
        amount = quantity * unit
        total += amount
        rows.append(f'''<tr><td><p class="item-title">{text(item['name'])}</p>
          <p class="item-english" lang="en">{text(item['english'])}</p>
          <p class="item-detail">{text(item['detail'])}</p></td>
          <td class="num">{quantity}</td><td class="num">{money(unit)}</td>
          <td class="num">{money(amount)}</td></tr>''')
    return f'''<!doctype html><html lang="zh-CN"><body><main>
      <div class="masthead"><p class="brand">云杉 / YUNSHAN</p><p class="small">设计与文档 · DESIGN &amp; DOCUMENTS</p></div>
      <div class="hero"><p class="eyebrow">{text(data['reference'])} / CNY</p><h1>服务账单</h1><p lang="en">Service invoice</p></div>
      <div class="parties"><div><p class="label">客户 / BILL TO</p><p class="customer">{text(data['customer'])}</p>
      <p class="small" lang="en">{text(data['customer_english'])}</p></div>
      <div><table class="dates"><tr><td class="small">开具日期 / ISSUED</td><td>{text(data['issued'])}</td></tr>
      <tr><td class="small">到期日期 / DUE</td><td>{text(data['due'])}</td></tr></table></div></div>
      <p class="project">项目 / PROJECT　{text(data['project'])}</p>
      <table class="items"><colgroup><col style="width:48%"><col style="width:10%"><col style="width:21%"><col style="width:21%"></colgroup>
      <thead><tr><th>服务 / SERVICE</th><th class="num">数量 / QTY</th><th class="num">单价 / RATE</th><th class="num">金额 / AMOUNT</th></tr></thead>
      <tbody>{''.join(rows)}</tbody></table>
      <div class="bottom"><div><p class="label">备注 / NOTE</p><p class="note">{text(data['note'])}</p>
      <p class="small" lang="en">Fictional sample. Not for payment.</p></div><div class="total"><p class="eyebrow">合计 / TOTAL · CNY</p><p class="amount">{money(total)}</p></div></div>
      <div class="footer"><p>云杉 / YUNSHAN STUDIO</p><p>中英文排版示例 / BILINGUAL SAMPLE</p></div>
      </main></body></html>'''


def render(data_path, out):
    source = json.loads((ROOT / 'font-source.json').read_text(encoding='utf-8'))
    font = ROOT / 'fonts' / source['output']['file']
    if not font.is_file():
        raise SystemExit('Run python prepare_font.py once before rendering.')
    if sha256(font.read_bytes()).hexdigest() != source['output']['sha256']:
        raise SystemExit('Font hash changed. Run python prepare_font.py to restore the verified face.')
    data = json.loads(data_path.read_text(encoding='utf-8'))
    html = document_html(data)
    css = (ROOT / 'invoice.css').read_text(encoding='utf-8')
    engine = fullbleed.PdfEngine(font_files=[str(font)], document_title='云杉 / Service invoice', document_lang='zh-CN')
    pdf, missing = engine.render_pdf_with_glyph_report(html, css)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'glyph-report.json').write_text(json.dumps(missing, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if missing:
        raise SystemExit('Missing glyphs; no new PDF written. See glyph-report.json.')
    path = out / 'invoice.pdf'
    path.write_bytes(pdf)
    (out / 'invoice.html').write_text(html, encoding='utf-8')
    (out / 'invoice.css').write_text(css, encoding='utf-8')
    engine.render_finalized_pdf_image_pages_to_dir(str(path), str(out / 'preview'), 110, 'invoice')
    report = {
        'fullbleed': version('fullbleed'), 'font_sha256': source['output']['sha256'],
        'pdf_sha256': sha256(pdf).hexdigest(), 'pdf_bytes': len(pdf), 'missing_glyphs': missing,
        'scope': 'Fictional Simplified Chinese/English horizontal-text example; ordinary PDF.',
    }
    (out / 'render.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data.json')
    parser.add_argument('--out', type=Path, default=ROOT / 'output')
    args = parser.parse_args()
    render(args.data, args.out)
