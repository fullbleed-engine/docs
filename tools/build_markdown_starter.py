"""Package the Markdown starter's explicit source set reproducibly."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/markdown'
DESTINATION = ROOT / 'docs/assets/markdown-starter'
FILES = [
    'LICENSE', 'README.md', 'requirements.txt', 'render.py', 'print.css', 'brief.md',
    'images/publishing.svg', 'fonts/IBMPlexMono-Regular.ttf', 'fonts/OFL.txt', 'fonts/source.json',
]


def main():
    DESTINATION.mkdir(parents=True, exist_ok=True)
    records = []
    archive_path = DESTINATION / 'project.zip'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(FILES):
            data = (SOURCE / name).read_bytes()
            entry = zipfile.ZipInfo('fullbleed-markdown-starter/' + name, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
            records.append({'path': name, 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
    manifest = {'source': 'examples/markdown', 'files': records,
                'zip_bytes': archive_path.stat().st_size, 'zip_sha256': sha256(archive_path.read_bytes()).hexdigest()}
    (DESTINATION / 'source.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'files': len(records), 'zip_bytes': manifest['zip_bytes'], 'zip_sha256': manifest['zip_sha256']}))


if __name__ == '__main__':
    main()
