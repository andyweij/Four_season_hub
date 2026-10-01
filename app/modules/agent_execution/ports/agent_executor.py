from collections.abc import AsyncIterator
from typing import Protocol

from app.modules.agent_execution.schemas.cancellation_response import (
    CancellationResponse,
)
from app.modules.agent_execution.schemas.execution_events import (
    ExecutionEvent,
)
from app.modules.agent_execution.schemas.task_request import AgentTaskRequest
from app.modules.agent_management.domain.agent_definition import (
    AgentDefinition,
)


class AgentExecutor(Protocol):
    """原生 client 與第三方 Adapter 都要遵循的 Hub 內部介面。"""

    def stream_run(
        self,
        definition: AgentDefinition,
        request: AgentTaskRequest,
    ) -> AsyncIterator[ExecutionEvent]:
        """
        將通用任務轉成對方格式，並產生統一事件。

        - 即使對方不支援串流，也可等待完整回答後產生事件。
        - 回傳事件使用 Hub 的 run_id。
        - 對方的工作/session ID 必須另外保存映射。
        - sources 只有取得結構化來源時才產生。
        - cancelled 只有確認遠端工作停止時才產生。
        """
        ...

    async def cancel(
        self,
        definition: AgentDefinition,
        run_id: str,
    ) -> CancellationResponse:
        """
        對指定 Hub run 提出取消。

        Adapter 透過已保存的映射找到第三方工作。
        不把停止本地等待，視為遠端取消完成。
        """
        ...