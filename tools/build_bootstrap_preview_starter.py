"""Build the static Bootstrap download, retaining the pinned preview unchanged."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from build_component_preview_starter import build_installer

ROOT = Path(__file__).resolve().parents[1]
FILES = ["README.md", "LICENSE", "requirements-preview.txt", "requirements-source.txt",
         "wheels.html", "first_document.py", "upstream.json",
         "examples/component_bootstrap/main.py", "examples/component_bootstrap/catalog.py"]


def build(channel="preview"):
    source = ROOT / f"examples/bootstrap-{channel}"
    dest = ROOT / f"docs/assets/bootstrap-{channel}"
    files = FILES if channel == "preview" else [
        "README.md", "LICENSE", "requirements.txt", "first_document.py", "upstream.json",
        "examples/component_bootstrap/main.py", "examples/component_bootstrap/catalog.py",
    ]
    upstream = json.loads((source / "upstream.json").read_text(encoding="utf-8"))
    for name, digest in upstream["source_files"].items():
        assert sha256((source / name).read_bytes()).hexdigest() == digest, name
    for name, record in upstream.get("adapted_files", {}).items():
        assert sha256((source / name).read_bytes()).hexdigest() == record["sha256"], name
    first = (source / "first_document.py").read_bytes()
    assert sha256(first).hexdigest() == upstream["first_document_sha256"]
    if channel == "preview":
        source_requirement = f"fullbleed @ {upstream['repository']}/archive/{upstream['commit']}.tar.gz"
        assert source_requirement in (source / "requirements-source.txt").read_text(encoding="utf-8").splitlines()
        build_installer(upstream, source=source)
    else:
        source_requirement = f"fullbleed=={upstream['engine_wheels']['package_version']}"
        assert (source / "requirements.txt").read_text(encoding="utf-8").strip() == source_requirement
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / "project.zip"
    records = []
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in files:
            data = (source / name).read_bytes()
            info = zipfile.ZipInfo(f"fullbleed-bootstrap-{channel}/" + name, date_time=(2026, 10, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
            records.append({"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    report = {"schema": f"fullbleed.bootstrap-{channel}-source.v1", "experimental": True,
              "source_commit": upstream["commit"], "contains_engine_binaries": False,
              "engine_installation": "prebuilt-wheel" if channel == "preview" else "pypi", "native_build_required": False,
              "native_build_scope": "Listed compatible wheels; the explicit source fallback requires Rust and native build tools." if channel == "preview" else "Compatible wheels need no Rust build; other platforms may build the PyPI sdist with Rust and native build tools.",
              "source_engine_requirement": source_requirement, "engine_wheels": upstream["engine_wheels"],
              "engine_python_files": upstream["engine_python_files"],
              "adapted_example_files": upstream.get("adapted_files", {}),
              "bootstrap_css_sha256": upstream["bootstrap_css_sha256"],
              "first_document_sha256": upstream["first_document_sha256"],
              "files": records, "zip_sha256": sha256(target.read_bytes()).hexdigest(), "zip_bytes": target.stat().st_size}
    (dest / "source.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "files": len(records), "zip_sha256": report["zip_sha256"]}))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", choices=("preview", "alpha", "alpha2", "alpha3"), default="preview")
    build(parser.parse_args().channel)
