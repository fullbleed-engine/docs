"""Check the notebook landing page and exact public downloads in a browser."""
import argparse
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", choices=["chrome", "chromium"], default="chrome")
    parser.add_argument("--base-url")
    parser.add_argument("--verify-published-source", action="store_true")
    args = parser.parse_args()
    root = args.site.resolve()
    args.out.mkdir(parents=True, exist_ok=True)
    folder = "component-notebook-alpha5"
    assets = root / "assets" / folder
    manifest = json.loads((assets / "verification.json").read_text(encoding="utf-8"))

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
            options = {"channel": "chrome"} if args.browser == "chrome" else {}
            browser = p.chromium.launch(**options)
            browser_version = browser.version
            for label, width, height in [("desktop", 1440, 1000), ("mobile", 390, 844), ("narrow-mobile", 320, 740)]:
                context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                response = page.goto(base + "/getting-started/component-notebook/", wait_until="networkidle")
                assert response.status == 200
                assert page.get_by_role("heading", name="Try Python components in a notebook", exact=False).is_visible()
                article = page.locator("article").inner_text()
                for value in ("Fullbleed 2.6.0a5", "fullbleed.ui.experimental", "no Bootstrap JavaScript",
                              "class_name", "Document(styles=...)", "Strong", "72-row", "four pages"):
                    assert value in article, value
                colab = page.get_by_role("link", name="Open in Colab", exact=True).get_attribute("href")
                source = page.get_by_role("link", name="View the source", exact=True).get_attribute("href")
                prefix = "https://colab.research.google.com/github/"
                assert colab.startswith(prefix)
                assert source == "https://github.com/" + colab[len(prefix):]
                revision = urlparse(source).path.split("/")[4]
                assert len(revision) == 40 and all(c in "0123456789abcdef" for c in revision)
                if args.verify_published_source and label == "desktop":
                    raw = context.request.get("https://raw.githubusercontent.com/" +
                                              source.removeprefix("https://github.com/").replace("/blob/", "/", 1))
                    assert raw.status == 200
                    assert sha256(raw.body()).hexdigest() == manifest["notebook_sha256"], "Colab's pinned source differs from the download"
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                preview = page.locator("article img")
                assert preview.count() == 1
                assert preview.evaluate("img => img.complete && img.naturalWidth > 0")
                page.screenshot(path=str(args.out / f"{label}-guide.png"), animations="disabled")
                with page.expect_download() as event:
                    page.get_by_role("link", name="Download the notebook", exact=True).click()
                download = event.value
                assert download.suggested_filename == "bootstrap_components.ipynb"
                saved = args.out / f"{label}-bootstrap_components.ipynb"
                download.save_as(saved)
                assert sha256(saved.read_bytes()).hexdigest() == manifest["notebook_sha256"]
                preview.scroll_into_view_if_needed()
                page.screenshot(path=str(args.out / f"{label}-preview.png"), animations="disabled")
                downloads = []
                for filename, title in (("order.pdf", "Open the sample PDF"), ("order.styled.html", "Open styled HTML"),
                                        ("order.unstyled.html", "Open unstyled HTML"), ("verification.json", "verification record")):
                    link = page.get_by_role("link", name=title, exact=True)
                    response = context.request.get(link.evaluate("a => a.href"))
                    assert response.status == 200, filename
                    assert response.body() == (assets / filename).read_bytes(), filename
                    downloads.append({"file": filename, "sha256": sha256(response.body()).hexdigest()})
                for filename in ("order.styled.html", "order.unstyled.html"):
                    response = page.goto(base + "/assets/" + folder + "/" + filename, wait_until="networkidle")
                    assert response.status == 200 and page.title() == "Order 1048"
                    assert page.locator("script").count() == 0
                    assert page.locator(".dispatch-note").count() == 1
                    if filename == "order.styled.html":
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        assert "Arial" in page.locator("body").evaluate("el => getComputedStyle(el).fontFamily")
                        page.screenshot(path=str(args.out / f"{label}-styled-html.png"), animations="disabled")
                    if "unstyled" in filename:
                        assert page.locator("style, [style], link[rel=stylesheet]").count() == 0
                for path in ("/", "/getting-started/notebook/", "/guides/bootstrap-components-preview/"):
                    response = page.goto(base + path, wait_until="networkidle")
                    assert response.status == 200
                    link = page.locator("article").get_by_role("link", name="Try the component notebook", exact=False)
                    assert link.count() == 1
                    assert urlparse(link.evaluate("a => a.href")).path == "/getting-started/component-notebook/"
                assert not errors, errors
                results.append({"viewport": label, "width": width, "colab_url": colab, "source_url": source,
                                "notebook_download": manifest["notebook_sha256"], "downloads": downloads,
                                "entry_pages_checked": 3, "styled_and_unstyled_html": True, "page_errors": errors})
                context.close()
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report = {"ok": True, "browser": browser_version, "base_url": base,
              "pinned_public_source_verified": args.verify_published_source,
              "notebook_sha256": manifest["notebook_sha256"], "cases": results,
              "scope": "Landing page at three widths, actual notebook download, exact sample files, static HTML exports and three discovery links. Hosted Colab execution and its download UI are not covered."}
    (args.out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "viewports": len(results), "notebook_sha256": manifest["notebook_sha256"]}))


if __name__ == "__main__":
    main()
