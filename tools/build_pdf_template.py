"""Package the explicit certificate template sources reproducibly."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/pdf-template'
DESTINATION = ROOT / 'docs/assets/pdf-template'
FILES = ['LICENSE', 'Inter-OFL.txt', 'README.md', 'requirements.txt', 'render.py', 'data.json',
         'overlay.css', 'template.pdf', 'template.html', 'template.css', 'build_template.py']


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = []
    path = DESTINATION / 'project.zip'
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(FILES):
            data = (SOURCE / name).read_bytes()
            entry = zipfile.ZipInfo('fullbleed-pdf-template/' + name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 0
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
            records.append(dict(path=name, bytes=len(data), sha256=sha256(data).hexdigest()))
    manifest = dict(source='examples/pdf-template', files=records,
                    zip_bytes=path.stat().st_size, zip_sha256=sha256(path.read_bytes()).hexdigest())
    (DESTINATION / 'source.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(dict(files=len(records), zip_bytes=manifest['zip_bytes'], zip_sha256=manifest['zip_sha256'])))


if __name__ == '__main__':
    main()
