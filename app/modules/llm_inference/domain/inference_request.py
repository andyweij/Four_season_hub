from pydantic import BaseModel
from app.modules.chat.domain.enums import MessageRole


class InferenceMessage(BaseModel):
    role: MessageRole
    content: str


class InferenceRequest(BaseModel):
    model_type: str
    model: str
    messages: list[InferenceMessage]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    reasoning_effort: bool = False
