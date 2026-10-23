"""Check the actual Yew exports in an isolated Chromium session."""
import argparse
from datetime import datetime, timezone
from functools import partial
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--chromium", type=Path)
args = parser.parse_args()
root, output = args.root.resolve(), args.output.resolve()
assert not output.exists()
output.mkdir(parents=True)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f"http://127.0.0.1:{server.server_port}"
checks = []
try:
    with sync_playwright() as p:
        options = {"headless": True}
        if args.chromium:
            options["executable_path"] = str(args.chromium.resolve())
        browser = p.chromium.launch(**options)
        try:
            for viewport in ({"width": 1280, "height": 1000}, {"width": 390, "height": 844}):
                context = browser.new_context(viewport=viewport)
                try:
                    for name, filename in (("default", "document.html"), ("default", "unstyled.html"),
                                           ("long", "document.html"), ("escaped", "document.html")):
                        page = context.new_page()
                        errors, failed_responses = [], []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.on("response", lambda response: failed_responses.append(response.url) if response.status >= 400 else None)
                        response = page.goto(f"{base}/{name}/{filename}", wait_until="networkidle", timeout=30000)
                        assert response.status == 200
                        page.evaluate("document.fonts.ready")
                        assert not errors and not failed_responses
                        assert page.locator("script, img").count() == 0
                        assert page.evaluate("typeof window.fullbleedInjected") == "undefined"
                        styled = filename == "document.html"
                        state = page.evaluate("""() => {
                            const region = document.querySelector('.table-scroll');
                            const header = document.querySelector('.masthead');
                            return {
                                documentWidth: document.documentElement.scrollWidth,
                                viewportWidth: document.documentElement.clientWidth,
                                background: getComputedStyle(header).backgroundColor,
                                tableWidth: region.scrollWidth,
                                regionWidth: region.clientWidth,
                                inter: document.fonts.check('16px Inter'),
                                serif: document.fonts.check('16px "DM Serif Display"'),
                                stylesheetCount: document.styleSheets.length
                            };
                        }""")
                        if styled:
                            assert state["documentWidth"] <= state["viewportWidth"] + 1, state
                            assert state["background"] == "rgb(24, 59, 63)"
                            assert state["inter"] and state["serif"] and state["stylesheetCount"] == 1
                            if viewport["width"] < 600:
                                region = page.get_by_role("region", name="Schedule table")
                                region.focus()
                                for _ in range(5):
                                    page.keyboard.press("ArrowRight")
                                page.wait_for_function("document.querySelector('.table-scroll').scrollLeft > 0")
                                region.evaluate("""el => new Promise(resolve => {
                                    let previous = -1, stable = 0;
                                    function frame() {
                                        const current = el.scrollLeft;
                                        stable = current === previous ? stable + 1 : 0;
                                        previous = current;
                                        if (stable >= 6) resolve();
                                        else requestAnimationFrame(frame);
                                    }
                                    frame();
                                })""")
                                region.evaluate("el => { el.scrollTo({left: 0, behavior: 'instant'}); el.blur(); }")
                                page.wait_for_function("document.querySelector('.table-scroll').scrollLeft === 0")
                        else:
                            assert state["stylesheetCount"] == 0
                        assert page.locator("tr.level").count() == (64 if name == "long" else 12)
                        if name == "escaped":
                            assert page.get_by_role("heading", name="Riverstone <Spring> & Friends", exact=True).count() == 1
                            assert "<script> window.fullbleedInjected" in page.locator("body").inner_text()
                        page.evaluate("window.scrollTo(0, 0)")
                        image = f"{name}-{'styled' if styled else 'unstyled'}-{viewport['width']}.png"
                        page.screenshot(path=str(output / image), full_page=name != "long")
                        if name == "long":
                            page.locator("footer").scroll_into_view_if_needed()
                            page.screenshot(path=str(output / image.replace('.png', '-end.png')))
                        pdf_response = context.request.get(f"{base}/{name}/document.pdf")
                        assert pdf_response.status == 200
                        assert sha256(pdf_response.body()).digest() == sha256((root / name / "document.pdf").read_bytes()).digest()
                        checks.append(dict(name=name, styled=styled, viewport=viewport, state=state,
                                           pdf_download_bytes_equal=True, screenshot=image))
                        page.close()
                finally:
                    context.close()
            record = dict(ok=True, at=datetime.now(timezone.utc).isoformat(), chromium=browser.version,
                          checks=checks, visual_review_pending=True)
            (output / "verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(dict(ok=True, checks=len(checks), chromium=browser.version)), flush=True)
        finally:
            browser.close()
finally:
    server.shutdown()
    server.server_close()
