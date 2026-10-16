"""Build the reproducible C# component download from its pinned source files."""
from hashlib import sha256
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/dotnet-components'
ASSETS = ROOT / 'docs/assets/dotnet-components'


def build():
    version = ET.parse(SOURCE / 'ComponentInvoice.csproj').find('.//PackageReference').attrib['Version']
    locked = json.loads((SOURCE / 'packages.lock.json').read_text())['dependencies']['net10.0']['FullBleed.DotNet']
    assert locked['resolved'] == version
    upstream = json.loads((SOURCE / 'upstream.json').read_text())
    for record in upstream['files']:
        assert sha256((SOURCE / record['path']).read_bytes()).hexdigest() == record['sha256'], record['path']
    names = ['.gitignore', 'ComponentInvoice.csproj', 'Program.cs', 'InvoiceDocument.cs', 'global.json',
             'packages.lock.json', 'README.md', 'LICENSE', 'upstream.json']
    names += [p.relative_to(SOURCE).as_posix() for p in (SOURCE / 'Assets').rglob('*') if p.is_file()]
    records = []
    ASSETS.mkdir(parents=True, exist_ok=True)
    target = ASSETS / 'project.zip'
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(names):
            data = (SOURCE / name).read_bytes()
            info = zipfile.ZipInfo('fullbleed-csharp-components/' + name, date_time=(2026, 10, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
            records.append({'path': name, 'bytes': len(data), 'sha256': sha256(data).hexdigest()})
    manifest = {'schema': 'fullbleed.dotnet-component-starter.v1', 'package': 'FullBleed.DotNet',
                'packageVersion': version, 'engineVersion': '2.5.22', 'framework': 'net10.0',
                'upstreamCommit': upstream['commit'], 'files': records,
                'zipSha256': sha256(target.read_bytes()).hexdigest(), 'zipBytes': target.stat().st_size,
                'outputs': {name: sha256((ASSETS / name).read_bytes()).hexdigest()
                            for name in ['invoice.pdf', 'page-1.png']}}
    (ASSETS / 'source.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'ok': True, 'files': len(records), 'zipSha256': manifest['zipSha256']}))
    return manifest


if __name__ == '__main__':
    build()
