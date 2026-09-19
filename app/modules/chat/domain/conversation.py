from datetime import datetime

from pydantic import BaseModel


class Conversation(BaseModel):
    id: str
    user_id: str
    title: str | None = None
    model: str
    message_seq: int = 0
    created_at: datetime
    updated_at: datetime