"""Check geometry and pixels in actual WASI, Python and Node project output."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from playground_decorations import ROOT, FIXTURES, EXPECTATIONS, cases, inspect_pdf

parser = ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=ROOT / 'playground/project-verification')
args = parser.parse_args()
out = args.root.resolve()
export = json.loads((out / 'export-verification.json').read_text(encoding='utf-8'))
assert export['ok']
exports = {case['name']: case for case in export['cases']}
rows = []
for mode, path_for in [
    ('wasi', lambda name: out / (name + '-expected') / 'output.pdf'),
    ('python', lambda name: out / 'extracted projects with spaces' / name / 'output/document.pdf'),
    ('node', lambda name: out / 'extracted node projects with spaces' / name / 'output/document.pdf'),
]:
    for case, wanted in cases():
        name = 'decoration-' + case['name']
        path = path_for(name)
        row = inspect_pdf(path, case, wanted, path.with_name('decoration-independent-preview.png'))
        row.update(mode=mode)
        row['checks']['matchesWasiReference'] = row['pdfSha256'] == exports[name]['pdf_sha256']
        row['passed'] = all(row['checks'].values())
        rows.append(row)
failed = [row for row in rows if not row['passed']]
record = dict(at=datetime.now(timezone.utc).isoformat(), ok=not failed,
    fixtureSha256=sha256(FIXTURES.read_bytes()).hexdigest(),
    expectationsSha256=sha256(EXPECTATIONS.read_bytes()).hexdigest(),
    cases=rows, passed=len(rows) - len(failed), failed=len(failed),
    scope='16 fixed-font decoration inputs in three output paths; independent PDFium glyph geometry and pixels match retained public-core evidence.')
(out / 'decorations-verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps({key: value for key, value in record.items() if key != 'cases'}))
assert not failed, failed
