"""Independent PDF checks for the playground's retained decoration inputs."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

import pypdfium2 as pdfium
from playground_decoration_inspection import check_image, glyph_geometry

ROOT = Path(__file__).resolve().parents[1]
ENGINE_VERSION = json.loads((ROOT / 'docs/assets/playground/build.json').read_text(encoding='utf-8'))['engine']['version']
FIXTURES = ROOT / 'tools/playground-fixtures/text-decorations-2.5.40.json'
EXPECTATIONS = ROOT / 'tools/playground-fixtures/text-decoration-expectations-2.5.40.json'


def cases():
    source = FIXTURES.read_bytes()
    fixtures, oracle = json.loads(source), json.loads(EXPECTATIONS.read_bytes())
    assert oracle['inputSha256'] == sha256(source).hexdigest()
    assert oracle['fontSha256'] == fixtures['fontSha256']
    assert oracle['engineVersion'] == '2.5.40'
    assert len(fixtures['cases']) == len(oracle['cases']) == 16
    assert {row['name'] for row in fixtures['cases']} == {row['name'] for row in oracle['cases']}
    return [(case, next(row for row in oracle['cases'] if row['name'] == case['name']))
            for case in fixtures['cases']]


def inspect_pdf(path, case, wanted, preview_path=None):
    """Compare glyph geometry and independent 144 dpi pixels with public-core evidence."""
    data = Path(path).read_bytes()
    checks = {'glyphGeometry': json.loads(json.dumps(glyph_geometry(data))) == wanted['geometry']}
    with pdfium.PdfDocument(data) as document:
        checks['onePage'] = len(document) == 1
        page = document[0]
        bitmap = page.render(scale=2)
        image = bitmap.to_pil()
        try:
            if preview_path is not None:
                image.save(preview_path)
            actual = check_image(image, case)
            checks['independentPixels'] = actual == wanted['pdfium']
        finally:
            image.close()
            bitmap.close()
            page.close()
    return dict(name=case['name'], passed=all(checks.values()), checks=checks,
        pdfSha256=sha256(data).hexdigest(), pdfium=actual)


def check_browser(page, out, expected=None):
    """Inspect real editor downloads and the displayed finalized-PDF previews."""
    from playwright.sync_api import expect
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    report = dict(ok=False, at=datetime.now(timezone.utc).isoformat(), cases=rows,
        fixtureSha256=sha256(FIXTURES.read_bytes()).hexdigest(),
        expectationsSha256=sha256(EXPECTATIONS.read_bytes()).hexdigest())
    try:
        for case, wanted in cases():
            name = 'decoration-' + case['name']
            folder = out / name
            folder.mkdir()
            for language in ['html', 'css']:
                page.locator('#pg-' + language + '-tab').click()
                page.locator('#pg-' + language).fill(case[language])
            page.locator('#pg-render').click()
            expect(page.locator('#pg-download')).to_have_attribute('href', re.compile('^blob:'), timeout=120000)
            expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
            expect(page.locator('#pg-result')).to_contain_text('Fullbleed ' + ENGINE_VERSION)
            with page.expect_download() as event:
                page.locator('#pg-download').click()
            pdf = folder / 'document.pdf'
            event.value.save_as(pdf)
            preview = bytes(page.locator('#pg-preview').evaluate('''async image => {
                await image.decode();
                return Array.from(new Uint8Array(await (await fetch(image.src)).arrayBuffer()));
            }'''))
            (folder / 'displayed-preview.png').write_bytes(preview)
            if expected is None:
                reference = ROOT / 'playground/project-verification' / (name + '-expected')
                hashes = {file: sha256((reference / file).read_bytes()).hexdigest()
                          for file in ['output.pdf', 'page-1.png']}
            else:
                hashes = expected[name]
            row = inspect_pdf(pdf, case, wanted, folder / 'independent-preview.png')
            row['checks'].update(downloadMatchesQualifiedPdf=row['pdfSha256'] == hashes['output.pdf'],
                displayedPreviewMatchesQualifiedPng=sha256(preview).hexdigest() == hashes['page-1.png'])
            row['passed'] = all(row['checks'].values())
            rows.append(row)
            assert row['passed'], row
            if case['name'] in ['underline', 'propagated-raised', 'nowrap-control']:
                page.locator('#pg-preview').scroll_into_view_if_needed()
                page.screenshot(path=str(folder / 'browser.png'), animations='disabled')
        report.update(ok=True, passed=len(rows), failed=0,
            scope='16 fixed-font decoration inputs through the actual editor; independent geometry/pixels and qualified PDF/preview bytes. No universal parity or conformance claim.')
    except BaseException as error:
        report['error'] = str(error)
        raise
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('All 16 decoration cases passed through the actual playground editor.', flush=True)
    return dict(ok=True, passed=len(rows), fixtureSha256=report['fixtureSha256'],
        expectationsSha256=report['expectationsSha256'], report='decorations/verification.json')
