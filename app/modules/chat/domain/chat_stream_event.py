from typing import Literal
from pydantic import BaseModel
from app.modules.chat.domain.enums import ChatEventType


class ChatStreamEvent(BaseModel):
    type: ChatEventType
    conversation_id: str
    user_message_id: str | None = None
    assistant_message_id: str | None = None
    content: str | None = None
    finish_reason: str | None = None
    usage: dict | None = None
