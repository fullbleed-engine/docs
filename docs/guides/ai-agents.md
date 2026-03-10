# AI Agent Integration

Fullbleed was accidentally designed to be the perfect PDF engine for AI agents. Here's why and how.

## Why Fullbleed + AI Agents?

Most PDF generation tools are black boxes — you feed in HTML, get a PDF, and if something's wrong, you're debugging blind. Fullbleed was built with extreme observability, and it turns out that's exactly what AI agents need to iterate effectively.

**What makes Fullbleed agent-friendly:**

1. **Structured JSON output** for every diagnostic — glyph misses, CSS selector misses, layout warnings, JIT compiler draw reports
2. **Image preview rendering** — agents can "see" the PDF without opening it
3. **Deterministic rendering** — same input = same output, making automated testing trivial
4. **Component-level validation** — errors are emitted per-component, not per-document
5. **CLI with `--json-only` and `--schema`** — machine-readable everything

## Quick Setup for Agents

```python
import fullbleed

engine = fullbleed.PdfEngine(
    page_width="8.5in",
    page_height="11in",
    margin="0.75in",
    jit_mode=True,     # Enable JIT diagnostics
    debug=True,        # Enable debug output
    debug_out="debug.json",
)

# Render PDF + preview images in one pass
pdf_bytes = engine.render_pdf(html, css)
previews = engine.render_image_pages(html, css, dpi=150)

# Agent can now:
# 1. Inspect debug.json for layout issues
# 2. View preview PNGs to verify visual output
# 3. Iterate on HTML/CSS based on structured feedback
```

## CLI for Agent Pipelines

```bash
# Render with full diagnostics as JSON
fullbleed render \
    --html document.html \
    --css style.css \
    --out output.pdf \
    --emit-image \
    --json-only \
    --debug

# Get the JSON schema for structured output
fullbleed render --schema
```

The `--json-only` flag ensures all output is machine-parseable JSON — no human-formatted text that agents need to parse.

## The Agent Loop

The typical AI agent workflow with Fullbleed:

```
1. Agent generates HTML/CSS from data + template
2. Agent calls render_pdf() + render_image_pages()
3. Agent inspects:
   - Preview images (visual check)
   - Debug JSON (layout warnings, glyph misses)
   - Component mount validation (accessibility)
4. Agent adjusts HTML/CSS based on feedback
5. Repeat until output passes all checks
```

This is exactly how Fullbleed was used to autonomously generate IRS tax form layouts from publications 1141, 1167, and 1179 — the agent iterated on each form until it matched the specification.

## Accessibility Engine for Agents

The `AccessibilityEngine` is particularly powerful for agent workflows because it produces a full evidence bundle:

```python
from fullbleed.accessibility import AccessibilityEngine

engine = AccessibilityEngine(
    page_size="letter",
    document_lang="en",
    document_title="Accessible Report",
    strict=True,
)

engine.render_bundle(
    body_html=html,
    css_text=css,
    out_dir="./output",
    stem="report",
    run_verifier=True,
    run_pmr=True,
    emit_reading_order_trace=True,
    emit_pdf_structure_trace=True,
    render_preview_png=True,
)
```

This produces 13+ artifacts that an agent can inspect:

- Tagged PDF
- Accessibility verifier report (JSON)
- PMR score report (JSON)
- Reading order trace + visualization
- PDF structure trace + visualization
- Component mount validation
- Preview PNGs

Each artifact gives the agent specific, actionable feedback for iteration.

## Batch Processing

For agents processing many documents:

```python
# Parallel rendering across all CPU cores
results = engine.render_pdf_batch_parallel(
    items=[{"html": h, "css": c} for h, c in document_pairs]
)
```

The GIL is released during rendering, so Python-based agents can render PDFs in parallel threads without blocking.

## Schema Output

For tool-using AI agents (function calling, tool use), get the full schema:

```bash
fullbleed render --schema > render_schema.json
fullbleed capabilities --json > capabilities.json
```

These JSON schemas can be fed directly into an agent's tool definition.
