from typing import Protocol
from app.modules.agent_management.domain.agent_definition import AgentDefinition


class AgentCatalogRepository(Protocol):
    async def get(self, agent_id: str) -> AgentDefinition | None: ...
    async def list_all(self) -> list[AgentDefinition]: ...
