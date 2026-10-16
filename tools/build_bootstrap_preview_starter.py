"""Build the static Bootstrap preview download from pinned source and wheels."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from build_component_preview_starter import build_installer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/bootstrap-preview"
DEST = ROOT / "docs/assets/bootstrap-preview"
FILES = ["README.md", "LICENSE", "requirements-preview.txt", "requirements-source.txt",
         "wheels.html", "first_document.py", "upstream.json",
         "examples/component_bootstrap/main.py", "examples/component_bootstrap/catalog.py"]


def build():
    upstream = json.loads((SOURCE / "upstream.json").read_text(encoding="utf-8"))
    for name, digest in upstream["source_files"].items():
        assert sha256((SOURCE / name).read_bytes()).hexdigest() == digest, name
    for name, record in upstream.get("adapted_files", {}).items():
        assert sha256((SOURCE / name).read_bytes()).hexdigest() == record["sha256"], name
    first = (SOURCE / "first_document.py").read_bytes()
    assert sha256(first).hexdigest() == upstream["first_document_sha256"]
    source_requirement = f"fullbleed @ {upstream['repository']}/archive/{upstream['commit']}.tar.gz"
    assert source_requirement in (SOURCE / "requirements-source.txt").read_text(encoding="utf-8").splitlines()
    build_installer(upstream, source=SOURCE)
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "project.zip"
    records = []
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            data = (SOURCE / name).read_bytes()
            info = zipfile.ZipInfo("fullbleed-bootstrap-preview/" + name, date_time=(2026, 10, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
            records.append({"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    report = {"schema": "fullbleed.bootstrap-preview-source.v1", "experimental": True,
              "source_commit": upstream["commit"], "contains_engine_binaries": False,
              "engine_installation": "prebuilt-wheel", "native_build_required": False,
              "native_build_scope": "Listed compatible wheels; the explicit source fallback requires Rust and native build tools.",
              "source_engine_requirement": source_requirement, "engine_wheels": upstream["engine_wheels"],
              "engine_python_files": upstream["engine_python_files"],
              "adapted_example_files": upstream.get("adapted_files", {}),
              "bootstrap_css_sha256": upstream["bootstrap_css_sha256"],
              "first_document_sha256": upstream["first_document_sha256"],
              "files": records, "zip_sha256": sha256(target.read_bytes()).hexdigest(), "zip_bytes": target.stat().st_size}
    (DEST / "source.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "files": len(records), "zip_sha256": report["zip_sha256"]}))
    return report


if __name__ == "__main__":
    build()
