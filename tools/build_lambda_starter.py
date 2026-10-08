"""Build a reproducible Lambda starter ZIP from an explicit source inventory."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/lambda-pdf'
DEST = ROOT / 'docs/assets/lambda-starter'
PREFIX = 'fullbleed-lambda-starter/'
FILES = ['.dockerignore', '.gitignore', 'Dockerfile', 'LICENSE', 'README.md',
         'base-images.json', 'client.py', 'handler.py', 'requirements.txt',
         'sample.json', 'template.yaml', 'test_handler.py',
         'templates/invoice.html', 'templates/invoice.css',
         'fonts/DMSerifDisplay-Regular.ttf', 'fonts/DMSerifDisplay-OFL.txt',
         'fonts/BebasNeue-Regular.ttf', 'fonts/BebasNeue-OFL.txt']


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    records = []
    path = DEST / 'project.zip'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(FILES):
            data = (SOURCE / name).read_bytes()
            entry = zipfile.ZipInfo(PREFIX + name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 0
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
            records.append(dict(path=name, bytes=len(data), sha256=sha256(data).hexdigest()))
    manifest = dict(schema='fullbleed.lambda-starter.v1', prefix=PREFIX, engine='2.5.20',
                    files=records, zip_bytes=path.stat().st_size,
                    zip_sha256=sha256(path.read_bytes()).hexdigest())
    (DEST / 'source.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode())
    print(json.dumps(dict(files=len(records), zip_bytes=manifest['zip_bytes'], sha256=manifest['zip_sha256'])))


if __name__ == '__main__':
    main()
