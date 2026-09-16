from pydantic import BaseModel


class ChatDelta(BaseModel):
    content: str
    reasoning_content: str | None = None
    finish_reason: str | None = None
    usage: dict | None = None
