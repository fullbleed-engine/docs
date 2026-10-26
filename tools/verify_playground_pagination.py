"""Inspect page flow in actual WASI output and both exported language projects."""
from argparse import ArgumentParser
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from playground_pagination import FIXTURES, cases, inspect_pdf

ROOT = Path(__file__).resolve().parents[1]
parser = ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, default=ROOT / 'playground/project-verification')
parser.add_argument('--negative-control', action='store_true')
args = parser.parse_args()
out = args.root.resolve()
records = []
if args.negative_control:
    manifest = json.loads((out / 'renders.json').read_text(encoding='utf-8'))
    assert manifest['engine'] == '2.5.29'
    assert manifest['fixture_sha256'] == sha256(FIXTURES.read_bytes()).hexdigest()
    modes = [('old-wasi', lambda case: out / (case['name'] + '.pdf'))]
else:
    export = json.loads((out / 'export-verification.json').read_text(encoding='utf-8'))
    assert export['ok']
    modes = [
        ('wasi', lambda case: out / (case['name'] + '-expected') / 'output.pdf'),
        ('python', lambda case: out / 'extracted projects with spaces' / case['name'] / 'output/document.pdf'),
        ('node', lambda case: out / 'extracted node projects with spaces' / case['name'] / 'output/document.pdf'),
    ]
for mode, path_for in modes:
    for case in cases():
        records.append({'mode': mode, **inspect_pdf(path_for(case), case)})
failed = [record for record in records if not record['passed']]
if args.negative_control:
    ok = {record['name'] for record in failed} == {case['name'] for case in cases() if case['name'] != 'pagination-break-fixed'}
else:
    ok = not failed
record = {'ok': ok, 'at': datetime.now(timezone.utc).isoformat(), 'negative_control': args.negative_control,
          'fixture_sha256': sha256(FIXTURES.read_bytes()).hexdigest(), 'cases': records,
          'passed': len(records) - len(failed), 'failed': len(failed)}
(out / 'pagination-verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({key: value for key, value in record.items() if key != 'cases'}))
assert ok, failed
