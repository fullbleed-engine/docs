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

# Route these source references to the existing runnable guides on this site.
LINK_TARGETS = {
    **PAGES,
    "docs/embedded-stylesheets.md": "guides/complete-html.md",
    "docs/component-authoring.md": "guides/python-components.md",
    "examples/components/README.md": "guides/python-components.md",
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
    "ui/overview.md": (
        "For `class_name`, selectors and attached styles, see the "
        "[worked styling examples](../guides/python-components.md#class-names-and-styles). "
        "The reference below focuses on the accessibility authoring layer."
    ),
    "guides/performance.md": (
        "For a current shared-input example, see the "
        "[Fullbleed 2.5.39, WeasyPrint, and Chromium comparison](renderer-comparison.md), "
        "measured October 27, 2026. "
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

BODY_REPLACEMENTS = {
    "css-coverage.md": (
        (
            "This document is the canonical statement of validated CSS coverage for Fullbleed's deterministic HTML/CSS-to-PDF engine.",
            "The imported report below preserves earlier version-specific coverage claims.\n"
            "Use the dated comparison evidence above for the current verified result.",
        ),
        ("## Latest retained full-corpus result", "## Historical source comparison"),
    ),
}


def published_css_context(docs: Path) -> tuple[str, str]:
    """Use the same publication pin as the evidence explorer, including its failed gate."""
    publication = json.loads((docs / "assets/css-corpus/published.json").read_text(encoding="utf-8"))
    if (publication.get("schema") != "fullbleed.css-corpus-publication.v1"
            or publication.get("packageSource") != "published"
            or not re.fullmatch(r"\d+\.\d+\.\d+", publication.get("version", ""))):
        raise ValueError("CSS context requires a published stable-wheel evidence manifest")
    overall = publication["overall"]
    counts = [overall[key] for key in ("pass", "fail", "reference_disputed", "total")]
    if any(type(value) is not int or value < 0 for value in counts) or sum(counts[:3]) != counts[3] or counts[3] == 0:
        raise ValueError("CSS evidence fixture counts are inconsistent")
    if type(publication.get("gatePassed")) is not bool:
        raise ValueError("CSS evidence must record its comparison gate")
    if publication["gatePassed"] and overall["fail"]:
        raise ValueError("CSS evidence cannot pass its gate with failed fixtures")
    version, total = publication["version"], overall["total"]
    conclusion = "is **success**" if publication["gatePassed"] else "remains **failure**"
    heading = f"""---
title: CSS support for HTML-to-PDF
description: Evaluate Fullbleed's CSS support for print documents with {total:,} tested fixtures, generated PDFs, reference images, and known limitations for the published {version} wheel.
---
# CSS support for PDF documents"""
    introduction = f"""Fullbleed lays out static HTML/CSS as paged documents. Use the tested examples
below to evaluate the styling and page layout your invoices and reports need.

The [published-wheel comparison](guides/css-corpus.md#published-wheel-comparison-{version.replace('.', '')})
tests **Fullbleed {version}** and reports **{overall['pass']:,} PASS, {overall['fail']} FAIL and {overall['reference_disputed']} REFERENCE-DISPUTED** across {total:,} fixtures.
Its overall conclusion {conclusion}. The exact PyPI wheel, report,
PDFs, images, and manifest verification are retained.

[Browse the actual results](guides/css-explorer.md), or read the
[method, package identity, and historical comparisons](guides/css-corpus.md).
The [navigation alpha source result](guides/css-corpus.md#navigation-alpha-source-comparison-260a14)
is recorded separately and has different verdict totals. Earlier zero-failure
reports below are historical; none establishes complete CSS conformance."""
    return heading, introduction


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--ref", required=True, help="Verified release tag or commit to import")
    args = parser.parse_args()
    docs = Path(__file__).resolve().parents[1] / "docs"
    css_heading, css_introduction = published_css_context(docs)
    headings = {"css-coverage.md": css_heading}
    introductions = {**INTRODUCTIONS, "css-coverage.md": css_introduction}
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
            if resolved in LINK_TARGETS:
                dest = posixpath.relpath(LINK_TARGETS[resolved], posixpath.dirname(target) or ".")
            else:
                dest = repo + resolved
            return "](" + dest + (marker + anchor if marker else "") + ")"

        content = re.sub(r"\]\(([^\s)]+)\)", link, content)
        heading, separator, body = content.partition("\n")
        heading = headings.get(target, heading)
        for before, after in BODY_REPLACEMENTS.get(target, ()):
            body = body.replace(before, after)
        note = f"\nReference imported from [{args.ref}]({repo}{source}). Check the installed runtime for your exact version.\n"
        if target in introductions:
            note = "\n" + introductions[target] + "\n" + note
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
