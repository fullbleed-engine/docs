"""Exercise the compiled Yew example's data, PDF and static HTML boundaries."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from pypdf import PdfReader
import pypdfium2 as pdfium

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--project", type=Path, required=True)
parser.add_argument("--metadata", type=Path, required=True)
args = parser.parse_args()
OUT = args.output.resolve()
assert not OUT.exists()
OUT.mkdir(parents=True)
PROJECT = args.project.resolve()
build = json.loads(args.metadata.read_text(encoding="utf-8"))
EXE = Path(build["executable"])
assert sha256(EXE.read_bytes()).hexdigest() == build["executable_sha256"]
source = json.loads((PROJECT / "data.json").read_text(encoding="utf-8"))

class HtmlDocument(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.text, self.stylesheets = [], [], []
        self.classes = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append(tag)
        if "class" in a:
            self.classes.append(a["class"])
        if tag == "link":
            self.stylesheets.append(a)
    def handle_data(self, text):
        self.text.append(text)

def normal(text):
    return " ".join(text.split())

records = []
def render(name, data):
    input_path = OUT / (name + ".json")
    input_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    destination = OUT / name
    result = subprocess.run([str(EXE), str(input_path), str(destination)],
                            text=True, encoding="utf-8", capture_output=True, timeout=90)
    (OUT / (name + ".log")).write_text(result.stdout + result.stderr, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    pdf_path = destination / "document.pdf"
    reader = PdfReader(pdf_path)
    assert "/OpenAction" not in reader.trailer["/Root"]
    assert "/JavaScript" not in reader.trailer["/Root"].get("/Names", {})
    page_text = [normal(page.extract_text()) for page in reader.pages]
    all_text = " ".join(page_text)
    for field in ("title", "subtitle", "starting_stack", "table_size", "registration"):
        assert normal(data[field]) in all_text, field
    for note in data["notes"]:
        assert normal(note) in all_text, note
    styled, plain = HtmlDocument(), HtmlDocument()
    styled.feed((destination / "document.html").read_text(encoding="utf-8"))
    plain.feed((destination / "unstyled.html").read_text(encoding="utf-8"))
    assert styled.stylesheets == [{"rel": "stylesheet", "href": "style.css"}]
    assert not plain.stylesheets
    assert styled.text == plain.text and styled.classes == plain.classes
    assert "script" not in styled.tags and "script" not in plain.tags
    assert "style" not in plain.tags
    assert len(styled.classes) > len(data["rows"])
    for filename, digest in build["font_hashes"].items():
        assert sha256((destination / "fonts" / filename).read_bytes()).hexdigest() == digest
    document = pdfium.PdfDocument(str(pdf_path))
    visible_chars = 0
    for index, page in enumerate(document):
        width, height = page.get_size()
        assert abs(width - 595.276) < 0.02 and abs(height - 841.89) < 0.02
        text_page = page.get_textpage()
        for char_index in range(text_page.count_chars()):
            char = text_page.get_text_range(char_index, 1)
            if char.strip():
                left, bottom, right, top = text_page.get_charbox(char_index)
                assert left >= -0.1 and bottom >= -0.1 and right <= width + 0.1 and top <= height + 0.1
                visible_chars += 1
        bitmap = page.render(scale=1.2)
        bitmap.to_pil().save(destination / f"pdfium-{index + 1}.png")
        bitmap.close()
        text_page.close()
        page.close()
    document.close()
    records.append(dict(name=name, pages=len(reader.pages), visible_chars_within_page=visible_chars,
                        styled_and_unstyled_content_equal=True, no_javascript=True,
                        pdf_sha256=sha256(pdf_path.read_bytes()).hexdigest(),
                        font_notices_included=True))
    print(json.dumps(records[-1]), flush=True)
    return page_text

default_pages = render("default", source)
assert len(default_pages) == 1
render("repeat", source)
assert records[0]["pdf_sha256"] == records[1]["pdf_sha256"]
long = deepcopy(source)
long["title"] = "The extended rotation"
long["rows"] = []
for index in range(1, 65):
    long["rows"].append(dict(kind="level", number=index, minutes=20,
        game=f"ROTATION-{index:03d} · Seven-card stud hi-lo 8-or-better",
        stakes="1,200 / 2,400", ante="300"))
    if index % 8 == 0:
        long["rows"].append(dict(kind="break", minutes=15, label=f"INTERVAL-{index:03d}"))
long_pages = render("long", long)
assert len(long_pages) > 1
joined = " ".join(long_pages)
assert all(joined.count(f"ROTATION-{index:03d}") == 1 for index in range(1, 65))
assert all(joined.count(f"INTERVAL-{index:03d}") == 1 for index in range(8, 65, 8))
for page in long_pages:
    if "ROTATION-" in page:
        assert "Blinds / bets" in page and "Minutes" in page and "Ante" in page
escaped = deepcopy(source)
escaped["title"] = 'Riverstone <Spring> & Friends'
escaped["notes"].append('<script> window.fullbleedInjected = true; </script> <img src=x onerror=alert(1)>')
render("escaped", escaped)
escaped_html = HtmlDocument()
escaped_html.feed((OUT / "escaped/document.html").read_text(encoding="utf-8"))
assert not {"script", "img", "spring"}.intersection(escaped_html.tags)
assert escaped["notes"][-1] in escaped_html.text

invalid = deepcopy(source)
invalid["rows"][0]["minutes"] = "twenty"
invalid_path = OUT / "invalid.json"
invalid_path.write_text(json.dumps(invalid), encoding="utf-8")
negative = subprocess.run([str(EXE), str(invalid_path), str(OUT / "invalid")],
                          text=True, encoding="utf-8", capture_output=True, timeout=30)
assert negative.returncode != 0 and not (OUT / "invalid").exists()
before = (OUT / "default/document.pdf").read_bytes()
overwrite = subprocess.run([str(EXE), str(PROJECT / "data.json"), str(OUT / "default")],
                           text=True, encoding="utf-8", capture_output=True, timeout=30)
assert overwrite.returncode != 0 and (OUT / "default/document.pdf").read_bytes() == before
result = dict(ok=True, at=datetime.now(timezone.utc).isoformat(), packages=build["packages"],
              executable_sha256=build["executable_sha256"], documents=records,
              repeat_pdf_bytes_equal=True, long_rows_complete_once=True,
              long_table_headers_repeat=True, escaped_text_not_markup=True,
              invalid_data_rejected_before_output=True, existing_output_preserved=True,
              visual_review_pending=True,
              scope="Standalone Yew SSR fixtures; not an application integration or accessibility certification.")
(OUT / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"ok": True, "documents": len(records), "output": str(OUT)}), flush=True)
