"""Execute the authored notebook and inspect its saved PDF, HTML, previews and ZIP."""
from __future__ import annotations
from argparse import ArgumentParser
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZipFile
import json
import shutil
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import AsyncKernelManager
from jupyter_client.kernelspec import KernelSpecManager
from pypdf import PdfReader
import pypdfium2 as pdfium

DEFAULT_PDF = 'eb8f7c2b4fb5e123feb46a99e0521a7ab04181c0847c675076fe759e2d4bbf94'
def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')
def normalize(text):
    return ' '.join(text.split())
def compact(text):
    # pypdf splits tracked headings into one-character lines; PDFium below
    # independently checks word-level extraction from the same saved PDF.
    return ''.join(text.split())
class Markup(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.elements, self.text = [], []
        self.feed(source)
    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
    def handle_data(self, text):
        self.text.append(text)
def execute(notebook, work, destination, kernel_dir):
    notebook.cells.append(nbformat.v4.new_code_cell('''
import fullbleed, importlib.metadata, json
assert prepared.render_pdf() == pdf_path.read_bytes(), "Repeat rendering differs"
assert document.render_pdf(renderer, a11y_mode="raise") == pdf_path.read_bytes(), "Direct rendering differs"
Path("notebook-runtime.json").write_text(json.dumps({
    "version": importlib.metadata.version("fullbleed"),
    "inspection": dict(fullbleed.inspect_pdf(str(pdf_path))),
    "repeat_pdf_identical": True,
    "direct_pdf_identical": True,
    "preview_count": len(preview_paths),
}), encoding="utf-8")
'''))
    name = 'page-band-notebook-check'
    client = NotebookClient(notebook, km=AsyncKernelManager(kernel_name=name,
        kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel_dir)])), timeout=300,
        kernel_name=name, resources={'metadata':{'path':str(work)}})
    try:
        client.execute(cleanup_kc=True)
    finally:
        nbformat.write(notebook, destination / 'executed.ipynb')
