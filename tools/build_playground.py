"""Build the optional static playground from a locked published Fullbleed crate."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / 'playground/engine'
ASSETS = ROOT / 'docs/assets/playground'

def run(args, cwd):
    subprocess.run(args, cwd=cwd, check=True)

run(['cargo', 'build', '--release', '--locked', '--target', 'wasm32-wasip1'], ENGINE)
run(['npm.cmd' if os.name == 'nt' else 'npm', 'ci', '--ignore-scripts', '--no-audit', '--no-fund'], ROOT / 'playground')
shutil.copyfile(ENGINE / 'target/wasm32-wasip1/release/fullbleed-playground.wasm', ASSETS / 'fullbleed.wasm')
shim = ROOT / 'playground/node_modules/@bjorn3/browser_wasi_shim'
(ASSETS / 'wasi').mkdir(exist_ok=True)
for path in (shim / 'dist').glob('*.js'):
    shutil.copyfile(path, ASSETS / 'wasi' / path.name)
metadata = json.loads(subprocess.check_output(['cargo', 'metadata', '--format-version', '1', '--locked'], cwd=ENGINE, text=True, encoding='utf-8'))
license_parts = []
for package in metadata['packages']:
    if package['source'] is None:
        continue
    folder = Path(package['manifest_path']).parent
    license_file = folder / 'LICENSE-MIT'
    if not license_file.exists():
        license_file = folder / 'LICENSE'
    if not license_file.exists():
        raise SystemExit(f"Missing bundled license for {package['name']}")
    license_parts.append(f"{package['name']} {package['version']} — MIT\n\n" + license_file.read_text(encoding='utf-8'))
license_parts.append('browser_wasi_shim 0.4.2 — MIT\n\n' + (shim / 'LICENSE-MIT').read_text(encoding='utf-8'))
for path in sorted(ASSETS.glob('fonts/*-OFL.txt')):
    license_parts.append(path.name + '\n\n' + path.read_text(encoding='utf-8'))
(ASSETS / 'LICENSES.txt').write_text('\n\n'.join(license_parts), encoding='utf-8', newline='\n')
record = {
    'engine': {'name': 'fullbleed', 'version': '2.5.0', 'source': 'https://crates.io/crates/fullbleed/2.5.0', 'core_changes': False},
    'adapter': 'playground/engine',
    'target': 'wasm32-wasip1',
    'rustc': subprocess.check_output(['rustc', '--version'], text=True).strip(),
    'wasi_shim': {'name': '@bjorn3/browser_wasi_shim', 'version': '0.4.2'},
    'limits': {'source_bytes': 200000, 'pages': 6, 'wasm_memory_bytes': 268435456, 'render_seconds': 30},
    'artifacts': {},
}
for path in sorted([ASSETS / 'fullbleed.wasm', *ASSETS.glob('fonts/*.ttf')]):
    raw = path.read_bytes()
    record['artifacts'][path.relative_to(ASSETS).as_posix()] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
(ASSETS / 'build.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
print(f"Built playground: {record['artifacts']['fullbleed.wasm']['bytes']:,} bytes of WebAssembly")
