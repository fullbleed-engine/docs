"""Check the released radial-gradient fixtures in PDFs and real browser downloads."""
from datetime import datetime, timezone
from hashlib import sha256
from importlib import metadata
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
from zipfile import ZipFile

from PIL import Image
from pypdf import PdfReader
from pypdf.generic import IndirectObject
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tools/playground-fixtures/radial-gradient-endpoints-2.5.43.json'
REFERENCE_ENGINE_VERSION = '2.5.43'
ENGINE_VERSION = '2.5.48'
NODE_VERSION = '0.9.1'


def cases():
    source = json.loads(FIXTURES.read_bytes())
    assert source['schema'] == 'fullbleed.radial_gradient_endpoints.v1'
    assert source['referenceVersion'] == REFERENCE_ENGINE_VERSION
    assert len(source['cases']) == 12 and sum(row['affected'] for row in source['cases']) == 9
    assert len({row['name'] for row in source['cases']}) == 12
    for case in source['cases']:
        assert sha256((case['html'] + '\0' + case['css']).encode()).hexdigest() == case['inputSha256']
    return source['cases']


def stitching_bounds(path):
    reader = PdfReader(path)
    size_ok = len(reader.pages) == 1 and tuple(map(float, reader.pages[0].mediabox)) == (0, 0, 100, 100)
    count, invalid = 0, []
    for generation, entries in reader.xref.items():
        for number in entries:
            if not number:
                continue
            value = reader.get_object(IndirectObject(number, generation, reader))
            if not hasattr(value, 'get') or value.get('/FunctionType') != 3:
                continue
            count += 1
            domain = list(map(float, value['/Domain']))
            bounds = list(map(float, value['/Bounds']))
            encode = list(map(float, value['/Encode']))
            valid = len(domain) == 2 and all(map(math.isfinite, domain + bounds + encode)) and domain[0] < domain[1]
            valid = valid and all(domain[0] < bound < domain[1] for bound in bounds)
            valid = valid and all(left < right for left, right in zip(bounds, bounds[1:]))
            valid = valid and len(value['/Functions']) == len(bounds) + 1 and len(encode) == 2 * len(value['/Functions'])
            if not valid:
                invalid.append(dict(object=number, generation=generation, domain=domain, bounds=bounds))
    return dict(onePage100pt=size_ok, functions=count, invalid=invalid)


def image_checks(image, case, dpi, tolerance):
    probes = []
    for x, y in case['probes']:
        pixel = image.getpixel((int(x * dpi / 72), int(y * dpi / 72)))
        error = max(abs(left - right) for left, right in zip(pixel, case['expected']))
        probes.append(dict(point=[x, y], pixel=list(pixel), maxChannelError=error))
    return dict(size=list(image.size), rgbSha256=sha256(image.tobytes()).hexdigest(), probes=probes,
                outerColorCorrect=all(probe['maxChannelError'] <= tolerance for probe in probes))


def inspect_pdf(path, case, native_path, independent_path):
    """Require release PDF bytes, valid stitching bounds and two readers' colors."""
    digest = sha256(Path(path).read_bytes()).hexdigest()
    with Image.open(native_path) as source:
        with source.convert('RGB') as image:
            assert image.size == (133, 133), image.size
            native = image_checks(image, case, 96, 1)
    with pdfium.PdfDocument(path) as document:
        assert len(document) == 1
        page = document[0]
        bitmap = page.render(scale=2)
        image = bitmap.to_pil().convert('RGB')
        try:
            assert image.size == (200, 200), image.size
            independent = image_checks(image, case, 144, 2 if case['name'] == 'smooth-control' else 1)
            image.save(independent_path)
        finally:
            image.close()
            bitmap.close()
            page.close()
    bounds = stitching_bounds(path)
    reference = case['referenceImages']['pdfium']
    checks = dict(releasedPdfBytes=digest == case['candidatePdfSha256'],
                  onePage100pt=bounds['onePage100pt'], validStitchingBounds=not bounds['invalid'],
                  nativeOuterColor=native['outerColorCorrect'], independentOuterColor=independent['outerColorCorrect'],
                  independentReleasedPixels=independent['size'] == reference['size'] and independent['rgbSha256'] == reference['rgbSha256'])
    return dict(name=case['name'], passed=all(checks.values()), checks=checks, pdfSha256=digest,
                nativePreviewSha256=sha256(Path(native_path).read_bytes()).hexdigest(),
                stitchingBounds=bounds, images=dict(native96=native, pdfium144=independent))


