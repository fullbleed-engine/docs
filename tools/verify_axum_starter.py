"""Build the exact Axum ZIP outside the checkout; verify HTTP, PDFs, and downloads."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path, PurePosixPath
import argparse
import copy
import io
import json
import os
import platform
import re
import shlex
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/axum-starter'


def digest(data):
    return sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'output/axum-verification')
    parser.add_argument('--archive', type=Path, default=ASSETS / 'project.zip')
    parser.add_argument('--manifest', type=Path, default=ASSETS / 'source.json')
    parser.add_argument('--sample-pdf', type=Path, default=ASSETS / 'invoice.pdf')
    parser.add_argument('--target-dir', type=Path, default=ROOT / 'examples/axum-pdf/target')
    parser.add_argument('--browser', choices=['chrome', 'chromium'])
    parser.add_argument('--toolchain', help='Installed rustup toolchain to use for the whole verification')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, commands, pdfs, responses = [], [], [], []
    report = dict(ok=False, platform=platform.system(), checks=checks, commands=commands,
                  pdfs=pdfs, responses=responses, versions={name: version(name) for name in
                  ['pypdf', 'pypdfium2', 'pillow']})
    env = {**os.environ, 'CARGO_TARGET_DIR': str(args.target_dir.resolve()),
           'PDF_BIND': '127.0.0.1:0'}
    if args.toolchain:
        env['RUSTUP_TOOLCHAIN'] = args.toolchain
    for key in ['RUST_MIN_STACK', 'RUSTFLAGS', 'CARGO_ENCODED_RUSTFLAGS']:
        env.pop(key, None)

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    def run(label, command, cwd, expected=0):
        print('Starting ' + label, flush=True)
        result = subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                                capture_output=True, text=True, encoding='utf-8', timeout=900)
        (out / (label + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
        (out / (label + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
        commands.append(dict(label=label, exit_code=result.returncode))
        check(label + ' exit status', result.returncode == expected if expected == 0 else result.returncode != 0)
        return result

    @contextmanager
    def server(label, executable, project):
        stdout = out / (label + '.stdout.txt')
        stderr = out / (label + '.stderr.txt')
        with stdout.open('w', encoding='utf-8') as output, stderr.open('w', encoding='utf-8') as errors:
            process = subprocess.Popen([str(executable)], cwd=project, env=env, stdout=output, stderr=errors)
            try:
                deadline = time.monotonic() + 30
                address = None
                while time.monotonic() < deadline:
                    log = stdout.read_text(encoding='utf-8')
                    found = re.search(r'Listening on (http://127\.0\.0\.1:\d+)', log)
                    if found:
                        address = found.group(1)
                        break
                    if process.poll() is not None:
                        raise RuntimeError(label + ' exited during startup: ' + stderr.read_text(encoding='utf-8'))
                    time.sleep(.05)
                check(label + ' printed its loopback address', address is not None)
                yield address
            finally:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    def request(address, payload=None, *, raw=None, content_type='application/json', path='/invoices/pdf'):
        if payload is None and raw is None:
            req = urllib.request.Request(address + path)
        else:
            body = raw if raw is not None else json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(address + path, data=body, headers={'Content-Type': content_type})
        try:
            response = urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()

    def pdf_response(label, result, number):
        status, headers, data = result
        normalized = {key.lower(): value for key, value in headers.items()}
        check(label + ' HTTP 200', status == 200)
        check(label + ' response headers', normalized['content-type'] == 'application/pdf'
              and normalized['content-disposition'] == f'attachment; filename="invoice-{number}.pdf"'
              and normalized['cache-control'] == 'private, no-store'
              and normalized['x-content-type-options'] == 'nosniff')
        check(label + ' PDF signature', data.startswith(b'%PDF-'))
        responses.append(dict(label=label, status=status, headers=normalized, sha256=digest(data)))
        return data

    def inspect(label, data, markers, *, multiple=False, letter=False):
        (out / (label + '.pdf')).write_bytes(data)
        reader = PdfReader(io.BytesIO(data), strict=True)
        page_texts = [page.extract_text() for page in reader.pages]
        text = '\n'.join(page_texts)
        (out / (label + '.txt')).write_text(text, encoding='utf-8')
        for index, page_text in enumerate(page_texts):
            check(f'{label} page {index + 1} correct footer count',
                  f'NORTHSTAR STUDIO / FICTIONAL SAMPLE {index + 1} / {len(reader.pages)}' in page_text)
            if re.search(r'Line \d{3}|Maximum item \d{3}', page_text):
                check(f'{label} page {index + 1} repeated table header',
                      all(word in page_text for word in ['DESCRIPTION', 'QTY', 'RATE', 'AMOUNT']))
        # Running footers interrupt extracted text when one paragraph spans pages.
        content_text = re.sub(r'NORTHSTAR STUDIO / FICTIONAL SAMPLE \d+ / \d+', '', text)
        compact = ''.join(content_text.split())
        check(label + ' expected text', all(''.join(marker.split()) in compact for marker in markers))
        check(label + ' page count', len(reader.pages) >= 1 if multiple is None else
              (len(reader.pages) > 1 if multiple else len(reader.pages) == 1))
        expected = (612, 792) if letter else (595.276, 841.89)
        check(label + ' paper size', all(abs(float(page.mediabox.width) - expected[0]) < .1
              and abs(float(page.mediabox.height) - expected[1]) < .1 for page in reader.pages))
        document = pdfium.PdfDocument(data)
        check(label + ' independent page count', len(document) == len(reader.pages))
        visible = 0
        for index in range(len(document)):
            page = document[index]
            textpage = page.get_textpage()
            width, height = page.get_size()
            outside = []
            for char in range(textpage.count_chars()):
                value = textpage.get_text_range(char, 1)
                if not value.strip():
                    continue
                left, bottom, right, top = textpage.get_charbox(char)
                if not (-1 <= left <= right <= width + 1 and -1 <= bottom <= top <= height + 1):
                    outside.append(dict(character=char, value=value, box=[left, bottom, right, top]))
                visible += 1
            check(f'{label} page {index + 1} all visible characters inside paper: {outside[:3]}', not outside)
            bitmap = page.render(scale=1)
            image = bitmap.to_pil()
            check(f'{label} page {index + 1} visible render',
                  image.convert('RGB').getextrema() != ((255, 255),) * 3)
            image.save(out / f'{label}-page-{index + 1}.png')
            textpage.close()
            page.close()
        document.close()
        pdfs.append(dict(label=label, pages=len(reader.pages), bytes=len(data), sha256=digest(data),
                         visible_characters=visible, text_sha256=digest(text.encode('utf-8'))))
        return text

    def browser_checks(address, expected_pdf, sample):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True,
                **({'channel': 'chrome'} if args.browser == 'chrome' else {}))
            report['browser'] = dict(channel=args.browser, version=browser.version, playwright=version('playwright'))
            context = browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 1100})
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(address, wait_until='networkidle')
            page.wait_for_function("!document.querySelector('#download').disabled")
            check('browser sample JSON matches distributed sample', json.loads(page.locator('#invoice').input_value()) == sample)
            with page.expect_download(timeout=60000) as capture:
                page.get_by_role('button', name='Download PDF').click()
            download = capture.value
            check('browser attachment filename', download.suggested_filename == 'invoice-NS-1042.pdf')
            path = out / 'browser-download.pdf'
            download.save_as(path)
            check('browser downloaded the same PDF as the HTTP client', path.read_bytes() == expected_pdf)
            page.wait_for_function("document.querySelector('#status').textContent.includes('Downloaded')")
            page.screenshot(path=out / 'browser-desktop.png', full_page=True)
            check('desktop form has no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            page.locator('#invoice').fill('{bad')
            page.get_by_role('button', name='Download PDF').click()
            page.wait_for_function("document.querySelector('#status').dataset.error === 'true'")
            check('malformed browser JSON shows an error', page.get_by_role('status').inner_text() != '')
            invalid = copy.deepcopy(sample)
            invalid['items'][0]['quantity'] = 0
            page.locator('#invoice').fill(json.dumps(invalid))
            page.get_by_role('button', name='Download PDF').click()
            page.wait_for_function("document.querySelector('#status').textContent.includes('quantity')")
            check('API validation appears in browser', page.locator('#status').get_attribute('data-error') == 'true')
            page.locator('#invoice').fill(json.dumps(sample, indent=2))
            with page.expect_download(timeout=60000) as capture:
                page.get_by_role('button', name='Download PDF').click()
            capture.value.save_as(out / 'browser-recovery.pdf')
            check('browser recovers after invalid input', (out / 'browser-recovery.pdf').read_bytes() == expected_pdf)
            page.wait_for_function("document.querySelector('#status').textContent.includes('Downloaded')")
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=out / 'browser-mobile.png', full_page=True)
            check('mobile form has no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
            check('browser has no uncaught script errors', not errors)
            context.close()
            browser.close()

    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        archive_bytes = args.archive.read_bytes()
        check('ZIP checksum and size', digest(archive_bytes) == manifest['zip_sha256']
              and len(archive_bytes) == manifest['zip_bytes'])
        check('expected archive root and public engine', manifest['prefix'] == 'fullbleed-axum-starter/'
              and manifest['engine'] == '2.5.19')
        report['source_zip_sha256'] = manifest['zip_sha256']
        with tempfile.TemporaryDirectory(prefix='fullbleed axum download ') as temporary:
            workspace = Path(temporary).resolve()
            check('fresh project is outside the checkout', not workspace.is_relative_to(ROOT))
            check('temporary workspace stays within the system temporary directory',
                  workspace.is_relative_to(Path(tempfile.gettempdir()).resolve()))
            with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
                names = [manifest['prefix'] + row['path'] for row in manifest['files']]
                check('ZIP contains exactly the manifest', sorted(archive.namelist()) == sorted(names))
                check('ZIP has confined regular-file paths', all(not PurePosixPath(name).is_absolute()
                      and '..' not in PurePosixPath(name).parts and '\\' not in name for name in names)
                      and all((item.external_attr >> 16) & 0o170000 == 0o100000 for item in archive.infolist()))
                for row in manifest['files']:
                    data = archive.read(manifest['prefix'] + row['path'])
                    check('source digest: ' + row['path'], digest(data) == row['sha256'] and len(data) == row['bytes'])
                archive.extractall(workspace)
            project = workspace / manifest['prefix']
            run('format', ['cargo', 'fmt', '--check'], project)
            run('unit-tests', ['cargo', 'test', '--release', '--locked'], project)
            run('build', ['cargo', 'build', '--release', '--locked'], project)
            metadata = json.loads(run('metadata', ['cargo', 'metadata', '--format-version', '1', '--locked'], project).stdout)
            core = next(package for package in metadata['packages'] if package['name'] == 'fullbleed')
            check('engine resolved from registry, without a local path',
                  core['version'] == manifest['engine'] and core['source'].startswith('registry+'))
            report['engine'] = core['version']
            report['rustc'] = run('rustc', ['rustc', '--version'], project).stdout.strip()
            executable = Path(metadata['target_directory']) / 'release' / ('fullbleed-axum-starter.exe' if os.name == 'nt' else 'fullbleed-axum-starter')
            sample = json.loads((project / 'sample.json').read_text(encoding='utf-8'))
            guide = (ROOT / 'docs/guides/axum-pdf.md').read_text(encoding='utf-8')
            guide_sample = re.search(r'```json\n(.*?)\n```', guide, re.S)
            check('guide JSON matches the distributed sample',
                  guide_sample is not None and json.loads(guide_sample.group(1)) == sample)
            with server('server', executable, project) as address:
                check('health endpoint responds', request(address, path='/health')[0::2] == (200, b'ok'))
                baseline = pdf_response('invoice', request(address, sample), sample['invoice_number'])
                inspect('invoice', baseline, ['Northstar', 'Maple & Finch', 'NS-1042', '$1,870.00'])
                check('published sample is exactly the generated invoice', args.sample_pdf.read_bytes() == baseline)
                curl_line = next(line for line in guide.splitlines() if line.startswith('curl --'))
                curl_command = shlex.split(curl_line)
                curl_command[0] = 'curl.exe' if os.name == 'nt' else 'curl'
                curl_command[curl_command.index('http://127.0.0.1:3000/invoices/pdf')] = address + '/invoices/pdf'
                curl_output = out / 'documented-curl.pdf'
                curl_command[curl_command.index('--output') + 1] = str(curl_output)
                run('documented-curl', curl_command, project)
                check('documented curl downloads the same PDF', curl_output.read_bytes() == baseline)
                check('repeated request is deterministic', pdf_response('repeat', request(address, sample), 'NS-1042') == baseline)
                literal = copy.deepcopy(sample)
                literal['customer']['name'] = '<b>Maple & Finch</b> {{ 7 * 7 }}'
                escaped = pdf_response('escaped', request(address, literal), 'NS-1042')
                inspect('escaped', escaped, [literal['customer']['name'], '$1,870.00'])
                many = copy.deepcopy(sample)
                many['items'] = [dict(description=f'Line {number:03d} / design deliverable', quantity=1,
                                      unit_price_cents=100) for number in range(1, 81)]
                data = pdf_response('pagination', request(address, many), 'NS-1042')
                text = inspect('pagination', data, [f'Line {number:03d}' for number in range(1, 81)] + ['$80.00'], multiple=True)
                check('every paginated line appears exactly once', all(text.count(f'Line {number:03d}') == 1 for number in range(1, 81)))
                maximum = copy.deepcopy(sample)
                maximum['invoice_number'] = 'MAX-' + 'X' * 28
                maximum['issued'] = 'Issued-' + '1' * 25
                maximum['due'] = 'Due-' + '2' * 28
                maximum['customer'] = dict(name='M' * 100, address_lines=[str(index) + 'A' * 99 for index in range(4)])
                maximum['note'] = 'N' * 600
                maximum['items'] = [dict(description=(f'Maximum item {number:03d}: ' + 'Detailed work item. ' * 12)[:200], quantity=10_000,
                                         unit_price_cents=100_000_000) for number in range(1, 201)]
                data = pdf_response('maximum', request(address, maximum), maximum['invoice_number'])
                text = inspect('maximum', data, [f'Maximum item {number:03d}' for number in range(1, 201)]
                               + ['M' * 100, 'N' * 600, '$2,000,000,000,000.00'], multiple=True)
                check('every maximum-size line appears once', all(text.count(f'Maximum item {number:03d}') == 1 for number in range(1, 201)))
                long_text = copy.deepcopy(sample)
                long_text['items'][0]['description'] = 'W' * 200
                long_text['note'] = 'N' * 600
                data = pdf_response('long-text', request(address, long_text), 'NS-1042')
                inspect('long-text', data, ['W' * 200, 'N' * 600, '$1,870.00'], multiple=None)
                invalids = []
                for label, field, value in [
                    ('unsafe-filename', 'invoice_number', 'bad\r\nheader'),
                    ('unknown-field', 'html', '<b>untrusted</b>'),
                    ('control-character', 'note', '\x00'),
                    ('note-too-long', 'note', 'N' * 601),
                    ('missing-glyph', 'note', chr(0x10ffff)),
                    ('too-many-items', 'items', maximum['items'] + maximum['items'][:1]),
                ]:
                    payload = copy.deepcopy(sample)
                    payload[field] = value
                    invalids.append((label, payload))
                for label, key, value in [('zero-quantity', 'quantity', 0), ('negative-price', 'unit_price_cents', -1),
                                          ('fractional-price', 'unit_price_cents', 1.5), ('excessive-price', 'unit_price_cents', 2**64 - 1)]:
                    payload = copy.deepcopy(sample)
                    payload['items'][0][key] = value
                    invalids.append((label, payload))
                for label, payload in invalids:
                    status, headers, data = request(address, payload)
                    check(label + ' rejects with JSON 422', status == 422 and isinstance(json.loads(data)['error'], str))
                    check(label + ' is not cached', headers.get('cache-control') == 'no-store')
                    responses.append(dict(label=label, status=status, error=json.loads(data)['error']))
                for label, raw, content_type, expected in [
                    ('malformed-json', b'{', 'application/json', 400),
                    ('wrong-content-type', b'{}', 'text/plain', 415),
                    ('oversized-body', b' ' * (64 * 1024 + 1), 'application/json', 413),
                ]:
                    status, _, data = request(address, raw=raw, content_type=content_type)
                    check(label + ' expected status and JSON error', status == expected and 'error' in json.loads(data))
                    responses.append(dict(label=label, status=status))
                check('recovery after failed requests', pdf_response('recovery', request(address, sample), 'NS-1042') == baseline)
                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(lambda _: request(address, many), range(8)))
                check('concurrent requests succeed or report bounded capacity', all(row[0] in [200, 503] for row in results)
                      and any(row[0] == 200 for row in results))
                for status, headers, data in results:
                    if status == 200:
                        check('concurrent output is deterministic', data == (out / 'pagination.pdf').read_bytes())
                    else:
                        check('busy response tells clients when to retry', headers.get('retry-after') == '1')
                report['concurrent_http'] = dict(requests=8, completed=sum(row[0] == 200 for row in results),
                                                busy=sum(row[0] == 503 for row in results),
                                                scope='Bounded functional probe; not throughput or capacity measurement')
                if args.browser:
                    browser_checks(address, baseline, sample)
            check('server logs do not contain synthetic customer or line-item data',
                  all(marker not in (out / 'server.stdout.txt').read_text(encoding='utf-8')
                      + (out / 'server.stderr.txt').read_text(encoding='utf-8')
                      for marker in ['Maple', 'Finch', 'Discovery', 'Maximum item']))
            check('server created no PDF files in its project', not list(project.rglob('*.pdf')))
            html_path, css_path = project / 'templates/invoice.html', project / 'templates/invoice.css'
            html, css = html_path.read_text(encoding='utf-8'), css_path.read_text(encoding='utf-8')
            html_path.write_text(html.replace('Northstar', 'Seabrook'), encoding='utf-8')
            css_path.write_text(css.replace('size: A4', 'size: Letter').replace('#17382e', '#1c355e'), encoding='utf-8')
            with server('edited-server', executable, project) as address:
                edited = pdf_response('edited-template', request(address, sample), 'NS-1042')
                inspect('edited-template', edited, ['Seabrook', '$1,870.00'], letter=True)
                check('template and stylesheet edit changes PDF', edited != baseline)
            html_path.write_text('<p>{{ invoice.no_such_field }}</p>', encoding='utf-8')
            with server('invalid-template-server', executable, project) as address:
                status, _, data = request(address, sample)
                check('unknown template variable fails without request data', status == 500
                      and 'error' in json.loads(data) and b'Maple' not in data)
            html_path.write_bytes(html.encode('utf-8'))
            css_path.write_bytes(css.encode('utf-8'))
            with server('restored-server', executable, project) as address:
                check('restored template recovers original PDF', pdf_response('restored', request(address, sample), 'NS-1042') == baseline)
            missing = workspace / 'missing-assets'
            missing.mkdir()
            run('missing-assets', [executable], missing, expected=1)
            for row in manifest['files']:
                check('project remains identical after verification: ' + row['path'],
                      digest((project / row['path']).read_bytes()) == row['sha256'])
        report['ok'] = True
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(ok=report['ok'], checks=len(checks), pdfs=len(pdfs), engine=report.get('engine'),
                          platform=report['platform'], evidence=str(out))), flush=True)


if __name__ == '__main__':
    main()
