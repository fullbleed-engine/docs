"""Run the actual downloadable project using the caller's installed Fullbleed."""
import argparse
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import json
import re
import subprocess
import sys
import tempfile
import zipfile

import fullbleed
from component_style_checks import PYTHON_RENDER, inspect_style_pdfs, styling_blocks

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/components"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "target/component-starter")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
    assert version("fullbleed") == manifest["fullbleed"]
    archive_path = ASSETS / "project.zip"
    assert sha256(archive_path.read_bytes()).hexdigest() == manifest["zip_sha256"]
    with tempfile.TemporaryDirectory(prefix="component-source-", dir=args.out) as folder:
        project = Path(folder).resolve()
        with zipfile.ZipFile(archive_path) as archive:
            assert set(archive.namelist()) == {"fullbleed-components/" + record["path"] for record in manifest["files"]}
            for record in manifest["files"]:
                name = record["path"]
                assert Path(name).name == name
                data = archive.read("fullbleed-components/" + name)
                assert sha256(data).hexdigest() == record["sha256"]
                (project / name).write_bytes(data)
        result = subprocess.run([sys.executable, str(project / "invoice.py"), "--output", str(args.out.resolve() / "render")],
                                cwd=project, capture_output=True, text=True, encoding="utf-8")
        (args.out / "render.log").write_text(result.stdout + result.stderr, encoding="utf-8")
        assert result.returncode == 0, result.stdout + result.stderr
    for output, published in [("invoice.pdf", "invoice.pdf"), ("page-1.png", "page-1.png")]:
        assert (args.out / "render" / output).read_bytes() == (ASSETS / published).read_bytes(), output
    rendered = json.loads((args.out / "render/verification.json").read_text(encoding="utf-8"))
    assert rendered["ok"] and rendered["pages"] == 1 and rendered["repeated_pdf_equal"]
    documentation_examples = []
    for page, output, required in [
        ("index.md", "component-invoice.pdf", ["Made for you", "Design", "$120"]),
        ("guides/python-components.md", "invoice.pdf", ["Maple & Finch", "Design", "Review", "$120.00", "$40.00"]),
    ]:
        source = (ROOT / "docs" / page).read_text(encoding="utf-8")
        blocks = re.findall(r"```python\n(.*?)```", source, flags=re.S)
        assert blocks, page
        code = blocks[0]
        folder = (args.out / "documentation" / page.removesuffix(".md").replace("/", "_")).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "example.py").write_text(code, encoding="utf-8", newline="\n")
        run = subprocess.run([sys.executable, "-I", str(folder / "example.py")], cwd=folder,
                             capture_output=True, text=True, encoding="utf-8", timeout=90)
        (folder / "example.log").write_text(run.stdout + run.stderr, encoding="utf-8")
        assert run.returncode == 0, (page, run.stdout + run.stderr)
        pdf = folder / output
        inspection = fullbleed.inspect_pdf(str(pdf))
        assert inspection["ok"] and inspection["page_count"] == 1, (page, inspection)
        assert inspection["profile"]["embedded_font_count"] > 0, page
        extracted = fullbleed.extract_pdf_page_texts(str(pdf))
        assert extracted["ok"] and len(extracted["pages"]) == 1, page
        compact = "".join(extracted["pages"][0]["text"].split())
        assert all("".join(text.split()) in compact for text in required), (page, required)
        if page == "guides/python-components.md":
            assert (folder / "invoice.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        documentation_examples.append({"page": page, "source_sha256": sha256(code.encode()).hexdigest(),
                                       "pdf_sha256": sha256(pdf.read_bytes()).hexdigest(),
                                       "pages": 1, "text_checks": required, "embedded_font": True})
    styling = (args.out / "guide-styles").resolve()
    styling.mkdir(parents=True, exist_ok=True)
    source = (ROOT / "docs/guides/python-components.md").read_text(encoding="utf-8")
    code = "\n".join(styling_blocks(source, "python")) + PYTHON_RENDER
    (styling / "example.py").write_text(code, encoding="utf-8", newline="\n")
    run = subprocess.run([sys.executable, "-I", str(styling / "example.py")], cwd=styling,
                         capture_output=True, text=True, encoding="utf-8", timeout=90)
    (styling / "example.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
    style_report = inspect_style_pdfs(styling)
    report = {"ok": True, "fullbleed": version("fullbleed"), "files": len(manifest["files"]),
              "zip_sha256": manifest["zip_sha256"], "rendered": rendered, "published_pdf_png_equal": True,
              "documentation_examples": documentation_examples, "class_styling": style_report}
    (args.out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
