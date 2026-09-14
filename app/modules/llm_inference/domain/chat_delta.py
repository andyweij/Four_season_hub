from pydantic import BaseModel


class ChatDelta(BaseModel):
    conversation_id: str
    message_id: str
    content: str
    finish_reason: str | None = None
    usage: dict | None = None
