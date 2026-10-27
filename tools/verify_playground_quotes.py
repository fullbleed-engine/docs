"""Verify quotation content in actual WASI, Python and Node project output."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from playground_quotes import ROOT, FIXTURES, cases, inspect_pdf

parser = ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=ROOT / 'playground/project-verification')
args = parser.parse_args()
out = args.root.resolve()
export = json.loads((out / 'export-verification.json').read_text(encoding='utf-8'))
assert export['ok']
exports = {case['name']: case for case in export['cases']}
records = []
for mode, path_for in [
    ('wasi', lambda name: out / (name + '-expected') / 'output.pdf'),
    ('python', lambda name: out / 'extracted projects with spaces' / name / 'output/document.pdf'),
    ('node', lambda name: out / 'extracted node projects with spaces' / name / 'output/document.pdf'),
]:
    for fixture in cases():
        name = 'quote-' + fixture['name']
        path = path_for(name)
        row = inspect_pdf(path, fixture)
        row.update(mode=mode)
        row['checks']['matchesWasiReference'] = row['pdfSha256'] == exports[name]['pdf_sha256']
        row['passed'] = all(row['checks'].values())
        records.append(row)
failed = [row for row in records if not row['passed']]
report = dict(at=datetime.now(timezone.utc).isoformat(), ok=not failed,
    fixtureSha256=sha256(FIXTURES.read_bytes()).hexdigest(), cases=records,
    passed=len(records) - len(failed), failed=len(failed),
    scope='41 retained quotation inputs in three actual output paths; independent PDF text, page geometry, visible raster output and reference hashes.')
(out / 'quotes-verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in report.items() if key != 'cases'}))
assert not failed, failed
