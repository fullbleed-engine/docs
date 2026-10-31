"""Execute the actual HTML migration download and guide with both renderers."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
from zipfile import ZipFile
from node_html_output import inspect

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node', default=shutil.which('node'))
parser.add_argument('--chrome', help='An already provisioned Chrome compatible with the pinned Puppeteer.')
parser.add_argument('--out', type=Path, default=Path('output/node-html-verification'))
parser.add_argument('--update-assets', action='store_true')
args = parser.parse_args()
node = Path(args.node).resolve()
npm = next((path for path in [node.parent / 'node_modules/npm/bin/npm-cli.js',
                              node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'] if path.is_file()), None)
assert npm, 'Use an official Node distribution containing npm.'
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix='html project with spaces ', dir=out))
assets = ROOT / 'docs/assets/node-html'
manifest = json.loads((assets / 'source.json').read_text(encoding='utf8'))
digest = lambda value: sha256(value).hexdigest()
archive_path = assets / 'project.zip'
assert digest(archive_path.read_bytes()) == manifest['zip_sha256']
with ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    prefix = 'node-html-to-pdf/'
    assert sorted(archive.namelist()) == sorted(prefix + name for name in manifest['files'])
    for name, expected in manifest['files'].items():
        destination = (workspace / name).resolve()
        assert destination.is_relative_to(workspace)
        data = archive.read(prefix + name)
        assert len(data) == expected['bytes'] and digest(data) == expected['sha256']
        assert data == (ROOT / 'examples/node-html' / name).read_bytes(), 'Rebuild the ZIP after changing ' + name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

env = dict(os.environ, PATH=str(node.parent) + os.pathsep + os.environ['PATH'])
env['PUPPETEER_CACHE_DIR'] = str(out / 'browser-cache')
if args.chrome:
    env.update(FULLBLEED_CHROME_PATH=str(Path(args.chrome).resolve()), PUPPETEER_SKIP_DOWNLOAD='true')
else:
    # Install the browser selected by this Puppeteer release, not an unrelated
    # Playwright/system browser that happens to be on the runner.
    env.pop('FULLBLEED_CHROME_PATH', None)
    env.pop('PUPPETEER_SKIP_DOWNLOAD', None)
commands = []

def run(label, arguments, cwd=workspace, timeout=180, extra_env=None):
    with (out / (label + '.stdout.log')).open('w', encoding='utf8') as stdout, \
            (out / (label + '.stderr.log')).open('w', encoding='utf8') as stderr:
        process = subprocess.Popen([str(node), *map(str, arguments)], cwd=cwd, env={**env, **(extra_env or {})},
                                   stdout=stdout, stderr=stderr, start_new_session=os.name != 'nt')
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Stop only the process tree created by this check.
            if os.name == 'nt':
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=False,
                               stdout=stderr, stderr=stderr)
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise
    commands.append({'name': label, 'exitCode': code})
    assert code == 0, f'{label} failed; inspect its retained stdout/stderr logs.'
    print(label + ': passed', flush=True)

run('fullbleed-install', [npm, 'ci', '--ignore-scripts', '--no-audit', '--no-fund'])
installed = json.loads((workspace / 'node_modules/fullbleed/package.json').read_text(encoding='utf8'))
assert installed['version'] == manifest['package_version']
assert installed['fullbleed']['engineVersion'] == manifest['engine_version']
run('fullbleed-render', [npm, 'run', '--silent', 'render'])
run('reference-install', [npm, 'ci', '--no-audit', '--no-fund'], workspace / 'reference', timeout=480)
puppeteer = json.loads((workspace / 'reference/node_modules/puppeteer/package.json').read_text(encoding='utf8'))
assert puppeteer['version'] == manifest['puppeteer_version']
run('reference-render', [npm, 'run', '--silent', 'render'], workspace / 'reference')

# Run the downloaded renderer with connections that outlive its final page.
# The preload rescues its own fixture after two seconds if shutdown stalls,
# marks the child as failed, and records the cause without an unbounded wait.
connection_checks = []
for mode in ['unused', 'partial']:
    label = 'reference-connections-' + mode
    report_path = out / (label + '.json')
    case_output = out / 'connection-cases' / mode / 'output'
    run(label, ['--import', Path(__file__).resolve().with_name('check_node_html_reference_connections.mjs').as_uri(),
                'render.mjs', 'all', case_output], workspace / 'reference',
        extra_env={'FULLBLEED_REFERENCE_CONNECTION_CASE': mode,
                   'FULLBLEED_REFERENCE_CONNECTION_REPORT': str(report_path)})
    report = json.loads(report_path.read_text(encoding='utf8'))
    assert report['ok'] and not report['rescueNeeded'], report
    rendered = json.loads((case_output / 'render.json').read_text(encoding='utf8'))
    assert [result['name'] for result in rendered['documents']] == ['short', 'long']
    for result in rendered['documents']:
        name = result['name']
        ordinary = workspace / 'output/chromium' / name
        assert (case_output / name / 'input.html').read_bytes() == (ordinary / 'input.html').read_bytes()
        assert result['pdfSha256'] == digest((case_output / name / 'document.pdf').read_bytes())
        assert result['assetsLoaded'] == {'font': True, 'images': True}
        assert all(request['allowed'] for request in result['requests'])
    connection_checks.append(report)

guide = (ROOT / 'docs/guides/node-html-to-pdf.md').read_text(encoding='utf8')
blocks = re.findall(r'```javascript\n(.*?)```', guide, re.S)
assert len(blocks) == 1
(workspace / 'example.mjs').write_text(blocks[0], encoding='utf8', newline='\n')
run('guide-snippet', ['example.mjs'])
assert (workspace / 'order.pdf').read_bytes() == (workspace / 'output/fullbleed/long/document.pdf').read_bytes()
assert f"3 pages; engine {manifest['engine_version']}" in (out / 'guide-snippet.stdout.log').read_text(encoding='utf8')

records = json.loads((workspace / 'records.json').read_text(encoding='utf8'))
render_records, checked = {}, {}
baseline = None if args.update_assets else json.loads((assets / 'verification.json').read_text(encoding='utf8'))
for renderer in ['fullbleed', 'chromium']:
    render_record = json.loads((workspace / 'output' / renderer / 'render.json').read_text(encoding='utf8'))
    render_records[renderer] = render_record
    checked[renderer] = {}
    for result in render_record['documents']:
        name = result['name']
        folder = workspace / 'output' / renderer / name
        assert result['inputSha256'] == digest((folder / 'input.html').read_bytes())
        assert result['pdfSha256'] == digest((folder / 'document.pdf').read_bytes())
        proof = inspect(folder / 'document.pdf', records[name], out / 'independent-previews' / renderer / name)
        assert proof['pages'] == (1 if name == 'short' else 3)
        assert proof['totalCents'] == result['totalCents'] and proof['items'] == result['items']
        if renderer == 'fullbleed':
            assert result['pages'] == proof['pages'] and result['missingGlyphs'] == 0
            assert result['engineVersion'] == manifest['engine_version']
            native_hashes = [digest((folder / f'page-{number}.png').read_bytes()) for number in range(1, proof['pages'] + 1)]
            assert native_hashes == result['previewSha256']
            proof['nativePreviewSha256'] = native_hashes
            if baseline:
                expected = baseline['checked'][renderer][name]
                assert proof['pdfSha256'] == expected['pdfSha256'], 'Fullbleed PDF differs from the reviewed baseline'
                assert native_hashes == expected['nativePreviewSha256'], 'Fullbleed preview differs from the reviewed baseline'
        else:
            assert result['assetsLoaded'] == {'font': True, 'images': True}
            assert all(request['allowed'] for request in result['requests'])
            assert {'/document', '/Brand-Regular.ttf', '/Brand-Bold.ttf', '/assets/logo.svg'} <= {request['path'] for request in result['requests']}
        checked[renderer][name] = proof
        if args.update_assets:
            destination = assets / renderer / name
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(folder / 'document.pdf', destination / 'document.pdf')
            for number in range(1, proof['pages'] + 1):
                preview = folder / f'page-{number}.png' if renderer == 'fullbleed' else out / 'independent-previews' / renderer / name / f'page-{number}.png'
                shutil.copyfile(preview, destination / preview.name)
        print(f'{renderer}/{name}: {proof["pages"]} pages; content, fonts, logo and bounds passed', flush=True)
    if args.update_assets:
        shutil.copyfile(workspace / 'output' / renderer / 'render.json', assets / renderer / 'render.json')
for name in ['short', 'long']:
    assert (workspace / 'output/fullbleed' / name / 'input.html').read_bytes() == (workspace / 'output/chromium' / name / 'input.html').read_bytes()

record = {'schema': 'fullbleed.node-html-verification.v1', 'ok': True,
          'packageVersion': installed['version'], 'engineVersion': installed['fullbleed']['engineVersion'],
          'puppeteerVersion': puppeteer['version'], 'browserVersion': render_records['chromium']['browserVersion'],
          'node': render_records['fullbleed']['node'], 'platform': os.name,
          'projectZipSha256': manifest['zip_sha256'], 'sameHtmlAndAssets': True,
          'guideSnippetMatchesLongPdf': True, 'guideSnippetSha256': digest(blocks[0].encode('utf8')),
          'commands': commands, 'checked': checked, 'referenceConnectionChecks': connection_checks,
          'scope': 'Two fictional static-HTML fixtures. No general layout parity, performance or PDF conformance claim.'}
(out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8', newline='\n')
if args.update_assets:
    (assets / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8', newline='\n')
print(json.dumps({'ok': True, 'verification': str(out / 'verification.json')}))
