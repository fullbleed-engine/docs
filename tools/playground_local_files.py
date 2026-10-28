"""Create a local-file specimen using an existing licensed font and synthetic images."""
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def fixture(folder):
    folder.mkdir(parents=True, exist_ok=False)
    assets = folder / 'assets'
    assets.mkdir()
    Image.new('RGB', (32, 24), (17, 153, 136)).save(assets / 'café mark.png')
    Image.new('RGB', (32, 24), (222, 144, 22)).save(assets / 'photo #1%.jpg', quality=100, subsampling=0)
    (assets / 'brand.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="80" height="48"><rect width="80" height="48" fill="#3559bb"/></svg>', encoding='utf-8')
    shutil.copyfile(ROOT / 'examples/markdown/fonts/IBMPlexMono-Regular.ttf', assets / 'Brand Mono.ttf')
    shutil.copyfile(ROOT / 'examples/markdown/fonts/OFL.txt', assets / 'OFL.txt')
    html = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Local files</title></head><body>
<p class="eyebrow">LOCAL FILES / 01</p><h1>Your document.<br>Your brand.</h1>
<p class="marker">LOCAL IMPORT CAFÉ 012345</p>
<div class="art"><img src="assets/café mark.png" alt="Teal PNG"><img src="assets/photo #1%.jpg" alt="Ochre JPEG"><img src="assets/brand.svg" alt="Blue SVG"></div>
<p class="note">Images, fonts and source stay together.</p>
<script>window.__localDocumentExecuted = true;</script>
</body></html>'''
    css = '''@page { size: 400px 420px; margin: 0; }
@font-face { font-family: Brand; src: url('assets/Brand Mono.ttf'); }
body { margin: 30px; color: #142c34; font-family: Brand; font-size: 13px; }
.eyebrow { color: #3559bb; font-size: 11px; margin: 0 0 18px; }
h1 { font-size: 30px; font-weight: 400; line-height: 1.2; margin: 0 0 20px; }
.marker { font-family: 'IBM Plex Mono'; margin: 0 0 24px; }
.art { display: flex; gap: 12px; }
.art img { width: 80px; height: 48px; }
.note { margin-top: 22px; font-size: 11px; }
'''
    (folder / 'document.html').write_text(html, encoding='utf-8')
    (folder / 'brand.css').write_text(css, encoding='utf-8')
    record = dict(html=html, css=css, assets=[dict(name=p.name, bytes=p.stat().st_size,
        sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(assets.iterdir())])
    (folder / 'fixture.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return record
