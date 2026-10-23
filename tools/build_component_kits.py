"""Package the exact, text-normalized component kit example reproducibly."""
from hashlib import sha256
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/component-kits"
DEST = ROOT / "docs/assets/component-kits"
FILES = ("README.md", "LICENSE", "requirements.txt", "requirements-check.txt",
         "billing.py", "impact.py", "report.py")


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    path = DEST / "project.zip"
    records = []
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            data = (SOURCE / name).read_text(encoding="utf-8").encode("utf-8")
            entry = zipfile.ZipInfo("fullbleed-component-kits/" + name, (2026, 10, 23, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data, compresslevel=9)
            records.append({"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    result = {"schema": "fullbleed.component-kits.v1", "fullbleed": "2.6.0a14",
              "files": records, "zip_sha256": sha256(path.read_bytes()).hexdigest()}
    (DEST / "source.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "files": len(records), "zip_sha256": result["zip_sha256"]}))
    return result


if __name__ == "__main__":
    build()
