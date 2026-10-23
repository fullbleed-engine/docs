"""Inspect styled and unstyled kit exports in an isolated Chromium session."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", type=Path, default=ROOT / "target/component-kits/render")
    parser.add_argument("--out", type=Path, default=ROOT / "target/component-kits/browser")
    parser.add_argument("--chromium", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    records, errors = [], []
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(args.render.resolve())))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, **(
                {"executable_path": str(args.chromium)} if args.chromium else {}))
            browser_version = browser.version
            for viewport, width in (("desktop", 1280), ("mobile", 390)):
                context = browser.new_context(viewport={"width": width, "height": 900})
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                for variant in ("default", "billing-brand", "impact-brand", "local-override"):
                    for kind in ("html", "unstyled.html"):
                        url = f"http://127.0.0.1:{server.server_port}/{variant}.{kind}"
                        response = page.goto(url, wait_until="networkidle")
                        assert response.status == 200
                        assert page.get_by_role("heading", level=1).count() == 1
                        assert page.get_by_text("$24,600", exact=True).count() == 1
                        assert page.get_by_text("128", exact=True).count() == 1
                        assert page.locator("script").count() == 0
                        data = page.evaluate("""() => {
                            const card = selector => {
                                const element = document.querySelector(selector);
                                const p = [...element.querySelectorAll('p')];
                                const rect = element.getBoundingClientRect();
                                return {background: getComputedStyle(element).backgroundColor,
                                    colors: p.map(x => getComputedStyle(x).color),
                                    x: rect.x, y: rect.y, width: rect.width, height: rect.height};
                            };
                            return {billing: card('.billing-summary'), impact: card('.impact-summary'),
                                overflow: document.documentElement.scrollWidth > innerWidth,
                                styles: document.querySelectorAll('style,[style]').length};
                        }""")
                        assert not data["overflow"], (viewport, variant, kind, data)
                        if kind == "html":
                            billing = "rgb(112, 71, 161)" if variant == "billing-brand" else "rgb(49, 91, 147)"
                            impact = {"impact-brand": "rgb(163, 78, 33)",
                                      "local-override": "rgb(155, 61, 100)"}.get(variant, "rgb(25, 113, 94)")
                            assert data["billing"]["colors"][1] == billing, data
                            assert data["impact"]["colors"][1] == impact, data
                            if viewport == "desktop":
                                assert abs(data["billing"]["y"] - data["impact"]["y"]) < 1
                            else:
                                assert data["impact"]["y"] >= data["billing"]["y"] + data["billing"]["height"]
                            page.screenshot(path=str(args.out / f"{viewport}-{variant}.png"), full_page=True)
                        else:
                            assert data["styles"] == 0, data
                        records.append({"viewport": viewport, "variant": variant, "export": kind, **data})
                context.close()
            browser.close()
        assert not errors, errors
        result = {"ok": True, "browser": browser_version, "checks": records,
                  "scope": "Actual static HTML exports; no browser/PDF pagination or pixel-parity claim."}
        (args.out / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "browser": browser_version, "exports_checked": len(records)}))
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


if __name__ == "__main__":
    main()
