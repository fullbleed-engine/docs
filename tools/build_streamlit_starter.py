"""Package the Streamlit app, template, sample data and licensed font reproducibly."""
from hashlib import sha256
from pathlib import Path
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/streamlit-report"
DEST = ROOT / "docs/assets/streamlit-report"
FILES = ["README.md", "LICENSE", "requirements.txt", ".streamlit/config.toml", "app.py",
         "report.py", "report.html", "report.css", "sales.csv",
         "fonts/DMSerifDisplay-Regular.ttf", "fonts/DMSerifDisplay-OFL.txt"]


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST / "project.zip"
    manifest = []
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in FILES:
            data = (SOURCE / name).read_bytes()
            info = zipfile.ZipInfo("fullbleed-streamlit-report/" + name, date_time=(2026, 10, 14, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
            manifest.append({"path": name, "bytes": len(data), "sha256": sha256(data).hexdigest()})
    record = {"schema": "fullbleed.streamlit-starter.v1", "fullbleed": "2.5.23", "streamlit": "1.65.0", "streamlit_pdf": "2.1.0",
              "files": manifest, "zip_bytes": target.stat().st_size, "zip_sha256": sha256(target.read_bytes()).hexdigest()}
    (DEST / "source.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"files": len(FILES), "zip_bytes": record["zip_bytes"], "zip_sha256": record["zip_sha256"]}))


if __name__ == "__main__":
    build()
