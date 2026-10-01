from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.agent_execution.schemas.execution_request import ModelRef


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolCall(ContractModel):
    """模型要求執行的工具呼叫。"""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)

    # 保留原始 JSON 字串。
    # 即使模型產生無效 JSON，也能讓 Agent 回傳工具錯誤。
    arguments: str


class ModelMessage(ContractModel):
    """文字版模型訊息，支援完整工具呼叫往返。"""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None

    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None

    # Gateway 管理的供應商原始狀態識別。
    # Agent 只保存並回傳，不解讀其中內容。
    provider_state_ref: str | None = None

    @model_validator(mode="after")
    def validate_role_fields(self) -> "ModelMessage":
        if self.role == "tool":
            if not self.tool_call_id:
                raise ValueError("tool message requires tool_call_id")
            if self.content is None:
                raise ValueError("tool message requires content")

        elif self.tool_call_id is not None:
            raise ValueError("tool_call_id is only valid for tool messages")

        if self.role != "assistant":
            if self.tool_calls:
                raise ValueError("tool_calls require assistant role")
            if self.provider_state_ref is not None:
                raise ValueError(
                    "provider_state_ref requires assistant role"
                )

        if self.role in {"system", "user"} and not self.content:
            raise ValueError("system/user message requires non-empty content")

        if self.role == "assistant":
            if self.content is None and not self.tool_calls:
                raise ValueError(
                    "assistant message requires content or tool_calls"
                )

        return self


class ToolDefinition(ContractModel):
    """統一工具定義，由 provider adapter 轉成供應商格式。"""

    name: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    description: str

    # JSON Schema；內容合法性與供應商限制另由 Gateway 驗證。
    parameters: dict[str, Any]


class CompletionParameters(ContractModel):
    """每次模型呼叫的生成參數。"""

    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    max_tokens: int | None = Field(default=None, ge=1)

    # 先固定支援的值；adapter 依模型能力轉換或拒絕。
    reasoning_effort: Literal["low", "medium", "high"] | None = None


class CompletionRequest(ContractModel):
    """Agent → Hub Model Gateway 的 v1 請求。"""

    contract_version: Literal["1"] = "1"
    run_id: str = Field(min_length=1, max_length=100)

    model_ref: ModelRef
    messages: list[ModelMessage] = Field(min_length=1)

    tools: list[ToolDefinition] = Field(default_factory=list)
    tool_choice: Literal["auto", "none", "required"] = "none"

    parameters: CompletionParameters = Field(
        default_factory=CompletionParameters
    )

    @model_validator(mode="after")
    def validate_tools(self) -> "CompletionRequest":
        names = [tool.name for tool in self.tools]

        if len(names) != len(set(names)):
            raise ValueError("tool names must be unique")

        if self.tool_choice != "none" and not self.tools:
            raise ValueError(
                "auto/required tool_choice requires tools"
            )

        return self