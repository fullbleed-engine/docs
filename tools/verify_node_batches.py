"""Execute the actual batch guide in an isolated install and inspect its PDF and page map."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node', default=shutil.which('node'))
parser.add_argument('--out', type=Path, default=ROOT / 'output/node-batch-verification')
parser.add_argument('--package', type=Path, help='Explicit local candidate tarball; otherwise install public fullbleed@0.9.0')
args = parser.parse_args()
node = Path(args.node).resolve()
npm = next(path for path in [node.parent / 'node_modules/npm/bin/npm-cli.js',
    node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'] if path.is_file())
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
consumer = out / 'consumer'
consumer.mkdir()
(consumer / 'package.json').write_text('{"private":true,"type":"module"}\n', encoding='utf-8')
(out / 'empty.npmrc').write_text('', encoding='utf-8')
env = {key: value for key, value in os.environ.items() if not key.upper().startswith('NPM_CONFIG_')
    and key.upper() not in ('NPM_TOKEN', 'NODE_AUTH_TOKEN', 'NODE_OPTIONS', 'RUST_MIN_STACK')}
env.update(PATH=str(node.parent) + os.pathsep + os.environ.get('PATH', ''),
    NPM_CONFIG_USERCONFIG=str(out / 'empty.npmrc'), NPM_CONFIG_CACHE=str(out / 'npm-cache'),
    NPM_CONFIG_REGISTRY='https://registry.npmjs.org/')
steps = []


def run(name, arguments):
    result = subprocess.run([str(node), *map(str, arguments)], cwd=consumer, env=env,
        capture_output=True, text=True, encoding='utf-8', timeout=180)
    log = out / (name + '.log')
    log.write_text(result.stdout + result.stderr, encoding='utf-8')
    assert result.returncode == 0, (name, result.stderr)
    steps.append(dict(name=name, exitCode=0, logSha256=sha256(log.read_bytes()).hexdigest()))
    return result.stdout


package = str(args.package.resolve()) if args.package else 'fullbleed@0.9.0'
run('install', [npm, 'install', '--ignore-scripts', '--no-audit', '--no-fund', '--save-exact', package])
installed = json.loads((consumer / 'node_modules/fullbleed/package.json').read_bytes())
lock = json.loads((consumer / 'package-lock.json').read_bytes())['packages']['node_modules/fullbleed']
assert installed['version'] == lock['version'] == '0.9.0' and installed['fullbleed']['engineVersion'] == '2.5.46'
if not args.package:
    assert lock['resolved'] == 'https://registry.npmjs.org/fullbleed/-/fullbleed-0.9.0.tgz'
guide = ROOT / 'docs/guides/node-pdf-batches.md'
text = guide.read_text(encoding='utf-8')
assert '**Node package 0.9.0**' in text and '**Fullbleed 2.5.46**' in text
blocks = re.findall(r'```javascript\n(.*?)\n```', text, re.S)
assert len(blocks) == 1
code = blocks[0] + '\n'
(consumer / 'notices.mjs').write_text(code, encoding='utf-8', newline='\n')
(out / 'notices.mjs').write_text(code, encoding='utf-8', newline='\n')
stdout = run('guide', ['notices.mjs'])
for name in ('notices.pdf', 'record-pages.json'):
    shutil.copyfile(consumer / name, out / name)
pdf = out / 'notices.pdf'
records = json.loads((out / 'record-pages.json').read_bytes())
assert len(records) == 2 and [row['recordIndex'] for row in records] == [0, 1]
assert records[0]['pageOffset'] == 0 and records[0]['pageCount'] == 1
assert records[1]['pageOffset'] == 1 and records[1]['pageCount'] == 4
assert all(row['missingGlyphs'] == [] for row in records)
reader = PdfReader(pdf, strict=True)
assert len(reader.pages) == sum(row['pageCount'] for row in records) <= 20
plain = lambda value: ' '.join(value.split())
page_text = [plain(page.extract_text() or '') for page in reader.pages]
expected = [
    'ACCOUNT NOTICE Account 1042 Your account is up to date. Thank you.',
    'ACCOUNT NOTICE Account 1043 ' + 'Your scheduled account review includes the following information. ' * 90,
]
for i, row in enumerate(records):
    first, last = row['pageOffset'], row['pageOffset'] + row['pageCount']
    assert plain(' '.join(page_text[first:last])) == plain(expected[i])
    assert f'Account {1042+i}: pages {first+1}–{last}' in stdout
for page in reader.pages:
    fonts = [font.get_object() for font in page['/Resources']['/Font'].values()]
    assert fonts and all('Inter' in str(font['/BaseFont']) for font in fonts)
    assert all('/FontFile2' in font['/DescendantFonts'][0].get_object()['/FontDescriptor'].get_object() for font in fonts)
images = []
(out / 'pages').mkdir()
with pdfium.PdfDocument(pdf) as document:
    assert len(document) == len(reader.pages)
    for index in range(len(document)):
        page = document[index]
        textpage = page.get_textpage()
        assert plain(textpage.get_text_range()) == page_text[index]
        textpage.close()
        bitmap = page.render(scale=1)
        image = bitmap.to_pil()
        path = out / 'pages' / f'page-{index+1}.png'
        try:
            image.save(path)
            images.append(dict(file=path.relative_to(out).as_posix(), width=image.width, height=image.height,
                sha256=sha256(path.read_bytes()).hexdigest()))
        finally:
            image.close(); bitmap.close(); page.close()
original = pdf.read_bytes()
run('repeat', ['notices.mjs'])
assert (consumer / 'notices.pdf').read_bytes() == original
assert json.loads((consumer / 'record-pages.json').read_bytes()) == records
report = dict(ok=True, checkedAt=datetime.now(timezone.utc).isoformat(), packageVersion='0.9.0', engineVersion='2.5.46',
    packageSource='local-candidate' if args.package else 'public-npm', packageIntegrity=lock['integrity'],
    localTarballSha256=sha256(args.package.read_bytes()).hexdigest() if args.package else None,
    guideSha256=sha256(guide.read_bytes()).hexdigest(), snippetSha256=sha256(code.encode()).hexdigest(),
    pdfSha256=sha256(original).hexdigest(), pages=len(reader.pages), records=records,
    embeddedFont='Inter', repeatedPdfAndReportsEqual=True, images=images, steps=steps,
    readers={name:version(name) for name in ('pypdf','pypdfium2','Pillow')},
    scope='Actual guide snippet, exact account text, complete record page ranges, embedded fonts, repeated bytes, and independent page rendering. Visual review is separate; no conformance claim.')
(out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(ok=True, packageSource=report['packageSource'], pages=report['pages'], records=len(records), pdfSha256=report['pdfSha256'])))
