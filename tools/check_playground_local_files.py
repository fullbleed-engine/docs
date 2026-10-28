"""Import real local files, download PDFs/ZIPs, and replay both project languages."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import threading
from urllib.parse import unquote, urlsplit
import zipfile

from PIL import Image
from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader
import pypdfium2 as pdfium

from playground_local_files import fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--site', type=Path)
    source.add_argument('--url')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--python', default=sys.executable)
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--npm-cli', type=Path)
    parser.add_argument('--browser-executable', type=Path, help='Optional Chrome executable for an isolated local reproduction')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    specimen = fixture(out / 'selected files')
    selected = out / 'selected files'
    checks, requests, errors, exports, console = [], [], [], [], []
    server = None
    url = args.url
    if args.site:
        root = args.site.resolve()

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(root), **kw)

            def end_headers(self):
                self.send_header('Cache-Control', 'no-store')
                super().end_headers()

            def log_message(self, *a):
                pass

            def copyfile(self, source, outputfile):
                try:
                    super().copyfile(source, outputfile)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}/playground/'

    def check(name, passed):
        assert passed, name
        checks.append(name)
        print(name + ': passed', flush=True)

    def run(label, command, cwd):
        process = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True,
                                 text=True, encoding='utf-8', timeout=120)
        (out / (label + '.log')).write_text(process.stdout + process.stderr, encoding='utf-8')
        assert process.returncode == 0, label + ': ' + process.stderr[-3000:]

    def inspect_pdf(path):
        reader = PdfReader(path)
        check(path.stem + ': one PDF page with imported text', len(reader.pages) == 1
              and 'LOCAL IMPORT CAFÉ 012345' in reader.pages[0].extract_text())
        fonts = [font.get_object() for font in reader.pages[0]['/Resources']['/Font'].values()]
        names = [str(font.get('/BaseFont', '')) for font in fonts]
        check(path.stem + ': the selected font is embedded', any('IBMPlexMono' in name for name in names)
              and all('/FontFile2' in font['/DescendantFonts'][0].get_object()['/FontDescriptor'].get_object()
                      for font in fonts if 'IBMPlexMono' in str(font.get('/BaseFont', ''))))
        with pdfium.PdfDocument(path) as pdf:
            page = pdf[0]
            image = page.render(scale=96 / 72).to_pil().convert('RGB')
            image.save(path.with_suffix('.pdfium.png'))
            colors = list(image.get_flattened_data())
            for name, rgb in [('PNG', (17, 153, 136)), ('JPEG', (222, 144, 22)), ('SVG', (53, 89, 187))]:
                count = sum(all(abs(a - b) <= 3 for a, b in zip(pixel, rgb)) for pixel in colors)
                check(path.stem + ': imported ' + name + ' is visible in independent PDF rendering', count > 2000)
            page.close()
        return dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(), fonts=names)

    try:
        with sync_playwright() as pw:
            browser = (pw.chromium.launch(executable_path=str(args.browser_executable))
                       if args.browser_executable else pw.chromium.launch(channel='chrome'))
            browser_version = browser.version
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: console.append(dict(type=message.type, text=message.text)))
            page.on('request', lambda request: requests.append(dict(url=request.url, method=request.method, body=request.post_data)))
            # Observe activation without injecting a user gesture or changing handlers.
            page.add_init_script('''(() => {
              window.__localFilePickerEvents = [];
              for (const type of ['focusin', 'keydown', 'keyup', 'click']) {
                document.addEventListener(type, event => {
                  if (!['pg-open-files', 'pg-files'].includes(event.target.id)) return;
                  const record = {type, key: event.key, target: event.target.id,
                    trusted: event.isTrusted, active: document.activeElement.id,
                    activation: navigator.userActivation.isActive};
                  window.__localFilePickerEvents.push(record);
                  queueMicrotask(() => { record.prevented = event.defaultPrevented; });
                }, true);
              }
            })();''')

            def ready():
                expect(page.locator('#pg-download')).to_have_attribute('href', re.compile(r'^blob:'), timeout=120000)
                expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')

            def open_files(paths):
                page.locator('#pg-files').set_input_files([str(path) for path in paths])
                expect(page.locator('#pg-open-files')).to_be_enabled()

            try:
                print('Opening the playground in an isolated browser context', flush=True)
                page.goto(url, wait_until='domcontentloaded')
                ready()
                print('Initial example is ready', flush=True)
                invoice = page.locator('#pg-html').input_value() + '\n<!-- retained invoice edit -->'
                page.locator('#pg-html').fill(invoice)
                # Each activation must open the actual chooser; no retry or direct-input fallback.
                button = page.locator('#pg-open-files')
                expect(button).to_be_enabled()
                expect(button).to_be_visible()
                for key in ['Enter', 'Space']:
                    button.focus()
                    expect(button).to_be_focused()
                    with page.expect_file_chooser() as chooser:
                        button.press(key)
                    chooser.value.set_files([])
                    check(key + ' opens the local-file chooser from the focused button', True)
                with page.expect_file_chooser() as chooser:
                    button.click()
                chooser.value.set_files([str(selected / 'document.html'), str(selected / 'brand.css')]
                                        + [str(selected / 'assets' / asset['name']) for asset in specimen['assets']])
                check('Click opens the local-file chooser and accepts the selected files', True)
                expect(page.locator('#pg-open-files')).to_be_enabled()
                expect(page.locator('#pg-example')).to_have_value('custom')
                expect(page.locator('#pg-asset-count')).to_have_text('5 local assets')
                check('Import preserves UTF-8 source and exposes exact asset paths',
                      page.locator('#pg-html').input_value() == specimen['html']
                      and page.locator('#pg-css').input_value() == specimen['css']
                      and all('assets/' + asset['name'] in page.locator('#pg-assets').inner_text() for asset in specimen['assets']))
                expect(page.locator('#pg-download')).to_have_attribute('aria-disabled', 'true')
                page.locator('#pg-render').click()
                ready()
                check('Document scripts do not execute in the host page', page.evaluate('window.__localDocumentExecuted === undefined'))
                with page.expect_download() as download:
                    page.locator('#pg-download').click()
                pdf = out / 'browser.pdf'
                download.value.save_as(pdf)
                pdf_record = inspect_pdf(pdf)
                encoded = page.locator('#pg-preview').evaluate('''async image => {
                    const bytes = new Uint8Array(await (await fetch(image.src)).arrayBuffer());
                    let text = ''; for (const byte of bytes) text += String.fromCharCode(byte); return btoa(text);
                }''')
                preview = base64.b64decode(encoded)
                (out / 'browser.png').write_bytes(preview)

                for language in ['python', 'node']:
                    page.locator('#pg-project-language').select_option(language)
                    with page.expect_download() as download:
                        page.locator('#pg-project').click()
                    archive_path = out / (language + '.zip')
                    download.value.save_as(archive_path)
                    project = out / ('extracted ' + language + ' project with spaces')
                    with zipfile.ZipFile(archive_path) as archive:
                        assert archive.testzip() is None
                        assert len(archive.namelist()) == len(set(archive.namelist()))
                        assert all(not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
                                   and '\\' not in name and ':' not in name for name in archive.namelist())
                        archive.extractall(project)
                    manifest = json.loads((project / 'project.json').read_text(encoding='utf-8'))
                    check(language + ': download preserves selected source and asset bytes',
                          (project / 'input.html').read_bytes() == specimen['html'].encode()
                          and (project / 'style.css').read_bytes() == specimen['css'].encode()
                          and all((project / 'assets' / a['name']).read_bytes() == (selected / 'assets' / a['name']).read_bytes()
                                  for a in specimen['assets']))
                    check(language + ': all manifest hashes and selected font roles match',
                          all(hashlib.sha256((project / item['path']).read_bytes()).hexdigest() == item['sha256']
                              and (project / item['path']).stat().st_size == item['bytes'] for item in manifest['files'])
                          and manifest['localAssets'] == [dict(path='assets/' + a['name'], font=a['name'].endswith('.ttf'))
                                                        for a in specimen['assets']])
                    if language == 'python':
                        run('python-render', [args.python, '-I', project / 'render.py'], out)
                    else:
                        npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
                        npm_cli = args.npm_cli or Path(npm).resolve().parent / 'node_modules/npm/bin/npm-cli.js'
                        if not npm_cli.is_file():
                            npm_cli = Path(npm).resolve().parent / 'npm-cli.js'
                        assert npm_cli.is_file() and args.node
                        run('node-install', [args.node, npm_cli, 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], project)
                        run('node-render', [args.node, project / 'render.mjs'], out)
                    report = json.loads((project / 'output/render.json').read_text(encoding='utf-8'))
                    check(language + ': PDF replay from another working directory is byte-identical',
                          (project / 'output/document.pdf').read_bytes() == pdf.read_bytes())
                    check(language + ': finalized-PDF preview replay is byte-identical',
                          len(report['previews']) == 1 and Path(report['previews'][0]).read_bytes() == preview)
                    exports.append(dict(language=language, zipSha256=hashlib.sha256(archive_path.read_bytes()).hexdigest(),
                                        pdfSha256=report['sha256'], assets=len(specimen['assets'])))

                for width in [1440, 390, 320]:
                    page.set_viewport_size({'width': width, 'height': 1000})
                    page.evaluate('window.scrollTo(0, 0)')
                    check(str(width) + 'px: imported asset list does not overflow',
                          page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    page.screenshot(path=str(out / f'viewport-{width}.png'), full_page=True)
                page.set_viewport_size({'width': 1440, 'height': 1000})
                # Duplicate, unsafe and invalid selections must leave a working document intact.
                for payload in [[{'name': 'café mark.png', 'mimeType': 'image/png', 'buffer': (selected / 'assets/café mark.png').read_bytes()}],
                                [{'name': 'bad.png', 'mimeType': 'image/png', 'buffer': b'not an image'}],
                                [{'name': 'bad.html', 'mimeType': 'text/html', 'buffer': b'\xff'}],
                                [{'name': 'new.html', 'mimeType': 'text/html', 'buffer': b'<h1>Do not apply</h1>'},
                                 {'name': 'bad.ttf', 'mimeType': 'font/ttf', 'buffer': b'bad'}]]:
                    page.locator('#pg-files').set_input_files(payload)
                    expect(page.locator('#pg-status')).to_have_attribute('data-error', 'true')
                    check('Invalid import preserves the previous source, assets and PDF',
                          page.locator('#pg-html').input_value() == specimen['html']
                          and page.locator('#pg-css').input_value() == specimen['css']
                          and page.locator('#pg-asset-count').inner_text() == '5 local assets'
                          and page.locator('#pg-download').get_attribute('aria-disabled') == 'false')
                page.locator('#pg-example').select_option('invoice')
                ready()
                check('Switching examples preserves earlier edits and selected assets',
                      page.locator('#pg-html').input_value() == invoice and page.locator('#pg-assets li').count() == 5)
                page.locator('#pg-example').select_option('custom')
                ready()
                check('Custom source remains available after switching examples', page.locator('#pg-html').input_value() == specimen['html'])
                page.get_by_role('button', name='Remove café mark.png', exact=True).click()
                expect(page.locator('#pg-download')).to_have_attribute('aria-disabled', 'true')
                check('Removing an asset invalidates the old PDF and restores keyboard focus',
                      page.locator('#pg-assets li').count() == 4 and page.locator('#pg-open-files').evaluate('button => button === document.activeElement'))
                open_files([selected / 'assets/café mark.png'])
                page.locator('#pg-render').click()
                ready()
                check('A removed asset can be re-added and rendered', page.locator('#pg-assets li').count() == 5)
                page.locator('#pg-files').set_input_files({'name': 'corrupt.ttf', 'mimeType': 'font/ttf', 'buffer': b'\x00\x01\x00\x00not a font'})
                expect(page.locator('#pg-status')).to_contain_text('Files opened locally.')
                page.locator('#pg-render').click()
                expect(page.locator('#pg-status')).to_have_attribute('data-error', 'true', timeout=60000)
                check('A corrupt font with a plausible header fails rendering instead of silently falling back',
                      page.locator('#pg-download').get_attribute('aria-disabled') == 'true')
                page.get_by_role('button', name='Remove corrupt.ttf', exact=True).click()
                page.locator('#pg-render').click()
                ready()
                page.locator('#pg-files').set_input_files({'name': 'replacement.css', 'mimeType': 'text/css', 'buffer': b'body { color: navy }'})
                expect(page.locator('#pg-status')).to_contain_text('Files opened locally.')
                check('CSS-only import preserves HTML', page.locator('#pg-html').input_value() == specimen['html']
                      and page.locator('#pg-css').input_value() == 'body { color: navy }')
                page.locator('#pg-files').set_input_files({'name': 'empty.html', 'mimeType': 'text/html', 'buffer': b'<p>New document</p>'})
                expect(page.locator('#pg-status')).to_contain_text('Files opened locally.')
                check('HTML-only import clears the previous separate CSS', page.locator('#pg-html').input_value() == '<p>New document</p>'
                      and page.locator('#pg-css').input_value() == '')
                check('Local inputs are not uploaded or fetched as network assets',
                      all(request['method'] == 'GET' and request['body'] is None for request in requests)
                      and not any(any(a['name'] == unquote(urlsplit(request['url']).path).rsplit('/', 1)[-1]
                                      for a in specimen['assets']) for request in requests))
                check('Browser reports no uncaught JavaScript errors', not errors)
            finally:
                try:
                    page.screenshot(path=str(out / 'final-browser-state.png'), full_page=True, timeout=10000)
                    (out / 'final-browser-state.json').write_text(json.dumps(dict(url=page.url,
                        browser=browser_version, platform=platform.platform(),
                        status=page.locator('#pg-status').text_content(timeout=5000),
                        picker=page.evaluate('''() => ({events: window.__localFilePickerEvents,
                            active: document.activeElement.id,
                            disabled: document.querySelector('#pg-open-files').disabled})''')),
                        indent=2) + '\n', encoding='utf-8')
                except Exception as error:
                    (out / 'state-capture-error.txt').write_text(str(error), encoding='utf-8')
                (out / 'network.json').write_text(json.dumps(requests, indent=2) + '\n', encoding='utf-8')
                (out / 'browser-errors.json').write_text(json.dumps(errors, indent=2) + '\n', encoding='utf-8')
                (out / 'console.json').write_text(json.dumps(console, indent=2) + '\n', encoding='utf-8')
                context.close()
                browser.close()
        result = dict(ok=True, checkedAt=datetime.now(timezone.utc).isoformat(), url=url,
                      browser=browser_version, platform=platform.platform(),
                      source_revision=os.environ.get('GITHUB_SHA'), ci_run_id=os.environ.get('GITHUB_RUN_ID'),
                      checks=checks, pdf=pdf_record, exports=exports,
                      scope='This selected-file specimen and its two project downloads; no universal parity or conformance claim.')
        (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(dict(ok=True, checks=len(checks), exports=len(exports))))
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
