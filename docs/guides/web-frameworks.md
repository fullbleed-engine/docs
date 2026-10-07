---
title: Generate PDF responses with FastAPI, Flask, and Django
description: Serve downloadable PDF invoices from FastAPI, Flask, or Django with Fullbleed. Runnable Python examples include bundled fonts, response headers, and output checks.
---
# Generate PDF responses with FastAPI, Flask, and Django

Fullbleed returns PDF bytes from Python data and HTML/CSS. Pass those bytes to
your framework's response object to serve an invoice, report, or statement.
The starter below generates a designed one-page invoice and sends it as a
download. It includes a browser page, editable HTML/CSS, and the same document
renderer behind three small framework adapters.

[Download the Python starter](../assets/python-web/project.zip){ .md-button .md-button--primary }
[Open the sample PDF](../assets/python-web/invoice.pdf){ .md-button }

[![Northstar Studio invoice with large green typography, three line items, and an orange-accented total panel.](../assets/python-web/invoice.png)](../assets/python-web/invoice.pdf)

The [source record and download hashes](../assets/python-web/source.json) identify
the exact source files, fonts, package version, and generated sample. This is a
fictional integration example; connect your application's authorized record
lookup before serving real invoices.

Want a container? The same download includes a [tested Docker path](python-docker.md)
for the FastAPI app, using Debian slim or Alpine.

## Set up the examples

Use Python 3.10–3.14. Extract the starter, open its `fullbleed-python-invoice`
directory, and create a virtual environment:

```bash
python -m venv .venv
```

