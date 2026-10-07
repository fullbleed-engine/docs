"""Install and exercise the exact downloadable Python web starter in isolation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/python-web"
OUT = ROOT / "output/python-web-verification"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", action="store_true", help="Also build and exercise the image from the extracted ZIP.")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=False)
    source = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
    assert source["engineVersion"] == "2.5.11"
    for item in source["assets"]:
        data = (ASSETS / item["file"]).read_bytes()
        assert len(data) == item["bytes"]
        assert hashlib.sha256(data).hexdigest() == item["sha256"], item["file"]
    unpacked = OUT / "project with spaces"
    with zipfile.ZipFile(ASSETS / "project.zip") as zipped:
        assert zipped.testzip() is None
        for item in zipped.infolist():
            assert (unpacked / item.filename).resolve().is_relative_to(unpacked.resolve())
        zipped.extractall(unpacked)
    project = unpacked / "fullbleed-python-invoice"
    manifest = json.loads((project / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["sourceCommit"] == source["sourceCommit"]
    assert manifest["files"] == source["files"]
    assert {"Dockerfile", ".dockerignore", "requirements-docker.txt", "check_docker.py", "LICENSE"} <= {item["path"] for item in manifest["files"]}
    for item in manifest["files"]:
        data = (project / item["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item["sha256"], item["path"]
    venv = OUT / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    commands = [
        ("install", [str(python), "-m", "pip", "install", "--disable-pip-version-check",
                     "--only-binary=:all:", "fullbleed==2.5.11", "-r", "requirements-check.txt"]),
        ("verify", [str(python), "check_examples.py", "--out", str(OUT / "checks")]),
    ]
    for name, command in commands:
        with (OUT / (name + ".log")).open("w", encoding="utf-8") as log:
            result = subprocess.run(command, cwd=project, stdout=log, stderr=subprocess.STDOUT, timeout=240)
        if result.returncode:
            raise RuntimeError(f"{name} failed; inspect {OUT / (name + '.log')}")
    for framework in ["fastapi", "flask", "django"]:
        for suffix in ["", "-http"]:
            assert (OUT / "checks" / f"{framework}{suffix}.pdf").read_bytes() == (ASSETS / "invoice.pdf").read_bytes()
    assert (OUT / "checks/preview/invoice_page1.png").read_bytes() == (ASSETS / "invoice.png").read_bytes()
    if args.docker:
        with (OUT / "docker.log").open("w", encoding="utf-8") as log:
            result = subprocess.run([str(python), "check_docker.py", "--out", str(OUT / "docker")],
                                    cwd=project, stdout=log, stderr=subprocess.STDOUT, timeout=900)
        if result.returncode:
            raise RuntimeError(f"Docker verification failed; inspect {OUT / 'docker.log'}")
        for filename in ["invoice.pdf", "invoice.png"]:
            assert (OUT / "docker" / filename).read_bytes() == (ASSETS / filename).read_bytes()
    report = {"ok": True, "checkedAt": datetime.now(timezone.utc).isoformat(),
              "sourceCommit": source["sourceCommit"], "engineVersion": "2.5.11",
              "manifestFilesVerified": len(manifest["files"]),
              "frameworkClientsPassed": 3, "actualHttpServersPassed": 3,
              "pdfAndPreviewMatchPublishedAssets": True,
              "dockerFromExactZipPassed": args.docker,
              "scope": "Isolated ZIP install and local HTTP verification; no production deployment claim."}
    (OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__": main()
