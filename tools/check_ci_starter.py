"""Verify the published starter ZIP and run its six real render scenarios."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile


def check_bytes(raw, expected, label):
    if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
        raise ValueError(f"Download does not match its manifest: {label}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--out", type=Path, default=Path("output/pdf-regression-verification"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    assets = args.assets or root / "docs/assets/pdf-regression"
    manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
    if manifest["schema"] != "fullbleed.ci_starter_download.v1":
        raise ValueError("Unsupported starter manifest")
    for name, expected in manifest["downloads"].items():
        check_bytes((assets / name).read_bytes(), expected, name)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix="download with spaces ", dir=out))
    prefix = manifest["zip_root"] + "/"
    expected_names = {prefix + name for name in manifest["project_files"]}
    for name in expected_names:
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or "\\" in name:
            raise ValueError(f"Invalid archive member: {name}")
    with zipfile.ZipFile(assets / "project.zip") as archive:
        if len(archive.namelist()) != len(expected_names) or set(archive.namelist()) != expected_names:
            raise ValueError("Starter ZIP has missing, extra, or duplicate files")
        if archive.testzip() is not None:
            raise ValueError("Starter ZIP failed its CRC check")
        for name, expected in manifest["project_files"].items():
            check_bytes(archive.read(prefix + name), expected, name)
        archive.extractall(workspace)
    project = workspace / manifest["zip_root"]
    check_bytes((assets / "invoice.pdf").read_bytes(), manifest["project_files"]["baseline.pdf"], "baseline preview PDF")
    command = [args.python, "-I", str(project / "verify.py"), "--out", str(out / "rendered")]
    result = subprocess.run(command, cwd=workspace, capture_output=True, text=True, encoding="utf-8", timeout=300)
    (out / "stdout.log").write_text(result.stdout, encoding="utf-8")
    (out / "stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode:
        raise SystemExit(f"Starter verification failed ({result.returncode}); see {out}")
    rendered = json.loads((out / "rendered/verification.json").read_text(encoding="utf-8"))
    if not rendered["ok"] or rendered["engine"] != manifest["engine"] or len(rendered["cases"]) != 6:
        raise ValueError("Incomplete or mismatched starter verification")
    for case, name in [("unchanged-relocated", "invoice"), ("changed-style", "changed-invoice")]:
        case_dir = out / "rendered" / case
        check_bytes((case_dir / "invoice.pdf").read_bytes(), manifest["downloads"][name + ".pdf"], name + " PDF")
        check_bytes((case_dir / "preview/invoice_page1.png").read_bytes(), manifest["downloads"][name + "-1.png"], name + " preview")
    report = {"ok": True, "source_commit": manifest["source_commit"],
              "archive_files": len(expected_names), "downloads_verified": len(manifest["downloads"]),
              "rendered": rendered}
    (out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
