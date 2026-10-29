"""Independently inspect radial-gradient PDFs from WASI, Python and Node exports."""
from hashlib import sha256
import json
from pathlib import Path

from playground_radial_gradients import ENGINE_VERSION, NODE_VERSION, FIXTURES, cases, inspect_pdf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'playground/project-verification'
destination = OUT / 'radial-independent'
destination.mkdir(parents=True, exist_ok=True)
result = dict(ok=False, engine=ENGINE_VERSION, nodePackage=NODE_VERSION,
              fixtureSha256=sha256(FIXTURES.read_bytes()).hexdigest(), cases=[])
try:
    assert json.loads((ROOT / 'docs/assets/playground/build.json').read_bytes())['engine']['version'] == ENGINE_VERSION
    reports = {mode: json.loads((OUT / filename).read_bytes()) for mode, filename in (
        ('wasi', 'export-verification.json'), ('python', 'python-verification.json'), ('node', 'node-verification.json'))}
    assert reports['python']['engine'] == reports['node']['engine'] == ENGINE_VERSION
    assert reports['node']['package'] == NODE_VERSION
    fixtures = cases()
    names = {'radial-endpoint-' + case['name'] for case in fixtures}
    for mode, report in reports.items():
        assert report['ok']
        selected = [row for row in report['cases'] if row['name'].startswith('radial-endpoint-')]
        assert len(selected) == 12 and {row['name'] for row in selected} == names
        selected = {row['name']: row for row in selected}
        for fixture in fixtures:
            name = 'radial-endpoint-' + fixture['name']
            case = selected[name]
            expected = OUT / (name + '-expected')
            assert case['pages'] == 1
            if mode == 'wasi':
                project, pdf, preview = expected, expected / 'output.pdf', expected / 'page-1.png'
            else:
                project = OUT / ('extracted projects with spaces' if mode == 'python' else 'extracted node projects with spaces') / name
                pdf = project / 'output/document.pdf'
                rendered = json.loads((project / 'output/render.json').read_bytes())
                assert rendered['engine'] == ENGINE_VERSION and len(rendered['previews']) == 1
                preview = Path(rendered['previews'][0])
                assert preview.resolve().is_relative_to(project.resolve())
            assert (project / 'input.html').read_bytes() == fixture['html'].encode()
            assert (project / 'style.css').read_bytes() == fixture['css'].encode()
            assert pdf.read_bytes() == (expected / 'output.pdf').read_bytes()
            assert preview.read_bytes() == (expected / 'page-1.png').read_bytes()
            assert sha256(pdf.read_bytes()).hexdigest() == case['pdf_sha256']
            folder = destination / (mode + '-' + fixture['name'])
            folder.mkdir(exist_ok=True)
            (folder / 'document.pdf').write_bytes(pdf.read_bytes())
            (folder / 'native-96.png').write_bytes(preview.read_bytes())
            row = inspect_pdf(folder / 'document.pdf', fixture, folder / 'native-96.png', folder / 'pdfium-144.png')
            row.update(mode=mode, directory=folder.name)
            result['cases'].append(row)
            assert row['passed'], row
    result.update(ok=True, passed=36, failed=0,
                  scope='Twelve retained radial-gradient inputs rendered through WASI and both exported project runners. Exact release PDFs, native 96 dpi outer colors, independent 144 dpi pixels, and Type 3 stitching bounds. No general parity or conformance claim.')
except BaseException as error:
    result['error'] = str(error)
    raise
finally:
    raw = json.dumps(result, indent=2) + '\n'
    (destination / 'verification.json').write_text(raw, encoding='utf-8')
    (ROOT / 'docs/assets/playground/radial-gradient-verification.json').write_text(raw, encoding='utf-8')
print(json.dumps(dict(ok=result['ok'], cases=len(result['cases']))))
