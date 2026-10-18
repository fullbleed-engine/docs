"""Check the comparison guide, code tabs and real source download in a fresh browser."""
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
import re
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "site")
    parser.add_argument("--out", type=Path, default=ROOT / "target/showcase-authoring-ui")
    parser.add_argument("--browser", default="chrome")
    parser.add_argument("--base-url")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    server = None
    if args.base_url:
        base = args.base_url.rstrip("/")
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(args.site.resolve())))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
    manifest = json.loads((ROOT / "docs/assets/showcase-authoring-alpha5/source.json").read_text(encoding="utf-8"))
    cases = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, channel=args.browser)
            try:
                for name, width, height in (("desktop", 1440, 1000), ("mobile", 390, 844), ("narrow-mobile", 320, 740)):
                    context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
                    try:
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        response = page.goto(base + "/guides/showcase-authoring/", wait_until="networkidle")
                        assert response.status == 200
                        page.get_by_role("heading", level=1, name=re.compile(r"^One design, two authoring paths")).wait_for()
                        assert page.locator("body").inner_text().count(manifest["engine_version"]) >= 2
                        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                        page.screenshot(path=str(args.out / f"{name}-guide.png"), animations="disabled")
                        page.locator(".tabbed-labels label").filter(has_text=re.compile(r"^HTML$")).click()
                        assert page.locator(".tabbed-block:visible").inner_text().find('class="kicker"') >= 0
                        page.screenshot(path=str(args.out / f"{name}-html.png"), animations="disabled")
                        page.locator(".tabbed-labels label").filter(has_text=re.compile(r"^Python components$")).click()
                        assert "InvoiceField(" in page.locator(".tabbed-block:visible").inner_text()
                        page.screenshot(path=str(args.out / f"{name}-components.png"), animations="disabled")
                        with page.expect_download() as downloaded:
                            page.get_by_role("link", name="Download both source versions", exact=True).click()
                        download = downloaded.value
                        destination = args.out / f"{name}-project.zip"
                        download.save_as(str(destination))
                        assert sha256(destination.read_bytes()).hexdigest() == manifest["zip_sha256"]
                        for filename in ("invoice-html.pdf", "invoice-components.pdf", "report-html.pdf", "report-components.pdf"):
                            href = f"/assets/showcase-authoring-alpha5/{filename}"
                            assert page.locator(f'a[href$="{filename}"]').count() >= 1
                            pdf = context.request.get(base + href)
                            assert pdf.status == 200 and pdf.body() == (ROOT / "docs" / href.lstrip("/")).read_bytes()
                        section = page.locator("#edit-with-a-live-pdf-preview")
                        section.evaluate("element => element.scrollIntoView({block: 'start'})")
                        assert "python examples/design_showcase/preview.py" in page.locator("main").inner_text()
                        preview = page.locator('img[src$="preview-desktop.png"]')
                        preview.evaluate("image => image.decode()")
                        assert preview.evaluate("image => image.naturalWidth > 0")
                        page.screenshot(path=str(args.out / f"{name}-live-preview.png"), animations="disabled")
                        page.get_by_text("What an authoring error looks like", exact=True).click()
                        example = page.locator('img[src$="preview-error-mobile.png"]')
                        example.evaluate("image => image.decode()")
                        example.scroll_into_view_if_needed()
                        assert example.is_visible()
                        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
                        page.screenshot(path=str(args.out / f"{name}-live-error.png"), animations="disabled")
                        assert not errors, errors
                        cases.append(dict(viewport=name, width=width, source_zip_download=True,
                                          code_tabs=True, pdf_links=4, live_preview_commands=True,
                                          live_preview_images=2, document_overflow=False, page_errors=errors))
                    finally:
                        context.close()
            finally:
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    result = dict(ok=True, base_url=base, source_commit=manifest["source_commit"], cases=cases)
    (args.out / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "viewports": len(cases), "zip_downloads": len(cases)}))


if __name__ == "__main__":
    main()
