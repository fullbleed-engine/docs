"""Execute the introductory documentation with its declared Fullbleed release."""
import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from textwrap import dedent

import fullbleed

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = [
    ("index.md", "invoice.pdf", [("Invoice INV-1042", "USD 1,200.00")], True),
    ("getting-started/quickstart.md", "invoice.pdf", [("Invoice INV-1042", "USD 1,200.00")], True),
    ("getting-started/first-pdf.md", "output/invoice.pdf", [("Service invoice", "INV-1042", "USD 1,200.00")], True),
    ("engine/assets.md", "registered-font.pdf", [("Quarterly statement",)], True),
    ("guides/bank-statements.md", "statements.pdf", [("ST-001", "Ada"), ("ST-002", "Grace")], True),
]


def compact(text):
    return "".join(text.split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("output/quickstart-verification"))
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    reference = json.loads((ROOT / "docs/reference-source.json").read_text(encoding="utf-8"))
    expected = reference["release"].removeprefix("v")
    installed = version("fullbleed")
    if installed != expected:
        raise SystemExit(f"Install fullbleed=={expected} in this environment; found {installed}.")
    workspace = Path(tempfile.mkdtemp(prefix="quickstarts with spaces ", dir=out))
    env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH="")
    checks = []

    def run(label, arguments, cwd):
        result = subprocess.run([sys.executable, *map(str, arguments)], cwd=cwd, env=env,
                                capture_output=True, text=True, encoding="utf-8", timeout=90)
        (cwd / (label + ".stdout.txt")).write_text(result.stdout, encoding="utf-8")
        (cwd / (label + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
        if result.returncode:
            raise RuntimeError(f"{label} exited {result.returncode}; see {cwd}")
        checks.append({"command": label, "exit_code": 0})
        return result

    def inspect(path, page_texts=None, embedded_font=False):
        report = fullbleed.inspect_pdf(str(path))
        assert report["ok"] and report["page_count"] > 0, (path, report)
        text = fullbleed.extract_pdf_page_texts(str(path))
        assert text["ok"] and len(text["pages"]) == report["page_count"], path
        if page_texts is not None:
            assert report["page_count"] == len(page_texts), (path, report)
            for page, required in zip(text["pages"], page_texts):
                for phrase in required:
                    assert compact(phrase) in compact(page["text"]), (path, page["page"], phrase)
        else:
            assert any(compact(page["text"]) for page in text["pages"]), path
        if embedded_font:
            assert report["profile"]["embedded_font_count"] > 0, path
        preview = path.parent / "review-preview"
        fullbleed.PdfEngine().render_finalized_pdf_image_pages_to_dir(str(path), str(preview), 96, path.stem)
        images = sorted(preview.glob(path.stem + "_page*.png"))
        assert len(images) == report["page_count"], path
        evidence = {"inspection": report, "text": text}
        (path.parent / (path.stem + "-inspection.json")).write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
        return {"pdf": path.relative_to(out).as_posix(), "pages": report["page_count"],
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "previews": [{"path": p.relative_to(out).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in images]}

    snippets = []
    capability_snippets = []
    for page, output, required, embedded_font in FIXTURES:
        source = (ROOT / "docs" / page).read_text(encoding="utf-8")
        blocks = re.findall(r"```python\n(.*?)```", source, flags=re.S)
        expected_blocks = 2 if page == "engine/assets.md" else 1
        assert len(blocks) == expected_blocks, (page, len(blocks))
        folder = workspace / page.removesuffix(".md").replace("/", "_")
        folder.mkdir()
        code = dedent(blocks[0])
        # This API snippet returns bytes; retain them without changing its example.
        retained = code
        if page == "engine/assets.md":
            retained += '\nfrom pathlib import Path\nPath("registered-font.pdf").write_bytes(pdf)\n'
        (folder / "snippet.py").write_text(retained, encoding="utf-8", newline="\n")
        run("snippet", ["-I", "snippet.py"], folder)
        pdf = folder / output
        snippets.append({"page": page, "source_sha256": hashlib.sha256(code.encode()).hexdigest(),
                         **inspect(pdf, required, embedded_font)})
        if page == "engine/assets.md":
            discovery = dedent(blocks[1])
            (folder / "capability.py").write_text(discovery, encoding="utf-8", newline="\n")
            result = run("preview-capability", ["-I", "capability.py"], folder)
            available = fullbleed.build_features().get("bundled_standard_font_previews", False)
            assert result.stdout.strip() == str(available), result.stdout
            capability_snippets.append({"page": page,
                "source_sha256": hashlib.sha256(discovery.encode()).hexdigest(),
                "feature": "bundled_standard_font_previews", "available": available})
        if page == "getting-started/first-pdf.md":
            assert len(list((folder / "output/preview").glob("*.png"))) == 1
        if page == "getting-started/quickstart.md":
            result = run("inspect-cli", ["-I", "-m", "fullbleed", "inspect", "pdf", "invoice.pdf", "--json"], folder)
            assert json.loads(result.stdout)["ok"]

    project = workspace / "my-report"
    project.mkdir()
    run("init-project", ["-I", "-m", "fullbleed", "init", "."], project)
    run("render-project", ["report.py"], project)
    scaffold = inspect(project / "output/report.pdf")
    for template in ["invoice", "accessible"]:
        folder = workspace / ("my-" + template)
        run("new-" + template, ["-I", "-m", "fullbleed", "new", "local", template, str(folder)], workspace)
        assert (folder / "report.py").is_file(), folder

    result = {"ok": True, "engine": installed, "reference_commit": reference["commit"],
              "platform": sys.platform, "python": sys.version, "snippets": snippets,
              "capability_snippets": capability_snippets,
              "scaffold": scaffold, "commands": checks,
              "scope": "Introductory snippets and scaffold commands; text, page counts, fonts, and previews. No general visual or standards certification."}
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "engine": installed, "snippets": len(snippets), "commands": len(checks)}))


if __name__ == "__main__":
    main()
