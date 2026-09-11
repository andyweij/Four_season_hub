from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ContentPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class Message(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    sequence: int
    role: Literal["user", "assistant", "system"]
    content: list[ContentPart]
    model: str | None = None
    finish_reason: str | None = None
    usage: dict | None = None
    status: Literal["complete", "cancelled", "error"] = "complete"
    created_at: datetime