"""Verify the downloaded n8n kit through actual HTTP and Docker workflow execution."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import argparse
import copy
import json
import os
import re
import socket
import subprocess
import sys
import time
import uuid
import zipfile

from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/n8n-starter'
parser = argparse.ArgumentParser()
parser.add_argument('--out', type=Path, default=ROOT / 'output/n8n-verification')
parser.add_argument('--archive', type=Path, default=ASSETS / 'project.zip')
parser.add_argument('--manifest', type=Path, default=ASSETS / 'source.json')
parser.add_argument('--native', action='store_true', help='Check the HTTP adapter locally; excludes actual n8n execution')
parser.add_argument('--browser', action='store_true', help='Also inspect the imported workflow in the real n8n editor')
args = parser.parse_args()
OUT = args.out.resolve()
OUT.mkdir(parents=True, exist_ok=False)
manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
assert sha256(args.archive.read_bytes()).hexdigest() == manifest['zip_sha256']
with zipfile.ZipFile(args.archive) as archive:
    assert archive.testzip() is None
    assert set(archive.namelist()) == {manifest['prefix'] + row['path'] for row in manifest['files']}
    for row in manifest['files']:
        data = archive.read(manifest['prefix'] + row['path'])
        assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256']
        destination = OUT / 'source' / row['path']
        assert destination.resolve().is_relative_to(OUT / 'source')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
PROJECT = OUT / 'source'
sample = json.loads((PROJECT / 'sample.json').read_text(encoding='utf-8'))
workflow = json.loads((PROJECT / 'workflows/invoice-webhook.json').read_text(encoding='utf-8'))
assert not workflow.get('id') and not workflow.get('active') and not workflow.get('pinData')
assert all(node['type'].startswith('n8n-nodes-base.') and not node.get('credentials') for node in workflow['nodes'])
assert {node['type'].split('.')[-1] for node in workflow['nodes']} == {'webhook', 'httpRequest', 'if', 'respondToWebhook', 'stickyNote'}
checks = []
pdfs = []
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
BASE = f'http://127.0.0.1:{port}'
URL = BASE + ('/invoices' if args.native else '/webhook/fullbleed-invoice')
environment = os.environ.copy()
environment['N8N_PORT'] = str(port)
project_name = 'fb-n8n-check-' + uuid.uuid4().hex[:12]
compose = ['docker', 'compose', '--project-name', project_name, '--project-directory', str(PROJECT), '-f', str(PROJECT / 'compose.yaml')]
process = None
server_log = None
compose_started = False
command_count = 0


def run(command, label, timeout=300, check=True):
    global command_count
    command_count += 1
    result = subprocess.run(list(map(str, command)), cwd=PROJECT, env=environment,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    (OUT / f'{command_count:02d}-{label}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if check and result.returncode:
        print((result.stdout + result.stderr)[-6000:], flush=True)
        raise RuntimeError(f'{label} exited {result.returncode}')
    return result


def check(condition, label):
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def request(data, url=URL, method='POST', content_type='application/json'):
    body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode('utf-8')
    req = Request(url, data=body, method=method, headers={'Content-Type': content_type})
    try:
        response = urlopen(req, timeout=45)
    except HTTPError as error:
        response = error
    with response:
        return response.status, dict(response.headers.items()), response.read()


def ready():
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError('HTTP adapter exited while starting')
        try:
            with urlopen(BASE + ('/healthz' if args.native else '/healthz/readiness'), timeout=3) as response:
                if response.status == 200:
                    return
        except (HTTPError, URLError, TimeoutError):
            pass
        time.sleep(1)
    raise RuntimeError('Server did not become ready')


def start_native():
    global process, server_log
    env = environment.copy()
    env['PYTHONPATH'] = str(PROJECT / 'renderer')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    server_log = (OUT / f'adapter-{len(pdfs)}.log').open('w', encoding='utf-8')
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server:app', '--host', '127.0.0.1',
                                '--port', str(port), '--no-proxy-headers', '--no-access-log',
                                '--limit-concurrency', '8'], cwd=PROJECT, env=env,
                               stdout=server_log, stderr=subprocess.STDOUT)
    ready()


def stop_native():
    global process, server_log
    if process:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
        process = None
    if server_log:
        server_log.close()
        server_log = None


def pdf_check(name, result, expected, many=False):
    status, raw_headers, data = result
    headers = {key.lower(): value for key, value in raw_headers.items()}
    check(status == 200, name + ': HTTP 200')
    check(headers.get('content-type') == 'application/pdf', name + ': PDF content type')
    check(headers.get('content-disposition') == f'attachment; filename="{expected["number"]}.pdf"', name + ': intended attachment filename')
    check(headers.get('cache-control') == 'private, no-store', name + ': private no-store')
    check(data.startswith(b'%PDF-') and len(data) <= 4_000_000, name + ': bounded actual PDF bytes')
    (OUT / (name + '.pdf')).write_bytes(data)
    reader = PdfReader(BytesIO(data))
    text = '\n'.join(page.extract_text() for page in reader.pages)
    check(expected['number'] in text and expected['customer'] in text, name + ': invoice identity')
    for row in expected['items']:
        check(row['description'] in text, name + ': item ' + row['description'][:35])
    if many:
        check(len(reader.pages) > 1, name + ': pagination')
        for row in expected['items']:
            check(text.count(row['description']) == 1, name + ': each item exactly once ' + row['description'])
    document = pdfium.PdfDocument(data)
    try:
        for index, page in enumerate(document):
            try:
                width, height = page.get_size()
                check(abs(width - 595.276) < 1 and abs(height - 841.89) < 1, f'{name}: page {index + 1} A4')
                text_page = page.get_textpage()
                try:
                    for char in range(text_page.count_chars()):
                        left, bottom, right, top = text_page.get_charbox(char)
                        assert -1 <= left <= right <= width + 1 and -1 <= bottom <= top <= height + 1
                finally:
                    text_page.close()
                bitmap = page.render(scale=1)
                try:
                    image = bitmap.to_pil()
                    check(image.getbbox() is not None, f'{name}: page {index + 1} rasterized')
                    image.save(OUT / f'{name}-{index + 1}.png')
                    image.close()
                finally:
                    bitmap.close()
            finally:
                page.close()
    finally:
        document.close()
    (OUT / (name + '.txt')).write_text(text, encoding='utf-8')
    pdfs.append(dict(file=name + '.pdf', bytes=len(data), pages=len(reader.pages), sha256=sha256(data).hexdigest()))
    return data


def browser_check(workflow_id):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1500, 'height': 1050})
        page = context.new_page()
        page.goto(BASE, wait_until='networkidle')
        try:
            page.get_by_label(re.compile(r'^Email$', re.I)).fill('synthetic@example.invalid')
            page.get_by_label(re.compile(r'^First name$', re.I)).fill('Synthetic')
            page.get_by_label(re.compile(r'^Last name$', re.I)).fill('Verification')
            page.get_by_label(re.compile(r'^Password$', re.I)).fill('Local-Only-Pdf-Check-42!')
            page.get_by_role('button', name=re.compile(r'^Next$|^Create account$|^Set up$', re.I)).click()
            page.wait_for_url(re.compile(r'.*(?!setup)$'), timeout=30000)
            page.goto(BASE + '/workflow/' + workflow_id, wait_until='networkidle')
            page.get_by_text('Render PDF', exact=True).first.wait_for(state='visible', timeout=30000)
            page.get_by_text('Return PDF', exact=True).first.wait_for(state='visible')
            page.get_by_text('Return validation error', exact=True).first.wait_for(state='visible')
            page.screenshot(path=str(OUT / 'n8n-workflow.png'), full_page=True)
            check(True, 'real n8n editor displays imported workflow and response branches')
        finally:
            (OUT / 'n8n-browser.html').write_text(page.content(), encoding='utf-8')
            page.screenshot(path=str(OUT / 'n8n-browser-last.png'), full_page=True)
            context.close()
            browser.close()


failure = None
try:
    if args.native:
        start_native()
    else:
        run(['docker', 'version'], 'docker-version')
        config = json.loads(run(compose + ['config', '--format', 'json'], 'compose-config').stdout)
        check(config['networks']['documents']['internal'] is True, 'private Compose network')
        check(not config['services']['renderer'].get('ports'), 'renderer has no published host port')
        check(config['services']['n8n']['ports'][0]['host_ip'] == '127.0.0.1', 'n8n listens on loopback')
        compose_started = True
        run(compose + ['up', '--build', '-d', 'renderer'], 'renderer-start', timeout=600)
        run(compose + ['run', '--rm', '--no-deps', 'n8n', 'import:workflow', '--input=/workflows/invoice-webhook.json'], 'workflow-import', timeout=600)
        run(compose + ['run', '--rm', '--no-deps', 'n8n', 'export:workflow', '--all', '--output=/home/node/.n8n/verification-workflow.json'], 'workflow-export')
        exported = json.loads(run(compose + ['run', '--rm', '--no-deps', '--entrypoint', 'node', 'n8n', '-e',
                                 "process.stdout.write(require('node:fs').readFileSync('/home/node/.n8n/verification-workflow.json','utf8'))"], 'workflow-readback').stdout)
        check(len(exported) == 1, 'exactly one isolated workflow imported')
        for field in ['nodes', 'connections']:
            check(exported[0][field] == workflow[field], 'import preserved exact workflow ' + field)
        workflow_id = exported[0]['id']
        run(compose + ['run', '--rm', '--no-deps', 'n8n', 'publish:workflow', '--id=' + workflow_id], 'workflow-publish')
        run(compose + ['up', '-d', 'n8n'], 'n8n-start')
        ready()
        if args.browser:
            browser_check(workflow_id)
    initial = pdf_check('invoice', request(sample), sample)
    check(initial == (ASSETS / 'invoice.pdf').read_bytes(), 'workflow PDF equals the independently verified sample')
    check(request(sample)[2] == initial, 'identical repeated request yields identical PDF bytes')
    escaped = copy.deepcopy(sample)
    escaped.update(number='N8N-ESCAPED', customer='<b>Finch & Sons</b> $number')
    escaped['items'] = [dict(description='<b>Literal & text</b>', quantity=3, unit_price='0.10')]
    pdf_check('escaped', request(escaped), escaped)
    check('0.30' in (OUT / 'escaped.txt').read_text(encoding='utf-8'), 'decimal total survives the workflow')
    many = copy.deepcopy(sample)
    many.update(number='N8N-100', customer='Pagination Example')
    many['items'] = [dict(description=f'ROW{i:03d} complete document item', quantity=1, unit_price='1.00') for i in range(1, 101)]
    pdf_check('many-rows', request(many), many, many=True)
    concurrent = [copy.deepcopy(sample) for _ in range(2)]
    for index, invoice in enumerate(concurrent):
        invoice.update(number=f'N8N-PARALLEL-{index}', customer=f'Independent customer {index}')
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(request, concurrent))
    for index, (invoice, result) in enumerate(zip(concurrent, results)):
        pdf_check('parallel-' + str(index), result, invoice)
        text = (OUT / f'parallel-{index}.txt').read_text(encoding='utf-8')
        check(concurrent[1-index]['customer'] not in text, 'parallel invoice data does not cross requests')
    invalid = []
    for field, value in [('number', '../bad'), ('issued', '2026-02-30'), ('customer', ''), ('items', []), ('items', many['items'] + [many['items'][0]])]:
        candidate = copy.deepcopy(sample)
        candidate[field] = value
        invalid.append(candidate)
    invalid.append(dict(sample, unexpected=True))
    for field, value in [('quantity', True), ('quantity', -1), ('unit_price', 1.25)]:
        candidate = copy.deepcopy(sample)
        candidate['items'][0][field] = value
        invalid.append(candidate)
    for index, candidate in enumerate(invalid):
        status, headers, data = request(candidate)
        headers = {key.lower(): value for key, value in headers.items()}
        check(status == 400 and headers.get('content-type', '').startswith('application/json') and not data.startswith(b'%PDF-'), f'invalid input {index} returns a JSON error')
        check('error' in json.loads(data), f'invalid input {index} has an error message')
    status, headers, body = request(dict(sample, customer='a' * 70_000))
    check(status == 413 and not body.startswith(b'%PDF-'), 'oversized request is rejected without a PDF')
    run([sys.executable, 'post_invoice.py', 'sample.json', 'client.pdf', '--url', URL], 'real-client')
    check((PROJECT / 'client.pdf').read_bytes() == initial, 'documented client saves exact workflow PDF')
    if not args.native:
        run(compose + ['stop', 'renderer'], 'renderer-stop')
        status, headers, data = request(sample)
        check(status == 502 and json.loads(data) == {'error': 'PDF service is unavailable. Try again later.'}, 'renderer unavailability follows the service-error branch')
        run(compose + ['start', '--wait', 'renderer'], 'renderer-restart')
    else:
        stop_native()
        start_native()
    pdf_check('recovered', request(sample), sample)
    check((OUT / 'recovered.pdf').read_bytes() == initial, 'recovery returns the original PDF bytes')
except BaseException as error:
    failure = f'{type(error).__name__}: {error}'
    raise
finally:
    stop_native()
    cleanup_ok = True
    if compose_started:
        run(compose + ['logs', '--no-color'], 'container-logs', check=False)
        assert re.fullmatch(r'fb-n8n-check-[0-9a-f]{12}', project_name)
        result = run(compose + ['down', '--volumes', '--remove-orphans'], 'task-container-cleanup', check=False)
        cleanup_ok = result.returncode == 0
        image = project_name + '-renderer'
        run(['docker', 'image', 'rm', image], 'task-image-cleanup', check=False)
    report = dict(ok=failure is None and cleanup_ok, checked_at=datetime.now(timezone.utc).isoformat(),
                  mode='native adapter' if args.native else 'actual n8n Docker workflow',
                  engine='2.5.20', n8n=None if args.native else '2.42.5', archive_sha256=manifest['zip_sha256'],
                  checks=checks, check_count=len(checks), pdfs=pdfs, cleanup_ok=cleanup_ok, error=failure,
                  limitations=['Synthetic local workflow; no production hosting, external delivery, or capacity claim.',
                               'No n8n marketplace registration or community-node verification is claimed.'])
    (OUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(ok=report['ok'], mode=report['mode'], checks=len(checks), pdfs=len(pdfs), error=failure)), flush=True)
    if failure is None and not cleanup_ok:
        raise RuntimeError('Task container cleanup failed')
