"""Build and exercise the actual downloadable Next.js starter in a fresh directory."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--node", default=shutil.which("node"))
parser.add_argument("--out", type=Path, default=ROOT / "output/nextjs-verification")
args = parser.parse_args()
if not args.node:
    raise SystemExit("Node.js 22 or newer is required.")
node = Path(args.node).resolve()
npm = next((path for path in [
    node.parent / "node_modules/npm/bin/npm-cli.js",
    node.parent.parent / "lib/node_modules/npm/bin/npm-cli.js",
] if path.is_file()), None)
if npm is None:
    raise SystemExit("Use an official Node distribution containing npm.")

digest = lambda data: hashlib.sha256(data).hexdigest()
assets = ROOT / "docs/assets/nextjs"
manifest = json.loads((assets / "source.json").read_text(encoding="utf8"))
expected_assets = {item["file"]: item for item in manifest["assets"]}
assert set(expected_assets) == {"project.zip", "invoice.pdf", "invoice.png"}
for name, expected in expected_assets.items():
    data = (assets / name).read_bytes()
    assert len(data) == expected["bytes"] and digest(data) == expected["sha256"], name

out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix="download with spaces ", dir=out))
with zipfile.ZipFile(assets / "project.zip") as archive:
    names = archive.namelist()
    assert len(names) == len(set(names)) == manifest["files"]
    for entry in archive.infolist():
        relative = PurePosixPath(entry.filename)
        assert not relative.is_absolute() and ".." not in relative.parts
        assert "\\" not in entry.filename and ":" not in entry.filename
        assert relative.parts[0] == "fullbleed-nextjs" and len(relative.parts) > 1
        assert not entry.is_dir() and entry.file_size <= 10 * 1024 * 1024
        assert (entry.external_attr >> 16) & 0o170000 != 0o120000, "No symlinks"
        destination = workspace.joinpath(*relative.parts).resolve()
        assert destination.is_relative_to(workspace)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archive.read(entry))
project = workspace / "fullbleed-nextjs"
env = dict(os.environ, PATH=str(node.parent) + os.pathsep + os.environ.get("PATH", ""),
           NEXT_TELEMETRY_DISABLED="1")
commands = []


def run(label, arguments):
    result = subprocess.run([str(node), str(npm), *arguments], cwd=project, env=env,
                            capture_output=True, text=True, encoding="utf8", timeout=360)
    (out / (label + ".stdout.txt")).write_text(result.stdout, encoding="utf8")
    (out / (label + ".stderr.txt")).write_text(result.stderr, encoding="utf8")
    if result.returncode:
        raise RuntimeError(f"{label} failed ({result.returncode}); inspect {out}")
    commands.append({"name": label, "exitCode": 0})
    print(label + ": passed", flush=True)


run("install", ["ci", "--ignore-scripts", "--no-audit", "--no-fund"])
run("preview", ["run", "preview:pdf"])
run("build", ["run", "build"])
run("verify", ["run", "verify"])
preview = json.loads((project / "output/preview.json").read_text(encoding="utf8"))
verification = json.loads((project / "output/verification.json").read_text(encoding="utf8"))
assert preview["pages"] == 1 and preview["missingGlyphs"] == 0
assert len(verification["checks"]) == 17 and all(item["passed"] for item in verification["checks"])
assert verification["isolation"] == "process"
for actual, expected in [("output/invoice.pdf", "invoice.pdf"),
                         ("output/route.pdf", "invoice.pdf"),
                         ("public/invoice.png", "invoice.png")]:
    assert (project / actual).read_bytes() == (assets / expected).read_bytes(), actual
    shutil.copyfile(project / actual, out / Path(actual).name)
for name in ["verification.json", "preview.json", "server.log"]:
    shutil.copyfile(project / "output" / name, out / ("starter-" + name))
report = {
    "ok": True, "checkedAt": datetime.now(timezone.utc).isoformat(),
    "sourceCommit": manifest["sourceCommit"], "downloadFiles": len(names),
    "projectZipSha256": expected_assets["project.zip"]["sha256"],
    "node": verification["node"], "platform": verification["platform"],
    "next": verification["next"], "nodePackage": verification["nodePackage"],
    "engineVersion": verification["engineVersion"], "isolation": verification["isolation"], "commands": commands,
    "pdfSha256": digest((out / "route.pdf").read_bytes()),
    "previewSha256": digest((out / "invoice.png").read_bytes()),
    "checks": verification["checks"],
    "scope": "Fresh public ZIP installation, production build, isolated standalone HTTP server, and exact sample-asset comparison. No application authentication or hosted-provider claim.",
}
(out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
print(json.dumps({"ok": True, "files": len(names), "checks": len(report["checks"])}))
