from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CancellationResponse(BaseModel):
    """描述取消要求的處理結果，不代表遠端工作已停止。"""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=100)

    status: Literal[
        "cancel_requested",
        "already_terminal",
        "unsupported",
        "not_found",
    ]

    # 只有 already_terminal 時使用。
    terminal_status: Literal[
        "completed",
        "failed",
        "cancelled",
    ] | None = None

    message: str | None = None

    @model_validator(mode="after")
    def validate_terminal_status(self) -> "CancellationResponse":
        if self.status == "already_terminal":
            if self.terminal_status is None:
                raise ValueError(
                    "already_terminal requires terminal_status"
                )
        elif self.terminal_status is not None:
            raise ValueError(
                "terminal_status only applies to already_terminal"
            )

        return self