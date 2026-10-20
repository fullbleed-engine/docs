# SPDX-License-Identifier: MIT
"""Exercise data boundaries and inspect actual saved PDFs with independent readers."""
import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys

import pandas as pd
from pandas.testing import assert_frame_equal
from pypdf import PdfReader
import pypdfium2 as pdfium

from data import load_products
from report import render

HERE = Path(__file__).resolve().parent


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags, self.attrs = [], []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attrs.extend(attrs)


def check_pdf(path, skus, out):
    reader = PdfReader(path)
    assert reader.trailer["/Root"].get("/StructTreeRoot")
    texts = [page.extract_text() for page in reader.pages]
    text = "\n".join(texts)
    observed = re.findall(r"\b(?:GL|TEST)-\d{3}\b", text)
    assert observed == list(skus), (path, observed)
    for i, content in enumerate(texts, 1):
        # pypdf separates individually positioned, letter-spaced header glyphs.
        assert "GRIDLINE/OPERATIONS" in re.sub(r"\s+", "", content), (path, i, "header")
        assert "GRIDLINE / FICTIONAL DATA" in content, (path, i, "footer")
        assert f"{i} / {len(texts)}" in content, (path, i, "page total")
        if re.search(r"\b(?:GL|TEST)-\d{3}\b", content):
            assert all(label in content for label in ("SKU", "Product", "Category", "Units", "Net sales", "Last restock"))
    out.mkdir(parents=True, exist_ok=True)
    with pdfium.PdfDocument(path) as doc:
        for i, page in enumerate(doc):
            width, height = page.get_size()
            assert abs(width - 841.89) < .1 and abs(height - 595.276) < .1
            textpage = page.get_textpage()
            for n in range(textpage.count_chars()):
                if not textpage.get_text_range(n, 1).strip():
                    continue
                left, bottom, right, top = textpage.get_charbox(n)
                assert 5 <= left <= right <= width - 5 and 5 <= bottom <= top <= height - 5, (path, i, n, "outside page")
            page.render(scale=1).to_pil().save(out / f"page-{i + 1}.png")
            textpage.close()
            page.close()
    return {"pages": len(reader.pages), "sha256": sha256(path.read_bytes()).hexdigest(), "rows": len(skus)}, text


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    frame = load_products(HERE / "products.csv")
    before = frame.copy(deep=True)
    cases = {"sample": frame, "one": frame.iloc[:1].copy()}
    mixed = frame.iloc[:3].copy()
    mixed.loc[0, "product"] = '<script>alert("literal")</script> & München — café'
    mixed.loc[1, "product"] = "A long, descriptive product name that wraps across several lines in the ledger. " * 5
    mixed.loc[0, "net_sales_cents"] = -12050
    mixed.loc[1, "last_restock"] = pd.NaT
    mixed.loc[2, "units"] = 0
    cases["mixed"] = mixed
    many = pd.concat([frame] * 3, ignore_index=True)
    many["sku"] = pd.Series([f"TEST-{i:03}" for i in range(1, 121)], dtype="string")
    cases["many"] = many
    results = {}
    for name, value in cases.items():
        snapshot = value.copy(deep=True)
        dest = out / name
        report = render(value, dest)
        assert_frame_equal(value, snapshot)
        result, text = check_pdf(dest / "report.pdf", value["sku"], dest / "independent-previews")
        assert report["page_count"] == result["pages"]
        styled_html = (dest / "report.html").read_text(encoding="utf-8")
        plain_html = (dest / "report-unstyled.html").read_text(encoding="utf-8")
        styled, plain = Markup(styled_html), Markup(plain_html)
        assert "style" in styled.tags and "style" not in plain.tags
        assert all(key != "style" for key, _ in plain.attrs)
        assert any(key == "class" and "ledger" in value.split() for key, value in plain.attrs)
        assert all("script" not in markup.tags for markup in (styled, plain))
        if name == "sample":
            assert result["pages"] == 3
            assert "$150,236.25" in text and "6,040" in text and "München" in text
        if name == "mixed":
            assert "-$120.50" in text and "Not recorded" in text and 'alert("literal")' in text
            assert "&lt;script&gt;" in styled_html
        results[name] = result
    assert_frame_equal(frame, before)
    # A fresh interpreter and output directory must produce the same saved PDF.
    replay = out / "fresh-process"
    run = subprocess.run([sys.executable, str(HERE / "report.py"), "--out", str(replay)],
                         text=True, capture_output=True, check=True)
    assert json.loads(run.stdout)["pdf_sha256"] == results["sample"]["sha256"]
    assert (replay / "report.pdf").read_bytes() == (out / "sample/report.pdf").read_bytes()

    raw = pd.read_csv(HERE / "products.csv", keep_default_na=False)
    invalid = {"empty": raw.iloc[:0], "missing-column": raw.drop(columns="sku"),
               "duplicate": pd.concat([raw, raw.iloc[:1]], ignore_index=True)}
    for name, column, value in (("blank-product", "product", "  "), ("missing-units", "units", ""),
                                ("negative-units", "units", -1), ("fractional-cents", "net_sales_cents", 1.5),
                                ("bad-date", "last_restock", "2026-99-99")):
        bad = raw.astype(object).copy()
        bad.loc[0, column] = value
        invalid[name] = bad
    for name, bad in invalid.items():
        path = out / f"invalid-{name}.csv"
        bad.to_csv(path, index=False)
        try:
            load_products(path)
        except (ValueError, TypeError):
            pass
        else:
            raise AssertionError(f"Accepted invalid CSV: {name}")
    evidence = {"ok": True, "cases": results, "invalid_inputs_rejected": list(invalid),
                "fresh_process_pdf_identical": True, "input_frames_unchanged": True,
                "html_styled_and_unstyled_checked": True,
                "scope": "Saved-PDF text, row order, repeated headings, page totals, page bounds, independent rasterization; no PDF/UA or browser-pagination claim."}
    (out / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "output/verification")
    main(parser.parse_args().out.resolve())
