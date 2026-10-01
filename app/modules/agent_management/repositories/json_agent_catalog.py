from pathlib import Path
from app.modules.agent_management.domain.agent_definition import AgentCatalog


class JsonAgentCatalogRepository:
    """Validated startup snapshot; persisted enablement lives in MongoDB."""
    def __init__(self, path: Path):
        self._catalog = AgentCatalog.model_validate_json(path.read_text(encoding="utf-8"))

    async def get(self, agent_id):
        return next((a.model_copy(deep=True) for a in self._catalog.agents if a.id == agent_id), None)

    async def list_all(self):
        return [a.model_copy(deep=True) for a in self._catalog.agents]
