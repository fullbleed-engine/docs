"""Bundle the Node render-queue example with its pinned public npm package."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/node-queue'
DEST = ROOT / 'docs/assets/node-queue'
FILES = ['LICENSE', 'README.md', 'invoice.html', 'invoice.css', 'render.mjs',
         'package.json', 'package-lock.json']
record = json.loads((SOURCE / 'source.json').read_text(encoding='utf-8'))
package = json.loads((SOURCE / 'package.json').read_text(encoding='utf-8'))
lock = json.loads((SOURCE / 'package-lock.json').read_text(encoding='utf-8'))
assert record['package_version'] == package['dependencies']['fullbleed']
assert record['package_integrity'] == lock['packages']['node_modules/fullbleed']['integrity']
assert record['package_integrity'].startswith('sha512-')
DEST.mkdir(parents=True, exist_ok=True)
target = DEST / 'project.zip'
records = []
with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name in FILES:
        data = (SOURCE / name).read_bytes()
        info = zipfile.ZipInfo('node-pdf-queue/' + name, date_time=(2026, 10, 7, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data, compresslevel=9)
        records.append({'path': name, 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
record.update(files=records, zip_bytes=target.stat().st_size,
              zip_sha256=sha256(target.read_bytes()).hexdigest())
(DEST / 'source.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({'ok': True, 'files': len(FILES), 'zip_sha256': record['zip_sha256']}))
