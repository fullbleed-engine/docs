"""Verify the styling tutorial, real notebook download and static HTML exports."""
from argparse import ArgumentParser
from hashlib import sha256
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--browser", choices=("chrome", "chromium"), default="chrome")
    parser.add_argument("--verify-published-source", action="store_true")
    args = parser.parse_args()
    root = args.site.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    asset_path = "/assets/styling-notebook-alpha10/"
    assets = root / asset_path.lstrip("/")
    manifest = json.loads((assets / "verification.json").read_text(encoding="utf-8"))
    assert manifest["ok"] and not manifest["visual_review_pending"]

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
            browser = p.chromium.launch(**({"channel": "chrome"} if args.browser == "chrome" else {}))
            try:
                for label, width, height in (("desktop", 1440, 1000), ("mobile", 390, 844), ("narrow", 320, 740)):
                    context = browser.new_context(viewport=dict(width=width, height=height), accept_downloads=True)
                    try:
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        response = page.goto(base + "/getting-started/component-styling/", wait_until="networkidle")
                        assert response.status == 200
                        article = page.locator("article")
                        assert article.get_by_role("heading", name="Make the components your own", exact=False).is_visible()
                        text = article.inner_text()
                        for marker in ("2.6.0a10", "class_name", "with_parts", "with_style", "to_html",
                                       "ACCENT", "TITLE_SIZE", "PANEL_BACKGROUND", "METRIC_COLOR", "FOLIO_COLOR",
                                       "23 PDF pages", "local Jupyter", "component-field-notes.zip"):
                            assert marker in text, marker
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        pictures = article.locator("img")
                        assert pictures.count() == 2
                        assert all(pictures.nth(i).evaluate("img => img.complete && img.naturalWidth > 0") for i in range(2))
                        colab = article.get_by_role("link", name="Open in Colab", exact=True).get_attribute("href")
                        source = article.get_by_role("link", name="View the pinned source", exact=True).get_attribute("href")
                        prefix = "https://colab.research.google.com/github/"
                        assert colab.startswith(prefix) and source == "https://github.com/" + colab[len(prefix):]
                        revision = urlparse(source).path.split("/")[4]
                        assert len(revision) == 40 and all(char in "0123456789abcdef" for char in revision)
                        if args.verify_published_source and label == "desktop":
                            raw = context.request.get("https://raw.githubusercontent.com/" +
                                source.removeprefix("https://github.com/").replace("/blob/", "/", 1))
                            assert raw.status == 200
                            assert sha256(raw.body()).hexdigest() == manifest["notebook_sha256"]
                        page.screenshot(path=str(out / f"{label}-guide.png"), animations="disabled")
                        with page.expect_download() as event:
                            article.get_by_role("link", name="Download the notebook", exact=True).click()
                        download = event.value
                        assert download.suggested_filename == "component_styling.ipynb"
                        assert download.failure() is None
                        saved = out / f"{label}-component_styling.ipynb"
                        download.save_as(saved)
                        assert sha256(saved.read_bytes()).hexdigest() == manifest["notebook_sha256"]
                        file_hashes = {}
                        for filename, digest in manifest["downloads"].items():
                            response = context.request.get(base + asset_path + filename)
                            assert response.status == 200, filename
                            assert sha256(response.body()).hexdigest() == digest, filename
                            assert response.body() == (assets / filename).read_bytes(), filename
                            file_hashes[filename] = digest
                        response = context.request.get(base + asset_path + "verification.json")
                        assert response.status == 200 and response.body() == (assets / "verification.json").read_bytes()
                        for styled in (True, False):
                            filename = "field-notes.styled.html" if styled else "field-notes.unstyled.html"
                            response = page.goto(base + asset_path + filename, wait_until="networkidle")
                            assert response.status == 200
                            assert page.title() == "Common Ground — Field notes"
                            assert page.locator("script").count() == 0
                            assert all(page.locator(tag).count() == 1 for tag in ("header", "main", "footer"))
                            assert page.locator(".folio").count() == 1
                            assert "[page] / [pages]" in page.locator("footer").inner_text()
                            if styled:
                                assert page.locator(".folio").evaluate("el => getComputedStyle(el).color") == "rgb(83, 102, 92)"
                                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                                assert "sans-serif" in page.locator("body").evaluate("el => getComputedStyle(el).fontFamily")
                                flows = page.locator("[data-fb-flow]")
                                assert flows.count() == 3
                                for index in range(flows.count()):
                                    assert flows.nth(index).evaluate("""el => {
                                        const css = getComputedStyle(el);
                                        const children = Array.from(el.children);
                                        return css.display === 'flex' && css.flexDirection === 'column' &&
                                            parseFloat(css.rowGap) > 0 && children.length > 1 &&
                                            children[1].getBoundingClientRect().top >
                                                children[0].getBoundingClientRect().bottom + 1;
                                    }""")
                            else:
                                assert page.locator("style, [style], link[rel=stylesheet]").count() == 0
                            page.screenshot(path=str(out / f"{label}-{'styled' if styled else 'unstyled'}-html.png"),
                                            animations="disabled", full_page=True)
                        for path, title in (
                            ("/", "Try the current styling notebook"),
                            ("/guides/component-preview-10/", "Try the styling notebook"),
                            ("/guides/python-components/", "edit the styling notebook"),
                        ):
                            response = page.goto(base + path, wait_until="networkidle")
                            assert response.status == 200
                            link = page.locator("article").get_by_role("link", name=title, exact=True)
                            assert link.count() == 1
                            assert urlparse(link.evaluate("a => a.href")).path == "/getting-started/component-styling/"
                        assert not errors, errors
                        results.append(dict(viewport=label, width=width, colab_url=colab, source_url=source,
                            actual_notebook_download=True, notebook_sha256=manifest["notebook_sha256"],
                            exact_downloads=file_hashes, styled_and_unstyled_html=True,
                            class_selector_computed_color="rgb(83, 102, 92)", discovery_links=3, page_errors=errors))
                    finally:
                        context.close()
                browser_version = browser.version
            finally:
                browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    result = dict(ok=True, base_url=base, browser=browser_version, cases=results,
        pinned_public_source_verified=args.verify_published_source,
        visual_review_pending=True,
        scope="Three landing-page widths, actual notebook downloads, exact PDF/HTML/evidence assets, CSS selector behavior in static HTML and three discovery links. Hosted Colab execution is not covered.")
    (out / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(ok=True, viewports=len(results), downloaded_notebooks=len(results))))


if __name__ == "__main__":
    main()
