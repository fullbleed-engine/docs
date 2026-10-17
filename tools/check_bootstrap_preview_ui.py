"""Check the Bootstrap guide, visible downloads and standalone HTML in a browser."""
import argparse
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", choices=["chrome", "chromium"], default="chrome")
    parser.add_argument("--executable-path", type=Path)
    parser.add_argument("--base-url")
    args = parser.parse_args()
    root = args.site.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    assets = root / "assets/bootstrap-alpha4"
    source = json.loads((assets / "source.json").read_text(encoding="utf-8"))
    manifest = json.loads((assets / "verification.json").read_text(encoding="utf-8"))
    assert source["source_commit"] == manifest["source_commit"]
    assert source["zip_sha256"] == manifest["source_zip_sha256"]

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(root), **kw)

        def log_message(self, *a):
            pass

    server = None
    if args.base_url:
        base = args.base_url.rstrip("/")
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
    results = []
    try:
        with sync_playwright() as p:
            options = ({"executable_path": str(args.executable_path)} if args.executable_path else
                       {"channel": "chrome"} if args.browser == "chrome" else
                       {"executable_path": p.chromium.executable_path})
            browser = p.chromium.launch(**options)
            browser_version = browser.version
            for label, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844), ("narrow-mobile", 320, 740)]:
                context = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                response = page.goto(base + "/guides/bootstrap-components-preview/", wait_until="networkidle")
                assert response.status == 200
                assert page.get_by_role("heading", name="Bootstrap components, authored in Python", exact=False).is_visible()
                article = page.locator("article").inner_text()
                for value in ("Opt-in alpha 2.6.0a4", "fullbleed.ui.experimental",
                              "static, including HTML export", "class_name",
                              "include_styles=True", "include_styles=False", "python first_document.py",
                              'python -m pip install --pre "fullbleed==2.6.0a4"'):
                    assert value in article, value
                assert page.get_by_role("link", name="alpha release", exact=True).get_attribute("href") == source["engine_wheels"]["release_url"]
                legacy = page.get_by_role("link", name="pinned preview kit", exact=True)
                retained = context.request.get(legacy.evaluate("element => element.href"))
                assert retained.status == 200
                assert sha256(retained.body()).hexdigest() == "cc9464999e64def4ce361b70c1826fef5a8a40c24b2abc02a839c6622878dbe4"
                older_alpha = page.get_by_role("link", name="alpha 1 kit", exact=True)
                retained_alpha = context.request.get(older_alpha.evaluate("element => element.href"))
                assert retained_alpha.status == 200
                assert sha256(retained_alpha.body()).hexdigest() == "ccdf8344fcbfd7b0afba9727287c9301fa8932e9a9ae97a1a67f5fca42059683"
                older_alpha2 = page.get_by_role("link", name="alpha 2 kit", exact=True)
                retained_alpha2 = context.request.get(older_alpha2.evaluate("element => element.href"))
                assert retained_alpha2.status == 200
                assert sha256(retained_alpha2.body()).hexdigest() == "5ec857a9d467ec5e43ce2a9c8ebc8f901bbb941eae4f23d9c9a661d381819520"
                older_alpha3 = page.get_by_role("link", name="alpha 3 kit", exact=True)
                retained_alpha3 = context.request.get(older_alpha3.evaluate("element => element.href"))
                assert retained_alpha3.status == 200
                assert sha256(retained_alpha3.body()).hexdigest() == "a0554fe19ab9927e34969dcf35b605e923b544c39ebc51449e0b0814efa47b60"
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                images = page.locator("article img").evaluate_all("items => items.map(img => ({src: img.src, loaded: img.complete && img.naturalWidth > 0}))")
                assert images and all(item["loaded"] for item in images)
                page.screenshot(path=str(args.out / f"{label}-guide.png"), animations="disabled")
                downloads = []
                links = {"project.zip": "Download the Bootstrap kit", "report.pdf": "Open the report PDF",
                         "forms.pdf": "form PDF", "report.styled.html": "Open the styled HTML",
                         "report.unstyled.html": "Compare unstyled HTML", "catalog.html": "Browse the HTML catalog"}
                for name, title in links.items():
                    link = page.get_by_role("link", name=title, exact=True)
                    result = context.request.get(link.evaluate("element => element.href"))
                    assert result.status == 200, name
                    assert result.body() == (assets / name).read_bytes(), name
                    if name.endswith(".pdf"):
                        assert result.headers["content-type"].split(";")[0] == "application/pdf"
                    downloads.append({"file": name, "sha256": sha256(result.body()).hexdigest()})
                with page.expect_navigation(wait_until="networkidle"):
                    page.get_by_role("link", name="Browse the HTML catalog", exact=True).click()
                assert page.title() == "Static Bootstrap 5.0.0 catalog"
                assert page.locator('[id^="sample-"]').count() == 27
                assert page.locator("script").count() == 0
                assert page.get_by_role("textbox", name="Company", exact=True).input_value() == "Northstar Studio"
                assert page.locator(".fb-bs-spinner").first.evaluate("element => getComputedStyle(element).animationName") == "none"
                if width >= 390:
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.screenshot(path=str(args.out / f"{label}-catalog.png"), animations="disabled")
                response = page.goto(base + "/assets/bootstrap-alpha4/catalog.unstyled.html", wait_until="networkidle")
                assert response.status == 200
                assert page.locator("style, [style], link[rel=stylesheet], script").count() == 0
                assert page.locator('[id^="sample-"]').count() == 27
                assert page.get_by_role("textbox", name="Company", exact=True).input_value() == "Northstar Studio"
                assert not errors, errors
                results.append({"viewport": label, "width": width, "guide_overflow": False,
                                "images": len(images), "downloads": downloads, "catalog_groups": 27,
                                "styled_and_unstyled_states": True, "page_errors": errors})
                context.close()
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report = {"ok": True, "browser": browser_version, "base_url": base,
              "source_commit": source["source_commit"], "cases": results,
              "scope": "Guide at three widths, loaded PDF preview, exact files fetched through visible links, catalog navigation and styled/unstyled form state. No interactive Bootstrap behavior or PDF viewer is claimed."}
    (args.out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "viewports": len(results), "source_commit": source["source_commit"]}))


if __name__ == "__main__":
    main()
