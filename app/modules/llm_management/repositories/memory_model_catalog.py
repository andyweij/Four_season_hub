from collections.abc import Iterable

from app.modules.llm_management.domain.models import (
    ModelCatalogEntry,
)


class InMemoryModelCatalog:
    def __init__(
        self,
        entries: Iterable[ModelCatalogEntry],
    ):
        self._entries = {
            entry.model_key: entry
            for entry in entries
        }

    async def get_by_key(
        self,
        model_key: str,
    ) -> ModelCatalogEntry | None:
        return self._entries.get(model_key)

    async def list_all(
        self,
    ) -> list[ModelCatalogEntry]:
        return list(self._entries.values())