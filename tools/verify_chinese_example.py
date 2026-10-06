"""Exercise the actual downloadable ZIP, prepared font, diagnostics and PDF output."""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import zipfile

import fullbleed
import pypdfium2 as pdfium
from fontTools.ttLib import TTFont
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs' / 'assets' / 'chinese-invoice'


def compact(text):
    return ''.join(text.split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'output' / 'chinese-verification')
    parser.add_argument('--update-assets', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    project = out / 'project with spaces'
    project.mkdir(exist_ok=False)
    checks = []
    commands = []

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    def run(label, arguments, cwd, expected=0):
        result = subprocess.run([sys.executable, *map(str, arguments)], cwd=cwd,
                                env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONPATH': ''},
                                capture_output=True, text=True, encoding='utf-8', timeout=240)
        (out / f'{label}.stdout.txt').write_text(result.stdout, encoding='utf-8')
        (out / f'{label}.stderr.txt').write_text(result.stderr, encoding='utf-8')
        if result.returncode != expected:
            raise AssertionError(f'{label}: expected exit {expected}, got {result.returncode}; see {out}')
        commands.append({'label': label, 'exit': result.returncode})
        return result

    check('installed public engine version', version('fullbleed') == '2.5.8')
    check('pinned font preparation version', version('fonttools') == '4.65.0')
    manifest = json.loads((ASSETS / 'source.json').read_text(encoding='utf-8'))
    zip_path = ASSETS / 'project.zip'
    check('ZIP hash matches manifest', sha256(zip_path.read_bytes()).hexdigest() == manifest['zip_sha256'])
    with zipfile.ZipFile(zip_path) as archive:
        expected_names = {'chinese-invoice/' + entry['path'] for entry in manifest['files']}
        check('ZIP has the exact expected file set', set(archive.namelist()) == expected_names)
        for entry in manifest['files']:
            data = archive.read('chinese-invoice/' + entry['path'])
            check('ZIP source matches repository: ' + entry['path'], data == (ROOT / 'examples/chinese-invoice' / entry['path']).read_bytes())
            check('ZIP source matches hash: ' + entry['path'], sha256(data).hexdigest() == entry['sha256'])
        archive.extractall(project)
    project /= 'chinese-invoice'
    run('prepare-font', ['-I', 'prepare_font.py'], project)
    font_path = project / 'fonts/NotoSansSC-Regular.ttf'
    font = TTFont(font_path)
    check('prepared font is a static regular face', 'fvar' not in font and font['OS/2'].usWeightClass == 400 and font['name'].getDebugName(6) == 'NotoSansSC-Regular')
    font.close()
    cached = run('prepare-cached', ['-I', 'prepare_font.py'], project)
    check('verified asset is reused without conversion', 'already prepared and verified' in cached.stdout)
    guide = (ROOT / 'docs/guides/chinese-pdf.md').read_text(encoding='utf-8')
    snippets = re.findall(r'```python\n(.*?)```', guide, flags=re.S)
    check('guide has one executable Python snippet', len(snippets) == 1)
    (project / 'guide-snippet.py').write_text(snippets[0], encoding='utf-8')
    run('guide-snippet', ['-I', 'guide-snippet.py'], project)
    guide_pdf = PdfReader(project / 'chinese.pdf')
    guide_text = compact(''.join(page.extract_text() for page in guide_pdf.pages))
    check('guide snippet renders Chinese and English', len(guide_pdf.pages) == 1 and '中文示例' in guide_text and '项目、数量、价格' in guide_text and 'Items,quantity,price' in guide_text)
    run('render', ['-I', 'render.py', '--out', out / 'render'], project)
    run('replay', ['-I', 'render.py', '--out', out / 'replay'], project)
    pdf_path = out / 'render/invoice.pdf'
    pdf = pdf_path.read_bytes()
    check('fixed-input PDF replay is byte-identical', pdf == (out / 'replay/invoice.pdf').read_bytes())
    check('registered sample has no missing glyphs', json.loads((out / 'render/glyph-report.json').read_text(encoding='utf-8')) == [])
    reader = PdfReader(pdf_path)
    check('one A4 page', len(reader.pages) == 1 and abs(float(reader.pages[0].mediabox.width) - 595.276) < 0.2 and abs(float(reader.pages[0].mediabox.height) - 841.89) < 0.2)
    text = '\n'.join(page.extract_text() for page in reader.pages)
    (out / 'extracted.txt').write_text(text, encoding='utf-8')
    required = ['服务账单', 'Service invoice', '山海设计工作室', 'Shanhai Design Studio', '秋季品牌更新',
                '品牌策略', '视觉设计', '版式制作', '¥2,400.00', '¥3,600.00', '¥1,350.00', '¥7,350.00',
                '2026-10-01', '2026-10-15', '中英文排版示例', 'Fictional sample. Not for payment.']
    required.append(json.loads((project / 'data.json').read_text(encoding='utf-8'))['note'])
    for phrase in required:
        check('independent text extraction: ' + phrase, compact(phrase) in compact(text))
    check('no Unicode replacement character', '\ufffd' not in text)
    descriptors = []
    for ref in reader.pages[0]['/Resources']['/Font'].values():
        item = ref.get_object()
        if '/DescendantFonts' in item:
            descriptor = item['/DescendantFonts'][0].get_object()['/FontDescriptor'].get_object()
            descriptors.append(descriptor)
            check('used Chinese font has a Unicode map', '/ToUnicode' in item)
    check('explicit regular TrueType face embedded', len(descriptors) == 1 and 'NotoSansSC-Regular' in str(descriptors[0]['/FontName']) and '/FontFile2' in descriptors[0])
    document = pdfium.PdfDocument(pdf)
    page = document[0]
    text_page = page.get_textpage()
    boxes = [text_page.get_charbox(index) for index in range(text_page.count_chars())]
    nonempty = [(l, b, r, t) for l, b, r, t in boxes if r > l and t > b]
    check('independent glyph boxes stay inside the page', bool(nonempty) and all(l >= 0 and b >= 0 and r <= page.get_width() + .1 and t <= page.get_height() + .1 for l, b, r, t in nonempty))
    bounds = [min(box[0] for box in nonempty), min(box[1] for box in nonempty), max(box[2] for box in nonempty), max(box[3] for box in nonempty)]
    page.render(scale=110/72).to_pil().save(out / 'pdfium.png')
    text_page.close()
    page.close()
    document.close()
    check('one finalized native preview', len(list((out / 'render/preview').glob('*.png'))) == 1)

    data = json.loads((project / 'data.json').read_text(encoding='utf-8'))
    data['customer'] = '山海 <设计> & Studio'
    modified = out / 'edited.json'
    modified.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    run('edited', ['-I', 'render.py', '--data', modified, '--out', out / 'edited'], project)
    edited_text = '\n'.join(page.extract_text() for page in PdfReader(out / 'edited/invoice.pdf').pages)
    check('edited customer stays literal text', compact(data['customer']) in compact(edited_text))

    data['customer'] = 'Missing ' + chr(0x10ffff)
    modified.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    run('missing-glyph', ['-I', 'render.py', '--data', modified, '--out', out / 'missing'], project, expected=1)
    missing = json.loads((out / 'missing/glyph-report.json').read_text(encoding='utf-8'))
    check('unsupported character reports its codepoint', any(entry['codepoint'] == 0x10ffff for entry in missing))
    check('missing-glyph gate writes no new PDF', not (out / 'missing/invoice.pdf').exists())

    _, no_font_report = fullbleed.PdfEngine().render_pdf_with_glyph_report('<p>中文</p>', 'body { font-family: Helvetica; }')
    (out / 'unregistered-font-report.json').write_text(json.dumps(no_font_report), encoding='utf-8')
    check('documented no-registered-font limitation retained', no_font_report == [])
    hidden = font_path.with_suffix('.held')
    font_path.rename(hidden)
    try:
        absent = run('absent-font', ['-I', 'render.py', '--out', out / 'absent'], project, expected=1)
        check('missing font file has actionable error', 'prepare_font.py' in absent.stderr and not (out / 'absent/invoice.pdf').exists())
    finally:
        hidden.rename(font_path)

    public_pdf = ASSETS / 'invoice.pdf'
    if not args.update_assets:
        check('downloadable PDF matches the actual extracted project', public_pdf.read_bytes() == pdf)
    result = {'ok': True, 'fullbleed': version('fullbleed'), 'python': platform.python_version(),
              'platform': sys.platform, 'fonttools': version('fonttools'), 'pypdf': version('pypdf'),
              'pdfium': version('pypdfium2'), 'checks': checks, 'commands': commands,
              'pages': len(reader.pages), 'pdf_bytes': len(pdf), 'pdf_sha256': sha256(pdf).hexdigest(),
              'font_sha256': sha256(font_path.read_bytes()).hexdigest(), 'glyph_bounds_pt': bounds,
              'zip_sha256': manifest['zip_sha256'], 'missing_glyph_case': missing,
              'scope': 'This fixed Simplified Chinese/English fixture, local font preparation, diagnostics, text, page bounds, replay and assets. No general language, shaping or standards certification.'}
    (out / 'verification.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')
    if args.update_assets:
        shutil.copy2(pdf_path, public_pdf)
        shutil.copy2(out / 'render/preview/invoice_page1.png', ASSETS / 'invoice.png')
        shutil.copy2(out / 'verification.json', ASSETS / 'verification.json')
    print(json.dumps({'ok': True, 'checks': len(checks), 'pdf_bytes': len(pdf), 'pdf_sha256': result['pdf_sha256']}))


if __name__ == '__main__':
    main()
