"""Exercise the real guide downloads and the delivered standalone HTML."""
from argparse import ArgumentParser
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright
from pypdf import PdfReader


def main(site, out, base_url=None):
    out.mkdir(parents=True, exist_ok=False)
    assets = site / "assets/pandas-components"
    checks, downloads, errors = [], {}, []
    server = None

    class Handler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

    if not base_url:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site)))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base_url = f"http://127.0.0.1:{server.server_port}/"

    def check(name, value):
        assert value, name
        checks.append(name)

    record = {"url": base_url, "checks": checks, "downloads": downloads, "errors": errors}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome")
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            record["browser"] = browser.version
            try:
                for width, scheme in ((1440, "light"), (390, "light"), (390, "dark")):
                    page.set_viewport_size({"width": width, "height": 1000})
                    page.emulate_media(color_scheme=scheme)
                    page.goto(base_url.rstrip("/") + "/guides/pandas-components/", wait_until="networkidle")
                    if scheme == "dark" and page.locator("body").get_attribute("data-md-color-scheme") != "slate":
                        page.locator('label[title="Switch to dark mode"]').click()
                    expect(page.locator("body")).to_have_attribute("data-md-color-scheme", "slate" if scheme == "dark" else "default")
                    expect(page.get_by_role("heading", level=1)).to_contain_text("pandas reports with Python components")
                    expect(page.locator(".md-content")).to_contain_text("2.6.0a9")
                    check(f"guide fits {width}px {scheme}", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
                    expect(page.locator(".md-content img").first).to_be_visible()
                    check(f"PDF preview loads {width}px {scheme}", page.locator(".md-content img").first.evaluate("img => img.complete && img.naturalWidth > 0"))
                    page.screenshot(path=str(out / f"guide-{width}-{scheme}.png"), animations="disabled")
                    if scheme == "dark":
                        continue
                    for label, filename in (("Download the PDF", "report.pdf"), ("Get the runnable source", "project.zip"),
                                            ("Download both HTML exports", "html-exports.zip")):
                        with page.expect_download() as pending:
                            page.get_by_role("link", name=label, exact=True).click()
                        target = out / f"{width}-{filename}"
                        pending.value.save_as(target)
                        data = target.read_bytes()
                        check(f"{width}px {filename} download matches", data == (assets / filename).read_bytes())
                        downloads[f"{width}-{filename}"] = sha256(data).hexdigest()
                        if filename.endswith(".pdf"):
                            check(f"{width}px PDF has three pages", len(PdfReader(target).pages) == 3)
                with ZipFile(out / "1440-html-exports.zip") as archive:
                    names = set(archive.namelist())
                    assert names == {"fullbleed-pandas-html/" + name for name in
                                     ("report.html", "report-unstyled.html", "fonts/Inter-Variable.ttf", "fonts/Inter-OFL.txt")}
                    archive.extractall(out)
                page.emulate_media(color_scheme="light")
                page.set_viewport_size({"width": 1280, "height": 1000})
                for plain, filename in ((False, "report.html"), (True, "report-unstyled.html")):
                    page.goto((out / "fullbleed-pandas-html" / filename).as_uri(), wait_until="load")
                    page.evaluate("document.fonts.ready")
                    check(f"{filename} has all records", page.locator("table tbody tr").count() == 40)
                    expect(page.get_by_role("heading", level=1)).to_have_text("The product edit.")
                    check(f"{filename} retains ledger class", page.locator("table.ledger").count() == 1)
                    check(f"{filename} has no scripts", page.locator("script").count() == 0)
                    if plain:
                        check("unstyled export has no CSS", page.locator("style, [style]").count() == 0)
                    else:
                        check("bundled Inter loads", page.evaluate("document.fonts.check('12px Inter')"))
                        check("styled table header is green", page.locator("th").first.evaluate("el=>getComputedStyle(el).backgroundColor") == "rgb(23, 62, 53)")
                        check("styled export fits desktop", page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"))
                    page.screenshot(path=str(out / filename.replace(".html", ".png")), animations="disabled")
                check("no uncaught browser errors", not errors)
                record["ok"] = True
            except Exception:
                page.screenshot(path=str(out / "failure.png"), full_page=True)
                raise
            finally:
                context.close()
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        (out / "verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": record["ok"], "checks": len(checks), "downloads": len(downloads)}), flush=True)


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-url")
    args = parser.parse_args()
    main(args.site.resolve(), args.out.resolve(), args.base_url)
