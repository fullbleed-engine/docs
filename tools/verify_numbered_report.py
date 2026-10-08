"""Execute the downloadable report, edit it, and inspect both PDFs independently."""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import argparse
import json
import os
import platform
import re
import subprocess
import sys
import zipfile

from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'docs/assets/numbered-report'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'output/numbered-report-verification')
    parser.add_argument('--expected-version', default='2.5.18')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    assert version('fullbleed') == args.expected_version
    manifest = json.loads((ASSETS/'source.json').read_text(encoding='utf-8'))
    archive_path = ASSETS/'project.zip'
    assert sha256(archive_path.read_bytes()).hexdigest() == manifest['zip_sha256']
    extracted = out/'project with spaces'
    extracted.mkdir()
    project = extracted/'fullbleed-numbered-report'
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'fullbleed-numbered-report/'+r['path'] for r in manifest['files']}
        for item in manifest['files']:
            data = archive.read('fullbleed-numbered-report/'+item['path'])
            assert len(data) == item['bytes'] and sha256(data).hexdigest() == item['sha256']
            assert data == (ROOT/'examples/numbered-report'/item['path']).read_bytes()
            path = project/item['path']
            assert path.resolve().is_relative_to(project.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def run(label):
        destination = out/label
        result = subprocess.run([sys.executable, '-I', str(project/'render.py'), '--out', str(destination)],
            cwd=out, env={**os.environ, 'PYTHONUTF8':'1', 'PYTHONPATH':''},
            capture_output=True, text=True, encoding='utf-8', timeout=120)
        (out/(label+'.stdout.txt')).write_text(result.stdout, encoding='utf-8')
        (out/(label+'.stderr.txt')).write_text(result.stderr, encoding='utf-8')
        assert result.returncode == 0, (label, result.stderr)
        record = json.loads((destination/'render.json').read_text())
        assert record['deterministic_replay'] and not record['missing_glyphs']
        assert record['version'] == args.expected_version
        return destination

    def inspect(folder, sections, pages=None):
        path = folder/'numbered-report.pdf'
        reader = PdfReader(path)
        assert len(reader.pages) == pages if pages else len(reader.pages) > 0
        text = '\n'.join(page.extract_text() for page in reader.pages)
        assert re.findall(r'\b[12]\.[1-4]\b', text) == sections, text
        compact = re.sub(r'\s+', '', text)
        for label in ['01Projectbrief', '02Workingprototype', '03Handoffpackage']:
            assert label in compact, (label, text)
        fonts = [ref.get_object() for page in reader.pages for ref in page['/Resources']['/Font'].values()]
        assert fonts and all(font.get('/Subtype') == '/Type0' and
            '/FontFile2' in font['/DescendantFonts'][0]['/FontDescriptor'] for font in fonts)
        other = []
        with pdfium.PdfDocument(str(path)) as document:
            for i in range(len(document)):
                page = document[i]
                textpage = page.get_textpage()
                other.append(textpage.get_text_range())
                boxes = [textpage.get_charbox(j) for j in range(textpage.count_chars())]
                painted = [(l,b,r,t) for l,b,r,t in boxes if r > l and t > b]
                assert painted and all(l >= -.2 and b >= -.2 and r <= page.get_width()+.2 and t <= page.get_height()+.2
                                       for l,b,r,t in painted), (folder.name, i, 'text outside page')
                page.render(scale=110/72).to_pil().save(folder/f'pdfium-{i+1}.png')
                textpage.close()
                page.close()
        other = '\n'.join(other)
        assert re.findall(r'\b[12]\.[1-4]\b', other) == sections, other
        assert '\ufffd' not in text+other
        if pages:
            assert all(f'{i+1} / {pages}' in page.extract_text() for i, page in enumerate(reader.pages))
        (folder/'pypdf.txt').write_text(text, encoding='utf-8')
        (folder/'pdfium.txt').write_text(other, encoding='utf-8')
        return dict(pages=len(reader.pages), sha256=sha256(path.read_bytes()).hexdigest(), sections=sections,
                    two_independent_readers=True, embedded_fonts=True, text_within_page_bounds=True)

    baseline = inspect(run('render'), ['1.1','1.2','1.3','2.1','2.2','2.3'], pages=2)
    html = (project/'report.html').read_text(encoding='utf-8')
    marker = '  <h2 class="chapter next-page">'
    assert html.count(marker) == 1
    html = html.replace(marker, '  <h3 class="section">Assign the next owner</h3>\n'+marker)
    (project/'report.html').write_text(html, encoding='utf-8')
    edited = inspect(run('edited'), ['1.1','1.2','1.3','1.4','2.1','2.2','2.3'])
    assert edited['sha256'] != baseline['sha256']
    result = dict(ok=True, platform=platform.system(), version=version('fullbleed'),
        zip_sha256=manifest['zip_sha256'], baseline=baseline, edited=edited,
        scope='This downloaded report and one inserted section; no complete CSS counter or PDF standards conformance claim.')
    (out/'verification.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
