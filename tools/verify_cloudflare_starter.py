"""Install the actual downloadable ZIP and exercise its Worker over local HTTP."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
import zipfile
from pypdf import PdfReader
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node', default=shutil.which('node'))
parser.add_argument('--out', type=Path, default=ROOT / 'output/cloudflare-starter-verification')
parser.add_argument('--port', type=int, default=9490)
args = parser.parse_args()
assert args.node, 'Node.js 22 or newer is required.'
node = Path(args.node).resolve()
npm = next((path for path in [node.parent / 'node_modules/npm/bin/npm-cli.js',
    node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'] if path.is_file()), None)
assert npm, 'Use an official Node distribution containing npm.'
assert 1024 < args.port < 65536
assets = ROOT / 'docs/assets/cloudflare-starter'
manifest = json.loads((assets / 'source.json').read_text(encoding='utf-8'))
assert manifest['schema'] == 'fullbleed.cloudflare-starter.v1'
archive_path = assets / 'project.zip'
assert sha256(archive_path.read_bytes()).hexdigest() == manifest['zipSha256']
for item in manifest['assets']:
    data = (assets / item['file']).read_bytes()
    assert len(data) == item['bytes'] and sha256(data).hexdigest() == item['sha256']
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix='download with spaces ', dir=out))
expected = {manifest['prefix'] + item['path']: item for item in manifest['files']}
with zipfile.ZipFile(archive_path) as archive:
    assert len(archive.namelist()) == len(set(archive.namelist())) == len(expected)
    assert set(archive.namelist()) == set(expected)
    for item in archive.infolist():
        path = PurePosixPath(item.filename)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename and ':' not in item.filename
        assert not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16) and item.file_size < 5 * 1024 * 1024
        data = archive.read(item)
        assert len(data) == expected[item.filename]['bytes']
        assert sha256(data).hexdigest() == expected[item.filename]['sha256']
        target = workspace.joinpath(*path.parts).resolve()
        assert target.is_relative_to(workspace)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
project = workspace / manifest['prefix'].rstrip('/')
env = {**os.environ, 'PATH': str(node.parent) + os.pathsep + os.environ.get('PATH', ''), 'WRANGLER_SEND_METRICS': 'false',
       'FULLBLEED_WORKER_URL': f'http://127.0.0.1:{args.port}'}
commands = []


def run(label, arguments):
    with (out / (label + '.log')).open('w', encoding='utf-8') as log:
        result = subprocess.run(list(map(str, arguments)), cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=240)
    assert result.returncode == 0, f'{label} failed; inspect {out / (label + ".log")}'
    commands.append(dict(name=label, exitCode=0))
    print(label + ': passed', flush=True)


run('install', [node, npm, 'ci', '--ignore-scripts', '--no-audit', '--no-fund'])
installed = json.loads((project / 'node_modules/fullbleed/package.json').read_text())
build = json.loads((project / 'node_modules/fullbleed/dist/build.json').read_text())
assert installed['version'] == build['packageVersion'] == manifest['packageVersion'] == '0.8.0'
assert build['engineVersion'] == manifest['engineVersion'] == '2.5.29'
assert build['files']['dist/engine.wasm']['sha256'] == manifest['wasmSha256']
lock = json.loads((project / 'package-lock.json').read_text())
assert lock['packages']['node_modules/fullbleed']['integrity'] == manifest['packageIntegrity']
run('input-tests', [node, npm, 'test'])
run('bundle', [node, npm, 'run', 'build'])
config = json.loads((project / 'wrangler.json').read_text())
assert config['workers_dev'] is False and config['preview_urls'] is False
assert not config.get('route') and not config.get('routes')
with socket.socket() as probe:
    assert probe.connect_ex(('127.0.0.1', args.port)) != 0, 'The test port is already occupied.'
wrangler = project / 'node_modules/wrangler/bin/wrangler.js'
creation = dict(creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW) if os.name == 'nt' else dict(start_new_session=True)
with (out / 'worker.log').open('w', encoding='utf-8') as log:
    worker = subprocess.Popen([str(node), str(wrangler), 'dev', '--local', '--ip', '127.0.0.1', '--port', str(args.port),
                               '--inspector-port', '0'], cwd=project, env=env, stdout=log, stderr=subprocess.STDOUT, **creation)
    try:
        deadline = time.monotonic() + 60
        while True:
            assert worker.poll() is None, 'Wrangler exited; inspect worker.log.'
            try:
                with urlopen(env['FULLBLEED_WORKER_URL'] + '/health', timeout=1) as response:
                    if json.load(response).get('ok') is True: break
            except Exception:
                pass
            if time.monotonic() >= deadline: raise TimeoutError('Local Worker did not start.')
            time.sleep(0.25)
        run('http-tests', [node, npm, 'run', 'test:worker'])
    finally:
        if worker.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(worker.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            else:
                try: os.killpg(worker.pid, signal.SIGTERM)
                except ProcessLookupError: pass
            try: worker.wait(timeout=10)
            except subprocess.TimeoutExpired:
                if os.name != 'nt': os.killpg(worker.pid, signal.SIGKILL)
                else: worker.kill()
                worker.wait(timeout=10)
assert worker.poll() is not None
with socket.socket() as probe:
    assert probe.connect_ex(('127.0.0.1', args.port)) != 0, 'The local Worker must stop.'
http = json.loads((project / 'output/http-verification.json').read_text(encoding='utf-8'))
assert http['ok'] and http['recovery'] and len(http['records']) == 6 and len(http['errors']) == 10
checked = []
for item in http['records']:
    path = project / 'output' / (item['name'] + '.pdf')
    assert sha256(path.read_bytes()).hexdigest() == item['pdf']
    pdf = PdfReader(path)
    assert item['minPages'] <= len(pdf.pages) <= item['maxPages']
    text = ' '.join(' '.join(page.extract_text().split()) for page in pdf.pages)
    assert all(value in text for value in item['text'])
    assert all(value in ''.join(text.split()) for value in item['trackedText'])
    shutil.copyfile(path, out / path.name)
    checked.append({**item, 'pages': len(pdf.pages)})
assert (out / 'sample.pdf').read_bytes() == (assets / 'invoice.pdf').read_bytes()
assert (out / 'long.pdf').read_bytes() == (assets / 'long-invoice.pdf').read_bytes()
preview_script = project / 'verify-node-preview.mjs'
preview_script.write_text('''
import {renderPdf} from 'fullbleed';
import {Invoice} from './src/document.mjs';
import {validateInvoice} from './src/handler.mjs';
import {readFile,writeFile} from 'node:fs/promises';
const data=validateInvoice(JSON.parse(await readFile('sample.json','utf8')));
const result=await Invoice({data}).renderPdf(renderPdf,{defaultStyles:false,maxPages:10,previewDpi:96});
await writeFile('output/node.pdf',result.pdf);
await writeFile('output/node.png',result.previews[0]);
''', encoding='utf-8', newline='\n')
run('node-preview', [node, preview_script])
assert (project / 'output/node.pdf').read_bytes() == (out / 'sample.pdf').read_bytes()
assert (project / 'output/node.png').read_bytes() == (assets / 'invoice.png').read_bytes()
with Image.open(project / 'output/node.png') as image:
    image.load()
    assert image.width > 100 and image.height > 100 and image.convert('RGB').getextrema() != ((255, 255),) * 3
shutil.copyfile(project / 'output/node.png', out / 'invoice.png')
report = dict(ok=True, checkedAt=datetime.now(timezone.utc).isoformat(), packageVersion=manifest['packageVersion'],
              engineVersion=manifest['engineVersion'], sourceCommit=manifest['sourceCommit'], zipSha256=manifest['zipSha256'],
              packageIntegrity=manifest['packageIntegrity'], platform=sys.platform,
              wrangler=json.loads((project / 'node_modules/wrangler/package.json').read_text())['version'],
              workerd=json.loads((project / 'node_modules/workerd/package.json').read_text())['version'],
              commands=commands, records=checked, errors=http['errors'], recovery=True, serverStopped=True,
              previewMatches=True, localOnly=True, hostedVerified=False, freePlanVerified=False)
(out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(ok=True, invoices=len(checked), pages=sum(row['pages'] for row in checked), errors=len(http['errors']))))
