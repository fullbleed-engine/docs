"""Require correct actual PDF fonts in WASI and both exported project runtimes."""
from hashlib import sha256
import json

from playground_font_cascade import ROOT, FIXTURES, cases, inspect_pdf

out = ROOT / 'playground/project-verification'
export = json.loads((out / 'export-verification.json').read_bytes())
assert export['ok']
exports = {row['name']: row for row in export['cases']}
records = []
for mode, path_for in [
    ('wasi', lambda name: out / (name + '-expected') / 'output.pdf'),
    ('python', lambda name: out / 'extracted projects with spaces' / name / 'output/document.pdf'),
    ('node', lambda name: out / 'extracted node projects with spaces' / name / 'output/document.pdf'),
]:
    for fixture in cases():
        row = inspect_pdf(path_for(fixture['name']), fixture)
        row['mode'] = mode
        row['checks']['matchesWasiReference'] = row['pdfSha256'] == exports[fixture['name']]['pdf_sha256']
        row['passed'] = all(row['checks'].values())
        records.append(row)
report = dict(ok=all(row['passed'] for row in records), engine='2.5.51', nodePackage='0.9.4',
              fixtureSha256=sha256(FIXTURES.read_bytes()).hexdigest(), cases=records,
              scope='Thirteen font-cascade witnesses in WASI and actual Python/Node exports; two text readers, actual text-font names, visible output and matching PDF bytes.')
raw = json.dumps(report, indent=2) + '\n'
(out / 'font-cascade-verification.json').write_text(raw, encoding='utf8')
(ROOT / 'docs/assets/playground/font-cascade-verification.json').write_text(raw, encoding='utf8')
assert report['ok'] and len(records) == 39, records
print(json.dumps(dict(ok=True, documents=len(records), engine=report['engine'])))
