"""Build the Laravel queue starter reproducibly, excluding local runtime state."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'examples/laravel-pdf'
DEST = ROOT / 'docs/assets/laravel-starter'
PREFIX = 'fullbleed-laravel-starter/'


def main():
    names = ['.env.example', '.gitignore', 'composer.json', 'composer.lock', 'artisan',
             'setup.php', 'README.md', 'LICENSE', 'sample.json',
             'bootstrap/app.php', 'bootstrap/providers.php', 'bootstrap/cache/.gitignore']
    for directory in ['app', 'config', 'database/migrations', 'routes', 'public', 'resources', 'renderer']:
        names.extend(p.relative_to(SOURCE).as_posix() for p in (SOURCE / directory).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts)
    names.extend(p.relative_to(SOURCE).as_posix() for p in (SOURCE / 'storage').rglob('.gitignore'))
    assert len(names) == len(set(names))
    DEST.mkdir(parents=True, exist_ok=True)
    files = []
    with zipfile.ZipFile(DEST / 'project.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(names):
            data = (SOURCE / name).read_bytes()
            entry = zipfile.ZipInfo(PREFIX + name, (2026, 1, 1, 0, 0, 0))
            entry.create_system = 0
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
            files.append(dict(path=name, bytes=len(data), sha256=sha256(data).hexdigest()))
    archive = (DEST / 'project.zip').read_bytes()
    lock = json.loads((SOURCE / 'composer.lock').read_text(encoding='utf-8'))
    laravel = next(p['version'] for p in lock['packages'] if p['name'] == 'laravel/framework')
    manifest = dict(schema='fullbleed.laravel-starter.v1', prefix=PREFIX, engine='2.5.21', laravel=laravel,
                    files=files, zip_bytes=len(archive), zip_sha256=sha256(archive).hexdigest())
    (DEST / 'source.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: manifest[k] for k in ['laravel', 'zip_bytes', 'zip_sha256']}))


if __name__ == '__main__':
    main()
