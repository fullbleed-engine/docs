# SPDX-License-Identifier: MIT
"""Focused handler tests; real document inspection is in the download verifier."""
import base64
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import handler
from client import event

SAMPLE = json.loads((Path(__file__).parent / 'sample.json').read_text())


class HandlerTests(unittest.TestCase):
    def test_method_path_and_content_type(self):
        for key, value, expected in [('rawPath', '/missing', 404), ('version', '1.0', 400), ('headers', {}, 415)]:
            with self.subTest(key=key):
                request = event(SAMPLE)
                request[key] = value
                self.assertEqual(handler.handler(request, None)['statusCode'], expected)
        request = event(SAMPLE)
        request['requestContext']['http']['method'] = 'GET'
        response = handler.handler(request, None)
        self.assertEqual(response['statusCode'], 405)
        self.assertEqual(response['headers']['Allow'], 'POST')

    def test_invalid_envelopes(self):
        for value in [None, [], {}, {'version': '2.0', 'requestContext': []}]:
            with self.subTest(value=value):
                self.assertEqual(handler.handler(value, None)['statusCode'], 400)

    def test_invalid_data_never_renders(self):
        cases = []
        for field, value in [('number', '../x'), ('number', 'x\r\nHeader: value'),
                             ('customer', '<' * 81), ('customer', '\ud800'),
                             ('issued', '2026-02-30'), ('due', '20261031'),
                             ('items', []), ('items', [SAMPLE['items'][0]] * 101)]:
            data = copy.deepcopy(SAMPLE)
            data[field] = value
            cases.append(data)
        for field, value in [('quantity', True), ('quantity', 0), ('quantity', 101),
                             ('unit_price', 1.5), ('unit_price', 'NaN'), ('unit_price', '-1.00'),
                             ('unit_price', '1000000.00'), ('description', 'x' * 161),
                             ('description', '\x00')]:
            data = copy.deepcopy(SAMPLE)
            data['items'][0][field] = value
            cases.append(data)
        cases.extend([[], None, {**SAMPLE, 'html': '<script>ignored</script>'}])
        with patch.object(handler, 'render_invoice') as render:
            for data in cases:
                with self.subTest(data=str(data)[:80]):
                    self.assertEqual(handler.handler(event(data), None)['statusCode'], 400)
            render.assert_not_called()

    def test_body_limits_and_encoding(self):
        for body, encoded, expected in [('x' * 65_537, False, 413), ('***', True, 400),
                                        ('[]', 'false', 400), ('{' * 3000, False, 400)]:
            request = event(SAMPLE)
            request.update(body=body, isBase64Encoded=encoded)
            self.assertEqual(handler.handler(request, None)['statusCode'], expected)
        request = event(SAMPLE)
        request.update(body=base64.b64encode(b' ' * 65_537).decode(), isBase64Encoded=True)
        self.assertEqual(handler.handler(request, None)['statusCode'], 413)

    def test_failure_and_output_limit_are_contained(self):
        with patch.object(handler, 'render_invoice', side_effect=RuntimeError('PRIVATE DATA')):
            response = handler.handler(event(SAMPLE), None)
            self.assertEqual(response['statusCode'], 500)
            self.assertNotIn('PRIVATE', response['body'])
        with patch.object(handler, 'render_invoice', return_value=b'x' * (handler.MAX_PDF_BYTES + 1)):
            self.assertEqual(handler.handler(event(SAMPLE), None)['statusCode'], 422)

    def test_real_render_recovers_and_does_not_change_input(self):
        data = copy.deepcopy(SAMPLE)
        request = event(data)
        first = handler.handler(request, None)
        self.assertEqual(first['statusCode'], 200)
        self.assertTrue(base64.b64decode(first['body']).startswith(b'%PDF-'))
        self.assertEqual(data, SAMPLE)
        invalid = event({})
        self.assertEqual(handler.handler(invalid, None)['statusCode'], 400)
        request['body'] = base64.b64encode(request['body'].encode()).decode()
        request['isBase64Encoded'] = True
        second = handler.handler(request, None)
        self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
