from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EventBase(ContractModel):
    """每個事件都必須能對應到同一次執行。"""

    contract_version: Literal["1"] = "1"
    run_id: str = Field(min_length=1, max_length=100)
    sequence: int = Field(ge=1)


class Source(ContractModel):
    """搜尋取得的參考資料，不代表一定被最終答案引用。"""

    id: str = Field(min_length=1)
    title: str
    url: str = Field(pattern=r"^https?://")
    summary: str


class Usage(ContractModel):
    """跨供應商共用的 token 統計；未知數值保持 None。"""

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class StartedEvent(EventBase):
    type: Literal["started"] = "started"


class ProgressEvent(EventBase):
    type: Literal["progress"] = "progress"
    stage: str = Field(min_length=1)
    message: str


class SourcesEvent(EventBase):
    type: Literal["sources"] = "sources"

    # 每次送出截至目前的完整來源清單；接收方以此取代舊清單。
    sources: list[Source]


class TextDeltaEvent(EventBase):
    type: Literal["text_delta"] = "text_delta"
    content: str = Field(min_length=1)


class ReasoningDeltaEvent(EventBase):
    type: Literal["reasoning_delta"] = "reasoning_delta"
    content: str = Field(min_length=1)


class CompletedEvent(EventBase):
    type: Literal["completed"] = "completed"
    finish_reason: str | None = None

    # 最終回答的 token 統計。
    usage: Usage | None = None

    # 包含決策與最終回答的全部模型呼叫統計；能完整取得時才填入。
    total_usage: Usage | None = None


class FailedEvent(EventBase):
    type: Literal["failed"] = "failed"
    code: str = Field(min_length=1)
    message: str


class CancelledEvent(EventBase):
    type: Literal["cancelled"] = "cancelled"
    reason: str | None = None


ExecutionEvent = Annotated[
    StartedEvent
    | ProgressEvent
    | SourcesEvent
    | TextDeltaEvent
    | ReasoningDeltaEvent
    | CompletedEvent
    | FailedEvent
    | CancelledEvent,
    Field(discriminator="type"),
]