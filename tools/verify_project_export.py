"""Extract real playground ZIPs and compare their Python output to WASI references."""
from importlib import metadata
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import zipfile

import fullbleed

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'playground/project-verification'
assets = ROOT / 'docs/assets/playground'
font_sources = json.loads((assets / 'font-sources.json').read_text(encoding='utf-8'))
required = {'input.html', 'style.css', 'render.py', 'README.txt', 'LICENSE.txt',
            'requirements.txt', 'project.json', 'fonts/font-sources.json'}
required.update('fonts/' + item['file'] for item in font_sources['files'])
records = []
for case in json.loads((OUT / 'export-verification.json').read_text())['cases']:
    name = case['name']
    project = OUT / 'extracted projects with spaces' / name
    expected = OUT / (name + '-expected')
    archive_path = OUT / (name + '.zip')
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None, 'Invalid ZIP CRC'
        assert set(archive.namelist()) == required
        assert len(archive.namelist()) == len(required), 'Duplicate ZIP names'
        for path in archive.namelist():
            assert not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts
        archive.extractall(project)
    for source in ['input.html', 'style.css']:
        assert (project / source).read_bytes() == (expected / source).read_bytes(), 'Source bytes changed'
    assert (project / 'requirements.txt').read_text() == f'fullbleed=={metadata.version("fullbleed")}\n'
    assert b'{{ENGINE_VERSION}}' not in (project / 'README.txt').read_bytes()
    manifest = json.loads((project / 'project.json').read_text(encoding='utf-8'))
    assert {f['path'] for f in manifest['files']} == required - {'project.json'}
    for item in manifest['files']:
        raw = (project / item['path']).read_bytes()
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
    for item in font_sources['files']:
        assert hashlib.sha256((project / 'fonts' / item['file']).read_bytes()).hexdigest() == item['sha256']
    # Use a different working directory to check that the runner resolves its own assets.
    run = subprocess.run([sys.executable, '-I', str(project / 'render.py')], cwd=ROOT,
                         capture_output=True, text=True, encoding='utf-8', check=True)
    (project / 'run.log').write_text(run.stdout + run.stderr, encoding='utf-8')
    rendered = json.loads((project / 'output/render.json').read_text())
    assert rendered['pages'] == case['pages']
    pdf = project / 'output/document.pdf'
    assert pdf.read_bytes() == (expected / 'output.pdf').read_bytes(), name + ': Python/WASI PDF mismatch'
    if name == 'notice':
        assert b'DOCUMENT DESIGN EXAMPLE' in (project / 'input.html').read_bytes()
        assert b'TAGGED DOCUMENT EXAMPLE' not in (project / 'input.html').read_bytes()
        assert not fullbleed.inspect_pdf(str(pdf))['profile']['struct_tree_root_present']
    for number, preview in enumerate(rendered['previews'], 1):
        assert Path(preview).read_bytes() == (expected / f'page-{number}.png').read_bytes(), name + ': PNG mismatch'
    records.append(dict(name=name, pages=case['pages'], files=len(required),
                        zip_crc_valid=True, sources_preserved=True, manifest_hashes_valid=True,
                        fonts_and_licenses_match=True, python_wasi_pdf_equal=True, python_wasi_png_equal=True,
                        pdf_sha256=rendered['sha256']))
result = dict(ok=True, platform=sys.platform, python=sys.version.split()[0],
              engine=metadata.version('fullbleed'), cases=records,
              source_revision=os.environ.get('GITHUB_SHA'), ci_run_id=os.environ.get('GITHUB_RUN_ID'),
              archive_checks=json.loads((OUT / 'export-verification.json').read_text())['checks'],
              preview_source='finalized_pdf',
              scope='These seven fixtures and bundled assets; no universal parity or standards-conformance claim.')
(OUT / 'python-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
(assets / 'project-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
