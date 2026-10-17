"""Open the synthetic Streamlit app and preserve evidence of startup failures."""
import json
import sys


def _capture_failure(page, out, attempt, stage, error, events):
    stem = out / f"startup-{attempt}"
    record = {"ok": False, "stage": stage,
              "error_type": type(error).__name__, "error": str(error),
              "url": None, "events": events, "capture_errors": []}

    def capture(name, action):
        try:
            return action()
        except Exception as exc:
            record["capture_errors"].append({"artifact": name, "error": str(exc)})
            return None

    if page is not None:
        record["url"] = capture("url", lambda: page.url)
        capture("screenshot", lambda: page.screenshot(path=str(stem.with_suffix(".png")), timeout=5000))
        capture("DOM", lambda: stem.with_suffix(".html").write_text(page.content(), encoding="utf-8"))
    stem.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def open_app_context(browser, url, *, out, attempt, browser_errors, external_requests, timeout=30000):
    """Use the existing readiness gate once; diagnostics never replace its error."""
    ctx = page = None
    stage = "new-context"
    events = {"console": [], "page_errors": [], "failed_requests": []}
    try:
        ctx = browser.new_context(viewport={"width": 1365, "height": 1100})

        def route(request):
            if request.request.url.startswith((url + "/", "data:", "blob:")):
                request.continue_()
            else:
                external_requests.append(request.request.url.split("?")[0])
                request.abort()

        ctx.route("**/*", route)
        stage = "new-page"
        page = ctx.new_page()

        def page_error(error):
            message = str(error)
            browser_errors.append(message)
            events["page_errors"].append(message)

        page.on("pageerror", page_error)
        page.on("console", lambda message: events["console"].append(
            {"type": message.type, "text": message.text, "location": message.location}))
        page.on("requestfailed", lambda request: events["failed_requests"].append(
            {"url": request.url.split("?")[0], "method": request.method, "failure": request.failure}))
        stage = "navigation"
        page.goto(url, timeout=timeout)
        stage = "initial-control"
        page.get_by_role("button", name="Prepare PDF", exact=True).wait_for(timeout=timeout)
        return ctx, page
    except Exception as error:
        try:
            _capture_failure(page, out, attempt, stage, error, events)
        except Exception as capture_error:
            print(f"Startup diagnostic capture failed: {capture_error}", file=sys.stderr)
        finally:
            if ctx is not None:
                try:
                    ctx.close()
                except Exception:
                    pass
        raise