def replay_download(archive_path, language, case, expected_pdf, expected_png):
    """Run an actual browser ZIP, outside its directory, using public packages."""
    project = archive_path.parent / ('extracted ' + language + ' project with spaces')
    project.mkdir(exist_ok=False)
    fonts = json.loads((ROOT / 'docs/assets/playground/font-sources.json').read_bytes())['files']
    required = {'input.html', 'style.css', 'README.txt', 'LICENSE.txt', 'project.json', 'fonts/font-sources.json'}
    required.update('fonts/' + item['file'] for item in fonts)
    required.update({'render.py', 'requirements.txt'} if language == 'python' else {'render.mjs', 'package.json', 'package-lock.json'})
    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert archive.testzip() is None and len(names) == len(set(names))
        assert set(names) == required
        for name in names:
            assert not PurePosixPath(name).is_absolute() and '..' not in PurePosixPath(name).parts
            assert '\\' not in name and ':' not in name
        manifest = json.loads(archive.read('project.json'))
        assert manifest['engine']['version'] == ENGINE_VERSION and not manifest.get('localAssets')
        assert {item['path'] for item in manifest['files']} == required - {'project.json'}
        assert len(manifest['files']) == len(required) - 1
        for item in manifest['files']:
            raw = archive.read(item['path'])
            assert len(raw) == item['bytes'] and sha256(raw).hexdigest() == item['sha256']
        assert archive.read('input.html').decode() == case['html'] and archive.read('style.css').decode() == case['css']
        for item in fonts:
            assert sha256(archive.read('fonts/' + item['file'])).hexdigest() == item['sha256']
        runner = 'render.py' if language == 'python' else 'render.mjs'
        runner_source = ROOT / 'docs/assets/playground/project' / (runner if language == 'python' else 'node/' + runner)
        assert archive.read(runner) == runner_source.read_bytes()
        if language == 'python':
            assert archive.read('requirements.txt').decode() == 'fullbleed==' + ENGINE_VERSION + '\n'
            assert metadata.version('fullbleed') == ENGINE_VERSION
            package = ENGINE_VERSION
        else:
            package = json.loads(archive.read('package.json'))['dependencies']['fullbleed']
            assert package == NODE_VERSION
            assert manifest['runtime']['package']['version'] == NODE_VERSION
        archive.extractall(project)
    if language == 'python':
        command = [sys.executable, '-I', str(project / runner)]
    else:
        node = Path(shutil.which('node') or '')
        assert node.is_file(), 'Node must be available on PATH'
        node_version = subprocess.check_output([str(node), '--version'], text=True).strip()
        assert int(node_version.removeprefix('v').split('.')[0]) >= 22
        candidates = [node.parent / 'node_modules/npm/bin/npm-cli.js', node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js']
        npm = next(path for path in candidates if path.is_file())
        lock = (project / 'package-lock.json').read_bytes()
        assert json.loads(lock)['packages']['node_modules/fullbleed']['version'] == NODE_VERSION
        command = [str(node), str(npm), 'ci', '--ignore-scripts', '--no-audit', '--no-fund',
                   '--cache', str(project.parent / 'npm-cache'), '--registry=https://registry.npmjs.org']
        installed = subprocess.run(command, cwd=project, capture_output=True, text=True, encoding='utf-8', timeout=180)
        (project / 'install.log').write_text(installed.stdout + installed.stderr, encoding='utf-8')
        installed.check_returncode()
        assert (project / 'package-lock.json').read_bytes() == lock
        command = [str(node), str(project / runner)]
    for attempt in ('first', 'repeat'):
        run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=90)
        (project / (attempt + '.log')).write_text(run.stdout + run.stderr, encoding='utf-8')
        run.check_returncode()
        rendered = json.loads((project / 'output/render.json').read_bytes())
        assert rendered['engine'] == ENGINE_VERSION and rendered['pages'] == 1
        if language == 'node':
            assert rendered['package'] == NODE_VERSION and rendered['missingGlyphs'] == 0
        assert (project / 'output/document.pdf').read_bytes() == expected_pdf
        assert rendered['sha256'] == sha256(expected_pdf).hexdigest()
        assert len(rendered['previews']) == 1 and Path(rendered['previews'][0]).resolve().is_relative_to(project.resolve())
        assert Path(rendered['previews'][0]).read_bytes() == expected_png
    return dict(language=language, package=package, engine=ENGINE_VERSION, archive=archive_path.name,
                zipSha256=sha256(archive_path.read_bytes()).hexdigest(), sourceAndManifestVerified=True,
                downloadedPdfAndPreviewMatch=True, repeatBytesMatch=True)


