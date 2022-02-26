import asyncio
import websockets
from websockets.legacy.server import WebSocketServerProtocol
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from threading import Thread

connected = set()


async def handler(websocket: WebSocketServerProtocol):
    connected.add(websocket)
    while True:
        try:
            message = await websocket.recv()
            websockets.broadcast(connected, message)
        except websockets.ConnectionClosedOK:
            connected.remove(websocket)
            break


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, directory='web')


def http_server():
    with TCPServer(('0.0.0.0', 8000), Handler) as httpd:
        print('starting http server...')
        httpd.serve_forever()


async def _ws_server():
    async with websockets.serve(handler, '0.0.0.0', 8765):
        print('starting ws server...')
        await asyncio.Future()


def ws_server():
    asyncio.run(_ws_server())


ws_thread = Thread(target=ws_server)
http_thread = Thread(target=http_server)

ws_thread.start()
http_thread.start()

ws_thread.join()
http_thread.join()
