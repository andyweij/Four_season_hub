from pydantic import BaseModel, Field
from app.modules.chat.domain.enums import MessageRole


class MessageResponse(BaseModel):
    role: MessageRole
    content: str
    sources: list[dict] = Field(default_factory=list)
    run_id: str | None = None
    agent_id: str | None = None
    agent_version: str | None = None
    status: str = "complete"
