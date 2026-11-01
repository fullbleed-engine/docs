"""Read actual text-font selections in saved playground and exported-project PDFs."""
from hashlib import sha256
import json
from pathlib import Path
import re

from pypdf import PdfReader
from pypdf.generic import ContentStream
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tools/playground-fixtures/font-cascade-2.5.51.json'


def cases():
    rows = json.loads(FIXTURES.read_bytes())['cases']
    assert len(rows) == len({row['name'] for row in rows}) == 13
    return rows


def inspect_pdf(path, fixture, preview=None):
    reader = PdfReader(path, strict=True)
    text = ' '.join(' '.join(page.extract_text() or '' for page in reader.pages).split())
    fonts = set()
    for page in reader.pages:
        stream = ContentStream(page.get_contents(), reader)
        used = {str(args[0]) for args, operator in stream.operations if operator == b'Tf'}
        mapping = page['/Resources']['/Font']
        fonts.update(str(mapping[key].get_object()['/BaseFont']).removeprefix('/') for key in used)
    independent, pixels, visible = [], [], []
    with pdfium.PdfDocument(path) as document:
        for page in document:
            textpage = page.get_textpage()
            try:
                independent.append(textpage.get_text_range())
            finally:
                textpage.close()
            bitmap = page.render(scale=1)
            try:
                image = bitmap.to_pil().convert('RGB')
                pixels.append(sha256(image.tobytes()).hexdigest())
                visible.append(min(channel[0] for channel in image.getextrema()) < 180)
                if preview is not None:
                    image.save(preview)
                image.close()
            finally:
                bitmap.close()
                page.close()
    independent = ' '.join(' '.join(independent).split())
    checks = dict(pageCount=len(reader.pages) == fixture['pages'] == 1,
                  pypdfText=text == 'Font witness', pdfiumText=independent == 'Font witness',
                  textFontSelection=sorted(fonts) == fixture['expectedBaseFonts'],
                  visibleIndependentOutput=bool(visible) and all(visible))
    return dict(name=fixture['name'], passed=all(checks.values()), checks=checks,
                actualBaseFonts=sorted(fonts), expectedBaseFonts=fixture['expectedBaseFonts'],
                text=text, pdfiumText=independent, pdfSha256=sha256(Path(path).read_bytes()).hexdigest(),
                pdfiumPixelSha256=pixels)


def check_browser(page, out, reference):
    """Check actual editor downloads, including the visible finalized-PDF preview."""
    from playwright.sync_api import expect
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    expected = {row['name']: row['hashes'] for row in reference['fixtures']}
    records = []
    for fixture in cases():
        page.locator('#pg-html-tab').click()
        page.locator('#pg-html').fill(fixture['html'])
        page.locator('#pg-css-tab').click()
        page.locator('#pg-css').fill(fixture['css'])
        page.locator('#pg-render').click()
        expect(page.locator('#pg-download')).to_have_attribute('href', re.compile('^blob:'), timeout=120000)
        expect(page.locator('#pg-status')).to_contain_text('Your PDF is ready.')
        with page.expect_download() as event:
            page.locator('#pg-download').click()
        pdf = out / (fixture['name'] + '.pdf')
        event.value.save_as(pdf)
        row = inspect_pdf(pdf, fixture, out / (fixture['name'] + '-pdfium.png'))
        preview_url = page.locator('#pg-preview').get_attribute('src')
        assert preview_url.startswith('blob:')
        preview = bytes(page.evaluate('''async url => Array.from(new Uint8Array(
            await (await fetch(url)).arrayBuffer()))''', preview_url))
        (out / (fixture['name'] + '-native.png')).write_bytes(preview)
        row['checks'].update(downloadMatchesReference=row['pdfSha256'] == expected[fixture['name']]['output.pdf'],
                             previewMatchesReference=sha256(preview).hexdigest() == expected[fixture['name']]['page-1.png'])
        row['passed'] = all(row['checks'].values())
        records.append(row)
    report = dict(ok=all(row['passed'] for row in records), cases=records,
                  fixtureSha256=sha256(FIXTURES.read_bytes()).hexdigest())
    (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    assert report['ok'], records
    return dict(ok=True, cases=len(records), report='font-cascade/verification.json')
