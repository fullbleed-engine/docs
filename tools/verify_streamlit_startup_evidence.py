"""Exercise startup success, navigation failure and readiness failure in a real browser."""
from contextlib import redirect_stderr
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from pathlib import Path
from threading import Thread
import argparse
import json
import socket

from playwright.sync_api import Error, TimeoutError, sync_playwright
from streamlit_browser_context import _capture_failure, open_app_context

ROOT = Path(__file__).resolve().parents[1]


class Fixture(BaseHTTPRequestHandler):
    ready = False
    delayed_ready = False

    def do_GET(self):
        if self.path.endswith("/broken.png"):
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            return
        if self.ready:
            if self.delayed_ready:
                body = b'''<!doctype html><title>Ready after initialization</title>
<button id="prepare" hidden>Prepare PDF</button>
<script>setTimeout(() => { document.getElementById("prepare").hidden = false; }, 1500);</script>'''
            else:
                body = b"<!doctype html><title>Ready</title><button>Prepare PDF</button>"
        else:
            body = b'''<!doctype html><title>Startup control</title><h1>Startup remains incomplete</h1>
<img src="/broken.png" alt="Synthetic failed asset">
<script>console.error("Synthetic startup console"); throw new Error("Synthetic startup error");</script>'''
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def verify(args):
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    record = {"ok": False, "playwright": version("playwright"), "controls": []}
    server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"

    def check_failure(browser, url, attempt, expected_error, evidence_out=out):
        errors, external = [], []
        try:
            open_app_context(browser, url, out=evidence_out, attempt=attempt,
                             browser_errors=errors, external_requests=external, timeout=1000)
        except expected_error as error:
            assert not external
            assert not browser.contexts, "Startup failure left a browser context open"
            return error, errors
        raise AssertionError("A startup failure was incorrectly accepted")

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**({"channel": "chrome"} if args.browser == "chrome" else {}), headless=True)
            record["browser"] = browser.version
            try:
                Fixture.ready = True
                ctx, page = open_app_context(browser, origin, out=out, attempt=1,
                                            browser_errors=[], external_requests=[])
                assert page.get_by_role("button", name="Prepare PDF", exact=True).is_visible()
                assert not list(out.glob("startup-1.*"))
                ctx.close()
                record["controls"].append({"name": "ready app returns its live context", "passed": True})

                # Successful startup uses the same bounded readiness timeout as
                # the real app. Only deliberate failure controls use 1000 ms.
                Fixture.delayed_ready = True
                ctx, page = open_app_context(browser, origin, out=out, attempt=5,
                                            browser_errors=[], external_requests=[])
                assert page.get_by_role("button", name="Prepare PDF", exact=True).is_visible()
                assert not list(out.glob("startup-5.*"))
                ctx.close()
                Fixture.delayed_ready = False
                Fixture.ready = False
                record["controls"].append({"name": "delayed ready app uses the normal bounded readiness timeout", "passed": True})

                error, errors = check_failure(browser, origin, 2, TimeoutError)
                failure = json.loads((out/"startup-2.json").read_text(encoding="utf-8"))
                assert failure["ok"] is False and failure["stage"] == "initial-control"
                assert failure["error"] == str(error) and "Prepare PDF" in str(error)
                assert failure["url"] == origin+"/"
                assert not failure["capture_errors"]
                assert errors == failure["events"]["page_errors"] and any("Synthetic startup error" in e for e in errors)
                assert any(e["text"] == "Synthetic startup console" for e in failure["events"]["console"])
                assert any(e["url"].endswith("/broken.png") for e in failure["events"]["failed_requests"])
                assert "Startup remains incomplete" in (out/"startup-2.html").read_text(encoding="utf-8")
                assert (out/"startup-2.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
                record["controls"].append({"name": "readiness timeout retains URL, DOM, screenshot and early events", "passed": True})

                with socket.socket() as unavailable:
                    unavailable.bind(("127.0.0.1", 0))
                    url = f"http://127.0.0.1:{unavailable.getsockname()[1]}"
                    error, _ = check_failure(browser, url, 3, Error)
                failure = json.loads((out/"startup-3.json").read_text(encoding="utf-8"))
                assert failure["stage"] == "navigation" and failure["error"] == str(error)
                assert failure["events"]["failed_requests"]
                assert (out/"startup-3.html").exists()
                assert (out/"startup-3.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
                record["controls"].append({"name": "navigation failure retains its original error and browser evidence", "passed": True})

                class ScreenshotFailurePage:
                    def __init__(self, page, persistent):
                        self.page, self.persistent, self.calls = page, persistent, 0

                    def __getattr__(self, name):
                        return getattr(self.page, name)

                    def screenshot(self, **kwargs):
                        self.calls += 1
                        if self.persistent or self.calls == 1:
                            raise Error("Protocol error (Page.captureScreenshot): Unable to capture screenshot")
                        return self.page.screenshot(**kwargs)

                # Exercise both recovery and permanent capture failure without
                # relying on the timing of Chromium's connection-refused page.
                Fixture.ready = True
                ctx, page = open_app_context(browser, origin, out=out, attempt=8,
                                            browser_errors=[], external_requests=[])
                try:
                    for attempt, persistent in [(6, False), (7, True)]:
                        proxy = ScreenshotFailurePage(page, persistent)
                        original = Error("Original navigation failure")
                        _capture_failure(proxy, out, attempt, "navigation", original,
                                         {"console": [], "page_errors": [], "failed_requests": []})
                        failure = json.loads((out/f"startup-{attempt}.json").read_text(encoding="utf-8"))
                        assert failure["error"] == str(original) and failure["stage"] == "navigation"
                        assert proxy.calls == 2 and (out/f"startup-{attempt}.html").exists()
                        assert len(failure["capture_errors"]) == (2 if persistent else 1)
                        assert failure["capture_errors"][0]["artifact"] == "screenshot"
                        if persistent:
                            assert failure["capture_errors"][1]["artifact"] == "screenshot-retry"
                            assert not (out/f"startup-{attempt}.png").exists()
                        else:
                            assert (out/f"startup-{attempt}.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
                    record["controls"].append({"name": "one screenshot retry recovers a transient capture error without erasing it", "passed": True})
                    record["controls"].append({"name": "persistent screenshot failure retains both errors and stops after two attempts", "passed": True})
                finally:
                    ctx.close()
                    Fixture.ready = False

                unwritable = out/"not-a-directory"
                unwritable.write_text("Deliberate diagnostic-write failure control", encoding="utf-8")
                with (out/"capture-failure.log").open("w", encoding="utf-8") as log, redirect_stderr(log):
                    error, _ = check_failure(browser, origin, 4, TimeoutError, unwritable)
                assert "Prepare PDF" in str(error)
                assert "Startup diagnostic capture failed" in (out/"capture-failure.log").read_text(encoding="utf-8")
                record["controls"].append({"name": "diagnostic write failure preserves the readiness TimeoutError", "passed": True})
                record["ok"] = True
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        record["artifacts"] = {path.name: sha256(path.read_bytes()).hexdigest()
                               for path in out.iterdir() if path.is_file() and path.name != "verification.json"}
        (out/"verification.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT/"output/streamlit-startup-controls")
    parser.add_argument("--browser", choices=["chrome", "chromium"], default="chrome")
    result = verify(parser.parse_args())
    print(json.dumps({"ok": result["ok"], "controls": len(result["controls"])}))
