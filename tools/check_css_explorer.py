"""Check the real evidence browser, including public PDF bytes and failure states."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
from urllib.parse import parse_qs, quote, unquote, urlsplit

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browser', choices=['chrome', 'chromium'], default='chrome')
    parser.add_argument('--base-url', help='Verify a deployed site instead of a local HTTP server.')
    args = parser.parse_args()
    root, out = args.site.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    publication = json.loads((root / 'assets/css-corpus/published.json').read_text(encoding='utf-8'))
    index_path = f"assets/css-corpus/{publication['version']}/index.json"
    index_bytes = (root / index_path).read_bytes()
    index = json.loads(index_bytes)
    fixtures = {row['key']: row for row in index['fixtures']}
    historical_indices = []
    checks, errors, downloads = [], [], []
    prefix = '/nested/docs/'

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def translate_path(self, path):
            name = unquote(urlsplit(path).path)
            resolved = (root / name[len(prefix):]).resolve() if name.startswith(prefix) else root / 'not-found'
            return str(resolved if resolved.is_relative_to(root) else root / 'not-found')

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

    server = None
    if args.base_url:
        base = args.base_url.rstrip('/') + '/'
    else:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}{prefix}'
    url = base + 'guides/css-explorer/'
    result = {'startedAt': datetime.now(timezone.utc).isoformat(), 'url': url,
              'version': index['version'], 'archiveSha256': publication['archiveSha256'],
              'checks': checks, 'downloads': downloads, 'historicalDownloads': [], 'errors': errors}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**({'channel': 'chrome'} if args.browser == 'chrome' else {}))
            result['browser'] = browser.version
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            try:
                response = context.request.get(base + index_path)
                check('served index preserves all verified bytes', response.ok and response.body() == index_bytes)
                for asset in ('explorer.js', 'explorer.css'):
                    asset_path = 'assets/css-corpus/' + asset
                    response = context.request.get(base + asset_path)
                    check('legacy browser asset URL remains available unchanged: ' + asset,
                          response.ok and response.body() == (root / asset_path).read_bytes())
                for config_path in sorted((root / 'assets/css-corpus/history').glob('*.json')):
                    historical = json.loads(config_path.read_text(encoding='utf-8'))
                    historical_prefix = f"assets/css-corpus/{historical['version']}/"
                    historical_bytes = (root / historical_prefix / 'index.json').read_bytes()
                    response = context.request.get(base + historical_prefix + 'index.json')
                    check('historical index remains byte-identical: ' + historical['version'],
                          response.ok and response.body() == historical_bytes)
                    historical_index = json.loads(historical_bytes)
                    assert historical_index['version'] == historical['version']
                    assert historical_index['archiveUrl'] == historical['archiveUrl']
                    historical_indices.append((historical, historical_index))
                    for verdict in ('PASS', 'FAIL', 'REFERENCE-DISPUTED'):
                        fixture = next(row for row in historical_index['fixtures'] if row['status'] == verdict)
                        response = context.request.get(base + historical_prefix + fixture['pdf'])
                        check(f"historical {verdict} PDF URL preserves its bytes: {historical['version']}",
                              response.ok and sha256(response.body()).hexdigest() == fixture['pdfSha256'])
                page.goto(url, wait_until='domcontentloaded')
                expect(page.locator('#ce-controls')).to_be_visible()
                expect(page.locator('#ce-loading')).to_contain_text('1,662 fixtures')
                expect(page.locator('#ce-loading')).to_contain_text('full comparison gate failed')
                expect(page.get_by_label('Package version', exact=True)).to_have_value(index['version'])
                check('current package is explicit in the selectable version and shared URL',
                      parse_qs(urlsplit(page.url).query).get('version') == [index['version']])
                for verdict, count in index['counts'].items():
                    expect(page.locator('#ce-counts')).to_contain_text(f'{verdict} {count:,}')
                check('all original verdict totals and failed gate are visible', True)
                expect(page.get_by_role('link', name='Complete evidence ZIP')).to_have_attribute('href', publication['archiveUrl'])
                expect(page.locator('.ce-result')).to_have_count(12)
                expect(page.locator('#ce-previous')).to_be_disabled()
                first = page.locator('.ce-result button').first.inner_text()
                page.locator('#ce-next').click()
                expect(page.locator('#ce-page')).to_have_text('Page 2 of 139')
                check('pagination exposes the next fixtures', page.locator('.ce-result button').first.inner_text() != first)
                page.locator('#ce-previous').click()
                expect(page.locator('.ce-result button').first).to_have_text(first)
                page.evaluate('scrollTo(0, 0)')
                page.screenshot(path=str(out / 'desktop.png'), animations='disabled')

                page.locator('#ce-verdict').select_option('FAIL')
                expect(page.locator('#ce-results-status')).to_contain_text(f"{index['counts']['FAIL']} matching fixtures")
                check('FAIL filter keeps only original failing verdicts',
                      set(page.locator('.ce-result .ce-verdict').all_text_contents()) == {'FAIL'})
                page.locator('#ce-category').select_option('grid')
                page.locator('#ce-search').fill('text-survival')
                expect(page.locator('.ce-result')).to_have_count(1)
                page.locator('.ce-result button').click()
                grid = fixtures['grid/grid-display-contents-fragmentation-text-survival']
                expect(page.locator('#ce-detail-title')).to_have_text(grid['id'])
                check('combined filters and selection preserve the FAIL label',
                      page.locator('#ce-detail .ce-verdict').inner_text() == grid['status'] == 'FAIL')
                check('selection moves keyboard focus to the detail', page.locator('#ce-detail').evaluate('(el) => el === document.activeElement'))
                shared = page.get_by_role('link', name='Link to this case').get_attribute('href')
                page.reload(wait_until='domcontentloaded')
                expect(page.locator('#ce-detail-title')).to_have_text(grid['id'])
                expect(page.locator('#ce-search')).to_have_value('text-survival')
                check('shared case URL restores filters and selected fixture', page.url == shared)
                expect(page.locator('#ce-detail .ce-images')).to_have_count(3)

                def download(key):
                    fixture = fixtures[key]
                    page.goto(url + '?case=' + quote(key), wait_until='domcontentloaded')
                    expect(page.locator('#ce-detail-title')).to_have_text(fixture['id'])
                    expect(page.locator('#ce-detail .ce-verdict')).to_have_text(fixture['status'])
                    expect(page.locator('#ce-detail')).to_contain_text('Reference metadata: ' + fixture['referenceStatus'])
                    with page.expect_download() as pending:
                        page.get_by_role('link', name='Download Fullbleed PDF').click()
                    target = out / (fixture['id'] + '.pdf')
                    pending.value.save_as(target)
                    digest = sha256(target.read_bytes()).hexdigest()
                    check('PDF bytes match original evidence: ' + fixture['id'], digest == fixture['pdfSha256'])
                    pages = len(PdfReader(target).pages)
                    check('PDF page inventory matches candidate previews: ' + fixture['id'],
                          pages == sum(bool(row['candidate']) for row in fixture['pages']))
                    downloads.append({'key': key, 'sha256': digest, 'pages': pages})
                    return fixture

                download(grid['key'])
                download(next(row['key'] for row in index['fixtures'] if row['status'] == 'REFERENCE-DISPUTED'))
                dropcap = download('generated-content/generated-content-first-letter-dropcap')
                check('PASS retains the reference dispute metadata',
                      dropcap['status'] == 'PASS' and dropcap['referenceStatus'].lower() == 'disputed')
                note = page.locator('#ce-detail details').filter(has=page.get_by_text('Upstream reference review note', exact=True))
                check('long reference notes are collapsed initially', not note.evaluate('(el) => el.open'))
                note.locator('summary').click()
                expect(note.locator('p')).to_have_text(dropcap['referenceNote'])
                note.locator('summary').click()
                check('the complete original reference note remains available', True)
                images = page.locator('#ce-detail img')
                for item in images.all():
                    item.scroll_into_view_if_needed()
                    expect(item).to_be_visible()
                    page.wait_for_function('(img) => img.complete && img.naturalWidth > 0', arg=item.element_handle())
                check('both original page previews load in a real browser', images.count() == 2)
                page.locator('#ce-detail').evaluate('(el) => el.scrollIntoView({block: "start"})')
                page.screenshot(path=str(out / 'desktop-detail.png'), animations='disabled')
                page.get_by_title('Switch to dark mode', exact=True).click()
                expect(page.locator('body')).to_have_attribute('data-md-color-scheme', 'slate')
                expect(page.get_by_role('link', name='Download Fullbleed PDF')).to_have_css('color', 'rgb(142, 222, 195)')
                check('real dark-mode toggle preserves readable download links', True)
                page.screenshot(path=str(out / 'dark-detail.png'), animations='disabled')
                page.get_by_title('Switch to light mode', exact=True).click()
                expect(page.locator('body')).to_have_attribute('data-md-color-scheme', 'default')
                for width in (390, 320):
                    page.set_viewport_size({'width': width, 'height': 844})
                    page.locator('#ce-detail').evaluate('(el) => el.scrollIntoView({block: "start"})')
                    check(f'selected heading clears the fixed header at {width}px',
                          page.locator('#ce-detail-title').bounding_box()['y'] >= page.locator('header.md-header').bounding_box()['height'])
                    check(f'no horizontal overflow at {width}px',
                          page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                    check(f'page previews stack at {width}px',
                          page.locator('.ce-images').first.evaluate('(el) => getComputedStyle(el).gridTemplateColumns.split(" ").length === 1'))
                    page.screenshot(path=str(out / f'mobile-{width}.png'), animations='disabled')

                page.locator('#ce-search').fill('<img src=x onerror=alert(1)>')
                expect(page.locator('#ce-results-status')).to_contain_text('No fixtures match')
                expect(page.locator('#ce-detail')).to_be_hidden()
                check('empty results clear selection without interpreting input as HTML', page.locator('#css-explorer img').count() == 0)
                page.goto(url + '?version=unknown&category=unknown&verdict=unknown&case=unknown', wait_until='domcontentloaded')
                expect(page.locator('#ce-controls')).to_be_visible()
                expect(page.locator('#ce-category')).to_have_value('')
                expect(page.locator('#ce-verdict')).to_have_value('')
                expect(page.locator('#ce-detail')).to_be_hidden()
                check('invalid shared filters fall back to all fixtures', page.locator('.ce-result').count() == 12)
                expect(page.get_by_label('Package version', exact=True)).to_have_value(index['version'])
                check('unsupported package versions normalize to the current published version',
                      parse_qs(urlsplit(page.url).query).get('version') == [index['version']])

                for historical, historical_index in historical_indices:
                    changed = next((row for row in historical_index['fixtures']
                                    if row['status'] != fixtures[row['key']]['status']), historical_index['fixtures'][0])
                    selected_url = (url + '?case=' + quote(changed['key']) + '&category=' + quote(changed['category'])
                                    + '&q=' + quote(changed['id']) + '&version=' + quote(index['version']))
                    page.goto(selected_url, wait_until='domcontentloaded')
                    expect(page.locator('#ce-detail .ce-verdict')).to_have_text(fixtures[changed['key']]['status'])
                    query = parse_qs(urlsplit(page.url).query)
                    check('legacy fixture search links migrate without opening site search: ' + historical['version'],
                          query.get('query') == [changed['id']] and 'q' not in query
                          and not page.locator('#__search').is_checked())
                    page.get_by_label('Package version', exact=True).select_option(historical['version'])
                    expect(page.locator('#ce-loading')).to_contain_text('published Fullbleed ' + historical['version'])
                    expect(page.locator('#ce-detail-title')).to_have_text(changed['id'])
                    expect(page.locator('#ce-search')).to_have_value(changed['id'])
                    expect(page.locator('#ce-category')).to_have_value(changed['category'])
                    expect(page.locator('#ce-detail .ce-verdict')).to_have_text(changed['status'])
                    for verdict, count in historical_index['counts'].items():
                        expect(page.locator('#ce-counts')).to_contain_text(f'{verdict} {count:,}')
                    expect(page.get_by_role('link', name='Complete evidence ZIP')).to_have_attribute('href', historical['archiveUrl'])
                    shared = page.get_by_role('link', name='Link to this case').get_attribute('href')
                    check('switching package versions preserves the selected case and filters: ' + historical['version'],
                          parse_qs(urlsplit(shared).query).get('version') == [historical['version']])
                    page.reload(wait_until='domcontentloaded')
                    expect(page.locator('#ce-loading')).to_contain_text('published Fullbleed ' + historical['version'])
                    expect(page.locator('#ce-detail .ce-verdict')).to_have_text(changed['status'])
                    check('shared historical selection survives reload: ' + historical['version'], page.url == shared)
                    check('shared historical link leaves mobile site search closed: ' + historical['version'],
                          not page.locator('#__search').is_checked())
                    with page.expect_download() as pending:
                        page.get_by_role('link', name='Download Fullbleed PDF').click()
                    target = out / f"historical-{historical['version']}-{changed['id']}.pdf"
                    pending.value.save_as(target)
                    digest = sha256(target.read_bytes()).hexdigest()
                    pages = len(PdfReader(target).pages)
                    check('selected historical PDF downloads the original package bytes: ' + historical['version'],
                          digest == changed['pdfSha256'] and pages == sum(bool(p['candidate']) for p in changed['pages']))
                    result['historicalDownloads'].append({'version': historical['version'], 'key': changed['key'],
                                                           'sha256': digest, 'pages': pages, 'file': target.name})
                    page.locator('#ce-detail').evaluate('(el) => el.scrollIntoView({block: "start"})')
                    page.screenshot(path=str(out / f"historical-{historical['version']}.png"), animations='disabled')
                    top = page.get_by_role('button', name='Back to top', exact=True)
                    check('historical heading clears the mobile floating navigation: ' + historical['version'],
                          not top.is_visible() or page.locator('#ce-detail-title').bounding_box()['y']
                          >= top.bounding_box()['y'] + top.bounding_box()['height'])
                    page.go_back(wait_until='domcontentloaded')
                    expect(page.locator('#ce-loading')).to_contain_text('published Fullbleed ' + index['version'])
                    expect(page.locator('#ce-detail-title')).to_have_text(changed['id'])
                    expect(page.locator('#ce-detail .ce-verdict')).to_have_text(fixtures[changed['key']]['status'])
                    check('browser Back restores the previous package and case: ' + historical['version'],
                          parse_qs(urlsplit(page.url).query).get('version') == [index['version']])

                unequal = next(row for row in index['fixtures']
                               if any(not p['candidate'] or not p['reference'] for p in row['pages']))
                page.goto(url + '?case=' + quote(unequal['key']), wait_until='domcontentloaded')
                expect(page.locator('#ce-detail-title')).to_have_text(unequal['id'])
                expect(page.locator('#ce-detail')).to_contain_text('No page on this side of the comparison.')
                check('unequal page counts remain visible without invented previews', True)

                page.route('**/out/generated-content/generated-content-first-letter-dropcap.png', lambda route: route.abort())
                page.goto(url + '?case=' + quote(dropcap['key']), wait_until='domcontentloaded')
                expect(page.locator('#ce-detail-title')).to_have_text(dropcap['id'])
                page.locator('#ce-detail .ce-images').scroll_into_view_if_needed()
                expect(page.locator('#ce-detail')).to_contain_text('This preview could not load.')
                expect(page.get_by_role('link', name='Download Fullbleed PDF')).to_be_visible()
                check('preview failure preserves the actual PDF download', True)

                page.route('**/' + index_path, lambda route: route.fulfill(status=503, body='Unavailable'))
                page.reload(wait_until='domcontentloaded')
                expect(page.locator('#ce-loading')).to_contain_text('The fixture browser could not load')
                expect(page.locator('#ce-controls')).to_be_hidden()
                expect(page.get_by_role('link', name='Read the method and limits')).to_be_visible()
                check('index outage preserves a useful evidence-guide fallback', True)
                page.unroute('**/' + index_path)
                page.route('**/assets/css-corpus/versions.json*', lambda route: route.fulfill(status=503, body='Unavailable'))
                page.reload(wait_until='domcontentloaded')
                expect(page.locator('#ce-loading')).to_contain_text('The fixture browser could not load')
                expect(page.locator('#ce-controls')).to_be_hidden()
                expect(page.get_by_role('link', name='Read the method and limits')).to_be_visible()
                check('version inventory outage preserves the evidence-guide fallback', True)
                check('no uncaught browser errors', not errors)
                result['passed'] = True
            except Exception:
                page.screenshot(path=str(out / 'failure.png'), full_page=True)
                raise
            finally:
                (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
                context.close()
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
