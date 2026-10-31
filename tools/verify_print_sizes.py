"""Run the real guide/download and independently inspect custom paper output."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata, resources
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import zipfile

import fullbleed
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/print-sizes'
SOURCE = ROOT / 'examples/print-sizes'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=ROOT / 'target/print-sizes')
parser.add_argument('--update-reference', action='store_true', help='Replace retained measurements/previews after source edits; visual review is still required.')
args = parser.parse_args()
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
assert metadata.version('fullbleed') == '2.5.46'
assert not Path(fullbleed.__file__).resolve().is_relative_to(ROOT)
assert fullbleed.build_features()['embedded_stylesheets']
manifest = json.loads((ASSETS / 'project.json').read_text(encoding='utf-8'))
assert manifest['version'] == '2.5.46'
for name, expected in manifest['assets'].items():
    data = (ASSETS / name).read_bytes()
    assert len(data) == expected['bytes'] and sha256(data).hexdigest() == expected['sha256'], name

destination = out / 'extracted project with spaces'
expected_names = {'LICENSE', 'README.md', 'requirements.txt', 'render.py', 'shelf-card.html'}
with zipfile.ZipFile(ASSETS / 'project.zip') as archive:
    names = archive.namelist()
    assert len(names) == len(set(names)) == len(expected_names)
    assert archive.testzip() is None
    for name in names:
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in name
        assert len(path.parts) == 2 and path.parts[0] == 'fullbleed-print-sizes'
        assert path.parts[1] in expected_names
        data = archive.read(name)
        assert data == (SOURCE / path.name).read_text(encoding='utf-8').encode('utf-8')
        assert sha256(data).hexdigest() == manifest['sources'][path.name]
    archive.extractall(destination)
project = destination / 'fullbleed-print-sizes'
assert (project / 'requirements.txt').read_text().strip() == 'fullbleed==2.5.46'
guide = ROOT / 'docs/guides/custom-paper-sizes.md'
blocks = re.findall(r'```python\n(.*?)\n```', guide.read_text(encoding='utf-8'), re.S)
assert len(blocks) == 1
assert blocks[0] + '\n' == (project / 'render.py').read_text(encoding='utf-8')


def run(label):
    completed = subprocess.run([sys.executable, '-I', str(project / 'render.py')], cwd=out,
        capture_output=True, text=True, encoding='utf-8', timeout=60)
    (out / (label + '.log')).write_text(completed.stdout + completed.stderr, encoding='utf-8')
    assert completed.returncode == 0, completed.stderr


run('downloaded-project')
compact = lambda text: ''.join(text.split())
expected_text = [
    'FIELDWORK', 'OBJECT NO. 04', 'Good days.', 'Good coffee.', 'THE DAILY CUP',
    'Hand-finished stoneware.', 'Warm chalk glaze. Made in small batches.',
    '$24', '250 ml', 'One good everyday object.',
    'Fieldwork Goods · Fictional product and price.', '20 mm · check at actual size',
]
font = resources.files('fullbleed_assets').joinpath('fonts/Inter-Variable.ttf')
engine = fullbleed.PdfEngine(font_files=[str(font)])
html = (project / 'shelf-card.html').read_text(encoding='utf-8')
cases = []
for name, dimensions, css in [
    ('metric-card', (100 * 72 / 25.4, 150 * 72 / 25.4), ''),
    ('inch-card', (288, 432), '@page { size: 4in 6in; margin: 8mm; }'),
]:
    path = project / 'output' / (name + '.pdf')
    data = path.read_bytes()
    assert data == (ASSETS / (name + '.pdf')).read_bytes(), name
    native = project / 'output' / name / (name + '_page1.png')
    assert native.read_bytes() == (ASSETS / (name + '.png')).read_bytes(), name
    assert len(list(native.parent.glob('*.png'))) == 1
    reader = PdfReader(path, strict=True)
    assert len(reader.pages) == 1, name
    page = reader.pages[0]
    size = (float(page.mediabox.width), float(page.mediabox.height))
    assert all(abs(actual - expected) < 0.01 for actual, expected in zip(size, dimensions)), (name, size)
    text = compact(page.extract_text() or '')
    assert all(compact(value) in text for value in expected_text), (name, text)
    assert 'Screenpreview' not in text
    fonts = [ref.get_object() for ref in page['/Resources']['/Font'].values()]
    assert fonts and all('Inter' in str(font['/BaseFont']) for font in fonts)
    assert all('/FontFile2' in font['/DescendantFonts'][0].get_object()['/FontDescriptor'].get_object() for font in fonts)
    report_pdf, glyphs = engine.render_pdf_with_glyph_report(html, css)
    assert report_pdf == data and glyphs == []
    inspection = fullbleed.inspect_pdf(str(path))
    assert inspection['page_count'] == 1 and inspection['warnings'] == []
    (out / (name + '-inspection.json')).write_text(json.dumps(inspection, indent=2) + '\n', encoding='utf-8')
    image_path = out / (name + '-pdfium.png')
    with pdfium.PdfDocument(path) as document:
        assert len(document) == 1
        independent_page = document[0]
        assert all(abs(a - b) < 0.01 for a, b in zip(independent_page.get_size(), dimensions))
        textpage = independent_page.get_textpage()
        assert compact(textpage.get_text_range()) == text
        for index in range(textpage.count_chars()):
            if not textpage.get_text_range(index, 1).strip():
                continue
            left, bottom, right, top = textpage.get_charbox(index)
            assert -0.02 <= left <= right <= dimensions[0] + 0.02
            assert -0.02 <= bottom <= top <= dimensions[1] + 0.02
        textpage.close()
        bitmap = independent_page.render(scale=2)
        image = bitmap.to_pil()
        try:
            image.save(image_path)
        finally:
            image.close(); bitmap.close(); independent_page.close()
    cases.append({'file':name + '.pdf', 'pages':1, 'points':list(size),
        'sha256':sha256(data).hexdigest(), 'missingGlyphs':glyphs,
        'nativePreviewSha256':sha256(native.read_bytes()).hexdigest(),
        'independentPreview':image_path.name, 'independentPreviewSha256':sha256(image_path.read_bytes()).hexdigest()})

run('repeat')
for case in cases:
    assert sha256((project / 'output' / case['file']).read_bytes()).hexdigest() == case['sha256']
result = {'ok':True, 'at':datetime.now(timezone.utc).isoformat(), 'version':'2.5.46',
    'guideSnippetMatchesDownload':True, 'downloadedProjectExecuted':True, 'sourceFiles':len(names),
    'projectZipSha256':sha256((ASSETS / 'project.zip').read_bytes()).hexdigest(),
    'guideSha256':sha256(guide.read_text(encoding='utf-8').encode()).hexdigest(),
    'embeddedFont':'Inter', 'screenTextExcluded':True, 'printScaleTextPresent':True,
    'allVisibleGlyphBoxesInsidePaper':True, 'repeatedPdfBytesEqual':True, 'cases':cases,
    'readers':{name:metadata.version(name) for name in ('pypdf','pypdfium2','Pillow')},
    'scope':'Exact guide/download execution, PDF page sizes, text/media filtering, embedded fonts, glyph coverage and repeated output. Visual review is separate. No printer, PDF/X or general CSS conformance claim.'}
if args.update_reference:
    for case in cases:
        shutil.copyfile(out / case['independentPreview'], ASSETS / case['independentPreview'])
    (ASSETS / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
else:
    reference = json.loads((ASSETS / 'verification.json').read_text(encoding='utf-8'))
    for key in ('ok', 'version', 'guideSnippetMatchesDownload', 'downloadedProjectExecuted', 'sourceFiles',
                'projectZipSha256', 'guideSha256', 'embeddedFont', 'screenTextExcluded', 'printScaleTextPresent',
                'allVisibleGlyphBoxesInsidePaper', 'repeatedPdfBytesEqual'):
        assert reference[key] == result[key], key
    assert len(reference['cases']) == len(cases)
    for actual, expected in zip(cases, reference['cases']):
        for key in ('file', 'pages', 'points', 'sha256', 'missingGlyphs', 'nativePreviewSha256'):
            assert actual[key] == expected[key], (actual['file'], key)
        assert sha256((ASSETS / expected['independentPreview']).read_bytes()).hexdigest() == expected['independentPreviewSha256']
(out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'ok':True, 'version':'2.5.46', 'cases':[{k:v for k,v in case.items() if k in ('file','pages','points','sha256')} for case in cases]}))
