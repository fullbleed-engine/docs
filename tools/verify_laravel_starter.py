"""Exercise the exact Laravel download with real SQLite queues, HTTP, PDFs and Chrome."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import argparse
import copy
import io
import json
import os
import platform
import runpy
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/laravel-starter'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'output/laravel-verification')
    parser.add_argument('--php', default='php')
    parser.add_argument('--composer', default='composer', help='Composer executable or .phar path')
    parser.add_argument('--browser', choices=['chrome', 'chromium'])
    parser.add_argument('--refresh-assets', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, pdfs, commands = [], [], []
    report = dict(schema='fullbleed.laravel-verification.v1', ok=False, platform=platform.system(),
                  checks=checks, pdfs=pdfs, commands=commands,
                  versions={n: version(n) for n in ['fullbleed', 'pypdf', 'pypdfium2', 'Pillow']})
    php = shutil.which(args.php) or str(Path(args.php).resolve())
    env = {**os.environ, 'PATH': str(Path(php).parent) + os.pathsep + os.environ['PATH'],
           'FULLBLEED_PYTHON': sys.executable, 'PDF_SECONDARY_API_KEY': secrets.token_hex(32)}
    secondary = env['PDF_SECONDARY_API_KEY']
    # An unrelated shell's Laravel credentials/configuration must not enter this test.
    for key in ['APP_KEY', 'APP_ENV', 'APP_DEBUG', 'APP_URL', 'PDF_API_KEY', 'PDF_RETENTION_HOURS']:
        env.pop(key, None)
    project = out / 'fullbleed-laravel-starter'
    database = project / 'database/database.sqlite'

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    def run(label, command, extra=None, expected=0):
        print('Starting ' + label, flush=True)
        result = subprocess.run(list(map(str, command)), cwd=project, env={**env, **(extra or {})},
                                capture_output=True, timeout=240)
        (out / (label + '.stdout.txt')).write_bytes(result.stdout)
        (out / (label + '.stderr.txt')).write_bytes(result.stderr)
        commands.append(dict(label=label, exit_code=result.returncode))
        check(label + ' exit status', result.returncode == expected)
        return result.stdout

    def sql(query, parameters=()):
        with sqlite3.connect(database, timeout=10) as connection:
            return connection.execute(query, parameters).fetchall()

    @contextmanager
    def server(label):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
        address = f'http://127.0.0.1:{port}'
        router = project / 'vendor/laravel/framework/src/Illuminate/Foundation/resources/server.php'
        with (out / (label + '.log')).open('wb') as log:
            process = subprocess.Popen([php, '-S', f'127.0.0.1:{port}', str(router)],
                                       cwd=project / 'public', env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline:
                    try:
                        with urllib.request.urlopen(address, timeout=1) as response:
                            if response.status == 200: break
                    except (OSError, urllib.error.URLError):
                        if process.poll() is not None: raise RuntimeError('PHP server exited')
                        time.sleep(.1)
                else: raise RuntimeError('PHP server startup timeout')
                yield address
            finally:
                process.terminate()
                process.wait(timeout=10)

    def request(address, path='/api/documents', *, data=None, raw=None, method=None,
                key=None, idempotency='sample-request-001', content_type='application/json'):
        headers = {'Accept': 'application/json', 'Content-Type': content_type, 'Idempotency-Key': idempotency}
        if key is not None: headers['Authorization'] = 'Bearer ' + key
        if data is not None: raw = json.dumps(data, ensure_ascii=False).encode()
        req = urllib.request.Request(address + path, data=raw, headers=headers, method=method)
        try: response = urllib.request.urlopen(req, timeout=40)
        except urllib.error.HTTPError as error: response = error
        with response:
            body = response.read()
            return response.status, dict(response.headers), body

    def worker(label, extra=None, once=False):
        return run(label, [php, 'artisan', 'queue:work', '--queue=pdf', '--sleep=1', '--timeout=45',
                           '--once' if once else '--stop-when-empty'], extra)

    def inspect_pdf(label, data, tokens, minimum=1):
        check(label + ' is PDF', data.startswith(b'%PDF-'))
        reader = PdfReader(io.BytesIO(data))
        text = '\n'.join(p.extract_text() or '' for p in reader.pages)
        check(label + ' page count', minimum <= len(reader.pages) <= 25)
        for token in tokens: check(label + ' text: ' + token, token in text)
        path = out / (label + '.pdf')
        path.write_bytes(data)
        with pdfium.PdfDocument(data) as doc:
            for index in range(len(doc)):
                page = doc[index]
                textpage = page.get_textpage()
                width, height = page.get_size()
                for char in range(textpage.count_chars()):
                    character = textpage.get_text_range(char, 1)
                    if not character.strip(): continue
                    left, bottom, right, top = textpage.get_charbox(char)
                    if not (-1 <= left <= right <= width + 1 and -1 <= bottom <= top <= height + 1):
                        raise AssertionError(f'{label} glyph outside page {index + 1}')
                if index in {0, len(doc) - 1}:
                    page.render(scale=1.4).to_pil().save(out / f'{label}-pdfium-{index + 1}.png')
            check(label + ' glyph bounds on every page', True)
        pdfs.append(dict(label=label, pages=len(reader.pages), bytes=len(data), sha256=sha256(data).hexdigest()))
        return text

    try:
        archive = (ASSETS / 'project.zip').read_bytes()
        manifest = json.loads((ASSETS / 'source.json').read_text(encoding='utf-8'))
        report['archive_sha256'] = sha256(archive).hexdigest()
        check('archive hash matches manifest', report['archive_sha256'] == manifest['zip_sha256'])
        check('installed Fullbleed matches starter pin', version('fullbleed') == manifest['engine'])
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            check('archive has exactly the manifest files', set(zipped.namelist()) == {manifest['prefix'] + f['path'] for f in manifest['files']})
            for item in manifest['files']:
                name = manifest['prefix'] + item['path']
                check('source hash ' + item['path'], sha256(zipped.read(name)).hexdigest() == item['sha256'])
                check('safe archive path ' + item['path'], (out / name).resolve().is_relative_to(out))
            check('no private configuration or dependencies in ZIP', not any('/vendor/' in n or n.endswith('/.env') or '.sqlite' in n for n in zipped.namelist()))
            zipped.extractall(out)
        composer = [php, args.composer] if args.composer.endswith('.phar') else [args.composer]
        run('composer-install', [*composer, 'install', '--no-interaction', '--prefer-dist', '--no-progress', '--no-ansi'])
        run('composer-validate', [*composer, 'validate', '--strict', '--no-check-publish'])
        run('composer-audit', [*composer, 'audit', '--locked', '--format=json'])
        report['versions']['php'] = run('php-version', [php, '-r', 'echo PHP_VERSION;']).decode()
        report['versions']['laravel'] = run('laravel-version', [php, 'artisan', '--version']).decode().strip()
        run('setup', [php, 'setup.php', sys.executable])
        original_env = (project / '.env').read_bytes()
        run('setup-repeat', [php, 'setup.php', sys.executable])
        check('setup preserves existing credentials', (project / '.env').read_bytes() == original_env)
        primary = next(line.split('=', 1)[1] for line in original_env.decode().splitlines() if line.startswith('PDF_API_KEY='))
        run('migrate', [php, 'artisan', 'migrate', '--force'])
        sample = json.loads((project / 'sample.json').read_text(encoding='utf-8'))
        with server('http') as address, server('concurrent-http') as second_address:
            for label, kwargs, expected in [
                ('missing key', dict(data=sample), 401),
                ('wrong key', dict(data=sample, key='wrong'), 401),
                ('malformed JSON', dict(raw=b'{broken', key=primary), 400),
                ('wrong content type', dict(data=sample, key=primary, content_type='text/plain'), 415),
                ('oversized body', dict(raw=b' ' * 65537, key=primary), 413),
                ('missing idempotency', dict(data=sample, key=primary, idempotency=''), 422),
                ('unknown input field', dict(data={**sample, 'html': '<p>no</p>'}, key=primary), 422),
                ('empty items', dict(data={**sample, 'items': []}, key=primary), 422),
                ('too many items', dict(data={**sample, 'items': sample['items'] * 26}, key=primary), 422),
                ('invalid date', dict(data={**sample, 'issued': '2026-02-30'}, key=primary), 422),
                ('non-object body', dict(raw=b'[]', key=primary), 422),
            ]:
                check(label, request(address, **kwargs)[0] == expected)
            for field, value in [('unit_price', 9.99), ('quantity', '2'), ('quantity', 0), ('unit_price', '01.00')]:
                bad = copy.deepcopy(sample); bad['items'][0][field] = value
                check('reject invalid ' + field + ' ' + str(value), request(address, data=bad, key=primary)[0] == 422)
            check('invalid requests did not create documents or jobs', sql('select count(*) from documents')[0][0] == sql('select count(*) from jobs')[0][0] == 0)
            status, _, body = request(address, data=sample, key=primary)
            record = json.loads(body); docid = record['id']; status_path = record['status_url']
            check('request returns queued 202 before worker', status == 202 and record['state'] == 'queued')
            check('no PDF before worker', not (project / f'storage/app/private/documents/{docid}.pdf').exists())
            encrypted = sql('select payload from documents')[0][0]
            queue_payload = sql('select payload from jobs')[0][0]
            check('invoice encrypted at rest', sample['customer'] not in encrypted and not encrypted.startswith('{'))
            check('queue contains ID without invoice fields', docid in queue_payload and sample['customer'] not in queue_payload and sample['number'] not in queue_payload)
            for suffix in ['', '/download']:
                check('different owner cannot read ' + suffix, request(address, status_path + suffix, key=secondary)[0] == 404)
            check('download before readiness rejected', request(address, status_path + '/download', key=primary)[0] == 409)
            for data in [sample, dict(reversed(list(sample.items())))]:
                code, _, body = request(address, data=data, key=primary)
                check('idempotency reuses queued job', code == 202 and json.loads(body)['id'] == docid)
            check('one queued job for repeated key', sql('select count(*) from jobs')[0][0] == 1)
            check('changed data conflicts', request(address, data={**sample, 'customer': 'Someone else'}, key=primary)[0] == 409)
            worker('sample-worker')
            record = json.loads(request(address, status_path, key=primary)[2])
            check('worker marks document ready', record['state'] == 'ready' and record['attempts'] == 1)
            code, headers, sample_pdf = request(address, record['download_url'], key=primary)
            check('private PDF response', code == 200 and headers['Content-Type'] == 'application/pdf' and 'no-store' in headers['Cache-Control'] and 'attachment' in headers['Content-Disposition'] and headers['X-Content-Type-Options'] == 'nosniff')
            inspect_pdf('invoice', sample_pdf, ['INVOICE', sample['number'], sample['customer'], '5,400.00'])
            check('ready duplicate is 200', request(address, data=sample, key=primary)[0] == 200)
            for path in [f'/storage/documents/{docid}.pdf', '/.env', '/database/database.sqlite']:
                check('private path unavailable ' + path, request(address, path, key=primary)[0] == 404)

            # Replay an actual database queue payload after completion.
            pdf_path = project / f'storage/app/private/documents/{docid}.pdf'
            before = pdf_path.stat().st_mtime_ns
            sql('insert into jobs(queue,payload,attempts,available_at,created_at) values(?,?,?,?,?)', ('pdf', queue_payload, 0, 0, int(time.time())))
            worker('completed-replay')
            check('completed replay did not rewrite PDF', pdf_path.stat().st_mtime_ns == before)
            second_id = json.loads(request(address, data=sample, key=primary, idempotency='deterministic-repeat')[2])['id']
            worker('deterministic-worker')
            check('independent render is byte identical', request(address, f'/api/documents/{second_id}/download', key=primary)[2] == sample_pdf)

            long = copy.deepcopy(sample)
            long['number'] = 'N' * 40; long['customer'] = 'W' * 80
            long['items'] = [dict(description=f'Line {n:03d} '+('Detailed deliverable ' * 7), quantity=100, unit_price='999999.99') for n in range(1, 101)]
            long_id = json.loads(request(address, data=long, key=primary, idempotency='large-invoice-test')[2])['id']
            worker('long-worker')
            long_pdf = request(address, f'/api/documents/{long_id}/download', key=primary)[2]
            long_text = inspect_pdf('long-invoice', long_pdf, ['Line 001', 'Line 100', '9,999,999,900.00'], minimum=2)
            check('all 100 lines survive pagination', all(f'Line {n:03d}' in long_text for n in range(1, 101)))
            escaped = copy.deepcopy(sample); escaped['customer'] = '<b>Literal & safe</b>'
            escaped_id = json.loads(request(address, data=escaped, key=primary, idempotency='escaped-data-test')[2])['id']
            worker('escaped-worker')
            inspect_pdf('escaped-invoice', request(address, f'/api/documents/{escaped_id}/download', key=primary)[2], [escaped['customer']])

            # Independent PHP servers contend on the same SQLite DB.
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [pool.submit(request, host, data=sample, key=primary, idempotency='concurrent-repeat') for host in [address, second_address] * 2]
                responses = [future.result() for future in futures]
            ids = {json.loads(body).get('id') for _, _, body in responses}
            check('concurrent submissions share one document', all(code == 202 for code, _, _ in responses) and len(ids) == 1 and None not in ids)
            check('concurrent submissions enqueue once', sql('select count(*) from jobs')[0][0] == 1)
            worker('concurrent-worker')

            # A broken dispatch must roll back the new document too.
            prior_count = sql('select count(*) from documents')[0][0]
            sql('alter table jobs rename to unavailable_jobs')
            try:
                check('dispatch failure is generic server error', request(address, data=sample, key=primary, idempotency='rollback-test')[0] == 500)
                check('dispatch failure rolls back document', sql('select count(*) from documents')[0][0] == prior_count)
            finally: sql('alter table unavailable_jobs rename to jobs')

            # Real failure/release attempts, then operator retry with working renderer.
            # Reset only rate counters to keep this deliberate test burst below no artificial limits.
            sql('delete from cache')
            failed_id = json.loads(request(address, data=sample, key=primary, idempotency='failed-render-test')[2])['id']
            for attempt in range(1, 4):
                sql('update jobs set available_at=0')
                worker(f'failure-attempt-{attempt}', {'FULLBLEED_PYTHON': str(project / 'missing-python')}, once=True)
                row = sql('select state,attempts from documents where id=?', (failed_id,))[0]
                check(f'failure attempt {attempt} state', row == ('failed' if attempt == 3 else 'queued', attempt))
            check('failed job retained for operator retry', sql('select count(*) from failed_jobs')[0][0] == 1)
            run('operator-retry', [php, 'artisan', 'queue:retry', 'all'])
            worker('recovery-worker')
            check('operator retry recovers same document', json.loads(request(address, f'/api/documents/{failed_id}', key=primary)[2])['state'] == 'ready')

            # Kill an actually stalled renderer at the configured subprocess deadline.
            timeout_id = json.loads(request(address, data=sample, key=primary, idempotency='timeout-render-test')[2])['id']
            renderer = project / 'renderer/render.py'; original_renderer = renderer.read_bytes()
            renderer.write_bytes(b'import time\ntime.sleep(90)\n' + original_renderer)
            try:
                began = time.monotonic()
                worker('timeout-worker', once=True)
                elapsed = time.monotonic() - began
                check('subprocess deadline terminates stalled renderer', 29 <= elapsed < 44)
                check('timeout leaves a retryable job without PDF', sql('select state from documents where id=?', (timeout_id,))[0][0] == 'queued' and not (project / f'storage/app/private/documents/{timeout_id}.pdf').exists())
            finally: renderer.write_bytes(original_renderer)
            sql('update jobs set available_at=0')
            worker('timeout-recovery-worker')
            check('timed-out job recovers', json.loads(request(address, f'/api/documents/{timeout_id}', key=primary)[2])['state'] == 'ready')

            queued_id = json.loads(request(address, data=sample, key=primary, idempotency='expired-queued-test')[2])['id']
            sql("update documents set expires_at='2000-01-01 00:00:00' where id in (?,?)", (docid, queued_id))
            check('expired PDF unavailable before pruning', request(address, status_path + '/download', key=primary)[0] == 410)
            run('prune', [php, 'artisan', 'documents:prune'])
            check('expired file deleted', not pdf_path.exists())
            check('expired data deleted', sql('select count(*) from documents where id in (?,?)', (docid, queued_id))[0][0] == 0)
            worker('expired-queue-worker')
            check('expired queued job cannot recreate document', sql('select count(*) from documents where id=?', (queued_id,))[0][0] == 0)

            late_id = json.loads(request(address, data=sample, key=primary, idempotency='late-render-test')[2])['id']
            renderer = project / 'renderer/render.py'; original_renderer = renderer.read_bytes()
            started, release = out / 'render-started', out / 'render-release'
            gate = f'import time\nfrom pathlib import Path\nPath({str(started)!r}).touch()\nwhile not Path({str(release)!r}).exists(): time.sleep(.05)\n'
            renderer.write_bytes(gate.encode() + original_renderer)
            with (out / 'late-worker.log').open('wb') as log:
                process = subprocess.Popen([php, 'artisan', 'queue:work', '--queue=pdf', '--once'], cwd=project, env=env, stdout=log, stderr=log)
                try:
                    deadline = time.monotonic() + 15
                    while not started.exists() and time.monotonic() < deadline: time.sleep(.05)
                    check('late render actually started', started.exists())
                    sql("update documents set expires_at='2000-01-01 00:00:00' where id=?", (late_id,))
                    run('prune-in-flight', [php, 'artisan', 'documents:prune'])
                    release.touch(); check('late worker exits', process.wait(timeout=30) == 0)
                    check('late render cannot restore pruned PDF', not (project / f'storage/app/private/documents/{late_id}.pdf').exists())
                    check('no temporary PDFs remain', not list((project / 'storage/app/private/documents').glob('*.tmp')))
                finally:
                    release.touch()
                    if process.poll() is None: process.terminate(); process.wait(timeout=10)
                    renderer.write_bytes(original_renderer)

            if args.browser:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(channel='chrome' if args.browser == 'chrome' else None, headless=True)
                    report['versions']['browser'] = browser.version
                    context = browser.new_context(accept_downloads=True)
                    page = context.new_page(); errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(address)
                    for width in [1440, 390, 320]:
                        page.set_viewport_size({'width': width, 'height': 1000})
                        check(f'browser fits {width}px viewport', page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
                        page.screenshot(path=str(out / f'studio-{width}.png'), full_page=True)
                    page.set_viewport_size({'width': 1440, 'height': 1000})
                    page.get_by_label('Service key').fill(primary)
                    page.get_by_role('button', name='Queue sample invoice').click()
                    page.wait_for_function("document.querySelector('#accepted').classList.contains('done')")
                    worker('browser-worker')
                    page.get_by_text('Your invoice is ready.', exact=True).wait_for()
                    with page.expect_download() as download:
                        page.get_by_role('button', name='Download PDF').click()
                    path = out / 'browser-invoice.pdf'; download.value.save_as(path)
                    check('real browser PDF equals API specimen', path.read_bytes() == sample_pdf)
                    page.get_by_label('Service key').fill('')
                    page.screenshot(path=str(out / 'studio-ready.png'), full_page=True)
                    check('browser has no JavaScript errors', not errors)
                    check('browser stores no service key', page.evaluate('localStorage.length + sessionStorage.length') == 0)
                    context.close(); browser.close()

        boot = "require 'vendor/autoload.php'; $app=require 'bootstrap/app.php'; $app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap(); "
        html = run('blade-render', [php, '-r', boot + "echo view('invoice', App\\Support\\Invoice::viewData(json_decode(file_get_contents('sample.json'),true)))->render();"])
        (out / 'invoice.html').write_bytes(html)
        renderer = runpy.run_path(str(project / 'renderer/render.py'))
        preview_dir = out / 'native-preview'
        renderer['engine']('Invoice ' + sample['number']).render_image_pages_to_dir(html.decode(), renderer['CSS'], str(preview_dir), dpi=144, stem='invoice')
        previews = list(preview_dir.glob('*.png'))
        check('native preview produced', len(previews) == 1)
        logs = '\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in (project / 'storage/logs').glob('*.log'))
        check('application logs exclude service keys and invoice customer', primary not in logs and secondary not in logs and sample['customer'] not in logs)
        if not args.refresh_assets:
            check('matches published sample PDF', (ASSETS / 'invoice.pdf').read_bytes() == sample_pdf)
        report['ok'] = True
        report['check_count'] = len(checks)
        if args.refresh_assets:
            (ASSETS / 'invoice.pdf').write_bytes(sample_pdf)
            shutil.copyfile(previews[0], ASSETS / 'invoice.png')
            (ASSETS / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(json.dumps(dict(ok=True, checks=len(checks), pdfs=len(pdfs), out=str(out))))
    finally:
        report['check_count'] = len(checks)
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
