"""Check native leave/reload prompts against real source, project and PDF downloads."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from threading import Thread
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    location = parser.add_mutually_exclusive_group(required=True)
    location.add_argument('--site', type=Path)
    location.add_argument('--url', help='Published playground URL, including trailing slash')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browser', choices=['chrome', 'chromium', 'firefox'], default='chrome')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = dict(ok=False, at=datetime.now(timezone.utc).isoformat(), browser=args.browser,
                  cases=[], dialogs=[], downloads=[], pageErrors=[])
    server = None
    if args.site:
        root = args.site.resolve()
        prefix = '/nested/docs/'

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(root), **kw)

            def translate_path(self, path):
                name = unquote(urlsplit(path).path)
                resolved = (root / name[len(prefix):]).resolve()
                return str(resolved if name.startswith(prefix) and resolved.is_relative_to(root)
                           else root / 'not-found')

            def end_headers(self):
                self.send_header('Cache-Control', 'no-store')
                super().end_headers()

            def copyfile(self, source, outputfile):
                try:
                    super().copyfile(source, outputfile)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}{prefix}playground/'
    else:
        url = args.url
    report['url'] = url

    try:
        with sync_playwright() as playwright:
            browser = (playwright.firefox.launch() if args.browser == 'firefox'
                       else playwright.chromium.launch(channel='chrome' if args.browser == 'chrome' else None))
            report['browserVersion'] = browser.version
            active_case = ''
            accept_dialog = False

            def dialog_handler(dialog):
                report['dialogs'].append(dict(case=active_case, type=dialog.type, accepted=accept_dialog))
                if accept_dialog:
                    dialog.accept()
                else:
                    dialog.dismiss()

            @contextmanager
            def case(name):
                nonlocal active_case, accept_dialog
                active_case, accept_dialog = name, False
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                page = context.new_page()
                page.on('dialog', dialog_handler)
                page.on('pageerror', lambda error: report['pageErrors'].append(str(error)))
                try:
                    page.goto(url, wait_until='domcontentloaded')
                    expect(page.locator('#pg-html')).to_be_enabled(timeout=30000)
                    # Actual activation is required for native beforeunload prompts.
                    page.locator('#pg-html').click()
                    if page.locator('#pg-cancel').is_visible():
                        page.locator('#pg-cancel').click()
                    if 'appSha256' not in report:
                        script = page.locator('script[src*="/playground/app.js"]').get_attribute('src')
                        absolute = page.evaluate('(src) => new URL(src, location.href).href', script)
                        response = context.request.get(absolute)
                        assert response.ok
                        report['appSha256'] = sha256(response.body()).hexdigest()
                    yield page
                    report['cases'].append(dict(name=name, ok=True))
                    print(json.dumps(dict(case=name, ok=True)), flush=True)
                except BaseException:
                    page.screenshot(path=str(out / f'{name}-failure.png'), full_page=True)
                    raise
                finally:
                    context.close()

            def source(page):
                return {name: page.locator('#pg-' + name).input_value() for name in ('html', 'css')}

            def edit(page, name, value):
                page.locator('#pg-' + name + '-tab').click()
                page.locator('#pg-' + name).fill(value)

            def guarded(page, reload=False):
                before = source(page)
                assets = page.locator('#pg-assets').inner_text()
                start_url = page.url
                count = len(report['dialogs'])
                with page.expect_event('dialog', timeout=10000) as pending:
                    if reload:
                        page.evaluate('() => { setTimeout(() => location.reload(), 0); }')
                    else:
                        page.get_by_role('link', name='CSS support', exact=True).click(no_wait_after=True)
                assert pending.value.type == 'beforeunload'
                assert len(report['dialogs']) == count + 1
                assert page.url == start_url and source(page) == before
                assert page.locator('#pg-assets').inner_text() == assets

            def clean_leave(page):
                nonlocal accept_dialog
                count = len(report['dialogs'])
                accept_dialog = True  # Unexpected prompts must fail, rather than hang the test.
                page.get_by_role('link', name='CSS support', exact=True).click()
                expect(page).to_have_url(re.compile(r'/css-coverage/$'))
                accept_dialog = False
                assert len(report['dialogs']) == count, 'Saved/unchanged work still prompted before leaving'

            def download(page, selector, name):
                with page.expect_download(timeout=60000) as pending:
                    page.locator(selector).click()
                path = out / name
                pending.value.save_as(path)
                assert pending.value.failure() is None
                report['downloads'].append(dict(name=name, bytes=path.stat().st_size,
                                               sha256=sha256(path.read_bytes()).hexdigest()))
                return path

            def project(page, name, expected=None, assets=None):
                expected = expected or source(page)
                path = download(page, '#pg-project', name + '.zip')
                check_project(path, expected, assets)
                return path

            def check_project(path, expected, assets=None):
                with ZipFile(path) as archive:
                    assert archive.testzip() is None
                    assert archive.read('input.html') == expected['html'].encode()
                    assert archive.read('style.css') == expected['css'].encode()
                    if assets is not None:
                        actual = {name: archive.read(name) for name in archive.namelist() if name.startswith('assets/')}
                        assert actual == assets
                    manifest = json.loads(archive.read('project.json'))
                    assert all(sha256(archive.read(item['path'])).hexdigest() == item['sha256']
                               for item in manifest['files'])

            def import_project(page, path):
                page.locator('#pg-project-file').set_input_files(str(path))
                expect(page.locator('#pg-status')).to_contain_text('Project opened locally.')
                expect(page.locator('#pg-open-project')).to_be_enabled()

            asset_a = dict(name='draft-a.txt', mimeType='text/plain', buffer=b'Synthetic asset A\n')
            asset_b = dict(name='draft-b.txt', mimeType='text/plain', buffer=b'Synthetic asset B\n')
            with case('unchanged') as page:
                clean_leave(page)
            with case('imported-line-endings') as page:
                page.locator('#pg-files').set_input_files([
                    dict(name='windows.html', mimeType='text/html', buffer=b'<h1>Imported document</h1>\r\n<p>Second line</p>\r'),
                    dict(name='windows.css', mimeType='text/css', buffer=b'h1 { color: black; }\r\n'),
                ])
                expect(page.locator('#pg-status')).to_contain_text('Files opened locally.')
                assert '\r' not in source(page)['html']
                clean_leave(page)
            with case('separate-source-saves') as page:
                original = source(page)
                edit(page, 'html', original['html'] + '\n<!-- draft HTML -->')
                edit(page, 'css', original['css'] + '\n/* draft CSS */')
                guarded(page)
                guarded(page, reload=True)
                expected = source(page)
                assert download(page, '#pg-save-html', 'source.html').read_bytes() == expected['html'].encode()
                guarded(page)
                assert download(page, '#pg-save-css', 'source.css').read_bytes() == expected['css'].encode()
                clean_leave(page)
            with case('restore-previously-saved-source') as page:
                original = source(page)
                first = original['html'] + '\n<!-- first saved version -->'
                edit(page, 'html', first)
                download(page, '#pg-save-html', 'first-version.html')
                edit(page, 'html', first + '\n<!-- second saved version -->')
                download(page, '#pg-save-html', 'second-version.html')
                edit(page, 'html', first)
                clean_leave(page)
            with case('multiple-examples') as page:
                edit(page, 'html', source(page)['html'] + '\n<!-- invoice draft -->')
                invoice = source(page)
                page.locator('#pg-example').select_option('report')
                guarded(page)
                edit(page, 'css', source(page)['css'] + '\n/* report draft */')
                page.locator('#pg-project-language').select_option('node')
                project(page, 'report-node')
                guarded(page)
                page.locator('#pg-example').select_option('invoice')
                assert source(page) == invoice
                page.locator('#pg-project-language').select_option('python')
                project(page, 'invoice-python')
                clean_leave(page)
            with case('asset-addition') as page:
                page.locator('#pg-files').set_input_files(asset_a)
                expect(page.locator('#pg-asset-count')).to_have_text('1 local asset')
                guarded(page)
                asset_project = project(page, 'with-asset', assets={'assets/draft-a.txt': asset_a['buffer']})
                clean_leave(page)
            with case('unchanged-project-import') as page:
                import_project(page, asset_project)
                clean_leave(page)
            with case('asset-removal') as page:
                import_project(page, asset_project)
                page.get_by_role('button', name='Remove draft-a.txt', exact=True).click()
                guarded(page)
                project(page, 'without-asset', assets={})
                clean_leave(page)
            with case('export-snapshot') as page:
                page.locator('#pg-files').set_input_files(asset_a)
                expect(page.locator('#pg-asset-count')).to_have_text('1 local asset')
                edit(page, 'html', source(page)['html'] + '\n<!-- export snapshot -->')
                snapshot = source(page)
                held = []
                route_pattern = '**/project/render.py?*'
                page.route(route_pattern, lambda route: held.append(route))
                with page.expect_request(re.compile(r'/project/render\.py\?')):
                    page.locator('#pg-project').click()
                expect(page.locator('#pg-project')).to_have_text('Preparing project…')
                assert len(held) == 1
                edit(page, 'html', snapshot['html'] + '\n<!-- newer draft -->')
                page.get_by_role('button', name='Remove draft-a.txt', exact=True).click()
                page.locator('#pg-files').set_input_files(asset_b)
                expect(page.locator('#pg-assets')).to_contain_text('draft-b.txt')
                with page.expect_download(timeout=60000) as pending:
                    held[0].continue_()
                snapshot_path = out / 'snapshot.zip'
                pending.value.save_as(snapshot_path)
                check_project(snapshot_path, snapshot, {'assets/draft-a.txt': asset_a['buffer']})
                expect(page.locator('#pg-project-status')).to_contain_text('include newer changes')
                guarded(page, reload=True)
                page.unroute(route_pattern)
                project(page, 'newer-project', assets={'assets/draft-b.txt': asset_b['buffer']})
                clean_leave(page)
            with case('failed-export') as page:
                edit(page, 'html', source(page)['html'] + '\n<!-- failed export draft -->')
                route_pattern = '**/project/render.py?*'
                page.route(route_pattern, lambda route: route.fulfill(status=503, body='Controlled export failure'))
                page.locator('#pg-project').click()
                expect(page.locator('#pg-project-status')).to_have_attribute('data-error', 'true')
                guarded(page)
                page.unroute(route_pattern)
                project(page, 'retried-project')
                clean_leave(page)
            with case('css-import-keeps-html-dirty') as page:
                import_project(page, asset_project)
                edit(page, 'html', source(page)['html'] + '\n<!-- retained custom HTML -->')
                page.locator('#pg-files').set_input_files(dict(name='import.css', mimeType='text/css', buffer=b'body { color: black; }'))
                expect(page.locator('#pg-status')).to_contain_text('Files opened locally.')
                guarded(page)
                page.locator('#pg-reset').click()
                guarded(page)  # Reset cannot save HTML retained by a CSS-only import.
                expected = source(page)['html']
                assert download(page, '#pg-save-html', 'retained.html').read_bytes() == expected.encode()
                clean_leave(page)
            with case('reset-discards-source-edits') as page:
                import_project(page, asset_project)
                baseline = source(page)
                edit(page, 'html', baseline['html'] + '\n<!-- discarded draft -->')
                edit(page, 'css', baseline['css'] + '\n/* discarded CSS */')
                guarded(page)
                page.locator('#pg-reset').click()
                assert source(page) == baseline
                clean_leave(page)
            with case('pdf-does-not-save-project') as page:
                edit(page, 'html', source(page)['html'] + '\n<!-- editable PDF source -->')
                page.locator('#pg-render').click()
                expect(page.locator('#pg-download')).to_have_attribute('href', re.compile('^blob:'), timeout=120000)
                path = download(page, '#pg-download', 'edited.pdf')
                assert path.read_bytes().startswith(b'%PDF-')
                guarded(page)
            assert not report['pageErrors'], report['pageErrors']
            report['ok'] = True
            browser.close()
    except BaseException as error:
        report['error'] = str(error)
        raise
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if server:
            server.shutdown()
            server.server_close()
    print(json.dumps(dict(ok=report['ok'], cases=len(report['cases']), nativeDialogs=len(report['dialogs']))), flush=True)


if __name__ == '__main__':
    main()
