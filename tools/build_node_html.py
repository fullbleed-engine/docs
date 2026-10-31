"""Reproducibly package the static-HTML migration example, including its reference."""
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/node-html'
DEST = ROOT / 'docs/assets/node-html'
FILES = ['LICENSE', 'README.md', 'package.json', 'package-lock.json', 'render.mjs', 'document.mjs',
         'template.html', 'print.css', 'records.json', 'assets/logo.svg', 'fonts/SourceSans3-Regular.ttf',
         'fonts/SourceSans3-Bold.ttf', 'fonts/OFL.txt', 'fonts/source.json',
         'reference/package.json', 'reference/package-lock.json', 'reference/render.mjs']

def build():
    package = json.loads((SOURCE / 'package.json').read_text(encoding='utf-8'))
    lock = json.loads((SOURCE / 'package-lock.json').read_text(encoding='utf-8'))
    reference = json.loads((SOURCE / 'reference/package.json').read_text(encoding='utf-8'))
    ref_lock = json.loads((SOURCE / 'reference/package-lock.json').read_text(encoding='utf-8'))
    assert package['dependencies'] == {'fullbleed': '0.9.0'}
    assert reference['dependencies'] == {'puppeteer': '25.16.0'}
    assert lock['packages']['node_modules/fullbleed']['version'] == package['dependencies']['fullbleed']
    assert ref_lock['packages']['node_modules/puppeteer']['version'] == reference['dependencies']['puppeteer']
    DEST.mkdir(parents=True, exist_ok=True)
    records = {}
    archive_path = DEST / 'project.zip'
    with ZipFile(archive_path, 'w', compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(FILES):
            data = (SOURCE / name).read_bytes()
            info = ZipInfo('node-html-to-pdf/' + name, date_time=(2026, 10, 31, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
            records[name] = {'bytes': len(data), 'sha256': sha256(data).hexdigest()}
    record = {'schema': 'fullbleed.node-html-project.v1', 'source_directory': 'examples/node-html',
              'package_version': '0.9.0', 'engine_version': '2.5.46', 'puppeteer_version': '25.16.0',
              'package_integrity': lock['packages']['node_modules/fullbleed']['integrity'],
              'puppeteer_integrity': ref_lock['packages']['node_modules/puppeteer']['integrity'],
              'files': records, 'zip_bytes': archive_path.stat().st_size,
              'zip_sha256': sha256(archive_path.read_bytes()).hexdigest()}
    (DEST / 'source.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'ok': True, 'files': len(records), 'zip_sha256': record['zip_sha256']}))

if __name__ == '__main__':
    build()
