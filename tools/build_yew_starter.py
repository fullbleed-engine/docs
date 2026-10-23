"""Bundle the reviewed Yew example with exact font and source bytes."""
from hashlib import sha256
import json
from pathlib import Path
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples/yew-sheet"
DEST = ROOT / "docs/assets/yew-starter"
PREFIX = "fullbleed-yew-sheet/"
FILES = ("Cargo.toml", "Cargo.lock", "README.md", "LICENSE", "data.json", "style.css",
         "src/main.rs", "src/document.rs", "fonts/Inter-Variable.ttf", "fonts/Inter-OFL.txt",
         "fonts/DMSerifDisplay-Regular.ttf", "fonts/DMSerifDisplay-OFL.txt")


def build():
    DEST.mkdir(parents=True, exist_ok=True)
    files = []
    archive_path = DEST / "project.zip"
    # Stored entries avoid platform compression differences for this small source kit.
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for name in sorted(FILES):
            data = (PROJECT / name).read_bytes()
            entry = zipfile.ZipInfo(PREFIX + name, (2026, 10, 23, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
            files.append(dict(path=name, bytes=len(data), sha256=sha256(data).hexdigest()))
    cargo = tomllib.loads((PROJECT / "Cargo.toml").read_text(encoding="utf-8"))
    packages = {name: cargo["dependencies"][name]["version"].removeprefix("=")
                for name in ("fullbleed", "yew", "tokio")}
    result = dict(schema="fullbleed.yew-starter.v1", prefix=PREFIX, packages=packages,
                  files=files, zip_bytes=archive_path.stat().st_size,
                  zip_sha256=sha256(archive_path.read_bytes()).hexdigest())
    (DEST / "source.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(dict(ok=True, files=len(files), bytes=result["zip_bytes"], sha256=result["zip_sha256"])))
    return result


if __name__ == "__main__":
    build()
