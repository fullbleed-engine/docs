"""Run the downloadable project and independently compare its saved PDFs."""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/showcase-authoring"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "target/showcase-authoring")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
    assert version("fullbleed") == manifest["engine_version"] == "2.6.0a4"
    archive = ASSETS / "project.zip"
    assert sha256(archive.read_bytes()).hexdigest() == manifest["zip_sha256"]
    project = out / "project"
    assert not project.exists(), "Use a fresh output directory"
    project.mkdir()
    with ZipFile(archive) as package:
        expected = {"fullbleed-showcase-authoring/" + name for name in manifest["package_files"]}
        assert set(package.namelist()) == expected and len(package.namelist()) == len(expected)
        for name, digest in manifest["package_files"].items():
            path = project / name
            assert project in path.resolve().parents
            data = package.read("fullbleed-showcase-authoring/" + name)
            assert sha256(data).hexdigest() == digest
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    run = subprocess.run([sys.executable, str(project / "examples/design_showcase/compare_authoring.py"),
                          "--out", str(out / "rendered")], capture_output=True, encoding="utf-8")
    (out / "comparison.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
    actual = json.loads((out / "rendered/comparison.json").read_text(encoding="utf-8"))
    expected = json.loads((ASSETS / "comparison.json").read_text(encoding="utf-8"))
    assert actual == expected, "The downloaded source changed the published comparison"
    pages = []
    for record in actual["documents"]:
        name = record["name"]
        paths = [out / "rendered" / lane / name / f"{name}.pdf" for lane in ("html", "components")]
        for lane, path in zip(("html", "components"), paths):
            assert path.read_bytes() == (ASSETS / f"{name}-{lane}.pdf").read_bytes()
        readers = [PdfReader(path) for path in paths]
        documents = [pdfium.PdfDocument(str(path)) for path in paths]
        try:
            assert len(documents[0]) == len(documents[1]) == record["page_count"]
            for index in range(record["page_count"]):
                assert readers[0].pages[index].extract_text() == readers[1].pages[index].extract_text()
                rendered = []
                for lane, document in zip(("html", "components"), documents):
                    page = document[index]
                    bitmap = page.render(scale=2)
                    try:
                        image = bitmap.to_pil().convert("RGB")
                        folder = out / "pdfium" / lane / name
                        folder.mkdir(parents=True, exist_ok=True)
                        image.save(folder / f"page-{index + 1}.png")
                        rendered.append((image.size, image.tobytes()))
                    finally:
                        bitmap.close()
                        page.close()
                assert rendered[0] == rendered[1], (name, index + 1)
                pages.append(dict(document=name, page=index + 1, dpi=144,
                                  pixels_sha256=sha256(rendered[0][1]).hexdigest(), identical=True))
        finally:
            for document in documents:
                document.close()
    guide = (ROOT / "docs/guides/showcase-authoring.md").read_text(encoding="utf-8")
    blocks = re.findall(r"^\s*```python\n(.*?)^\s*```", guide, re.M | re.S)
    assert len(blocks) == 3
    import textwrap
    sys.path.insert(0, str(project / "examples/design_showcase"))
    code_out = out / "guide"
    code_out.mkdir()
    prior = Path.cwd()
    try:
        os.chdir(code_out)
        namespace = {"__name__": "__showcase_guide__"}
        for block in blocks:
            exec(compile(textwrap.dedent(block), "showcase-authoring.md", "exec"), namespace)
    finally:
        os.chdir(prior)
    assert (code_out / "invoice.pdf").read_bytes() == (ASSETS / "invoice-components.pdf").read_bytes()
    # Exercise editing, including escaping and data-dependent amounts, rather
    # than validating only the original fixture's literal strings.
    import compare_authoring
    previous_data = compare_authoring.original.DATA
    changed = deepcopy(previous_data)
    changed["invoice"][0].update(description="Research & review <phase 1>", hours=7, rate="130.25")
    changed["report"].update(households=1255, volunteer_hours=4905,
                             quarterly_households=[400, 555, 750, 975])
    changed["report"]["allocations"][0]["amount"] = 176000
    try:
        compare_authoring.original.DATA = changed
        edited = [compare_authoring.compare(out / "edited-data", name, dpi=120) for name in ("invoice", "report")]
    finally:
        compare_authoring.original.DATA = previous_data
    assert all(record["ok"] for record in edited), edited
    result = dict(ok=True, engine_version=version("fullbleed"), source_commit=manifest["source_commit"],
                  zip_sha256=manifest["zip_sha256"], native_comparison=actual, independent_pages=pages,
                  pdfium_version=version("pypdfium2"), guide_blocks=len(blocks), edited_data=edited)
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"ok": True, "native_pages": 4, "independent_pages": len(pages), "guide_blocks": len(blocks),
                      "edited_documents": len(edited)}))


if __name__ == "__main__":
    main()
