"""Independent acceptance checks for the two static-HTML order fixtures."""
from hashlib import sha256
import re
import unicodedata
from pypdf import PdfReader
import pypdfium2 as pdfium

def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).replace('\u00ad', '').split())

def inspect(pdf_path, record, out):
    out.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(pdf_path, strict=True)
    expected_codes = [item['code'] for item in record['items']]
    total = sum(item['quantity'] * item['unitCents'] for item in record['items'])
    texts = [page.extract_text() for page in reader.pages]
    text = normalize(' '.join(texts))
    assert re.findall(r'\bFN-\d{3}\b', text) == expected_codes, 'Line items missing, repeated or out of order'
    for item in record['items']:
        assert normalize(item['name']) in text and normalize(item['description']) in text, item['code']
    assert normalize(record['customer']) in text
    assert f'${total / 100:.2f}' in normalize(texts[-1])
    assert 'No payment is requested.' in normalize(texts[-1])
    assert 'tracking details' in normalize(texts[-1])
    assert f"{len(record['items'])} line items" in normalize(texts[-1])
    assert len(reader.pages) == 1 if len(record['items']) == 3 else len(reader.pages) >= 2
    fonts = set()
    for number, page in enumerate(reader.pages, 1):
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        assert abs(width - 595.2756) < 1 and abs(height - 841.8898) < 1, 'Not A4'
        compact = re.sub(r'\s+', '', texts[number - 1]).casefold()
        assert f'page{number}of{len(reader.pages)}' in compact, 'Missing or wrong page counter'
        if re.search(r'\bFN-\d{3}\b', texts[number - 1]):
            assert 'thegoodstuff' in compact, 'Missing table headings'
        for font in page['/Resources'].get('/Font', {}).get_object().values():
            font = font.get_object()
            name = str(font['/BaseFont'])
            fonts.add(name)
            assert 'sourcesans3' in name.lower(), 'Unexpected font substitution: ' + name
            descendant = font['/DescendantFonts'][0].get_object() if '/DescendantFonts' in font else font
            descriptor = descendant['/FontDescriptor'].get_object()
            assert any(key in descriptor for key in ['/FontFile', '/FontFile2', '/FontFile3']), 'Font is not embedded'
    assert any('bold' in name.lower() for name in fonts) and any('regular' in name.lower() for name in fonts), 'Expected both supplied static faces'
    pages, independent = [], []
    with pdfium.PdfDocument(pdf_path) as document:
        for number in range(len(document)):
            page = document[number]
            textpage = page.get_textpage()
            independent.append(textpage.get_text_range())
            width, height = page.get_size()
            boxes = []
            for index in range(textpage.count_chars()):
                char = textpage.get_text_range(index, 1)
                if not char or char.isspace():
                    continue
                left, bottom, right, top = textpage.get_charbox(index)
                assert min(left, bottom) >= -0.25 and right <= width + 0.25 and top <= height + 0.25, (number + 1, char, [left, bottom, right, top])
                boxes.append([left, bottom, right, top])
            image = page.render(scale=96 / 72).to_pil().convert('RGB')
            path = out / f'page-{number + 1}.png'
            image.save(path)
            if number == 0:
                orange = sum(all(abs(actual - expected) <= 12 for actual, expected in zip(pixel, (198, 101, 66)))
                             for pixel in image.crop((50, 40, 150, 140)).getdata())
                assert orange > 100, 'The supplied logo is missing from its header position'
            pages.append({'page': number + 1, 'characters': len(boxes), 'allTextWithinPage': True,
                          'previewSha256': sha256(path.read_bytes()).hexdigest()})
            textpage.close()
            page.close()
    independent_text = normalize(' '.join(independent))
    assert re.findall(r'\bFN-\d{3}\b', independent_text) == expected_codes
    for item in record['items']:
        assert normalize(item['name']) in independent_text and normalize(item['description']) in independent_text
    return {'ok': True, 'pages': len(reader.pages), 'items': len(expected_codes), 'totalCents': total,
            'pdfSha256': sha256(pdf_path.read_bytes()).hexdigest(), 'fonts': sorted(fonts),
            'embeddedBrandFont': True, 'localLogoVisible': True, 'lineItemsOnceAndInOrder': True,
            'closingTogetherOnFinalPage': True, 'pageChecks': pages}
