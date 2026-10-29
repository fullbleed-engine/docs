"""Check first-use version text and actual project downloads in an anonymous browser."""
import argparse
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import os
from pathlib import Path
import re
from threading import Thread
from urllib.parse import urljoin
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader


def main(args):
    site, out = args.site.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    load = lambda path: json.loads(path.read_bytes())
    node = load(site / 'assets/node/project.json')
    rust = load(site / 'assets/rust-starter/source.json')
    dotnet = load(site / 'assets/dotnet-components/source.json')
    checks, downloads, errors = [], [], []
    record = dict(ok=False, at=datetime.now(timezone.utc).isoformat(), checks=checks, downloads=downloads, errors=errors,
                  scope='Fresh anonymous Chromium; visible guide text, real ZIP downloads, preview loading, and HTTP verification of the linked report and evidence.')
    server = None

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    if args.origin:
        origin = args.origin.rstrip('/')
    else:
        server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Handler, directory=str(site)))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f'http://127.0.0.1:{server.server_port}'
    record['origin'] = origin

    def check(label, condition):
        assert condition, label
        checks.append(label)

    cases = [
        ('node', 'getting-started/node/', 'assets/node/project.zip', node['zip_sha256'],
         [f"Node package {node['package_version']}", f"Fullbleed {node['engine_version']}", 'npm run render:report']),
        ('rust', 'getting-started/rust/', 'assets/rust-starter/project.zip', rust['zip_sha256'],
         [f"cargo add fullbleed@={rust['engine']}", 'cargo run --release --locked --bin from-files']),
        ('dotnet', 'getting-started/dotnet/', 'assets/dotnet-components/project.zip', dotnet['zipSha256'],
         [f"dotnet add package FullBleed.DotNet --version {dotnet['packageVersion']}", f"It pins Fullbleed {dotnet['engineVersion']}."]),
    ]
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            record['browser'] = browser.version
            try:
                for width in [1440, 390]:
                    page.set_viewport_size({'width': width, 'height': 1000})
                    for name, route, archive, digest, phrases in cases:
                        response = page.goto(origin + '/' + route, wait_until='domcontentloaded')
                        check(f'{name} {width}px page loads', response.status == 200)
                        for phrase in phrases:
                            expect(page.locator('.md-content')).to_contain_text(phrase)
                        check(f'{name} {width}px document fits', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
                        page.evaluate('window.scrollTo(0, 0)')
                        page.screenshot(path=str(out / f'{name}-{width}.png'), animations='disabled')
                        with page.expect_download() as pending:
                            page.locator(f'a[href$="{archive}"]').first.click()
                        check(f'{name} {width}px download succeeds', pending.value.failure() is None)
                        target = out / f'{name}-{width}.zip'
                        pending.value.save_as(target)
                        raw = target.read_bytes()
                        check(f'{name} {width}px actual ZIP matches qualified project', sha256(raw).hexdigest() == digest and raw == (site / archive).read_bytes())
                        with ZipFile(target) as zipped:
                            check(f'{name} {width}px ZIP is intact', zipped.testzip() is None)
                            if name == 'node':
                                check(f'node {width}px contains runnable report', {'report.html', 'report.css', 'render-report.mjs'} <= set(zipped.namelist()))
                                check(f'node {width}px pins current package', json.loads(zipped.read('package.json'))['dependencies']['fullbleed'] == node['package_version'])
                        downloads.append(dict(name=name, width=width, path=target.name, sha256=digest))
                        if name == 'node':
                            heading = page.get_by_role('heading', name=re.compile(r'^Style a report with gradients'))
                            expect(heading).to_be_visible()
                            image = page.locator('.md-content img[src$="report-2.png"]')
                            image.scroll_into_view_if_needed()
                            expect(image).to_be_visible()
                            expect(image).to_have_js_property('complete', True)
                            check(f'node {width}px report preview loads', image.evaluate('img => img.complete && img.naturalWidth > 0'))
                            heading.scroll_into_view_if_needed()
                            page.screenshot(path=str(out / f'node-report-{width}.png'), animations='disabled')
                            evidence_link = page.get_by_role('link', name='current guide verification', exact=True).get_attribute('href')
                            evidence_response = context.request.get(urljoin(page.url, evidence_link))
                            check('linked guide verification loads', evidence_response.ok)
                            evidence = evidence_response.json()
                            check('guide evidence identifies actual package and report', evidence['ok'] and evidence['package_version'] == node['package_version'] and evidence['engine_version'] == node['engine_version'] and evidence['report']['pages'] == 3)
                            revision = args.expected_revision or os.environ.get('GITHUB_SHA')
                            if revision:
                                check('guide evidence belongs to expected revision', evidence['source_revision'] == revision)
                            report_link = page.get_by_role('link', name='Open the report PDF', exact=True).get_attribute('href')
                            pdf_response = context.request.get(urljoin(page.url, report_link))
                            check('linked report has qualified bytes', pdf_response.ok and sha256(pdf_response.body()).hexdigest() == node['report']['report.pdf'])
                            check('linked report has three pages', len(PdfReader(io.BytesIO(pdf_response.body())).pages) == 3)
                        print(json.dumps(dict(guide=name, width=width, downloadVerified=True)), flush=True)
                page.set_viewport_size({'width': 1440, 'height': 1000})
                page.goto(origin + '/', wait_until='domcontentloaded')
                for label, expected in [('Node.js', 'npm install fullbleed'), ('Rust', f"fullbleed@={rust['engine']}"), ('C# / .NET', f"FullBleed.DotNet --version {dotnet['packageVersion']}")]:
                    page.locator('.tabbed-labels label').filter(has_text=re.compile('^' + re.escape(label) + '$')).click()
                    expect(page.locator('.tabbed-block:visible')).to_contain_text(expected)
                    checks.append('homepage ' + label + ' tab shows tested setup')
                check('homepage links current core release', page.get_by_role('link', name=f"{rust['engine']} release", exact=True).get_attribute('href').endswith('/v' + rust['engine']))
                check('no uncaught browser errors', not errors)
                record['ok'] = True
            except Exception:
                for label, action in [('screenshot', lambda: page.screenshot(path=str(out / 'failure.png'), timeout=5000)),
                                      ('DOM', lambda: (out / 'failure.html').write_text(page.content(), encoding='utf-8'))]:
                    try:
                        action()
                    except Exception as error:
                        record.setdefault('captureErrors', []).append(dict(artifact=label, error=str(error)))
                raise
            finally:
                context.close()
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        (out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(ok=record['ok'], checks=len(checks), downloads=len(downloads))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--origin')
    parser.add_argument('--expected-revision')
    main(parser.parse_args())
