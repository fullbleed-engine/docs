"""Bundle the checked Node invoice project reproducibly."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/node"
OUTPUT = ROOT / "docs/assets/node"
NAMES = ["LICENSE", "README.md", "invoice.css", "invoice.html", "package-lock.json", "package.json", "render.mjs"]
record = json.loads((SOURCE / "source.json").read_text(encoding="utf8"))
files = {}
OUTPUT.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(OUTPUT / "project.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for name in NAMES:
        data = (SOURCE / name).read_bytes()
        files[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        info = zipfile.ZipInfo(name, (2026, 10, 2, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, data)
record["files"] = files
record["zip_sha256"] = hashlib.sha256((OUTPUT / "project.zip").read_bytes()).hexdigest()
(OUTPUT / "project.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf8", newline="\n")
print(json.dumps({"ok": True, "files": len(files), "zip_sha256": record["zip_sha256"]}))
