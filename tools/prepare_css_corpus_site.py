"""Materialize checksum-pinned CSS comparison evidence into a built documentation site."""
from collections import Counter
from hashlib import sha256
import argparse
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'ironpress-evidence/current/'
VERDICTS = {'PASS', 'FAIL', 'REFERENCE-DISPUTED'}


def prepare(site, config_path, archive_path=None):
    config = json.loads(config_path.read_text(encoding='utf-8'))
    assert config['schema'] == 'fullbleed.css-corpus-publication.v1'
    assert config['packageSource'] == 'published'
    assert re.fullmatch(r'\d+\.\d+\.\d+', config['version'])
    assert re.fullmatch(r'[a-f0-9]{64}', config['archiveSha256'])
    url = urlsplit(config['archiveUrl'])
    assert url.scheme == 'https' and url.netloc == 'github.com'
    assert url.path.startswith('/fullbleed-engine/fullbleed-official/releases/download/')
    if archive_path is None:
        archive_path = ROOT / 'target' / f"css-corpus-{config['archiveSha256']}.zip"
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        if not archive_path.exists():
            with urlopen(Request(config['archiveUrl'], headers={'User-Agent': 'Fullbleed-docs-evidence-build'}), timeout=120) as response:
                data = response.read(config['archiveBytes'] + 1)
            assert len(data) == config['archiveBytes']
            assert sha256(data).hexdigest() == config['archiveSha256']
            archive_path.write_bytes(data)
    assert archive_path.stat().st_size == config['archiveBytes']
    assert sha256(archive_path.read_bytes()).hexdigest() == config['archiveSha256']
    site = site.resolve(strict=True)
    assert (site / 'index.html').is_file()
    output = site / 'assets/css-corpus' / config['version']
    assert output.resolve().is_relative_to(site)
    output.mkdir(parents=True, exist_ok=True)
    written = {}

    def put(name, data):
        parts = PurePosixPath(name)
        assert not parts.is_absolute() and '..' not in parts.parts and '\\' not in name
        destination = output.joinpath(*parts.parts)
        assert destination.resolve().is_relative_to(output.resolve())
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            assert destination.read_bytes() == data, f'Conflicting generated artifact: {name}'
        else:
            destination.write_bytes(data)
        written[name] = {'bytes': len(data), 'sha256': sha256(data).hexdigest()}
        return name

    with zipfile.ZipFile(archive_path) as archive:
        assert len(set(archive.namelist())) == len(archive.namelist())
        assert sum(item.file_size for item in archive.infolist()) < 512 * 1024 * 1024
        manifest = json.loads(archive.read(PREFIX + 'manifest.json'))

        def verified(name):
            data = archive.read(PREFIX + name)
            assert manifest['files'][name] == {'bytes': len(data), 'sha256': sha256(data).hexdigest()}, name
            return data

        provenance = json.loads(verified('fullbleed-run.json'))
        report_data = verified('report.json')
        report = json.loads(report_data)
        input_record = json.loads(archive.read('ironpress-input.json'))
        assert input_record['package_source'] == 'published'
        assert input_record['wheel_sha256'] == provenance['wheel']['sha256'] == config['wheelSha256']
        assert input_record['wheel'] == provenance['wheel']['filename'] == config['wheelFilename']
        assert provenance['wheel']['version'] == config['version']
        assert provenance['upstream_commit'] == config['upstreamCommit']
        assert provenance['filter'] is None and provenance['scope'] == 'full_corpus'
        assert provenance['report_check']['verified_complete'] and not provenance['report_check']['problems']
        assert not provenance['copy_problems'] and report['run_complete']
        assert report['invocation_id'] == provenance['invocation_id'] == config['invocationId']
        assert sha256(report_data).hexdigest() == provenance['report_check']['report_sha256']
        assert report['overall'] == config['overall']
        assert provenance['gate_passed'] == config['gatePassed']
        fixtures = []
        keys = set()
        for category in report['categories']:
            for feature in category['features']:
                for fixture in feature['fixtures']:
                    category_name, name = fixture['category'], fixture['id']
                    assert all(re.fullmatch(r'[a-z0-9_-]+', value) for value in [category_name, name])
                    key = f'{category_name}/{name}'
                    assert key not in keys and fixture['status'] in VERDICTS
                    keys.add(key)
                    pdf_name = f'pdfs/{key}.pdf'
                    put(pdf_name, verified(pdf_name))
                    pages = []
                    for index in range(max(len(fixture['raster']['candidate']), len(fixture['raster']['oracle']))):
                        suffix = '' if index == 0 else f'.p{index + 1}'
                        page = {}
                        for label, directory, raster in [('candidate', 'out', 'candidate'), ('reference', 'refs', 'oracle')]:
                            if index < len(fixture['raster'][raster]):
                                image_name = f'{directory}/{key}{suffix}.png'
                                page[label] = put(image_name, verified(image_name))
                            else:
                                page[label] = None
                        pages.append(page)
                    fixtures.append({
                        'key': key, 'id': name, 'category': category_name, 'feature': fixture['feature'],
                        'description': fixture['description'], 'status': fixture['status'],
                        'differencePercent': fixture['semantic_diff_pct'], 'referenceRenderer': fixture['oracle'],
                        'referenceStatus': fixture['reference']['status'], 'referenceNote': fixture['reference']['note'],
                        'diagnosis': (fixture.get('diagnosis') or {}).get('headline'), 'pdf': pdf_name,
                        'pdfSha256': written[pdf_name]['sha256'], 'pages': pages,
                        'htmlSha256': fixture['html_sha256'],
                        'sourceUrl': f"https://github.com/gastongouron/ironpress/blob/{config['upstreamCommit']}/tests/parity/cases/{key}.html",
                    })
        counts = Counter(f['status'] for f in fixtures)
        expected = {'PASS': report['overall']['pass'], 'FAIL': report['overall']['fail'],
                    'REFERENCE-DISPUTED': report['overall']['reference_disputed']}
        assert dict(counts) == expected and len(fixtures) == report['overall']['total'] == 1662
        put('report.json', report_data)
        put('fullbleed-run.json', verified('fullbleed-run.json'))
        put('IRONPRESS-LICENSE.txt', verified('IRONPRESS-LICENSE'))
        index = {'schema': 'fullbleed.css-explorer.v1', 'version': config['version'],
            'packageSource': 'published', 'counts': expected, 'total': len(fixtures),
            'gatePassed': provenance['gate_passed'], 'runUrl': config['runUrl'],
            'archiveUrl': config['archiveUrl'], 'upstreamCommit': config['upstreamCommit'],
            'wheelSha256': config['wheelSha256'], 'invocationId': config['invocationId'],
            'fixtures': sorted(fixtures, key=lambda row: row['key'])}
        put('index.json', (json.dumps(index, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'))
    summary = {'schema': 'fullbleed.css-explorer-build.v1', 'archiveSha256': config['archiveSha256'],
        'counts': expected, 'fixtures': len(fixtures), 'files': written,
        'scope': 'Presentation copy of verified published-wheel evidence. Original fixture verdicts, reference metadata, images and PDF bytes are preserved.'}
    (output / 'site-manifest.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'fixtures': len(fixtures), 'counts': expected, 'files': len(written),
        'bytes': sum(item['bytes'] for item in written.values()), 'gatePassed': provenance['gate_passed']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', type=Path)
    parser.add_argument('--config', type=Path, default=ROOT / 'docs/assets/css-corpus/published.json')
    parser.add_argument('--archive', type=Path)
    args = parser.parse_args()
    # Previously published evidence URLs must continue to resolve when the
    # current explorer advances to another package. Each historical manifest
    # retains its own immutable archive and is checked just like the current one.
    historical = sorted((args.config.parent / 'history').glob('*.json'))
    versions = set()
    for config_path in [*historical, args.config]:
        config = json.loads(config_path.read_text(encoding='utf-8'))
        assert config['version'] not in versions, f'Duplicate published evidence version: {config["version"]}'
        versions.add(config['version'])
    for config_path in historical:
        prepare(args.site, config_path)
    prepare(args.site, args.config, args.archive)
    current = json.loads(args.config.read_text(encoding='utf-8'))['version']
    inventory = {'schema': 'fullbleed.css-explorer-versions.v1', 'current': current,
                 'versions': [current, *[json.loads(path.read_text(encoding='utf-8'))['version'] for path in historical]]}
    (args.site / 'assets/css-corpus/versions.json').write_text(
        json.dumps(inventory, indent=2) + '\n', encoding='utf-8', newline='\n')
