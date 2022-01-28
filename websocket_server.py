import asyncio
import websockets
from websockets.legacy.server import WebSocketServerProtocol

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


async def main():
    async with websockets.serve(handler, '0.0.0.0', 8765):
        await asyncio.Future()

asyncio.run(main())
