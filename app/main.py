from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy.orm import Session
import json

from app.connection_manager import manager
from app.database import Base, engine, get_db
from app import security, crud
from fastapi.staticfiles import StaticFiles



Base.metadata.create_all(bind=engine)

app = FastAPI(title="Chat Service")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

async def broadcast_user_list(room_name: str):
    users = manager.get_users_in_room(room_name)
    await manager.broadcast_to_room(room_name, json.dumps({
        "type": "user_list",
        "users": users,
    }))


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

    await manager.connect(websocket, room_name, user_email)

    recent_messages = crud.get_recent_messages(db, room.id)
    for msg in recent_messages:
        await websocket.send_text(json.dumps({
            "type": "message",
            "user_email": msg.user_email,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }))

    await manager.broadcast_to_room(room_name, json.dumps({
        "type": "system",
        "content": f"{user_email} se unió a la sala",
    }))
    await broadcast_user_list(room_name)

    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)

            if data.get("type") == "typing":
                await manager.broadcast_to_room(
                    room_name,
                    json.dumps({"type": "typing", "user_email": user_email}),
                    exclude=websocket,
                )
                continue

            content = data.get("content", "")
            crud.save_message(db, room.id, user_id, user_email, content)

            await manager.broadcast_to_room(room_name, json.dumps({
                "type": "message",
                "user_email": user_email,
                "content": content,
            }))

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name)
        await manager.broadcast_to_room(room_name, json.dumps({
            "type": "system",
            "content": f"{user_email} salió de la sala",
        }))
        await broadcast_user_list(room_name)