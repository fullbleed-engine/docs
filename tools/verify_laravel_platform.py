"""Verify the actual Laravel download rejects PHP 8.3 before writing local state."""
from hashlib import sha256
import argparse
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--php', default='php')
    parser.add_argument('--composer', default='composer')
    parser.add_argument('--out', type=Path, default=Path('output/laravel-platform'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    assets = root / 'docs/assets/laravel-starter'
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((assets/'source.json').read_text(encoding='utf-8'))
    archive = assets/'project.zip'
    assert sha256(archive.read_bytes()).hexdigest() == manifest['zip_sha256']
    php_version = subprocess.check_output([args.php,'-r','echo PHP_VERSION;'],text=True).strip()
    assert php_version.startswith('8.3.'), php_version
    with zipfile.ZipFile(archive) as source:
        assert set(source.namelist()) == {manifest['prefix'] + row['path'] for row in manifest['files']}
        for row in manifest['files']:
            name = manifest['prefix'] + row['path']
            assert (out/name).resolve().is_relative_to(out)
            assert sha256(source.read(name)).hexdigest() == row['sha256']
        source.extractall(out)
    project = out/manifest['prefix']
    composer = [args.php,args.composer] if args.composer.endswith('.phar') else [args.composer]
    requirements = subprocess.run([*composer,'check-platform-reqs','--lock','--format=json'],cwd=project,
        capture_output=True,text=True,timeout=60)
    report = json.loads(requirements.stdout)
    php, = [row for row in report if row['name'] == 'php']
    assert requirements.returncode != 0 and php['status'] == 'failed', report
    setup = subprocess.run([args.php,'setup.php',sys.executable],cwd=project,
        capture_output=True,text=True,timeout=30)
    assert setup.returncode == 1 and 'PHP 8.4 or later is required' in setup.stderr
    assert not (project/'.env').exists() and not (project/'database/database.sqlite').exists()
    result = {'ok':True,'php':php_version,'archive_sha256':manifest['zip_sha256'],
        'checks':['Composer checks reject the actual PHP runtime', 'setup explains the required PHP version',
                  'unsupported setup creates no credentials or database'],
        'composer_platform':report,'setup_message':setup.stderr.strip()}
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
