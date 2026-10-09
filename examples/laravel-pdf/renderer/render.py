"""Trusted Blade HTML on stdin; PDF bytes on stdout. No request-selected files."""
from importlib import resources
import json
from pathlib import Path
import sys

import fullbleed

ROOT = Path(__file__).resolve().parent
CSS = (ROOT / 'invoice.css').read_text(encoding='utf-8')
FONTS = [str(resources.files('fullbleed_assets').joinpath('fonts/Inter-Variable.ttf')),
         str(ROOT / 'fonts/BebasNeue-Regular.ttf')]


def engine(title):
    return fullbleed.PdfEngine(font_files=FONTS, document_title=title, document_lang='en-US')


def main():
    raw = sys.stdin.buffer.read(262145)
    if len(raw) > 262144:
        raise ValueError('Input limit')
    data = json.loads(raw)
    pdf, _, missing = engine(data['title']).render_pdf_with_page_data_and_glyph_report(data['html'], CSS)
    if missing or len(pdf) > 4000000:
        raise ValueError('Output or font coverage limit')
    sys.stdout.buffer.write(pdf)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never include the request, HTML or engine diagnostics in subprocess logs.
        sys.stderr.write('Fullbleed render failed. Check trusted assets and font coverage.\n')
        sys.exit(1)
