from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["assistant"] = "assistant"
    content: str


class TokenUsageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    conversation_id: str
    message_id: str

    model: str
    message: ChatMessageResponse
    finish_reason: str | None = None
    usage: TokenUsageResponse | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class GetModelsResponse(BaseModel):
    model_name: list[str]