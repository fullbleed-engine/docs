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
parser.add_argument("--browser-verification-dir", type=Path, help="Optional actual Jupyter browser check for this exact notebook")
parser.add_argument("--channel", choices=("alpha3", "alpha5", "alpha6", "alpha6-r1"), default="alpha3")
args = parser.parse_args()
checked = args.verification_dir.resolve()
report = json.loads((checked / "verification.json").read_text(encoding="utf-8"))
folder = "component-notebook" if args.channel == "alpha3" else f"component-notebook-{args.channel}"
runtime_version = {"alpha3": "2.6.0a3", "alpha5": "2.6.0a5", "alpha6": "2.6.0a6", "alpha6-r1": "2.6.0a6"}[args.channel]
source = ROOT / "examples" / folder / "bootstrap_components.ipynb"
assert report["ok"] and report["runtime_version"] == runtime_version
assert report["notebook_sha256"] == sha256(source.read_bytes()).hexdigest()
assert [r["name"] for r in report["cases"]] == ["default", "edited", "long", "empty-after-long"]
assert report["stale_pages_excluded_from_download"]
assets = ROOT / "docs/assets" / folder
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
if all(row.get("rich_cell_components_checked") for row in report["cases"]):
    for row in manifest["cases"]:
        row["rich_cell_components_checked"] = True
    manifest["checks"].insert(5, "Rich item cell emphasis, order and escaped text in both HTML exports")
if args.browser_verification_dir:
    browser_path = args.browser_verification_dir / "verification.json"
    browser = json.loads(browser_path.read_text(encoding="utf-8"))
    assert browser["ok"] and browser["notebook_sha256"] == report["notebook_sha256"]
    assert browser["runtime_version"] == report["runtime_version"]
    assert [r["name"] for r in browser["cases"]] == [r["name"] for r in report["cases"]]
    for actual, expected in zip(browser["cases"], report["cases"]):
        assert actual["actual_browser_download"] and actual["visible_previews_match_download"]
        assert actual["filename"] == "component-order.zip"
        assert actual["artifact_hashes"] == expected["artifact_hashes"]
    assert browser["stale_previews_excluded"]
    shutil.copyfile(browser_path, assets / "browser-verification.json")
    manifest["browser_verification"] = {"file": "browser-verification.json",
        "sha256": sha256(browser_path.read_bytes()).hexdigest(), "system": browser["system"],
        "scope": browser["scope"]}
(assets / "verification.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"ok": True, "downloads": len(manifest["downloads"]), "cases": len(manifest["cases"])}))
