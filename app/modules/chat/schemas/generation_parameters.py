from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GenerationParameters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
    )

    top_p: float | None = Field(
        default=None,
        gt=0,
        le=1,
    )

    top_k: int | None = Field(
        default=None,
        ge=-1,
    )

    max_tokens: int | None = Field(
        default=None,
        gt=0,
    )

    seed: int | None = None

    extra_parameters: dict[str, Any] = Field(
        default_factory=dict
    )