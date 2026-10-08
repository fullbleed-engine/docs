"""Build the standalone Axum download from checked sources and licensed fonts."""
from hashlib import sha256
from pathlib import Path
import json
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'examples/axum-pdf'
DESTINATION = ROOT / 'docs/assets/axum-starter'
PREFIX = 'fullbleed-axum-starter/'
SOURCES = {name: PROJECT / name for name in [
    'Cargo.toml', 'Cargo.lock', 'README.md', 'LICENSE', '.gitignore',
    'src/main.rs', 'src/lib.rs', 'sample.json', 'ui/index.html',
    'templates/invoice.html', 'templates/invoice.css',
]}
for name in ['Inter-Variable.ttf', 'Inter-OFL.txt', 'DMSerifDisplay-Regular.ttf',
             'DMSerifDisplay-OFL.txt', 'BebasNeue-Regular.ttf', 'BebasNeue-OFL.txt']:
    SOURCES['fonts/' + name] = ROOT / 'docs/assets/playground/fonts' / name


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    archive_path = DESTINATION / 'project.zip'
    records = []
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, source in sorted(SOURCES.items()):
            data = source.read_bytes() if source.suffix == '.ttf' else source.read_text(encoding='utf-8').encode('utf-8')
            info = zipfile.ZipInfo(PREFIX + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
            records.append(dict(path=name, source=source.relative_to(ROOT).as_posix(),
                                bytes=len(data), sha256=sha256(data).hexdigest()))
    cargo = tomllib.loads((PROJECT / 'Cargo.toml').read_text(encoding='utf-8'))
    manifest = dict(schema='fullbleed.axum-starter.v1', prefix=PREFIX,
        repository='https://github.com/fullbleed-engine/docs',
        engine=cargo['dependencies']['fullbleed'].removeprefix('='),
        rust=cargo['package']['rust-version'], files=records,
        zip_bytes=archive_path.stat().st_size, zip_sha256=sha256(archive_path.read_bytes()).hexdigest())
    (DESTINATION / 'source.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(files=len(records), bytes=manifest['zip_bytes'], sha256=manifest['zip_sha256'])))


if __name__ == '__main__':
    main()
