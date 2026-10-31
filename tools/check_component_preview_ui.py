"""Check the component preview guide and its visible PDF/source downloads."""
import argparse
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browser', choices=['chrome', 'chromium'], default='chrome')
    parser.add_argument('--base-url', help='Check the deployed site instead of a local server')
    args = parser.parse_args()
    root = args.site.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((root / 'assets/component-preview/verification.json').read_text(encoding='utf-8'))
    source = json.loads((root / 'assets/component-preview/source.json').read_text(encoding='utf-8'))
    assert source['source_commit'] == manifest['source_commit']
    assert source['zip_sha256'] == manifest['source_zip_sha256']

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
        base = f'http://127.0.0.1:{server.server_port}'
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**({'channel': 'chrome'} if args.browser == 'chrome'
                                          else {'executable_path': p.chromium.executable_path}))
            browser_version = browser.version
            for label, width, height in [('desktop', 1440, 1000), ('mobile', 390, 844), ('narrow-mobile', 320, 740)]:
                context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1)
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                response = page.goto(base + '/guides/component-design-preview/', wait_until='networkidle')
                assert response.status == 200
                assert page.get_by_role('heading', name='Components that carry their design', exact=False).is_visible()
                assert page.get_by_text('Archived design prototype', exact=True).is_visible()
                assert page.get_by_role('link', name='current component guide', exact=True).get_attribute('href') == '../component-preview-12/'
                assert page.get_by_role('link', name='release status', exact=True).get_attribute('href') == '../component-status/'
                article = page.locator('article').inner_text()
                assert 'not included in the published 2.5.26 wheel' in article
                assert source['source_commit'][:7] in article and 'with_values' in article and 'required_tokens' in article
                assert 'Document(styles=' in article and 'selector_styles()' in article
                assert 'python first_pdf.py' in article and 'summary.pdf' in article
                assert '--force-reinstall -r requirements-preview.txt' in article and 'prebuilt wheel' in article
                assert page.get_by_role('link', name='GitHub preview', exact=True).get_attribute('href') == 'https://github.com/fullbleed-engine/fullbleed-official/releases/tag/component-preview-f88cced'
                assert page.get_by_role('link', name='Share an editing task in the design discussion', exact=True).get_attribute('href') == 'https://github.com/fullbleed-engine/fullbleed-official/discussions/86'
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                images = page.locator('article img').evaluate_all('(items) => items.map(i => ({loaded: i.complete && i.naturalWidth > 0, alt: i.alt}))')
                assert len(images) == 2 and all(image['loaded'] and image['alt'] for image in images), images
                page.screenshot(path=str(args.out / f'{label}-top.png'), animations='disabled')
                for section, heading in [('authoring', 'Make your first PDF'),
                                         ('styling', 'Connect an existing class to its styles'),
                                         ('installation', 'Try the preview')]:
                    page.get_by_role('heading', name=heading, exact=False).scroll_into_view_if_needed()
                    page.screenshot(path=str(args.out / f'{label}-{section}.png'), animations='disabled')
                downloads = []
                for document in manifest['documents']:
                    filename = document['file']
                    link = page.get_by_role('link', name='Open the invoice PDF' if filename == 'invoice.pdf' else 'Open the five-page report', exact=True)
                    result = context.request.get(link.evaluate('(element) => element.href'))
                    assert result.status == 200 and result.headers['content-type'].split(';')[0] == 'application/pdf'
                    assert sha256(result.body()).hexdigest() == document['sha256']
                    downloads.append({'file': filename, 'exact_bytes': True})
                link = page.get_by_role('link', name='Download the example kit', exact=True)
                result = context.request.get(link.evaluate('(element) => element.href'))
                assert result.status == 200 and sha256(result.body()).hexdigest() == source['zip_sha256']
                assert len(result.body()) == source['zip_bytes']
                (args.out / 'project.zip').write_bytes(result.body())
                downloads.append({'file': 'project.zip', 'exact_bytes': True})
                assert not errors, errors
                results.append({'viewport': label, 'width': width, 'horizontal_overflow': False, 'images': len(images), 'downloads': downloads, 'page_errors': errors})
                context.close()
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report = {'ok': True, 'browser': browser_version, 'base_url': base, 'source_commit': source['source_commit'],
              'cases': results, 'scope': 'Rendered guide, desktop/mobile layout, loaded previews and exact PDF/source ZIP bytes fetched from visible links. No PDF viewer or interactive editor is claimed.'}
    (args.out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'viewports': len(results), 'source_commit': source['source_commit']}))


if __name__ == '__main__':
    main()
