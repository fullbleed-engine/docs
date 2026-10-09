"""Exercise the built homepage playground with real PDFs and project downloads."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
import json
from pathlib import Path
import re
import threading
from urllib.parse import unquote, urlsplit
import zipfile

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader
from starter_engine_fixes import verify_engine_fixes


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--site', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--browser', choices=['chrome', 'firefox', 'webkit'], default='chrome')
args = parser.parse_args()
root = args.site.resolve()
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
manifest = json.loads((root / 'assets/playground/build.json').read_text(encoding='utf-8'))
reference = json.loads((root / 'assets/playground/verification.json').read_text(encoding='utf-8'))
prefix = '/nested/docs/'
checks, network, errors, documents = [], [], [], []
paused, requested, released = threading.Event(), threading.Event(), threading.Event()


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
        if paused.is_set() and urlsplit(self.path).path.endswith('/playground/fullbleed.wasm'):
            requested.set()
            released.wait(15)
        super().do_GET()

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, *a):
        pass


def check(name, passed):
    assert passed, name
    checks.append(name)
    print(name + ': passed', flush=True)


server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f'http://127.0.0.1:{server.server_port}{prefix}'
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome') if args.browser == 'chrome' else getattr(pw, args.browser).launch()
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: network.append({'url': request.url, 'method': request.method, 'body': request.post_data}))

        def ready():
            expect(page.locator('#pg-download')).to_have_attribute('href', re.compile(r'^blob:'), timeout=120000)
            expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
            expect(page.locator('#pg-result')).to_contain_text('Fullbleed ' + manifest['engine']['version'])

        def edit(html, css):
            page.locator('#pg-html-tab').click()
            page.locator('#pg-html').fill(html)
            page.locator('#pg-css-tab').click()
            page.locator('#pg-css').fill(css)

        def download(name, pages):
            with page.expect_download() as event:
                page.locator('#pg-download').click()
            path = out / (name + '.pdf')
            event.value.save_as(path)
            check(name + ': actual downloaded PDF has the required pages', len(PdfReader(path).pages) == pages)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            documents.append({'name': name, 'pages': pages, 'sha256': digest, 'filename': event.value.suggested_filename})
            return path, digest

        try:
            page.goto(url + 'playground/', wait_until='domcontentloaded')
            ready()
            check('playground uses the current published engine with SVG rendering',
                  manifest['engine']['version'] == '2.5.22' and manifest['engine']['features'] == ['svg_raster'])
            check('playground retains its bounded runtime', manifest['limits'] ==
                  {'source_bytes': 200000, 'pages': 6, 'wasm_memory_bytes': 268435456, 'render_seconds': 30})
            for name, pages in [('invoice', 1), ('report', 3), ('notice', 1)]:
                if name != 'invoice':
                    page.locator('#pg-example').select_option(name)
                    ready()
                _, digest = download(name, pages)
                expected = next(item for item in reference['fixtures'] if item['name'] == name)
                check(name + ': browser download matches native/WASI verification', digest == expected['hashes']['output.pdf'])
                expect(page.locator('#pg-page-count')).to_have_text(f'1 / {pages}')
                if pages > 1:
                    first = page.locator('#pg-preview').get_attribute('src')
                    page.locator('#pg-next').click()
                    expect(page.locator('#pg-page-count')).to_have_text('2 / 3')
                    check('report pagination displays a different PDF page', page.locator('#pg-preview').get_attribute('src') != first)
                    page.locator('#pg-previous').click()
                    expect(page.locator('#pg-page-count')).to_have_text('1 / 3')
            page.locator('#pg-example').select_option('invoice')
            ready()
            for width, height in [(1440, 1000), (390, 844), (320, 760)]:
                page.set_viewport_size({'width': width, 'height': height})
                check(f'{width}px: page fits the viewport', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                page.screenshot(path=str(out / f'width-{width}.png'), full_page=True)
            page.set_viewport_size({'width': 1440, 'height': 1000})
            verify_engine_fixes(page, out, check, ready, manual=True,
                                html_selector='#pg-html', css_selector='#pg-css',
                                render_selector='#pg-render', download_selector='#pg-download',
                                preview_selector='#pg-preview', edit_sources=edit)
            html = page.locator('#pg-html').input_value().replace('Maple &amp; Finch', 'Cedar &amp; Stone')
            html = html.replace('</head>', '<script>window.documentScriptExecuted = true;</script></head>')
            css = page.locator('#pg-css').input_value().replace('#17382e', '#17315a')
            edit(html, css)
            check('edited source disables the previous PDF download', page.locator('#pg-download').get_attribute('href') is None)
            page.locator('#pg-render').click()
            ready()
            edited, _ = download('edited-invoice', 1)
            check('pasted HTML changes the downloaded text', 'Cedar & Stone' in PdfReader(edited).pages[0].extract_text())
            check('document JavaScript is not executed in the page', page.evaluate('window.documentScriptExecuted !== true'))
            with page.expect_download() as event:
                page.locator('#pg-project').click()
            project = out / 'edited-project.zip'
            event.value.save_as(project)
            with zipfile.ZipFile(project) as archive:
                check('downloaded project has a valid ZIP CRC and unique paths', archive.testzip() is None and len(archive.namelist()) == len(set(archive.namelist())))
                check('project download preserves the actual HTML and CSS edits', archive.read('input.html').decode('utf-8') == html and archive.read('style.css').decode('utf-8') == css)
                check('project pins the engine used in the browser', archive.read('requirements.txt').decode('utf-8') == 'fullbleed==2.5.22\n')
                record = json.loads(archive.read('project.json'))
                check('project manifest verifies each exported source, font and license',
                      all(hashlib.sha256(archive.read(item['path'])).hexdigest() == item['sha256']
                          and len(archive.read(item['path'])) == item['bytes'] for item in record['files']))
            page.screenshot(path=str(out / 'edited-template.png'), full_page=True)
            edit('x' * 200001, '')
            page.locator('#pg-render').click()
            expect(page.locator('#pg-status')).to_contain_text('200 KB')
            check('oversized source leaves no stale download', page.locator('#pg-download').get_attribute('href') is None)
            edit('<div>Page</div>' * 7, '@page{size:A4}div{break-after:page}')
            page.locator('#pg-render').click()
            expect(page.locator('#pg-status')).to_contain_text('1 to 6 pages', timeout=45000)
            check('page limit failure leaves the editor usable', page.locator('#pg-render').is_enabled() and page.locator('#pg-download').get_attribute('href') is None)
            edit(html, css)
            paused.set()
            page.locator('#pg-render').click()
            assert requested.wait(8), 'Expected a held engine request before cancellation.'
            page.locator('#pg-cancel').click()
            expect(page.locator('#pg-status')).to_contain_text('canceled')
            check('cancellation preserves source and restores controls', page.locator('#pg-html').input_value() == html and page.locator('#pg-render').is_enabled())
            paused.clear()
            released.set()
            page.locator('#pg-render').click()
            ready()
            recovered, _ = download('recovered', 1)
            check('rendering recovers after source/page errors and cancellation', recovered.read_bytes() == edited.read_bytes())
            blob_origin = f'blob:http://127.0.0.1:{server.server_port}/'
            # The shared docs header fetches these two fixed public GitHub URLs.
            # Neither endpoint accepts the editor source or any variable query.
            header_metadata = {'https://api.github.com/repos/fullbleed-engine/fullbleed-official',
                               'https://api.github.com/repos/fullbleed-engine/fullbleed-official/releases/latest'}
            check('document requests stay local; only fixed header metadata queries leave the site',
                  all(item['method'] == 'GET' and not item['body'] and
                      (item['url'].startswith((url, blob_origin)) or item['url'] in header_metadata)
                      for item in network))
            check('no uncaught page errors', not errors)
            result = {'ok': True, 'checkedAt': datetime.now(timezone.utc).isoformat(),
                      'browser': browser.version, 'browserEngine': args.browser, 'playwright': version('playwright'),
                      'engine': manifest['engine'], 'checks': checks, 'documents': documents,
                      'projectSha256': hashlib.sha256(project.read_bytes()).hexdigest(), 'network': network, 'errors': errors,
                      'scope': 'Owned browser, synthetic source, real built page at a nested path; downloaded PDFs and project ZIP.'}
            (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
        except Exception:
            page.screenshot(path=str(out / 'failure.png'), full_page=True)
            (out / 'failure.json').write_text(json.dumps({'checks': checks, 'network': network, 'errors': errors}, indent=2) + '\n', encoding='utf-8')
            raise
        finally:
            context.close()
            browser.close()
finally:
    released.set()
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
