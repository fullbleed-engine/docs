# PDF invoice downloads with Axum

A local Rust application that accepts invoice JSON and returns a styled PDF
using Fullbleed 2.5.19. It includes editable MiniJinja HTML/CSS, licensed fonts,
an example request, and a browser form. The server keeps no document files.

## Run the download

Install Rust 1.85.0 or newer and a native Rust toolchain. Extract the project ZIP,
open a terminal in `fullbleed-axum-starter`, then run:

```sh
cargo run --release --locked
```

Open <http://127.0.0.1:3000>. Edit the JSON and choose **Download PDF**.
The initial invoice has three line items and a total of **$1,870.00**.
The first build downloads Cargo dependencies; PDF generation makes no network
requests. Fonts and document assets come from this project.

For an HTTP client, leave the server running and open another terminal here:

```sh
curl --fail-with-body --request POST http://127.0.0.1:3000/invoices/pdf --header "Content-Type: application/json" --data-binary "@sample.json" --output invoice.pdf
```

In PowerShell, use `curl.exe` in that command. Open `invoice.pdf` after a
successful response. The API sets `application/pdf`, a safe attachment filename,
and `Cache-Control: private, no-store`.

If port 3000 is occupied, set `PDF_BIND` to a different loopback address such as
`127.0.0.1:3100`. `PDF_BIND=127.0.0.1:0` selects an available port and prints it.

## Change the document

- Change the customer, dates, line items, and note in the browser form or
  `sample.json`. Dates are displayed as supplied; no payment-date arithmetic is
  performed. This example uses USD with no tax or discount calculation.
- `unit_price_cents` is a whole number. Multiplication and totals use integer
  cents, without floating-point rounding.
- Edit `templates/invoice.html` and `templates/invoice.css`, then restart the
  server. MiniJinja escapes request strings; keep its HTML autoescaping enabled
  and do not apply `safe` to untrusted values.
- The template receives `invoice`, display-ready `items`, and `total`. Each
  display item has `description`, `quantity`, `unit_price`, and `amount`.
- Register additional licensed fonts in `AppState::load` and select their family
  in CSS. Uncovered characters return an error instead of an incomplete PDF.

The source files under `ui/` are compiled into the executable; restart with
`cargo run --release --locked` after changing the form. For an ordinary invoice
data edit, submit the new JSON without restarting.

## Request behavior

Requests are limited to 64 KiB and 200 line items. Each quantity is 1–10,000;
each unit price is 0–100,000,000 cents. Names, addresses, descriptions, and notes
have explicit length limits in `Invoice::validate`. Unknown JSON fields,
control characters, and unsafe invoice numbers are rejected.

| Response | Meaning |
| --- | --- |
| `200 application/pdf` | Complete invoice bytes |
| `400`, `413`, `415`, or `422` | Invalid JSON, oversized body, wrong content type, or invalid invoice data |
| `503` with `Retry-After: 1` | Both rendering slots are occupied |
| `500` | Template or rendering failure; the response does not expose request data |

Rendering runs through Tokio's blocking pool with two application-owned slots.
There is no unbounded queue of PDF jobs. A running blocking task cannot be
aborted: disconnecting its request leaves the slot occupied until that task
finishes. For hard execution deadlines or native-crash containment, run renders
in a separate worker process; an HTTP timeout alone does not stop native work.

This is a runnable integration example, not a hosted invoice service. It binds
to loopback and includes no authentication, tenant authorization, TLS, durable
job queue, or payment logic. Apply your application's access controls before
exposing the endpoint, and choose limits for its workload. Only trusted
server-side templates and fonts are loaded; clients supply data, not HTML/CSS.

## Check the project

```sh
cargo test --release --locked
```

The repository verifier extracts this exact ZIP into a directory outside the
checkout, builds it, calls its real HTTP endpoint, checks independent PDF text
and page rendering, and exercises input errors and recovery. The concurrency
tests use controlled blocking jobs to verify admission and permit lifetime,
including a disconnected request. These checks are not a throughput benchmark
or proof of standards conformance.

Guide and verification source:
<https://docs.fullbleed.dev/guides/axum-pdf/>

Code is MIT licensed. Keep the font license notices in `fonts/` when distributing
the project. All invoice names, addresses, and prices are fictional examples.
