"""Execute the downloadable queue project and guide using the public npm package."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

import pypdf
import pypdfium2

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node', default=shutil.which('node'))
parser.add_argument('--out', type=Path, default=ROOT / 'output/node-queue-verification')
parser.add_argument('--zip', type=Path)
parser.add_argument('--update-assets', action='store_true')
args = parser.parse_args()
node = Path(args.node).resolve()
npm = next(p for p in [node.parent / 'node_modules/npm/bin/npm-cli.js',
                       node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'] if p.is_file())
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix='queue project with spaces ', dir=out))
assets = ROOT / 'docs/assets/node-queue'
manifest = json.loads((assets / 'source.json').read_text(encoding='utf-8'))
archive_path = args.zip or assets / 'project.zip'
digest = lambda data: sha256(data).hexdigest()
checks = []


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})
    assert condition, name


check('download ZIP matches the source manifest', digest(archive_path.read_bytes()) == manifest['zip_sha256'])
with zipfile.ZipFile(archive_path) as archive:
    check('ZIP contains exactly the reviewed files',
          sorted(archive.namelist()) == sorted('node-pdf-queue/' + f['path'] for f in manifest['files']))
    for record in manifest['files']:
        name = record['path']
        data = archive.read('node-pdf-queue/' + name)
        destination = (workspace / 'node-pdf-queue' / name).resolve()
        assert destination.is_relative_to(workspace)
        check('source and ZIP bytes: ' + name, len(data) == record['bytes'] and digest(data) == record['sha256']
              and data == (ROOT / 'examples/node-queue' / name).read_bytes())
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
project = workspace / 'node-pdf-queue'
env = {**os.environ, 'PATH': str(node.parent) + os.pathsep + os.environ['PATH']}
commands = []


def run(label, command, cwd=project):
    result = subprocess.run([str(node), *map(str, command)], cwd=cwd, env=env,
                            capture_output=True, text=True, encoding='utf-8', timeout=180)
    (out / (label + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
    (out / (label + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
    check(label + ' command succeeds', result.returncode == 0)
    commands.append({'name': label, 'exit_code': result.returncode})
    return result.stdout


run('install', [npm, 'ci', '--ignore-scripts', '--no-audit', '--no-fund'])
package = json.loads((project / 'node_modules/fullbleed/package.json').read_text(encoding='utf-8'))
lock = json.loads((project / 'package-lock.json').read_text(encoding='utf-8'))
check('installed version and engine match the guide', package['version'] == manifest['package_version']
      and package['fullbleed']['engineVersion'] == manifest['engine_version'])
check('lockfile integrity matches the verified release',
      lock['packages']['node_modules/fullbleed']['integrity'] == manifest['package_integrity'])
(project / 'observe.mjs').write_text('''import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
let created = 0, peak = 0;
const active = new Set();
process.on('worker', worker => {
  created++; active.add(worker); peak = Math.max(peak, active.size);
  worker.once('exit', () => active.delete(worker));
});
assert.equal(import.meta.resolve('fullbleed'), new URL('node_modules/fullbleed/src/index.js', import.meta.url).href);
await import('./render.mjs');
assert.equal(created, 6); assert.equal(peak, 2); assert.equal(active.size, 0);
await writeFile('workers.json', JSON.stringify({ created, peak, remaining: active.size,
  node: process.version, platform: process.platform }));
''', encoding='utf-8')
batch = json.loads(run('batch', ['observe.mjs']))
workers = json.loads((project / 'workers.json').read_text(encoding='utf-8'))
check('six distinct invoices rendered without missing glyphs', len(batch['invoices']) == 6
      and len({row['reference'] for row in batch['invoices']}) == 6
      and all(row['pages'] == 1 and row['missingGlyphs'] == 0 for row in batch['invoices']))
check('actual worker concurrency stays at two and all workers exit',
      workers['created'] == 6 and workers['peak'] == 2 and workers['remaining'] == 0)


def inspect(path, expected):
    pdf = pypdf.PdfReader(path)
    check(path.name + ': one PDF page', len(pdf.pages) == 1)
    texts = {'pypdf': pdf.pages[0].extract_text()}
    with pypdfium2.PdfDocument(path) as document:
        assert len(document) == 1
        page = document[0]
        textpage = page.get_textpage()
        try:
            texts['PDFium'] = textpage.get_text_range()
        finally:
            textpage.close()
            page.close()
    for reader, text in texts.items():
        normalized = ' '.join(text.split())
        check(path.name + ': expected fields in ' + reader, all(value in normalized for value in expected))


rendered = project / 'output/queued-invoices'
outputs = {}
for row in batch['invoices']:
    name = row['reference'] + '.pdf'
    inspect(rendered / name, [row['reference'], row['customer'], '1,870.00'])
for name, expected in manifest['rendered'].items():
    data = (rendered / name).read_bytes()
    outputs[name] = digest(data)
    check(name + ': matches reviewed output', outputs[name] == expected)
    if args.update_assets:
        (assets / name).write_bytes(data)
    else:
        check(name + ': published asset bytes match', data == (assets / name).read_bytes())
run('replay', ['render.mjs'])
check('exact-input replay preserves every PDF and PNG',
      all(digest((rendered / name).read_bytes()) == value for name, value in outputs.items()))

guide = (ROOT / 'docs/guides/node-render-queue.md').read_text(encoding='utf-8')
snippets = re.findall(r'```javascript\n(.*?)```', guide, re.S)
check('guide contains one executable JavaScript example', len(snippets) == 1)
snippet_dir = project / 'guide-snippet'
snippet_dir.mkdir()
(snippet_dir / 'guide.mjs').write_text(snippets[0], encoding='utf-8')
run('guide-snippet', ['guide.mjs'], snippet_dir)
for reference in [1042, 1043, 1044]:
    inspect(snippet_dir / f'invoice-{reference}.pdf', [f'NS-{reference}', '1,200.00'])

report = {'schema': 'fullbleed.node-queue-example-verification.v1', 'ok': True,
          'package_version': package['version'], 'engine_version': package['fullbleed']['engineVersion'],
          'workers': workers, 'readers': ['pypdf', 'PDFium'], 'commands': commands,
          'project_zip_sha256': manifest['zip_sha256'], 'outputs': outputs, 'checks': checks,
          'scope': 'This downloaded batch, guide snippet, and exact replay; no throughput or memory-capacity claim.'}
(out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
if args.update_assets:
    (assets / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'ok': True, 'checks': len(checks), 'workers': workers}))