def check_browser(page, out, expected=None):
    """Drive the real editor and replay its Python and Node project downloads."""
    from playwright.sync_api import expect
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    report = dict(ok=False, at=datetime.now(timezone.utc).isoformat(), engine=ENGINE_VERSION,
                  fixtureSha256=sha256(FIXTURES.read_bytes()).hexdigest(), cases=[], exports=[])
    try:
        for case in cases():
            name = 'radial-endpoint-' + case['name']
            folder = out / name
            folder.mkdir()
            for language in ('html', 'css'):
                page.locator('#pg-' + language + '-tab').click()
                page.locator('#pg-' + language).fill(case[language])
                (folder / ('input.html' if language == 'html' else 'style.css')).write_bytes(case[language].encode())
            assert page.locator('#pg-download').get_attribute('href') is None
            page.locator('#pg-render').click()
            expect(page.locator('#pg-download')).to_have_attribute('href', re.compile('^blob:'), timeout=120000)
            expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
            expect(page.locator('#pg-result')).to_contain_text('Fullbleed ' + ENGINE_VERSION)
            with page.expect_download() as pending:
                page.locator('#pg-download').click()
            assert pending.value.failure() is None
            pdf = folder / 'document.pdf'
            pending.value.save_as(pdf)
            preview = bytes(page.locator('#pg-preview').evaluate('''async image => {
                await image.decode();
                return Array.from(new Uint8Array(await (await fetch(image.src)).arrayBuffer()));
            }'''))
            native = folder / 'displayed-preview.png'
            native.write_bytes(preview)
            if expected is None:
                reference = ROOT / 'playground/project-verification' / (name + '-expected')
                hashes = {file: sha256((reference / file).read_bytes()).hexdigest() for file in ('output.pdf', 'page-1.png')}
            else:
                hashes = expected[name]
            row = inspect_pdf(pdf, case, native, folder / 'independent-preview.png')
            row['checks'].update(downloadMatchesQualifiedPdf=row['pdfSha256'] == hashes['output.pdf'],
                                 displayedPreviewMatchesQualifiedPng=sha256(preview).hexdigest() == hashes['page-1.png'])
            row['passed'] = all(row['checks'].values())
            report['cases'].append(row)
            assert row['passed'], row
            if case['name'] == 'opaque':
                for language in ('python', 'node'):
                    page.locator('#pg-project-language').select_option(language)
                    with page.expect_download() as pending:
                        page.locator('#pg-project').click()
                    assert pending.value.failure() is None
                    archive = folder / (language + '-project.zip')
                    pending.value.save_as(archive)
                    report['exports'].append(replay_download(archive, language, case, pdf.read_bytes(), preview))
            if case['name'] in ('opaque', 'alpha', 'smooth-control'):
                page.locator('#pg-preview').scroll_into_view_if_needed()
                page.screenshot(path=str(folder / 'browser.png'), animations='disabled')
        report.update(ok=True, passed=len(report['cases']), failed=0,
                      scope='Twelve fixed radial-gradient inputs through the actual editor, exact release PDF bytes, independent PDFium pixels, valid stitching bounds, and two actual project ZIPs replayed twice. No general parity or conformance claim.')
    except BaseException as error:
        report['error'] = str(error)
        raise
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('All 12 radial-gradient browser cases and both downloaded projects passed.', flush=True)
    return dict(ok=True, passed=12, exportsReplayed=2, fixtureSha256=report['fixtureSha256'], report='radial-gradients/verification.json')
