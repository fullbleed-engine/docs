"""Check a generated launcher's source payload without calling StackBlitz."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import parse_qs
import zipfile

from playwright.sync_api import sync_playwright, expect
from online_starter import STARTERS

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('starter', choices=list(STARTERS))
parser.add_argument('--out', type=Path)
args = parser.parse_args()
flavor = args.starter
out = (args.out or ROOT / f'output/{flavor}-online').resolve()
out.mkdir(parents=True, exist_ok=False)
assets = ROOT / f'docs/assets/{flavor}-starter'
manifest = json.loads((assets / 'source.json').read_text(encoding='utf-8'))
prefix = f'fullbleed-{flavor}-starter/'
with zipfile.ZipFile(assets / 'project.zip') as archive:
    expected = {f'project[files][{name.removeprefix(prefix)}]': archive.read(name).decode('utf-8') for name in archive.namelist()}
title = f'Fullbleed {STARTERS[flavor]["name"]} PDF starter'
expected.update({'project[title]': title,
    'project[description]': 'Editable HTML/CSS templates and local PDF previews. MIT licensed; fictional sample data.',
    'project[template]': 'node', 'project[dependencies]': '{}'})

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs): super().__init__(*args, directory=str(ROOT / 'docs/assets'), **kwargs)
    def log_message(self, *args): pass

server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
entry = STARTERS[flavor]['entry']
action = f'https://stackblitz.com/run?file={entry}&startScript=dev'
submitted = []
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True, java_script_enabled=False)
        try:
            def capture(route):
                request = route.request
                assert request.url == action and request.method == 'POST'
                values = parse_qs(request.post_data, keep_blank_values=True)
                assert all(len(items) == 1 for items in values.values())
                # HTML form serialization uses CRLF; compare source text as LF.
                actual = {key: items[0].replace('\r\n', '\n') for key, items in values.items()}
                assert actual == expected, 'Submitted project differs from the downloadable ZIP'
                submitted.append({'fields': len(actual), 'source_files': len(manifest['files'])})
                route.fulfill(status=200, content_type='text/plain', body='Payload checked locally; no project was created.')
            context.route('https://stackblitz.com/**', capture)
            page = context.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/{flavor}-starter/edit-online.html', wait_until='networkidle')
            expect(page.locator('footer')).to_contain_text(manifest['package_version'])
            expect(page.locator('footer')).to_contain_text(manifest['engine_version'])
            button = page.get_by_role('button', name='Open in StackBlitz', exact=True)
            for width, height in [(1440,1000), (390,844), (320,760)]:
                page.set_viewport_size({'width': width, 'height': height})
                expect(button).to_be_visible()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                page.screenshot(path=str(out / f'width-{width}.png'), full_page=True)
            with page.expect_download() as event:
                page.get_by_role('link', name='Download the complete project', exact=True).click()
            download = out / 'project.zip'
            event.value.save_as(download)
            assert download.read_bytes() == (assets / 'project.zip').read_bytes()
            button.focus()
            with page.expect_navigation(wait_until='domcontentloaded'):
                page.keyboard.press('Enter')
            assert len(submitted) == 1
            record = {'ok': True, 'checked_at': datetime.now(timezone.utc).isoformat(), 'browser': browser.version,
                'starter': flavor,
                'package': manifest['package_version'], 'engine': manifest['engine_version'], 'source_commit': manifest['source_commit'],
                'source_files': len(manifest['files']), 'zip_sha256': sha256(download.read_bytes()).hexdigest(),
                'launcher_sha256': sha256((assets / 'edit-online.html').read_bytes()).hexdigest(),
                'viewport_widths': [1440,390,320], 'javascript_disabled': True, 'keyboard_submission': True,
                'submitted_source_matches_zip': True,
                'scope': 'Actual browser form serialization intercepted locally; all source fields, ZIP download, keyboard submission and responsive layout checked. Does not test StackBlitz availability or project startup.'}
            (out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(record))
        finally:
            context.close()
            browser.close()
finally:
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)
