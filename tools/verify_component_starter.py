"""Run the actual downloadable project using the caller's installed Fullbleed."""
import argparse
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/components"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "target/component-starter")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
    assert version("fullbleed") == manifest["fullbleed"]
    archive_path = ASSETS / "project.zip"
    assert sha256(archive_path.read_bytes()).hexdigest() == manifest["zip_sha256"]
    with tempfile.TemporaryDirectory(prefix="component-source-", dir=args.out) as folder:
        project = Path(folder).resolve()
        with zipfile.ZipFile(archive_path) as archive:
            assert set(archive.namelist()) == {"fullbleed-components/" + record["path"] for record in manifest["files"]}
            for record in manifest["files"]:
                name = record["path"]
                assert Path(name).name == name
                data = archive.read("fullbleed-components/" + name)
                assert sha256(data).hexdigest() == record["sha256"]
                (project / name).write_bytes(data)
        result = subprocess.run([sys.executable, str(project / "invoice.py"), "--output", str(args.out.resolve() / "render")],
                                cwd=project, capture_output=True, text=True, encoding="utf-8")
        (args.out / "render.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        assert result.returncode == 0, result.stdout + result.stderr
    for output, published in [("invoice.pdf", "invoice.pdf"), ("page-1.png", "page-1.png")]:
        assert (args.out / "render" / output).read_bytes() == (ASSETS / published).read_bytes(), output
    rendered = json.loads((args.out / "render/verification.json").read_text(encoding="utf-8"))
    assert rendered["ok"] and rendered["pages"] == 1 and rendered["repeated_pdf_equal"]
    report = {"ok": True, "fullbleed": version("fullbleed"), "files": len(manifest["files"]),
              "zip_sha256": manifest["zip_sha256"], "rendered": rendered, "published_pdf_png_equal": True}
    (args.out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
