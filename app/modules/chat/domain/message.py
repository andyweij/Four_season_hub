from datetime import datetime
from typing import Literal

from pydantic import BaseModel
from app.modules.chat.domain.enums import MessageRole, MessageStatus


class ContentPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class Message(BaseModel):
    id: str
    conversation_id: str
    user_id: str
    sequence: int
    role: MessageRole
    content: list[ContentPart]
    model: str | None = None
    finish_reason: str | None = None
    usage: dict | None = None
    status: MessageStatus = MessageStatus.COMPLETE
    created_at: datetime
