"""Package the locked Workers invoice example with a reproducible inventory."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/cloudflare-pdf'
DEST = ROOT / 'docs/assets/cloudflare-starter'
PREFIX = 'fullbleed-cloudflare-invoice/'
FILES = ['.gitignore', 'LICENSE', 'README.md', 'package.json', 'package-lock.json',
         'release.json', 'sample.json', 'wrangler.json', 'src/index.mjs', 'src/handler.mjs',
         'src/document.mjs', 'src/styles.mjs', 'test/fixtures.mjs', 'test/request.test.mjs', 'test/worker.mjs']


def main():
    release = json.loads((SOURCE / 'release.json').read_text(encoding='utf-8'))
    package = json.loads((SOURCE / 'package.json').read_text(encoding='utf-8'))
    lock = json.loads((SOURCE / 'package-lock.json').read_text(encoding='utf-8'))
    assert package['dependencies']['fullbleed'] == release['packageVersion'] == '0.8.0'
    assert lock['packages']['node_modules/fullbleed']['integrity'] == release['packageIntegrity']
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
    assets = []
    for name in ['invoice.pdf', 'invoice.png', 'long-invoice.pdf']:
        data = (DEST / name).read_bytes()
        assets.append(dict(file=name, bytes=len(data), sha256=sha256(data).hexdigest()))
    manifest = dict(schema='fullbleed.cloudflare-starter.v1', prefix=PREFIX, **release,
                    files=records, zipBytes=path.stat().st_size, zipSha256=sha256(path.read_bytes()).hexdigest(), assets=assets)
    (DEST / 'source.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(dict(files=len(records), zipBytes=manifest['zipBytes'], sha256=manifest['zipSha256'])))


if __name__ == '__main__':
    main()
