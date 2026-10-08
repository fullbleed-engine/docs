# SPDX-License-Identifier: MIT
"""Post invoice JSON to the workflow and save a successful PDF attachment."""
import argparse
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

parser = argparse.ArgumentParser()
parser.add_argument('input', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--url', default='http://localhost:5678/webhook/fullbleed-invoice')
args = parser.parse_args()
request = Request(args.url, data=args.input.read_bytes(), method='POST', headers={'Content-Type': 'application/json'})
try:
    with urlopen(request, timeout=45) as response:
        pdf = response.read(4_000_001)
        if response.status != 200 or response.headers.get_content_type() != 'application/pdf' or not pdf.startswith(b'%PDF-') or len(pdf) > 4_000_000:
            raise SystemExit('The workflow did not return a successful PDF; no file written.')
except HTTPError as error:
    raise SystemExit(f'Workflow returned HTTP {error.code}; no file written. Check input and workflow configuration.') from None
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open('xb') as output:
    output.write(pdf)
print(f'Saved {len(pdf)} PDF bytes to {args.output}')
