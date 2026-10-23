"""Build the actual Yew source download and check its native and browser boundaries."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
from importlib.metadata import version
import json
import os
from pathlib import Path, PurePosixPath
import platform
import shutil
import subprocess
import sys
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs/assets/yew-starter"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "target/yew-starter")
    parser.add_argument("--target-dir", type=Path, default=ROOT / "examples/yew-sheet/target")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "CARGO_TARGET_DIR": str(args.target_dir.resolve())}
    for name in ("RUST_MIN_STACK", "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS"):
        env.pop(name, None)
    report = dict(ok=False, at=datetime.now(timezone.utc).isoformat(),
                  platform=platform.platform(), checks=[], commands=[],
                  verifier_versions={name: version(name) for name in ("pypdf", "pypdfium2", "pillow")})

    def check(label, condition):
        if not condition:
            raise AssertionError(label)
        report["checks"].append(label)

    def run(label, command, cwd):
        print("Checking " + label, flush=True)
        result = subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                                capture_output=True, text=True, encoding="utf-8", timeout=1200)
        (out / (label + ".stdout.txt")).write_text(result.stdout, encoding="utf-8")
        (out / (label + ".stderr.txt")).write_text(result.stderr, encoding="utf-8")
        report["commands"].append(dict(name=label, exit_code=result.returncode))
        check(label + " exit status", result.returncode == 0)
        return result.stdout

    try:
        manifest = json.loads((ASSETS / "source.json").read_text(encoding="utf-8"))
        archive_path = ASSETS / "project.zip"
        check("source archive checksum and size", digest(archive_path) == manifest["zip_sha256"]
              and archive_path.stat().st_size == manifest["zip_bytes"])
        prefix = manifest["prefix"]
        check("expected archive root", prefix == "fullbleed-yew-sheet/")
        workspace = out / "extracted"
        with zipfile.ZipFile(archive_path) as archive:
            names = [prefix + item["path"] for item in manifest["files"]]
            check("archive contains exactly the declared files", sorted(archive.namelist()) == sorted(names)
                  and len(names) == len(set(names)))
            check("archive paths are confined", all(not PurePosixPath(name).is_absolute()
                  and ".." not in PurePosixPath(name).parts and "\\" not in name
                  and ":" not in name for name in names))
            for item in manifest["files"]:
                data = archive.read(prefix + item["path"])
                check("source digest: " + item["path"], len(data) == item["bytes"]
                      and sha256(data).hexdigest() == item["sha256"])
            archive.extractall(workspace)
        project = workspace / prefix
        command = "cargo run --release --locked -- data.json output"
        check("documented command appears in README and guide", all(command in path.read_text(encoding="utf-8")
              for path in (project / "README.md", ROOT / "docs/getting-started/rust.md")))
        lock_hash = digest(project / "Cargo.lock")
        run("build", ["cargo", "build", "--release", "--locked"], project)
        metadata = json.loads(run("metadata", ["cargo", "metadata", "--format-version", "1", "--locked"], project))
        packages = {}
        for name, expected in manifest["packages"].items():
            package = next(p for p in metadata["packages"] if p["name"] == name)
            check("published pinned dependency: " + name, package["version"] == expected
                  and package["source"].startswith("registry+"))
            packages[name] = package["version"]
        executable = Path(metadata["target_directory"]) / "release" / ("fullbleed-yew-sheet" + (".exe" if os.name == "nt" else ""))
        build = dict(executable=str(executable), executable_sha256=digest(executable), packages=packages,
                     font_hashes={Path(f["path"]).name: f["sha256"] for f in manifest["files"] if f["path"].startswith("fonts/")})
        metadata_path = out / "build.json"
        metadata_path.write_text(json.dumps(build, indent=2) + "\n", encoding="utf-8")
        report.update(packages=packages, source_zip_sha256=manifest["zip_sha256"],
                      rustc=run("rustc", ["rustc", "--version"], project).strip())
        run("native-outputs", [sys.executable, ROOT / "tools/verify_yew_outputs.py", "--project", project,
                              "--metadata", metadata_path, "--output", out / "documents"], project)
        report["native"] = json.loads((out / "documents/verification.json").read_text(encoding="utf-8"))
        run("readme-command", command.split(), project)
        generated = out / "documents/default"
        for path in sorted((project / "output").rglob("*")):
            if path.is_file():
                relative = path.relative_to(project / "output")
                check("README command output: " + relative.as_posix(), path.read_bytes() == (generated / relative).read_bytes())
        check("public PDF fixture matches generated bytes", (ASSETS / "document.pdf").read_bytes() == (generated / "document.pdf").read_bytes())
        for path in sorted((ASSETS / "preview").rglob("*")):
            if path.is_file():
                relative = path.relative_to(ASSETS / "preview")
                check("public HTML export: " + relative.as_posix(), path.read_bytes() == (generated / relative).read_bytes())
        with Image.open(ASSETS / "document.png") as published, Image.open(generated / "pdfium-1.png") as actual:
            published.load()
            actual.load()
            check("public preview format, mode, dimensions, metadata and pixels match",
                  published.format == actual.format == "PNG" and published.mode == actual.mode
                  and published.size == actual.size and published.info == actual.info
                  and published.tobytes() == actual.tobytes())
        fixture = out / "client-check"
        shutil.copytree(ROOT / "tools/fixtures/yew-client", fixture)
        shutil.copy2(project / "src/document.rs", fixture / "src/document.rs")
        shutil.copy2(project / "data.json", fixture / "data.json")
        client_lock_hash = digest(fixture / "Cargo.lock")
        run("client-check", ["cargo", "check", "--target", "wasm32-unknown-unknown", "--locked"], fixture)
        client_metadata = json.loads(run("client-metadata", ["cargo", "metadata", "--format-version", "1", "--locked"], fixture))
        check("browser component has no Fullbleed dependency", not any(p["name"] == "fullbleed" for p in client_metadata["packages"]))
        yew = next(p for p in client_metadata["packages"] if p["name"] == "yew")
        features = next(n["features"] for n in client_metadata["resolve"]["nodes"] if n["id"] == yew["id"])
        check("browser component uses Yew CSR without SSR", "csr" in features and "ssr" not in features)
        check("both Cargo lockfiles unchanged", digest(project / "Cargo.lock") == lock_hash
              and digest(fixture / "Cargo.lock") == client_lock_hash)
        report["ok"] = True
        report["scope"] = "Pinned native fixtures and browser-component compilation; browser execution is checked separately for static HTML exports."
    except Exception as error:
        report["error"] = str(error)
        raise
    finally:
        (out / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(ok=True, checks=len(report["checks"]), output=str(out))), flush=True)


if __name__ == "__main__":
    main()