Activate it with `source .venv/bin/activate` on macOS/Linux or
`.venv\Scripts\Activate.ps1` in Windows PowerShell. A repository checkout also
works: the [source directory](https://github.com/fullbleed-engine/fullbleed-official/tree/master/examples/web_frameworks)
is `examples/web_frameworks`.

Choose one framework below. Each requirement file installs that framework;
`fullbleed` remains a separate package. The examples are checked with Fullbleed
2.5.11, FastAPI 0.142.2, Flask 3.1.3, and Django 5.2.17.

Each app serves this fictional record:

```text
http://127.0.0.1:8000/invoices/INV-1042.pdf
```

Open `http://127.0.0.1:8000/` after starting the app and select **Download invoice**.
The browser downloads `invoice.pdf`, which
contains three line items and a total of **USD 1,870.00**. An unknown invoice ID
returns HTTP 404. Stop the server before trying another framework on the same port.

## FastAPI

```bash
python -m pip install fullbleed==2.5.11 -r requirements-fastapi.txt
python -m uvicorn fastapi_app:app --host 127.0.0.1 --port 8000
```

The route in `fastapi_app.py` uses the shared `invoice.py` renderer:

```python
from fastapi import FastAPI, HTTPException, Response
from invoice import PDF_HEADERS, load_invoice, render_invoice

class PDFResponse(Response):
    media_type = "application/pdf"

app = FastAPI(title="Fullbleed invoice example")

@app.get("/invoices/{invoice_id}.pdf", response_class=PDFResponse)
def invoice_pdf(invoice_id: str) -> PDFResponse:
    invoice = load_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return PDFResponse(render_invoice(invoice), headers=PDF_HEADERS)
```

The custom response class advertises `application/pdf` in OpenAPI. You can also
try the route at `http://127.0.0.1:8000/docs`. See
[FastAPI's response documentation](https://fastapi.tiangolo.com/advanced/custom-response/)
for how explicit response classes affect the generated API schema.

The route uses a normal `def` because rendering is synchronous. FastAPI runs
these route functions in its thread pool. Calling a synchronous renderer directly
inside `async def` would still occupy that event-loop thread until rendering
finishes. See [FastAPI's concurrency documentation](https://fastapi.tiangolo.com/async/#path-operation-functions).

## Flask

```bash
python -m pip install fullbleed==2.5.11 -r requirements-flask.txt
python -m flask --app flask_app run --host 127.0.0.1 --port 8000
```

`flask_app.py` returns a regular Flask response:

```python
from flask import Flask, Response, abort
from invoice import PDF_HEADERS, load_invoice, render_invoice

app = Flask(__name__)

@app.get("/invoices/<invoice_id>.pdf")
def invoice_pdf(invoice_id: str) -> Response:
    invoice = load_invoice(invoice_id)
    if invoice is None:
        abort(404)
    return Response(
        render_invoice(invoice), mimetype="application/pdf", headers=PDF_HEADERS
    )
```

See [Flask's Response API](https://flask.palletsprojects.com/en/stable/api/#flask.Response)
for response bodies, media types, and headers.

## Django

```bash
python -m pip install fullbleed==2.5.11 -r requirements-django.txt
python django_app.py runserver 127.0.0.1:8000 --noreload
```

The [complete Django example](https://github.com/fullbleed-engine/fullbleed-official/blob/master/examples/web_frameworks/django_app.py)
includes minimal local settings. In an existing project, keep your project's
settings and adapt this view and URL pattern:

```python
from django.http import Http404, HttpResponse
from django.urls import path
from django.views.decorators.http import require_safe
from invoice import PDF_HEADERS, load_invoice, render_invoice

@require_safe
def invoice_pdf(request, invoice_id: str) -> HttpResponse:
    invoice = load_invoice(invoice_id)
    if invoice is None:
        raise Http404("Invoice not found")
    return HttpResponse(
        render_invoice(invoice), content_type="application/pdf", headers=PDF_HEADERS
    )

urlpatterns = [path("invoices/<str:invoice_id>.pdf", invoice_pdf)]
```

Adjust the `invoice` import to its location in your Django project. See
[Django's HttpResponse documentation](https://docs.djangoproject.com/en/5.2/ref/request-response/#httpresponse-objects)
for response construction and headers.

## The shared document renderer

[`invoice.py`](https://github.com/fullbleed-engine/fullbleed-official/blob/master/examples/web_frameworks/invoice.py)
contains the fictional record lookup and `render_invoice()`.
It calculates line totals with `Decimal`, escapes text before inserting it into
HTML, and registers the Inter font shipped with Fullbleed alongside the included
DM Serif Display and Bebas Neue families. A new `PdfEngine` renders each request
into memory. Font licenses and pinned source hashes are included in `fonts/`.

## Edit the HTML and CSS

Change `templates/invoice.html` for document structure and
`templates/invoice.css` for typography, spacing, columns, and color. The renderer
reads those files for each request, so a new download uses your edits without
restarting the server. Its Python `string.Template` placeholders include
`$customer`, `$number`, `$rows`, and `$total`; write a literal dollar sign as `$$`.
Text values are escaped before substitution and are not interpreted again as
template markup.

The included layout is a fixed one-page A4 sample for three line items. Adapt
its geometry and pagination before using longer records, and review the final
PDF. This starter leaves tax, discounts, invoice numbering, payment collection,
and application authentication to your application. `static/index.html` is the
local demo page; replace it with your application's interface when integrating.

## Return a private PDF attachment

The response headers are shared too:

```python
PDF_HEADERS = {
    "Content-Disposition": 'attachment; filename="invoice.pdf"',
    "Cache-Control": "private, no-store",
}
```

The download filename is fixed. To display the PDF in the browser instead,
change `attachment` to `inline`. The response carries binary PDF bytes directly;
it does not need JSON or base64 encoding, and requests do not share output files.

Replace `load_invoice()` with your application's authorized record lookup. It
returns an invoice number, customer, date strings, and items with descriptions,
integer quantities, unit-price strings, and an optional item `detail`.
Keep access checks before rendering.

## Verify and deploy your workflow

From the extracted starter's directory, with Fullbleed installed:

```bash
python -m pip install -r requirements-check.txt
python check_examples.py --out output/check
```

The check exercises each framework's test client and starts the documented
local servers in turn. It verifies actual HTTP downloads, an independent PDF
reader's text and totals, page count, embedded fonts, headers, 404/405 responses,
and matching simultaneous downloads. It also checks font/license hashes,
literal markup and placeholder-like customer text, and the saved preview.
Servers stop when the checks finish.

Review `output/check/verification.json`, its PDFs, and the PNG preview after a
layout change. To refresh the download page's saved preview, run:

```bash
python check_examples.py --out output/check --update-preview
```

The browser page shows a saved preview of the included invoice. Its **Download
invoice** link always renders the current HTML/CSS. Verification covers these
synthetic fixtures and local servers; it does not establish production capacity
or PDF standards conformance.

For the FastAPI app, follow the [Docker deployment guide](python-docker.md).
The Flask and Django commands above run local development servers; use your
framework's deployment setup for a public app. For large jobs, render in your job queue and
store the finished PDF for download. The [variable-data guide](bank-statements.md)
covers compiled document families when many records share a template.

[Invoice data examples](invoices.md) · [Python API](../engine/pdf-engine.md) ·
[Ask a question](https://github.com/fullbleed-engine/fullbleed-official/discussions)
