"""Assemble the n8n workflow kit and the shared invoice renderer reproducibly."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'docs/assets/n8n-starter'
SOURCE = ROOT / 'examples/n8n-pdf'
LAMBDA = ROOT / 'examples/lambda-pdf'
PREFIX = 'fullbleed-n8n-starter/'
OWN = ['README.md', '.gitignore', '.dockerignore', 'Dockerfile', 'compose.yaml',
       'server.py', 'requirements.txt', 'post_invoice.py', 'workflows/invoice-webhook.json']
SHARED = ['handler.py', 'LICENSE', 'templates/invoice.html', 'templates/invoice.css',
          'fonts/DMSerifDisplay-Regular.ttf', 'fonts/DMSerifDisplay-OFL.txt',
          'fonts/BebasNeue-Regular.ttf', 'fonts/BebasNeue-OFL.txt']


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    sources = {name: SOURCE / name for name in OWN}
    sources.update({'renderer/' + name: LAMBDA / name for name in SHARED})
    sources.update({'LICENSE': LAMBDA / 'LICENSE', 'sample.json': LAMBDA / 'sample.json'})
    records = []
    with zipfile.ZipFile(DEST / 'project.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, source in sorted(sources.items()):
            data = source.read_bytes()
            entry = zipfile.ZipInfo(PREFIX + name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 0
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
            records.append(dict(path=name, source=source.relative_to(ROOT).as_posix(),
                                bytes=len(data), sha256=sha256(data).hexdigest()))
    archive = (DEST / 'project.zip').read_bytes()
    manifest = dict(schema='fullbleed.n8n-starter.v1', prefix=PREFIX, engine='2.5.20', n8n='2.42.5',
                    files=records, zip_bytes=len(archive), zip_sha256=sha256(archive).hexdigest())
    (DEST / 'source.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode())
    (DEST / 'invoice-webhook.json').write_bytes((SOURCE / 'workflows/invoice-webhook.json').read_bytes())
    for name in ['invoice.pdf', 'invoice.png']:
        (DEST / name).write_bytes((ROOT / 'docs/assets/lambda-starter' / name).read_bytes())
    print(json.dumps(dict(files=len(records), bytes=len(archive), sha256=manifest['zip_sha256'])))


if __name__ == '__main__':
    main()
