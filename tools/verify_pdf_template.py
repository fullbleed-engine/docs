"""Exercise the downloadable template, edited data, boundaries and rejected inputs."""
import argparse
from datetime import date
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import zipfile

from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/pdf-template'
MONTHS = ('', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'output/pdf-template-verification')
    parser.add_argument('--expected-version', default='2.5.39')
    args = parser.parse_args()
    assert version('fullbleed') == args.expected_version
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ASSETS / 'source.json').read_text(encoding='utf-8'))
    archive_path = ASSETS / 'project.zip'
    assert sha256(archive_path.read_bytes()).hexdigest() == manifest['zip_sha256']
    project = out / 'project with spaces/fullbleed-pdf-template'
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'fullbleed-pdf-template/' + row['path'] for row in manifest['files']}
        for row in manifest['files']:
            data = archive.read('fullbleed-pdf-template/' + row['path'])
            assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256']
            assert data == (ROOT / 'examples/pdf-template' / row['path']).read_bytes()
            path = project / row['path']
            assert path.resolve().is_relative_to(project.resolve())
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    template = project / 'template.pdf'
    template_hash = sha256(template.read_bytes()).hexdigest()
    default_records = json.loads((project / 'data.json').read_text(encoding='utf-8'))
    commands = []

    def run(label, data=None, custom_template=None, expected=0):
        destination = out / label
        command = [sys.executable, '-I', '-X', 'utf8', str(project / 'render.py'), '--out', str(destination)]
        if data is not None:
            path = out / (label + '-data.json')
            path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
            command += ['--data', str(path)]
        if custom_template:
            command += ['--template', str(custom_template)]
        result = subprocess.run(command, cwd=out, env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONPATH': ''}, capture_output=True, text=True, encoding='utf-8', timeout=120)
        (out / (label + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
        (out / (label + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
        commands.append(dict(label=label, exitCode=result.returncode))
        assert result.returncode == expected, (label, result.stderr)
        assert sha256(template.read_bytes()).hexdigest() == template_hash
        if expected:
            assert not (destination / 'certificates.pdf').exists()
            return None
        record = json.loads((destination / 'render.json').read_text(encoding='utf-8'))
        assert record['version'] == args.expected_version
        assert record['deterministic_repeat'] and record['template_unchanged'] and not record['missing_glyphs']
        assert (destination / 'certificates.pdf').read_bytes() == (destination / 'certificates-repeat.pdf').read_bytes()
        return destination

    def inspect(folder, records, heading='CERTIFICATE OF PARTICIPATION'):
        path = folder / 'certificates.pdf'
        reader = PdfReader(path, strict=True)
        assert len(reader.pages) == len(records)
        assert all(not page.get('/Annots') for page in reader.pages)
        checks = []
        with pdfium.PdfDocument(str(path)) as document:
            assert len(document) == len(records)
            for index, record in enumerate(records):
                first = reader.pages[index].extract_text()
                page = document[index]
                assert tuple(page.get_size()) == (792.0, 612.0)
                textpage = page.get_textpage()
                second = textpage.get_text_range()
                # PDF readers can insert spaces between letter-spaced capitals.
                assert re.sub(r'\s+', '', heading) in re.sub(r'\s+', '', first)
                assert re.sub(r'\s+', '', heading) in re.sub(r'\s+', '', second)
                completed = date.fromisoformat(record['completed_on'])
                values = [record['name'], record['workshop'], f'{completed.day} {MONTHS[completed.month]} {completed.year}', record['certificate_id']]
                for value in values:
                    assert re.sub(r'\s+', '', value) in re.sub(r'\s+', '', first), (folder.name, index, value)
                    assert re.sub(r'\s+', '', value) in re.sub(r'\s+', '', second), (folder.name, index, value)
                regions = [(45, 248, 747, 322), (45, 157, 747, 211), (45, 100, 251, 132), (288, 100, 534, 132)]
                for value, bounds in zip(values, regions):
                    field_text = textpage.get_text_bounded(*bounds)
                    assert re.sub(r'\s+', '', value) in re.sub(r'\s+', '', field_text), (folder.name, index, value, field_text)
                assert '\ufffd' not in first + second
                boxes = [textpage.get_charbox(j) for j in range(textpage.count_chars())]
                painted = [(l, b, r, t) for l, b, r, t in boxes if r > l and t > b]
                assert painted and all(l >= -.2 and b >= -.2 and r <= 792.2 and t <= 612.2 for l, b, r, t in painted)
                page.render(scale=110/72).to_pil().save(folder / f'pdfium-{index+1}.png')
                (folder / f'pypdf-{index+1}.txt').write_text(first, encoding='utf-8')
                (folder / f'pdfium-{index+1}.txt').write_text(second, encoding='utf-8')
                assert (folder / f'page-{index+1}.png').is_file()
                checks.append(dict(page=index+1, fields=values, textWithinPage=True, annotations=0))
                textpage.close()
                page.close()
        return dict(pdfSha256=sha256(path.read_bytes()).hexdigest(), pages=checks)

    baseline = inspect(run('default'), default_records)
    edited_data = [dict(name='Zoë <Workshop> & Co.', workshop='Building spaces & <stories>', completed_on='2028-02-29', certificate_id='CG_2028.001')]
    edited = inspect(run('edited', edited_data), edited_data)
    long_data = [dict(name='W' * 47 + 'M', workshop='M' * 79 + 'W', completed_on='2026-10-24', certificate_id='Z' * 20)]
    long_values = inspect(run('long-values', long_data), long_data)
    artwork = project / 'template.html'
    html = artwork.read_text(encoding='utf-8')
    assert html.count('CERTIFICATE OF PARTICIPATION') == 1
    artwork.write_text(html.replace('CERTIFICATE OF PARTICIPATION', 'COMMUNITY WORKSHOP RECORD'), encoding='utf-8')
    revised = out / 'revised-template.pdf'
    rebuilt = subprocess.run([sys.executable, '-I', '-X', 'utf8', str(project / 'build_template.py'), '--out', str(revised)],
                             cwd=out, capture_output=True, text=True, encoding='utf-8', timeout=120)
    (out / 'rebuild-template.stdout.txt').write_text(rebuilt.stdout, encoding='utf-8')
    (out / 'rebuild-template.stderr.txt').write_text(rebuilt.stderr, encoding='utf-8')
    assert rebuilt.returncode == 0, rebuilt.stderr
    assert revised.read_bytes() != template.read_bytes()
    custom_background = inspect(run('custom-background', [default_records[0]], custom_template=revised), [default_records[0]], heading='COMMUNITY WORKSHOP RECORD')
    for label, bad in [
        ('empty-data', []),
        ('extra-field', [{**default_records[0], 'extra': True}]),
        ('invalid-date', [{**default_records[0], 'completed_on': '2026-02-30'}]),
        ('long-name', [{**default_records[0], 'name': 'W' * 49}]),
        ('invalid-id', [{**default_records[0], 'certificate_id': 'CG 001'}]),
        ('control-character', [{**default_records[0], 'name': 'Name\nNew line'}]),
        ('missing-glyph', [{**default_records[0], 'name': '\U0001f984'}]),
    ]:
        run(label, bad, expected=2)
    multi = out / 'two-page-template.pdf'
    writer = PdfWriter()
    writer.append(str(template))
    writer.append(str(template))
    writer.write(multi)
    writer.close()
    run('reject-multiple-pages', custom_template=multi, expected=2)
    encrypted = out / 'encrypted-template.pdf'
    writer = PdfWriter()
    writer.append(str(template))
    writer.encrypt('synthetic-template-password')
    writer.write(encrypted)
    writer.close()
    run('reject-encrypted-template', custom_template=encrypted, expected=2)
    result = dict(ok=True, platform=platform.system(), version=version('fullbleed'), zipSha256=manifest['zip_sha256'], templateSha256=template_hash,
                  default=baseline, edited=edited, longValues=long_values, customBackground=custom_background, commands=commands,
                  scope='Downloaded one-page template project, edited and boundary data, independent text/page bounds and input rejection. No general geometry, accessibility, PDF standards or raster parity claim.')
    (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(ok=True, platform=platform.system(), version=version('fullbleed'), defaultPages=len(default_records), totalPages=6, rebuiltCustomBackground=True, rejected=9)))


if __name__ == '__main__':
    main()
