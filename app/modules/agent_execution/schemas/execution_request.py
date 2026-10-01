from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ContractModel(BaseModel):
    """禁止未知欄位，避免兩個服務的契約不一致時被默默忽略。"""

    model_config = ConfigDict(extra="forbid")


class ModelRef(ContractModel):
    """指定模型來源與識別，不包含 endpoint 或 API Key。"""

    source: Literal["local", "cloud"]
    id: str = Field(min_length=1, max_length=200)


class ExecutionMessage(ContractModel):
    """第一版只支援文字；工具訊息由 Agent 執行過程自行產生。"""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ExecutionParameters(ContractModel):
    """本次回答的生成參數；實際支援範圍由 Gateway 驗證。"""

    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    max_tokens: int | None = Field(default=None, ge=1)


class ExecutionLimits(ContractModel):
    """Hub 核准的執行上限；Agent 仍可套用更嚴格的服務限制。"""

    timeout_seconds: int = Field(default=120, ge=1, le=600)
    max_iterations: int = Field(default=3, ge=1, le=10)
    max_search_calls: int = Field(default=5, ge=1, le=20)
    max_results_per_search: int = Field(default=3, ge=1, le=10)


class ExecutionRequest(ContractModel):
    """Hub → Agent 的 v1 執行契約。"""

    contract_version: Literal["1"] = "1"
    run_id: str = Field(min_length=1, max_length=100)
    agent_version: str = Field(min_length=1, max_length=100)

    model_ref: ModelRef

    execution_mode: Literal["tool_calling", "search_first"]

    # 歷史訊息加上本次問題；由 Hub 驗證所有權並限制上下文大小。
    messages: list[ExecutionMessage] = Field(min_length=1)

    parameters: ExecutionParameters = Field(
        default_factory=ExecutionParameters
    )
    limits: ExecutionLimits = Field(default_factory=ExecutionLimits)