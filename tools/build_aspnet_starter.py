"""Assemble the self-contained ASP.NET starter with stable ZIP bytes and hashes."""
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples/aspnet"
ASSETS = ROOT / "docs/assets/aspnet"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def project_files():
    names = ["FullbleedWeb.csproj", "Program.cs", "InvoiceRenderer.cs", "global.json",
             "packages.lock.json", "README.md", "LICENSE"]
    names += [p.relative_to(PROJECT).as_posix() for p in (PROJECT / "Assets").rglob("*") if p.is_file()]
    return {name: (PROJECT / name).read_bytes() for name in sorted(names)}


def archive_bytes(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in files.items():
            entry = zipfile.ZipInfo("fullbleed-aspnet/" + name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
    return buffer.getvalue()


def build():
    ASSETS.mkdir(parents=True, exist_ok=True)
    files = project_files()
    archive = archive_bytes(files)
    (ASSETS / "project.zip").write_bytes(archive)
    manifest = {
        "source": "https://github.com/fullbleed-engine/docs/tree/main/examples/aspnet",
        "framework": "net10.0", "package": "FullBleed.DotNet", "packageVersion": "0.1.5",
        "projectZipSha256": digest(archive),
        "files": [{"path": name, "bytes": len(data), "sha256": digest(data)} for name, data in files.items()],
        "outputs": {name: digest((ASSETS / name).read_bytes()) for name in ["invoice.pdf", "invoice.png"]},
    }
    (ASSETS / "source.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"files": len(files), "zipBytes": len(archive), "sha256": digest(archive)}))


if __name__ == "__main__":
    build()
