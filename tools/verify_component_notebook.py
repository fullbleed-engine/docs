#!/usr/bin/env python3
"""Execute the component notebook and inspect its real PDF/HTML/ZIP outputs."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from html.parser import HTMLParser
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import tempfile
from zipfile import ZipFile

import nbformat
from nbclient import NotebookClient
from jupyter_client import AsyncKernelManager
from jupyter_client.kernelspec import KernelSpecManager
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
CHANNELS = {
    "alpha3": ("2.6.0a3", "component-notebook"),
    "alpha5": ("2.6.0a5", "component-notebook-alpha5"),
    "alpha6": ("2.6.0a6", "component-notebook-alpha6"),
    "alpha6-r1": ("2.6.0a6", "component-notebook-alpha6-r1"),
}


class Markup(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.text = []
        self.classes = set()
        self.cell_strong_text = []
        self._cell_depth = 0
        self._strong_depth = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        self.classes.update(attrs.get("class", "").split())
        if tag == "td":
            self._cell_depth += 1
        if tag == "strong":
            self._strong_depth += 1

    def handle_endtag(self, tag):
        if tag == "td":
            self._cell_depth -= 1
        if tag == "strong":
            self._strong_depth -= 1

    def handle_data(self, data):
        self.text.append(data)
        if self._cell_depth and self._strong_depth:
            self.cell_strong_text.append(data)


def write(path: Path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def normalize(text: str) -> str:
    return " ".join(text.split())


def execute(notebook, work: Path, destination: Path, kernel_dir: str):
    notebook.cells.append(nbformat.v4.new_code_cell('''
import fullbleed, importlib.metadata, json
from hashlib import sha256
assert prepared.render_pdf() == pdf_path.read_bytes(), "Repeat rendering changed the PDF"
assert document.render_pdf(renderer) == pdf_path.read_bytes(), "Direct and prepared output differ"
Path("notebook-runtime.json").write_text(json.dumps({
    "version": importlib.metadata.version("fullbleed"),
    "inspection": dict(fullbleed.inspect_pdf(str(pdf_path))),
    "repeat_pdf_identical": True,
    "direct_pdf_identical": True,
    "preview_count": len(preview_paths),
}), encoding="utf-8")
'''))
    client = NotebookClient(
        notebook,
        km=AsyncKernelManager(
            kernel_name="component-notebook-check",
            kernel_spec_manager=KernelSpecManager(kernel_dirs=[kernel_dir]),
        ),
        timeout=300,
        kernel_name="component-notebook-check",
        resources={"metadata": {"path": str(work)}},
    )
    try:
        client.execute(cleanup_kc=True)
    finally:
        nbformat.write(notebook, destination / "executed.ipynb")


def verify(work: Path, destination: Path, name: str, order: dict, accent: str, version: str, rich_cells: bool):
    output = work / "output"
    runtime = json.loads((work / "notebook-runtime.json").read_text(encoding="utf-8"))
    assert runtime["version"] == version, runtime["version"]
    inspection = runtime["inspection"]
    assert not inspection.get("warnings"), inspection.get("warnings")
    assert not inspection.get("composition", {}).get("issues"), inspection.get("composition")
    assert inspection["profile"]["embedded_font_count"] >= 1

    pdf_path = output / "order.pdf"
    reader = PdfReader(pdf_path)
    page_texts = [normalize(page.extract_text() or "") for page in reader.pages]
    text = normalize(" ".join(page_texts))
    total = sum((Decimal(row["unit_price"]) * row["quantity"] for row in order["items"]), Decimal("0.00"))
    markers = [f'Order {order["number"]}', order["customer"], order["collection"],
               order["status"], f"USD {total:,.2f}", "Please retain this copy with your shipment."]
    for marker in markers:
        assert normalize(marker) in text, (name, marker)
    for row in order["items"]:
        assert normalize(row["item"]) in text, (name, row["item"])
    assert len(reader.pages) == inspection["page_count"] == runtime["preview_count"]
    if name == "long":
        assert len(reader.pages) >= 2, "Long order did not paginate"
        for page_text in page_texts:
            if "Edition" in page_text:
                assert all(label in page_text for label in ("Item", "Quantity", "Amount")), "Missing repeated table heading"
    else:
        assert len(reader.pages) == 1, (name, len(reader.pages))
    if not order["items"]:
        assert "No items in this order." in text

    styled = (output / "order.styled.html").read_text(encoding="utf-8")
    unstyled = (output / "order.unstyled.html").read_text(encoding="utf-8")
    for markup in (styled, unstyled):
        parsed = Markup(markup)
        assert "dispatch-note" in parsed.classes
        for marker in markers:
            assert normalize(marker) in normalize(" ".join(parsed.text)), (name, marker, "HTML")
        assert not any(tag == "script" for tag, attrs in parsed.elements)
        assert not any(key.lower().startswith("on") for tag, attrs in parsed.elements for key in attrs)
        assert not any(tag == "studio" for tag, attrs in parsed.elements), "Customer data became HTML"
        if rich_cells:
            assert parsed.cell_strong_text == [row["item"] for row in order["items"]], (name, "Rich item cells lost their content or order")
            assert not any(tag == "notebooks" for tag, attrs in parsed.elements), "Rich cell text became HTML"
    assert any(tag == "style" for tag, attrs in Markup(styled).elements)
    assert not any(tag == "style" or "style" in attrs or
                   (tag == "link" and attrs.get("rel") == "stylesheet")
                   for tag, attrs in Markup(unstyled).elements)

    native_previews = [f"order-page-{n}.png" for n in range(1, len(reader.pages) + 1)]
    expected_files = ["order.pdf", "order.styled.html", "order.unstyled.html", *native_previews]
    with ZipFile(output / "component-order.zip") as archive:
        assert set(archive.namelist()) == set(expected_files)
        for filename in expected_files:
            assert archive.read(filename) == (output / filename).read_bytes(), filename
    for filename in [*expected_files, "component-order.zip"]:
        shutil.copyfile(output / filename, destination / filename)
    for filename in native_previews:
        assert (destination / filename).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")

    colour = tuple(int(accent[i:i + 2], 16) for i in (1, 3, 5))
    colour_pixels = 0
    characters_checked = 0
    independent_texts = []
    document = pdfium.PdfDocument(pdf_path)
    try:
        assert len(document) == len(reader.pages)
        for index in range(len(document)):
            page = document[index]
            textpage = page.get_textpage()
            independent_texts.append(normalize(textpage.get_text_range()))
            width, height = page.get_size()
            for number in range(textpage.count_chars()):
                char = textpage.get_text_range(number, 1)
                if char.isspace() or not char:
                    continue
                x0, y0, x1, y1 = textpage.get_charbox(number)
                assert x0 >= -0.5 and y0 >= -0.5 and x1 <= width + 0.5 and y1 <= height + 0.5, (
                    name, index + 1, repr(char), (x0, y0, x1, y1), (width, height))
                characters_checked += 1
            bitmap = page.render(scale=110 / 72)
            image = bitmap.to_pil().convert("RGB")
            colour_pixels += sum(pixel == colour for pixel in image.get_flattened_data())
            image.save(destination / f"pdfium-page-{index + 1}.png")
            image.close()
            bitmap.close()
            textpage.close()
            page.close()
    finally:
        document.close()
    independent_text = normalize(" ".join(independent_texts))
    for marker in markers + [row["item"] for row in order["items"]]:
        assert normalize(marker) in independent_text, (name, marker, "PDFium")
    assert colour_pixels > 50, (name, "Requested accent absent from rendered PDF", colour_pixels)

    result = {
        "name": name, "pages": len(reader.pages), "row_count": len(order["items"]),
        "total": f"{total:.2f}", "pdf_sha256": sha256(pdf_path.read_bytes()).hexdigest(),
        "text_markers": markers, "font_count": inspection["profile"]["embedded_font_count"],
        "accent": accent, "accent_pixels": colour_pixels,
        "independent_char_bounds_checked": characters_checked,
        "repeat_pdf_identical": runtime["repeat_pdf_identical"],
        "direct_pdf_identical": runtime["direct_pdf_identical"],
        "zip_files": expected_files, "static_styled_and_unstyled_html": True,
        "rich_cell_components_checked": rich_cells,
        "artifact_hashes": {f: sha256((destination / f).read_bytes()).hexdigest() for f in expected_files},
    }
    write(destination / "verification.json", result)
    write(destination / "inspection.json", inspection)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "target/component-notebook")
    parser.add_argument("--channel", choices=tuple(CHANNELS), default="alpha3")
    parser.add_argument("--check-downloads", action="store_true", help="Check the published sample files against the executed notebook")
    args = parser.parse_args()
    version, folder = CHANNELS[args.channel]
    source_path = ROOT / "examples" / folder / "bootstrap_components.ipynb"
    out = args.out.resolve()
    assert not (out / "verification.json").exists(), "Use a new output directory to retain prior evidence"
    out.mkdir(parents=True, exist_ok=True)
    source = nbformat.read(source_path, as_version=4)
    nbformat.validate(source)
    assert all(not c.outputs and c.execution_count is None for c in source.cells if c.cell_type == "code")
    assert len({c.id for c in source.cells}) == len(source.cells)
    original_order = {}
    exec(next(c.source for c in source.cells if c.id == "order-data"), {}, original_order)
    default = original_order["order"]
    edited = deepcopy(default)
    edited.update(number="1051", customer="Moss & Fern <Studio>", status="Packed")
    edited["items"][0]["quantity"] = 32
    edited["items"][1]["item"] = "Personalized note cards"
    if args.channel in {"alpha5", "alpha6", "alpha6-r1"}:
        edited["items"][0]["item"] = "Studio <notebooks> & cards"
    long = deepcopy(default)
    long["items"] = [{"item": f"Edition {n:02d} / art print", "quantity": 1, "unit_price": "9.50"}
                     for n in range(1, 73)]
    empty = deepcopy(default)
    empty["items"] = []
    cases = [("default", default, "#205b47", 30), ("edited", edited, "#763c96", 26),
             ("long", long, "#205b47", 30), ("empty-after-long", empty, "#205b47", 30)]
    reports = []
    work = out / "work"
    work.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fullbleed-component-notebook-") as kernel_dir:
        spec = Path(kernel_dir) / "component-notebook-check"
        spec.mkdir()
        write(spec / "kernel.json", {
            "argv": [sys.executable, "-I", "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "Component notebook check", "language": "python",
        })
        for index, (name, order, accent, title_size) in enumerate(cases):
            notebook = deepcopy(source)
            for cell in notebook.cells:
                if index and cell.id == "install-fullbleed":
                    cell.metadata.setdefault("tags", []).append("skip-execution")
                if index and cell.id == "order-data":
                    cell.source = f"order = {order!r}"
                if index and cell.id == "style-controls":
                    cell.source = f"accent = {accent!r}\ntitle_size = {title_size!r}"
            destination = out / name
            destination.mkdir()
            execute(notebook, work, destination, kernel_dir)
            report = verify(work, destination, name, order, accent, version, args.channel in {"alpha5", "alpha6", "alpha6-r1"})
            reports.append(report)
            print(json.dumps({"case": name, "pages": report["pages"], "ok": True}), flush=True)
    assert len({r["pdf_sha256"] for r in reports}) == len(reports)
    # The same working directory is reused: the short rerun must leave old long
    # previews out of its download even when those files remain on disk.
    assert (work / "output/order-page-2.png").exists()
    assert "order-page-2.png" not in reports[-1]["zip_files"]
    if args.check_downloads:
        assets = ROOT / "docs/assets" / folder
        manifest = json.loads((assets / "verification.json").read_text(encoding="utf-8"))
        assert manifest["notebook_sha256"] == sha256(source_path.read_bytes()).hexdigest()
        assert (assets / "bootstrap_components.ipynb").read_bytes() == source_path.read_bytes()
        for filename, digest in manifest["downloads"].items():
            assert sha256((assets / filename).read_bytes()).hexdigest() == digest, filename
        for filename in ("order.pdf", "order.styled.html", "order.unstyled.html"):
            assert (assets / filename).read_bytes() == (out / "default" / filename).read_bytes(), filename
        assert [r["pdf_sha256"] for r in reports] == [r["pdf_sha256"] for r in manifest["cases"]]
    result = {
        "ok": True, "checked_at": datetime.now(timezone.utc).isoformat(),
        "notebook": source_path.relative_to(ROOT).as_posix(),
        "notebook_sha256": sha256(source_path.read_bytes()).hexdigest(),
        "runtime_version": version, "install_cell_executed": True,
        "published_downloads_match": args.check_downloads,
        "cases": reports, "stale_pages_excluded_from_download": True,
        "tools": {name: importlib.metadata.version(name) for name in
                  ("nbformat", "nbclient", "ipykernel", "pypdf", "pypdfium2", "Pillow")},
        "scope": "Executed Jupyter cells and independent PDF/HTML/ZIP checks. Hosted Colab runtime and download UI, exhaustive CSS/browser parity and standards conformance are not evaluated.",
    }
    write(out / "verification.json", result)
    print(json.dumps({"ok": True, "cases": len(reports), "pages": sum(x["pages"] for x in reports)}))


if __name__ == "__main__":
    main()
