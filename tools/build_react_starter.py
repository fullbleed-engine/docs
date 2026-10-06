"""Build the exact downloadable React project and install its static demo."""
import argparse
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--node', default=shutil.which('node'))
parser.add_argument('--out', type=Path, default=ROOT / 'output/react-starter')
args = parser.parse_args()
if not args.node:
    raise SystemExit('Node.js 22.12 or newer is required.')
node = Path(args.node).resolve()
npm = next((path for path in [node.parent / 'node_modules/npm/bin/npm-cli.js',
    node.parent.parent / 'lib/node_modules/npm/bin/npm-cli.js'] if path.is_file()), None)
if npm is None:
    raise SystemExit('Use an official Node distribution containing npm.')

assets = ROOT / 'docs/assets/react-starter'
manifest = json.loads((assets / 'source.json').read_text(encoding='utf-8'))
for page, expected in [('docs/index.md', 'assets/react-starter/edit-online.html'),
                       ('docs/guides/react-pdf.md', '../assets/react-starter/edit-online.html')]:
    source = (ROOT / page).read_text(encoding='utf-8')
    links = re.findall(r'\]\(([^)]+)\)', source)
    assert links.count(expected) == 1 and not any('stackblitz.com/github/' in link for link in links), (
        f'{page}: online editor must use the launcher built from the downloadable React starter')
data = (assets / 'project.zip').read_bytes()
digest = lambda value: hashlib.sha256(value).hexdigest()
assert digest(data) == manifest['zip_sha256'] and len(data) == manifest['zip_bytes']
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix='project with spaces ', dir=out))
project_files = {}
with zipfile.ZipFile(assets / 'project.zip') as archive:
    names = archive.namelist()
    assert len(names) == len(set(names)) == len(manifest['files'])
    for entry in archive.infolist():
        path = PurePosixPath(entry.filename)
        assert not entry.is_dir() and not path.is_absolute() and '..' not in path.parts
        assert '\\' not in entry.filename and ':' not in entry.filename
        assert path.parts[0] == 'fullbleed-react-starter'
        assert digest(archive.read(entry)) == manifest['files'][entry.filename]
        project_files['/'.join(path.parts[1:])] = archive.read(entry).decode('utf-8')
    archive.extractall(workspace)
project = workspace / 'fullbleed-react-starter'
package = json.loads((project / 'package.json').read_text())
lock = json.loads((project / 'package-lock.json').read_text())
assert package['dependencies']['fullbleed'] == manifest['package_version'] == '0.3.1'
assert package['devDependencies']['vite'] == '8.3.2'
assert package['dependencies']['react'] == package['dependencies']['react-dom'] == manifest['react_version']
assert lock['packages']['node_modules/fullbleed']['integrity'] == manifest['package_integrity']
assert lock['packages']['node_modules/fullbleed']['resolved'].startswith('https://registry.npmjs.org/')
empty = out / 'empty.npmrc'; empty.write_text('', encoding='utf-8')
env = {**os.environ, 'PATH': str(node.parent) + os.pathsep + os.environ['PATH'],
    'NPM_CONFIG_USERCONFIG': str(empty), 'NPM_CONFIG_CACHE': str(workspace / 'cache'),
    'NPM_CONFIG_REGISTRY': 'https://registry.npmjs.org/'}
for name, arguments in [('install', ['ci', '--ignore-scripts', '--no-audit', '--no-fund']), ('build', ['run', 'build'])]:
    with (out / (name + '.log')).open('w', encoding='utf-8') as log:
        subprocess.run([str(node), str(npm), *arguments], cwd=project, env=env,
            stdout=log, stderr=subprocess.STDOUT, check=True)
installed = project / 'node_modules/fullbleed'
assert json.loads((installed / 'package.json').read_text())['version'] == manifest['package_version']
runtime = json.loads((project / 'dist/fullbleed/build.json').read_text())
assert runtime['packageVersion'] == manifest['package_version'] and runtime['engineVersion'] == '2.5.10'
for name, expected in runtime['files'].items():
    value = (project / 'dist/fullbleed' / name).read_bytes()
    assert len(value) == expected['bytes'] and digest(value) == expected['sha256']
site = ROOT / 'docs/assets/react-demo'
shutil.copytree(project / 'dist', site, dirs_exist_ok=True)
files = {p.relative_to(project / 'dist').as_posix(): digest(p.read_bytes()) for p in (project / 'dist').rglob('*') if p.is_file()}
assert all(digest((site / name).read_bytes()) == sha for name, sha in files.items())
fields = {'project[title]': 'Fullbleed React PDF starter',
    'project[description]': 'Editable HTML/CSS templates and local PDF previews. MIT licensed; fictional sample data.',
    'project[template]': 'node', 'project[dependencies]': '{}'}
fields.update({f'project[files][{name}]': value for name, value in sorted(project_files.items())})
inputs = '\n'.join(f'<input type="hidden" name="{escape(name, quote=True)}" value="{escape(value, quote=True)}">'
    for name, value in fields.items())
launcher = (ROOT / 'tools/react_online.html').read_text(encoding='utf-8')
for token, value in {'__PACKAGE_VERSION__': escape(manifest['package_version']),
    '__ENGINE_VERSION__': escape(manifest['engine_version']), '__PROJECT_FIELDS__': inputs}.items():
    assert token in launcher
    launcher = launcher.replace(token, value)
launcher_path = assets / 'edit-online.html'
launcher_path.write_text(launcher, encoding='utf-8', newline='\n')
record = dict(ok=True, checked_at=datetime.now(timezone.utc).isoformat(),
    zip_sha256=manifest['zip_sha256'], source_commit=manifest['source_commit'],
    package_version=manifest['package_version'], package_integrity=manifest['package_integrity'],
    online_editor_path='assets/react-starter/edit-online.html',
    online_editor_sha256=digest(launcher_path.read_bytes()), online_editor_files=len(project_files),
    node=subprocess.check_output([str(node), '--version'], text=True).strip(),
    fresh_cache=True, empty_user_config=True, files=files,
    scope='Exact downloadable project installed from its registry lockfile, production build, copied runtime hashes, and online launcher generated from the same source files.')
(out / 'verification.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(ok=True, files=len(files), package=manifest['package_version'], zip_sha256=manifest['zip_sha256'])))
