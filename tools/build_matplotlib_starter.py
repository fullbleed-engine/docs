"""Package the exact chart-report source as a stable standalone download."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/matplotlib-report"
DEST = ROOT / "docs/assets/matplotlib-report"
FILES = ["README.md", "LICENSE", "requirements.txt", "report.py", "report.css", "data.json"]


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "project.zip"
    manifest = []
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            data = (SOURCE / name).read_bytes()
            info = zipfile.ZipInfo("matplotlib-report/" + name, date_time=(2026, 10, 7, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
            manifest.append({"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    result = {"schema": "fullbleed.matplotlib-starter.v1", "fullbleed": "2.5.14", "matplotlib": "3.11.2",
              "files": manifest, "zip_bytes": target.stat().st_size, "zip_sha256": sha256(target.read_bytes()).hexdigest()}
    (DEST / "source.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"zip_bytes": result["zip_bytes"], "zip_sha256": result["zip_sha256"], "files": len(FILES)}))
    return result


if __name__ == "__main__":
    build()
