from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from app.connection_manager import manager

app = FastAPI(title="Chat Service")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Mensaje: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)