def check(work, destination, name, controls, version):
    output = work / 'output'
    runtime = json.loads((work / 'notebook-runtime.json').read_text(encoding='utf-8'))
    inspection = runtime['inspection']
    assert runtime['version'] == version
    assert not inspection.get('warnings') and not inspection.get('composition', {}).get('issues')
    assert inspection['profile']['embedded_font_count'] >= 1
    pdf_path = output / 'field-notes.pdf'
    reader = PdfReader(pdf_path)
    texts = [normalize(page.extract_text() or '') for page in reader.pages]
    pages = len(texts)
    assert pages == inspection['page_count'] == runtime['preview_count']
    assert (pages > 3 if name == 'long' else pages == 3), (name, pages)
    markers = [controls['PROJECT_NAME'], controls['HEADLINE'], 'Keep the welcome growing.']
    markers += [str(row[0]) for row in controls['ACTIVITY']]
    text = normalize(' '.join(texts))
    assert all(compact(marker) in compact(text) for marker in markers), (name, markers)
    assert all(f'{index} / {pages}' in text for index, text in enumerate(texts, 1)), (name, texts)
    assert all(compact(controls['PROJECT_NAME'].upper()) in compact(text) for text in texts), (name, 'repeating header')
    for filename, styled in [('field-notes.styled.html', True), ('field-notes.unstyled.html', False)]:
        parsed = Markup((output / filename).read_text(encoding='utf-8'))
        tags = [tag for tag, attrs in parsed.elements]
        assert all(tags.count(tag) == 1 for tag in ('header', 'main', 'footer'))
        assert 'script' not in tags and not any(key.lower().startswith('on') for _, attrs in parsed.elements for key in attrs)
        assert 'studio' not in tags and 'notebooks' not in tags
        assert any('folio' in attrs.get('class', '').split() for _, attrs in parsed.elements)
        html_text = normalize(' '.join(parsed.text))
        assert all(normalize(marker) in html_text for marker in markers), (name, filename)
        assert '[page]' in html_text and '[pages]' in html_text
        assert ('style' in tags) == styled
        if not styled:
            assert not any('style' in attrs or (tag == 'link' and attrs.get('rel') == 'stylesheet') for tag, attrs in parsed.elements)
    previews = [f'field-notes-page-{index}.png' for index in range(1, pages + 1)]
    expected = ['field-notes.pdf', 'field-notes.styled.html', 'field-notes.unstyled.html', *previews]
    bundle_path = output / 'component-field-notes.zip'
    with ZipFile(bundle_path) as bundle:
        assert bundle.testzip() is None and len(bundle.namelist()) == len(set(bundle.namelist()))
        assert set(bundle.namelist()) == set(expected)
        assert all(bundle.read(filename) == (output / filename).read_bytes() for filename in expected)
    for filename in [*expected, bundle_path.name]:
        shutil.copyfile(output / filename, destination / filename)
    accent = tuple(int(controls['ACCENT'][index:index+2], 16) for index in (1, 3, 5))
    color_pixels = characters = 0
    styling_colors = {
        key: tuple(int(controls[key][index:index+2], 16) for index in (1, 3, 5))
        for key in ('PANEL_BACKGROUND', 'METRIC_COLOR', 'FOLIO_COLOR') if key in controls
    }
    styling_pixels = {key: 0 for key in styling_colors}
    independent_texts = []
    document = pdfium.PdfDocument(pdf_path)
    try:
        assert len(document) == pages
        for index in range(pages):
            page = document[index]
            textpage = page.get_textpage()
            independent_texts.append(normalize(textpage.get_text_range()))
            width, height = page.get_size()
            for number in range(textpage.count_chars()):
                char = textpage.get_text_range(number, 1)
                if not char or char.isspace():
                    continue
                x0, y0, x1, y1 = textpage.get_charbox(number)
                assert x0 >= -0.5 and y0 >= -0.5 and x1 <= width + 0.5 and y1 <= height + 0.5, (name, index + 1, char)
                characters += 1
            bitmap = page.render(scale=110 / 72)
            image = bitmap.to_pil().convert('RGB')
            colors = dict((color, count) for count, color in image.getcolors(image.width * image.height))
            color_pixels += colors.get(accent, 0)
            for key, color in styling_colors.items():
                styling_pixels[key] += colors.get(color, 0)
            image.save(destination / f'pdfium-page-{index + 1}.png')
            image.close(); bitmap.close(); textpage.close(); page.close()
    finally:
        document.close()
    independent_text = normalize(' '.join(independent_texts))
    assert all(normalize(marker) in independent_text for marker in markers)
    assert all(f'{index} / {pages}' in text for index, text in enumerate(independent_texts, 1))
    assert all(controls['PROJECT_NAME'].upper() in text for text in independent_texts)
    lesson_page, = [text for text in independent_texts if 'AUSEFULLESSON' in compact(text)]
    assert 'Make the first step visible.' in lesson_page, (name, 'Lesson heading separated from its body')
    assert color_pixels > 30, (name, color_pixels)
    # An eight-point folio has few fully covered pixels at preview resolution.
    # Presence is the color check; the separate image-isolation check below
    # establishes that the selector changes only the footer.
    assert all(count > (0 if key == 'FOLIO_COLOR' else 20)
               for key, count in styling_pixels.items()), (name, styling_pixels)
    result = dict(name=name, pages=pages, row_count=len(controls['ACTIVITY']), controls=controls,
        pdf_sha256=sha256(pdf_path.read_bytes()).hexdigest(), text_markers=markers,
        font_count=inspection['profile']['embedded_font_count'], accent=controls['ACCENT'], accent_pixels=color_pixels,
        independent_char_bounds_checked=characters, repeat_pdf_identical=True, direct_pdf_identical=True,
        zip_files=expected, styled_and_unstyled_html=True, finalized_page_counts=True, callout_kept_together=True,
        artifact_hashes={filename:sha256((destination / filename).read_bytes()).hexdigest() for filename in expected},
        styling_pixels=styling_pixels)
    if name == 'default':
        assert result['pdf_sha256'] == DEFAULT_PDF, 'Notebook default differs from the qualified source-kit PDF; inspect before claiming reproduction.'
        result['qualified_field_notes_pdf_reproduced'] = True
    save(destination / 'verification.json', result)
    save(destination / 'inspection.json', inspection)
    return result
