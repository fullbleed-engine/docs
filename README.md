# Fullbleed documentation site

Published at https://fullbleed-engine.github.io/docs/ using GitHub Pages.

```bash
python -m pip install -r requirements.txt
python -m mkdocs build --strict
python tools/check_site.py site
python -m mkdocs serve
```

Changes to `main` build, check internal links and metadata, then deploy through `.github/workflows/docs.yml`. Pull requests run the same build checks without deployment.

## Updating a release

Reference pages come from the engine repository's release tag. Keep hand-authored introductions and guides here; import API, CLI, CSS, architecture, print, and performance references with:

```bash
python tools/sync_reference.py --source /path/to/fullbleed-official --ref v2.4.0
```

`docs/reference-source.json` records the exact source commit. Use a built, installed release wheel to rerun examples and review the final PDFs and previews before replacing downloadable artifacts. `docs/assets/examples/verification.json` records the checks performed on published examples.

When changing the canonical domain, update `site_url`, `docs/robots.txt`, and this README, configure GitHub Pages, and verify DNS, HTTPS, sitemap URLs, and redirects. Keep the GitHub Pages URL until the custom domain is working.

Fullbleed is MIT licensed. Do not publish unsupported performance comparisons, standards conformance claims, or stale licensing statements. Retain old page URLs through the redirect map when consolidating reference material.
