"""Exercise the downloadable app with independent PDF readers and real Chrome downloads."""
from collections import Counter
from datetime import date
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
import argparse
import csv
import importlib.util
import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
import urllib.request
import zipfile

import pypdfium2 as pdfium
from pypdf import PdfReader
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/streamlit-report"


def verify(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    checks = []
    evidence = {"schema": "fullbleed.streamlit-verification.v1", "ok": False,
                "platform": platform.system(), "python": platform.python_version(),
                "versions": {key: version(key) for key in ["fullbleed", "streamlit", "streamlit-pdf", "pypdf", "pypdfium2", "playwright"]},
                "checks": checks, "scope": "Synthetic downloaded project, local HTTP and browser sessions; no hosted deployment or standards-conformance claim."}

    def check(name, condition):
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    def inspect(data, name, rows, pages=None):
        (out / (name + ".pdf")).write_bytes(data)
        reader = PdfReader(BytesIO(data))
        check(name + " PDF page count", len(reader.pages) == pages if pages else 1 <= len(reader.pages) <= 12)
        check(name + " A4 geometry", all(abs(float(p.mediabox.width) - 595.276) < 1 and abs(float(p.mediabox.height) - 841.89) < 1 for p in reader.pages))
        check(name + " vector charts and selectable text", all(not list(p.images) for p in reader.pages))
        texts = ["\n".join(p.extract_text() for p in reader.pages)]
        with pdfium.PdfDocument(data) as document:
            independent = []
            for n in range(len(document)):
                page = document[n]
                textpage = page.get_textpage()
                independent.append(textpage.get_text_range())
                boxes = [textpage.get_charbox(i) for i in range(textpage.count_chars())]
                painted = [b for b in boxes if b[2] > b[0] and b[3] > b[1]]
                check(f"{name} page {n+1} text bounds", bool(painted) and all(l >= 0 and b >= 0 and r <= page.get_width()+.2 and t <= page.get_height()+.2 for l, b, r, t in painted))
                page.render(scale=96/72).to_pil().save(out / f"{name}-pdfium-{n+1}.png")
                textpage.close()
                page.close()
            texts.append("\n".join(independent))
        expected_ids = Counter(f"R{r.row:03}" for r in rows)
        orders, cents = sum(r.orders for r in rows), sum(r.cents for r in rows)
        for engine, text in zip(["pypdf", "pdfium"], texts):
            (out / f"{name}-{engine}.txt").write_text(text, encoding="utf-8")
            check(name + " all row IDs exactly once in " + engine, Counter(re.findall(r"R\d{3}", text)) == expected_ids)
            compact = "".join(text.split())
            check(name + " exact totals in " + engine, "".join(report.money(cents).split()) in compact and f"{orders:,}orders" in compact)
            for row in rows:
                wanted = f"R{row.row:03}{row.day.isoformat()}{row.region}{row.channel}{row.orders:,}{report.money(row.cents).removeprefix('USD ')}"
                check(f"{name} row {row.row} values in {engine}", "".join(wanted.split()) in compact)
            check(name + " no replacement glyph in " + engine, "\ufffd" not in text)
        return {"pages": len(reader.pages), "sha256": sha256(data).hexdigest(), "bytes": len(data)}

    def render(rows, name, title="Northstar Supply / Quarterly review", start=None, end=None, regions=None, channel=None):
        start = start or min(row.day for row in rows)
        end = end or max(row.day for row in rows)
        regions = regions or sorted({row.region for row in rows})
        html, css = report.document(rows, title, start, end, regions, channel)
        result = report.render_report(html, css)
        check(name + " deterministic replay", report.render_report(html, css)["pdf"] == result["pdf"])
        info = inspect(result["pdf"], name, rows)
        return result, info

    try:
        manifest = json.loads((ASSETS / "source.json").read_text())
        archive_path = args.zip or ASSETS / "project.zip"
        check("exact downloadable ZIP checksum", sha256(archive_path.read_bytes()).hexdigest() == manifest["zip_sha256"])
        extracted = out / "project with spaces"
        with zipfile.ZipFile(archive_path) as z:
            expected = {"fullbleed-streamlit-report/" + row["path"] for row in manifest["files"]}
            check("exact archive member set", set(z.namelist()) == expected and len(z.namelist()) == len(expected))
            for row in manifest["files"]:
                name = "fullbleed-streamlit-report/" + row["path"]
                check("safe archive path: " + row["path"], not Path(name).is_absolute() and ".." not in Path(name).parts and ":" not in name and "\\" not in name)
                data = z.read(name)
                check("source hash: " + row["path"], data == (ROOT / "examples/streamlit-report" / row["path"]).read_bytes() and sha256(data).hexdigest() == row["sha256"])
            z.extractall(extracted)
        project = extracted / "fullbleed-streamlit-report"
        for line in (project / "requirements.txt").read_text().splitlines():
            package, pin = line.split("==")
            check("installed pin: " + package, version(package) == pin)
        spec = importlib.util.spec_from_file_location("streamlit_report_fixture", project / "report.py")
        report = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = report
        spec.loader.exec_module(report)
        sample = (project / "sales.csv").read_bytes()
        rows = report.load_sales(sample)
        check("sample's independently specified totals", len(rows) == 36 and report.totals(rows) == (2628, 22209930))
        normal, normal_info = render(rows, "sample")
        check("sample uses two complete pages", normal_info["pages"] == 2)
        selected = report.select_sales(rows, date(2026, 8, 3), date(2026, 8, 17), ["East", "North", "South"], "Online")
        check("inclusive date and channel selection", [r.row for r in selected] == [15, 17, 19])
        render(selected, "filtered", start=date(2026, 8, 3), end=date(2026, 8, 17), channel="Online")
        literal = report.load_sales(b'date,region,channel,orders,revenue_usd\n2026-07-06,"<b>East & West</b>","${region}",0,0.00\n')
        render(literal, "literal-zero", title="<b>Literal & ${name}</b>")
        long_csv = "date,region,channel,orders,revenue_usd\n" + "".join(f"2026-07-06,Region {i%6} prolonged label,Channel {i%6} long label,1,{i}.00\n" for i in range(1, 251))
        long_rows = report.load_sales(long_csv.encode())
        _, long_info = render(long_rows, "long")
        check("250 records paginate", long_info["pages"] > 2)
        invalid = {"empty": b"", "oversize": b"x" * 65537, "invalid UTF8": b"\xff", "wrong header": b"a,b\n1,2\n"}
        header = b"date,region,channel,orders,revenue_usd\n"
        for name, tail in {"negative orders": "2026-07-06,East,Online,-1,1.00", "NaN": "2026-07-06,East,Online,1,NaN",
                           "exponent": "2026-07-06,East,Online,1,1e5", "extra precision": "2026-07-06,East,Online,1,1.234",
                           "invalid date": "2026-02-30,East,Online,1,1.00", "extra field": "2026-07-06,East,Online,1,1.00,extra",
                           "missing field": "2026-07-06,East,Online,1", "control character": "2026-07-06,Ea\x00st,Online,1,1.00",
                           "large revenue": "2026-07-06,East,Online,1,1000000.01"}.items():
            invalid[name] = header + tail.encode() + b"\n"
        invalid["too many records"] = header + b"2026-07-06,East,Online,1,1.00\n" * 251
        invalid["too many groups"] = header + "".join(f"2026-07-06,Region{i},Online,1,1.00\n" for i in range(7)).encode()
        for name, data in invalid.items():
            try:
                report.load_sales(data)
            except ValueError:
                check("reject " + name, True)
            else:
                check("reject " + name, False)

        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        url = f"http://127.0.0.1:{port}"
        browser_errors, external_requests = [], []
        with (out / "server.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.address", "127.0.0.1",
                                        "--server.port", str(port), "--server.headless", "true"], cwd=project,
                                       env={**os.environ, "PYTHONUTF8": "1"}, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 45
                while True:
                    try:
                        if urllib.request.urlopen(url + "/_stcore/health", timeout=1).status == 200:
                            break
                    except Exception:
                        if process.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError("Streamlit did not become healthy; see server.log")
                        time.sleep(.2)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(**({"channel": "chrome"} if args.browser == "chrome" else {}), headless=True)
                    evidence["browser"] = browser.version

                    def context():
                        ctx = browser.new_context(viewport={"width": 1365, "height": 1100})
                        def route(request):
                            if request.request.url.startswith((url + "/", "data:", "blob:")):
                                request.continue_()
                            else:
                                external_requests.append(request.request.url.split("?")[0])
                                request.abort()
                        ctx.route("**/*", route)
                        page = ctx.new_page()
                        page.on("pageerror", lambda exc: browser_errors.append(str(exc)))
                        page.goto(url)
                        page.get_by_role("button", name="Prepare PDF", exact=True).wait_for(timeout=30000)
                        return ctx, page

                    def prepare(page):
                        button = page.get_by_role("button", name="Prepare PDF", exact=True)
                        button.focus()
                        button.press("Enter")
                        page.get_by_role("button", name="Download prepared PDF", exact=True).wait_for(timeout=30000)
                        viewer = page.get_by_role("region", name="Sales report for the prepared selection", exact=True)
                        painted_canvas(page, viewer.locator('[data-page-number="1"] canvas'))
                        return viewer

                    def painted_canvas(page, canvas):
                        canvas.wait_for(timeout=30000)
                        page.wait_for_function('''canvas => {
                            if (!canvas.width || !canvas.height) return false;
                            const data=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
                            let ink=0;for(let i=0;i<data.length;i+=4)if(data[i]<180&&data[i+1]<180&&data[i+2]<180&&data[i+3]>100)ink++;
                            return ink > 300;
                        }''', arg=canvas.element_handle(), timeout=30000)

                    def download(page, name):
                        with page.expect_download() as event:
                            page.get_by_role("button", name="Download prepared PDF", exact=True).click()
                        item = event.value
                        check(name + " download filename", item.suggested_filename == "sales-brief.pdf")
                        data = Path(item.path()).read_bytes()
                        response = page.request.get(item.url)
                        check(name + " HTTP media type and bytes", response.ok and response.headers["content-type"].split(";")[0] == "application/pdf" and response.body() == data)
                        return data

                    ctx, page = context()
                    viewer = prepare(page)
                    check("browser output matches the direct renderer", download(page, "browser-sample") == normal["pdf"])
                    page.get_by_role("heading", name="Sales report studio", exact=True).scroll_into_view_if_needed()
                    page.screenshot(path=str(out / "app-desktop.png"))
                    page_two = viewer.locator('[data-page-number="2"]')
                    page_two.scroll_into_view_if_needed()
                    painted_canvas(page, page_two.locator('canvas'))
                    header_pixels = page_two.locator('canvas').evaluate('''canvas => {
                        const w=canvas.width,h=canvas.height;
                        const data=canvas.getContext('2d').getImageData(Math.floor(w*.06),Math.floor(h*.04),Math.floor(w*.24),Math.floor(h*.023)).data;
                        let ink=0;for(let i=0;i<data.length;i+=4)if(data[i]<180&&data[i+1]<180&&data[i+2]<180&&data[i+3]>100)ink++;
                        return ink;
                    }''')
                    check("actual PDF viewer paints the repeated page-two masthead", header_pixels > 30)
                    evidence["viewer_page_two_masthead_pixels"] = header_pixels
                    viewer.screenshot(path=str(out / "pdf-viewer-page-two.png"))
                    check("viewing page two preserves the prepared PDF", download(page, "preview-page-two") == normal["pdf"])
                    page.get_by_label("Channel", exact=True).click()
                    page.get_by_role("option", name="Only Online", exact=True).click()
                    expect(page.get_by_role("button", name="Download prepared PDF", exact=True)).to_have_count(0)
                    check("channel change clears prepared download", True)
                    dates = page.locator('input[type="date"]')
                    dates.nth(0).fill("2026-08-03")
                    dates.nth(0).press("Tab")
                    dates.nth(1).fill("2026-08-17")
                    dates.nth(1).press("Tab")
                    prepare(page)
                    inspect(download(page, "browser-filtered"), "browser-filtered", selected, 2)
                    page.get_by_label("Report name", exact=True).fill("A new report name")
                    page.get_by_label("Report name", exact=True).press("Tab")
                    expect(page.get_by_role("button", name="Download prepared PDF", exact=True)).to_have_count(0)
                    check("report name change clears prepared download", True)
                    prepare(page)
                    first_session_pdf = download(page, "session-one")
                    ctx2, second = context()
                    expect(second.get_by_role("button", name="Download prepared PDF", exact=True)).to_have_count(0)
                    check("second browser session has no prepared report", True)
                    second_csv = header + b"2026-10-01,Private branch,Online,1,19.99\n"
                    second.locator('input[type="file"]').set_input_files({"name": "second.csv", "mimeType": "text/csv", "buffer": second_csv})
                    expect(second.get_by_text("USD 19.99", exact=True)).to_be_visible()
                    prepare(second)
                    inspect(download(second, "session-two"), "session-two", report.load_sales(second_csv), 2)
                    check("second session does not replace first session bytes", download(page, "session-one-again") == first_session_pdf)
                    second.locator('input[type="file"]').set_input_files({"name": "invalid.csv", "mimeType": "text/csv", "buffer": invalid["NaN"]})
                    expect(second.get_by_text("CSV record 1 needs nonnegative USD revenue with at most two decimals.", exact=True)).to_be_visible()
                    expect(second.get_by_role("button", name="Download prepared PDF", exact=True)).to_have_count(0)
                    check("invalid upload clears the old PDF", True)
                    second.locator('input[type="file"]').set_input_files({"name": "restored.csv", "mimeType": "text/csv", "buffer": sample})
                    expect(second.get_by_text("USD 222,099.30", exact=True)).to_be_visible()
                    prepare(second)
                    check("valid upload recovers the sample", download(second, "recovered") == normal["pdf"])
                    second.get_by_label("Report name", exact=True).fill("Missing glyph \U0001f984")
                    second.get_by_label("Report name", exact=True).press("Tab")
                    second.get_by_role("button", name="Prepare PDF", exact=True).click()
                    expect(second.get_by_text("A character is missing from the report fonts. Add a suitable font before exporting this data.", exact=True)).to_be_visible()
                    expect(second.get_by_role("button", name="Download prepared PDF", exact=True)).to_have_count(0)
                    check("missing glyph prevents a damaged download", True)
                    second.get_by_label("Report name", exact=True).fill("Northstar Supply / Quarterly review")
                    second.get_by_label("Report name", exact=True).press("Tab")
                    prepare(second)
                    check("font coverage error recovers after correction", download(second, "glyph-recovered") == normal["pdf"])
                    second.set_viewport_size({"width": 390, "height": 844})
                    expect(second.get_by_test_id("stSidebar")).not_to_be_in_viewport()
                    second.get_by_role("button", name="Download prepared PDF", exact=True).scroll_into_view_if_needed()
                    second.screenshot(path=str(out / "app-mobile.png"))
                    check("mobile document has no horizontal overflow", second.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
                    check("mobile download stays valid", download(second, "mobile") == normal["pdf"])
                    check("no browser JavaScript errors", not browser_errors)
                    check("no off-site browser asset requests", not external_requests)
                    ctx2.close()
                    ctx.close()
                    browser.close()
            finally:
                process.terminate()
                process.wait(timeout=15)
        evidence.update(sample=normal_info, long_report=long_info,
                        project_zip_sha256=manifest["zip_sha256"], browser_errors=browser_errors,
                        external_requests=external_requests)
        if args.refresh_assets:
            (ASSETS / "report.pdf").write_bytes(normal["pdf"])
            for n in range(1, normal_info["pages"] + 1):
                (ASSETS / f"page-{n}.png").write_bytes((out / f"sample-pdfium-{n}.png").read_bytes())
            (ASSETS / "app.png").write_bytes((out / "app-desktop.png").read_bytes())
        else:
            check("sample PDF matches the published specimen", normal["pdf"] == (ASSETS / "report.pdf").read_bytes())
        evidence["ok"] = True
        if args.refresh_assets:
            (ASSETS / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8", newline="\n")
        return evidence
    finally:
        (out / "verification.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "output/streamlit-verification")
    parser.add_argument("--zip", type=Path)
    parser.add_argument("--browser", choices=["chrome", "chromium"], default="chrome")
    parser.add_argument("--refresh-assets", action="store_true")
    result = verify(parser.parse_args())
    print(json.dumps({"ok": result["ok"], "checks": len(result["checks"]), "sample": result["sample"], "long_report": result["long_report"]}))
