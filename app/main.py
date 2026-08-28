from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from app.connection_manager import manager
from app import security

app = FastAPI(title="Chat Service")


@app.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str, token: str = Query(...)):
    payload = security.decode_token(token)

    if payload is None or payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    user_id = payload.get("sub")

    await manager.connect(websocket, room)
    await manager.broadcast_to_room(room, f"[Sistema] Un usuario se unió a la sala")

    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast_to_room(room, f"Usuario {user_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)
        await manager.broadcast_to_room(room, f"[Sistema] Un usuario salió de la sala")