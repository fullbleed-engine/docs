"""Check the downloaded project, dependency contracts and saved PDF pixels."""
import argparse
from hashlib import sha256
from html.parser import HTMLParser
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

import fullbleed
from fullbleed.components import AuthoringError, Document, Paragraph, Theme, style, token
from PIL import Image, ImageChops
from pypdf import PdfReader
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/component-kits"


class Html(HTMLParser):
    def __init__(self):
        super().__init__()
        self.styles = 0
        self.inline = 0
        self.scripts = 0
        self.classes = set()
        self.text = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.styles += tag == "style"
        self.inline += "style" in attrs
        self.scripts += tag == "script"
        self.classes.update(attrs.get("class", "").split())
        if tag in ("style", "script", "title"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("style", "script", "title"):
            self.hidden -= 1

    def handle_data(self, text):
        if not self.hidden:
            self.text.append(text)


def color_box(image, color):
    rgb = image.convert("RGB")
    channels = ImageChops.difference(rgb, Image.new("RGB", rgb.size, color)).split()
    distance = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    return distance.point(lambda value: 255 if value == 0 else 0).getbbox()


def contained(inner, outer, tolerance=1):
    return (inner and outer and inner[0] >= outer[0] - tolerance
            and inner[1] >= outer[1] - tolerance and inner[2] <= outer[2] + tolerance
            and inner[3] <= outer[3] + tolerance)


def expect_error(call, code):
    try:
        call()
    except AuthoringError as error:
        assert error.code == code, error.to_dict()
        return error.to_dict()
    raise AssertionError(f"Expected {code}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "target/component-kits")
    parser.add_argument("--check-published", action="store_true")
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    project = out / "project"
    project.mkdir(exist_ok=True)
    manifest = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
    assert version("fullbleed") == manifest["fullbleed"] == "2.6.0a14"
    archive_path = ASSETS / "project.zip"
    assert sha256(archive_path.read_bytes()).hexdigest() == manifest["zip_sha256"]
    with zipfile.ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {"fullbleed-component-kits/" + r["path"] for r in manifest["files"]}
        for record in manifest["files"]:
            name = record["path"]
            assert Path(name).name == name
            data = archive.read("fullbleed-component-kits/" + name)
            assert sha256(data).hexdigest() == record["sha256"]
            (project / name).write_bytes(data)
    rendered = out / "render"
    run = subprocess.run([sys.executable, str(project / "report.py"), "--output", str(rendered)],
                         cwd=project, capture_output=True, text=True, encoding="utf-8", timeout=90)
    (out / "render.log").write_text(run.stdout + run.stderr, encoding="utf-8")
    assert run.returncode == 0, run.stdout + run.stderr
    guide = (ROOT / "docs/guides/component-kits.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", guide, re.S)
    assert len(blocks) == 3
    snippets = "\n\n".join(blocks)
    (out / "guide-snippets.py").write_text(snippets, encoding="utf-8")
    snippet_run = subprocess.run([sys.executable, "-c", snippets], cwd=project,
                                 capture_output=True, text=True, encoding="utf-8", timeout=30)
    (out / "guide-snippets.log").write_text(snippet_run.stdout + snippet_run.stderr, encoding="utf-8")
    assert snippet_run.returncode == 0, snippet_run.stdout + snippet_run.stderr
    assert (project / "cards.html").exists() and (project / "cards.unstyled.html").exists()
    sys.path.insert(0, str(project))
    from billing import BillingPalette, billing_kit
    from impact import IMPACT_DEFAULTS, Impact
    from report import report, renderer, VARIANTS

    Balance = billing_kit()
    plain = Balance("Balance", "$10", "A concrete kit")
    assert plain.required_tokens == ()
    Document(plain).compile()
    impact = Impact("Impact", "12", "A token kit")
    assert set(impact.required_tokens) == set(IMPACT_DEFAULTS)
    assert "12" in Document(impact).to_html(include_styles=False)
    errors = {"missing_theme": expect_error(lambda: Document(impact).compile(), "theme.missing")}
    for missing in IMPACT_DEFAULTS:
        incomplete = {k: v for k, v in IMPACT_DEFAULTS.items() if k != missing}
        errors[missing] = expect_error(lambda: Document(impact, theme=Theme(incomplete)).compile(), "theme.missing")
        assert missing in errors[missing]["message"]
    errors["unknown_part"] = expect_error(lambda: impact.with_parts(number=style(color="red")), "style.part")
    # A deliberately colliding name has one document-wide binding; no automatic scope.
    first = Theme({"accent": "#315b93"})
    combined = first.with_values({"accent": "#a34e21"})
    collision = Document(Paragraph("A", style=style(color=token("accent"))),
                         Paragraph("B", style=style(color=token("accent"))), theme=combined)
    assert dict(first.values)["accent"] == "#315b93"
    assert dict(combined.values)["accent"] == "#a34e21"
    collision_html = collision.to_html(include_styles=True)
    assert "#a34e21" in collision_html and "#315b93" not in collision_html
    original = report().to_html(include_styles=True)
    billing_kit(BillingPalette(accent="#7047a1"))("New", "$20", "Separate kit")
    impact_before = impact.to_html(include_styles=True, theme=Theme(IMPACT_DEFAULTS))
    impact.with_parts(value=style(color="#9b3d64"))
    assert impact.to_html(include_styles=True, theme=Theme(IMPACT_DEFAULTS)) == impact_before
    assert report().to_html(include_styles=True) == original
    assert impact.required_tokens == tuple(sorted(IMPACT_DEFAULTS))

    records, images = [], {}
    expected_text = ("$24,600", "128", "November action plan", "Member workshops",
                     "Community grants", "Studio access", "SYNTHETIC EXAMPLE")
    for variant in VARIANTS:
        path = rendered / f"{variant}.pdf"
        reader = PdfReader(path)
        assert len(reader.pages) == 1
        page = reader.pages[0]
        assert abs(float(page.mediabox.width) - 595.276) < 0.02
        assert abs(float(page.mediabox.height) - 841.890) < 0.02
        text = "".join(page.extract_text().split())
        assert all("".join(value.split()) in text for value in expected_text)
        inspection = fullbleed.inspect_pdf(str(path))
        assert inspection["ok"] and inspection["profile"]["embedded_font_count"] > 0
        trace = json.loads((rendered / f"{variant}.pagination.json").read_text(encoding="utf-8"))
        assert trace["ok"] and len(trace["pages"]) == 1
        assert trace["pages"][0]["text_overlap_count"] == 0
        assert report(variant).render_pdf(renderer()) == path.read_bytes()
        with pdfium.PdfDocument(str(path)) as pdf:
            bitmap = pdf[0].render(scale=1.5)
            image = bitmap.to_pil().convert("RGB")
            image.save(rendered / f"{variant}-1.png")
        images[variant] = image
        exports = []
        for suffix, styled_export in (("html", True), ("unstyled.html", False)):
            html = Html()
            html.feed((rendered / f"{variant}.{suffix}").read_text(encoding="utf-8"))
            assert not html.scripts
            assert {"billing-summary", "impact-summary", "report-metrics"} <= html.classes
            assert (html.styles > 0) if styled_export else (html.styles == 0 and html.inline == 0)
            content = "".join("".join(html.text).split())
            assert all("".join(value.split()) in content for value in expected_text)
            exports.append(content)
        assert exports[0] == exports[1]
        if args.check_published:
            for name in (f"{variant}.pdf", f"{variant}-1.png"):
                assert (rendered / name).read_bytes() == (ASSETS / name).read_bytes(), name
        records.append({"variant": variant, "pages": 1, "pdf_sha256": sha256(path.read_bytes()).hexdigest(),
                        "repeated_pdf_equal": True, "embedded_font": True, "text_overlaps": 0,
                        "required_tokens": list(report(variant).required_tokens)})
    base = images["default"]
    billing_region = color_box(base, "#edf2f9")
    impact_region = color_box(base, "#eaf5ef")
    value_region = color_box(base, "#19715e")
    differences = []
    for variant, allowed, accent in (("billing-brand", billing_region, "#7047a1"),
                                     ("impact-brand", impact_region, "#a34e21"),
                                     ("local-override", value_region, "#9b3d64")):
        changed = ImageChops.difference(base, images[variant]).getbbox()
        assert contained(changed, allowed), (variant, changed, allowed)
        assert color_box(images[variant], accent), (variant, accent)
        differences.append({"variant": variant, "changed_pixels_bbox": changed,
                            "allowed_region": allowed, "outside_region_identical": True})
    result = {"ok": True, "fullbleed": version("fullbleed"), "zip_sha256": manifest["zip_sha256"],
              "documents": records, "pdf_pixel_isolation": differences, "expected_errors": errors,
              "guide_python_blocks_executed": len(blocks), "guide_snippets_sha256": sha256(snippets.encode()).hexdigest(),
              "collision": "Document-wide name; later explicit theme value wins; original theme unchanged.",
              "published_assets_equal": args.check_published,
              "scope": "Maintainer-authored kit contracts; no independent-author or general conformance claim."}
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
