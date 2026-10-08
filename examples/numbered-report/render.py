"""Render the editable report and retain previews of its final PDF."""
from pathlib import Path
import argparse
import hashlib
from importlib.metadata import version
import json

import fullbleed
import fullbleed_assets


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=root/'output', help='New output directory')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    font = Path(fullbleed_assets.asset_path('fonts/Inter-Variable.ttf'))
    if not font.is_file():
        raise FileNotFoundError(font)
    html = (root/'report.html').read_text(encoding='utf-8')
    css = (root/'report.css').read_text(encoding='utf-8')
    engine = fullbleed.PdfEngine(font_files=[str(font)],
        document_title='From brief to handoff', document_lang='en-US')
    pdf, missing = engine.render_pdf_with_glyph_report(html, css)
    (args.out/'glyph-report.json').write_text(json.dumps(missing, indent=2)+'\n', encoding='utf-8')
    if missing:
        raise ValueError('Missing glyphs; no PDF written. See glyph-report.json.')
    pdf = bytes(pdf)
    if pdf != bytes(engine.render_pdf(html, css)):
        raise ValueError('The repeated render changed.')
    path = args.out/'numbered-report.pdf'
    path.write_bytes(pdf)
    previews = engine.render_finalized_pdf_image_pages(str(path), 110)
    for i, png in enumerate(previews, 1):
        (args.out/f'page-{i}.png').write_bytes(bytes(png))
    record = dict(version=version('fullbleed'), pages=len(previews), pdf_sha256=digest(pdf),
        html_sha256=digest((root/'report.html').read_bytes()),
        css_sha256=digest((root/'report.css').read_bytes()), font_sha256=digest(font.read_bytes()),
        missing_glyphs=missing, deterministic_replay=True, fictional_content=True)
    (args.out/'render.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
