from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.model_gateway.schemas.completion_request import (
    ModelMessage,
)


class TokenUsage(BaseModel):
    """未知的統計保持 None，不當成 0。"""

    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class CompletionResponse(BaseModel):
    """一次非串流模型呼叫的結果。"""

    model_config = ConfigDict(extra="forbid")

    contract_version: Literal["1"] = "1"
    run_id: str = Field(min_length=1, max_length=100)

    # Gateway 產生，用來追蹤這一次模型呼叫。
    completion_id: str = Field(min_length=1)

    message: ModelMessage

    reasoning_content: str | None = None
    finish_reason: str | None = None
    usage: TokenUsage | None = None

    @model_validator(mode="after")
    def validate_assistant_response(self) -> "CompletionResponse":
        if self.message.role != "assistant":
            raise ValueError("completion response requires assistant role")

        return self