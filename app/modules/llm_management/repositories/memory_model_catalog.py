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
            entry.model_name: entry
            for entry in entries
        }

    async def get_by_name(
        self,
        model_name: str,
    ) -> ModelCatalogEntry | None:
        return self._entries.get(model_name)

    async def list_all(
        self,
    ) -> list[ModelCatalogEntry]:
        return list(self._entries.values())