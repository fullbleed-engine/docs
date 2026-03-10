# Batch Rendering

Fullbleed's Rust core uses Rayon for parallel rendering, and releases the Python GIL on every render call. This means you can render thousands of documents concurrently without blocking your Python application.

## Why It's Fast

Traditional HTML-to-PDF tools have a per-document overhead:

| Tool | Per-Document Cost |
|------|-------------------|
| Puppeteer/Playwright | Launch Chromium tab (~200MB RAM), navigate, wait, screenshot |
| wkhtmltopdf | Fork Qt WebKit process |
| WeasyPrint | Parse CSS (pure Python, single-threaded) |
| **Fullbleed** | Rust thread, no browser, no process, GIL released |

Fullbleed renders happen in Rust threads. Python can submit work to a thread pool and do other things while rendering completes.

## Basic Parallel Rendering

```python
from fullbleed import PdfEngine
from concurrent.futures import ThreadPoolExecutor
import time

# Create engine once, reuse for all renders
engine = PdfEngine(
    margin="0.75in",
    footer_each="Page {page} of {pages}",
    pdf_profile="tagged",
)

# Your document data
documents = [
    {"title": f"Invoice #{i}", "html": f"<h1>Invoice #{i}</h1><p>Amount: ${i * 100}</p>"}
    for i in range(1000)
]

def render_one(doc):
    pdf_bytes = engine.render(doc["html"])
    return {"title": doc["title"], "size": len(pdf_bytes), "pdf": pdf_bytes}

# Render 1000 documents in parallel
start = time.time()
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(render_one, documents))
elapsed = time.time() - start

print(f"Rendered {len(results)} documents in {elapsed:.1f}s")
print(f"Average: {elapsed/len(results)*1000:.0f}ms per document")
```

Because Fullbleed releases the GIL via `py.allow_threads` on every render call, Python threads actually run in parallel — not sequentially like most Python C extensions.

## Batch with AccessibilityEngine

The same pattern works for accessible document generation:

```python
from fullbleed import AccessibilityEngine
from concurrent.futures import ThreadPoolExecutor

engine = AccessibilityEngine(
    strict=False,
    document_lang="en",
    footer_each="Page {page} of {pages}",
)

def render_accessible(doc):
    results = engine.render_bundle(doc["html"])
    return {
        "title": doc["title"],
        "pdf": results["pdf"],
        "pmr_score": results["pmr_score"]["score"],
        "a11y_failures": results["a11y_report"]["fail_count"],
    }

with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(render_accessible, documents))

# Report on accessibility across all documents
avg_pmr = sum(r["pmr_score"] for r in results) / len(results)
failures = sum(1 for r in results if r["a11y_failures"] > 0)
print(f"Average PMR: {avg_pmr:.1f}/100")
print(f"Documents with failures: {failures}/{len(results)}")
```

## Memory Considerations

Fullbleed doesn't launch browser processes, so memory usage is predictable:

- **Per-engine**: Minimal — the engine is a lightweight Rust struct
- **Per-render**: Proportional to document size (HTML + CSS + output PDF)
- **No leaks**: Rust's ownership model guarantees cleanup

Compare this to Puppeteer, where each Chromium tab can consume 100–200MB and leaked pages are a common production issue.

## Error Handling in Batch

```python
from fullbleed import PdfEngine
from concurrent.futures import ThreadPoolExecutor, as_completed

engine = PdfEngine(margin="0.75in")

def render_safe(doc):
    try:
        pdf = engine.render(doc["html"])
        return {"id": doc["id"], "ok": True, "pdf": pdf}
    except Exception as e:
        return {"id": doc["id"], "ok": False, "error": str(e)}

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {pool.submit(render_safe, doc): doc for doc in documents}
    for future in as_completed(futures):
        result = future.result()
        if not result["ok"]:
            print(f"Failed: {result['id']} — {result['error']}")
```

## Async Integration

For async web frameworks (FastAPI, aiohttp), run renders in a thread executor:

```python
import asyncio
from fullbleed import PdfEngine

engine = PdfEngine(margin="0.75in", pdf_profile="tagged")

async def render_pdf(html: str) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, engine.render, html)

# In a FastAPI route:
# @app.post("/render")
# async def render(request: RenderRequest):
#     pdf = await render_pdf(request.html)
#     return Response(content=pdf, media_type="application/pdf")
```

## Next Steps

- [PdfEngine API →](pdf-engine.md) — Full constructor reference
- [Template Composition →](template-composition.md) — Overlay onto existing PDFs
- [Accessibility Engine →](../accessibility/engine.md) — Batch accessible documents
