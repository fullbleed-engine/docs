"""Verify the delivered ZIP as a consumer, including the published PDF bytes."""
from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/pandas-components"


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    source = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
    assert sha256((ASSETS / "project.zip").read_bytes()).hexdigest() == source["zip_sha256"]
    with ZipFile(ASSETS / "project.zip") as archive:
        assert set(archive.namelist()) == {"fullbleed-pandas-components/" + name for name in source["files"]}
        archive.extractall(out)
    project = out / "fullbleed-pandas-components"
    for name, digest in source["files"].items():
        assert sha256((project / name).read_bytes()).hexdigest() == digest
    result = subprocess.run([sys.executable, str(project / "verify.py"), "--out", str(out / "checks")],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    record = json.loads(result.stdout)
    assert record["ok"]
    assert (out / "checks/sample/report.pdf").read_bytes() == (ASSETS / "report.pdf").read_bytes(), "Published PDF differs from source kit"
    record.update(source_zip_sha256=source["zip_sha256"], published_pdf_identical=True)
    (out / "verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "target/pandas-components")
    main(parser.parse_args().out.resolve())
