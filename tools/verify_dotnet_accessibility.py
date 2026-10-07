"""Restore the real tagged-notice ZIP and verify its isolated published .NET app."""
import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

from pypdf import PdfReader
from build_dotnet_accessibility_starter import ROOT, ASSETS, project_files, digest
from pdfua_validation import validator, check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dotnet', default=shutil.which('dotnet'))
    parser.add_argument('--out', type=Path, default=ROOT / 'output/dotnet-accessibility-verification')
    parser.add_argument('--verapdf-cp', type=Path)
    parser.add_argument('--refresh-evidence', action='store_true',
                        help='Replace the downloadable reports after all checks pass')
    args = parser.parse_args()
    assert args.dotnet, 'Install the .NET 10 SDK or pass --dotnet'
    dotnet = str(Path(args.dotnet).resolve())
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix='tagged notice with spaces ', dir=out)).resolve()
    project = workspace / 'fullbleed-tagged-notice'
    manifest = json.loads((ASSETS / 'source.json').read_text(encoding='utf-8'))
    assert manifest['framework'] == 'net10.0' and manifest['packageVersion'] == '0.1.7'
    sources = project_files()
    content = (ASSETS / 'project.zip').read_bytes()
    assert digest(content) == manifest['projectZipSha256']
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        expected = {'fullbleed-tagged-notice/' + name: data for name, data in sources.items()}
        assert len(archive.namelist()) == len(expected) and set(archive.namelist()) == set(expected)
        for name, data in expected.items():
            assert archive.read(name) == data
            path = workspace / name
            assert path.resolve().is_relative_to(workspace)
            path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
    assert len(manifest['files']) == len(sources)
    for entry in manifest['files']:
        data = sources[entry['path']]
        assert digest(data) == entry['sha256'] and len(data) == entry['bytes']
    env = dict(os.environ, DOTNET_ROOT=str(Path(dotnet).parent), DOTNET_ROLL_FORWARD='LatestPatch',
               NUGET_PACKAGES=str(workspace / 'nuget-cache'), NUGET_HTTP_CACHE_PATH=str(workspace / 'nuget-http-cache'),
               DOTNET_CLI_TELEMETRY_OPTOUT='1')
    env.pop('FULLBLEED_NATIVE_LIBRARY', None)
    commands = []
    def run(label, arguments, cwd=project):
        result = subprocess.run([dotnet, *map(str, arguments)], cwd=cwd, env=env,
                                capture_output=True, text=True, encoding='utf-8', timeout=240)
        (out / (label + '.stdout.txt')).write_text(result.stdout, encoding='utf-8')
        (out / (label + '.stderr.txt')).write_text(result.stderr, encoding='utf-8')
        assert result.returncode == 0, f'{label} failed; see {out}'
        commands.append(label)
        return result.stdout
    sdk = run('sdk', ['--version']).strip(); assert sdk.startswith('10.0.')
    run('restore', ['restore', '--locked-mode', '--source', 'https://api.nuget.org/v3/index.json'])
    published = workspace / 'isolated-publish'
    run('publish', ['publish', '-c', 'Release', '--no-restore', '-o', published])
    package_dir = workspace / 'nuget-cache/fullbleed.dotnet/0.1.7'
    provenance = json.loads((package_dir / 'native-provenance.json').read_text())
    engine = next(p for p in provenance['dependencies'] if p['name'] == 'fullbleed')
    assert engine['version'] == '2.5.13'
    classpath = args.verapdf_cp or validator(out / 'validator-cache')
    records = []
    native_identity = None
    for profile in ['ua1', 'ua2']:
        folder = out / profile
        run(profile, [published / 'AccessibleNotice.dll', '--profile', profile, '--out', folder], cwd=workspace)
        run(profile + '-repeat', [published / 'AccessibleNotice.dll', '--profile', profile, '--out', out / (profile + '-repeat')], cwd=workspace)
        pdf = folder / 'notice.pdf'
        assert pdf.read_bytes() == (out / (profile + '-repeat') / 'notice.pdf').read_bytes()
        assert pdf.read_bytes() == (ASSETS / f'notice-{profile}.pdf').read_bytes(), 'Review changed sample PDF'
        previews = list((folder / 'preview').glob('*.png')); assert len(previews) == 1
        assert previews[0].read_bytes() == (ASSETS / 'notice.png').read_bytes(), 'Review changed sample preview'
        report = json.loads((folder / 'render.json').read_text())
        assert report['profile'] == profile and report['pdfSha256'] == digest(pdf.read_bytes())
        assert report['runtime'].startswith('10.0.') and report['framework'] == '.NETCoreApp,Version=v10.0'
        assert report['engine']['BindingVersion'] == '0.1.7'
        native_name = {'win-x64': 'fullbleed_dotnet_native.dll', 'linux-x64': 'libfullbleed_dotnet_native.so',
                       'osx-x64': 'libfullbleed_dotnet_native.dylib', 'osx-arm64': 'libfullbleed_dotnet_native.dylib'}[report['runtimeRid']]
        relative_native = Path('runtimes') / report['runtimeRid'] / 'native' / native_name
        assert (published / relative_native).read_bytes() == (package_dir / relative_native).read_bytes()
        identity = {'runtime': report['runtime'], 'framework': report['framework'], 'rid': report['runtimeRid'],
                    'nativeLibrarySha256': digest((published / relative_native).read_bytes())}
        assert native_identity is None or native_identity == identity
        native_identity = identity
        assert not report['diagnostics']['MissingGlyphs']
        reader = PdfReader(pdf, strict=True)
        assert len(reader.pages) == 1
        catalog = reader.trailer['/Root']
        assert catalog['/Lang'] == 'en-US' and catalog['/MarkInfo']['/Marked']
        assert catalog['/StructTreeRoot'].get('/K') is not None
        text = ' '.join(reader.pages[0].extract_text().split())
        for phrase in ['Your next chapter.', 'Your visit', 'Session schedule', 'Finding the room',
                       'Before you arrive', 'example.org/workshops', 'Fictional event and location.']:
            assert text.count(phrase) == 1, phrase
        (folder / 'text.txt').write_text(text + '\n', encoding='utf-8')
        validation = check(pdf, profile, classpath, folder)
        records.append({'profile': profile, 'pdfSha256': digest(pdf.read_bytes()),
                        'previewSha256': digest(previews[0].read_bytes()), 'textSha256': digest(text.encode()),
                        'repeatPdfBytesIdentical': True, 'veraPDF': validation})
    assert records[0]['previewSha256'] == records[1]['previewSha256']
    assert records[0]['textSha256'] == records[1]['textSha256']
    for name, expected_hash in manifest['outputs'].items():
        assert digest((ASSETS / name).read_bytes()) == expected_hash
    result = {'ok': True, 'checkedAt': datetime.now(timezone.utc).isoformat(), 'sdk': sdk,
        'package': 'FullBleed.DotNet', 'packageVersion': '0.1.7', 'engineVersion': engine['version'],
        'packageSha256': digest((package_dir / 'fullbleed.dotnet.0.1.7.nupkg').read_bytes()),
        'projectZipSha256': manifest['projectZipSha256'], 'freshNugetCache': True,
        'nativeLibraryOverride': False, 'isolatedPublishedApp': True, 'commands': commands, 'profiles': records,
        'runtimeIdentity': native_identity,
        'scope': 'Downloaded starter, retained final PDFs and machine-verifiable PDF/UA checks. No blanket accessibility or assistive-technology claim.'}
    if args.refresh_evidence:
        result['validatorReports'] = {}
        for profile in ['ua1', 'ua2']:
            report_bytes = (out / profile / 'verapdf.json').read_bytes()
            name = f'verapdf-{profile}.json'
            (ASSETS / name).write_bytes(report_bytes)
            result['validatorReports'][name] = digest(report_bytes)
        (ASSETS / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    retained = json.loads((ASSETS / 'verification.json').read_text(encoding='utf-8'))
    assert retained['ok']
    for key in ['packageVersion', 'engineVersion', 'packageSha256', 'projectZipSha256', 'profiles']:
        assert retained[key] == result[key], f'Refresh the published verification record: {key}'
    assert set(retained['validatorReports']) == {'verapdf-ua1.json', 'verapdf-ua2.json'}
    for name, expected_hash in retained['validatorReports'].items():
        assert digest((ASSETS / name).read_bytes()) == expected_hash
    result['publishedEvidenceVerified'] = True
    (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'profiles': 2, 'packageVersion': '0.1.7', 'engineVersion': engine['version']}))


if __name__ == '__main__':
    main()
