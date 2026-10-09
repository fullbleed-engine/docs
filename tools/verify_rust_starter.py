"""Compile and exercise the actual downloadable Rust ZIP outside the source tree."""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path, PurePosixPath
import argparse
import json
import os
import platform
import shutil
import subprocess
import tempfile
import zipfile

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/rust-starter'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT / 'output/rust-starter-verification')
    parser.add_argument('--archive', type=Path, default=ASSETS / 'project.zip')
    parser.add_argument('--manifest', type=Path, default=ASSETS / 'source.json')
    parser.add_argument('--target-dir', type=Path, default=ROOT / 'examples/rust/target')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks, commands, fixtures = [], [], []
    report = {'ok': False, 'platform': platform.system(),
              'verificationVersions': {'python': platform.python_version(), 'pypdf': version('pypdf'), 'pillow': version('pillow')}, 'checks': checks,
              'commands': commands, 'fixtures': fixtures}
    env = {**os.environ, 'CARGO_TARGET_DIR': str(args.target_dir.resolve())}

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        checks.append(label)

    def run(label, command, cwd, expected=0):
        result = subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                                capture_output=True, text=True, encoding='utf-8', timeout=900)
        (out / (label + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
        (out / (label + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
        commands.append({'label': label, 'exit': result.returncode})
        check(label + ' exit status', result.returncode == expected)
        return result

    def inspect(name, pages, markers=()):
        folder = out / name
        reader = PdfReader(folder / 'document.pdf')
        check(name + ' page count', len(reader.pages) == pages)
        text = '\n'.join(page.extract_text() for page in reader.pages)
        (out / (name + '-text.txt')).write_text(text, encoding='utf-8')
        compact = ''.join(text.split())
        check(name + ' expected text', all(''.join(marker.split()) in compact for marker in markers))
        check(name + ' every page has text', all(len(page.extract_text().strip()) > 10 for page in reader.pages))
        check(name + ' one finalized preview per page', len(list(folder.glob('page-*.png'))) == pages)
        for index in range(1, pages + 1):
            with Image.open(folder / f'page-{index}.png') as image:
                check(f'{name} preview {index} has visible content',
                      min(image.size) > 300 and image.convert('RGB').getextrema() != ((255, 255),) * 3)
        files = {path.name: digest(path) for path in sorted(folder.iterdir()) if path.suffix in {'.pdf', '.png'}}
        fixtures.append({'name': name, 'pages': pages, 'files': files})
        return reader, files

    try:
        manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
        check('archive checksum and size', digest(args.archive) == manifest['zip_sha256']
              and args.archive.stat().st_size == manifest['zip_bytes'])
        prefix = manifest['prefix']
        check('expected archive root', prefix == 'fullbleed-rust-starter/')
        with tempfile.TemporaryDirectory(prefix='fullbleed rust download ') as temporary:
            workspace = Path(temporary).resolve()
            check('project is outside the repository', not workspace.is_relative_to(ROOT))
            with zipfile.ZipFile(args.archive) as archive:
                names = [prefix + item['path'] for item in manifest['files']]
                check('archive contains exactly the manifest files', sorted(archive.namelist()) == sorted(names))
                check('archive paths are confined', all(not PurePosixPath(name).is_absolute()
                      and '..' not in PurePosixPath(name).parts and '\\' not in name for name in names))
                for item in manifest['files']:
                    data = archive.read(prefix + item['path'])
                    check('file digest: ' + item['path'], len(data) == item['bytes']
                          and sha256(data).hexdigest() == item['sha256'])
                archive.extractall(workspace)
            project = workspace / prefix
            readme = (project / 'README.md').read_text(encoding='utf-8')
            guide = (ROOT / 'docs/getting-started/rust.md').read_text(encoding='utf-8')
            for name in ['invoice', 'report']:
                command = f'cargo run --release --locked --bin from-files -- templates/{name}.html templates/{name}.css fonts output/{name}'
                check(name + ' command appears in README and guide', command in readme and command in guide)
            check('font license notices included', all((project / 'fonts' / name).is_file()
                  for name in ['Inter-OFL.txt', 'DMSerifDisplay-OFL.txt', 'BebasNeue-OFL.txt']))
            lock_hash = digest(project / 'Cargo.lock')
            run('format', ['cargo', 'fmt', '--check'], project)
            run('build', ['cargo', 'build', '--release', '--locked'], project)
            metadata = json.loads(run('metadata', ['cargo', 'metadata', '--format-version', '1', '--locked'], project).stdout)
            core = next(package for package in metadata['packages'] if package['name'] == 'fullbleed')
            check('published pinned crate, no local engine path', core['version'] == manifest['engine']
                  and core['source'].startswith('registry+'))
            features = sorted(next(node for node in metadata['resolve']['nodes'] if node['id'] == core['id'])['features'])
            check('download includes the SVG support used in playground projects',
                  features == manifest['engine_features'] == ['svg_raster'])
            check('Cargo lockfile unchanged', digest(project / 'Cargo.lock') == lock_hash)
            report['engine'] = core['version']
            report['engine_features'] = features
            report['rustc'] = run('rustc', ['rustc', '--version'], project).stdout.strip()
            report['source_zip_sha256'] = manifest['zip_sha256']
            target = Path(metadata['target_directory']) / 'release'
            suffix = '.exe' if os.name == 'nt' else ''
            render = target / ('from-files' + suffix)
            for name, pages, markers in [
                ('invoice', 1, ['Northstar', 'Maple & Finch', 'NS-1042', '$1,870.00']),
                ('report', 3, ['Common Ground', 'Small actions.', 'Clear allocations.', '$420,000.00']),
            ]:
                result = run(name, ['cargo', 'run', '--release', '--locked', '--bin', 'from-files', '--',
                                    'templates/' + name + '.html', 'templates/' + name + '.css',
                                    'fonts', 'output/' + name], project)
                shutil.copytree(project / 'output' / name, out / name)
                check(name + ' renderer confirms page count', f'Rendered {pages} page(s)' in result.stdout)
                inspect(name, pages, markers)
            run('repeat', [render, 'templates/invoice.html', 'templates/invoice.css', 'fonts', out / 'repeat'], project)
            _, repeated = inspect('repeat', 1)
            check('repeat PDF and finalized PNG bytes match', repeated == fixtures[0]['files'])

            (project / 'edited.html').write_text('<h1>Rust starter edit</h1><p>Custom HTML &amp; CSS, checked.</p>', encoding='utf-8')
            (project / 'edited.css').write_text('@page {size:A5;margin:20pt} body {font-family:Inter;color:#175c52}', encoding='utf-8')
            run('edited', [render, 'edited.html', 'edited.css', 'fonts', out / 'edited'], project)
            edited, _ = inspect('edited', 1, ['Rust starter edit', 'Custom HTML & CSS, checked.'])
            check('edited CSS changes the paper to A5',
                  abs(float(edited.pages[0].mediabox.width) - 419.528) < .01
                  and abs(float(edited.pages[0].mediabox.height) - 595.276) < .01)

            run('usage', [render], project, expected=1)
            run('missing-fonts', [render, 'edited.html', 'edited.css', 'absent-fonts', out / 'missing-fonts'], project, expected=1)
            (project / 'missing.html').write_text('<p>' + chr(0x10ffff) + '</p>', encoding='utf-8')
            missing = run('missing-glyph', [render, 'missing.html', 'edited.css', 'fonts', out / 'missing-glyph'], project, expected=1)
            check('uncovered characters produce the expected error', 'do not cover all document characters' in missing.stderr)
            check('failed inputs leave no PDF', not (out / 'missing-fonts/document.pdf').exists()
                  and not (out / 'missing-glyph/document.pdf').exists())
            run('recovery', [render, 'edited.html', 'edited.css', 'fonts', out / 'recovery'], project)
            _, recovered = inspect('recovery', 1)
            check('render after failures matches edited PDF and PNG', recovered == fixtures[3]['files'])
            run('hello', [target / ('hello' + suffix)], out)
            hello = PdfReader(out / 'invoice.pdf')
            check('minimal API example produces its documented PDF', len(hello.pages) == 1
                  and 'INV-1042' in hello.pages[0].extract_text())
        report['ok'] = True
    finally:
        (out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': report['ok'], 'checks': len(checks), 'engine': report['engine'],
                      'platform': report['platform'], 'evidence': str(out)}))


if __name__ == '__main__':
    main()
