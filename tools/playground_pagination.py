"""Independent pagination checks shared by playground exports and browser QA."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from pypdf import PdfReader
import pypdfium2 as pdfium

FIXTURES = Path(__file__).with_name('playground-fixtures') / 'pagination.json'


def cases():
    return json.loads(FIXTURES.read_text(encoding='utf-8'))['cases']


def inspect_pdf(path, case):
    reader = PdfReader(path)
    texts = [page.extract_text() for page in reader.pages]
    checks = {'page_count': len(texts) == case['pages']}
    if case['kind'] == 'table':
        checks['every_row_once'] = Counter(re.findall(r'ROW-\s*(\d{3})', '\n'.join(texts))) == Counter(f'{i:03}' for i in range(1, 81))
        checks['repeated_headers'] = all('Record' in text and 'Details' in text for text in texts if 'ROW-' in text)
    elif case['kind'] == 'break':
        checks['both_markers'] = bool(texts) and 'BEFORE' in texts[0] and 'AFTER' in texts[-1]
        if case['pages'] == 2:
            checks['break_separates_markers'] = len(texts) == 2 and 'AFTER' not in texts[0] and 'BEFORE' not in texts[1]
    else:
        checks['preceding_line_retained'] = len(texts) == 2 and 'First line stays here' in texts[0] and 'First line stays here' not in texts[1]
        checks['footnotes_follow_call'] = len(texts) == 2 and 'Second line has notes' not in texts[0] and all(value in texts[1] for value in ['Second line has notes', 'first note', 'second note'])
    outside = 0
    with pdfium.PdfDocument(path) as document:
        for page in document:
            width, height = page.get_size()
            text = page.get_textpage()
            try:
                for index in range(text.count_chars()):
                    if text.get_text_range(index, 1).strip():
                        left, bottom, right, top = text.get_charbox(index)
                        outside += int(left < -0.1 or bottom < -0.1 or right > width + 0.1 or top > height + 0.1)
            finally:
                text.close()
                page.close()
    checks['glyphs_inside_pages'] = outside == 0
    return {'name': case['name'], 'pages': len(texts), 'off_page_glyphs': outside,
            'passed': all(checks.values()), 'checks': checks, 'pdf_sha256': sha256(path.read_bytes()).hexdigest()}


def check_browser(page, out, check, ready, edit, reference):
    """Paste real editor inputs and retain every displayed page and PDF download."""
    from playwright.sync_api import expect
    evidence = out / 'pagination'
    evidence.mkdir(exist_ok=False)
    original = (page.locator('#pg-html').input_value(), page.locator('#pg-css').input_value())
    records = []
    for case in cases():
        name = case['name']
        edit(case['html'], case['css'])
        page.locator('#pg-render').click()
        ready()
        with page.expect_download() as event:
            page.locator('#pg-download').click()
        path = evidence / (name + '.pdf')
        event.value.save_as(path)
        record = inspect_pdf(path, case)
        for label, passed in record['checks'].items():
            check(name + ': ' + label, passed)
        expected = next(item for item in reference['fixtures'] if item['name'] == name)
        check(name + ': browser PDF matches the native/WASI result', record['pdf_sha256'] == expected['hashes']['output.pdf'])
        previews = []
        for number in range(1, case['pages'] + 1):
            expect(page.locator('#pg-page-count')).to_have_text(f"{number} / {case['pages']}")
            data = bytes(page.locator('#pg-preview').evaluate('''async image => {
                await image.decode();
                return Array.from(new Uint8Array(await (await fetch(image.src)).arrayBuffer()));
            }'''))
            preview = evidence / f'{name}-{number}.png'
            preview.write_bytes(data)
            check(f'{name}: displayed page {number} matches the native/WASI preview',
                  sha256(data).hexdigest() == expected['hashes'][f'page-{number}.png'])
            previews.append(sha256(data).hexdigest())
            if number < case['pages']:
                page.locator('#pg-next').click()
        records.append({**record, 'preview_sha256': previews})
    edit(*original)
    page.locator('#pg-render').click()
    ready()
    record = {'ok': True, 'fixture_sha256': sha256(FIXTURES.read_bytes()).hexdigest(), 'cases': records}
    (evidence / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    return record
