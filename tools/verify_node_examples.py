"""Install and render the actual Node invoice/report download and guide snippets."""
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
from textwrap import dedent
from pypdf import PdfReader
import pypdfium2 as pdfium

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
installed = json.loads((workspace / "node_modules/fullbleed/package.json").read_text(encoding="utf8"))
assert installed["version"] == manifest["package_version"], "Installed package version differs from the guide."
assert installed["fullbleed"]["engineVersion"] == manifest["engine_version"]
lock = json.loads((workspace / "package-lock.json").read_text(encoding="utf8"))
assert lock["packages"]["node_modules/fullbleed"]["integrity"] == manifest["package_integrity"]
result = json.loads(run("render", [npm, "run", "--silent", "render"]))
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

report_result = json.loads(run("render-report", [npm, "run", "--silent", "render:report"]))
assert report_result["pages"] == 3 and report_result["missingGlyphs"] == 0
assert report_result["engine"] == manifest["report_engine_version"] == manifest["engine_version"]
assert installed["version"] == manifest["report_package_version"]
report_pdf = workspace / "output/report/report.pdf"
report_reader = PdfReader(report_pdf, strict=True)
assert len(report_reader.pages) == 3
report_text = ''.join(page.extract_text() for page in report_reader.pages)
for expected in ["COMMON", "GROUND", "1,240", "4,860", "$420,000.00"]:
    assert expected in report_text, expected
report_outputs = {}
for name, relative in [("report.pdf", "output/report/report.pdf"), ("report-2.png", "output/report/page-2.png")]:
    data = (workspace / relative).read_bytes()
    assert digest(data) == manifest["report"][name], name
    report_outputs[name] = digest(data)
    if args.update_assets:
        (assets / name).write_bytes(data)
    else:
        assert (assets / name).read_bytes() == data, name
with pdfium.PdfDocument(report_pdf) as document:
    report_independent_text = []
    for page in document:
        textpage = page.get_textpage()
        report_independent_text.append(textpage.get_text_range())
        textpage.close()
        page.close()
assert all(text.strip() for text in report_independent_text)
assert '$420,000.00' in ''.join(report_independent_text)

source = (ROOT / "docs/getting-started/node.md").read_text(encoding="utf8")
assert f'**Node package {installed["version"]}**' in source
assert f'**Fullbleed {installed["fullbleed"]["engineVersion"]}**' in source
assert 'npm run render:report' in source and 'npm run render:report' in (workspace / 'README.md').read_text(encoding='utf8')
blocks = re.findall(r"```javascript\n(.*?)```", source, re.S)
assert len(blocks) == 3
quickstart_code, named_font_code, process_code = blocks
home = (ROOT / 'docs/index.md').read_text(encoding='utf8')
home_code = re.findall(r'```javascript\n(.*?)```', home, re.S)
assert len(home_code) == 1 and dedent(home_code[0]).strip() == quickstart_code.strip(), 'Homepage Node example differs from the executed guide.'
snippet = workspace / "guide-snippet"
snippet.mkdir()
(snippet / "invoice.mjs").write_text(quickstart_code, encoding="utf8", newline="\n")
stdout = run("guide-snippet", ["invoice.mjs"], snippet)
assert "1 page; engine " + manifest["engine_version"] in stdout
for name in ["invoice.pdf", "invoice.png"]:
    data = (snippet / name).read_bytes()
    assert digest(data) == manifest["quickstart"][name], name
process_script = """import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { renderPdf } from 'fullbleed';
""" + process_code + """
assert.equal(result.pages, 1);
assert.equal(result.missingGlyphs, 0);
assert.equal(result.pdf.subarray(0, 5).toString(), '%PDF-');
await writeFile('process-statement.pdf', result.pdf);
"""
(snippet / "process-snippet.mjs").write_text(process_script, encoding="utf8", newline="\n")
run("process-snippet", ["process-snippet.mjs"], snippet)
process_pdf = (snippet / "process-statement.pdf").read_bytes()
(out / "process-statement.pdf").write_bytes(process_pdf)
# Execute the named-font guide block with the public version used by the playground.
named = workspace / "named-font-guide"
named.mkdir()
for name in ["package.json", "package-lock.json"]:
    shutil.copyfile(ROOT / "docs/assets/playground/project/node" / name, named / name)
