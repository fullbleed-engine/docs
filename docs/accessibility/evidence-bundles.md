# Evidence Bundles

When an organization needs to prove PDF accessibility compliance — for ADA audits, Section 508 reviews, or procurement requirements — a passing score from a checker isn't enough. Auditors want to see *how* compliance was achieved, not just that it was.

Fullbleed's `AccessibilityEngine.render_bundle()` produces **15 artifacts** from a single render call. Together, these form an evidence bundle that documents every aspect of the accessible PDF generation process.

## What's in the Bundle

```python
from fullbleed import AccessibilityEngine

engine = AccessibilityEngine(
    strict=False,
    document_title="Annual Report 2025",
    document_lang="en",
)

results = engine.render_bundle(html)

# results is a dict with these keys:
print(list(results.keys()))
```

### Core Output

| Key | Type | What It Is |
|-----|------|------------|
| `pdf` | `bytes` | The tagged PDF/UA document |
| `html` | `str` | Input HTML as rendered |
| `css` | `str` | Resolved CSS used for rendering |

### Accessibility Verification

| Key | Type | What It Is |
|-----|------|------------|
| `a11y_report` | `dict` | Per-rule pass/fail/warning/manual results |
| `pmr_score` | `dict` | Quantified accessibility score (0–100) |
| `pdfua_seed_verify` | `dict` | 14 PDF/UA structural tag checks |

### Reading Order & Structure

| Key | Type | What It Is |
|-----|------|------------|
| `reading_order_trace` | `dict` | Every text block in order with page/coordinates |
| `pdf_structure_trace` | `dict` | Complete tag tree with MCID mapping |
| `cross_check` | `dict` | Render-time vs. PDF extraction comparison |

### Resolution Traces

| Key | Type | What It Is |
|-----|------|------------|
| `asset_resolution_trace` | `dict` | How images and assets were found/embedded |
| `font_resolution_trace` | `dict` | Font matching, fallback, and embedding |
| `pagination_trace` | `dict` | Where and why page breaks occurred |

### Visual & Diagnostic

| Key | Type | What It Is |
|-----|------|------------|
| `preview_pngs` | `list[bytes]` | Per-page PNG previews |
| `run_report` | `dict` | Overall render status and timing |
| `diagnostics` | `dict` | Engine-level diagnostic info |

## The Accessibility Report

The `a11y_report` checks your document against accessibility rules and categorizes each as pass, fail, warning, or needs-manual-review:

```python
report = results["a11y_report"]

# Summary counts
print(f"Pass: {report['pass_count']}")
print(f"Fail: {report['fail_count']}")
print(f"Warnings: {report['warning_count']}")
print(f"Manual: {report['manual_count']}")

# Individual rules
for rule in report["rules"]:
    status = "✅" if rule["status"] == "pass" else "❌" if rule["status"] == "fail" else "⚠️"
    print(f"  {status} {rule['id']}: {rule['description']}")
```

A well-structured HTML document typically achieves:
- **11+ passes**
- **0 failures**
- **3 warnings** (usually about color contrast, which requires visual verification)
- **4 manual-needed** (items like "confirm reading order matches visual order")

## The PMR Score

PMR (Pagination/Markup/Readability) is a composite score unique to Fullbleed:

```python
pmr = results["pmr_score"]

print(f"Score: {pmr['score']}/100")
print(f"Band: {pmr['band']}")           # "excellent" | "good" | "fair" | "poor"
print(f"Confidence: {pmr['confidence']}%")

# Sub-scores
print(f"Pagination: {pmr['pagination']}")
print(f"Markup: {pmr['markup']}")
print(f"Readability: {pmr['readability']}")
```

| Band | Score Range | Meaning |
|------|------------|---------|
| Excellent | 90–100 | Fully accessible, well-structured |
| Good | 70–89 | Accessible with minor improvements possible |
| Fair | 50–69 | Partially accessible, needs work |
| Poor | 0–49 | Significant accessibility issues |

## PDF/UA Seed Verification

The 14 PDF/UA seed checks verify structural requirements at the PDF tag level:

```python
verify = results["pdfua_seed_verify"]

print(f"Passed: {verify['passed']}/{verify['total']}")

for check in verify["checks"]:
    icon = "✅" if check["pass"] else "❌"
    print(f"  {icon} {check['rule']}")
```

These checks verify things like:
- Document has a title
- Language is set
- Tag structure is valid
- All content is tagged
- Tables have proper header associations

## Reading Order Cross-Check

This is Fullbleed's unique verification: comparing the order content was *written* to the PDF against the order a reader *extracts* it:

```python
cross = results["cross_check"]

print(f"Match: {cross['match']}")  # True if orders agree
print(f"Render blocks: {cross['render_count']}")
print(f"Extract blocks: {cross['extract_count']}")

if not cross["match"]:
    for diff in cross["differences"]:
        print(f"  Mismatch at position {diff['position']}: "
              f"rendered '{diff['render_text'][:30]}' "
              f"vs extracted '{diff['extract_text'][:30]}'")
```

No other PDF engine does this. It's the difference between "we think the reading order is correct" and "we verified it from two independent sources."

## Using Evidence Bundles in CI/CD

```python
import json
from fullbleed import AccessibilityEngine

engine = AccessibilityEngine(strict=False, document_title="Report", document_lang="en")
results = engine.render_bundle(html)

# Gate on PMR score
pmr = results["pmr_score"]
assert pmr["score"] >= 90, f"PMR score {pmr['score']} below threshold"

# Gate on zero failures
report = results["a11y_report"]
assert report["fail_count"] == 0, f"{report['fail_count']} accessibility failures"

# Gate on PDF/UA checks
verify = results["pdfua_seed_verify"]
assert verify["passed"] == verify["total"], f"PDF/UA: {verify['passed']}/{verify['total']}"

# Save evidence for audit trail
with open("evidence.json", "w") as f:
    json.dump({
        "pmr": pmr,
        "a11y": report,
        "pdfua": verify,
        "reading_order_match": results["cross_check"]["match"],
    }, f, indent=2)

# Save the PDF
with open("report.pdf", "wb") as f:
    f.write(results["pdf"])
```

## Next Steps

- [Accessibility Engine →](engine.md) — Constructor options and HTML guidelines
- [Coverage Report →](coverage.md) — WCAG 2.0 AA and Section 508 coverage details
- [AI Agent Integration →](../guides/ai-agents.md) — How agents use evidence bundles for autonomous authoring
