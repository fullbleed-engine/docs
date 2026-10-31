"""Exercise responsive playground views with real rendering and project downloads."""
import argparse
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--site', type=Path)
    source.add_argument('--url', help='Public documentation root, including a trailing slash')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'webkit'], default='chrome')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    prefix = '/nested/docs/'
    server = None

    class Handler(SimpleHTTPRequestHandler):
        def translate_path(self, path):
            name = unquote(urlsplit(path).path)
            if not name.startswith(prefix):
                return str(args.site / 'not-found')
            resolved = (args.site / name[len(prefix):]).resolve()
            return str(resolved if resolved.is_relative_to(args.site) else args.site / 'not-found')

        def log_message(self, *a):
            pass

        def copyfile(self, source, outputfile):
            try:
                super().copyfile(source, outputfile)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass

    if args.site:
        args.site = args.site.resolve()
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(args.site)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}{prefix}'
    else:
        base = args.url.rstrip('/') + '/'
    report = dict(at=datetime.now(timezone.utc).isoformat(), url=base, status='running', browser=args.browser,
                  checks=[], viewports=[], downloads=[], pageErrors=[], nonGetRequests=[])

    def check(name, value):
        assert value, name
        report['checks'].append(name)
        print(name + ': passed', flush=True)

    def ready(page):
        expect(page.locator('#pg-download')).to_have_attribute('href', re.compile('^blob:'), timeout=120000)
        expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
        page.wait_for_function('document.querySelector("#pg-preview").naturalWidth > 0')

    def download(page, selector, name):
        with page.expect_download() as pending:
            page.locator(selector).click()
        path = out / name
        pending.value.save_as(str(path))
        report['downloads'].append(dict(file=name, sha256=sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
        return path

    def open_tools(page):
        if not page.locator('#pg-tools').evaluate('tools => tools.open'):
            page.locator('#pg-tools > summary').click()
        expect(page.locator('#pg-open-files')).to_be_visible()

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome') if args.browser == 'chrome' else getattr(pw, args.browser).launch()
            report['browserVersion'] = browser.version
            page = None
            try:
                for name, width, height, dark in [('mobile', 390, 844, False), ('narrow-dark', 320, 740, True), ('desktop', 1440, 1000, False)]:
                    context = browser.new_context(viewport=dict(width=width, height=height), accept_downloads=True,
                                                  color_scheme='dark' if dark else 'light', reduced_motion='reduce')
                    if dark:
                        context.add_init_script("localStorage.setItem('__palette', JSON.stringify({index:1,color:{scheme:'slate',primary:'custom',accent:'custom'}}))")
                    page = context.new_page()
                    page.on('pageerror', lambda error: report['pageErrors'].append(str(error)))
                    page.on('request', lambda request: report['nonGetRequests'].append(dict(url=request.url, method=request.method)) if request.method != 'GET' else None)
                    page.goto(base + 'playground/', wait_until='domcontentloaded')
                    ready(page)
                    page.evaluate('document.fonts.ready')
                    page.evaluate('window.scrollTo(0, 0)')
                    preview = page.locator('#pg-preview').bounding_box()
                    check(name + ': first PDF starts in the initial viewport', preview is not None and preview['y'] < height - 40)
                    check(name + ': no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    if width < 851:
                        expect(page.locator('#pg-editor')).to_be_hidden()
                        expect(page.locator('#pg-view-preview')).to_have_attribute('aria-pressed', 'true')
                        check(name + ': file tools initially closed', not page.locator('#pg-tools').evaluate('tools => tools.open'))
                    else:
                        expect(page.locator('#pg-editor')).to_be_visible()
                        expect(page.locator('#pg-output')).to_be_visible()
                        expect(page.locator('#pg-view')).to_be_hidden()
                        check('desktop: file tools open', page.locator('#pg-tools').evaluate('tools => tools.open'))
                    report['viewports'].append(dict(name=name, width=width, height=height, previewTop=preview['y']))
                    page.screenshot(path=str(out / f'{name}-initial.png'), animations='disabled')
                    pdf = download(page, '#pg-download', name + '-invoice.pdf')
                    reference = context.request.get(base + 'assets/playground/verification.json').json()
                    expected = next(item for item in reference['fixtures'] if item['name'] == 'invoice')['hashes']['output.pdf']
                    check(name + ': actual invoice bytes preserved', sha256(pdf.read_bytes()).hexdigest() == expected)
                    if name != 'mobile':
                        context.close()
                        continue

                    # Editing via the keyboard keeps the source visible and focused.
                    page.locator('#pg-view-source').focus()
                    page.keyboard.press('Enter')
                    expect(page.locator('#pg-html')).to_be_visible()
                    expect(page.locator('#pg-output')).to_be_hidden()
                    html = '<h1>Mobile proof one</h1><p>Edited on a small screen.</p><section class="next"><h1>Mobile proof two</h1></section>'
                    css = '@page {size: A5; margin: 15mm} body {font-family: Inter; font-size: 12pt} .next {break-before: page}'
                    page.locator('#pg-html').fill(html)
                    expect(page.locator('#pg-download')).to_have_attribute('aria-disabled', 'true')
                    page.locator('#pg-css-tab').click()
                    page.locator('#pg-css').fill(css)
                    page.locator('#pg-html-tab').click()
                    page.locator('#pg-html').focus()
                    page.keyboard.press('Control+Enter')
                    ready(page)
                    expect(page.locator('#pg-html')).to_be_focused()
                    expect(page.locator('#pg-html')).to_be_visible()
                    check('keyboard render keeps editor focus and current source', page.locator('#pg-html').input_value() == html)
                    page.locator('#pg-view-preview').click()
                    expect(page.locator('#pg-page-count')).to_have_text('1 / 2')
                    page.locator('#pg-next').click()
                    expect(page.locator('#pg-page-count')).to_have_text('2 / 2')
                    page.locator('#pg-previous').click()
                    expect(page.locator('#pg-page-count')).to_have_text('1 / 2')
                    proof = download(page, '#pg-download', 'edited.pdf')
                    document = PdfReader(proof)
                    check('edited two-page PDF downloads and paginates', len(document.pages) == 2
                          and 'Mobile proof one' in document.pages[0].extract_text() and 'Mobile proof two' in document.pages[1].extract_text())
                    page.locator('#pg-view-source').click()
                    page.locator('#pg-html').focus()
                    page.set_viewport_size(dict(width=1440, height=1000))
                    expect(page.locator('#pg-output')).to_be_visible()
                    expect(page.locator('#pg-html')).to_be_focused()
                    page.set_viewport_size(dict(width=390, height=844))
                    expect(page.locator('#pg-html')).to_be_visible()
                    expect(page.locator('#pg-html')).to_be_focused()
                    check('resizing preserves focused editor and edits', page.locator('#pg-html').input_value() == html and page.locator('#pg-css').input_value() == css)
                    page.screenshot(path=str(out / 'mobile-editor.png'), full_page=True, animations='disabled')
                    page.locator('#pg-render').click()
                    expect(page.locator('#pg-view-preview')).to_have_attribute('aria-pressed', 'true')
                    ready(page)
                    expect(page.locator('#pg-output')).to_be_visible()
                    check('render button opens preview without changing the PDF', download(page, '#pg-download', 'render-button.pdf').read_bytes() == proof.read_bytes())

                    # Open files through a real file chooser; verify saved projects carry edits.
                    open_tools(page)
                    imported_html = '<h1>Local mobile document</h1><img src="assets/mark.svg" width="60" height="30">'
                    imported_css = '@page {size:A5; margin:15mm} body {font-family:Inter; color:#17382e}'
                    mark = b'<svg xmlns="http://www.w3.org/2000/svg" width="60" height="30"><rect width="60" height="30" fill="#17382e"/></svg>'
                    with page.expect_file_chooser() as chooser:
                        page.locator('#pg-open-files').click()
                    chooser.value.set_files([dict(name='document.html', mimeType='text/html', buffer=imported_html.encode()),
                                             dict(name='style.css', mimeType='text/css', buffer=imported_css.encode()),
                                             dict(name='mark.svg', mimeType='image/svg+xml', buffer=mark)])
                    expect(page.locator('#pg-status')).to_contain_text('Files opened locally.')
                    expect(page.locator('#pg-html')).to_be_visible()
                    expect(page.locator('#pg-asset-count')).to_have_text('1 local asset')
                    check('local imports open source view with exact source', page.locator('#pg-html').input_value() == imported_html and page.locator('#pg-css').input_value() == imported_css)
                    projects = {}
                    for language in ['python', 'node']:
                        page.locator('#pg-project-language').select_option(language)
                        projects[language] = download(page, '#pg-project', language + '-project.zip')
                        with ZipFile(projects[language]) as zipped:
                            check(language + ': downloaded project preserves imported source and asset', zipped.testzip() is None
                                  and zipped.read('input.html') == imported_html.encode() and zipped.read('style.css') == imported_css.encode()
                                  and zipped.read('assets/mark.svg') == mark)
                    page.screenshot(path=str(out / 'mobile-files.png'), full_page=True, animations='disabled')
                    page.locator('#pg-render').click()
                    ready(page)
                    imported_pdf = download(page, '#pg-download', 'imported.pdf')
                    page.locator('#pg-example').select_option('notice')
                    ready(page)
                    page.locator('#pg-example').select_option('custom')
                    ready(page)
                    check('switching examples retains imported source and asset', page.locator('#pg-html').input_value() == imported_html
                          and page.locator('#pg-css').input_value() == imported_css and page.locator('#pg-assets li').count() == 1)
                    for language, project in projects.items():
                        open_tools(page)
                        with page.expect_file_chooser() as chooser:
                            page.locator('#pg-open-project').click()
                        chooser.value.set_files(str(project))
                        expect(page.locator('#pg-status')).to_contain_text('Project opened locally.')
                        expect(page.locator('#pg-html')).to_be_visible()
                        expect(page.locator('#pg-project-language')).to_have_value(language)
                        page.locator('#pg-render').click()
                        ready(page)
                        check(language + ': reopened mobile project renders the same PDF', download(page, '#pg-download', language + '-reopened.pdf').read_bytes() == imported_pdf.read_bytes())

                    # A failed worker load remains actionable with the source preserved.
                    page.route('**/playground/worker.js*', lambda route: route.abort())
                    page.locator('#pg-render').click()
                    expect(page.locator('#pg-status')).to_have_attribute('data-error', 'true', timeout=30000)
                    expect(page.locator('#pg-render')).to_be_enabled()
                    expect(page.locator('#pg-output')).to_be_visible()
                    page.locator('#pg-view-source').click()
                    check('mobile load failure retains editable source and assets', page.locator('#pg-html').input_value() == imported_html and page.locator('#pg-assets li').count() == 1)
                    page.unroute('**/playground/worker.js*')
                    page.locator('#pg-render').click()
                    ready(page)
                    check('retry recovers without navigation or source changes', download(page, '#pg-download', 'recovered.pdf').read_bytes() == imported_pdf.read_bytes())
                    page.locator('#pg-view-source').click()
                    page.locator('#pg-view-source').focus()
                    page.set_viewport_size(dict(width=1440, height=1000))
                    expect(page.locator('#pg-editor')).to_be_focused()
                    expect(page.locator('#pg-editor')).to_be_visible()
                    expect(page.locator('#pg-output')).to_be_visible()
                    check('desktop resize leaves no focus on hidden view controls', page.locator('#pg-view').is_hidden())
                    page.set_viewport_size(dict(width=390, height=844))
                    page.route('**/playground/worker.js*', lambda route: route.fulfill(status=200, content_type='application/javascript', body='self.onmessage = () => {};'))
                    page.locator('#pg-render').click()
                    expect(page.locator('#pg-cancel')).to_be_visible()
                    expect(page.locator('#pg-render')).to_be_disabled()
                    page.locator('#pg-view-source').click()
                    page.locator('#pg-view-source').focus()
                    page.set_viewport_size(dict(width=1440, height=1000))
                    expect(page.locator('#pg-editor')).to_be_focused()
                    page.locator('#pg-cancel').click()
                    expect(page.locator('#pg-status')).to_contain_text('Rendering canceled.')
                    expect(page.locator('#pg-render')).to_be_enabled()
                    check('resizing during a render preserves accessible focus and cancellation', page.locator('#pg-html').input_value() == imported_html)
                    page.unroute('**/playground/worker.js*')
                    context.close()
                check('no uncaught browser errors', not report['pageErrors'])
                check('no document uploads', not report['nonGetRequests'])
                report['status'] = 'passed'
            except BaseException as error:
                report['error'] = str(error)
                if page and not page.is_closed():
                    page.screenshot(path=str(out / 'unexpected-failure.png'))
                    page.screenshot(path=str(out / 'unexpected-failure-full.png'), full_page=True)
                raise
            finally:
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        (out / 'verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')


if __name__ == '__main__':
    main()
