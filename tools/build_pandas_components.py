"""Build the small deterministic source kit; never replace rendered evidence."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples/pandas-components"
ASSETS = ROOT / "docs/assets/pandas-components"
FILES = ("LICENSE", "Inter-OFL.txt", "README.md", "components.py", "data.py", "products.csv", "report.py",
         "requirements.txt", "requirements-check.txt", "verify.py")


def main():
    contents = {name: (PROJECT / name).read_bytes() for name in sorted(FILES)}
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_STORED) as archive:
        for name, data in contents.items():
            entry = ZipInfo("fullbleed-pandas-components/" + name, (2026, 10, 20, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    package = buffer.getvalue()
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "project.zip").write_bytes(package)
    source = {"schema": "fullbleed.pandas_components_source.v1", "fullbleed": "2.6.0a9", "pandas": "3.0.6",
              "zip_sha256": sha256(package).hexdigest(), "zip_bytes": len(package),
              "files": {name: sha256(data).hexdigest() for name, data in contents.items()}}
    (ASSETS / "source.json").write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "files": len(contents), "zip_sha256": source["zip_sha256"]}))


if __name__ == "__main__":
    main()