named_spec = json.loads((named / "package.json").read_text(encoding="utf8"))
named_version = named_spec["dependencies"]["fullbleed"]
named_engine = named_spec["fullbleed"]["engineVersion"]
assert named_engine == json.loads((ROOT / "docs/assets/playground/build.json").read_text(encoding="utf8"))["engine"]["version"]
assert f"use **Node package {named_version}** with the same **{named_engine}** engine." in source, "Update the guide's playground export versions."
font_source = ROOT / "examples/markdown/fonts/IBMPlexMono-Regular.ttf"
shutil.copyfile(font_source, named / "Brand.ttf")
shutil.copyfile(font_source.with_name("OFL.txt"), named / "OFL.txt")
run("named-font-install", [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"], named)
named_installed = json.loads((named / "node_modules/fullbleed/package.json").read_text(encoding="utf8"))
assert named_installed["version"] == named_version and named_installed["fullbleed"]["engineVersion"] == named_engine
named_script = """import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
""" + named_font_code + """
assert.equal(result.pages, 1);
assert.equal(result.missingGlyphs, 0);
await writeFile('named-font-guide.pdf', result.pdf);
"""
named_script += f"\nassert.equal(result.engineVersion, {json.dumps(named_engine)});\n"
(named / "named-font-guide.mjs").write_text(named_script, encoding="utf8", newline="\n")
run("named-font-snippet", ["named-font-guide.mjs"], named)
named_pdf = out / "named-font-guide.pdf"
shutil.copyfile(named / named_pdf.name, named_pdf)
reader = PdfReader(named_pdf)
assert len(reader.pages) == 1 and reader.pages[0].extract_text().strip() == "Your document, your typography."
fonts = [font.get_object() for font in reader.pages[0]["/Resources"]["/Font"].values()]
assert fonts and all("IBMPlexMono" in str(font["/BaseFont"]) for font in fonts), "The guide font alias fell back to another font."
assert all("/FontFile2" in font["/DescendantFonts"][0].get_object()["/FontDescriptor"].get_object() for font in fonts)
named_preview = out / "named-font-guide.pdfium.png"
with pdfium.PdfDocument(named_pdf) as document:
    page = document[0]
    page.render(scale=96 / 72).to_pil().save(named_preview)
    page.close()
report = {"ok": True, "node": subprocess.check_output([str(node), "--version"], text=True).strip(),
          "platform": os.name, "package_version": installed["version"], "engine_version": installed["fullbleed"]["engineVersion"],
          "installed_package_matches_manifest": True,
          "source_commit": manifest["source_commit"], "commands": commands, "download_files": len(manifest["files"]),
          "project_zip_sha256": manifest["zip_sha256"], "outputs": outputs, "quickstart": manifest["quickstart"],
          "report": {"pages": 3, "outputs": report_outputs, "pdfiumText": report_independent_text},
          "homepage_snippet_matches_executed_guide": True,
          "process_snippet": {"ok": True, "pdf_sha256": digest(process_pdf)},
          "named_font_snippet": {"ok": True, "package_version": named_version, "engine_version": named_engine,
                                 "source_sha256": digest(named_font_code.encode("utf8")),
                                 "font_sha256": digest(font_source.read_bytes()),
                                 "pdf_sha256": digest(named_pdf.read_bytes()), "preview_sha256": digest(named_preview.read_bytes()),
                                 "embedded_fonts": [str(font["/BaseFont"]) for font in fonts]},
          "workspace": workspace.name, "scope": "Actual public package installation, downloadable project, and documentation snippet; reviewed output hashes."}
(out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
public = {key: value for key, value in report.items() if key != 'workspace'}
public.update(schema='fullbleed.node-guide-verification.v1',
              source_revision=os.environ.get('GITHUB_SHA'), ci_run_id=os.environ.get('GITHUB_RUN_ID'),
              input_sha256={name: digest((ROOT / name).read_bytes()) for name in [
                  'docs/getting-started/node.md', 'docs/index.md', 'tools/verify_node_examples.py',
                  'examples/node/render.mjs', 'examples/node/render-report.mjs', 'examples/node/source.json']})
(assets / 'guide-verification.json').write_text(json.dumps(public, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({"ok": True, "node": report["node"], "files": report["download_files"], "commands": len(commands)}))
