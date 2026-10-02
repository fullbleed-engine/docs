"""Install and render the actual downloadable Node project and guide snippet."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--node", default=shutil.which("node"))
parser.add_argument("--out", type=Path, default=Path("output/node-verification"))
parser.add_argument("--update-assets", action="store_true")
args = parser.parse_args()
node = Path(args.node).resolve()
npm_candidates = [node.parent / "node_modules/npm/bin/npm-cli.js", node.parent.parent / "lib/node_modules/npm/bin/npm-cli.js"]
npm = next((p for p in npm_candidates if p.is_file()), None)
if npm is None:
    raise SystemExit("Use an official Node distribution containing npm.")
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix="node invoice with spaces ", dir=out))
assets = ROOT / "docs/assets/node"
manifest = json.loads((assets / "project.json").read_text(encoding="utf8"))
digest = lambda data: hashlib.sha256(data).hexdigest()
assert digest((assets / "project.zip").read_bytes()) == manifest["zip_sha256"]
with zipfile.ZipFile(assets / "project.zip") as archive:
    assert sorted(archive.namelist()) == sorted(manifest["files"])
    for name, expected in manifest["files"].items():
        destination = (workspace / name).resolve()
        assert destination.is_relative_to(workspace)
        data = archive.read(name)
        assert len(data) == expected["bytes"] and digest(data) == expected["sha256"]
        assert data == (ROOT / "examples/node" / name).read_bytes(), "Rebuild the project ZIP after changing " + name
        destination.write_bytes(data)
env = dict(os.environ, PATH=str(node.parent) + os.pathsep + os.environ["PATH"])
commands = []

def run(label, command, cwd=workspace):
    result = subprocess.run([str(node), *map(str, command)], cwd=cwd, env=env, capture_output=True, text=True, encoding="utf8", timeout=180)
    (out / (label + ".stdout.txt")).write_text(result.stdout, encoding="utf8")
    (out / (label + ".stderr.txt")).write_text(result.stderr, encoding="utf8")
    assert result.returncode == 0, (label, result.stderr)
    commands.append({"name": label, "exit_code": 0})
    return result.stdout

run("install", [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"])
result = json.loads(run("render", ["render.mjs"]))
assert result["pages"] == 1 and result["missingGlyphs"] == 0 and result["engine"] == manifest["engine_version"]
outputs = {}
for name, relative in [("invoice.pdf", "output/invoice/invoice.pdf"), ("invoice.png", "output/invoice/page-1.png")]:
    data = (workspace / relative).read_bytes()
    assert digest(data) == manifest["rendered"][name], name
    outputs[name] = digest(data)
    if args.update_assets:
        (assets / name).write_bytes(data)
    else:
        assert (assets / name).read_bytes() == data, name

source = (ROOT / "docs/getting-started/node.md").read_text(encoding="utf8")
blocks = re.findall(r"```javascript\n(.*?)```", source, re.S)
assert len(blocks) == 1
snippet = workspace / "guide-snippet"
snippet.mkdir()
(snippet / "invoice.mjs").write_text(blocks[0], encoding="utf8", newline="\n")
stdout = run("guide-snippet", ["invoice.mjs"], snippet)
assert "1 page; engine " + manifest["engine_version"] in stdout
for name in ["invoice.pdf", "invoice.png"]:
    data = (snippet / name).read_bytes()
    assert digest(data) == manifest["quickstart"][name], name
report = {"ok": True, "node": subprocess.check_output([str(node), "--version"], text=True).strip(),
          "platform": os.name, "package_version": manifest["package_version"], "engine_version": manifest["engine_version"],
          "source_commit": manifest["source_commit"], "commands": commands, "download_files": len(manifest["files"]),
          "project_zip_sha256": manifest["zip_sha256"], "outputs": outputs, "quickstart": manifest["quickstart"],
          "workspace": workspace.name, "scope": "Actual public package installation, downloadable project, and documentation snippet; reviewed output hashes."}
(out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
print(json.dumps({"ok": True, "node": report["node"], "files": report["download_files"], "commands": len(commands)}))
