# Fullbleed Laravel queue starter

Queue a PDF from a trusted Blade template. The request returns a document ID;
a Laravel database worker renders it with Fullbleed, and authenticated clients
poll its status and download the private PDF. The included invoice is fictional.

## Run locally

Requirements: PHP 8.3+ with PDO SQLite, mbstring and Laravel's standard extensions,
Composer 2, and Python 3.10+ on a platform with a Fullbleed wheel. The lockfile
pins Laravel 13.35.0; the Python requirement pins Fullbleed 2.5.21.

```sh
composer install
python -m venv .venv
.venv/bin/python -m pip install -r renderer/requirements.txt
php setup.php .venv/bin/python
php artisan migrate --force
php artisan serve --host=127.0.0.1 --port=8000
```

On Windows use `.venv\Scripts\python.exe` for both Python commands and the argument
to `setup.php`. Setup generates APP_KEY and PDF_API_KEY in `.env` without printing
them or overwriting existing configuration.

In a second terminal, from the same directory:

```sh
php artisan queue:work --queue=pdf --sleep=1 --tries=3 --timeout=45
```

Open <http://127.0.0.1:8000>, copy PDF_API_KEY from your local `.env` into the service
key field, and queue the sample. The key is held only in page memory. The browser
uses the same API as your backend; it does not render the PDF. Stop the server
and worker with Ctrl+C when done.

## Automate it

From a trusted backend, POST the shape in `sample.json` to `/api/documents` with
`Authorization: Bearer YOUR_SERVICE_KEY`, `Content-Type: application/json`, and
an `Idempotency-Key` of 8–100 letters, digits, underscores or hyphens. Use a stable
business-event ID, such as `order-1042-invoice-v1`.

The response is 202 with `id`, `state`, `status_url`, `download_url`, `expires_at`
and `attempts`. Poll `status_url`; when `state` is `ready`, GET `download_url`
with the same Authorization header. Ready duplicates return 200. Changed data
under the same key returns 409. The second configured service key has a separate
owner namespace. Keys are server credentials, not browser authentication for
your customers; use your application's sessions/policies for customer access.

The request accepts up to 64 KiB and 100 items. Quantities are integers from 1 to
100. Prices are decimal strings from `0.00` to `999999.99`. Arithmetic uses integer
cents in the application. This sample totals line items; it does not calculate
tax, exchange rates, discounts, or establish jurisdiction-specific invoice compliance.

## Customize the document

- `resources/views/invoice.blade.php`: structure and normal escaped Blade fields.
- `renderer/invoice.css`: print layout, colors, type, tables and pagination.
- `renderer/fonts`: bundled Bebas Neue and its SIL Open Font License; Inter comes
  from the installed Fullbleed package.
- `app/Support/Invoice.php`: validation and decimal-to-integer money handling.

Only trusted application templates reach the renderer. Do not add an endpoint
for arbitrary HTML/CSS, uploaded template execution or remote asset fetching.
Missing font glyphs fail the render; add licensed fonts and test your required
languages. This specimen covers Latin text, not a universal language claim.

## Worker and retention behavior

The document and database queue entry use one SQLite transaction. This choice is
intentional: switching the queue to Redis/SQS needs a durable outbox or another
verified dispatch/recovery design. The job carries only the document UUID; invoice
data uses Laravel's encrypted model cast. Protect APP_KEY and your database backups.

The renderer process has a 30-second timeout, the job 45 seconds, and the queue
reservation 120 seconds. Failed renders get up to three attempts with 2- and
10-second backoff. Terminal failure is visible as `failed`; operators can inspect
the installation and use `php artisan queue:failed` / `php artisan queue:retry ID`.
Exceptions are deliberately generic to keep invoice text out of logs and failed jobs.
Only the complete PDF is promoted into private storage. Replayed ready jobs do
not render again. This is retry-safe job handling, not an exactly-once guarantee.

Downloads expire after 24 hours (PDF_RETENTION_HOURS, bounded to 1–168). Expired
records return 410 until pruning; after deletion they return 404. Pruning removes
the encrypted inputs and private PDFs. Idempotency is retained only while the
document record exists. Keep durable business-event deduplication in your system
if it must outlive that window. Expired queued jobs cannot recreate deleted records.

```sh
php artisan documents:prune
php artisan schedule:work
```

The schedule prunes every five minutes and failed queue records daily. For a server,
run Laravel's scheduler every minute and supervise/restart its workers. Set your
web server's document root to `public`, keep storage/database/backups private,
configure HTTPS and a request-body limit, and replace the demo key mapping with
your authorization policy. The PHP development server is local-only. This ZIP is
a verified integration starter, not a managed production hosting service.

## Verification and licensing

The documentation repository's `tools/verify_laravel_starter.py` extracts the exact
ZIP, installs its Composer lockfile, and runs real HTTP requests, queue workers,
failure/retry/expiry scenarios, independent PDF checks and optional browser downloads.
The guide links the retained report. No mocked queue establishes these checks.

Application source: MIT (LICENSE). Composer dependencies retain their own licenses.
Fonts retain their included licenses. No billing account, hosted API, browser PDF
stack, or paid service is required by this starter.
