# SPDX-License-Identifier: MIT
"""Create an event, invoke the local emulator, or decode an AWS CLI response."""
import argparse
import base64
import json
from pathlib import Path
import urllib.request


def event(data):
    return {'version': '2.0', 'rawPath': '/invoices',
            'requestContext': {'http': {'method': 'POST'}},
            'headers': {'content-type': 'application/json'},
            'body': json.dumps(data), 'isBase64Encoded': False}


def save_pdf(response, destination):
    if response.get('statusCode') != 200 or response.get('isBase64Encoded') is not True:
        raise ValueError('PDF request failed: ' + json.dumps(response))
    pdf = base64.b64decode(response['body'], validate=True)
    if not pdf.startswith(b'%PDF-'):
        raise ValueError('Response is not a PDF')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(pdf)
    print(f'Wrote {destination} ({len(pdf):,} bytes)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    make = sub.add_parser('event', help='Write a Lambda event for aws lambda invoke')
    make.add_argument('input', type=Path)
    make.add_argument('output', type=Path)
    local = sub.add_parser('local', help='Invoke the loopback runtime emulator')
    local.add_argument('input', type=Path)
    local.add_argument('output', type=Path)
    local.add_argument('--port', type=int, default=9000)
    decode = sub.add_parser('decode', help='Decode an aws lambda invoke response')
    decode.add_argument('input', type=Path)
    decode.add_argument('output', type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding='utf-8'))
    if args.command == 'event':
        args.output.write_text(json.dumps(event(data)), encoding='utf-8')
    elif args.command == 'decode':
        save_pdf(data, args.output)
    else:
        request = urllib.request.Request(
            f'http://127.0.0.1:{args.port}/2015-03-31/functions/function/invocations',
            data=json.dumps(event(data)).encode(), headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=40) as response:
            save_pdf(json.load(response), args.output)
