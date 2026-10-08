"""Extract the exact Lambda download; inspect native or real-emulator responses."""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import argparse
import base64
import copy
import importlib
import io
import json
import platform
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
import zipfile

from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/lambda-starter'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'output/lambda-verification')
    parser.add_argument('--archive', type=Path, default=ASSETS / 'project.zip')
    parser.add_argument('--manifest', type=Path, default=ASSETS / 'source.json')
    parser.add_argument('--sample-pdf', type=Path, default=ASSETS / 'invoice.pdf')
    parser.add_argument('--docker-arch', choices=['x86_64', 'arm64'])
    parser.add_argument('--record', action='store_true', help='Save the inspected sample PDF, raster and native record')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, pdfs, responses = [], [], []
    report = dict(ok=False, mode='runtime-emulator' if args.docker_arch else 'native-handler',
                  os=platform.system(), machine=platform.machine(), checks=checks, pdfs=pdfs,
                  responses=responses, hosted_aws_deployment=False,
                  versions={name: version(name) for name in ['fullbleed', 'pypdf', 'pypdfium2', 'pillow']})
    container = image = None

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    def run(label, command, cwd=None, timeout=900):
        print('Starting ' + label, flush=True)
        result = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=timeout)
        (out / (label + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
        (out / (label + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
        check(label + ' exit status', result.returncode == 0)
        return result.stdout

    def inspect(label, response, markers, minimum_pages=1):
        check(label + ' status', response.get('statusCode') == 200)
        check(label + ' binary flag', response.get('isBase64Encoded') is True)
        headers = response['headers']
        check(label + ' PDF content type', headers['Content-Type'] == 'application/pdf')
        check(label + ' private response', headers['Cache-Control'] == 'private, no-store')
        check(label + ' attachment', headers['Content-Disposition'].startswith('attachment; filename="'))
        data = base64.b64decode(response['body'], validate=True)
        check(label + ' PDF signature', data.startswith(b'%PDF-'))
        reader = PdfReader(io.BytesIO(data), strict=True)
        check(label + ' page count', len(reader.pages) >= minimum_pages)
        text = '\n'.join(page.extract_text() for page in reader.pages)
        for marker in markers:
            check(label + ' text ' + marker, marker in text)
            if marker.startswith(('Line ', 'MAX-')):
                check(label + ' unique row ' + marker, text.count(marker) == 1)
        (out / (label + '.pdf')).write_bytes(data)
        doc = pdfium.PdfDocument(data)
        try:
            for page_index in range(len(doc)):
                page = doc[page_index]
                text_page = page.get_textpage()
                try:
                    width, height = page.get_size()
                    check(f'{label} page {page_index + 1} A4', abs(width - 595.28) < 1 and abs(height - 841.89) < 1)
                    for i in range(text_page.count_chars()):
                        char = text_page.get_text_range(i, 1)
                        if char.strip():
                            left, bottom, right, top = text_page.get_charbox(i)
                            if not (-1 <= left <= right <= width + 1 and -1 <= bottom <= top <= height + 1):
                                raise AssertionError(f'{label} page {page_index + 1}: text outside page')
                    bitmap = page.render(scale=1.25)
                    try:
                        bitmap.to_pil().save(out / f'{label}-{page_index + 1}.png')
                    finally:
                        bitmap.close()
                finally:
                    text_page.close()
                    page.close()
        finally:
            doc.close()
        pdfs.append(dict(name=label, bytes=len(data), pages=len(reader.pages), sha256=sha256(data).hexdigest()))
        check(label + ' all visible characters inside pages', True)
        return data

    try:
        manifest = json.loads(args.manifest.read_text())
        archive = args.archive.read_bytes()
        check('exact ZIP bytes and hash', len(archive) == manifest['zip_bytes'] and sha256(archive).hexdigest() == manifest['zip_sha256'])
        check('public engine pin', manifest['engine'] == report['versions']['fullbleed'] == '2.5.20')
        with tempfile.TemporaryDirectory(prefix='fullbleed lambda download ') as temp:
            temp_path = Path(temp).resolve()
            check('temporary directory stays in system temp', temp_path.parent == Path(tempfile.gettempdir()).resolve())
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                names = [manifest['prefix'] + f['path'] for f in manifest['files']]
                check('exact source inventory', sorted(bundle.namelist()) == sorted(names) and len(names) == len(set(names)))
                for item in manifest['files']:
                    relative = item['path']
                    destination = temp_path / manifest['prefix'] / relative
                    check('safe archive member ' + relative, not Path(relative).is_absolute() and '..' not in Path(relative).parts and destination.resolve().is_relative_to(temp_path))
                    data = bundle.read(manifest['prefix'] + relative)
                    check('source hash ' + relative, len(data) == item['bytes'] and sha256(data).hexdigest() == item['sha256'])
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(data)
            project = temp_path / manifest['prefix']
            run('handler-tests', [sys.executable, '-m', 'unittest', '-v', 'test_handler.py'], project)
            sys.path.insert(0, str(project))
            client = importlib.import_module('client')
            handler = importlib.import_module('handler')
            sample = json.loads((project / 'sample.json').read_text())
            invoke = lambda event: handler.handler(event, None)
            if args.docker_arch:
                base = json.loads((project / 'base-images.json').read_text())[args.docker_arch]
                image = 'fullbleed-lambda-check-' + uuid.uuid4().hex[:12]
                run('docker-build', ['docker', 'buildx', 'build', '--platform', base['platform'], '--provenance=false', '--load',
                                     '--build-arg', 'LAMBDA_BASE=' + base['image'], '--tag', image, '.'], project)
                image_info = json.loads(run('docker-image', ['docker', 'image', 'inspect', image]))[0]
                report['container_image'] = dict(id=image_info['Id'], architecture=image_info['Architecture'], base=base['image'])
                check('native image architecture', image_info['Architecture'] == ('amd64' if args.docker_arch == 'x86_64' else 'arm64'))
                container = run('docker-start', ['docker', 'run', '--rm', '--detach', '--publish', '127.0.0.1::8080',
                    '--read-only', '--tmpfs', '/tmp:rw,size=64m', '--user', '10001:10001', '--cap-drop', 'ALL',
                    '--security-opt', 'no-new-privileges:true', '--memory', '512m', '--cpus', '2', '--pids-limit', '128', image]).strip()
                port = int(run('docker-port', ['docker', 'port', container, '8080/tcp']).strip().rsplit(':', 1)[1])
                deadline = time.monotonic() + 30
                while True:
                    try:
                        with socket.create_connection(('127.0.0.1', port), timeout=1):
                            break
                    except OSError:
                        if time.monotonic() > deadline:
                            raise
                        time.sleep(.2)

                def invoke(event):
                    request = urllib.request.Request(f'http://127.0.0.1:{port}/2015-03-31/functions/function/invocations',
                        data=json.dumps(event).encode(), headers={'Content-Type': 'application/json'})
                    with urllib.request.urlopen(request, timeout=40) as response:
                        return json.load(response)

                package = json.loads(run('container-wheel', ['docker', 'exec', container, '/var/lang/bin/python', '-c',
                    'import json,platform; from pathlib import Path; from importlib.metadata import version; print(json.dumps(dict(version=version("fullbleed"),python=platform.python_version(),install=json.loads(Path("/var/task/pip-install.json").read_text()))))']))
                report['installed_container_package'] = package
                check('container public package version', package['version'] == '2.5.20')
            first = inspect('invoice', invoke(client.event(sample)), ['INV-1042', 'Maple & Finch', '1,870.00'])
            if args.record:
                check('record only native inspection', not args.docker_arch)
                args.sample_pdf.write_bytes(first)
                (ASSETS / 'invoice.png').write_bytes((out / 'invoice-1.png').read_bytes())
            else:
                check('published sample PDF identical', first == args.sample_pdf.read_bytes())
            request = client.event(sample)
            request.update(body=base64.b64encode(request['body'].encode()).decode(), isBase64Encoded=True)
            check('base64 body matches ordinary body', inspect('base64', invoke(request), ['INV-1042']) == first)
            alternate = copy.deepcopy(sample)
            alternate.update(number='INV-OTHER', customer='<b>Finch & Sons</b> $number')
            other = inspect('escaped', invoke(client.event(alternate)), ['<b>Finch & Sons</b> $number', 'INV-OTHER'])
            check('different customer changes PDF', other != first)
            many = copy.deepcopy(sample)
            many['items'] = [dict(description=f'Line {i:03d} - design and delivery', quantity=1, unit_price='1.25') for i in range(100)]
            inspect('many-rows', invoke(client.event(many)), [f'Line {i:03d}' for i in range(100)] + ['125.00'], 2)
            maximum = copy.deepcopy(many)
            maximum['customer'] = 'W' * 80
            maximum['items'] = [dict(description=f'MAX-{i:03d} ' + 'W' * 150, quantity=100, unit_price='999999.99') for i in range(100)]
            inspect('maximum', invoke(client.event(maximum)), [f'MAX-{i:03d}' for i in range(100)] + ['9,999,999,900.00'], 2)
            for label, changes, expected in [
                ('wrong-path', {'rawPath': '/missing'}, 404),
                ('wrong-method', {'requestContext': {'http': {'method': 'GET'}}}, 405),
                ('wrong-type', {'headers': {'content-type': 'text/plain'}}, 415),
                ('invalid-json', {'body': '{'}, 400),
                ('oversized', {'body': 'x' * 65_537}, 413),
                ('invalid-base64', {'body': '***', 'isBase64Encoded': True}, 400),
                ('extra-fields', {'body': json.dumps({**sample, 'html': '<h1>Do not run</h1>'})}, 400),
            ]:
                request = client.event(sample)
                request.update(changes)
                response = invoke(request)
                check(label + ' rejected', response.get('statusCode') == expected and response.get('isBase64Encoded') is False)
                responses.append(dict(name=label, status=response['statusCode']))
            check('warm recovery and no previous invoice data', inspect('recovered', invoke(client.event(sample)), ['Maple & Finch']) == first)
            if args.docker_arch:
                run('client-local', [sys.executable, 'client.py', 'local', 'sample.json', out / 'client.pdf', '--port', str(port)], project)
                check('documented client downloads matching PDF', (out / 'client.pdf').read_bytes() == first)
            run('client-event', [sys.executable, 'client.py', 'event', 'sample.json', out / 'event.json'], project)
            response = invoke(json.loads((out / 'event.json').read_text()))
            (out / 'response.json').write_text(json.dumps(response))
            run('client-decode', [sys.executable, 'client.py', 'decode', out / 'response.json', out / 'decoded.pdf'], project)
            check('documented decode produces matching PDF', (out / 'decoded.pdf').read_bytes() == first)
            check('no source directory PDF output', not list(project.rglob('*.pdf')))
            check('temporary tree remains in expected directory', all(p.resolve().is_relative_to(temp_path) and not p.is_symlink() for p in temp_path.rglob('*')))
            report['ok'] = True
    finally:
        original_error = sys.exc_info()[1]
        if original_error:
            report['error'] = str(original_error)
        cleanup = []
        if container:
            for label, command in [('container-logs', ['docker', 'logs', container]),
                                   ('container-stop', ['docker', 'stop', container])]:
                result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45)
                (out / (label + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
                (out / (label + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
                cleanup.append(dict(action=label, exit_code=result.returncode))
            report['container_stopped'] = cleanup[-1]['exit_code'] == 0
        if image:
            result = subprocess.run(['docker', 'image', 'rm', image], capture_output=True, timeout=45)
            cleanup.append(dict(action='remove-task-image', exit_code=result.returncode))
        report['cleanup'] = cleanup
        if any(row['exit_code'] for row in cleanup):
            report['ok'] = False
        report['check_count'] = len(checks)
        (out / 'verification.json').write_bytes((json.dumps(report, indent=2) + '\n').encode('utf-8'))
        if args.record and report['ok']:
            (ASSETS / 'verification.json').write_bytes((out / 'verification.json').read_bytes())
        if not original_error and not report['ok']:
            raise RuntimeError('Verification cleanup failed; see verification.json')
    print(json.dumps(dict(ok=report['ok'], checks=len(checks), pdfs=len(pdfs), pages=sum(p['pages'] for p in pdfs), mode=report['mode'])), flush=True)


if __name__ == '__main__':
    main()
