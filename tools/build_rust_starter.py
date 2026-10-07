"""Bundle a standalone Rust project using the existing checked sources."""
from hashlib import sha256
from pathlib import Path
import json
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'docs/assets/rust-starter'
PREFIX = 'fullbleed-rust-starter/'
SOURCES = {
    'Cargo.toml': 'examples/rust/Cargo.toml',
    'Cargo.lock': 'examples/rust/Cargo.lock',
    'src/hello.rs': 'examples/rust/src/hello.rs',
    'src/from_files.rs': 'examples/rust/src/from_files.rs',
    'LICENSE': 'examples/rust/LICENSE',
    'README.md': 'examples/rust/STARTER.md',
}
for name in ['invoice.html', 'invoice.css', 'report.html', 'report.css']:
    SOURCES['templates/' + name] = 'docs/assets/showcase/' + name
for name in ['Inter-Variable.ttf', 'Inter-OFL.txt', 'DMSerifDisplay-Regular.ttf',
             'DMSerifDisplay-Italic.ttf', 'DMSerifDisplay-OFL.txt',
             'BebasNeue-Regular.ttf', 'BebasNeue-OFL.txt']:
    SOURCES['fonts/' + name] = 'docs/assets/playground/fonts/' + name
GENERATED = {'.gitignore': b'/target/\n/output/\n/invoice.pdf\n'}


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    files = []
    archive_path = DESTINATION / 'project.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(SOURCES.keys() | GENERATED.keys()):
            if name in SOURCES:
                source = ROOT / SOURCES[name]
                data = source.read_bytes() if name.endswith('.ttf') else source.read_text(encoding='utf-8').encode('utf-8')
            else:
                data = GENERATED[name]
            entry = zipfile.ZipInfo(PREFIX + name, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
            files.append({'path': name, 'source': SOURCES.get(name), 'bytes': len(data),
                          'sha256': sha256(data).hexdigest()})
    cargo = tomllib.loads((ROOT / SOURCES['Cargo.toml']).read_text(encoding='utf-8'))
    manifest = {'schema': 'fullbleed.rust-starter.v1',
                'repository': 'https://github.com/fullbleed-engine/docs',
                'engine': cargo['dependencies']['fullbleed'].removeprefix('='),
                'prefix': PREFIX, 'files': files,
                'zip_bytes': archive_path.stat().st_size,
                'zip_sha256': sha256(archive_path.read_bytes()).hexdigest()}
    (DESTINATION / 'source.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'files': len(files), 'bytes': manifest['zip_bytes'], 'sha256': manifest['zip_sha256']}))


if __name__ == '__main__':
    main()
