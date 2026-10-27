"""Build the C# PDF-template download from an explicit source inventory."""
from hashlib import sha256
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/dotnet-pdf-template'
ASSETS = ROOT / 'docs/assets/dotnet-pdf-template'
FILES = ['.gitignore', 'CertificateRecords.cs', 'Program.cs', 'TemplateCertificates.csproj',
    'global.json', 'packages.lock.json', 'upstream.json', 'README.md', 'LICENSE',
    'Assets/data.json', 'Assets/template.pdf', 'Assets/template.html', 'Assets/template.css',
    'Assets/overlay.css', 'Assets/Inter-Variable.ttf', 'Assets/Inter-OFL.txt']

def main():
    upstream = json.loads((SOURCE / 'upstream.json').read_text(encoding='utf-8'))
    version = ET.parse(SOURCE / 'TemplateCertificates.csproj').find('.//PackageReference').attrib['Version']
    locked = json.loads((SOURCE / 'packages.lock.json').read_text())['dependencies']['net10.0']['FullBleed.DotNet']
    assert version == upstream['packageVersion'] == locked['resolved']
    for record in upstream['assets']:
        assert sha256((SOURCE / record['path']).read_bytes()).hexdigest() == record['sha256']
    ASSETS.mkdir(parents=True, exist_ok=True)
    target = ASSETS / 'project.zip'
    records = []
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(FILES):
            data = (SOURCE / name).read_bytes()
            entry = zipfile.ZipInfo('fullbleed-csharp-pdf-template/' + name, (2026, 10, 27, 0, 0, 0))
            entry.create_system = 3
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data, compresslevel=9)
            records.append(dict(path=name, bytes=len(data), sha256=sha256(data).hexdigest()))
    manifest = dict(schema='fullbleed.dotnet-pdf-template.v1', source='examples/dotnet-pdf-template',
        package='FullBleed.DotNet', packageVersion=version, engineVersion=upstream['engineVersion'],
        packageSha256=upstream['packageSha256'], packageCommit=upstream['packageCommit'], framework='net10.0',
        files=records, zipBytes=target.stat().st_size, zipSha256=sha256(target.read_bytes()).hexdigest(),
        outputs={name: sha256((ASSETS / name).read_bytes()).hexdigest()
            for name in ['certificates.pdf', 'page-1.png', 'page-2.png', 'page-3.png']})
    (ASSETS / 'source.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode('utf-8'))
    print(json.dumps(dict(files=len(records), zipBytes=manifest['zipBytes'], zipSha256=manifest['zipSha256'])))

if __name__ == '__main__':
    main()
