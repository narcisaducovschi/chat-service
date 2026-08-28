from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
import json

from app.connection_manager import manager
from app.database import Base, engine, get_db
from app import security, crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chat Service")


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_name: str,
    token: str = Query(...),
    db: Session = Depends(get_db),
):
    payload = security.decode_token(token)

    if payload is None or payload.get("type") != "access":
        await websocket.close(code=1008)
        return

    user_id = payload.get("sub")
    user_email = payload.get("email", "usuario")  

    room = crud.get_or_create_room(db, room_name)

    await manager.connect(websocket, room_name)

    recent_messages = crud.get_recent_messages(db, room.id)
    for msg in recent_messages:
        await websocket.send_text(json.dumps({
            "user_email": msg.user_email,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }))

    await manager.broadcast_to_room(room_name, json.dumps({
        "system": True,
        "content": f"Un usuario se unió a la sala",
    }))

    try:
        while True:
            data = await websocket.receive_text()

            crud.save_message(db, room.id, user_id, user_email, data)

            await manager.broadcast_to_room(room_name, json.dumps({
                "user_email": user_email,
                "content": data,
            }))
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name)
        await manager.broadcast_to_room(room_name, json.dumps({
            "system": True,
            "content": f"Un usuario salió de la sala",
        }))