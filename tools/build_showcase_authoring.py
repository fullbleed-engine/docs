"""Build the reproducible source ZIP for the paired authoring examples."""
import argparse
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_STORED

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "examples/showcase-authoring"
ASSETS = ROOT / "docs/assets/showcase-authoring"


def main(channel="alpha4"):
    suffix = "" if channel == "alpha4" else "-" + channel
    project = ROOT / ("examples/showcase-authoring" + suffix)
    assets = ROOT / ("docs/assets/showcase-authoring" + suffix)
    archive_root = "fullbleed-showcase-authoring" + suffix
    source = json.loads((project / "SOURCE.json").read_text(encoding="utf-8"))
    names = sorted([*source["source_files"], "LICENSE", "README.md", "SOURCE.json", "requirements.txt"])
    contents = {name: (project / name).read_bytes() for name in names}
    assert all(sha256(contents[name]).hexdigest() == digest for name, digest in source["source_files"].items())
    archive = BytesIO()
    with ZipFile(archive, "w", compression=ZIP_STORED) as package:
        for name, data in contents.items():
            info = ZipInfo(archive_root + "/" + name, (2026, 10, 17, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            package.writestr(info, data)
    data = archive.getvalue()
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "project.zip").write_bytes(data)
    record = {**source, "zip_sha256": sha256(data).hexdigest(), "zip_bytes": len(data),
              "package_files": {name: sha256(content).hexdigest() for name, content in contents.items()}}
    (assets / "source.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "files": len(contents), "zip_sha256": record["zip_sha256"], "bytes": len(data)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", choices=("alpha4", "alpha5"), default="alpha4")
    main(parser.parse_args().channel)
