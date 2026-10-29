"""Verify actionable loading failures and same-page recovery with real edited PDFs and assets."""
import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from threading import Lock, Thread
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader

from playground_local_files import fixture

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--site', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
args = parser.parse_args()
root, out = args.site.resolve(), args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
specimen = fixture(out / 'selected files')
selected = out / 'selected files'
html = specimen['html'].replace('LOCAL IMPORT CAFÉ 012345', 'RETRY CAFÉ 012345')
css = specimen['css'] + '\n.marker { color: #175c52; }\n'
prefix = '/nested/docs/'
active_failure = None
failures = []
lock = Lock()
report = dict(ok=False, at=datetime.now(timezone.utc).isoformat(), cases=[], pageErrors=[],
              sourceSha256={name: sha256((root / 'assets/playground' / name).read_bytes()).hexdigest() for name in ('app.js', 'worker.js')})

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(root), **kw)
    def translate_path(self, path):
        name = unquote(urlsplit(path).path)
        if not name.startswith(prefix):
            return str(root / 'not-found')
        resolved = (root / name[len(prefix):]).resolve()
        return str(resolved if resolved.is_relative_to(root) else root / 'not-found')
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()
    def do_GET(self):
        path = urlsplit(self.path).path
        with lock:
            fail = active_failure is not None and path == prefix + 'assets/playground/' + active_failure
            if fail:
                failures.append(dict(path=path, status=503))
        if fail:
            self.send_error(503, 'Controlled recovery test failure')
        else:
            super().do_GET()
    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
    def log_message(self, *_):
        pass

server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda error: report['pageErrors'].append(str(error)))
        def ready():
            expect(page.locator('#pg-download')).to_have_attribute('href', re.compile('^blob:'), timeout=120000)
            expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
        def enter_source(include_assets=False):
            paths = [selected / 'document.html', selected / 'brand.css']
            if include_assets:
                paths += [selected / 'assets' / asset['name'] for asset in specimen['assets']]
            page.locator('#pg-files').set_input_files(list(map(str, paths)))
            expect(page.locator('#pg-open-files')).to_be_enabled()
            expect(page.locator('#pg-example')).to_have_value('custom')
            page.locator('#pg-html-tab').click()
            page.locator('#pg-html').fill(html)
            page.locator('#pg-css-tab').click()
            page.locator('#pg-css').fill(css)
            expect(page.locator('#pg-asset-count')).to_have_text('5 local assets')
        def download(name):
            with page.expect_download() as pending:
                page.locator('#pg-download').click()
            pending.value.save_as(out / (name + '.pdf'))
            raw = (out / (name + '.pdf')).read_bytes()
            encoded = page.locator('#pg-preview').evaluate('''async image => {
                const bytes = new Uint8Array(await (await fetch(image.src)).arrayBuffer());
                let text = ''; for (const byte of bytes) text += String.fromCharCode(byte); return btoa(text);
            }''')
            preview = base64.b64decode(encoded)
            (out / (name + '.png')).write_bytes(preview)
            return raw, preview
        def unchanged():
            return page.locator('#pg-html').input_value() == html and page.locator('#pg-css').input_value() == css and page.locator('#pg-assets li').count() == 5
        try:
            page.goto(f'http://127.0.0.1:{server.server_port}{prefix}playground/', wait_until='domcontentloaded')
            ready()
            enter_source(include_assets=True)
            page.locator('#pg-render').click()
            ready()
            baseline_pdf, baseline_png = download('baseline')
            document = PdfReader(out / 'baseline.pdf')
            assert len(document.pages) == 1 and 'RETRY CAFÉ 012345' in document.pages[0].extract_text()
            report['baseline'] = dict(pdfSha256=sha256(baseline_pdf).hexdigest(), previewSha256=sha256(baseline_png).hexdigest())
            for name, asset in [('worker-entry', 'worker.js'), ('renderer-module', 'renderer.js'), ('engine', 'fullbleed.wasm'), ('bundled-font', 'fonts/Inter-Variable.ttf')]:
                enter_source()
                assert unchanged()
                with lock:
                    before = len(failures)
                    active_failure = asset
                page.locator('#pg-render').click()
                expect(page.locator('#pg-status')).to_have_attribute('data-error', 'true', timeout=30000)
                expect(page.locator('#pg-render')).to_be_enabled()
                expect(page.locator('#pg-download')).to_have_attribute('aria-disabled', 'true')
                expect(page.locator('#pg-cancel')).to_be_hidden()
                assert page.locator('.pg-output').get_attribute('aria-busy') == 'false' and unchanged()
                failure_state = dict(name=name, asset=asset, sourceAndAssetListPreserved=True,
                    status=page.locator('#pg-status').inner_text(), placeholder=page.locator('#pg-placeholder').inner_text())
                failure_state['guidance'] = dict(
                    renderActionNamed='Render PDF' in failure_state['status'],
                    noReloadInstruction='reload' not in failure_state['status'].lower(),
                    noSourceBlame='adjust your source' not in failure_state['placeholder'].lower(),
                    noInternalUrl=not re.search(r'https?://', failure_state['status']))
                failure_state['viewports'] = []
                for width in (1440, 390):
                    page.set_viewport_size({'width': width, 'height': 1000})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                    page.screenshot(path=str(out / f'{name}-{width}-failure.png'), full_page=True, animations='disabled')
                    failure_state['viewports'].append(dict(width=width, fits=True))
                page.set_viewport_size({'width': 1440, 'height': 1000})
                with lock:
                    failure_state['failedRequests'] = failures[before:]
                    assert failure_state['failedRequests']
                    active_failure = None
                page.locator('#pg-render').click()
                ready()
                pdf, png = download(name + '-recovered')
                assert unchanged() and pdf == baseline_pdf and png == baseline_png
                failure_state.update(recoveredWithoutNavigation=True, exactPdfAndPreview=True)
                report['cases'].append(failure_state)
                print(json.dumps(failure_state), flush=True)
            page.locator('#pg-project-language').select_option('python')
            with page.expect_download() as pending:
                page.locator('#pg-project').click()
            pending.value.save_as(out / 'recovered-project.zip')
            with ZipFile(out / 'recovered-project.zip') as zipped:
                assert zipped.testzip() is None and len(zipped.namelist()) == len(set(zipped.namelist()))
                manifest = json.loads(zipped.read('project.json'))
                assert zipped.read('input.html') == html.encode() and zipped.read('style.css') == css.encode()
                assert all(zipped.read('assets/' + a['name']) == (selected / 'assets' / a['name']).read_bytes() for a in specimen['assets'])
                assert all(sha256(zipped.read(item['path'])).hexdigest() == item['sha256'] for item in manifest['files'])
            report.update(projectSourceAndAssetsPreserved=True, projectSha256=sha256((out / 'recovered-project.zip').read_bytes()).hexdigest())
            assert all(all(row['guidance'].values()) for row in report['cases']), 'Loading failures need an actionable retry without source blame or internal URLs.'
            assert not report['pageErrors'], report['pageErrors']
            report['ok'] = True
        except BaseException as error:
            report['error'] = str(error)
            page.screenshot(path=str(out / 'unexpected-failure.png'), full_page=True)
            raise
        finally:
            (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            context.close()
            browser.close()
finally:
    server.shutdown()
    server.server_close()
print(json.dumps(dict(ok=report['ok'], recoveryCases=len(report['cases']), projectSourceAndAssetsPreserved=report.get('projectSourceAndAssetsPreserved'))), flush=True)
