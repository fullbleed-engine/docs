"""Independently inspect the real WASI, Python and Node exported-project PDFs."""
from hashlib import sha256
import json
from pathlib import Path

from playground_preformatted_inspection import verify

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'playground/project-verification'
FIXTURES = ROOT / 'tools/playground-fixtures'
INPUTS = FIXTURES / 'preformatted-whitespace-2.5.41.json'
inputs = json.loads(INPUTS.read_bytes())
reference = json.loads((FIXTURES / 'preformatted-2.5.41-reference.json').read_bytes())
assert sha256(INPUTS.read_bytes()).hexdigest() == reference['inputSha256']
font = FIXTURES / 'fonts/NotoSans-Regular.ttf'
assert sha256(font.read_bytes()).hexdigest() == inputs['fontSha256']
destination = OUT / 'preformatted-independent'
destination.mkdir(parents=True, exist_ok=True)
records = []
reports = {mode: json.loads((OUT / name).read_bytes()) for mode, name in [
    ('wasi', 'export-verification.json'), ('python', 'python-verification.json'), ('node', 'node-verification.json')]}
for mode, report in reports.items():
    cases = {row['name']: row for row in report['cases'] if row['name'].startswith('preformatted-')}
    assert len(cases) == 17
    for fixture in inputs['cases']:
        name = 'preformatted-' + fixture['name']
        case = cases[name]
        assert case['pages'] == reference['pages'][fixture['name']] and case['repeat_equal'] is True
        expected = OUT / (name + '-expected')
        assert (expected / 'input.html').read_bytes() == fixture['html'].encode()
        assert (expected / 'style.css').read_bytes() == fixture['css'].encode()
        if mode == 'wasi':
            pdf = expected / 'output.pdf'
            previews = [expected / f'page-{n}.png' for n in range(1, case['pages'] + 1)]
        else:
            project = OUT / ('extracted projects with spaces' if mode == 'python' else 'extracted node projects with spaces') / name
            pdf = project / 'output/document.pdf'
            rendered = json.loads((project / 'output/render.json').read_bytes())
            previews = [Path(path) for path in rendered['previews']]
            assert (project / 'assets/NotoSans-Regular.ttf').read_bytes() == font.read_bytes()
        assert sha256(pdf.read_bytes()).hexdigest() == case['pdf_sha256']
        assert pdf.read_bytes() == (expected / 'output.pdf').read_bytes()
        folder = destination / (mode + '-' + fixture['name'])
        folder.mkdir(exist_ok=True)
        (folder / 'document.pdf').write_bytes(pdf.read_bytes())
        preview_files, preview_hashes = [], []
        for n, path in enumerate(previews, 1):
            raw = path.read_bytes()
            assert raw == (expected / f'page-{n}.png').read_bytes()
            filename = f'native-{n}.png'
            (folder / filename).write_bytes(raw)
            preview_files.append(filename)
            preview_hashes.append(sha256(raw).hexdigest())
        records.append(dict(mode=mode, name=fixture['name'], directory=folder.name, pages=case['pages'],
            pdfSha256=case['pdf_sha256'], repeatPdfBytesMatch=case['repeat_equal'],
            previewFiles=preview_files, previewSha256=preview_hashes))
engine = json.loads((ROOT / 'docs/assets/playground/build.json').read_bytes())['engine']['version']
assert reports['python']['engine'] == reports['node']['engine'] == engine
renders = dict(packageVersion='playground-' + engine, engineVersion=engine,
    inputSha256=sha256(INPUTS.read_bytes()).hexdigest(), fontSha256=inputs['fontSha256'], cases=records)
(destination / 'renders.json').write_text(json.dumps(renders, indent=2) + '\n', encoding='utf-8')
result = verify(destination, INPUTS, ['wasi', 'python', 'node'], require_previews=True, preview_size=(240, 160))
(OUT / 'preformatted-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(ok=result['ok'], cases=len(result['cases']), pages=sum(r['pages'] for r in records))))
