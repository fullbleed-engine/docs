"""Build the reproducible experimental project and its pinned wheel installer."""
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/component-preview"
DEST = ROOT / "docs/assets/component-preview"
FILES = ["README.md", "LICENSE", "requirements-preview.txt", "requirements-source.txt", "wheels.html",
         "first_pdf.py", "edit_tasks.py", "upstream.json",
         "examples/component_recipes/kit.py", "examples/component_recipes/documents.py",
         "examples/component_recipes/main.py", "examples/components/data.json"]

def build_installer(upstream, source=SOURCE):
    engine = upstream["engine_wheels"]
    wheels = engine["files"]
    assert len(wheels) == len({wheel["file"] for wheel in wheels}) == 15
    requirements = [
        "# Experimental snapshot; use an isolated environment and --force-reinstall.",
        "# The URLs and hashes identify this preview; package metadata alone does not.",
        "--no-index", "--only-binary=:all:", "--require-hashes", "--find-links wheels.html", "",
        f"fullbleed=={engine['package_version']} \\",
    ]
    links = []
    for index, wheel in enumerate(wheels):
        assert wheel["kind"] == "wheel"
        assert wheel["file"].startswith(f"fullbleed-{engine['package_version']}-cp310-abi3-")
        assert wheel["url"] == f"{upstream['repository']}/releases/download/{engine['release_tag']}/{wheel['file']}"
        digest = wheel["sha256"]
        assert len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)
        requirements.append(f"    --hash=sha256:{digest}" + (" \\" if index < len(wheels) - 1 else ""))
        links.append(f'<li><a href="{escape(wheel["url"] + "#sha256=" + digest, quote=True)}">{escape(wheel["file"])}</a></li>')
    (source / "requirements-preview.txt").write_bytes(("\n".join(requirements) + "\n").encode("utf-8"))
    html = (
        '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<title>Fullbleed experimental wheels</title></head><body>\n'
        f'<h1>Component preview {upstream["commit"][:7]}</h1>\n'
        '<p>Exact experimental distributions. These differ from the stable PyPI package.</p>\n<ul>\n'
        + "\n".join(links) + "\n</ul></body></html>\n"
    )
    (source / "wheels.html").write_bytes(html.encode("utf-8"))


def build():
    upstream = json.loads((SOURCE / "upstream.json").read_text(encoding="utf-8"))
    for name, digest in upstream["source_files"].items():
        assert sha256((SOURCE / name).read_bytes()).hexdigest() == digest, name
    assert sha256((SOURCE / "first_pdf.py").read_bytes()).hexdigest() == upstream["first_pdf_sha256"]
    source_requirement = f"fullbleed @ {upstream['repository']}/archive/{upstream['commit']}.tar.gz"
    assert source_requirement in (SOURCE / "requirements-source.txt").read_text(encoding="utf-8").splitlines()
    build_installer(upstream)
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
              "contains_engine_binaries": False, "engine_installation": "prebuilt-wheel",
              "engine_requirement": f"fullbleed=={upstream['engine_wheels']['package_version']}",
              "source_engine_requirement": source_requirement, "native_build_required": False,
              "native_build_scope": "Listed compatible wheels; the explicit source fallback requires Rust and native build tools.",
              "engine_wheels": upstream["engine_wheels"],
              "engine_python_files": upstream["engine_python_files"],
              "first_pdf_sha256": upstream["first_pdf_sha256"],
              "files": records, "zip_sha256": sha256(target.read_bytes()).hexdigest(), "zip_bytes": target.stat().st_size}
    (DEST / "source.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "files": len(records), "zip_sha256": report["zip_sha256"]}))
    return report


if __name__ == "__main__":
    build()
