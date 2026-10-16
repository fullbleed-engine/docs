"""Exercise the exact preview download and guide using an installed candidate."""
import argparse
from contextlib import closing
from hashlib import sha256
from io import BytesIO
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
ASSETS = ROOT / "docs/assets/component-preview"


def compact(text):
    return "".join(text.split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Isolated candidate Python; verification readers stay in the caller")
    parser.add_argument("--out", type=Path, default=ROOT / "target/component-preview")
    args = parser.parse_args()
    args.out = args.out.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
    archive_path = ASSETS / "project.zip"
    assert sha256(archive_path.read_bytes()).hexdigest() == manifest["zip_sha256"]
    with tempfile.TemporaryDirectory(prefix="component-preview-") as folder:
        project = Path(folder)
        with zipfile.ZipFile(archive_path) as archive:
            assert len(archive.namelist()) == len(manifest["files"])
            assert set(archive.namelist()) == {"fullbleed-component-preview/" + record["path"] for record in manifest["files"]}
            for record in manifest["files"]:
                name = PurePosixPath(record["path"])
                assert not name.is_absolute() and ".." not in name.parts
                data = archive.read("fullbleed-component-preview/" + str(name))
                assert sha256(data).hexdigest() == record["sha256"]
                target = project / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)

        def run(label, arguments, cwd=project):
            result = subprocess.run([args.python, *arguments], cwd=cwd, capture_output=True,
                                    text=True, encoding="utf-8", timeout=180)
            (args.out / (label + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
            assert result.returncode == 0, (label, result.stdout, result.stderr)
            return result.stdout

        runtime = json.loads(run("runtime", ["-I", "-c",
            "import json,fullbleed;from fullbleed.ui.experimental import Theme,Document;"
            "assert hasattr(Theme,'with_values') and hasattr(Document,'required_tokens') and hasattr(Document,'styles');"
            "assert hasattr(fullbleed.CompiledDocument,'export_render_time_pagination_trace');"
            "print(json.dumps({'module':fullbleed.__file__,'features':fullbleed.build_features()}))"]))
        run("documents", ["examples/component_recipes/main.py", "--output", str(args.out / "documents")])
        run("edits", ["edit_tasks.py", "--output", str(args.out / "edits")])
        source = (ROOT / "docs/guides/component-design-preview.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```python\n(.*?)```", source, re.S)
        assert len(blocks) == 5
        guide = project / "guide.py"
        guide.write_text("\n\n".join(blocks), encoding="utf-8")
        run("guide", ["guide.py"])
        guide_pdf = project / "component-preview.pdf"
        assert guide_pdf.is_file()
        (args.out / "guide.pdf").write_bytes(guide_pdf.read_bytes())

    cases = []
    for name, file, pages, size, required in (
        ("invoice", "documents/invoice.pdf", 1, (595.276, 841.89), ["Maple & Finch", "$8,100.00"]),
        ("report", "documents/report.pdf", 5, (612, 792), [f"Deliverable {index:03d}" for index in range(1, 61)]),
        ("shared-components", "edits/shared-components.pdf", 1, (419.528, 595.276), ["Made for your next project", "Maple & Finch", "$8,100.00"]),
        ("extra-column", "edits/extra-column.pdf", 1, (595.276, 841.89), ["Cost per project", "Hours", "$3,600.00"]),
        ("letter-invoice", "edits/letter-invoice.pdf", 1, (612, 792), ["Maple & Finch", "$8,100.00"]),
        ("selector-styles", "edits/selector-styles.pdf", 1, (419.528, 595.276), ["Shared class: blue", "One instance: rust"]),
        ("repaired-notice", "edits/repaired-notice.pdf", 1, (595.276, 841.89), ["A long notice can continue"]),
    ):
        data = (args.out / file).read_bytes()
        reader = PdfReader(BytesIO(data))
        assert len(reader.pages) == pages, (name, len(reader.pages))
        text = compact(" ".join(page.extract_text() for page in reader.pages))
        assert all(compact(value) in text for value in required), name
        for page in reader.pages:
            assert abs(float(page.mediabox.width) - size[0]) < .1 and abs(float(page.mediabox.height) - size[1]) < .1, name
        if name in {"invoice", "report"}:
            assert data == (ASSETS / (name + ".pdf")).read_bytes(), name
        if name == "report":
            assert all(text.count(compact(value)) == 1 for value in required)
            assert all("ProjectHoursRateAmount" in compact(page.extract_text()) for page in reader.pages)
        cases.append({"name": name, "pages": pages, "sha256": sha256(data).hexdigest(), "text_checked": True, "size_checked": True})
        if name == "selector-styles":
            with closing(pdfium.PdfDocument(data)) as pdf:
                # At 144 dpi the 16 pt letters have enough interior pixels to
                # check both colors independently of their antialiased edges.
                with closing(pdf[0]) as page, closing(page.render(scale=2)) as bitmap:
                    image = bitmap.to_pil().convert("RGB")
                    pixels = list(image.getdata())
                    for color in ((49, 93, 155), (160, 68, 46)):
                        assert sum(max(abs(a-b) for a,b in zip(pixel,color)) <= 2 for pixel in pixels) > 100, color
                    image.save(args.out / "selector-styles.png")
            cases[-1]["selector_and_instance_colors_checked"] = True
    error = json.loads((args.out / "edits/expected-layout-error.json").read_text(encoding="utf-8"))
    assert error["code"] == "layout.unsplittable" and error["reason"] == "clipped_container", error
    assert ["Notice", "div"] in error["failure_sources"], error
    guide_text = compact(" ".join(page.extract_text() for page in PdfReader(args.out / "guide.pdf").pages))
    assert all(compact(text) in guide_text for text in ("Maple & Finch", "Portable design", "Shared selector styling", "Design", "$120.00"))
    result = {"ok": True, "source_commit": manifest["source_commit"], "zip_sha256": manifest["zip_sha256"],
              "runtime": runtime, "cases": cases, "guide_blocks": len(blocks), "expected_layout_error": error,
              "scope": "Actual ZIP extraction and entry points, real guide snippets, page geometry/text, exact published invoice/report bytes and a rejected/repaired layout. Not independent usability or conformance evidence."}
    (args.out / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "cases": len(cases), "pages": sum(case["pages"] for case in cases), "guide_blocks": len(blocks)}))


if __name__ == "__main__":
    main()