def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--notebook', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--channel', choices=('alpha9', 'alpha10'), default='alpha9')
    parser.add_argument('--local-wheel', type=Path, help='Local qualification only: substitute this verified wheel for the public install cell.')
    args = parser.parse_args()
    version = '2.6.0a10' if args.channel == 'alpha10' else '2.6.0a9'
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source_path = args.notebook.resolve()
    source = nbformat.read(source_path, as_version=4)
    nbformat.validate(source)
    assert all(not cell.outputs and cell.execution_count is None for cell in source.cells if cell.cell_type == 'code')
    assert len({cell.id for cell in source.cells}) == len(source.cells)
    default = {}
    exec(next(cell.source for cell in source.cells if cell.id == 'report-controls'), {}, default)
    edited = deepcopy(default)
    edited.update(PROJECT_NAME='River <Studio>', HEADLINE='A place to meet & make.', ACCENT='#763c96')
    edited['ACTIVITY'][0] = ('Studio <notebooks> & cards', '16', '89 visits')
    if args.channel == 'alpha10':
        assert {'PANEL_BACKGROUND', 'METRIC_COLOR', 'FOLIO_COLOR', 'TITLE_SIZE'} <= default.keys()
        edited.update(PANEL_BACKGROUND='#f1e8f5', METRIC_COLOR='#8c2f6b',
                      FOLIO_COLOR='#206b7a', TITLE_SIZE=27)
    long = deepcopy(default)
    long['ACTIVITY'] = [(f'Session {number:02d}', str(number), '8 neighbors') for number in range(1, 73)]
    empty = deepcopy(default)
    empty['ACTIVITY'] = []
    cases = [('default', default), ('edited', edited)]
    if args.channel == 'alpha10':
        selector = deepcopy(default)
        selector['FOLIO_COLOR'] = '#206b7a'
        parts = deepcopy(default)
        parts['METRIC_COLOR'] = '#8c2f6b'
        cases += [('selector-only', selector), ('parts-only', parts)]
    cases += [('long', long), ('empty-after-long', empty)]
    work = out / 'work'
    work.mkdir()
    kernel = out / 'kernelspec/page-band-notebook-check'
    kernel.mkdir(parents=True)
    save(kernel / 'kernel.json', dict(argv=[sys.executable, '-I', '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
                                    display_name='Page-band notebook check', language='python'))
    reports = []
    for index, (name, controls) in enumerate(cases):
        notebook = deepcopy(source)
        for cell in notebook.cells:
            if cell.id == 'install-fullbleed':
                if index:
                    cell.metadata.setdefault('tags', []).append('skip-execution')
                elif args.local_wheel:
                    assert args.local_wheel.is_file()
                    cell.source = '%pip install --quiet --no-index --no-deps "' + args.local_wheel.resolve().as_posix() + '"'
            if cell.id == 'report-controls' and index:
                cell.source = '\n'.join(key + ' = ' + repr(value) for key, value in controls.items())
        destination = out / name
        destination.mkdir()
        execute(notebook, work, destination, kernel.parent)
        reports.append(check(work, destination, name, controls, version))
        print(json.dumps(dict(case=name, pages=reports[-1]['pages'], ok=True)), flush=True)
    assert len({row['pdf_sha256'] for row in reports}) == len(cases)
    if args.channel == 'alpha10':
        from PIL import Image, ImageChops
        isolation = {}
        for name in ('selector-only', 'parts-only'):
            differences = []
            for page in range(1, 4):
                base = Image.open(out / f'default/pdfium-page-{page}.png').convert('RGB')
                changed = Image.open(out / f'{name}/pdfium-page-{page}.png').convert('RGB')
                assert base.size == changed.size
                bbox = ImageChops.difference(base, changed).getbbox()
                differences.append(bbox)
                if name == 'selector-only':
                    assert bbox is not None and bbox[1] > base.height * .85, (name, page, bbox)
                elif page == 1:
                    assert bbox is not None
                else:
                    assert bbox is None, (name, page, bbox)
            isolation[name] = differences
        save(out / 'style-isolation.json', dict(ok=True, cases=isolation,
             scope='Selector-only changes stay in the footer on every page; named-part-only changes leave pages 2 and 3 identical.'))
    assert (work / 'output/field-notes-page-4.png').exists()
    assert 'field-notes-page-4.png' not in reports[-1]['zip_files']
    record = dict(ok=True, notebook=str(source_path), notebook_sha256=sha256(source_path.read_bytes()).hexdigest(),
        runtime_version=version, install_cell_executed=True, public_install_cell=not bool(args.local_wheel),
        local_install_override=bool(args.local_wheel), cases=reports, stale_previews_excluded=True,
        local_wheel=(dict(path=str(args.local_wheel.resolve()), sha256=sha256(args.local_wheel.read_bytes()).hexdigest()) if args.local_wheel else None),
        checked_at=datetime.now(timezone.utc).isoformat(),
        scope='Jupyter kernel execution, independent saved-PDF inspection, repeat rendering, HTML semantics, and ZIP contents. Browser downloads and hosted Colab are separate checks.')
    save(out / 'verification.json', record)
    print(json.dumps(dict(ok=True, cases=len(reports), pages=sum(row['pages'] for row in reports))), flush=True)
if __name__ == '__main__':
    main()
