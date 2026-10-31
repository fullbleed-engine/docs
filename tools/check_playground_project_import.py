"""Reopen actual playground downloads in fresh browser contexts and verify PDFs."""
import argparse
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import struct
import threading
from urllib.parse import unquote, urlsplit
import zipfile
import zlib

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader
from playground_local_files import fixture


def older_project(source, target):
    """Change only same-length engine metadata, refreshing the ZIP CRC."""
    data = bytearray(source.read_bytes())
    with zipfile.ZipFile(source) as archive:
        info = archive.getinfo('project.json')
        content = archive.read(info)
    manifest = json.loads(content)
    old_version = manifest['engine']['version']
    previous = old_version[:-1] + ('0' if old_version[-1] != '0' else '1')
    changed = content.replace(f'"version": "{old_version}"'.encode(), f'"version": "{previous}"'.encode(), 1)
    assert len(changed) == len(content) and changed != content
    start = info.header_offset + 30 + len(info.filename.encode('utf-8'))
    data[start:start + len(changed)] = changed
    crc = zlib.crc32(changed)
    struct.pack_into('<I', data, info.header_offset + 14, crc)
    directory = struct.unpack_from('<I', data, len(data) - 6)[0]
    while struct.unpack_from('<I', data, directory)[0] == 0x02014b50:
        name_size, extra_size, comment_size = struct.unpack_from('<HHH', data, directory + 28)
        name = data[directory + 46:directory + 46 + name_size].decode('utf-8')
        if name == 'project.json':
            struct.pack_into('<I', data, directory + 16, crc)
            break
        directory += 46 + name_size + extra_size + comment_size
    else:
        raise AssertionError('Missing project manifest directory entry')
    target.write_bytes(data)
    return previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--site', type=Path)
    source.add_argument('--url')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--browser', choices=['chrome', 'firefox', 'webkit'], default='chrome')
    parser.add_argument('--legacy-zip', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    specimen = fixture(out / 'selected-files')
    checks, errors, requests, documents = [], [], [], []
    server = None
    prefix = '/nested/docs/'
    url = args.url
    if args.site:
        root = args.site.resolve()

        class Handler(SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(root), **kw)

            def translate_path(self, path):
                name = unquote(urlsplit(path).path)
                if not name.startswith(prefix):
                    return str(root / 'not-found')
                resolved = (root / name[len(prefix):]).resolve()
                return str(resolved if resolved.is_relative_to(root) else root / 'not-found')

            def log_message(self, *a):
                pass

            def copyfile(self, source, outputfile):
                try:
                    super().copyfile(source, outputfile)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{server.server_port}{prefix}playground/'

    def check(name, passed):
        assert passed, name
        checks.append(name)
        print(name + ': passed', flush=True)

    def ready(page):
        expect(page.locator('#pg-download')).to_have_attribute('href', re.compile(r'^blob:'), timeout=120000)
        expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')

    def download(page, selector, name):
        with page.expect_download() as item:
            page.locator(selector).click()
        path = out / name
        item.value.save_as(path)
        return path

    def record_pdf(page, name):
        path = download(page, '#pg-download', name + '.pdf')
        reader = PdfReader(path)
        check(name + ': restored text is in the PDF', len(reader.pages) == 1 and 'LOCAL IMPORT CAFÉ 012345' in reader.pages[0].extract_text())
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        documents.append({'path': path.name, 'sha256': digest})
        return digest

    def snapshot(page):
        return page.evaluate('''() => ({html: document.querySelector('#pg-html').value,
          css: document.querySelector('#pg-css').value, language: document.querySelector('#pg-project-language').value,
          assets: document.querySelector('#pg-assets').textContent, pdf: document.querySelector('#pg-download').href,
          preview: document.querySelector('#pg-preview').src})''')

    def open_project(page, path, keyboard=False):
        button = page.locator('#pg-open-project')
        with page.expect_file_chooser() as chooser:
            if keyboard:
                button.focus()
                button.press('Enter')
            else:
                button.click()
        chooser.value.set_files(str(path))
        expect(page.locator('#pg-status')).to_contain_text('Project opened locally.', timeout=30000)
        expect(button).to_be_enabled()

    browser_version = None
    ok = False
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel='chrome') if args.browser == 'chrome' else getattr(pw, args.browser).launch()
            browser_version = browser.version

            def fresh():
                context = browser.new_context(viewport={'width': 1440, 'height': 1000}, accept_downloads=True)
                page = context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda request: requests.append({'url': request.url, 'method': request.method, 'body': request.post_data}))
                page.goto(url, wait_until='domcontentloaded')
                ready(page)
                return context, page

            context, page = fresh()
            selected = out / 'selected-files'
            page.locator('#pg-files').set_input_files([str(selected / 'document.html'), str(selected / 'brand.css'), *map(str, sorted((selected / 'assets').iterdir()))])
            expect(page.locator('#pg-status')).to_contain_text('Files opened locally.')
            page.locator('#pg-render').click()
            ready(page)
            original_pdf = record_pdf(page, 'before-saving')
            projects = {}
            for language in ['python', 'node']:
                page.locator('#pg-project-language').select_option(language)
                projects[language] = download(page, '#pg-project', language + '-project.zip')
            context.close()

            for language, project in projects.items():
                context, page = fresh()
                previous_asset = out / (language + '-previous.txt')
                previous_asset.write_text('An asset from the previous document.', encoding='utf-8')
                page.locator('#pg-files').set_input_files(str(previous_asset))
                expect(page.locator('#pg-asset-count')).to_have_text('1 local asset')
                open_project(page, project, keyboard=True)
                check(language + ': exact source and language restored in a fresh tab', page.locator('#pg-html').input_value() == specimen['html']
                      and page.locator('#pg-css').input_value() == specimen['css'] and page.locator('#pg-project-language').input_value() == language)
                check(language + ': custom images, font and license restored', page.locator('#pg-assets code').all_text_contents() == ['assets/' + asset['name'] for asset in specimen['assets']])
                check(language + ': stale example PDF is cleared before rendering', page.locator('#pg-download').get_attribute('href') is None)
                page.locator('#pg-render').click()
                ready(page)
                check(language + ': restored PDF is byte-identical', record_pdf(page, language + '-reopened') == original_pdf)
                replay = download(page, '#pg-project', language + '-reexported.zip')
                check(language + ': reexported ZIP is byte-identical', replay.read_bytes() == project.read_bytes())
                check(language + ': authored scripts have not executed', page.evaluate('window.__localDocumentExecuted === undefined'))
                saved = snapshot(page)
                page.locator('#pg-open-project').focus()
                with page.expect_file_chooser() as canceled:
                    page.locator('#pg-open-project').press('Space')
                canceled.value.set_files([])
                check(language + ': canceling the keyboard-opened picker preserves work', snapshot(page) == saved)
                bad = out / (language + '-damaged.zip')
                data = bytearray(project.read_bytes())
                data[45] ^= 1
                bad.write_bytes(data)
                page.locator('#pg-project-file').set_input_files(str(bad))
                expect(page.locator('#pg-status')).to_contain_text('damaged')
                check(language + ': invalid project preserves source, assets and rendered PDF', snapshot(page) == saved)
                # Editing remains available while the file is being read; newer edits win.
                page.evaluate('''() => {
                  const original = File.prototype.arrayBuffer;
                  File.prototype.arrayBuffer = async function() {
                    await new Promise(resolve => { window.__releaseProjectRead = resolve; });
                    return original.call(this);
                  };
                  window.__restoreProjectRead = () => { File.prototype.arrayBuffer = original; };
                }''')
                page.locator('#pg-project-file').set_input_files(str(project))
                page.wait_for_function('typeof window.__releaseProjectRead === "function"')
                edited = specimen['html'] + '\n<!-- edit during import -->'
                page.locator('#pg-html').fill(edited)
                page.evaluate('window.__releaseProjectRead(); window.__restoreProjectRead()')
                expect(page.locator('#pg-status')).to_contain_text('document changed while the project was opening')
                check(language + ': edits made during import survive', page.locator('#pg-html').input_value() == edited)
                open_project(page, project)
                expect(page.locator('#pg-html')).to_have_value(specimen['html'])
                older = out / (language + '-older.zip')
                version = older_project(project, older)
                open_project(page, older)
                expect(page.locator('#pg-status')).to_contain_text('saved with Fullbleed ' + version)
                check(language + ': older engine notice appears before rendering', page.locator('#pg-download').get_attribute('href') is None)
                page.locator('#pg-render').click()
                ready(page)
                check(language + ': older project uses the current preview engine', record_pdf(page, language + '-older-preview') == original_pdf)
                for width in [1440, 390, 320]:
                    page.set_viewport_size({'width': width, 'height': 1000})
                    check(f'{language}: no horizontal overflow at {width}px', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                    expect(page.locator('#pg-open-project')).to_be_visible()
                    page.locator('#playground').screenshot(path=str(out / f'{language}-{width}.png'))
                context.close()

            if args.legacy_zip:
                context, page = fresh()
                open_project(page, args.legacy_zip)
                with zipfile.ZipFile(args.legacy_zip) as archive:
                    check('ZIP downloaded before this feature still restores', page.locator('#pg-html').input_value() == archive.read('input.html').decode('utf-8')
                          and page.locator('#pg-css').input_value() == archive.read('style.css').decode('utf-8'))
                page.locator('#pg-render').click()
                ready(page)
                context.close()
            browser.close()
        check('no uncaught browser errors', errors == [])
        check('no document uploads', all(request['method'] == 'GET' and request['body'] is None for request in requests))
        ok = True
    finally:
        if server:
            server.shutdown()
            server.server_close()
        record = {'ok': ok, 'at': datetime.now(timezone.utc).isoformat(), 'browser': args.browser, 'browserVersion': browser_version,
                  'url': url, 'checks': checks, 'errors': errors, 'requests': requests, 'documents': documents}
        (out / 'verification.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'passed': len(checks), 'browser': args.browser, 'out': str(out)}))


if __name__ == '__main__':
    main()
