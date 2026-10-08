# SPDX-License-Identifier: MIT
"""Small ASGI adapter around the shared, bounded invoice handler."""
import asyncio
import base64

from handler import MAX_BODY_BYTES, handler


async def reply(send, status, body, headers):
    await send({'type': 'http.response.start', 'status': status,
                'headers': [(key.lower().encode('ascii'), value.encode('ascii'))
                            for key, value in headers.items()]})
    await send({'type': 'http.response.body', 'body': body})


async def app(scope, receive, send):
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
    if scope['type'] != 'http':
        return
    if scope['path'] == '/healthz' and scope['method'] == 'GET':
        await reply(send, 200, b'{"ok":true}', {'Content-Type': 'application/json'})
        return
    body = bytearray()
    while True:
        message = await receive()
        if message['type'] == 'http.disconnect':
            return
        body.extend(message.get('body', b''))
        if len(body) > MAX_BODY_BYTES:
            await reply(send, 413, b'{"error":"Invoice request is too large"}',
                        {'Content-Type': 'application/json', 'Cache-Control': 'private, no-store'})
            return
        if not message.get('more_body', False):
            break
    event = dict(version='2.0', rawPath=scope['path'],
                 requestContext={'http': {'method': scope['method']}},
                 headers={key.decode('latin-1'): value.decode('latin-1') for key, value in scope['headers']},
                 body=base64.b64encode(body).decode('ascii'), isBase64Encoded=True)
    result = await asyncio.to_thread(handler, event, None)
    payload = base64.b64decode(result['body'], validate=True) if result['isBase64Encoded'] else result['body'].encode('utf-8')
    await reply(send, result['statusCode'], payload, result['headers'])
