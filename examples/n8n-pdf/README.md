# Invoice PDFs in n8n

An incoming JSON invoice becomes a styled PDF attachment. The workflow uses
n8n's built-in Webhook, HTTP Request, If, and Respond to Webhook nodes. Fullbleed
renders the document in a separate local container, with editable HTML/CSS and
bundled fonts. No custom/community node is required.

This download is a local development kit for Docker with Linux containers and
Docker Compose v2. Its n8n port is published on loopback; the renderer is reachable
only on the private Compose network. The sample businesses and prices are fictional.

## Run the workflow

1. Extract the ZIP and open `fullbleed-n8n-starter` in a terminal.
2. Run `docker compose up --build -d`.
3. Open <http://localhost:5678> and create the local n8n owner account.
4. Create a workflow. Use its menu's **Import from File** command to import
   `workflows/invoice-webhook.json`. Save and publish the workflow.
5. From the extracted project directory, run:

   ```sh
   python post_invoice.py sample.json output/invoice.pdf
   ```

Open `output/invoice.pdf`. Change a customer, quantity, price, or line item in
`sample.json`, then send it again using a new output filename. The client refuses
to overwrite an existing file or save an error response as a PDF.

The default production webhook URL is
`http://localhost:5678/webhook/fullbleed-invoice`. n8n calls it a production URL
to distinguish it from the editor's temporary test listener; this does not make
the local kit a production deployment. If you use **Listen for test event**, pass
`--url http://localhost:5678/webhook-test/fullbleed-invoice` instead.

Stop the kit with `docker compose down`. The named n8n volume remains so your
local owner account and workflow survive a restart. Do not delete that volume
unless you intend to erase those local settings and workflows.

## How the PDF moves through n8n

`Receive invoice` forwards the request's JSON body to `Render PDF`.
The HTTP Request node calls `http://renderer:8000/invoices` with a 25-second
timeout. Its response format is **File**, its binary field is **pdf**, and it
includes the response status and headers.

`PDF received?` requires both HTTP 200 and `Content-Type: application/pdf`.
The true output passes the binary **pdf** field to `Return PDF`. The false output
returns a JSON error with an appropriate 4xx code or 502. Connection failures use
the HTTP node's separate error output and return JSON with HTTP 502.

To deliver a PDF through another application, connect the successful branch to
your storage or delivery node and select **pdf** as its binary input field.
Configure that destination and its credentials in your n8n instance. Do not
wire the rejected-request or service-error branches to a PDF delivery node.

Keep the renderer URL configured by the workflow author. Do not take a server URL,
template path, or HTML/CSS from an unauthenticated caller.

## Invoice data and design

The required fields are `number`, `customer`, `issued`, `due`, and `items`.
Use ISO dates (`YYYY-MM-DD`), integer quantities, and decimal **strings** for prices:

```json
{"description": "Design workshop", "quantity": 8, "unit_price": "125.00"}
```

The renderer accepts 1–100 rows, quantities 1–100, prices 0.00–999999.99,
customer names up to 80 characters, and descriptions up to 160 characters.
Invoice numbers use 1–40 ASCII letters, digits, hyphens, or underscores and must
start with a letter or digit. Decoded JSON is limited to 64 KiB and the PDF to
4,000,000 bytes. Unsupported fields, malformed text, and invalid dates are rejected.
Prices and totals use decimal arithmetic; this example has no tax, discounts,
currency conversion, or payment processing.

Edit `renderer/templates/invoice.html` and `invoice.css`, then rebuild with
`docker compose up --build -d`. Fonts are in `renderer/fonts`; their OFL licenses
are included. The table flows across pages with repeated headers and page counters.
Input strings are escaped before insertion into the application-owned template.

## Use your existing n8n installation

You can import `workflows/invoice-webhook.json` separately. Set the HTTP node's URL
to a renderer endpoint reachable from your n8n server. `localhost` inside a
container refers to that container; the kit uses the Compose service name
`renderer`. An n8n Cloud instance cannot reach this kit's private network.

An existing instance keeps its own network and execution-retention settings. If
it enables SSRF protection, allow only the intended renderer destination under
your administrator's policy. Use its credential store for any endpoint secrets.

## Deployment boundaries

The local webhook has no authentication. Before exposing a real invoice workflow,
authenticate callers, authorize the requested record, configure TLS and request
limits, and protect the renderer endpoint. Set secure cookies when moving n8n
behind HTTPS. n8n's owner-account login does not authenticate a webhook configured
with no authentication.

The renderer uses only the internal `documents` network. n8n also joins the
`access` network so Docker can publish its loopback port and destination nodes
can make outbound connections. No destination credentials are included.
The kit disables diagnostics,
version notifications, and saved successful, failed, and manual execution data.
n8n still persists its account/workflow settings and may use temporary binary
storage during execution; review storage and retention settings for your deployment.

A webhook response is synchronous. For durable jobs, add a queue or persistent
job record, output storage, retries, and idempotency keyed to the invoice and
template version. Repeating this workflow renders again; it does not prevent a
downstream email or upload from occurring twice. No destination is preconfigured.

The image pins are n8n 2.42.5 and Python 3.14.8; the renderer uses the published
Fullbleed 2.5.20 wheel. Resource limits are local test settings, not capacity
recommendations. Update pins periodically and rerun the workflow checks.

## Source and verification

The kit is assembled by `tools/build_n8n_starter.py` in the
[Fullbleed docs repository](https://github.com/fullbleed-engine/docs).
It includes the exact invoice handler, templates, and fonts shared with the
[Lambda starter](https://docs.fullbleed.dev/guides/aws-lambda-pdf/).
The source manifest identifies every included file and its hash.

The workflow verification script imports and publishes the actual downloadable
workflow into an isolated n8n instance, posts synthetic invoices, independently
reads the returned PDFs, and checks validation errors, renderer unavailability,
and recovery. It retains the result and removes only its own containers and volume.
See [the guide](https://docs.fullbleed.dev/guides/n8n-pdf/) for retained evidence.

Fullbleed and this example use MIT; included font licenses are separate. n8n is
separately licensed under its [Sustainable Use License](https://docs.n8n.io/n8n-community-license/community-license).
This is a Fullbleed example, not an n8n endorsement or verified community node.
Written with AI coding assistance.

[n8n HTTP Request](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)
· [Respond to Webhook](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/)
· [Workflow import/export](https://docs.n8n.io/hosting/cli-commands/)
