"""Independently inspect the page-font fixtures' actual PDF text and faces."""
from hashlib import sha256
import json
from pathlib import Path

from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / 'tools/playground-fixtures/page-margin-fonts-2.5.48.json'
ENGINE = '2.5.51'
NODE = '0.9.4'


def fixtures():
    source = json.loads(FIXTURE_PATH.read_bytes())
    assert len(source['cases']) == 8
    for font in source['fonts']:
        assert sha256((ROOT / font['path']).read_bytes()).hexdigest() == font['sha256']
    return source


def inspect_pdf(path, specimen, out):
    path, out = Path(path), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    reader = PdfReader(path)
    assert len(reader.pages) == len(specimen['footerFaces'])
    pages = []
    with pdfium.PdfDocument(path) as independent:
        assert len(independent) == len(reader.pages)
        for index, (page, face) in enumerate(zip(reader.pages, specimen['footerFaces'])):
            footer = []
            def visit(text, cm, tm, font, size):
                if 'FOOTER' in text:
                    assert font is not None
                    actual = str(font['/BaseFont'])
                    descendant = font['/DescendantFonts'][0].get_object() if '/DescendantFonts' in font else font
                    descriptor = descendant['/FontDescriptor'].get_object()
                    embedded = any(key in descriptor and len(descriptor[key].get_object().get_data()) > 0 for key in ['/FontFile', '/FontFile2', '/FontFile3'])
                    footer.append({'text': ' '.join(text.split()), 'face': actual, 'size': size, 'embedded': embedded})
            page.extract_text(visitor_text=visit)
            assert len(footer) == 1, footer
            row = footer[0]
            assert row['text'] == f'FOOTER {index + 1} of {len(reader.pages)}', row
            assert row['face'].endswith(face) and row['embedded'], row
            assert abs(row['size'] - specimen['footerSize']) < 0.001, row
            other_page = independent[index]
            textpage = other_page.get_textpage()
            assert row['text'] in ' '.join(textpage.get_text_range().split())
            textpage.close()
            bitmap = other_page.render(scale=2)
            image = bitmap.to_pil().convert('RGB')
            try:
                row.update(pixelsSha256=sha256(image.tobytes()).hexdigest(), pixelSize=list(image.size))
                image.save(out / f'page-{index + 1}.png')
            finally:
                image.close()
                bitmap.close()
                other_page.close()
            pages.append(row)
    return {'pdfSha256': sha256(path.read_bytes()).hexdigest(), 'pages': pages}
