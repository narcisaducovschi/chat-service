import uuid
from datetime import datetime
from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    user_id: uuid.UUID
    user_email: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True