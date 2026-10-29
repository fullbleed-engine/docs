"""Use the real file picker, editor and downloads for preformatted-block regressions."""
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
from pypdf import PdfReader

from playground_preformatted_inspection import verify

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tools/playground-fixtures'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--site', type=Path)
    source.add_argument('--origin', help='Public docs origin, with any deployment prefix')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--npm-cli', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    inputs_path = FIXTURES / 'preformatted-whitespace-2.5.41.json'
    raw_inputs = inputs_path.read_bytes()
    inputs = json.loads(raw_inputs)
    reference = json.loads((FIXTURES / 'preformatted-2.5.41-reference.json').read_bytes())
    assert sha256(raw_inputs).hexdigest() == reference['inputSha256']
    font = FIXTURES / 'fonts/NotoSans-Regular.ttf'
    license_path = font.with_name('NotoSans-OFL.txt')
    assert sha256(font.read_bytes()).hexdigest() == inputs['fontSha256']
    selected = out / 'selected files'
    selected.mkdir()
    (selected / 'document.html').write_text(inputs['cases'][0]['html'], encoding='utf-8', newline='\n')
    (selected / 'style.css').write_text(inputs['cases'][0]['css'], encoding='utf-8', newline='\n')
    for path in [font, license_path]:
        (selected / path.name).write_bytes(path.read_bytes())
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

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
    origin = origin.rstrip('/')
    records, exports, network, errors = [], [], [], []
    engine_version = json.loads((ROOT / 'docs/assets/playground/build.json').read_bytes())['engine']['version']
    node_package = json.loads((ROOT / 'docs/assets/playground/project/node/package.json').read_bytes())['dependencies']['fullbleed']
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: network.append(dict(url=request.url, method=request.method)))

            def ready():
                expect(page.locator('#pg-download')).to_have_attribute('href', re.compile(r'^blob:'), timeout=120000)
                expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
                expect(page.locator('#pg-result')).to_contain_text('Fullbleed ' + engine_version)

            def render():
                previous = page.locator('#pg-download').get_attribute('href')
                page.locator('#pg-render').click()
                if previous:
                    expect(page.locator('#pg-download')).not_to_have_attribute('href', previous, timeout=120000)
                ready()

            def edit(fixture):
                page.locator('#pg-html-tab').click()
                page.locator('#pg-html').fill(fixture['html'])
                page.locator('#pg-css-tab').click()
                page.locator('#pg-css').fill(fixture['css'])
                assert page.locator('#pg-html').input_value() == fixture['html']
                assert page.locator('#pg-css').input_value() == fixture['css']

            def download_pdf(path):
                with page.expect_download() as pending:
                    page.locator('#pg-download').click()
                assert pending.value.failure() is None
                pending.value.save_as(path)

            try:
                response = page.goto(origin + '/playground/', wait_until='domcontentloaded')
                assert response.status == 200
                ready()
                response = context.request.get(origin + '/assets/playground/build.json')
                assert response.status == 200
                build = response.json()
                assert build['engine']['version'] == engine_version
                (out / 'build.json').write_text(json.dumps(build, indent=2) + '\n', encoding='utf-8')
                with page.expect_file_chooser() as chooser:
                    page.locator('#pg-open-files').click()
                chooser.value.set_files([str(selected / name) for name in ['document.html', 'style.css', font.name, license_path.name]])
                expect(page.locator('#pg-open-files')).to_be_enabled()
                expect(page.locator('#pg-example')).to_have_value('custom')
                expect(page.locator('#pg-assets')).to_contain_text(font.name)
                for fixture in inputs['cases']:
                    name = fixture['name']
                    folder = out / ('browser-' + name)
                    folder.mkdir()
                    edit(fixture)
                    (folder / 'input.html').write_text(fixture['html'], encoding='utf-8', newline='\n')
                    (folder / 'style.css').write_text(fixture['css'], encoding='utf-8', newline='\n')
                    render()
                    download_pdf(folder / 'document.pdf')
                    pages = len(PdfReader(folder / 'document.pdf', strict=True).pages)
                    assert pages == reference['pages'][name]
                    preview_files, preview_hashes = [], []
                    for index in range(pages):
                        expect(page.locator('#pg-page-count')).to_have_text(f'{index + 1} / {pages}')
                        # Read the visible preview blob; rendering and navigation use the real controls.
                        encoded = page.locator('#pg-preview').evaluate('''async image => {
                            const bytes = new Uint8Array(await (await fetch(image.src)).arrayBuffer());
                            let text = ''; for (const byte of bytes) text += String.fromCharCode(byte); return btoa(text);
                        }''')
                        data = base64.b64decode(encoded, validate=True)
                        filename = f'native-{index + 1}.png'
                        (folder / filename).write_bytes(data)
                        preview_files.append(filename)
                        preview_hashes.append(sha256(data).hexdigest())
                        if name in ['wrap-anywhere', 'whitespace-pre-line', 'no-wrap-pre'] and index in [0, pages - 1]:
                            page.screenshot(path=str(folder / f'browser-page-{index + 1}.png'), animations='disabled')
                        if index + 1 < pages:
                            page.locator('#pg-next').click()
                    render()
                    download_pdf(folder / 'repeat.pdf')
                    assert (folder / 'document.pdf').read_bytes() == (folder / 'repeat.pdf').read_bytes()
                    records.append(dict(mode='browser', name=name, directory=folder.name, pages=pages,
                        pdfSha256=sha256((folder / 'document.pdf').read_bytes()).hexdigest(),
                        repeatPdfBytesMatch=True, previewFiles=preview_files, previewSha256=preview_hashes))
                    if name in ['wrap-anywhere', 'whitespace-pre-line', 'no-wrap-pre']:
                        for language in ['python', 'node']:
                            page.locator('#pg-project-language').select_option(language)
                            with page.expect_download() as pending:
                                page.locator('#pg-project').click()
                            assert pending.value.failure() is None
                            archive_path = folder / (language + '.zip')
                            pending.value.save_as(archive_path)
                            destination = folder / (language + ' project')
                            destination.mkdir()
                            with zipfile.ZipFile(archive_path) as archive:
                                assert archive.testzip() is None
                                names = archive.namelist()
                                assert len(names) == len(set(names))
                                for name_in_zip in names:
                                    path = PurePosixPath(name_in_zip)
                                    assert not path.is_absolute() and '..' not in path.parts and '\\' not in name_in_zip and ':' not in name_in_zip
                                    assert (destination / name_in_zip).resolve().is_relative_to(destination)
                                archive.extractall(destination)
                            manifest = json.loads((destination / 'project.json').read_bytes())
                            assert {item['path'] for item in manifest['files']} == set(names) - {'project.json'}
                            assert manifest['engine']['version'] == engine_version
                            assert (destination / 'input.html').read_bytes() == fixture['html'].encode()
                            assert (destination / 'style.css').read_bytes() == fixture['css'].encode()
                            for path in [font, license_path]:
                                assert (destination / 'assets' / path.name).read_bytes() == path.read_bytes()
                            for item in manifest['files']:
                                data = (destination / item['path']).read_bytes()
                                assert sha256(data).hexdigest() == item['sha256'] and len(data) == item['bytes']
                            if language == 'python':
                                assert (destination / 'requirements.txt').read_text() == f'fullbleed=={engine_version}\n'
                            else:
                                assert manifest['runtime']['package']['version'] == node_package
                            exports.append(dict(case=name, language=language, directory=destination.relative_to(out).as_posix(),
                                zipSha256=sha256(archive_path.read_bytes()).hexdigest(), sourceAndAssetsMatch=True))
                    print(json.dumps(dict(case=name, pages=pages, repeatedPdfMatches=True)), flush=True)
                edit(inputs['cases'][0])
                render()
                for width in [390, 320]:
                    page.set_viewport_size({'width': width, 'height': 900})
                    page.locator('#playground').scroll_into_view_if_needed()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    page.screenshot(path=str(out / f'mobile-{width}.png'), full_page=True, animations='disabled')
                assert not errors, errors
                assert all(request['method'] == 'GET' for request in network), 'Unexpected non-GET traffic'
                browser_version = browser.version
            finally:
                context.close()
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    renders = dict(packageVersion='playground-' + engine_version, engineVersion=engine_version,
        inputSha256=sha256(raw_inputs).hexdigest(), fontSha256=inputs['fontSha256'], cases=records)
    (out / 'renders.json').write_text(json.dumps(renders, indent=2) + '\n', encoding='utf-8')
    browser_record = dict(at=datetime.now(timezone.utc).isoformat(), origin=origin, browser=browser_version,
        errors=errors, network=network, exports=exports,
        scope='Fresh anonymous headless Chromium; actual file picker, editor, PDF/project downloads and visible previews. No authenticated tabs used.')
    (out / 'browser.json').write_text(json.dumps(browser_record, indent=2) + '\n', encoding='utf-8')
    result = verify(out, inputs_path, ['browser'], require_previews=True, preview_size=(240, 160))

    def run(label, command):
        process = subprocess.run(list(map(str, command)), cwd=out, capture_output=True,
            text=True, encoding='utf-8', timeout=180)
        (out / (label + '.log')).write_text(process.stdout + process.stderr, encoding='utf-8')
        assert process.returncode == 0, label + ': ' + process.stderr[-3000:]

    npm_cli = args.npm_cli
    if npm_cli is None:
        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
        assert npm
        npm_cli = Path(npm).resolve().parent / 'node_modules/npm/bin/npm-cli.js'
        if not npm_cli.is_file():
            npm_cli = Path(npm).resolve().parent / 'npm-cli.js'
    assert args.node and npm_cli.is_file()
    run('python-version', [args.python, '-I', '-c', f'import importlib.metadata; assert importlib.metadata.version("fullbleed") == "{engine_version}"'])
    for item in exports:
        project = out / item['directory']
        label = item['case'] + '-' + item['language']
        if item['language'] == 'python':
            command = [args.python, '-I', project / 'render.py']
        else:
            lock = (project / 'package-lock.json').read_bytes()
            run(label + '-install', [args.node, npm_cli, 'ci', '--prefix', project, '--ignore-scripts', '--no-audit', '--no-fund'])
            assert (project / 'package-lock.json').read_bytes() == lock
            command = [args.node, project / 'render.mjs']
        run(label + '-render', command)
        folder = project.parent
        rendered = json.loads((project / 'output/render.json').read_bytes())
        assert rendered['pages'] == reference['pages'][item['case']]
        assert (project / 'output/document.pdf').read_bytes() == (folder / 'document.pdf').read_bytes()
        assert len(rendered['previews']) == rendered['pages']
        for number, preview in enumerate(rendered['previews'], 1):
            assert Path(preview).read_bytes() == (folder / f'native-{number}.png').read_bytes()
        item.update(replayed=True, pdfAndPreviewsMatchBrowser=True)
    browser_record['exports'] = exports
    browser_record['ok'] = result['ok'] and len(exports) == 6
    (out / 'browser.json').write_text(json.dumps(browser_record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(ok=browser_record['ok'], cases=len(records), pages=sum(row['pages'] for row in records), replayedExports=len(exports))), flush=True)


if __name__ == '__main__':
    main()
