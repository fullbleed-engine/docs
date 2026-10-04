"""Compile the documented Rust examples and compare their actual document output."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples/rust"
EVIDENCE = EXAMPLES / "verification"
ASSETS = ROOT / "docs/assets"


def run(args, cwd=ROOT):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, encoding="utf-8")
    if result.returncode:
        raise SystemExit(f"{' '.join(args)} failed:\n{result.stdout}\n{result.stderr}")
    return result


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


guide = (ROOT / "docs/getting-started/rust.md").read_text(encoding="utf-8")
hello = (EXAMPLES / "src/hello.rs").read_text(encoding="utf-8").strip()
assert re.findall(r"```rust\n(.*?)\n```", guide, re.S)[0].strip() == hello
home = (ROOT / 'docs/index.md').read_text(encoding='utf-8')
home_code = re.findall(r'```rust\n(.*?)```', home, re.S)
assert len(home_code) == 1 and dedent(home_code[0]).strip() == hello, 'Homepage Rust example differs from the compiled source.'
run(["cargo", "fmt", "--manifest-path", str(EXAMPLES / "Cargo.toml"), "--check"])
run(["cargo", "build", "--release", "--locked", "--manifest-path", str(EXAMPLES / "Cargo.toml")])
suffix = ".exe" if os.name == "nt" else ""
bin_dir = EXAMPLES / "target/release"
hello_dir = EVIDENCE / "hello"
hello_dir.mkdir(parents=True, exist_ok=True)
run([str(bin_dir / ("hello" + suffix))], hello_dir)
assert (hello_dir / "invoice.pdf").read_bytes().startswith(b"%PDF-1.7")

playground = json.loads((ASSETS / "playground/verification.json").read_text())
metadata = json.loads(run(["cargo", "metadata", "--format-version", "1", "--locked", "--manifest-path", str(EXAMPLES / "Cargo.toml")]).stdout)
core = next(package for package in metadata["packages"] if package["name"] == "fullbleed")
assert core["source"].startswith("registry+")
assert playground["ok"] and playground["engine"] == core["version"]
report = {
    "ok": True,
    "engine": core["version"],
    "preview_source": "finalized_pdf",
    "rustc": run(["rustc", "--version"]).stdout.strip(),
    "platform": os.name,
    "hello_pdf_sha256": sha256(hello_dir / "invoice.pdf"),
    "documented_hello_matches_source": True,
    "homepage_snippet_matches_compiled_source": True,
    "fixtures": [],
}
for fixture in playground["fixtures"]:
    name = fixture["name"]
    output = EVIDENCE / name
    # Replay the actual playground inputs, including its ordinary-output notice label.
    prepared = ROOT / "playground/verification"
    html_path = prepared / fixture["source_files"]["html"]
    css_path = prepared / fixture["source_files"]["css"]
    assert sha256(html_path) == fixture["source_files"]["html_sha256"]
    assert sha256(css_path) == fixture["source_files"]["css_sha256"]
    result = run([
        str(bin_dir / ("from-files" + suffix)),
        str(html_path),
        str(css_path),
        str(ASSETS / "playground/fonts"),
        str(output),
    ])
    expected_pages = fixture["pages"]
    assert f"Rendered {expected_pages} page(s)" in result.stdout
    hashes = {"document.pdf": sha256(output / "document.pdf")}
    assert hashes["document.pdf"] == fixture["hashes"]["output.pdf"], name
    for index in range(1, expected_pages + 1):
        file = f"page-{index}.png"
        hashes[file] = sha256(output / file)
        assert hashes[file] == fixture["hashes"][file], f"{name}/{file}"
    report["fixtures"].append({
        "name": name, "pages": expected_pages,
        "matches_playground_pdf_and_pngs": True, "sha256": hashes,
    })
assert len(report["fixtures"]) == len(playground["fixtures"]) == 7
(EVIDENCE / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
