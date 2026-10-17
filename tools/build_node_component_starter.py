"""Build the reproducible JavaScript/TSX component project download."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/node-components'
DEST = ROOT / 'docs/assets/node-components'
FILES = ['README.md', 'LICENSE', 'package.json', 'package-lock.json', 'tsconfig.json',
         'document.mjs', 'styles.mjs', 'invoice.mjs', 'invoice.tsx', 'render-tsx.mjs', 'data.json', 'upstream.json']


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    records = []
    target = DEST / 'project.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            # This source-only project uses canonical LF text in Git and the ZIP.
            data = (SOURCE / name).read_bytes().replace(b'\r\n', b'\n')
            info = zipfile.ZipInfo('fullbleed-node-components/' + name, date_time=(2026, 10, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
            records.append({'path': name, 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
    manifest = {'schema': 'fullbleed.node-component-starter.v1', 'package': 'fullbleed@0.7.1', 'engine': '2.5.29',
                'files': records, 'zip_sha256': sha256(target.read_bytes()).hexdigest(), 'zip_bytes': target.stat().st_size}
    manifest['rendered'] = {name: {'sha256': sha256((DEST / name).read_bytes()).hexdigest(), 'bytes': (DEST / name).stat().st_size}
                            for name in ['invoice.pdf', 'page-1.png']}
    (DEST / 'source.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'ok': True, 'files': len(records), 'zip_sha256': manifest['zip_sha256']}))
    return manifest


if __name__ == '__main__':
    build()
