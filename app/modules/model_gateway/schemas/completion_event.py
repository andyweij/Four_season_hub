from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.model_gateway.schemas.completion_response import TokenUsage


class EventBase(BaseModel):
    """識別單次模型呼叫；同一個 Agent run 可有多次 completion。"""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    run_id: str = Field(min_length=1, max_length=100)
    completion_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)


class CompletionStartedEvent(EventBase):
    type: Literal["started"] = "started"


class ContentDeltaEvent(EventBase):
    type: Literal["content_delta"] = "content_delta"
    content: str = Field(min_length=1)


class ReasoningDeltaEvent(EventBase):
    type: Literal["reasoning_delta"] = "reasoning_delta"
    content: str = Field(min_length=1)


class CompletionCompletedEvent(EventBase):
    type: Literal["completed"] = "completed"

    finish_reason: str | None = None
    usage: TokenUsage | None = None


class CompletionFailedEvent(EventBase):
    type: Literal["failed"] = "failed"

    code: str = Field(min_length=1)
    message: str


class CompletionCancelledEvent(EventBase):
    type: Literal["cancelled"] = "cancelled"


CompletionEvent = Annotated[
    CompletionStartedEvent
    | ContentDeltaEvent
    | ReasoningDeltaEvent
    | CompletionCompletedEvent
    | CompletionFailedEvent
    | CompletionCancelledEvent,
    Field(discriminator="type"),
]