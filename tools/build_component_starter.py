"""Build a reproducible component-authoring source download."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/components"
DEST = ROOT / "docs/assets/components"
FILES = ["README.md", "LICENSE", "requirements.txt", "invoice.py", "styles.py", "data.json", "upstream.json"]


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "project.zip"
    records = []
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            data = (SOURCE / name).read_bytes()
            info = zipfile.ZipInfo("fullbleed-components/" + name, date_time=(2026, 10, 15, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
            records.append({"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    report = {"schema": "fullbleed.component-starter.v1", "fullbleed": "2.5.25", "files": records,
              "zip_sha256": sha256(target.read_bytes()).hexdigest(), "zip_bytes": target.stat().st_size}
    (DEST / "source.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "files": len(records), "zip_sha256": report["zip_sha256"]}))
    return report


if __name__ == "__main__":
    build()
