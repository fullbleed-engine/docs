"""Build the custom-paper example download from its maintained sources."""
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'examples/print-sizes'
ASSETS = ROOT / 'docs/assets/print-sizes'
NAMES = ('LICENSE', 'README.md', 'render.py', 'requirements.txt', 'shelf-card.html')
assert version('fullbleed') == '2.5.46'
ASSETS.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, '-I', str(PROJECT / 'render.py')], check=True, cwd=ROOT)
sources = {}
with zipfile.ZipFile(ASSETS / 'project.zip', 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
    for name in NAMES:
        data = (PROJECT / name).read_text(encoding='utf-8').encode('utf-8')
        info = zipfile.ZipInfo('fullbleed-print-sizes/' + name, (2026, 10, 30, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.create_system = 3
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data, compresslevel=9)
        sources[name] = sha256(data).hexdigest()
for name in ('metric-card', 'inch-card'):
    shutil.copyfile(PROJECT / 'output' / (name + '.pdf'), ASSETS / (name + '.pdf'))
    shutil.copyfile(PROJECT / 'output' / name / (name + '_page1.png'), ASSETS / (name + '.png'))
assets = {name: {'sha256':sha256((ASSETS / name).read_bytes()).hexdigest(), 'bytes':(ASSETS / name).stat().st_size}
          for name in ('inch-card.pdf', 'inch-card.png', 'metric-card.pdf', 'metric-card.png', 'project.zip')}
(ASSETS / 'project.json').write_text(json.dumps({
    'version':'2.5.46', 'sources':sources, 'assets':assets,
    'scope':'Source and asset integrity; rendered-output checks are recorded separately.'
}, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({'version':'2.5.46', 'sources':len(sources), 'assets':len(assets)}))
