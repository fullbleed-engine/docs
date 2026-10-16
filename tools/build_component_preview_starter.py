"""Build the reproducible, source-only experimental component project."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/component-preview"
DEST = ROOT / "docs/assets/component-preview"
FILES = ["README.md", "LICENSE", "requirements-preview.txt", "first_pdf.py", "edit_tasks.py", "upstream.json",
         "examples/component_recipes/kit.py", "examples/component_recipes/documents.py",
         "examples/component_recipes/main.py", "examples/components/data.json"]


def build():
    upstream = json.loads((SOURCE / "upstream.json").read_text(encoding="utf-8"))
    for name, digest in upstream["source_files"].items():
        assert sha256((SOURCE / name).read_bytes()).hexdigest() == digest, name
    assert sha256((SOURCE / "first_pdf.py").read_bytes()).hexdigest() == upstream["first_pdf_sha256"]
    requirement = f"fullbleed @ {upstream['repository']}/archive/{upstream['commit']}.tar.gz"
    assert requirement in (SOURCE / "requirements-preview.txt").read_text(encoding="utf-8").splitlines()
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "project.zip"
    records = []
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            data = (SOURCE / name).read_bytes()
            info = zipfile.ZipInfo("fullbleed-component-preview/" + name, date_time=(2026, 10, 16, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
            records.append({"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    report = {"schema": "fullbleed.component-preview-source.v1", "experimental": True,
              "source_commit": upstream["commit"], "source_only": True,
              "engine_requirement": requirement, "native_build_required": True,
              "engine_python_files": upstream["engine_python_files"],
              "first_pdf_sha256": upstream["first_pdf_sha256"],
              "files": records, "zip_sha256": sha256(target.read_bytes()).hexdigest(), "zip_bytes": target.stat().st_size}
    (DEST / "source.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "files": len(records), "zip_sha256": report["zip_sha256"]}))
    return report


if __name__ == "__main__":
    build()
