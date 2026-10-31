"""Check flowing invoice PDFs, previews, and real saved-project downloads."""
import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import threading
import zipfile

from playwright.sync_api import expect, sync_playwright
from playground_invoice import cases, inspect

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--site', type=Path)
    source.add_argument('--origin')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'webkit'], default='chrome')
    parser.add_argument('--quick', action='store_true', help='Only the short and 24-line cases.')
    parser.add_argument('--skip-replay', action='store_true', help='Browser checks only; no Python/Node subprocesses.')
    parser.add_argument('--reference', type=Path, help='Compare PDF and preview bytes to another browser run.')
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--npm-cli', type=Path)
    args = parser.parse_args()
    if not args.skip_replay:
        if not args.node:
            parser.error('Project replay requires Node.js 22 or newer; use --node to select it.')
        node_version = subprocess.check_output([args.node, '--version'], text=True).strip()
        if int(node_version.removeprefix('v').split('.')[0]) < 22:
            parser.error(f'Project replay requires Node.js 22 or newer, found {node_version}; use --node to select it.')
        npm_cli = args.npm_cli
        if npm_cli is None:
            npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
            if not npm:
                parser.error('Project replay requires npm; pass --npm-cli explicitly.')
            npm_bin = Path(npm).resolve().parent
            npm_cli = next((path for path in [npm_bin / 'node_modules/npm/bin/npm-cli.js',
                                             npm_bin / 'npm-cli.js'] if path.is_file()), None)
        if npm_cli is None or not npm_cli.is_file():
            parser.error('Cannot locate npm beside Node.js; pass --npm-cli explicitly.')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    server = None
    origin = args.origin
    if args.site:
        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(args.site.resolve()), **kw)
            def log_message(self, *a):
                pass
            def end_headers(self):
                self.send_header('Cache-Control', 'no-store')
                super().end_headers()
            def copyfile(self, source, outputfile):
                try:
                    super().copyfile(source, outputfile)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
    origin = origin.rstrip('/')
    reference = {row['name']: row for row in json.loads(args.reference.read_text(encoding='utf-8'))['cases']} if args.reference else {}
    records, exports, errors, network = [], [], [], []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel='chrome') if args.browser == 'chrome' else getattr(p, args.browser).launch()
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: network.append({'url': request.url, 'method': request.method}))
            def ready():
                expect(page.locator('#pg-download')).to_have_attribute('href', re.compile(r'^blob:'), timeout=120000)
                expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
                expect(page.locator('#pg-status')).to_have_attribute('data-error', 'false')
            def download(path):
                with page.expect_download() as pending:
                    page.locator('#pg-download').click()
                assert pending.value.failure() is None
                pending.value.save_as(path)
            def render():
                previous = page.locator('#pg-download').get_attribute('href')
                page.locator('#pg-render').click()
                if previous:
                    expect(page.locator('#pg-download')).not_to_have_attribute('href', previous, timeout=120000)
                ready()
            try:
                response = page.goto(origin + '/playground/', wait_until='domcontentloaded')
                assert response.status == 200
                ready()
                original = page.locator('#pg-html').input_value()
                css = page.locator('#pg-css').input_value()
                assert original == (ROOT / 'docs/assets/playground/invoice.html').read_text(encoding='utf-8')
                assert css == (ROOT / 'docs/assets/playground/invoice.css').read_text(encoding='utf-8')
                fixtures = cases(original, css)
                if args.quick:
                    fixtures = [row for row in fixtures if row['name'] in ('short', 'long')]
                for fixture in fixtures:
                    name = fixture['name']
                    folder = out / name
                    folder.mkdir()
                    page.locator('#pg-html-tab').click()
                    page.locator('#pg-html').fill(fixture['html'])
                    render()
                    (folder / 'input.html').write_text(fixture['html'], encoding='utf-8', newline='\n')
                    (folder / 'style.css').write_text(css, encoding='utf-8', newline='\n')
                    download(folder / 'document.pdf')
                    result = inspect(folder / 'document.pdf', fixture)
                    previews = []
                    for index in range(result['pages']):
                        expect(page.locator('#pg-page-count')).to_have_text(f'{index + 1} / {result["pages"]}')
                        encoded = page.locator('#pg-preview').evaluate('''async image => {
                            const bytes = new Uint8Array(await (await fetch(image.src)).arrayBuffer());
                            let text = ''; for (const byte of bytes) text += String.fromCharCode(byte); return btoa(text);
                        }''')
                        data = base64.b64decode(encoded, validate=True)
                        (folder / f'page-{index + 1}.png').write_bytes(data)
                        previews.append(sha256(data).hexdigest())
                        if index + 1 < result['pages']:
                            page.locator('#pg-next').click()
                    result['previewSha256'] = previews
                    if name in reference:
                        assert result['pdfSha256'] == reference[name]['pdfSha256']
                        assert previews == reference[name]['previewSha256']
                    if name == 'long':
                        for width, height in [(1440, 1000), (390, 844), (320, 760)]:
                            page.set_viewport_size({'width': width, 'height': height})
                            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                            page.locator('#playground').screenshot(path=str(folder / f'browser-{width}.png'))
                        page.set_viewport_size({'width': 1440, 'height': 1000})
                        render()
                        download(folder / 'repeat.pdf')
                        assert (folder / 'document.pdf').read_bytes() == (folder / 'repeat.pdf').read_bytes()
                        result['repeatPdfBytesMatch'] = True
                    if not args.skip_replay and name in ('long', 'wrapped'):
                        for language in ('python', 'node'):
                            page.locator('#pg-project-language').select_option(language)
                            with page.expect_download() as pending:
                                page.locator('#pg-project').click()
                            archive_path = folder / f'{language}.zip'
                            pending.value.save_as(archive_path)
                            project = folder / f'{language} project'
                            with zipfile.ZipFile(archive_path) as archive:
                                assert archive.testzip() is None
                                names = archive.namelist()
                                assert len(names) == len(set(names))
                                for raw in names:
                                    path = PurePosixPath(raw)
                                    assert not path.is_absolute() and '..' not in path.parts and '\\' not in raw and ':' not in raw
                                manifest = json.loads(archive.read('project.json'))
                                assert {item['path'] for item in manifest['files']} == set(names) - {'project.json'}
                                for item in manifest['files']:
                                    data = archive.read(item['path'])
                                    assert len(data) == item['bytes'] and sha256(data).hexdigest() == item['sha256']
                                assert archive.read('input.html').decode('utf-8') == fixture['html']
                                assert archive.read('style.css').decode('utf-8') == css
                                archive.extractall(project)
                            exports.append({'name': name, 'language': language, 'directory': str(project),
                                            'archiveSha256': sha256(archive_path.read_bytes()).hexdigest(),
                                            'pdfSha256': result['pdfSha256'], 'previewSha256': previews})
                        # Restore a real long project and render through the same controls.
                        if name == 'long':
                            page.locator('#pg-html').fill('<p>Temporary editor state</p>')
                            page.locator('#pg-project-file').set_input_files(str(folder / 'node.zip'))
                            expect(page.locator('#pg-project-language')).to_have_value('node')
                            expect(page.locator('#pg-html')).to_have_value(fixture['html'])
                            render()
                            download(folder / 'reopened.pdf')
                            assert (folder / 'document.pdf').read_bytes() == (folder / 'reopened.pdf').read_bytes()
                            result['savedProjectReopensIdentically'] = True
                    records.append(result)
                    print(f'{name}: {result["pages"]} pages, all text within bounds', flush=True)
                assert not errors, errors
                assert all(row['method'] == 'GET' for row in network)
                version = browser.version
            finally:
                context.close()
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    record = {'ok': False, 'at': datetime.now(timezone.utc).isoformat(), 'origin': origin,
              'browser': args.browser, 'browserVersion': version, 'cases': records, 'exports': exports,
              'errors': errors, 'nonGetRequests': 0, 'reference': str(args.reference) if args.reference else None,
              'scope': 'These synthetic invoice layouts, final PDF glyph bounds, actual browser previews, and selected saved projects. No universal layout, adoption, accessibility or conformance claim.'}
    (out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    empty = out / 'empty.npmrc'
    empty.write_text('', encoding='utf-8')
    env = {**os.environ, 'NPM_CONFIG_USERCONFIG': str(empty), 'NPM_CONFIG_CACHE': str(out / 'npm-cache'),
           'NPM_CONFIG_REGISTRY': 'https://registry.npmjs.org/'}
    def run(label, command):
        with (out / (label + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run([str(x) for x in command], cwd=out, env=env, stdout=log, stderr=subprocess.STDOUT,
                           check=True, timeout=180)
    if exports:
        record['replayNodeVersion'] = node_version
        for item in exports:
            project = Path(item['directory'])
            label = item['name'] + '-' + item['language']
            if item['language'] == 'python':
                command = [args.python, '-I', project / 'render.py']
            else:
                lock = (project / 'package-lock.json').read_bytes()
                run(label + '-install', [args.node, npm_cli, 'ci', '--prefix', project, '--ignore-scripts', '--no-audit', '--no-fund'])
                assert (project / 'package-lock.json').read_bytes() == lock
                command = [args.node, project / 'render.mjs']
            run(label + '-render', command)
            assert sha256((project / 'output/document.pdf').read_bytes()).hexdigest() == item['pdfSha256'], label
            report = json.loads((project / 'output/render.json').read_text(encoding='utf-8'))
            assert report['engine'] == json.loads((ROOT / 'docs/assets/playground/build.json').read_bytes())['engine']['version']
            assert [sha256(Path(path).read_bytes()).hexdigest() for path in report['previews']] == item['previewSha256'], label
            item['pdfAndPreviewsMatchBrowser'] = True
            (out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    record['ok'] = True
    (out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'cases': len(records), 'pages': sum(row['pages'] for row in records), 'replayedExports': len(exports)}))


if __name__ == '__main__':
    main()
