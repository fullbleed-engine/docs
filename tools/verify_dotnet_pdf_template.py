"""Verify the exact C# PDF-template ZIP against public NuGet and independent PDF readers."""
import argparse
from datetime import date, datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pypdf import PdfReader, PdfWriter
import pypdfium2 as pdfium

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, default=root / 'output/dotnet-pdf-template-verification')
parser.add_argument('--dotnet', default=shutil.which('dotnet') or 'dotnet')
args = parser.parse_args()
dotnet = Path(args.dotnet)
source = root / 'examples/dotnet-pdf-template'
assets = root / 'docs/assets/dotnet-pdf-template'
manifest = json.loads((assets / 'source.json').read_text(encoding='utf-8'))
assert manifest['packageVersion'] == '0.2.3' and manifest['engineVersion'] == '2.5.39'
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=False)
project = out / 'project with spaces/fullbleed-csharp-pdf-template'
digest = lambda path: sha256(path.read_bytes()).hexdigest()
archive_path = assets / 'project.zip'
assert digest(archive_path) == manifest['zipSha256']
preparation = dict(sourceSha256={row['path']: row['sha256'] for row in manifest['files']})
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    expected = {'fullbleed-csharp-pdf-template/' + row['path'] for row in manifest['files']}
    assert set(archive.namelist()) == expected and len(archive.namelist()) == len(expected)
    for row in manifest['files']:
        data = archive.read('fullbleed-csharp-pdf-template/' + row['path'])
        assert len(data) == row['bytes'] and sha256(data).hexdigest() == row['sha256']
        assert data == (source / row['path']).read_bytes()
        target = (project / row['path']).resolve()
        assert target.is_relative_to(project.resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
env = {key: value for key, value in os.environ.items() if key not in [
    'FULLBLEED_NATIVE_LIBRARY', 'PYTHONPATH', 'PYTHONHOME', 'DOTNET_ROOT', 'DOTNET_ROLL_FORWARD',
    'NUGET_PACKAGES', 'NUGET_HTTP_CACHE_PATH', 'NUGET_FALLBACK_PACKAGES']}
env.update(DOTNET_CLI_TELEMETRY_OPTOUT='1', DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true',
    NUGET_PACKAGES=str(out / 'package-cache'), NUGET_HTTP_CACHE_PATH=str(out / 'http-cache'),
    DOTNET_CLI_HOME=str(out / 'cli-home'), DOTNET_SKIP_FIRST_TIME_EXPERIENCE='1')
(project / 'NuGet.Config').write_text(
    '<?xml version="1.0" encoding="utf-8"?><configuration><packageSources><clear />'
    '<add key="nuget.org" value="https://api.nuget.org/v3/index.json" /></packageSources>'
    '<fallbackPackageFolders><clear /></fallbackPackageFolders></configuration>\n', encoding='utf-8')
commands = []
record = dict(status='starting', startedAt=datetime.now(timezone.utc).isoformat(), commands=commands,
    platform=platform.system(), zipSha256=manifest['zipSha256'])

def save():
    record['updatedAt'] = datetime.now(timezone.utc).isoformat()
    (out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')

def invoke(label, arguments, expected=0):
    record['status'] = label
    save()
    completed = subprocess.run(list(map(str, arguments)), cwd=project, env=env, capture_output=True,
        text=True, encoding='utf-8', timeout=120)
    (out / (label + '.stdout.txt')).write_text(completed.stdout, encoding='utf-8')
    (out / (label + '.stderr.txt')).write_text(completed.stderr, encoding='utf-8')
    commands.append(dict(label=label, exitCode=completed.returncode, expected=expected))
    save()
    if completed.returncode != expected:
        print((completed.stdout + completed.stderr)[-4000:], flush=True)
        raise RuntimeError(label)
    print(label + ': passed', flush=True)

template = project / 'Assets/template.pdf'
template_hash = digest(template)
records = json.loads((project / 'Assets/data.json').read_text(encoding='utf-8'))
app = project / 'bin/Release/net10.0/TemplateCertificates.dll'

def render(label, data=None, supplied_template=None, expected=0, raw=None):
    destination = out / label
    args = [dotnet, app, '--out', destination]
    if data is not None or raw is not None:
        path = out / (label + '-data.json')
        path.write_text(raw if raw is not None else json.dumps(data, ensure_ascii=False), encoding='utf-8')
        args += ['--data', path]
    if supplied_template:
        args += ['--template', supplied_template]
    invoke(label, args, expected)
    assert digest(template) == template_hash
    if expected:
        assert not (destination / 'certificates.pdf').exists()
        return None
    report = json.loads((destination / 'render.json').read_text(encoding='utf-8'))
    assert report['packageVersion'] == '0.2.3' and report['templateUnchanged'] and report['deterministicRepeat']
    assert report['missingGlyphs'] == 0 and report['annotationMode'] == 'none'
    assert report['pdfSha256'] == digest(destination / 'certificates.pdf')
    assert (destination / 'certificates.pdf').read_bytes() == (destination / 'certificates-repeat.pdf').read_bytes()
    for preview in report['previews']:
        assert digest(destination / preview['file']) == preview['sha256']
    return destination

def inspect(folder, expected_records, heading='CERTIFICATE OF PARTICIPATION'):
    path = folder / 'certificates.pdf'
    reader = PdfReader(path, strict=True)
    assert len(reader.pages) == len(expected_records)
    compact = lambda text: ''.join(text.split())
    checks = []
    with pdfium.PdfDocument(path) as document:
        assert len(document) == len(expected_records)
        for index, item in enumerate(expected_records):
            page = document[index]
            assert tuple(page.get_size()) == (792.0, 612.0) and not reader.pages[index].get('/Annots')
            text = page.get_textpage()
            try:
                first, second = reader.pages[index].extract_text(), text.get_text_range()
                assert compact(first) == compact(second) and compact(heading) in compact(first)
                completed = date.fromisoformat(item['completed_on'])
                month = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'][completed.month]
                fields = [unicodedata.normalize('NFC', item['name'].strip()), unicodedata.normalize('NFC', item['workshop'].strip()),
                    f'{completed.day} {month} {completed.year}', item['certificate_id'].strip()]
                for value, bounds in zip(fields, [(47, 232, 745, 320), (47, 140, 745, 207), (47, 95, 250, 130), (290, 95, 535, 130)], strict=True):
                    assert compact(value) in compact(text.get_text_bounded(*bounds)), (folder.name, index, value)
                assert '\ufffd' not in first + second
                boxes = [text.get_charbox(offset) for offset in range(text.count_chars())]
                painted = [box for box in boxes if box[2] > box[0] and box[3] > box[1]]
                assert painted and all(left >= -.2 and bottom >= -.2 and right <= 792.2 and top <= 612.2 for left, bottom, right, top in painted)
                bitmap = page.render(scale=110 / 72)
                try:
                    image = bitmap.to_pil().convert('RGB')
                    image.save(folder / f'pdfium-{index + 1}.png')
                    pixels = sha256(image.tobytes()).hexdigest()
                finally:
                    bitmap.close()
                (folder / f'text-{index + 1}.txt').write_text(first, encoding='utf-8')
                checks.append(dict(page=index + 1, fields=fields, textWithinPage=True, annotations=0, pdfiumPixelsSha256=pixels))
            finally:
                text.close()
                page.close()
    return dict(pdfSha256=digest(path), pages=checks)

try:
    invoke('restore', [dotnet, 'restore', 'TemplateCertificates.csproj', '--locked-mode', '--configfile', 'NuGet.Config'])
    restored = out / 'package-cache/fullbleed.dotnet/0.2.3/fullbleed.dotnet.0.2.3.nupkg'
    assert digest(restored) == manifest['packageSha256']
    with zipfile.ZipFile(restored) as package:
        assert '.signature.p7s' in package.namelist()
        metadata = ET.fromstring(package.read('FullBleed.DotNet.nuspec'))
        ns = {'n': metadata.tag.split('}')[0].strip('{')}
        assert metadata.find('n:metadata/n:repository', ns).get('commit') == manifest['packageCommit']
        provenance = json.loads(package.read('native-provenance.json'))
        core, = [item for item in provenance['dependencies'] if item['name'] == 'fullbleed']
        assert core['version'] == manifest['engineVersion']
    record['packageSha256'] = digest(restored)
    invoke('build', [dotnet, 'build', 'TemplateCertificates.csproj', '-c', 'Release', '--no-restore'])
    default_folder = render('default')
    baseline = inspect(default_folder, records)
    for name, expected in manifest['outputs'].items():
        assert digest(default_folder / name) == expected
        assert (default_folder / name).read_bytes() == (assets / name).read_bytes()
    # This concrete certificate shares the existing Python example's artwork and raster output.
    # PDF bytes differ because the authoring paths emit different metadata.
    for index in range(1, 4):
        assert (default_folder / f'page-{index}.png').read_bytes() == (root / f'docs/assets/pdf-template/page-{index}.png').read_bytes()
    record['defaultPreviewsMatchPythonExample'] = True
    edited_data = [dict(name='Zoe\u0308 <Workshop> & Co.', workshop='Building spaces & <stories>', completed_on='2028-02-29', certificate_id='CG_2028.001')]
    edited_folder = render('edited', edited_data)
    edited = inspect(edited_folder, edited_data)
    html = (edited_folder / 'overlay.html').read_text(encoding='utf-8')
    assert 'Zo\u00eb &lt;Workshop&gt; &amp; Co.' in html and '\u0308' not in html and '<Workshop>' not in html
    long_data = [dict(name='W' * 47 + 'M', workshop='M' * 79 + 'W', completed_on='2026-10-24', certificate_id='Z' * 20)]
    long_values = inspect(render('long-values', long_data), long_data)
    artwork = project / 'Assets/template.html'
    content = artwork.read_text(encoding='utf-8')
    assert content.count('CERTIFICATE OF PARTICIPATION') == 1
    artwork.write_text(content.replace('CERTIFICATE OF PARTICIPATION', 'COMMUNITY WORKSHOP RECORD'), encoding='utf-8')
    revised = out / 'revised-template.pdf'
    invoke('rebuild-template', [dotnet, 'run', '--project', 'TemplateCertificates.csproj', '-c', 'Release', '--no-restore', '--', 'build-template', '--out', revised])
    assert revised.is_file() and revised.read_bytes() != template.read_bytes()
    custom = inspect(render('custom-background', [records[0]], revised), [records[0]], heading='COMMUNITY WORKSHOP RECORD')
    rejected = [
        ('empty-data', []), ('extra-field', [{**records[0], 'extra': True}]),
        ('invalid-date', [{**records[0], 'completed_on': '2026-02-30'}]),
        ('long-name', [{**records[0], 'name': 'W' * 49}]),
        ('invalid-id', [{**records[0], 'certificate_id': 'CG 001'}]),
        ('control-character', [{**records[0], 'name': 'Name\nNew line'}]),
        ('missing-glyph', [{**records[0], 'name': '\U0001f984'}]),
        ('numeric-name', [{**records[0], 'name': 14}]),
        ('missing-field', [{key: value for key, value in records[0].items() if key != 'workshop'}]),
    ]
    for label, data in rejected:
        render(label, data, expected=2)
    duplicate = json.dumps([records[0]])
    duplicate = duplicate.replace('"name":', '"name":"Duplicate", "name":', 1)
    render('duplicate-field', raw=duplicate, expected=2)
    multi = out / 'two-page-template.pdf'
    writer = PdfWriter()
    writer.append(str(template)); writer.append(str(template)); writer.write(multi); writer.close()
    render('reject-multiple-pages', supplied_template=multi, expected=2)
    encrypted = out / 'encrypted-template.pdf'
    writer = PdfWriter()
    writer.append(str(template)); writer.encrypt('synthetic-template-password'); writer.write(encrypted); writer.close()
    render('reject-encrypted-template', supplied_template=encrypted, expected=2)
    invoke('preserve-existing-output', [dotnet, app, '--out', default_folder], expected=2)
    assert digest(default_folder / 'certificates.pdf') == baseline['pdfSha256']
    invoke('preserve-template-path', [dotnet, app, 'build-template', '--out', template], expected=2)
    assert digest(template) == template_hash
    for name, expected in preparation['sourceSha256'].items():
        assert digest(source / name) == expected, name
    record.update(status='passed', package='0.2.3', engine='2.5.39', default=baseline, edited=edited,
        longValues=long_values, customBackground=custom, renderedPages=6, invalidInputsRejected=12,
        existingPathsPreserved=2, unchangedAuthoringSource=True,
        scope='Exact downloadable source restored only from public NuGet into empty caches, using a path with spaces. Four rendered cases, Unicode normalization/escaping, independent field geometry, rejected inputs and preserved paths. The default native previews match the Python example; this is not universal raster parity or a conformance claim.')
except BaseException as error:
    record.update(status='failed', error=str(error))
    raise
finally:
    save()
print(json.dumps(dict(status=record['status'], renderedPages=record['renderedPages'], invalidInputsRejected=record['invalidInputsRejected'], existingPathsPreserved=record['existingPathsPreserved'])), flush=True)
