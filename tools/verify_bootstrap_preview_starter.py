"""Run the exact Bootstrap ZIP and guide with an installed preview or alpha."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile

from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--channel", choices=("preview", "alpha", "alpha2", "alpha3"), default="preview")
    parser.add_argument("--install-report", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "target/bootstrap-preview")
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    assets = ROOT / f"docs/assets/bootstrap-{args.channel}"
    manifest = json.loads((assets / "source.json").read_text(encoding="utf-8"))
    output_manifest = json.loads((assets / "verification.json").read_text(encoding="utf-8"))
    for item in output_manifest["files"]:
        path = (assets / item["file"]).resolve()
        assert path.is_relative_to(assets.resolve())
        data = path.read_bytes()
        assert len(data) == item["bytes"] and sha256(data).hexdigest() == item["sha256"], item["file"]
    installation = None
    if args.install_report:
        report = json.loads(args.install_report.read_text(encoding="utf-8"))
        packages = [item for item in report["install"] if item["metadata"]["name"].lower() == "fullbleed"]
        assert len(packages) == 1
        package = packages[0]
        assert package["metadata"]["version"] == manifest["engine_wheels"]["package_version"]
        download = package["download_info"]
        matches = [item for item in manifest["engine_wheels"]["files"] if item["url"] == download["url"]]
        assert len(matches) == 1 and matches[0]["sha256"] == download["archive_info"]["hashes"]["sha256"]
        installation = {"url": download["url"], "sha256": matches[0]["sha256"]}

    archive_path = assets / "project.zip"
    assert sha256(archive_path.read_bytes()).hexdigest() == manifest["zip_sha256"]
    with tempfile.TemporaryDirectory(prefix="bootstrap-preview-") as folder:
        project = Path(folder)
        with zipfile.ZipFile(archive_path) as archive:
            prefix = f"fullbleed-bootstrap-{args.channel}/"
            assert set(archive.namelist()) == {prefix + item["path"] for item in manifest["files"]}
            for record in manifest["files"]:
                name = PurePosixPath(record["path"])
                assert not name.is_absolute() and ".." not in name.parts
                data = archive.read(prefix + str(name))
                assert sha256(data).hexdigest() == record["sha256"]
                target = project / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

        def run(label, arguments, cwd=project):
            result = subprocess.run([args.python, *arguments], cwd=cwd, capture_output=True,
                                    text=True, encoding="utf-8", timeout=240)
            (args.out / (label + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
            assert result.returncode == 0, (label, result.stdout, result.stderr)
            return result.stdout

        runtime = json.loads(run("runtime", ["-I", "-c",
            "import json,fullbleed;from pathlib import Path;from hashlib import sha256;from importlib.metadata import version;"
            "from fullbleed.ui.experimental import bootstrap as bs;"
            "root=Path(fullbleed.__file__).parent.parent;"
            "hashes={p.relative_to(root).as_posix():sha256(p.read_text(encoding='utf-8').encode('utf-8')).hexdigest() "
            "for p in sorted((root/'fullbleed/ui/experimental').rglob('*')) "
            "if p.suffix in ('.py','.pyi') or p.name=='py.typed'};"
            "print(json.dumps({'module':fullbleed.__file__,'version':version('fullbleed'),'engine_python_files':hashes,"
            "'bootstrap':bs.VERSION,'families':sorted(bs.COMPONENT_FAMILIES),"
            "'css_sha256':sha256(bs.stylesheet().encode()).hexdigest()}))"]))
        assert runtime["engine_python_files"] == manifest["engine_python_files"]
        assert runtime["version"] == manifest["engine_wheels"]["package_version"]
        assert runtime["bootstrap"] == "5.0.0" and len(runtime["families"]) == 23
        assert runtime["css_sha256"] == manifest["bootstrap_css_sha256"]
        first_folder = args.out / "first"
        first_folder.mkdir(exist_ok=True)
        run("first-document", ["-I", str(project / "first_document.py")], cwd=first_folder)
        run("catalog", ["examples/component_bootstrap/main.py", "--out", str(args.out / "catalog"), "--catalog-pdfs"])
        guide = (ROOT / "docs/guides/bootstrap-components-preview.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```python\n(.*?)```", guide, re.S)
        assert len(blocks) == 3
        assert "\n".join(blocks[:2]) == (project / "first_document.py").read_text(encoding="utf-8")
        assert sha256("\n".join(blocks[:2]).encode()).hexdigest() == manifest["first_document_sha256"]
        guide_folder = args.out / "guide"
        guide_folder.mkdir(exist_ok=True)
        for label, source in (("html-only", blocks[0]), ("complete-guide", "\n".join(blocks))):
            program = project / (label + ".py")
            program.write_text(source, encoding="utf-8")
            run(label, ["-I", str(program)], cwd=guide_folder)
        assert (guide_folder / "order.pdf").read_bytes() == (first_folder / "order.pdf").read_bytes()

    cases = []
    for path in sorted((args.out / "catalog").glob("*.pdf")) + [first_folder / "order.pdf"]:
        reader = PdfReader(path)
        assert len(reader.pages) == 1, path
        text = "\n".join(page.extract_text() for page in reader.pages)
        assert text.strip(), path
        if path.name == "catalog-forms.pdf":
            for value in ("Northstar Studio", "Company", "Standard stock", "Handle with care", "50 / 100"):
                assert value in text, value
            assert "Premium stock" not in text
        if path.name == "catalog-navs-tabs.pdf":
            assert "Inactive record history" not in text
        if path.name == "catalog-carousel.pdf":
            assert "Inactive collection" not in text
        if path.name == "catalog-list-group.pdf":
            compact = "".join(text.split())
            assert "1.Firstcheckpoint" in compact and "2.Finalcheckpoint" in compact
        if path.name == "report.pdf":
            assert all(value in text for value in ("408", "$8,640", "98%", "Studio notebooks", "$2,880.00", "75%"))
            assert path.read_bytes() == (assets / "report.pdf").read_bytes()
        if path.name == "order.pdf":
            assert all(value in text for value in ("Ready to ship", "ORDER / 1048", "Studio notebook", "$360.00", "Approved"))
            with closing(pdfium.PdfDocument(path)) as pdf:
                with closing(pdf[0]) as page, closing(page.render(scale=1.4)) as bitmap:
                    bitmap.to_pil().save(args.out / "order.png")
        cases.append({"file": path.relative_to(args.out).as_posix(), "pages": len(reader.pages),
                      "sha256": sha256(path.read_bytes()).hexdigest()})
    assert len(cases) == 29
    for stem in ("order",):
        styled = (first_folder / (stem + ".html")).read_text(encoding="utf-8")
        unstyled = (first_folder / (stem + ".unstyled.html")).read_text(encoding="utf-8")
        assert styled.count("Bootstrap v5.0.0") == 1 and "<script" not in styled.lower()
        assert not re.search(r"<style\b|\sstyle\s*=|<link\b|<script\b", unstyled, re.I)
        assert 'class="' in unstyled and "Ready to ship" in unstyled
    for name in ("report.styled.html", "report.unstyled.html", "catalog.html", "catalog.unstyled.html"):
        assert (args.out / "catalog" / name).read_bytes() == (assets / name).read_bytes(), name
    result = {"ok": True, "source_commit": manifest["source_commit"], "zip_sha256": manifest["zip_sha256"],
              "runtime": runtime, "cases": cases, "guide_blocks": len(blocks),
              "first_guide_block_runs_alone": True, "installed_authoring_source_matches": True,
              "wheel_installation": installation,
              "scope": "Exact ZIP entry points, guide blocks, 29 one-page PDFs, printed form selections and hidden states, styled/unstyled HTML, installed authoring source hashes, and matching published report/HTML bytes. Not exhaustive Bootstrap, accessibility or independent usability verification."}
    (args.out / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "pdfs": len(cases), "guide_blocks": len(blocks)}))


if __name__ == "__main__":
    main()
