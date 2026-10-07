"""Verify the actual bilingual starter ZIP and PDFs with independent readers."""
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile

import pypdfium2 as pdfium
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/arabic-invoice"


def compact(text):
    return "".join(text.split())


def verify(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    extracted = out / "project with spaces"
    extracted.mkdir(exist_ok=False)
    checks, commands = [], []
    report = {"schema": "fullbleed.arabic-example-verification.v1", "ok": False,
              "engine": version("fullbleed"), "platform": platform.system(),
              "readers": {"pypdf": version("pypdf"), "pypdfium2": version("pypdfium2")},
              "checks": checks, "commands": commands}

    def check(name, passed):
        checks.append({"name": name, "passed": bool(passed)})
        if not passed:
            raise AssertionError(name)

    def run(label, arguments, expected=0):
        result = subprocess.run([sys.executable, "-I", *map(str, arguments)], cwd=project,
                                env={**os.environ, "PYTHONUTF8": "1", "PYTHONPATH": ""},
                                capture_output=True, text=True, encoding="utf-8", timeout=240)
        (out / (label + ".stdout.txt")).write_text(result.stdout, encoding="utf-8")
        (out / (label + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
        commands.append({"label": label, "exit": result.returncode})
        check(label + " exit", result.returncode == expected)
        return result

    try:
        check("required installed engine version", version("fullbleed") == "2.5.14")
        manifest = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
        archive_path = args.zip or ASSETS / "project.zip"
        check("ZIP hash matches the manifest", sha256(archive_path.read_bytes()).hexdigest() == manifest["zip_sha256"])
        with zipfile.ZipFile(archive_path) as archive:
            expected = {"arabic-invoice/" + item["path"] for item in manifest["files"]}
            check("exact expected ZIP file set", set(archive.namelist()) == expected)
            check("ZIP paths stay within the project", all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in expected))
            for item in manifest["files"]:
                data = archive.read("arabic-invoice/" + item["path"])
                check("source and hash: " + item["path"], data == (ROOT / "examples/arabic-invoice" / item["path"]).read_bytes() and sha256(data).hexdigest() == item["sha256"])
            archive.extractall(extracted)
        project = extracted / "arabic-invoice"
        run("render", ["render.py", "--out", out / "render"])
        run("replay", ["render.py", "--out", out / "replay"])
        pdf_path = out / "render/invoice.pdf"
        pdf = pdf_path.read_bytes()
        check("exact-input PDFs are byte-identical", pdf == (out / "replay/invoice.pdf").read_bytes())
        native_png = out / "render/preview/invoice_page1.png"
        check("exact-input previews are byte-identical", native_png.read_bytes() == (out / "replay/preview/invoice_page1.png").read_bytes())
        check("explicit fonts cover all sample glyphs", json.loads((out / "render/glyph-report.json").read_text(encoding="utf-8")) == [])
        reader = PdfReader(pdf_path)
        check("one A4 page", len(reader.pages) == 1 and abs(float(reader.pages[0].mediabox.width) - 595.276) < .2 and abs(float(reader.pages[0].mediabox.height) - 841.89) < .2)
        text = "\n".join(page.extract_text() for page in reader.pages)
        (out / "pypdf.txt").write_text(text, encoding="utf-8")
        for phrase in ["فاتورة", "نوى للتصميم", "شركة أفق", "NAWA STUDIO", "Ufuq Company", "NW-2048",
                       "2026-10-07", "2026-10-21", "Brand identity design", "Document templates", "Handover sessions",
                       "875.00", "325.00", "190.00", "1,390.00", "شكراً", "يُرجى"]:
            check("PDF text: " + phrase, compact(phrase) in compact(text))
        descriptors = []
        for ref in reader.pages[0]["/Resources"]["/Font"].values():
            font = ref.get_object()
            check("each font has a Unicode map", "/ToUnicode" in font)
            descriptor = font["/DescendantFonts"][0].get_object()["/FontDescriptor"].get_object()
            descriptors.append(str(descriptor["/FontName"]))
            check("font program embedded: " + descriptors[-1], "/FontFile2" in descriptor or "/FontFile3" in descriptor)
        check("regular and bold Arabic faces used", any("NotoSansArabic-Regular" in f for f in descriptors) and any("NotoSansArabic-Bold" in f for f in descriptors))
        document = pdfium.PdfDocument(pdf)
        page = document[0]
        textpage = page.get_textpage()
        other = textpage.get_text_range()
        (out / "pdfium.txt").write_text(other, encoding="utf-8")
        for phrase in ["NW-2048", "1,390.00", "2026-10-07", "2026-10-21", "شكراً", "يُرجى"]:
            check("independent PDFium text: " + phrase, compact(phrase) in compact(other))
        check("no injected bidi controls or replacement characters", not any(unicodedata.category(ch) == "Cf" or ch == "\ufffd" for ch in text + other))
        boxes = [textpage.get_charbox(index) for index in range(textpage.count_chars())]
        painted = [(l, b, r, t) for l, b, r, t in boxes if r > l and t > b]
        check("glyph boxes stay inside the A4 page", bool(painted) and all(l >= 0 and b >= 0 and r <= page.get_width() + .1 and t <= page.get_height() + .1 for l, b, r, t in painted))
        page.render(scale=110 / 72).to_pil().save(out / "pdfium.png")
        textpage.close()
        page.close()
        document.close()

        guide = (ROOT / "docs/guides/arabic-pdf.md").read_text(encoding="utf-8")
        snippets = re.findall(r"```python\n(.*?)```", guide, flags=re.S)
        check("one executable guide snippet", len(snippets) == 1)
        (project / "guide-snippet.py").write_text(snippets[0], encoding="utf-8")
        run("guide-snippet", ["guide-snippet.py"])
        guide_text = PdfReader(project / "arabic.pdf").pages[0].extract_text()
        check("guide renders marked Arabic and isolated fields", all(phrase in guide_text for phrase in ["مرحباً", "INV-2048", "2026-10-21"]))

        data = json.loads((project / "data.json").read_text(encoding="utf-8"))
        data["customer_ar"] = "مؤسسة بيان"
        data["customer_en"] = "Mira & Co <Design>"
        data["reference"] = "TEST-2049"
        data["items"] = [{"ar": "إعداد قالب مخصص", "en": "Custom template", "quantity": 2, "unit_cents": 12345}]
        edited = project / "edited.json"
        edited.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        css_path = project / "invoice.css"
        css_path.write_text(css_path.read_text(encoding="utf-8").replace("#213c37", "#25375d"), encoding="utf-8")
        run("edited", ["render.py", "--data", edited, "--out", out / "edited"])
        edited_pdf = (out / "edited/invoice.pdf").read_bytes()
        edited_text = "".join(page.extract_text() for page in PdfReader(out / "edited/invoice.pdf").pages)
        check("edited data and escaped HTML text reach PDF", all(compact(p) in compact(edited_text) for p in ["مؤسسة بيان", "Mira & Co <Design>", "TEST-2049", "246.90"]))
        check("new data and theme change the output", edited_pdf != pdf)
        check("integer cents calculate the edited total", json.loads((out / "edited/render.json").read_text())["total_cents"] == 24690)

        data["items"][0]["quantity"] = -1
        edited.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        invalid = run("invalid-quantity", ["render.py", "--data", edited, "--out", out / "invalid-quantity"], expected=1)
        check("invalid amounts fail before a PDF is written", "positive integer quantities" in invalid.stderr and not (out / "invalid-quantity/invoice.pdf").exists())
        data["items"][0]["quantity"] = 1
        data["customer_ar"] += " 字"
        edited.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        run("missing-glyph", ["render.py", "--data", edited, "--out", out / "missing-glyph"], expected=1)
        check("missing glyph is reported without a new PDF", bool(json.loads((out / "missing-glyph/glyph-report.json").read_text(encoding="utf-8"))) and not (out / "missing-glyph/invoice.pdf").exists())
        font_path = project / "fonts/NotoSansArabic-Regular.ttf"
        original_font = font_path.read_bytes()
        try:
            font_path.unlink()
            missing = run("missing-font", ["render.py", "--out", out / "missing-font"], expected=1)
            check("missing font has an explicit diagnostic", "Missing or changed project font asset" in missing.stderr)
            font_path.write_bytes(b"changed font")
            changed = run("changed-font", ["render.py", "--out", out / "changed-font"], expected=1)
            check("changed font is rejected before parsing", "Missing or changed project font asset" in changed.stderr)
        finally:
            font_path.write_bytes(original_font)

        report.update(ok=True, zip_sha256=manifest["zip_sha256"], pdf_sha256=sha256(pdf).hexdigest(),
                      native_png_sha256=sha256(native_png.read_bytes()).hexdigest(), fonts=descriptors,
                      total_cents=139000, pages=1)
        if args.update_assets:
            shutil.copyfile(pdf_path, ASSETS / "invoice.pdf")
            shutil.copyfile(native_png, ASSETS / "invoice.png")
            shutil.copyfile(out / "pdfium.png", ASSETS / "invoice-pdfium.png")
            (ASSETS / "verification.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        return report
    finally:
        (out / "verification.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output/arabic-verification")
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--update-assets", action="store_true")
    result = verify(parser.parse_args())
    print(json.dumps({"ok": result["ok"], "checks": len(result["checks"]), "pdf_sha256": result["pdf_sha256"]}))
