from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.agent_execution.schemas.execution_request import (
    ExecutionMessage,
    ExecutionParameters,
    ModelRef,
)


class AgentTaskRequest(BaseModel):
    """Hub 內部任務，由 Adapter 轉換成 Agent 的外部請求。"""

    model_config = ConfigDict(extra="forbid")

    # 由 Hub 產生，不使用第三方的工作 ID 取代。
    run_id: str = Field(min_length=1, max_length=100)

    agent_id: str = Field(min_length=1, max_length=100)

    # 第一版統一支援文字對話。
    # Hub 負責驗證對話所有權、取得歷史並限制上下文大小。
    messages: list[ExecutionMessage] = Field(min_length=1)

    # 只有 hub_per_run 模式允許在任務內指定模型。
    model_ref: ModelRef | None = None

    # None 表示採用 Agent 自己的生成設定。
    # 是否可指定，由整合模式與 Adapter 驗證。
    parameters: ExecutionParameters | None = None

    # Hub 等待與管理這次任務的整體時限。
    # 能否同時限制遠端工作，由 Adapter 能力決定。
    timeout_seconds: int = Field(default=120, ge=1, le=600)

    # Agent 專用、非敏感的選項。
    # 例如 Web Search 的搜尋次數、RAG 的資料集識別。
    # Adapter 必須用專屬 schema 驗證，不直接原樣轉送。
    options: dict[str, Any] = Field(default_factory=dict)