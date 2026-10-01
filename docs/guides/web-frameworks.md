---
title: Generate PDF responses with FastAPI, Flask, and Django
description: Serve downloadable PDF invoices from FastAPI, Flask, or Django with Fullbleed. Runnable Python examples include bundled fonts, response headers, and output checks.
---
# Generate PDF responses with FastAPI, Flask, and Django

Fullbleed returns PDF bytes from Python data and HTML/CSS. Pass those bytes to
your framework's response object to serve an invoice, report, or statement.
The examples below generate the same one-page invoice and send it as a download.

[Get the complete examples](https://github.com/fullbleed-engine/fullbleed-official/tree/master/examples/web_frameworks){ .md-button .md-button--primary }
[Try a PDF in your browser](../getting-started/notebook.md){ .md-button }

## Set up the examples

Use a Python 3.10–3.14 virtual environment, then get the example source:

```bash
git clone https://github.com/fullbleed-engine/fullbleed-official.git
cd fullbleed-official/examples/web_frameworks
```

Choose one framework below. Each requirement file installs that framework;
`fullbleed` remains a separate package. The examples are checked with Fullbleed
2.4.0, FastAPI 0.142.2, Flask 3.1.3, and Django 5.2.17.

Each app serves this fictional record:

```text
http://127.0.0.1:8000/invoices/INV-1042.pdf
```

Open that URL after starting the app. The browser downloads `invoice.pdf`, which
contains three line items and a total of **USD 1,870.00**. An unknown invoice ID
returns HTTP 404. Stop the server before trying another framework on the same port.

## FastAPI

```bash
python -m pip install fullbleed -r requirements-fastapi.txt
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
python -m pip install fullbleed -r requirements-flask.txt
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
python -m pip install fullbleed -r requirements-django.txt
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
contains the fictional record lookup, HTML/CSS template, and `render_invoice()`.
It calculates line totals with `Decimal`, escapes text before inserting it into
HTML, and embeds the Inter font shipped with Fullbleed. A new `PdfEngine` renders
each request into memory.

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
integer quantities, and unit-price strings. Keep access checks before rendering.
This sample omits tax and discounts.

## Verify and deploy your workflow

From the repository root, with Fullbleed installed:

```bash
python -m pip install -r examples/web_frameworks/requirements-check.txt
python examples/web_frameworks/check_examples.py --out target/web-framework-check
```

The check exercises each framework's test client, saves its PDF response, and
verifies the expected text and total, page count, embedded font, HTTP headers,
404 behavior, and repeated output bytes. It also emits a PNG preview and
`verification.json`. Review the preview after changing the document's layout.

The launch commands above run local development servers. Use your framework's
deployment setup for a public app. For large jobs, render in your job queue and
store the finished PDF for download. The [variable-data guide](bank-statements.md)
covers compiled document families when many records share a template.

[Invoice data examples](invoices.md) · [Python API](../engine/pdf-engine.md) ·
[Ask a question](https://github.com/fullbleed-engine/fullbleed-official/discussions)
