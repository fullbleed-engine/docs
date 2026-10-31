"""Compare actual WASI, Python and Node projects for registered page fonts."""
from hashlib import sha256
import json
from pathlib import Path

from playground_font_inspection import ROOT, ENGINE, NODE, FIXTURE_PATH, fixtures, inspect_pdf

out = ROOT / 'playground/project-verification'
destination = out / 'page-font-independent'
destination.mkdir(exist_ok=True)
source = fixtures()
references = json.loads((ROOT / 'docs/assets/playground/verification.json').read_bytes())
assert references['ok'] and references['engine'] == ENGINE
reference_cases = {row['name']: row for row in references['fixtures']}
reports = {mode: json.loads((out / name).read_bytes()) for mode, name in [
    ('wasi', 'export-verification.json'), ('python', 'python-verification.json'), ('node', 'node-verification.json')]}
assert all(report['ok'] for report in reports.values())
assert reports['python']['engine'] == reports['node']['engine'] == ENGINE
assert reports['node']['package'] == NODE
record = {'ok': False, 'engine': ENGINE, 'nodePackage': NODE, 'fixtureSha256': sha256(FIXTURE_PATH.read_bytes()).hexdigest(), 'pairs': []}
try:
    expected_names = {f'page-font-{case["name"]}-{kind}' for case in source['cases'] for kind in ['control', 'alias']}
    for mode, report in reports.items():
        selected = {row['name']: row for row in report['cases'] if row['name'].startswith('page-font-')}
        assert set(selected) == expected_names
        for specimen in source['cases']:
            pair = []
            previews = []
            for kind in ['control', 'alias']:
                name = f'page-font-{specimen["name"]}-{kind}'
                expected = out / (name + '-expected')
                folder = expected if mode == 'wasi' else out / ('extracted projects with spaces' if mode == 'python' else 'extracted node projects with spaces') / name
                pdf = folder / ('output.pdf' if mode == 'wasi' else 'output/document.pdf')
                assert (folder / 'input.html').read_bytes() == specimen['html'].encode()
                assert (folder / 'style.css').read_bytes() == specimen[kind + 'Css'].encode()
                assert pdf.read_bytes() == (expected / 'output.pdf').read_bytes()
                assert sha256(pdf.read_bytes()).hexdigest() == reference_cases[name]['hashes']['output.pdf']
                result = inspect_pdf(pdf, specimen, destination / mode / name)
                paths = [expected / f'page-{i + 1}.png' for i in range(len(specimen['footerFaces']))]
                if mode != 'wasi':
                    rendered = json.loads((folder / 'output/render.json').read_bytes())
                    assert rendered['engine'] == ENGINE and len(rendered['previews']) == len(paths)
                    assert all(Path(path).resolve().is_relative_to(folder.resolve()) for path in rendered['previews'])
                    assert [Path(path).read_bytes() for path in rendered['previews']] == [path.read_bytes() for path in paths]
                previews.append([sha256(path.read_bytes()).hexdigest() for path in paths])
                pair.append(result)
            assert pair[0] == pair[1], (mode, specimen['name'])
            assert previews[0] == previews[1]
            record['pairs'].append({'mode': mode, 'name': specimen['name'], **pair[0], 'nativePreviewSha256': previews[0]})
    record.update(ok=True, pairsVerified=24, pagesVerified=54, scope='Eight font alias/control comparisons in WASI and both exported languages, including embedded faces, footer sizes, PDF bytes, native previews and independent PDFium pixels. No general CSS or conformance claim.')
finally:
    raw = json.dumps(record, indent=2) + '\n'
    (destination / 'verification.json').write_text(raw, encoding='utf8')
    (ROOT / 'docs/assets/playground/page-font-verification.json').write_text(raw, encoding='utf8')
print(json.dumps({'ok': record['ok'], 'pairs': len(record['pairs']), 'engine': ENGINE}))
