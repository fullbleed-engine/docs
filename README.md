# Fullbleed documentation site

Published at https://docs.fullbleed.dev/ using GitHub Pages.

```bash
python -m pip install -r requirements.txt
rustup target add wasm32-wasip1
python tools/build_playground.py
node tools/verify_playground.mjs
python tools/build_browser_starter.py
python tools/build_react_starter.py
python tools/build_vue_starter.py
python -m mkdocs build --strict
python tools/check_site.py site
python -m mkdocs serve
```

Changes to `main` build, check internal links and metadata, then deploy through `.github/workflows/docs.yml`. Pull requests run the same build checks without deployment.

Building all browser demos needs Rust and Node 22.12 or newer. CI uses Rust
1.97.0 and Node 22. Its locked adapter compiles the published engine; it does not
modify or vendor the engine source. See [playground/README.md](playground/README.md)
for limits, privacy behavior, and native/WASI verification.

The browser, React, and Vue builds also create `edit-online.html` beside each
verified project ZIP. These plain HTML forms open the exact source files in
StackBlitz through the [POST API](https://developer.stackblitz.com/platform/api/post-api).
Keep the homepage and respective guides linked to these generated launchers so
package updates reach both the download and the online editor. All use
`tools/online_starter.html`; run `tools/check_online_starter.py` with `browser`,
`react`, or `vue` to verify the submitted files locally without creating
third-party projects.

## Updating a release

Reference pages come from the engine repository's release tag. Keep hand-authored introductions and guides here; import API, CLI, CSS, architecture, print, and performance references with:

```bash
python tools/sync_reference.py --source /path/to/fullbleed-official --ref v2.5.4
```

`docs/reference-source.json` records the exact source commit. Use a built, installed release wheel to rerun examples and review the final PDFs and previews before replacing downloadable artifacts. `docs/assets/examples/verification.json` records the checks performed on published examples.

Run `python -I tools/verify_quickstarts.py` in an environment with that reference
release installed. It executes the Python snippets directly from five introductory
pages, checks their PDF text and page counts, and exercises the documented project
commands. CI retains the PDFs, previews, and structured report. Older showcase,
playground, and tutorial downloads keep their own verified release pins.

The tagged C# notice lives in `examples/dotnet-accessibility`. When updating it,
restore its lockfile from public NuGet, render both `ua1` and `ua2`, and review
the final PDFs and native preview before replacing `docs/assets/dotnet-accessibility`.
Run `python tools/build_dotnet_accessibility_starter.py` to rebuild the stable
ZIP and source manifest, then `python tools/verify_dotnet_accessibility.py`.
The verifier needs the .NET 10 SDK, Java 21 or later, and `pypdf==6.19.0`; it
downloads a checksum-pinned veraPDF 1.30.2 validator. These are maintainer checks,
not dependencies of the console application. Pass `--refresh-evidence` when
updating the downloadable reports; it writes `verification.json`,
`verapdf-ua1.json` and `verapdf-ua2.json` only after rendering and validation pass.
CI verifies the actual ZIP in isolated published applications on Windows and
Linux and checks that the retained reports still describe those specimens.

When changing the canonical domain, update `site_url`, `docs/robots.txt`, and this README, configure GitHub Pages, and verify DNS, HTTPS, sitemap URLs, and redirects. Keep the GitHub Pages URL until the custom domain is working.

Fullbleed is MIT licensed. Do not publish unsupported performance comparisons, standards conformance claims, or stale licensing statements. Retain old page URLs through the redirect map when consolidating reference material.

The Matplotlib report lives in `examples/matplotlib-report`. Install its pinned
requirements and the independent PDF readers from the `matplotlib` CI job, then
run `python tools/build_matplotlib_starter.py` and
`python tools/verify_matplotlib_starter.py`. The verifier extracts the actual ZIP,
executes its source and the guide snippet, inspects vector/PDF content, and tests
replay, customization and invalid data. Use `--update-assets` only after reviewing
both report pages; otherwise the verifier compares the output to the published
PDF. New evidence runs need a fresh `--out` directory. CI retains Windows and
Linux results and requires both jobs before deployment.

The Laravel queued-PDF example lives in `examples/laravel-pdf`. Run
`python tools/build_laravel_starter.py` to rebuild its deterministic ZIP. The
verifier, `python tools/verify_laravel_starter.py --browser chromium`, needs PHP,
Composer, the pinned Fullbleed wheel, independent PDF readers and Playwright.
It extracts the ZIP into a new output directory, installs the Composer lockfile,
then exercises real HTTP, database queues, retries, expiry and browser downloads.
Use `--refresh-assets` only when replacing the reviewed specimen and report.
CI tests PHP 8.3 and 8.4 on Linux before deployment. Evidence uploads exclude
the extracted application's generated `.env`, private database and vendor tree.

## Search discovery

The site publishes an XML sitemap and crawlable canonical URLs. When the optional
`INDEXNOW_KEY` repository secret is configured, deployment also hosts its ownership
file for [IndexNow](https://www.indexnow.org/documentation). Keep the key out of
source and logs. Pull-request builds do not receive it.

After a substantive content update or migration, notify IndexNow of the changed
`docs.fullbleed.dev` URLs using its documented API. Do not repeatedly resubmit
unchanged pages. An accepted notification means the URLs were received; it does
not establish search indexing or ranking.
