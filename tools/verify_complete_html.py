"""Exercise the complete-HTML guide and its actual downloadable project."""
from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

import fullbleed
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/complete-html"
OUT = ROOT / "target/complete-html"
OUT.mkdir(parents=True, exist_ok=True)
record = json.loads((ASSETS / "verification.json").read_text(encoding="utf-8"))
assert metadata.version("fullbleed") == record["version"] == "2.5.26"
assert fullbleed.build_features().get("embedded_stylesheets")
assert not Path(fullbleed.__file__).resolve().is_relative_to(ROOT)
for name, expected in record["files"].items():
    data = (ASSETS / name).read_bytes()
    assert len(data) == expected["bytes"] and sha256(data).hexdigest() == expected["sha256"], name

guide = ROOT / "docs/guides/complete-html.md"
blocks = re.findall(r"```python\n(.*?)```", guide.read_text(encoding="utf-8"), re.S)
assert len(blocks) == 3
guide_out = OUT / "guide"
guide_out.mkdir(exist_ok=True)
previous = Path.cwd()
try:
    os.chdir(guide_out)
    namespace = {"__name__": "__main__"}
    for block in blocks:
        exec(compile(block, str(guide), "exec"), namespace)
finally:
    os.chdir(previous)

guide_outputs = []
for name in ("receipt.pdf", "warm-receipt.pdf"):
    path = guide_out / name
    pdf = PdfReader(path)
    assert len(pdf.pages) == 1
    page = pdf.pages[0]
    assert abs(float(page.mediabox.width) - 419.528) < 0.02
    assert abs(float(page.mediabox.height) - 595.276) < 0.02
    text = page.extract_text()
    assert "Payment received" in text and "Maple & Finch" in text and "$120.00" in text
    guide_outputs.append({"file": name, "pages": 1, "sha256": sha256(path.read_bytes()).hexdigest()})
assert guide_outputs[0]["sha256"] != guide_outputs[1]["sha256"]

destination = OUT / "extracted project with spaces"
with zipfile.ZipFile(ASSETS / "project.zip") as archive:
    names = archive.namelist()
    expected = {"LICENSE", "README.txt", "invoice.html", "render.py", "requirements.txt"}
    assert len(names) == len(set(names)) == len(expected)
    for name in names:
        path = PurePosixPath(name)
        assert not path.is_absolute() and ".." not in path.parts and "\\" not in name
        assert len(path.parts) == 2 and path.parts[0] == "fullbleed-complete-html"
        assert path.parts[1] in expected
    assert archive.testzip() is None
    archive.extractall(destination)
project = destination / "fullbleed-complete-html"
assert (project / "requirements.txt").read_text().strip() == "fullbleed==2.5.26"
completed = subprocess.run(
    [sys.executable, "-I", str(project / "render.py")], cwd=OUT,
    capture_output=True, text=True, encoding="utf-8", timeout=60,
)
(OUT / "example.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
assert completed.returncode == 0, completed.stderr
for emitted, expected in (("invoice.pdf", "invoice.pdf"), ("invoice-page-1.png", "invoice.png")):
    assert (project / emitted).read_bytes() == (ASSETS / expected).read_bytes(), emitted
pdf = PdfReader(project / "invoice.pdf")
assert len(pdf.pages) == 1
text = "".join(pdf.pages[0].extract_text().split())
for expected in record["text_checks"]:
    assert "".join(expected.split()) in text

result = {
    "ok": True, "version": metadata.version("fullbleed"), "guide_python_blocks": len(blocks),
    "guide_outputs": guide_outputs, "downloaded_project_files": len(names),
    "project_zip_sha256": record["files"]["project.zip"]["sha256"],
    "example_pdf_matches_download": True, "example_native_preview_matches_download": True,
    "example_pdf_sha256": record["pdf_sha256"], "example_pages": 1,
    "scope": "Installed PyPI engine, exact guide code, actual ZIP extraction and execution, and retained PDF/preview comparison.",
}
(OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result))
