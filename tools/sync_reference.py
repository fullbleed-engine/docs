"""Import reference pages from a specific engine release, preserving source links."""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import subprocess
from pathlib import Path

PAGES = {
    "docs/python-api.md": "engine/pdf-engine.md",
    "docs/engine.md": "engine/overview.md",
    "docs/cli.md": "cli/commands.md",
    "docs/ui-accessibility.md": "ui/overview.md",
    "docs/css-coverage.md": "css-coverage.md",
    "docs/pdf-templates.md": "engine/template-composition.md",
    "docs/pdf-vt.md": "guides/print-output.md",
    "docs/performance-pass-2026-08-04.md": "guides/performance.md",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ref", default="v2.4.0")
    args = parser.parse_args()
    docs = Path(__file__).resolve().parents[1] / "docs"
    commit = subprocess.check_output(
        ["git", "-C", str(args.source), "rev-parse", args.ref + "^{commit}"], text=True
    ).strip()
    repo = f"https://github.com/fullbleed-engine/fullbleed-official/blob/{commit}/"
    for source, target in PAGES.items():
        content = subprocess.check_output(
            ["git", "-C", str(args.source), "show", f"{commit}:{source}"],
        ).decode("utf-8")

        def link(match: re.Match[str]) -> str:
            url = match.group(1)
            if re.match(r"[a-zA-Z][\w+.-]*:", url) or url.startswith(("#", "/")):
                return match.group(0)
            path, marker, anchor = url.partition("#")
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(source), path))
            if resolved in PAGES:
                dest = posixpath.relpath(PAGES[resolved], posixpath.dirname(target) or ".")
            else:
                dest = repo + resolved
            return "](" + dest + (marker + anchor if marker else "") + ")"

        content = re.sub(r"\]\(([^\s)]+)\)", link, content)
        heading, separator, body = content.partition("\n")
        note = f"\nReference imported from [{args.ref}]({repo}{source}). Check the installed runtime for your exact version.\n"
        path = docs / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(heading + separator + note + body, encoding="utf-8", newline="\n")
    (docs / "reference-source.json").write_text(
        json.dumps({"release": args.ref, "commit": commit, "pages": PAGES}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Imported {len(PAGES)} reference pages from {args.ref} ({commit[:12]})")


if __name__ == "__main__":
    main()
