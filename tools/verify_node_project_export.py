"""Install actual Node project ZIPs and compare their PDF/PNG output with WASI."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import zipfile

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'playground/project-verification'
assets = ROOT / 'docs/assets/playground'
font_sources = json.loads((assets / 'font-sources.json').read_text(encoding='utf-8'))
required = {'input.html', 'style.css', 'render.mjs', 'README.txt', 'LICENSE.txt',
            'package.json', 'package-lock.json', 'project.json', 'fonts/font-sources.json'}
required.update('fonts/' + item['file'] for item in font_sources['files'])
node = shutil.which('node')
assert node, 'Node.js 22 or newer is required'
node_version = subprocess.check_output([node, '--version'], text=True).strip()
assert int(node_version[1:].split('.')[0]) >= 22
npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
assert npm
# Calling npm's JS entry keeps Windows shell quoting out of project paths.
npm_cli = Path(npm).resolve().parent / 'node_modules/npm/bin/npm-cli.js'
if not npm_cli.is_file():
    npm_cli = Path(npm).resolve().parent / 'npm-cli.js'
assert npm_cli.is_file(), f'Cannot locate npm CLI beside {npm}'
cache = OUT / 'node-npm-cache'
env = {**os.environ, 'npm_config_cache': str(cache), 'npm_config_update_notifier': 'false'}
records = []
package_version = None
engine_version = json.loads((assets / 'build.json').read_text())['engine']['version']
for case in json.loads((OUT / 'export-verification.json').read_text())['cases']:
    name = case['name']
    local_assets = case.get('local_assets', [])
    case_required = required | {item['path'] for item in local_assets}
    project = OUT / 'extracted node projects with spaces' / name
    expected = OUT / (name + '-expected')
    archive_path = OUT / (name + '-node.zip')
    assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == case['node_zip_sha256']
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == case_required and len(archive.namelist()) == len(case_required)
        for path in archive.namelist():
            assert not PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts
            assert '\\' not in path and ':' not in path
        archive.extractall(project)
    for source in ['input.html', 'style.css']:
        assert (project / source).read_bytes() == (expected / source).read_bytes()
    manifest = json.loads((project / 'project.json').read_text(encoding='utf-8'))
    assert manifest['engine']['version'] == engine_version
    assert manifest['runtime']['name'] == 'node'
    assert {f['path'] for f in manifest['files']} == case_required - {'project.json'}
    assert {f['path'] for f in manifest.get('localAssets', [])} == {f['path'] for f in local_assets}
    for item in local_assets:
        data = (project / item['path']).read_bytes()
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    for item in manifest['files']:
        data = (project / item['path']).read_bytes()
        assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    for item in font_sources['files']:
        assert hashlib.sha256((project / 'fonts' / item['file']).read_bytes()).hexdigest() == item['sha256']
    assert b'{{' not in (project / 'README.txt').read_bytes()
    pkg = json.loads((project / 'package.json').read_text())
    lock_bytes = (project / 'package-lock.json').read_bytes()
    lock = json.loads(lock_bytes)
    package_version = package_version or pkg['dependencies']['fullbleed']
    assert pkg['dependencies'] == {'fullbleed': package_version}
    assert manifest['runtime']['package']['version'] == package_version
    assert pkg['fullbleed']['engineVersion'] == engine_version
    assert lock['packages']['node_modules/fullbleed']['version'] == package_version
    assert lock['packages']['node_modules/fullbleed']['resolved'].startswith('https://registry.npmjs.org/fullbleed/')
    command = [node, str(npm_cli), 'ci', '--ignore-scripts', '--no-audit', '--no-fund']
    if records:
        command.append('--offline')
    installed = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, encoding='utf-8', timeout=120)
    (project / 'install.log').write_text(installed.stdout + installed.stderr, encoding='utf-8')
    assert installed.returncode == 0, installed.stderr
    assert (project / 'package-lock.json').read_bytes() == lock_bytes
    # Use the documented command once, then check paths from a different cwd.
    command = [node, str(npm_cli), 'run', 'render'] if not records else [node, str(project / 'render.mjs')]
    run = subprocess.run(command, cwd=project if not records else ROOT, env=env,
                         capture_output=True, text=True, encoding='utf-8', timeout=90)
    (project / 'run.log').write_text(run.stdout + run.stderr, encoding='utf-8')
    assert run.returncode == 0, run.stderr
    rendered = json.loads((project / 'output/render.json').read_text())
    assert rendered['pages'] == case['pages'] and rendered['missingGlyphs'] == 0
    assert rendered['package'] == package_version and rendered['engine'] == engine_version
    pdf = project / 'output/document.pdf'
    assert pdf.read_bytes() == (expected / 'output.pdf').read_bytes(), name + ': Node/WASI PDF mismatch'
    assert len(PdfReader(pdf).pages) == case['pages']
    for number, preview in enumerate(rendered['previews'], 1):
        assert Path(preview).read_bytes() == (expected / f'page-{number}.png').read_bytes(), name + ': PNG mismatch'
    assert len(rendered['previews']) == case['pages']
    repeat_equal = None
    if name.startswith('preformatted-'):
        first = [pdf.read_bytes(), *[Path(path).read_bytes() for path in rendered['previews']]]
        repeated = subprocess.run([node, str(project / 'render.mjs')], cwd=ROOT, env=env,
                                  capture_output=True, text=True, encoding='utf-8', timeout=90)
        (project / 'repeat.log').write_text(repeated.stdout + repeated.stderr, encoding='utf-8')
        assert repeated.returncode == 0, repeated.stderr
        assert json.loads((project / 'output/render.json').read_text()) == rendered
        assert first == [pdf.read_bytes(), *[Path(path).read_bytes() for path in rendered['previews']]]
        repeat_equal = True
    records.append(dict(name=name, pages=case['pages'], files=len(case_required), zip_crc_valid=True,
                        sources_preserved=True, manifest_hashes_valid=True, fonts_and_licenses_match=True,
                        lock_unchanged=True, offline_install=bool(records), node_wasi_pdf_equal=True,
                        node_wasi_png_equal=True, pdf_sha256=rendered['sha256'],
                        local_assets=local_assets, repeat_equal=repeat_equal))
result = dict(ok=True, checkedAt=datetime.now(timezone.utc).isoformat(), platform=sys.platform,
              node=node_version, package=package_version, engine=engine_version, cases=records,
              source_revision=os.environ.get('GITHUB_SHA'), ci_run_id=os.environ.get('GITHUB_RUN_ID'),
              preview_source='finalized_pdf', scope=f'These {len(records)} downloaded projects and bundled assets; no universal parity or standards-conformance claim.')
(OUT / 'node-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
(assets / 'node-project-verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result))
