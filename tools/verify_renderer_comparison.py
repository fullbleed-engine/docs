"""Check downloadable evidence, recompute statistics, and re-read the nine PDFs."""
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs/assets/renderer-comparison'
OUT = ROOT / 'output/renderer-comparison-verification'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def stats(values):
    q = statistics.quantiles(values, n=4, method='inclusive')
    return {'n': len(values), 'median': statistics.median(values), 'min': min(values),
            'max': max(values), 'q1': q[0], 'q3': q[2]}


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ASSETS / 'manifest.json').read_text())
    for item in manifest['files']:
        data = (ASSETS / item['path']).read_bytes()
        assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
    archive_counts = {}
    for item in manifest['archives']:
        with zipfile.ZipFile(ASSETS / item['file']) as z:
            assert z.testzip() is None
            listing = json.loads(z.read('MANIFEST.json'))
            assert listing['sourceCommit'] == manifest['sourceCommit']
            assert len(listing['files']) == item['members']
            assert set(z.namelist()) == {'MANIFEST.json', *(f['path'] for f in listing['files'])}
            for member in listing['files']:
                data = z.read(member['path'])
                assert len(data) == member['bytes'] and sha(data) == member['sha256'], member['path']
            archive_counts[item['file']] = len(listing['files'])
            if item['file'] == 'measured-evidence.zip':
                for name in z.namelist():
                    assert (OUT / name).resolve().is_relative_to(OUT.resolve())
                z.extractall(OUT)
    measured = OUT / 'measured'
    environment = json.loads((measured / 'environment.json').read_text())
    assert environment['source_revision'] == manifest['sourceCommit']
    for name, digest in environment['source_sha256'].items():
        assert sha((measured / 'source' / name).read_bytes()) == digest
    summary = json.loads((measured / 'summary.json').read_text())
    assert summary == json.loads((ASSETS / 'summary.json').read_text())
    assert summary['all_qualified'] and not summary['smoke']
    jobs = json.loads((measured / 'jobs.json').read_text())
    assert len(jobs) == 81
    collected = defaultdict(lambda: {'cold': [], 'warm': [], 'bytes': [], 'pages': set()})
    representatives = {}
    token_set = set()
    pdf_count = 0
    for job in jobs:
        assert job['exit_code'] == 0
        key = job['engine'], job['fixture']
        if job['engine'] == 'chromium':
            assert job['metadata']['browser_version'] == '153.0.8010.12'
        pair = collected[key]
        if job['phase'] == 'cold':
            pair['cold'].append(job['process_ms'])
        if job['phase'] == 'memory':
            samples = json.loads((measured / 'jobs' / job['job'] / 'rss-samples.json').read_text())
            pair['rss'] = max(s['rss_bytes'] for s in samples)
            assert pair['rss'] == job['sampled_peak_tree_rss_bytes']
        for row in job['rows']:
            assert row['token'] not in token_set
            token_set.add(row['token'])
            q = row['qualification']
            assert q['passed'] and not q['failures']
            data = (measured / row['path']).read_bytes()
            assert sha(data) == q['sha256'] and len(data) == q['bytes']
            pair['bytes'].append(len(data))
            pair['pages'].add(q['pages'])
            if job['phase'] == 'warm' and not row['warmup']:
                pair['warm'].append(row['render_write_ms'])
            representatives.setdefault(key, row)
            pdf_count += 1
    assert pdf_count == manifest['qualifiedPdfs'] == 414
    assert sum(len(p['cold']) + len(p['warm']) for p in collected.values()) == manifest['timedPdfs'] == 315
    article = (ROOT / 'docs/guides/renderer-comparison.md').read_text(encoding='utf-8')
    names = {'fullbleed': 'Fullbleed', 'weasyprint': 'WeasyPrint', 'chromium': 'Chromium'}
    for result in summary['results']:
        key = result['engine'], result['fixture']
        actual = collected[key]
        assert len(actual['cold']) == 5 and len(actual['warm']) == 30
        for key_name in ['cold', 'warm']:
            assert stats(actual[key_name]) == result[f'{key_name}_ms']
        assert stats(actual['bytes']) == result['bytes']
        assert sorted(actual['pages']) == result['pages']
        assert actual['rss'] == result['sampled_peak_tree_rss_bytes']
        cold, warm = result['cold_ms'], result['warm_ms']
        row = f"| {result['fixture'].title()} | {names[result['engine']]} | {result['pages'][0]} | "
        row += f"{cold['median']:,.1f} ({cold['min']:,.1f}–{cold['max']:,.1f}) | "
        row += f"{warm['median']:,.1f} ({warm['min']:,.1f}–{warm['max']:,.1f}) |"
        assert row in article, row
        size_row = f"| {result['fixture'].title()} | {names[result['engine']]} | {result['bytes']['median']/1024:.1f} | {actual['rss']/1024**2:.1f} |"
        assert size_row in article, size_row
    spec = importlib.util.spec_from_file_location('comparison_validation', measured / 'source/validate.py')
    validation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validation)
    page_count = 0
    for (engine, fixture), row in representatives.items():
        path = ASSETS / 'pdfs' / engine / f'{fixture}.pdf'
        assert sha(path.read_bytes()) == row['qualification']['sha256']
        contract = json.loads((measured / 'inputs' / f'{fixture}.json').read_text())
        result = validation.check_pdf(path, contract, row['token'])
        assert result['passed'], result
        page_count += result['pages']
    assert page_count == manifest['representativePages'] == 22
    controls = json.loads((measured / 'negative-controls.json').read_text())
    for control in controls.values():
        assert control['passed']
        for name in ['wrong_token', 'missing_page', 'missing_font', 'outside_page_inset']:
            assert control[name]
    report = {'ok': True, 'sourceCommit': manifest['sourceCommit'], 'archives': archive_counts,
              'retainedPdfsHashed': pdf_count, 'timedSamplesRecomputed': 315,
              'representativePdfsRevalidated': len(representatives), 'representativePages': page_count,
              'publishedTableRowsVerified': 18}
    (OUT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
