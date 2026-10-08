"""Package the numbered report's explicit sources reproducibly."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'examples/numbered-report'
DESTINATION = ROOT/'docs/assets/numbered-report'
FILES = ['LICENSE', 'README.md', 'requirements.txt', 'render.py', 'report.html', 'report.css']


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = []
    archive_path = DESTINATION/'project.zip'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(FILES):
            data = (SOURCE/name).read_bytes()
            entry = zipfile.ZipInfo('fullbleed-numbered-report/'+name, (2026, 1, 1, 0, 0, 0))
            # Preserve the published ZIP bytes on Windows and Unix hosts.
            entry.create_system = 0
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
            records.append(dict(path=name, bytes=len(data), sha256=sha256(data).hexdigest()))
    manifest = dict(source='examples/numbered-report', files=records,
        zip_bytes=archive_path.stat().st_size, zip_sha256=sha256(archive_path.read_bytes()).hexdigest())
    (DESTINATION/'source.json').write_bytes((json.dumps(manifest, indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(files=len(records), zip_bytes=manifest['zip_bytes'], zip_sha256=manifest['zip_sha256'])))


if __name__ == '__main__':
    main()
