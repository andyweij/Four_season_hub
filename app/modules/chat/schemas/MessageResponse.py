from pydantic import BaseModel
from app.modules.chat.domain.enums import MessageRole


class MessageResponse(BaseModel):
    role: MessageRole
    content: str
