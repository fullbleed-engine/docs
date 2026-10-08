# Fullbleed PDF invoices for AWS Lambda

Send invoice JSON to a Python handler and receive a styled PDF. This starter
uses the published Fullbleed 2.5.20 wheel, bundled Inter, and the included DM Serif
Display and Bebas Neue fonts. No browser or system-font installation is needed.
All business details and prices in the sample are fictional.

## Try it locally

Install Docker with Linux containers (25 or newer, with Buildx) and Python 3.10
or newer for the small client. No AWS account is needed for this local path.
Run from this directory:

```sh
docker buildx build --platform linux/amd64 --provenance=false --load --tag fullbleed-lambda .
docker run --rm --name fullbleed-lambda --publish 127.0.0.1:9000:8080 --read-only --tmpfs /tmp:rw,size=64m --user 10001:10001 --cap-drop ALL --security-opt no-new-privileges:true --memory 512m --cpus 2 --pids-limit 128 fullbleed-lambda
```

Keep that terminal open. In another terminal in this directory:

```sh
python client.py local sample.json output/invoice.pdf
```

Open `output/invoice.pdf`. Edit the JSON or `templates/invoice.html` and
`templates/invoice.css`; rebuild the image after source/template changes.
Data values are escaped once before substitution. The table can span pages and
repeats its header. The sample does not calculate tax, discounts, or payments.

Stop the container when finished:

```sh
docker stop fullbleed-lambda
```

For native ARM64, use `--platform linux/arm64` in the build command and add
`--build-arg LAMBDA_BASE=public.ecr.aws/lambda/python:3.13-arm64@sha256:5c171b30fe6af43e6264da6f3cd932f71563dacb334c545473c0120ca7d99168`.
The architecture-specific image pins are also in `base-images.json`.

AWS's base image includes its Runtime Interface Emulator. The local invocation
URL returns a JSON envelope; `client.py` decodes its base64 body to a PDF.
It is not the same HTTP interface as a deployed Function URL.
See [AWS's Python container instructions](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html).

## Endpoint contract

The handler accepts Function URL / HTTP API payload format 2.0 events for
`POST /invoices` with `Content-Type: application/json`. `sample.json` shows the
complete required document schema. Both ordinary and base64 request bodies work.

| Field | Limit |
| --- | --- |
| Request JSON | 64 KiB after decoding |
| `number` | 1–40 ASCII letters, digits, `_` or `-`; starts with a letter/digit |
| `customer` | 1–80 characters |
| `issued`, `due` | Valid `YYYY-MM-DD` dates |
| `items` | 1–100 rows |
| `description` | 1–160 characters per row |
| `quantity` | Integer 1–100 |
| `unit_price` | Decimal string `0.00` through `999999.99` |
| Returned PDF | At most 4,000,000 bytes before base64 |

Unknown fields and control characters are rejected. Prices use decimal
arithmetic. The configured fonts suit the included Latin-script examples;
add explicit fonts and inspect output for other writing systems.

Success returns an `application/pdf` attachment, `private, no-store`, and
`isBase64Encoded: true`. Errors are JSON: 400 invalid data, 404 wrong path,
405 wrong method, 413 oversized input, 415 wrong content type, 422 oversized PDF,
or 500 rendering failure. PDFs and invoice inputs are not retained by this code.
Application templates and fonts are read-only; it fetches no document assets.

## Deploy in your AWS account

Local tests incur no AWS charges. Deployment creates AWS resources and may incur
charges. Build one architecture, push the image to your private ECR repository,
and obtain its digest URI using [AWS's deployment instructions](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html).
The ECR image and function must use the same Region and architecture.

`template.yaml` accepts that image URI; it does not build or push an image.
It creates a 512 MiB, 30-second function with two reserved concurrent executions,
a Function URL with `AWS_IAM` authorization, and logs retained for seven days.
Review these settings for your account and workload:

```sh
aws cloudformation deploy --template-file template.yaml --stack-name fullbleed-pdf --capabilities CAPABILITY_IAM --parameter-overrides ImageUri=YOUR_ECR_URI_WITH_DIGEST Architecture=x86_64
```

The Function URL needs signed requests and caller permissions. See
[AWS's Function URL access controls](https://docs.aws.amazon.com/lambda/latest/dg/urls-auth.html).
Keep application-level customer/tenant authorization in your calling service.
An authorized caller can supply the invoice data; this starter is not an order
database, payment system, durable job queue, or public anonymous renderer.

For a synchronous automation step, get `FunctionName` from the stack outputs and
invoke using the AWS CLI, which uses your configured AWS credentials:

```sh
python client.py event sample.json event.json
aws lambda invoke --function-name YOUR_FUNCTION_NAME --payload fileb://event.json response.json
python client.py decode response.json output/invoice.pdf
```

This synchronous call returns the document; asynchronous invocation discards the
returned bytes. For queued jobs, store output in your application's durable
storage and define idempotency, retries, and delivery there.

## Verification

To run the focused handler tests outside Docker:

```sh
python -m pip install --only-binary=:all: -r requirements.txt
python -m unittest -v test_handler.py
```

The docs repository's `tools/verify_lambda_starter.py` also extracts the exact
download, invokes the real runtime emulator, checks repeated and multi-page
PDFs using independent readers, and retains output for inspection. The
CloudFormation template is schema-checked with `cfn-lint`.

These checks do not validate deployment, IAM enforcement, Lambda's orchestrator,
hosted latency, throughput, or cost. AWS explains the emulator's scope in its
[RIE repository](https://github.com/aws/aws-lambda-runtime-interface-emulator).

Code: MIT (`LICENSE`). Included fonts: SIL OFL (notices in `fonts/`); Inter ships
with Fullbleed. Written with AI coding assistance for Fullbleed.
