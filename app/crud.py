import uuid
from sqlalchemy.orm import Session
from app import models

def get_or_create_room(db: Session , room_name: str) -> models.Room:
    room = db.query(models.Room).filter(models.Room.name == room_name).first()
    if room is None:
        room = models.Room(name = room_name)
        db.add(room)
        db.commit()
        db.refresh(room)
    return room

def save_message(
    db: Session,
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    user_email: str,
    content: str,
) -> models.Message:
    message = models.Message(
        room_id=room_id,
        user_id=user_id,
        user_email=user_email,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_recent_messages(db: Session, room_id: uuid.UUID, limit: int = 50) -> list[models.Message]:
    messages = (
        db.query(models.Message)
        .filter(models.Message.room_id == room_id)
        .order_by(models.Message.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(messages))