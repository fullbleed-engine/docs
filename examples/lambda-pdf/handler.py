# SPDX-License-Identifier: MIT
"""A bounded JSON-to-PDF endpoint for Lambda Function URLs (payload format 2.0)."""
import base64
import binascii
from datetime import date
from decimal import Decimal
from html import escape
from importlib import resources
import json
import logging
from pathlib import Path
import re
from string import Template

import fullbleed

ROOT = Path(__file__).resolve().parent
HTML = Template((ROOT / 'templates/invoice.html').read_text(encoding='utf-8'))
CSS = (ROOT / 'templates/invoice.css').read_text(encoding='utf-8')
FONTS = [str(resources.files('fullbleed_assets').joinpath('fonts/Inter-Variable.ttf')),
         str(ROOT / 'fonts/DMSerifDisplay-Regular.ttf'), str(ROOT / 'fonts/BebasNeue-Regular.ttf')]
MAX_BODY_BYTES = 65_536
MAX_ITEMS = 100
MAX_PDF_BYTES = 4_000_000  # Leaves room for base64 and JSON inside a buffered response.
LOGGER = logging.getLogger(__name__)


class InvalidInvoice(ValueError):
    pass


def text(value, limit):
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise InvalidInvoice('Invalid text field')
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise InvalidInvoice('Control characters are not accepted')
    value.encode('utf-8')
    return value


def fields(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise InvalidInvoice('Unexpected or missing fields')


def validate(data):
    fields(data, ['number', 'customer', 'issued', 'due', 'items'])
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,39}', text(data['number'], 40)):
        raise InvalidInvoice('Invalid invoice number')
    text(data['customer'], 80)
    for key in ['issued', 'due']:
        value = text(data[key], 10)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise InvalidInvoice('Dates must use YYYY-MM-DD')
        date.fromisoformat(value)
    if not isinstance(data['items'], list) or not 1 <= len(data['items']) <= MAX_ITEMS:
        raise InvalidInvoice('Expected 1 to 100 line items')
    for item in data['items']:
        fields(item, ['description', 'quantity', 'unit_price'])
        text(item['description'], 160)
        if type(item['quantity']) is not int or not 1 <= item['quantity'] <= 100:
            raise InvalidInvoice('Quantity must be an integer from 1 to 100')
        if not re.fullmatch(r'(?:0|[1-9][0-9]{0,5})\.[0-9]{2}', text(item['unit_price'], 9)):
            raise InvalidInvoice('Price must be a decimal string from 0.00 to 999999.99')
    return data


def render_invoice(data):
    # Templates/fonts are reusable application assets. Each invocation gets its
    # own engine and document data; no customer record or PDF is cached globally.
    items = data['items']
    amounts = [Decimal(item['unit_price']) * item['quantity'] for item in items]
    total = f"{sum(amounts, Decimal('0.00')):,.2f}"
    rows = ''.join(
        f"<tr><td>{escape(item['description'])}</td><td class='number'>{item['quantity']}</td>"
        f"<td class='number'>{Decimal(item['unit_price']):,.2f}</td><td class='number'>{amount:,.2f}</td></tr>"
        for item, amount in zip(items, amounts)
    )
    html = HTML.substitute(**{key: escape(data[key]) for key in ['number', 'customer', 'issued', 'due']},
                           rows=rows, total=total, total_class='compact' if len(total) > 12 else '')
    engine = fullbleed.PdfEngine(font_files=FONTS, document_title='Invoice ' + data['number'], document_lang='en-US')
    return engine.render_pdf(html, CSS)


def error(status, message, **headers):
    return dict(statusCode=status, isBase64Encoded=False,
                headers={'Content-Type': 'application/json', 'Cache-Control': 'private, no-store', **headers},
                body=json.dumps({'error': message}))


def handler(event, context):
    if not isinstance(event, dict) or event.get('version') != '2.0':
        return error(400, 'Expected a Lambda Function URL payload format 2.0 event')
    request_context = event.get('requestContext')
    http = request_context.get('http') if isinstance(request_context, dict) else None
    if not isinstance(http, dict) or not isinstance(http.get('method'), str):
        return error(400, 'Missing HTTP request context')
    if event.get('rawPath') != '/invoices':
        return error(404, 'Not found')
    if http['method'] != 'POST':
        return error(405, 'Use POST', Allow='POST')
    headers = event.get('headers')
    if not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
        return error(400, 'Invalid headers')
    content_type = {k.lower(): v for k, v in headers.items()}.get('content-type', '').split(';', 1)[0].strip().lower()
    if content_type != 'application/json':
        return error(415, 'Use application/json')
    body = event.get('body')
    encoded = event.get('isBase64Encoded', False)
    if not isinstance(body, str) or type(encoded) is not bool:
        return error(400, 'Invalid body encoding')
    if len(body) > (MAX_BODY_BYTES * 4 // 3 + 4 if encoded else MAX_BODY_BYTES):
        return error(413, 'Invoice request is too large')
    try:
        raw = base64.b64decode(body, validate=True) if encoded else body.encode('utf-8')
        if len(raw) > MAX_BODY_BYTES:
            return error(413, 'Invoice request is too large')
        data = validate(json.loads(raw.decode('utf-8')))
    except (ValueError, UnicodeError, binascii.Error, RecursionError):
        return error(400, 'Invalid invoice JSON; see the sample and field limits')
    try:
        pdf = render_invoice(data)
        if len(pdf) > MAX_PDF_BYTES:
            return error(422, 'PDF exceeds this endpoint output limit')
        return dict(statusCode=200, isBase64Encoded=True,
                    headers={'Content-Type': 'application/pdf',
                             'Content-Disposition': f'attachment; filename="{data["number"]}.pdf"',
                             'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff'},
                    body=base64.b64encode(pdf).decode('ascii'))
    except Exception:
        # Log no event, customer data, or PDF bytes. Inspect deployment/assets if
        # this happens; the client receives a generic error and can retry later.
        LOGGER.error('PDF rendering failed (request %s)', getattr(context, 'aws_request_id', 'local'))
        return error(500, 'PDF rendering failed')
