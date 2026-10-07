"""Install the downloadable ASP.NET starter and check its isolated published server."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request
import zipfile

from pypdf import PdfReader
from build_aspnet_starter import ROOT, ASSETS, project_files, digest

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dotnet", default=shutil.which("dotnet"))
parser.add_argument("--out", type=Path, default=ROOT / "output/aspnet-verification")
args = parser.parse_args()
if not args.dotnet:
    raise SystemExit("Install the .NET 10 SDK or pass --dotnet.")
dotnet = str(Path(args.dotnet).resolve())
out = args.out.resolve()
out.mkdir(parents=True, exist_ok=True)
workspace = Path(tempfile.mkdtemp(prefix="aspnet download with spaces ", dir=out))
manifest = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
archive = (ASSETS / "project.zip").read_bytes()
assert digest(archive) == manifest["projectZipSha256"]
sources = project_files()
project = workspace / "fullbleed-aspnet"
with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
    expected = {"fullbleed-aspnet/" + name: data for name, data in sources.items()}
    assert len(bundle.namelist()) == len(expected) and set(bundle.namelist()) == set(expected)
    for name, data in expected.items():
        assert bundle.read(name) == data, name
        destination = workspace / name
        assert destination.resolve().is_relative_to(workspace)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
for entry in manifest["files"]:
    data = sources[entry["path"]]
    assert len(data) == entry["bytes"] and digest(data) == entry["sha256"]
assert len(manifest["files"]) == len(sources)

env = dict(os.environ, DOTNET_ROOT=str(Path(dotnet).parent),
           NUGET_PACKAGES=str(workspace / "nuget-cache"),
           NUGET_HTTP_CACHE_PATH=str(workspace / "nuget-http-cache"),
           DOTNET_ROLL_FORWARD="LatestPatch", ASPNETCORE_ENVIRONMENT="Production",
           DOTNET_ENVIRONMENT="Production", DOTNET_CLI_TELEMETRY_OPTOUT="1")
env.pop("FULLBLEED_NATIVE_LIBRARY", None)
commands = []


def run(label, arguments, cwd=project):
    result = subprocess.run([dotnet, *arguments], cwd=cwd, env=env, capture_output=True,
                            text=True, encoding="utf-8", timeout=240)
    for stream in ["stdout", "stderr"]:
        (out / f"{label}.{stream}.txt").write_text(getattr(result, stream), encoding="utf-8")
    assert result.returncode == 0, f"{label} failed; see {out}"
    commands.append(label)


run("restore", ["restore", "--locked-mode", "--source", "https://api.nuget.org/v3/index.json"])
published = workspace / "isolated-publish"
run("publish", ["publish", "-c", "Release", "--no-restore", "-o", str(published)])
application = str(published / "FullbleedWeb.dll")
preview_dir = out / "preview"
run("preview", [application, "--preview", str(preview_dir)], cwd=workspace)
preview = json.loads((preview_dir / "preview.json").read_text(encoding="utf-8"))
assert preview["runtime"].startswith("10.0.")
assert preview["pages"] == 1 and preview["missingGlyphs"] == 0
pdf = (preview_dir / "invoice.pdf").read_bytes()
png = (preview_dir / "invoice_page1.png").read_bytes()
assert digest(pdf) == manifest["outputs"]["invoice.pdf"]
assert digest(png) == manifest["outputs"]["invoice.png"]
assert pdf == (ASSETS / "invoice.pdf").read_bytes()
assert png == (ASSETS / "invoice.png").read_bytes() == sources["Assets/invoice.png"]
reader = PdfReader(io.BytesIO(pdf), strict=True)
text = " ".join(reader.pages[0].extract_text().split())
assert len(reader.pages) == 1 and "Maple & Finch" in text and text.count("$1,870.00") == 2
checks = ["download matches tracked source and manifest", "fresh NuGet restore with lockfile",
          "publish artifact runs outside source project", "one-page PDF text and total",
          "final-PDF preview and PDF match published assets"]
with socket.socket() as reserved:
    reserved.bind(("127.0.0.1", 0))
    port = reserved.getsockname()[1]
base = f"http://127.0.0.1:{port}"


def request(path, method="GET"):
    try:
        response = urlopen(Request(base + path, method=method), timeout=30)
    except HTTPError as error:
        response = error
    with response:
        return response.status, dict(response.headers), response.read()


def private_response(result, status):
    code, headers, body = result
    headers = {key.lower(): value for key, value in headers.items()}
    assert code == status, (code, body[:100])
    assert headers["cache-control"] == "private, no-store"
    assert headers["x-content-type-options"] == "nosniff"
    if status == 200:
        assert headers["content-type"] == "application/pdf"
        assert int(headers["content-length"]) == len(body)
        assert "attachment; filename=invoice-NS-1042.pdf" in headers["content-disposition"]
        assert body == pdf
    return headers, body


log = (out / "server.log").open("w", encoding="utf-8")
server = subprocess.Popen([dotnet, application, "--urls", base], cwd=workspace, env=env,
                          stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
try:
    deadline = time.monotonic() + 30
    while True:
        assert server.poll() is None, "Server exited; inspect server.log"
        try:
            if request("/health")[0] == 200:
                break
        except (URLError, TimeoutError, ConnectionError):
            pass
        assert time.monotonic() < deadline, "Server readiness timed out"
        time.sleep(0.1)
    home = request("/")
    assert home[0] == 200 and b'href="/invoices/NS-1042/pdf"' in home[2]
    assert request("/invoice.png")[2] == png
    checks.append("download page and preview served by published app")
    private_response(request("/invoices/NS-1042/pdf"), 200)
    checks.append("HTTP attachment headers, private caching, exact PDF bytes")
    private_response(request("/invoices/unknown/pdf"), 404)
    private_response(request("/invoices/NS-1042/pdf", "POST"), 405)
    private_response(request("/invoices/%2e%2e%2fAssets%2finvoice.html/pdf"), 404)
    checks.append("unknown IDs, encoded path and unsupported method rejected")
    barrier = threading.Barrier(12)

    def concurrent_request(_):
        barrier.wait(timeout=20)
        return request("/invoices/NS-1042/pdf")

    with ThreadPoolExecutor(max_workers=12) as pool:
        burst = list(pool.map(concurrent_request, range(12)))
    assert {item[0] for item in burst} == {200, 503}
    for result in burst:
        headers, _ = private_response(result, result[0])
        if result[0] == 503:
            assert headers["retry-after"] == "2"
    private_response(request("/invoices/NS-1042/pdf"), 200)
    checks.append("concurrent requests bounded, Retry-After sent, next request succeeds")
    template = published / "Assets/invoice.html"
    original = template.read_bytes()
    try:
        template.write_text("<html><body><p>PRIVATE_INPUT_MARKER \U0010ffff</p></body></html>", encoding="utf-8")
        _, error = private_response(request("/invoices/NS-1042/pdf"), 500)
        problem = json.loads(error)
        assert problem["title"] == "The invoice PDF could not be generated."
        assert b"PRIVATE_INPUT_MARKER" not in error and str(workspace).encode() not in error
    finally:
        template.write_bytes(original)
    private_response(request("/invoices/NS-1042/pdf"), 200)
    checks.append("missing glyph rejected without partial PDF; recovery succeeds")
    css = published / "Assets/invoice.css"
    held = published / "Assets/invoice.css.held"
    css.rename(held)
    try:
        _, error = private_response(request("/invoices/NS-1042/pdf"), 500)
        assert str(published).encode() not in error and b"invoice.css" not in error
    finally:
        held.rename(css)
    private_response(request("/invoices/NS-1042/pdf"), 200)
    checks.append("missing asset returns generic error; permit released and recovery succeeds")
finally:
    server.terminate()
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()
        server.wait(timeout=5)
    log.close()
assert "PRIVATE_INPUT_MARKER" not in (out / "server.log").read_text(encoding="utf-8")
version = manifest["packageVersion"]
installed = workspace / "nuget-cache/fullbleed.dotnet" / version
package = installed / f"fullbleed.dotnet.{version}.nupkg"
provenance = json.loads((installed / "native-provenance.json").read_text(encoding="utf-8"))
engine = next(item for item in provenance["dependencies"] if item["name"] == "fullbleed")
assert version == "0.1.6" and engine["version"] == "2.5.11"
report = {
    "ok": True, "checkedAt": datetime.now(timezone.utc).isoformat(),
    "platform": platform.system(), "architecture": platform.machine(),
    "runtime": preview["runtime"], "framework": "net10.0",
    "package": "FullBleed.DotNet", "packageVersion": version, "engineVersion": engine["version"],
    "packageSha256": digest(package.read_bytes()), "freshNuGetCache": True,
    "projectZipSha256": digest(archive), "pdfSha256": digest(pdf), "previewSha256": digest(png),
    "commands": commands, "checks": checks,
    "concurrentStatuses": {str(code): sum(item[0] == code for item in burst) for code in [200, 503]},
    "scope": "Synthetic fixture, released NuGet package, isolated framework-dependent publish output. No authorization, hosted capacity, or PDF standards claim.",
}
(out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"ok": True, "checks": len(checks), "platform": report["platform"], "runtime": report["runtime"]}))
