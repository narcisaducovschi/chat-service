from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from app.connection_manager import manager
from app import security

app = FastAPI(title="Chat Service")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket , token: str = Query(...)):
    payload = security.decode_token(token)

    if payload is None or payload.get('type') != 'access':
        await websocket.close(code=1008)
        return

    user_id = payload.get('sub')

    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Usuario {user_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)