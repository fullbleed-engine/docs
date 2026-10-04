"""Restore a fresh NuGet cache and execute the C# guide and designed invoice."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--package-source', default='https://api.nuget.org/v3/index.json')
parser.add_argument('--out', type=Path, default=Path('output/dotnet-verification'))
parser.add_argument('--update-assets', action='store_true')
args = parser.parse_args()
guide = (ROOT / 'docs/getting-started/dotnet.md').read_text(encoding='utf-8')
framework = re.search(r'dotnet new console -n InvoiceDemo --framework (net\d+\.0)', guide).group(1)
framework_version = framework.removeprefix('net')
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix='fullbleed dotnet docs ')).resolve()
(workspace / 'global.json').write_text(json.dumps({
    'sdk': {'version': framework_version + '.100', 'rollForward': 'latestFeature', 'allowPrerelease': False}
}) + '\n', encoding='utf-8')
cache = workspace / 'nuget-cache'
env = dict(os.environ, NUGET_PACKAGES=str(cache),
           NUGET_HTTP_CACHE_PATH=str(workspace / 'nuget-http-cache'),
           DOTNET_ROLL_FORWARD='LatestPatch')
env.pop('FULLBLEED_NATIVE_LIBRARY', None)
commands = []


def run(label, command, cwd=workspace):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                            text=True, encoding='utf-8', timeout=240)
    (out / f'{label}.stdout.txt').write_text(result.stdout, encoding='utf-8')
    (out / f'{label}.stderr.txt').write_text(result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'{label} failed; see {out / (label + ".stdout.txt")}')
    commands.append({'name': label, 'exit_code': 0})
    return result.stdout


project_source = ROOT / 'examples/dotnet/NorthstarInvoice.csproj'
version = ET.parse(project_source).find('.//PackageReference').attrib['Version']
assert ET.parse(project_source).find('.//TargetFramework').text == framework
assert f'dotnet add package FullBleed.DotNet --version {version}' in guide
blocks = re.findall(r'```csharp\n(.*?)```', guide, re.S)
assert len(blocks) == 2

run('new-console', ['dotnet', 'new', 'console', '--framework', framework,
                    '--name', 'InvoiceDemo', '--output', 'InvoiceDemo', '--no-restore'])
snippet = workspace / 'InvoiceDemo'
(snippet / 'Program.cs').write_text(blocks[0], encoding='utf-8')
run('install-package', ['dotnet', 'add', 'package', 'FullBleed.DotNet', '--version',
                        version, '--source', args.package_source], snippet)
run('run-guide', ['dotnet', 'run', '-c', 'Release', '--no-restore'], snippet)
snippet_pdf = snippet / 'invoice.pdf'
reader = PdfReader(snippet_pdf, strict=True)
assert len(reader.pages) == 1
assert ' '.join(reader.pages[0].extract_text().split()) == (
    'Invoice INV-1042 Consulting: USD 1,200.00'
)
shutil.copy2(snippet_pdf, out / 'quickstart.pdf')

sample = workspace / 'examples/dotnet'
sample.mkdir(parents=True)
for name in ['NorthstarInvoice.csproj', 'Program.cs']:
    shutil.copy2(ROOT / 'examples/dotnet' / name, sample / name)
assets = workspace / 'docs/assets/showcase'
assets.mkdir(parents=True)
for name in ['invoice.html', 'invoice.css']:
    shutil.copy2(ROOT / 'docs/assets/showcase' / name, assets / name)
shutil.copytree(ROOT / 'docs/assets/playground/fonts', workspace / 'docs/assets/playground/fonts')
run('restore-sample', ['dotnet', 'restore', '--source', args.package_source,
                       '--packages', str(cache), '--force-evaluate'], sample)
sample_output = run('run-sample', ['dotnet', 'run', '-c', 'Release', '--no-restore', '--',
                                  str(out / 'northstar')], sample)
runtime_version = re.search(r'Rendered with \.NET (\d+\.\d+\.\d+)\.', sample_output).group(1)
assert runtime_version.startswith(framework_version + '.')

installed = cache / 'fullbleed.dotnet' / version
provenance = json.loads((installed / 'native-provenance.json').read_text(encoding='utf-8'))
engine = next(p for p in provenance['dependencies'] if p['name'] == 'fullbleed')
assert f'It pins Fullbleed {engine["version"]}.' in guide
outputs = {}
for generated, published in [('invoice.pdf', 'invoice-dotnet.pdf'),
                             ('invoice_page1.png', 'invoice-dotnet.png')]:
    content = (out / 'northstar' / generated).read_bytes()
    outputs[generated] = hashlib.sha256(content).hexdigest()
    destination = ROOT / 'docs/assets/showcase' / published
    if args.update_assets:
        destination.write_bytes(content)
    else:
        assert content == destination.read_bytes(), f'Review regenerated {published}'
invoice = PdfReader(out / 'northstar/invoice.pdf', strict=True)
assert len(invoice.pages) == 1
text = ' '.join(invoice.pages[0].extract_text().split())
assert text.count('Maple & Finch') == 1 and text.count('$1,870.00') == 2
package = installed / f'fullbleed.dotnet.{version}.nupkg'
report = {
    'ok': True,
    'sdk': subprocess.check_output(['dotnet', '--version'], cwd=workspace, text=True).strip(),
    'target_framework': framework,
    'runtime_version': runtime_version,
    'package_version': version,
    'engine_version': engine['version'],
    'package_source': args.package_source,
    'package_sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
    'workspace': str(workspace),
    'fresh_nuget_cache': True,
    'fresh_nuget_http_cache': True,
    'native_library_override': False,
    'commands': commands,
    'outputs': outputs,
    'quickstart_pdf_sha256': hashlib.sha256(snippet_pdf.read_bytes()).hexdigest(),
    'scope': 'The guide snippet and exact sample sources consume the NuGet package outside the checkout.',
}
(out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps({'ok': True, 'package': version, 'engine': engine['version'],
                  'commands': len(commands), 'package_source': args.package_source}))
