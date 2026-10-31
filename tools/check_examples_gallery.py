"""Exercise the visual catalog, shared filters, legacy links and real source downloads."""
from argparse import ArgumentParser
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import unquote, urlparse
from zipfile import ZipFile

from playwright.sync_api import sync_playwright, expect


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--base-url')
    parser.add_argument('--browser', choices=['chrome', 'chromium'], default='chrome')
    args = parser.parse_args()
    root, out = args.site.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def log_message(self, *a):
            pass

    server = None
    if args.base_url:
        base = args.base_url.rstrip('/')
    else:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = 'http://127.0.0.1:' + str(server.server_port)
    results, downloads, assets = [], [], {}
    legacy = ['made-for-the-printed-page', 'python-components', 'accessible-components', 'csharp-components',
              'pdf-template', 'numbered-report', 'linked-report', 'styled-invoice', 'business-report',
              'tagged-service-notice', 'hillside-member-statements', 'run-the-showcase',
              'gridline-product-report-from-pandas', 'northstar-sales-brief-from-streamlit',
              'fieldnote-report-with-matplotlib', 'yunshan-bilingual-invoice',
              'nawa-studio-arabic-and-english-invoice', 'northstar-engineering-markdown-brief',
              'smaller-starting-points']
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**({'channel': 'chrome'} if args.browser == 'chrome' else {}))
            try:
                for label, width, height, dark in [('desktop', 1440, 1000, False), ('mobile', 390, 844, False),
                                                   ('narrow-dark', 320, 740, True)]:
                    context = browser.new_context(viewport=dict(width=width, height=height), accept_downloads=True,
                                                  color_scheme='dark' if dark else 'light')
                    try:
                        page = context.new_page()
                        errors = []
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        response = page.goto(base + '/examples/', wait_until='networkidle')
                        assert response.status == 200
                        expect(page.get_by_role('group', name='Filter examples by document type')).to_be_visible()
                        cards = page.locator('.example-card')
                        total = cards.count()
                        assert total >= 16
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
                        image_state = cards.locator('figure img').evaluate_all('''images => images.map(img => ({
                            src:img.currentSrc, loaded:img.complete && img.naturalWidth > 0, loading:img.loading,
                            top:img.getBoundingClientRect().top, bottom:img.getBoundingClientRect().bottom,
                            frameTop:img.closest('figure').getBoundingClientRect().top,
                            frameBottom:img.closest('figure').getBoundingClientRect().bottom,
                            declaredWidth:img.getAttribute('width'), declaredHeight:img.getAttribute('height')
                        }))''')
                        page.screenshot(path=str(out / (label + '-all.png')), animations='disabled')
                        (out / (label + '-initial.json')).write_text(json.dumps(image_state, indent=2) + '\n', encoding='utf8')
                        assert image_state[0]['loaded'] and image_state[0]['top'] < height - 100
                        assert all(x['bottom'] - x['top'] > 100 and x['top'] >= x['frameTop']
                                   and x['bottom'] <= x['frameBottom'] + 1 for x in image_state)
                        assert all(x['declaredWidth'] and x['declaredHeight'] for x in image_state)
                        assert sum(x['loaded'] for x in image_state) < total, 'Offscreen previews should not all load immediately.'
                        initial_image_bytes = page.evaluate('performance.getEntriesByType("resource").filter(x => x.initiatorType === "img").reduce((sum, x) => sum + x.encodedBodySize, 0)')
                        for anchor in legacy:
                            assert page.locator('[id="' + anchor + '"]').count() == 1, anchor

                        reports = page.get_by_role('button', name='Reports & guides', exact=True)
                        reports.focus()
                        reports.press('Space')
                        expect(reports).to_have_attribute('aria-pressed', 'true')
                        expect(page.locator('#business-report')).to_be_visible()
                        expect(page.locator('#styled-invoice')).not_to_be_visible()
                        assert urlparse(page.url).query == 'type=reports'
                        report_count = page.locator('.example-card:visible').count()
                        expect(page.get_by_role('status')).to_have_text(f'Showing {report_count} of {total} examples')
                        page.screenshot(path=str(out / (label + '-reports.png')), animations='disabled')

                        page.get_by_role('button', name='Invoices', exact=True).click()
                        expect(page.locator('#styled-invoice')).to_be_visible()
                        expect(page.locator('#business-report')).not_to_be_visible()
                        page.go_back()
                        expect(reports).to_have_attribute('aria-pressed', 'true')
                        expect(page.locator('#business-report')).to_be_visible()
                        page.go_forward()
                        expect(page.get_by_role('button', name='Invoices', exact=True)).to_have_attribute('aria-pressed', 'true')

                        page.goto(base + '/examples/?type=templates', wait_until='networkidle')
                        expect(page.locator('#pdf-template')).to_be_visible()
                        assert page.locator('.example-card:visible').count() == 1
                        assert page.locator('.example-card:visible').bounding_box()['width'] < 600
                        page.screenshot(path=str(out / (label + '-templates.png')), animations='disabled')
                        page.goto(base + '/examples/?type=invoices#business-report', wait_until='networkidle')
                        expect(page.locator('#business-report')).to_be_visible()
                        assert urlparse(page.url).fragment == 'business-report' and not urlparse(page.url).query
                        assert 48 <= page.locator('#business-report').bounding_box()['y'] < height - 100
                        expect(page.get_by_role('button', name='All examples', exact=True)).to_have_attribute('aria-pressed', 'true')

                        if label == 'desktop':
                            for anchor, index, filename in [
                                ('styled-invoice', 0, 'fullbleed-styled-invoice.zip'),
                                ('pdf-template', 0, 'fullbleed-pdf-template.zip'),
                                ('pdf-template', 1, 'fullbleed-pdf-template-csharp.zip'),
                                ('csharp-components', 0, 'fullbleed-csharp-components.zip'),
                            ]:
                                card = page.locator('.example-card').filter(has=page.locator('#' + anchor))
                                link = card.locator('.example-source').nth(index)
                                url = link.evaluate('a => a.href')
                                relative = unquote(urlparse(url).path).lstrip('/')
                                expected = (root / relative).resolve()
                                assert expected.is_relative_to(root) and expected.is_file()
                                with page.expect_download() as pending:
                                    link.click()
                                download = pending.value
                                assert download.failure() is None
                                assert download.suggested_filename == filename
                                saved = out / download.suggested_filename
                                download.save_as(saved)
                                assert saved.read_bytes() == expected.read_bytes()
                                with ZipFile(saved) as archive:
                                    assert archive.testzip() is None
                                downloads.append(dict(example=anchor, file=saved.name, sha256=sha256(saved.read_bytes()).hexdigest()))
                            # Inspect every PDF destination exposed by the catalog against the built artifact.
                            for link in page.locator('.example-pdf').all():
                                url = link.evaluate('a => a.href')
                                relative = unquote(urlparse(url).path).lstrip('/')
                                expected = (root / relative).resolve()
                                assert expected.is_relative_to(root)
                                response = context.request.get(url)
                                assert response.status == 200 and response.body().startswith(b'%PDF-')
                                assert response.body() == expected.read_bytes()
                                assets[relative] = sha256(response.body()).hexdigest()
                            notice = page.locator('.example-card').filter(has=page.locator('#tagged-service-notice'))
                            notice.locator('summary').click()
                            assert 'not a complete accessibility or independent conformance assessment' in ' '.join(notice.inner_text().split())
                            page.goto(base + '/examples/?type=unknown', wait_until='networkidle')
                            assert page.locator('.example-card:visible').count() == total
                        assert not errors, errors
                        results.append(dict(device=label, total=total, initialImagesLoaded=sum(x['loaded'] for x in image_state),
                                            firstPreviewTop=image_state[0]['top'], viewportHeight=height,
                                            initialImageBytes=initial_image_bytes, reports=report_count,
                                            filters=True, keyboard=True, history=True, directCategory=True, legacyAnchor=True, errors=errors))
                    finally:
                        context.close()
                context = browser.new_context(viewport=dict(width=390, height=844), java_script_enabled=False)
                try:
                    page = context.new_page()
                    response = page.goto(base + '/examples/?type=invoices', wait_until='networkidle')
                    assert response.status == 200
                    assert page.locator('.example-card:visible').count() == total
                    expect(page.locator('.example-filters')).not_to_be_visible()
                    notice = page.locator('.example-card').filter(has=page.locator('#tagged-service-notice'))
                    notice.locator('summary').click()
                    expect(notice.locator('details')).to_have_attribute('open', '')
                    assert notice.get_by_role('link', name='accessibility workflow', exact=True).is_visible()
                    page.screenshot(path=str(out / 'no-javascript-details.png'), animations='disabled')
                finally:
                    context.close()
            finally:
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    record = dict(status='passed', results=results, actualSourceDownloads=downloads, pdfAssets=assets,
                  withoutJavaScript=True, authenticatedTabsTouched=False)
    (out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
