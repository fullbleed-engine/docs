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

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def check_browser(page, context, source, work, out, reference, token):
    source_cells = {c["id"]: "".join(c["source"]) for c in source["cells"] if c["cell_type"] == "code"}
    assert len(source_cells) == 8
    downloads = []
    context.on("page", lambda child: child.on("download", lambda item: downloads.append(item)))
    page.on("download", lambda item: downloads.append(item))
    reports = []
    write(out / "startup-progress.json", dict(stage="waiting-for-run-menu"))
    page.get_by_role("menuitem", name="Run", exact=True).wait_for(timeout=60000)
    write(out / "startup-progress.json", dict(stage="waiting-for-cell-editors"))
    # The notebook shell can appear before its CodeMirror editors finish
    # initializing. Allow the same startup budget as the menu and kernel.
    expect(page.get_by_role("textbox")).to_have_count(8, timeout=60000)
    # The editor can finish loading before its first kernel connection. The
    # observed first attempt marked cells trusted but executed none of them.
    write(out / "startup-progress.json", dict(stage="waiting-for-kernel-ready"))
    expect(page.get_by_role("progressbar", name="Kernel status")).to_have_attribute("aria-valuenow", "100", timeout=60000)
    write(out / "startup-progress.json", dict(stage="recording-ready-snapshot"))
    (out / "ready-to-run.txt").write_text(page.locator("body").aria_snapshot().replace(token, "[redacted]"), encoding="utf-8")
    for index, expected in enumerate(reference["cases"]):
        name = expected["name"]
        destination = out / name
        destination.mkdir()
        if index:
            text = "\n".join(key + " = " + repr(value) for key, value in expected["controls"].items())
            editor = page.get_by_role("textbox").nth(1)
            editor.scroll_into_view_if_needed()
            editor.fill(text)
            assert "\n".join(editor.locator("div.cm-line").all_text_contents()) == text
        page.get_by_role("menuitem", name="Run", exact=True).click()
        page.get_by_role("menuitem", name="Run All Cells", exact=True).click()
        page.get_by_text(f"[{(index + 1) * 8}]:", exact=True).wait_for(timeout=180000)
        expect(page.get_by_role("progressbar", name="Kernel status")).to_have_attribute("aria-valuenow", "100", timeout=30000)
        link = page.get_by_role("link", name="output/component-field-notes.zip", exact=True)
        link.wait_for()
        href_path = urlsplit(link.get_attribute("href")).path
        assert href_path == "/files/output/component-field-notes.zip", href_path
        page.get_by_role("button", name="Save and create checkpoint (Ctrl+S)", exact=True).click()
        downloads.clear()
        link.click()
        deadline = time.monotonic() + 15
        while not downloads and time.monotonic() < deadline:
            page.wait_for_timeout(100)
        assert len(downloads) == 1, "Expected the actual browser ZIP download"
        download = downloads[0]
        assert download.suggested_filename == "component-field-notes.zip" and download.failure() is None
        archive = destination / download.suggested_filename
        download.save_as(archive)
        hashes = {}
        with ZipFile(archive) as bundle:
            assert bundle.testzip() is None
            assert len(bundle.namelist()) == len(set(bundle.namelist()))
            assert set(bundle.namelist()) == set(expected["zip_files"])
            for filename in bundle.namelist():
                content = bundle.read(filename)
                assert sha256(content).hexdigest() == expected["artifact_hashes"][filename], (name, filename)
                assert content == (work / "output" / filename).read_bytes()
                hashes[filename] = sha256(content).hexdigest()
        previews = page.get_by_role("feed", name="Cells").get_by_role("img")
        assert previews.count() == expected["pages"]
        for number in range(expected["pages"]):
            preview = previews.nth(number)
            preview.scroll_into_view_if_needed()
            image = preview.evaluate("img => ({complete: img.complete, width: img.naturalWidth, src: img.src})")
            assert image["complete"] and image["width"] > 0 and image["src"].startswith("data:image/png;base64,")
            assert sha256(base64.b64decode(image["src"].split(",", 1)[1])).hexdigest() == hashes[f"field-notes-page-{number + 1}.png"]
            preview.screenshot(path=str(destination / f"visible-preview-{number + 1}.png"))
        link.scroll_into_view_if_needed()
        page.screenshot(path=str(destination / "notebook-download.png"))
        (destination / "notebook.txt").write_text(page.locator("body").aria_snapshot().replace(token, "[redacted]"), encoding="utf-8")
        report = dict(name=name, pages=expected["pages"], actual_browser_download=True,
            filename=download.suggested_filename, href_path=href_path,
            zip_sha256=sha256(archive.read_bytes()).hexdigest(), artifact_hashes=hashes,
            matches_independent_reference=True, visible_previews_match_download=True)
        write(destination / "verification.json", report)
        reports.append(report)
        print(json.dumps(dict(case=name, pages=expected["pages"], browser_download=True)), flush=True)
    assert (work / "output/field-notes-page-4.png").exists()
    assert "field-notes-page-4.png" not in reports[-1]["artifact_hashes"]
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
    source_path = Path(reference["notebook"])
    assert reference["ok"] and reference["install_cell_executed"]
    assert source_path.name == "component_page_bands.ipynb"
    assert sha256(source_path.read_bytes()).hexdigest() == reference["notebook_sha256"]
    source = json.loads(source_path.read_text(encoding="utf-8"))
    assert all(not c["outputs"] and c["execution_count"] is None for c in source["cells"] if c["cell_type"] == "code")
    out.mkdir(parents=True)
    work = out / "work"
    work.mkdir()
    shutil.copyfile(source_path, work / source_path.name)
    if reference["local_install_override"]:
        wheel = Path(reference["local_wheel"]["path"])
        assert sha256(wheel.read_bytes()).hexdigest() == reference["local_wheel"]["sha256"]
        install = next(cell for cell in source["cells"] if cell["id"] == "install-fullbleed")
        install["source"] = ['%pip install --quiet --no-index --no-deps "' + wheel.as_posix() + '"']
        (work / source_path.name).write_text(json.dumps(source, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
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
                if server.poll() is None:
                    try:
                        request = urllib.request.Request(base + "/api/shutdown", data=b"", method="POST",
                            headers={"Authorization": "token " + token})
                        with urllib.request.urlopen(request, timeout=10):
                            pass
                        server.wait(timeout=30)
                    except (urllib.error.URLError, TimeoutError, subprocess.TimeoutExpired):
                        server.terminate()
                        server.wait(timeout=15)
                write(out / "server-stopped.json", dict(stopped=server.poll() is not None, returncode=server.returncode))
                log.flush()
                sanitized = (private / "server.log").read_text(encoding="utf-8", errors="replace").replace(token, "[redacted]")
                (out / "server.log").write_text(sanitized, encoding="utf-8")
    report = dict(ok=True, checked_at=datetime.now(timezone.utc).isoformat(),
        notebook_sha256=reference["notebook_sha256"], runtime_version=importlib.metadata.version("fullbleed"),
        system=platform.system(), python=platform.python_version(), browser=browser_version,
        tools={name: importlib.metadata.version(name) for name in ("notebook", "jupyter_server", "ipykernel", "playwright")},
        cases=cases, stale_previews_excluded=True, local_install_override=reference["local_install_override"],
        scope="Local Jupyter Notebook editing, execution, finalized counters, displayed previews and actual browser ZIP downloads. The receipt identifies any local-wheel install override. Hosted Colab is not tested.")
    assert report["runtime_version"] == reference["runtime_version"]
    write(out / "verification.json", report)
    print(json.dumps(dict(ok=True, cases=len(cases), pages=sum(c["pages"] for c in cases))))


if __name__ == "__main__":
    main()
