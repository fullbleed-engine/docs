"""Check the deployed artifact's internal links and essential search metadata."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import sys


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.canonical = None
        self.description = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag in {"a", "img", "script", "link"}:
            url = attrs.get("href") or attrs.get("src")
            if url:
                self.links.append(url)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
        if tag == "meta" and attrs.get("name") == "description":
            self.description = attrs.get("content")


root = Path(sys.argv[1]).resolve()
pages = {}
failures = []
for path in root.rglob("*.html"):
    page = Page()
    page.feed(path.read_text(encoding="utf-8"))
    pages[path] = page
for path, page in pages.items():
    for url in page.links:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
            continue
        dest = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
        if dest.is_dir():
            dest /= "index.html"
        if not dest.exists():
            failures.append(f"{path.relative_to(root)}: missing {url}")
        elif parsed.fragment and dest in pages and unquote(parsed.fragment) not in pages[dest].ids:
            failures.append(f"{path.relative_to(root)}: missing anchor {url}")
for key in ["index.html", "getting-started/quickstart/index.html", "examples/index.html"]:
    page = pages.get(root / key)
    if not page or not page.canonical or not page.description:
        failures.append(f"{key}: missing canonical URL or description")
if not (root / "sitemap.xml").exists() or not (root / "robots.txt").exists():
    failures.append("Missing sitemap.xml or robots.txt")
if failures:
    raise SystemExit("\n".join(failures))
print(f"Checked {len(pages)} HTML pages: internal paths, anchors, and search metadata passed")
