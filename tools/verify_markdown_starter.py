"""Verify the actual Markdown ZIP, CLI failures, fonts, images, and rendered pages."""
from hashlib import sha256
from importlib import metadata, resources
from pathlib import Path
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import zipfile

from fontTools.ttLib import TTFont
from io import BytesIO
from PIL import Image
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/markdown-starter'


def compact(text):
    return ''.join(text.split())


def faces(reader):
    names = set()
    for page in reader.pages:
        for ref in page['/Resources']['/Font'].values():
            font = ref.get_object()
            for item in font.get('/DescendantFonts', [font]):
                descriptor = item.get_object().get('/FontDescriptor')
                if descriptor is not None:
                    program = descriptor.get_object().get('/FontFile2')
                    if program is not None:
                        with TTFont(BytesIO(program.get_object().get_data())) as parsed:
                            names.add(parsed['name'].getDebugName(6))
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'output/markdown-verification')
    parser.add_argument('--update-assets', action='store_true')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, commands = [], []
    report = {'ok': False, 'platform': platform.system(), 'versions': {
        name: metadata.version(name) for name in ['fullbleed', 'markdown-it-py', 'pypdf', 'pypdfium2', 'fonttools', 'pillow']},
        'checks': checks, 'commands': commands}

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        checks.append(name)

    def run(label, arguments, expected=0):
        result = subprocess.run([sys.executable, '-I', str(project / 'render.py'), *map(str, arguments)],
                                cwd=out, env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONPATH': ''},
                                capture_output=True, text=True, encoding='utf-8', timeout=120)
        (out / f'{label}.stdout.txt').write_text(result.stdout, encoding='utf-8')
        (out / f'{label}.stderr.txt').write_text(result.stderr, encoding='utf-8')
        commands.append({'label': label, 'exit': result.returncode})
        check(label + ' exit status', result.returncode == expected)
        return result

    try:
        check('pinned engine and parser', metadata.version('fullbleed') == '2.5.10'
              and metadata.version('markdown-it-py') == '4.2.0')
        manifest = json.loads((ASSETS / 'source.json').read_text(encoding='utf-8'))
        archive_path = ASSETS / 'project.zip'
        check('ZIP digest', sha256(archive_path.read_bytes()).hexdigest() == manifest['zip_sha256'])
        with zipfile.ZipFile(archive_path) as archive:
            check('ZIP has exactly the documented files', set(archive.namelist()) ==
                  {'fullbleed-markdown-starter/' + item['path'] for item in manifest['files']})
            for item in manifest['files']:
                data = archive.read('fullbleed-markdown-starter/' + item['path'])
                check('source and digest: ' + item['path'], data == (ROOT / 'examples/markdown' / item['path']).read_bytes()
                      and sha256(data).hexdigest() == item['sha256'])
            archive.extractall(out / 'project with spaces')
        project = out / 'project with spaces/fullbleed-markdown-starter'
        guide = (ROOT / 'docs/guides/markdown-pdf.md').read_text(encoding='utf-8')
        check('guide and README use the verified command', all(
            'python render.py brief.md --out output --title "Release notes that travel"' in text
            for text in [guide, (project / 'README.md').read_text(encoding='utf-8')]))
        check('dependencies remain an explicit optional starter', (project / 'requirements.txt').read_text(encoding='utf-8').splitlines()
              == ['fullbleed==2.5.10', 'markdown-it-py==4.2.0', 'mdurl==0.1.2'])
        sample = out / 'render'
        run('sample', [project / 'brief.md', '--out', sample, '--title', 'Release notes that travel'])
        reader = PdfReader(sample / 'document.pdf')
        text = ' '.join(' '.join(page.extract_text() for page in reader.pages).split())
        (out / 'sample-text.txt').write_text(text, encoding='utf-8')
        render = json.loads((sample / 'render.json').read_text(encoding='utf-8'))
        check('two-page sample with title', len(reader.pages) == 2 and reader.metadata.title == 'Release notes that travel')
        # Readers can synthesize spaces between separately positioned glyphs
        # in letter-spaced headings. Compare content without those spaces.
        check('complete representative content', all(compact(needle) in compact(text) for needle in [
            'Release notes that travel', 'Markdown', 'HTML + CSS', 'PDF', 'Deliverable Owner Review evidence',
            'from markdown_it import MarkdownIt', 'Review before sharing', 'Edit print.css to change the paper size',
            'does not claim PDF/A or PDF/UA conformance.']))
        embedded = faces(reader)
        check('both intended fonts are embedded', 'IBMPlexMono-Regular' in embedded and any('Inter' in face for face in embedded))
        check('glyph report is empty', json.loads((sample / 'glyph-report.json').read_text(encoding='utf-8')) == [])
        check('local SVG registered', len(render['images']) == 1 and render['images'][0]['path'] == 'images/publishing.svg')
        check('finalized native previews recorded', len(render['previews']) == 2
              and all((sample / path).is_file() for path in render['previews']))
        with pdfium.PdfDocument(sample / 'document.pdf') as document:
            for index in range(len(document)):
                page = document[index]
                textpage = page.get_textpage()
                independent_text = textpage.get_text_range()
                check(f'PDFium page {index + 1} has text', len(independent_text) > 500)
                if index == 1:
                    start = independent_text.index('Edit print.css to change')
                    prefix = [textpage.get_charbox(start + i) for i in range(4)]
                    code = [textpage.get_charbox(start + i) for i in range(5, 14)]
                    after = textpage.get_charbox(start + 15)
                    check('inline code does not overlap the surrounding words',
                          max(b[2] for b in prefix) < min(b[0] for b in code)
                          and max(b[2] for b in code) < after[0])
                bitmap = page.render(scale=110 / 72)
                image = bitmap.to_pil()
                image.save(out / f'pdfium-{index + 1}.png')
                check(f'PDFium page {index + 1} has visible ink', image.convert('RGB').getextrema() != ((255, 255),) * 3)
                image.close()
                bitmap.close()
                textpage.close()
                page.close()

        run('repeat', [project / 'brief.md', '--out', out / 'repeat', '--title', 'Release notes that travel'])
        check('repeat PDF bytes match', (sample / 'document.pdf').read_bytes() == (out / 'repeat/document.pdf').read_bytes())
        repeated = json.loads((out / 'repeat/render.json').read_text(encoding='utf-8'))
        check('repeat preview bytes match', all((sample / first).read_bytes() == (out / 'repeat' / second).read_bytes()
              for first, second in zip(render['previews'], repeated['previews'])))

        edited = project / 'edited.md'
        edited.write_text('# Edited field note\n\n**Bold** and *italic* and ~~old~~ and `inline code`.\n\n'
                          '> A short quotation.\n\n- One bullet\n- Another bullet\n\n1. First step\n2. Second step\n\n'
                          '| Item | Status |\n|---|---|\n| Changed | Ready |\n\n'
                          '```python\nopen("executed-marker", "w").write("bad")\n```\n\n'
                          '<script>window.example = 1</script>\n\n[Docs](https://docs.fullbleed.dev/)\n', encoding='utf-8')
        custom_css = project / 'custom.css'
        custom_css.write_text((project / 'print.css').read_text(encoding='utf-8') + '\n@page {size:Letter;margin:30pt} h1 {color:#243c69}\n', encoding='utf-8')
        run('edited', [edited, '--out', out / 'edited', '--css', custom_css, '--title', 'Edited field note', '--no-preview'])
        edited_reader = PdfReader(out / 'edited/document.pdf')
        edited_text = ' '.join(' '.join(p.extract_text() for p in edited_reader.pages).split())
        check('content and CSS customization', len(edited_reader.pages) == 1
              and list(edited_reader.pages[0].mediabox)[2:] == [612, 792]
              and all(compact(s) in compact(edited_text) for s in ['Edited field note', 'One bullet', 'Second step', 'Changed', 'Ready']))
        check('code and raw HTML are inert text', not (out / 'executed-marker').exists()
              and '&lt;script&gt;' in (out / 'edited/document.html').read_text(encoding='utf-8')
              and 'window.example' in edited_text)
        check('no-preview produces no preview list', json.loads((out / 'edited/render.json').read_text(encoding='utf-8'))['previews'] == [])

        image_dir = project / 'images'
        Image.new('RGB', (32, 16), '#243c69').save(image_dir / 'blue square.png')
        Image.new('RGB', (32, 16), '#c45331').save(image_dir / 'orange.jpg')
        image_doc = project / 'images.md'
        image_doc.write_text('# Local images\n\n![Blue](images/blue%20square.png)\n\n![Orange](images/orange.jpg)\n\n'
                             '![Diagram](images/publishing.svg)\n', encoding='utf-8')
        run('images', [image_doc, '--out', out / 'images'])
        check('PNG, JPEG, SVG, and URL-encoded paths', len(json.loads((out / 'images/render.json').read_text(encoding='utf-8'))['images']) == 3)
        noto = Path(str(resources.files('fullbleed_assets').joinpath('fonts/NotoSans-Regular.ttf')))
        custom_css.write_text(custom_css.read_text(encoding='utf-8') + '\nbody {font-family:"Noto Sans"}\n', encoding='utf-8')
        run('extra-font', [edited, '--out', out / 'extra-font', '--css', custom_css, '--font', noto, '--no-preview'])
        check('additional TTF selected and embedded', 'NotoSans-Regular' in faces(PdfReader(out / 'extra-font/document.pdf')))

        bad = project / 'invalid.md'
        def reject(label, content, expected_message):
            bad.write_text(content, encoding='utf-8')
            result = run(label, [bad, '--out', out / label, '--no-preview'], expected=1)
            check(label + ' diagnostic and no new PDF', expected_message in result.stderr and not (out / label / 'document.pdf').exists())

        reject('empty', ' \n\t', 'empty')
        reject('remote-image', '![image](https://example.invalid/image.png)', 'local image path')
        reject('missing-image', '![image](missing.png)', 'does not exist')
        reject('outside-image', '![image](../outside.png)', 'outside')
        reject('absolute-image', '![image](/image.png)', 'relative image path')
        reject('unsupported-image', '![image](brief.md)', 'PNG, JPEG, or SVG')
        reject('oversized-markdown', 'a' * 4_000_001, 'exceeds')
        large_image = image_dir / 'too-large.png'
        with large_image.open('wb') as stream:
            stream.truncate(16 * 1024 * 1024 + 1)
        reject('oversized-image', '![image](images/too-large.png)', '16 MiB')
        custom_css.write_text(' ' * 4_000_001, encoding='utf-8')
        result = run('oversized-css', [edited, '--css', custom_css, '--out', out / 'oversized-css'], expected=1)
        check('oversized CSS diagnostic', 'exceeds' in result.stderr)
        result = run('missing-font', [edited, '--font', project / 'missing.ttf', '--out', out / 'missing-font'], expected=1)
        check('missing extra font diagnostic', 'Font does not exist' in result.stderr)
        font = project / 'fonts/IBMPlexMono-Regular.ttf'
        original = font.read_bytes()
        font.write_bytes(b'changed font')
        result = run('changed-font', [edited, '--out', out / 'changed-font'], expected=1)
        check('modified bundled font rejected', 'bundled IBM Plex Mono font changed' in result.stderr)
        font.write_bytes(original)

        missing_out = out / 'missing-glyph'
        missing_out.mkdir()
        sentinel = b'previous output must survive a failed render'
        (missing_out / 'document.pdf').write_bytes(sentinel)
        bad.write_text('# Missing glyph\n\n' + chr(0x10FFFF), encoding='utf-8')
        result = run('missing-glyph', [bad, '--out', missing_out], expected=1)
        check('missing glyph diagnosed without replacing prior output', 'Missing glyphs' in result.stderr
              and json.loads((missing_out / 'glyph-report.json').read_text(encoding='utf-8'))
              and (missing_out / 'document.pdf').read_bytes() == sentinel)
        conflict = out / 'input-conflict'
        conflict.mkdir()
        input_path = conflict / 'document.html'
        input_path.write_text('# Keep this source\n', encoding='utf-8')
        result = run('input-conflict', [input_path, '--out', conflict], expected=1)
        check('output cannot replace the input', 'overwrite an input' in result.stderr and input_path.read_text(encoding='utf-8') == '# Keep this source\n')

        bad.write_text('# Many paragraphs\n\n' + ('A paragraph for testing pagination and changing document length. ' * 8 + '\n\n') * 30, encoding='utf-8')
        changing = out / 'changing'
        run('long-document', [bad, '--out', changing])
        long_report = json.loads((changing / 'render.json').read_text(encoding='utf-8'))
        bad.write_text('# Short document\n\nOne paragraph.\n', encoding='utf-8')
        run('short-document', [bad, '--out', changing])
        short_report = json.loads((changing / 'render.json').read_text(encoding='utf-8'))
        check('shorter rerender records only its current page', len(long_report['previews']) > 1
              and len(short_report['previews']) == 1 and set(long_report['previews']).isdisjoint(short_report['previews'])
              and all((changing / path).exists() for path in long_report['previews'] + short_report['previews']))

        report.update(sample_pdf_sha256=sha256((sample / 'document.pdf').read_bytes()).hexdigest(),
                      sample_pages=2, embedded_faces=sorted(embedded), sample_render=render)
        if args.update_assets:
            shutil.copyfile(sample / 'document.pdf', ASSETS / 'document.pdf')
            for i, preview in enumerate(render['previews'], 1):
                shutil.copyfile(sample / preview, ASSETS / f'page-{i}.png')
        check('published PDF matches the rendered sample',
              (ASSETS / 'document.pdf').read_bytes() == (sample / 'document.pdf').read_bytes())
        check('published native previews match the rendered sample', all(
            (ASSETS / f'page-{i}.png').read_bytes() == (sample / preview).read_bytes()
            for i, preview in enumerate(render['previews'], 1)))
        report['ok'] = True
        if args.update_assets:
            (ASSETS / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'ok': True, 'checks': len(checks), 'commands': len(commands), 'pdf_sha256': report['sample_pdf_sha256']}))
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
