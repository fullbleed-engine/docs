"""Check the focused React recipe's published download bytes and source manifest."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

root = Path(__file__).resolve().parents[1] / 'docs/assets/react-preview-recipe'
digest = lambda data: hashlib.sha256(data).hexdigest()
source = json.loads((root / 'source.json').read_text(encoding='utf-8'))
report = json.loads((root / 'verification.json').read_text(encoding='utf-8'))
for name, expected in source['public_files'].items():
    assert Path(name).name == name, f'Unexpected asset path: {name}'
    assert digest((root / name).read_bytes()) == expected, f'Asset hash differs: {name}'
archive_bytes = (root / 'project.zip').read_bytes()
assert len(archive_bytes) == source['zip_bytes']
assert digest(archive_bytes) == source['zip_sha256'] == report['source_project_sha256']
with zipfile.ZipFile(root / 'project.zip') as archive:
    names = archive.namelist()
    assert len(names) == len(set(names)) == len(source['files'])
    assert set(names) == set(source['files'])
    for name in names:
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name
        assert path.parts[0] == 'fullbleed-react-starter'
        assert digest(archive.read(name)) == source['files'][name], f'ZIP source hash differs: {name}'
    assert archive.read('fullbleed-react-starter/src/App.tsx') == (root / 'App.tsx').read_bytes()
    package = json.loads(archive.read('fullbleed-react-starter/package.json'))
    lock = json.loads(archive.read('fullbleed-react-starter/package-lock.json'))
    assert package['dependencies']['fullbleed'] == source['package_version']
    assert package['dependencies']['react'] == source['react_version']
    assert lock['packages']['node_modules/fullbleed']['integrity'] == source['package_integrity']
assert digest((root / 'App.tsx').read_bytes()) == report['source_sha256']
default = next(document for document in report['documents'] if document['name'] == 'default')
assert digest((root / 'invoice.pdf').read_bytes()) == default['sha256']
assert report['runtime_manifest']['engineVersion'] == source['engine_version']
print(json.dumps({'ok': True, 'source_files': len(source['files']),
                  'public_files': len(source['public_files']), 'zip_sha256': source['zip_sha256']}))
