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
    "docs/font-registration.md": "engine/font-registration.md",
    "docs/cli.md": "cli/commands.md",
    "docs/ui-accessibility.md": "ui/overview.md",
    "docs/css-coverage.md": "css-coverage.md",
    "docs/pdf-templates.md": "engine/template-composition.md",
    "docs/pdf-vt.md": "guides/print-output.md",
    "docs/performance-pass-2026-08-04.md": "guides/performance.md",
}

# Site-only context must survive later imports of the historical report.
INTRODUCTIONS = {
    "engine/font-registration.md": (
        "The [Chinese-text guide](../guides/chinese-pdf.md) includes a runnable "
        "bilingual invoice, pinned font preparation, and the current variable-font "
        "weight and glyph-report limitations. The "
        "[Arabic and English invoice](../guides/arabic-pdf.md) includes static "
        "regular and bold Noto Sans Arabic files with a font manifest and glyph checks."
    ),
    "css-coverage.md": (
        "See the [complete 1,662-fixture CSS comparison and release follow-ups]"
        "(guides/css-corpus.md), including the published 2.5.14 baseline, "
        "the reviewed 2.5.22 source candidate, remaining failures, PDFs, images, and hashes. "
        "The imported reference below preserves earlier version-specific reports."
    ),
    "guides/performance.md": (
        "For a current shared-input example, see the "
        "[Fullbleed 2.5.6, WeasyPrint, and Chromium comparison](renderer-comparison.md). "
        "The historical report below uses different fixtures and measurement methods; "
        "its numbers should not be combined with that comparison."
    ),
}

APPENDICES = {
    "engine/font-registration.md": (
        "\n## Retained synthesis evidence\n\n"
        "The [2.5.16 release notes]"
        "(https://github.com/fullbleed-engine/fullbleed-official/releases/tag/v2.5.16), "
        "[executable evidence bundle]"
        "(https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.5.16/fullbleed-2.5.16-font-synthesis-evidence.zip), "
        "and [verification record]"
        "(https://github.com/fullbleed-engine/fullbleed-official/releases/download/v2.5.16/fullbleed-2.5.16-verification.json) "
        "retain the original Windows and Linux checks for the named synthesis controls. "
        "They do not establish complete CSS Fonts conformance.\n"
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ref", required=True, help="Verified release tag or commit to import")
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
        if target in INTRODUCTIONS:
            note = "\n" + INTRODUCTIONS[target] + "\n" + note
        path = docs / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            heading + separator + note + body + APPENDICES.get(target, ""),
            encoding="utf-8", newline="\n",
        )
    (docs / "reference-source.json").write_text(
        json.dumps({"release": args.ref, "commit": commit, "pages": PAGES}, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Imported {len(PAGES)} reference pages from {args.ref} ({commit[:12]})")


if __name__ == "__main__":
    main()
