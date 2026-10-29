"""Shared independent PDF checks for the playground's quotation fixtures."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ENGINE_VERSION = json.loads((ROOT / 'docs/assets/playground/build.json').read_text(encoding='utf-8'))['engine']['version']
FIXTURES = ROOT / 'tools/playground-fixtures/generated-quotes-2.5.38.json'


def cases():
    records = json.loads(FIXTURES.read_text(encoding='utf-8'))['cases']
    assert len(records) == len({item['name'] for item in records}) == 41
    return records


def inspect_pdf(path, fixture, preview_path=None):
    """Check actual exported text, page dimensions and visible independent output."""
    normalize = lambda text: ''.join(text.split())
    reader = PdfReader(path, strict=True)
    text = normalize(''.join(page.extract_text() or '' for page in reader.pages))
    independent_text, pixel_hashes, visible = '', [], []
    with pdfium.PdfDocument(path) as document:
        for number, page in enumerate(document, 1):
            textpage = page.get_textpage()
            try:
                independent_text += normalize(textpage.get_text_range())
                bitmap = page.render(scale=1)
                try:
                    image = bitmap.to_pil().convert('RGB')
                    pixel_hashes.append(sha256(image.tobytes()).hexdigest())
                    visible.append(min(channel[0] for channel in image.getextrema()) < 180)
                    if preview_path is not None:
                        image.save(preview_path)
                finally:
                    bitmap.close()
            finally:
                textpage.close()
                page.close()
    checks = dict(onePage=len(reader.pages) == 1,
        pypdfText=text == fixture['expectedText'], pdfiumText=independent_text == fixture['expectedText'],
        pageGeometry=all(abs(float(page.mediabox.width) - 450) < 0.01 and
            abs(float(page.mediabox.height) - 300) < 0.01 for page in reader.pages),
        visibleIndependentOutput=bool(visible) and all(visible))
    return dict(name=fixture['name'], passed=all(checks.values()), checks=checks,
        text=text, pdfiumText=independent_text, expected=fixture['expectedText'],
        pdfSha256=sha256(Path(path).read_bytes()).hexdigest(), pdfiumPixelSha256=pixel_hashes)


def check_browser(page, out, expected=None):
    """Render each quotation in the actual editor and inspect its downloaded PDF."""
    from playwright.sync_api import expect
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    records = []
    report = dict(at=datetime.now(timezone.utc).isoformat(), ok=False, cases=records,
        fixtureSha256=sha256(FIXTURES.read_bytes()).hexdigest())
    try:
        for fixture in cases():
            name = 'quote-' + fixture['name']
            folder = out / name
            folder.mkdir()
            page.locator('#pg-html-tab').click()
            page.locator('#pg-html').fill(fixture['html'])
            page.locator('#pg-css-tab').click()
            page.locator('#pg-css').fill(fixture['css'])
            page.locator('#pg-render').click()
            expect(page.locator('#pg-download')).to_have_attribute('href', re.compile(r'^blob:'), timeout=120000)
            expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
            expect(page.locator('#pg-result')).to_contain_text('Fullbleed ' + ENGINE_VERSION)
            with page.expect_download() as event:
                page.locator('#pg-download').click()
            pdf = folder / 'document.pdf'
            event.value.save_as(pdf)
            preview_url = page.locator('#pg-preview').get_attribute('src')
            assert preview_url.startswith('blob:')
            preview = bytes(page.evaluate('''async url => {
                const response = await fetch(url);
                return Array.from(new Uint8Array(await response.arrayBuffer()));
            }''', preview_url))
            (folder / 'displayed-preview.png').write_bytes(preview)
            row = inspect_pdf(pdf, fixture, folder / 'independent-preview.png')
            if expected is None:
                reference = ROOT / 'playground/project-verification' / (name + '-expected')
                hashes = {file: sha256((reference / file).read_bytes()).hexdigest()
                    for file in ['output.pdf', 'page-1.png']}
            else:
                hashes = expected[name]
            row['checks'].update(downloadMatchesQualifiedPdf=row['pdfSha256'] == hashes['output.pdf'],
                displayedPreviewMatchesQualifiedPng=sha256(preview).hexdigest() == hashes['page-1.png'])
            row['passed'] = all(row['checks'].values())
            records.append(row)
            assert row['passed'], row
            if fixture['name'] in ['inline-nested', 'contents-nested', 'block-nested']:
                page.locator('#pg-preview').scroll_into_view_if_needed()
                page.screenshot(path=str(folder / 'browser.png'), animations='disabled')
        report.update(ok=True, passed=len(records), failed=0,
            scope='Actual editor downloads and displayed previews for 41 retained quotation inputs; exact PDF text from two independent readers and qualified output hashes.')
    except BaseException as error:
        report['error'] = str(error)
        raise
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('All 41 quotation cases passed through the actual playground editor.', flush=True)
    return dict(ok=True, passed=len(records), fixtureSha256=report['fixtureSha256'], report='quotes/verification.json')
