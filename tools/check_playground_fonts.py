"""Verify page fonts through the real editor, PDF download and project exports."""
import argparse
import base64
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import threading
from urllib.parse import urlsplit
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from playground_font_inspection import ROOT, ENGINE, NODE, FIXTURE_PATH, fixtures, inspect_pdf

parser = argparse.ArgumentParser(description=__doc__)
target = parser.add_mutually_exclusive_group(required=True)
target.add_argument('--site', type=Path)
target.add_argument('--url', help='Published docs origin, for example https://docs.fullbleed.dev')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--python', default=sys.executable, help='Python with the matching public Fullbleed wheel')
args = parser.parse_args()
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
source = fixtures()
server = None
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass
if args.site:
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(args.site.resolve())))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f'http://127.0.0.1:{server.server_port}'
else:
    origin = args.url.rstrip('/')
record = {'ok': False, 'at': datetime.now(timezone.utc).isoformat(), 'origin': origin,
          'engine': ENGINE, 'nodePackage': NODE, 'fixtureSha256': sha256(FIXTURE_PATH.read_bytes()).hexdigest(),
          'anonymousContext': True, 'pairs': [], 'exports': [], 'errors': [], 'requests': []}


def replay(archive_path, language, specimen, expected_pdf, expected_pngs):
    project = out / ('exported ' + language + ' project with spaces')
    project.mkdir()
    with ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert len(names) == len(set(names))
        for name in names:
            assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
            assert ':' not in name and '\\' not in name
        manifest = json.loads(archive.read('project.json'))
        assert manifest['engine']['version'] == ENGINE
        assert archive.read('input.html') == specimen['html'].encode()
        assert archive.read('style.css') == specimen['aliasCss'].encode()
        assert {item['path'] for item in manifest['files']} == set(names) - {'project.json'}
        for item in manifest['files']:
            data = archive.read(item['path'])
            assert len(data) == item['bytes'] and sha256(data).hexdigest() == item['sha256']
        for font in source['fonts']:
            assert sha256(archive.read('assets/' + font['name'])).hexdigest() == font['sha256']
        assert {'assets/Body-OFL.txt', 'assets/Display-OFL.txt'} <= set(names)
        if language == 'python':
            assert archive.read('requirements.txt').decode() == f'fullbleed=={ENGINE}\n'
        else:
            package = json.loads(archive.read('package.json'))
            lock = json.loads(archive.read('package-lock.json'))
            assert package['dependencies']['fullbleed'] == lock['packages']['node_modules/fullbleed']['version'] == NODE
            assert package['fullbleed']['engineVersion'] == ENGINE
        archive.extractall(project)
    if language == 'python':
        command = [args.python, '-I', str(project / 'render.py')]
    else:
        node = Path(shutil.which('node') or '')
        assert node.is_file()
        assert int(subprocess.check_output([str(node), '--version'], text=True).strip()[1:].split('.')[0]) >= 22
        npm = next(path for path in [node.parent / 'node_modules/npm/bin/npm-cli.js', node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'] if path.is_file())
        empty_config = out / 'anonymous.npmrc'
        empty_config.write_text('', encoding='utf8')
        before = (project / 'package-lock.json').read_bytes()
        installed = subprocess.run([str(node), str(npm), 'ci', '--ignore-scripts', '--no-audit', '--no-fund',
            '--registry=https://registry.npmjs.org', '--cache', str(out / 'npm-cache'), '--userconfig', str(empty_config)],
            cwd=project, capture_output=True, text=True, encoding='utf8', timeout=180)
        (project / 'install.log').write_text(installed.stdout + installed.stderr, encoding='utf8')
        installed.check_returncode()
        assert (project / 'package-lock.json').read_bytes() == before
        command = [str(node), str(project / 'render.mjs')]
    run = subprocess.run(command, cwd=out, capture_output=True, text=True, encoding='utf8', timeout=90)
    (project / 'render.log').write_text(run.stdout + run.stderr, encoding='utf8')
    run.check_returncode()
    rendered = json.loads((project / 'output/render.json').read_bytes())
    assert rendered['engine'] == ENGINE and rendered['pages'] == len(expected_pngs)
    if language == 'node':
        assert rendered['package'] == NODE and rendered['missingGlyphs'] == 0
    assert (project / 'output/document.pdf').read_bytes() == expected_pdf
    assert all(Path(path).resolve().is_relative_to(project.resolve()) for path in rendered['previews'])
    assert [Path(path).read_bytes() for path in rendered['previews']] == expected_pngs
    return {'language': language, 'zipSha256': sha256(archive_path.read_bytes()).hexdigest(),
            'pages': len(expected_pngs), 'sourceAndAssetsPreserved': True, 'browserPdfAndPreviewsEqual': True}


try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome', headless=True)
        context = browser.new_context(accept_downloads=True, viewport={'width': 1365, 'height': 1000})
        page = context.new_page()
        page.on('pageerror', lambda error: record['errors'].append(str(error)))
        page.on('request', lambda request: record['requests'].append({'url': request.url, 'method': request.method, 'body': request.post_data}))
        def ready():
            expect(page.locator('#pg-download')).to_have_attribute('href', re.compile('^blob:'), timeout=120000)
            expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
            expect(page.locator('#pg-result')).to_contain_text('Fullbleed ' + ENGINE)
        page.goto(origin + '/playground/', wait_until='domcontentloaded')
        ready()
        response = context.request.get(origin + '/assets/playground/verification.json?v=page-fonts-2548')
        assert response.ok
        reference = response.json()
        assert reference['ok'] and reference['engine'] == ENGINE
        reference_cases = {row['name']: row for row in reference['fixtures']}
        payloads = [{'name': font['name'], 'mimeType': 'font/ttf', 'buffer': (ROOT / font['path']).read_bytes()} for font in source['fonts']]
        for name, path in [('Body-OFL.txt', 'tools/playground-fixtures/fonts/NotoSans-OFL.txt'), ('Display-OFL.txt', 'docs/assets/playground/fonts/DMSerifDisplay-OFL.txt')]:
            payloads.append({'name': name, 'mimeType': 'text/plain', 'buffer': (ROOT / path).read_bytes()})
        page.locator('#pg-files').set_input_files(payloads)
        expect(page.locator('#pg-asset-count')).to_have_text('4 local assets')
        for specimen in source['cases']:
            pair = []
            for kind in ['control', 'alias']:
                name = f'page-font-{specimen["name"]}-{kind}'
                page.locator('#pg-html-tab').click()
                page.locator('#pg-html').fill(specimen['html'])
                page.locator('#pg-css-tab').click()
                page.locator('#pg-css').fill(specimen[kind + 'Css'])
                page.locator('#pg-render').click()
                ready()
                with page.expect_download() as download:
                    page.locator('#pg-download').click()
                path = out / (name + '.pdf')
                download.value.save_as(path)
                assert sha256(path.read_bytes()).hexdigest() == reference_cases[name]['hashes']['output.pdf']
                inspected = inspect_pdf(path, specimen, out / 'independent' / name)
                pngs = []
                for index in range(len(specimen['footerFaces'])):
                    expect(page.locator('#pg-page-count')).to_have_text(f'{index + 1} / {len(specimen["footerFaces"])}')
                    raw = page.locator('#pg-preview').evaluate('async image => { const bytes = new Uint8Array(await (await fetch(image.src)).arrayBuffer()); let value = ""; for (const byte of bytes) value += String.fromCharCode(byte); return btoa(value); }')
                    png = base64.b64decode(raw)
                    assert sha256(png).hexdigest() == reference_cases[name]['hashes'][f'page-{index + 1}.png']
                    (out / f'{name}-page-{index + 1}.png').write_bytes(png)
                    pngs.append(png)
                    if index + 1 < len(specimen['footerFaces']):
                        page.locator('#pg-next').click()
                pair.append(inspected)
                if specimen['name'] == 'named-pages' and kind == 'alias':
                    page.locator('.pg-output').screenshot(path=str(out / 'named-pages-preview.png'))
                    for language in ['python', 'node']:
                        page.locator('#pg-project-language').select_option(language)
                        with page.expect_download() as download:
                            page.locator('#pg-project').click()
                        archive_path = out / f'named-pages-{language}.zip'
                        download.value.save_as(archive_path)
                        record['exports'].append(replay(archive_path, language, specimen, path.read_bytes(), pngs))
            assert pair[0] == pair[1], specimen['name']
            record['pairs'].append({'name': specimen['name'], **pair[0]})
            print(specimen['name'] + ': browser PDF and previews passed', flush=True)
        assert not record['errors']
        external = {'https://api.github.com/repos/fullbleed-engine/fullbleed-official', 'https://api.github.com/repos/fullbleed-engine/fullbleed-official/releases/latest'}
        site_origin = urlsplit(origin)
        blob_origin = f'blob:{site_origin.scheme}://{site_origin.netloc}/'
        assert all(row['method'] == 'GET' and not row['body'] and (row['url'].startswith((origin + '/', blob_origin)) or row['url'] in external) for row in record['requests'])
        record.update(ok=True, browser=browser.version, pairsVerified=8, pagesVerified=18, documentUploads=False,
                      scope='Eight real editor font comparisons and both actual named-page project downloads; no universal browser parity or conformance claim.')
        context.close()
        browser.close()
finally:
    if server:
        server.shutdown()
        server.server_close()
    (out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf8')
print(json.dumps({'ok': record['ok'], 'pairs': len(record['pairs']), 'exports': len(record['exports'])}))
