"""Edit and run the notebook in a browser, then verify actual ZIP downloads.

Run verify_component_notebook.py first and supply its --out as --reference.
The reference supplies independently inspected PDF/HTML/PNG bytes. A private
loopback Jupyter server and a separate headless browser are stopped on exit.
"""
from __future__ import annotations

import argparse
import ast
import base64
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright

# Resolve only the checked-in helper when this tool is run with python -I.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from notebook_browser_processes import stop_process_tree

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def check_browser(page, context, source, work, out, reference, token):
    source_cells = {c["id"]: "".join(c["source"]) for c in source["cells"] if c["cell_type"] == "code"}
    assert len(source_cells) == 7
    order = ast.literal_eval(ast.parse(source_cells["order-data"]).body[0].value)
    downloads = []
    context.on("page", lambda child: child.on("download", lambda item: downloads.append(item)))
    page.on("download", lambda item: downloads.append(item))
    reports = []
    write(out / "startup-progress.json", dict(stage="waiting-for-run-menu"))
    page.get_by_role("menuitem", name="Run", exact=True).wait_for(timeout=60000)
    # The Run menu appears before Jupyter finishes creating the cell editors.
    # A loaded Windows runner exceeded Playwright's default five-second wait.
    write(out / "startup-progress.json", dict(stage="waiting-for-cell-editors"))
    expect(page.get_by_role("textbox")).to_have_count(7, timeout=60000)
    write(out / "startup-progress.json", dict(stage="waiting-for-kernel-ready"))
    expect(page.get_by_role("progressbar", name="Kernel status")).to_have_attribute("aria-valuenow", "100", timeout=60000)
    write(out / "startup-progress.json", dict(stage="ready-to-run"))
    for index, name in enumerate(("default", "edited", "long", "empty-after-long")):
        destination = out / name
        destination.mkdir()
        if index:
            data = deepcopy(order)
            accent, size = "#205b47", 30
            if name == "edited":
                data.update(number="1051", customer="Moss & Fern <Studio>", status="Packed")
                data["items"][0].update(quantity=32, item="Studio <notebooks> & cards")
                data["items"][1]["item"] = "Personalized note cards"
                accent, size = "#763c96", 26
            elif name in {"long", "empty-after-long"}:
                data["items"] = []
            data_source = "order = " + repr(data)
            if name == "long":
                data_source += "\norder['items'] = [\n    dict(item=f'Edition {n:02d} / art print', quantity=1, unit_price='9.50')\n    for n in range(1, 73)\n]"
            for position, text in ((1, data_source), (2, f"accent = {accent!r}\ntitle_size = {size!r}")):
                editor = page.get_by_role("textbox").nth(position)
                editor.scroll_into_view_if_needed()
                editor.fill(text)
                assert "\n".join(editor.locator("div.cm-line").all_text_contents()) == text
        page.get_by_role("menuitem", name="Run", exact=True).click()
        page.get_by_role("menuitem", name="Run All Cells", exact=True).click()
        page.get_by_text(f"[{(index + 1) * 7}]:", exact=True).wait_for(timeout=180000)
        expect(page.get_by_role("progressbar", name="Kernel status")).to_have_attribute("aria-valuenow", "100", timeout=30000)
        link = page.get_by_role("link", name="output/component-order.zip", exact=True)
        link.wait_for()
        href_path = urlsplit(link.get_attribute("href")).path
        assert href_path == "/files/output/component-order.zip", href_path
        page.get_by_role("button", name="Save and create checkpoint (Ctrl+S)", exact=True).click()
        downloads.clear()
        link.click()
        deadline = time.monotonic() + 15
        while not downloads and time.monotonic() < deadline:
            page.wait_for_timeout(100)
        assert len(downloads) == 1, "Expected a real browser download, including a temporary download tab"
        download = downloads[0]
        assert download.suggested_filename == "component-order.zip", download.suggested_filename
        assert download.failure() is None
        archive = destination / download.suggested_filename
        download.save_as(archive)
        expected = next(row for row in reference["cases"] if row["name"] == name)
        hashes = {}
        with ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            assert len(bundle.namelist()) == len(set(bundle.namelist()))
            assert set(bundle.namelist()) == set(expected["zip_files"])
            for filename in bundle.namelist():
                content = bundle.read(filename)
                assert sha256(content).hexdigest() == expected["artifact_hashes"][filename], (name, filename)
                assert content == (work / "output" / filename).read_bytes(), (name, filename)
                hashes[filename] = sha256(content).hexdigest()
        previews = page.get_by_role("feed", name="Cells").get_by_role("img")
        assert previews.count() == expected["pages"]
        for number in range(expected["pages"]):
            preview = previews.nth(number)
            preview.scroll_into_view_if_needed()
            image = preview.evaluate("img => ({complete: img.complete, width: img.naturalWidth, src: img.src})")
            assert image["complete"] and image["width"] > 0
            assert image["src"].startswith("data:image/png;base64,")
            assert sha256(base64.b64decode(image["src"].split(",", 1)[1])).hexdigest() == hashes[f"order-page-{number + 1}.png"]
            preview.screenshot(path=str(destination / f"visible-preview-{number + 1}.png"))
        link.scroll_into_view_if_needed()
        page.screenshot(path=str(destination / "notebook-download.png"))
        snapshot = page.locator("body").aria_snapshot().replace(token, "[redacted]")
        (destination / "notebook.txt").write_text(snapshot, encoding="utf-8")
        report = dict(name=name, pages=expected["pages"], actual_browser_download=True,
            filename=download.suggested_filename, href_path=href_path,
            zip_sha256=sha256(archive.read_bytes()).hexdigest(), artifact_hashes=hashes,
            matches_independent_reference=True, visible_previews_match_download=True)
        write(destination / "verification.json", report)
        reports.append(report)
        print(json.dumps(dict(case=name, pages=expected["pages"], browser_download=True)), flush=True)
    assert (work / "output/order-page-4.png").exists()
    assert "order-page-2.png" not in reports[-1]["artifact_hashes"]
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--browser", choices=("chrome", "chromium"), default="chrome")
    args = parser.parse_args()
    out = args.out.resolve()
    assert not out.exists(), "Use a new output directory to retain earlier evidence"
    reference = json.loads((args.reference / "verification.json").read_text(encoding="utf-8"))
    source_path = ROOT / reference["notebook"]
    assert reference["ok"] and reference["install_cell_executed"]
    assert reference["notebook"] == "examples/component-notebook-alpha6-r1/bootstrap_components.ipynb"
    assert sha256(source_path.read_bytes()).hexdigest() == reference["notebook_sha256"]
    source = json.loads(source_path.read_text(encoding="utf-8"))
    assert all(not c["outputs"] and c["execution_count"] is None for c in source["cells"] if c["cell_type"] == "code")
    out.mkdir(parents=True)
    work = out / "work"
    work.mkdir()
    shutil.copyfile(source_path, work / source_path.name)
    environment = {k: v for k, v in os.environ.items() if not k.startswith(("JUPYTER_", "IPYTHON"))}
    token = secrets.token_urlsafe(32)
    environment.update(JUPYTER_TOKEN=token, PYTHONUTF8="1")
    with tempfile.TemporaryDirectory(prefix="fullbleed-notebook-browser-") as private:
        private = Path(private)
        for key, name in (("JUPYTER_CONFIG_DIR", "config"), ("JUPYTER_DATA_DIR", "data"),
                          ("JUPYTER_RUNTIME_DIR", "runtime"), ("IPYTHONDIR", "ipython")):
            (private / name).mkdir()
            environment[key] = str(private / name)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        with (private / "server.log").open("w", encoding="utf-8") as log:
            server = subprocess.Popen([sys.executable, "-m", "notebook", "--no-browser", "--ServerApp.ip=127.0.0.1",
                f"--ServerApp.port={port}", "--ServerApp.port_retries=0", f"--ServerApp.root_dir={work}",
                "--ServerApp.shutdown_no_activity_timeout=600"], cwd=work, env=environment,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                deadline = time.monotonic() + 60
                while True:
                    assert server.poll() is None, "The private Jupyter server exited"
                    try:
                        request = urllib.request.Request(base + "/api/status", headers={"Authorization": "token " + token})
                        with urllib.request.urlopen(request, timeout=2) as response:
                            assert response.status == 200
                        break
                    except (urllib.error.URLError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise RuntimeError("Private Jupyter server did not become ready") from None
                        time.sleep(0.2)
                with sync_playwright() as p:
                    options = {"channel": "chrome"} if args.browser == "chrome" else {}
                    browser = p.chromium.launch(**options)
                    try:
                        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
                        page = context.new_page()
                        page_events = []
                        page.on("crash", lambda: page_events.append("page-crash"))
                        page.on("pageerror", lambda error: page_events.append(str(error).replace(token, "[redacted]")))
                        page.goto(base + "/tree?token=" + token, wait_until="domcontentloaded")
                        page.goto(base + "/notebooks/" + source_path.name, wait_until="domcontentloaded")
                        try:
                            cases = check_browser(page, context, source, work, out, reference, token)
                        except Exception as error:
                            # Save the original failure before browser captures or
                            # process cleanup can raise their own exceptions.
                            failure = dict(ok=False, type=type(error).__name__,
                                error=str(error).replace(token, "[redacted]"), page_events=page_events,
                                url=page.url.replace(token, "[redacted]"), capture_errors=[])
                            write(out / "failure.json", failure)
                            for capture in ("screenshot", "snapshot"):
                                try:
                                    if capture == "screenshot":
                                        page.screenshot(path=str(out / "failure.png"), timeout=5000, animations="disabled")
                                    else:
                                        (out / "failure.txt").write_text(page.locator("body").aria_snapshot(timeout=5000).replace(token, "[redacted]"), encoding="utf-8")
                                except Exception as capture_error:
                                    failure["capture_errors"].append(dict(capture=capture, error=str(capture_error).replace(token, "[redacted]")))
                                    write(out / "failure.json", failure)
                            raise
                        browser_version = browser.version
                    finally:
                        browser.close()
            finally:
                def request_shutdown():
                    request = urllib.request.Request(base + "/api/shutdown", data=b"", method="POST",
                        headers={"Authorization": "token " + token})
                    with urllib.request.urlopen(request, timeout=10):
                        pass
                write(out / "server-stopped.json", stop_process_tree(server, request_shutdown))
                log.flush()
                sanitized = (private / "server.log").read_text(encoding="utf-8", errors="replace").replace(token, "[redacted]")
                (out / "server.log").write_text(sanitized, encoding="utf-8")
    report = dict(ok=True, checked_at=datetime.now(timezone.utc).isoformat(),
        notebook_sha256=reference["notebook_sha256"], runtime_version=importlib.metadata.version("fullbleed"),
        system=platform.system(), python=platform.python_version(), browser=browser_version,
        tools={name: importlib.metadata.version(name) for name in ("notebook", "jupyter_server", "ipykernel", "playwright", "psutil")},
        cases=cases, stale_previews_excluded=True,
        scope="Local Jupyter Notebook editing, execution, displayed previews and actual browser ZIP downloads. Hosted Colab is not tested.")
    assert report["runtime_version"] == reference["runtime_version"]
    write(out / "verification.json", report)
    print(json.dumps(dict(ok=True, cases=len(cases), pages=sum(c["pages"] for c in cases))))


if __name__ == "__main__":
    main()
