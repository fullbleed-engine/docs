#!/usr/bin/env python3
"""Publish sample assets from a successfully executed component notebook."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--verification-dir", required=True, type=Path)
args = parser.parse_args()
checked = args.verification_dir.resolve()
report = json.loads((checked / "verification.json").read_text(encoding="utf-8"))
source = ROOT / "examples/component-notebook/bootstrap_components.ipynb"
assert report["ok"] and report["runtime_version"] == "2.6.0a3"
assert report["notebook_sha256"] == sha256(source.read_bytes()).hexdigest()
assert [r["name"] for r in report["cases"]] == ["default", "edited", "long", "empty-after-long"]
assert report["stale_pages_excluded_from_download"]
assets = ROOT / "docs/assets/component-notebook"
assets.mkdir(parents=True, exist_ok=True)
for name in ("order.pdf", "order.styled.html", "order.unstyled.html"):
    data = (checked / "default" / name).read_bytes()
    assert sha256(data).hexdigest() == report["cases"][0]["artifact_hashes"][name]
    (assets / name).write_bytes(data)
shutil.copyfile(checked / "default/pdfium-page-1.png", assets / "order-page-1.png")
shutil.copyfile(source, assets / "bootstrap_components.ipynb")
manifest = {
    "runtime_version": report["runtime_version"],
    "notebook_sha256": report["notebook_sha256"],
    "cases": [{k: row[k] for k in ("name", "pages", "row_count", "total", "pdf_sha256", "accent")}
              for row in report["cases"]],
    "downloads": {name: sha256((assets / name).read_bytes()).hexdigest() for name in
                  ("bootstrap_components.ipynb", "order.pdf", "order-page-1.png", "order.styled.html", "order.unstyled.html")},
    "preview": "PDFium rendering of the default output PDF at 110 DPI",
    "checks": ["Notebook installation and execution", "Independent PDF text and page bounds",
               "Requested PDF accent colours", "Repeat/direct PDF byte equality",
               "Static styled and unstyled HTML", "Exact ZIP contents", "Long-to-empty rerun excludes old pages"],
    "scope": report["scope"],
}
(assets / "verification.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"ok": True, "downloads": len(manifest["downloads"]), "cases": len(manifest["cases"])}))
